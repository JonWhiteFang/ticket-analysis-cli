"""Resilience patterns for external service communication.

This module implements resilience patterns including Circuit Breaker, Retry Policy,
and Exponential Backoff to handle failures in external service calls gracefully.
These patterns help prevent cascading failures and improve system reliability.
"""

from __future__ import annotations
import logging
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from dataclasses import dataclass

from ..interfaces import ResilienceInterface
from ..models import (
    CircuitBreakerOpenError,
    DataRetrievalError,
    MCPError,
    MCPTimeoutError,
    MCPConnectionError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: timedelta = timedelta(minutes=1)
    failure_rate_threshold: float = 0.5
    minimum_requests: int = 10


class CircuitBreaker:
    """Circuit breaker pattern implementation for external service calls.
    
    The circuit breaker monitors failures and prevents requests to failing
    services, allowing them time to recover while providing fast failure
    responses to clients.
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None) -> None:
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration.
        """
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._request_count = 0
        self._failure_rate = 0.0
        
        logger.info(f"Circuit breaker initialized with config: {self._config}")
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute.
            *args: Positional arguments for function.
            **kwargs: Keyword arguments for function.
            
        Returns:
            Function result.
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
        """
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError(
                    "Circuit breaker is open",
                    {"failure_count": self._failure_count, "state": self._state.value}
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self._last_failure_time:
            return True
        
        return datetime.now() - self._last_failure_time > self._config.timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self._request_count += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._reset_circuit()
                logger.info("Circuit breaker reset to CLOSED after successful calls")
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0
        
        self._update_failure_rate()
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        self._request_count += 1
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        # Only count certain exceptions as circuit breaker failures
        if self._is_circuit_breaker_failure(exception):
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker opened from HALF_OPEN due to failure")
            elif self._state == CircuitState.CLOSED:
                self._update_failure_rate()
                if self._should_open_circuit():
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker opened due to {self._failure_count} failures")
    
    def _is_circuit_breaker_failure(self, exception: Exception) -> bool:
        """Determine if exception should trigger circuit breaker."""
        # Circuit breaker should trigger on connection and timeout errors
        # but not on authentication or validation errors
        circuit_breaker_exceptions = (
            MCPConnectionError,
            MCPTimeoutError,
            ConnectionError,
            TimeoutError
        )
        return isinstance(exception, circuit_breaker_exceptions)
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened based on failure criteria."""
        # Check failure count threshold
        if self._failure_count >= self._config.failure_threshold:
            return True
        
        # Check failure rate threshold (only if we have minimum requests)
        if (self._request_count >= self._config.minimum_requests and 
            self._failure_rate >= self._config.failure_rate_threshold):
            return True
        
        return False
    
    def _update_failure_rate(self) -> None:
        """Update failure rate calculation."""
        if self._request_count > 0:
            self._failure_rate = self._failure_count / self._request_count
    
    def _reset_circuit(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._request_count = 0
        self._failure_rate = 0.0
        self._last_failure_time = None
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self._state.value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "request_count": self._request_count,
            "failure_rate": self._failure_rate,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._reset_circuit()
        logger.info("Circuit breaker manually reset")


@dataclass
class RetryConfig:
    """Configuration for retry policy."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple = (MCPConnectionError, MCPTimeoutError, ConnectionError, TimeoutError)


class ExponentialBackoff:
    """Exponential backoff with jitter for retry delays."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0,
                 backoff_factor: float = 2.0, jitter: bool = True) -> None:
        """Initialize exponential backoff.
        
        Args:
            base_delay: Base delay in seconds.
            max_delay: Maximum delay in seconds.
            backoff_factor: Multiplier for each retry.
            jitter: Whether to add random jitter.
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.
        
        Args:
            attempt: Attempt number (0-based).
            
        Returns:
            Delay in seconds.
        """
        # Calculate exponential delay
        delay = self.base_delay * (self.backoff_factor ** attempt)
        
        # Cap at maximum delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


class RetryPolicy:
    """Retry policy with exponential backoff and jitter."""
    
    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        """Initialize retry policy.
        
        Args:
            config: Retry configuration.
        """
        self._config = config or RetryConfig()
        self._backoff = ExponentialBackoff(
            base_delay=self._config.base_delay,
            max_delay=self._config.max_delay,
            backoff_factor=self._config.backoff_factor,
            jitter=self._config.jitter
        )
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry logic.
        
        Args:
            func: Function to execute.
            *args: Positional arguments for function.
            **kwargs: Keyword arguments for function.
            
        Returns:
            Function result.
            
        Raises:
            Last exception if all retries fail.
        """
        last_exception = None
        
        for attempt in range(self._config.max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    logger.debug(f"Non-retryable exception: {type(e).__name__}")
                    raise
                
                # Don't retry on last attempt
                if attempt == self._config.max_attempts - 1:
                    break
                
                # Calculate delay and wait
                delay = self._backoff.calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
        
        # All retries exhausted
        logger.error(f"All {self._config.max_attempts} retry attempts failed")
        raise last_exception
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        return isinstance(exception, self._config.retry_exceptions)


class ResilienceManager(ResilienceInterface):
    """Manager that combines circuit breaker and retry patterns."""
    
    def __init__(self,
                 circuit_breaker: Optional[CircuitBreaker] = None,
                 retry_policy: Optional[RetryPolicy] = None) -> None:
        """Initialize resilience manager.
        
        Args:
            circuit_breaker: Circuit breaker instance.
            retry_policy: Retry policy instance.
        """
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._retry_policy = retry_policy or RetryPolicy()
    
    def execute_with_resilience(self, operation: Callable[..., T], 
                               *args: Any, **kwargs: Any) -> T:
        """Execute operation with resilience patterns applied.
        
        Args:
            operation: Function to execute with resilience.
            *args: Positional arguments for the operation.
            **kwargs: Keyword arguments for the operation.
            
        Returns:
            Result of the operation.
            
        Raises:
            ResilienceError: If operation fails after all retry attempts.
        """
        def resilient_operation() -> T:
            return self._circuit_breaker.call(operation, *args, **kwargs)
        
        try:
            return self._retry_policy.execute(resilient_operation)
        except Exception as e:
            logger.error(f"Resilient operation failed: {e}")
            raise DataRetrievalError(
                f"Operation failed with resilience patterns: {e}",
                {
                    "circuit_state": self._circuit_breaker.get_state(),
                    "operation": operation.__name__ if hasattr(operation, '__name__') else str(operation)
                }
            )
    
    def get_circuit_state(self) -> str:
        """Get current circuit breaker state."""
        return self._circuit_breaker.get_state()
    
    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._circuit_breaker.reset()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get resilience metrics."""
        return {
            "circuit_breaker": self._circuit_breaker.get_metrics(),
            "retry_config": {
                "max_attempts": self._retry_policy._config.max_attempts,
                "base_delay": self._retry_policy._config.base_delay,
                "max_delay": self._retry_policy._config.max_delay
            }
        }


def with_resilience(circuit_breaker: Optional[CircuitBreaker] = None,
                   retry_policy: Optional[RetryPolicy] = None):
    """Decorator for adding resilience patterns to functions.
    
    Args:
        circuit_breaker: Circuit breaker instance.
        retry_policy: Retry policy instance.
        
    Returns:
        Decorated function with resilience patterns.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        resilience_manager = ResilienceManager(circuit_breaker, retry_policy)
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return resilience_manager.execute_with_resilience(func, *args, **kwargs)
        
        return wrapper
    return decorator


def with_circuit_breaker(config: Optional[CircuitBreakerConfig] = None):
    """Decorator for adding circuit breaker pattern to functions.
    
    Args:
        config: Circuit breaker configuration.
        
    Returns:
        Decorated function with circuit breaker protection.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        circuit_breaker = CircuitBreaker(config)
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return circuit_breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator for adding retry pattern to functions.
    
    Args:
        config: Retry configuration.
        
    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        retry_policy = RetryPolicy(config)
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_policy.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator


class EmptyDatasetHandler:
    """Handler for empty dataset scenarios."""
    
    @staticmethod
    def handle_empty_response(response: Any, operation: str) -> Any:
        """Handle empty response from external service.
        
        Args:
            response: Response from external service.
            operation: Operation that returned empty response.
            
        Returns:
            Appropriate default value for empty response.
        """
        if response is None:
            logger.info(f"Empty response for operation: {operation}")
            return []
        
        if isinstance(response, (list, dict)) and len(response) == 0:
            logger.info(f"Empty dataset returned for operation: {operation}")
            return response
        
        return response
    
    @staticmethod
    def validate_response_format(response: Any, expected_type: type) -> bool:
        """Validate response format matches expected type.
        
        Args:
            response: Response to validate.
            expected_type: Expected response type.
            
        Returns:
            True if response format is valid.
        """
        if not isinstance(response, expected_type):
            logger.warning(
                f"Response type mismatch: expected {expected_type.__name__}, "
                f"got {type(response).__name__}"
            )
            return False
        
        return True


class MalformedResponseHandler:
    """Handler for malformed response scenarios."""
    
    @staticmethod
    def handle_malformed_response(response: Any, operation: str) -> Dict[str, Any]:
        """Handle malformed response from external service.
        
        Args:
            response: Malformed response.
            operation: Operation that returned malformed response.
            
        Returns:
            Sanitized response or empty result.
        """
        logger.warning(f"Malformed response for operation {operation}: {type(response)}")
        
        # Try to extract useful data from malformed response
        if isinstance(response, str):
            try:
                import json
                return json.loads(response)
            except json.JSONDecodeError:
                logger.error("Failed to parse string response as JSON")
                return {"error": "malformed_response", "raw_data": response}
        
        if hasattr(response, '__dict__'):
            return response.__dict__
        
        # Return empty result for completely unusable responses
        return {"error": "malformed_response", "data": []}
    
    @staticmethod
    def sanitize_response_data(data: Any) -> Any:
        """Sanitize response data to handle malformed fields.
        
        Args:
            data: Response data to sanitize.
            
        Returns:
            Sanitized data.
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip None values and empty strings
                if value is not None and value != "":
                    sanitized[key] = MalformedResponseHandler.sanitize_response_data(value)
            return sanitized
        
        elif isinstance(data, list):
            return [
                MalformedResponseHandler.sanitize_response_data(item) 
                for item in data if item is not None
            ]
        
        else:
            return data


class TimeoutHandler:
    """Handler for timeout scenarios."""
    
    def __init__(self, default_timeout: float = 30.0) -> None:
        """Initialize timeout handler.
        
        Args:
            default_timeout: Default timeout in seconds.
        """
        self.default_timeout = default_timeout
    
    def handle_timeout(self, operation: str, timeout_duration: float) -> None:
        """Handle timeout scenario.
        
        Args:
            operation: Operation that timed out.
            timeout_duration: Timeout duration in seconds.
            
        Raises:
            DataRetrievalError: Always raises with timeout information.
        """
        logger.error(f"Operation {operation} timed out after {timeout_duration} seconds")
        raise DataRetrievalError(
            f"Operation timed out: {operation}",
            {
                "operation": operation,
                "timeout_duration": timeout_duration,
                "error_type": "timeout"
            }
        )
    
    def with_timeout(self, func: Callable[..., T], timeout: Optional[float] = None) -> Callable[..., T]:
        """Add timeout handling to function.
        
        Args:
            func: Function to add timeout to.
            timeout: Timeout duration in seconds.
            
        Returns:
            Function with timeout handling.
        """
        timeout_duration = timeout or self.default_timeout
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import signal
            
            def timeout_handler(signum: int, frame: Any) -> None:
                self.handle_timeout(func.__name__, timeout_duration)
            
            # Set up timeout signal
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout_duration))
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Clean up timeout
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        return wrapper