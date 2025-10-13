"""Tests for resilience patterns in data retrieval.

This module contains unit tests for circuit breaker, retry logic,
rate limiting, and other resilience patterns used in data retrieval.
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, patch, call

from ticket_analyzer.external.resilience import (
    CircuitBreaker,
    CircuitState,
    RetryPolicy,
    RateLimiter,
    TimeoutManager,
    BulkheadIsolation
)
from ticket_analyzer.models import (
    DataRetrievalError,
    MCPError,
    AuthenticationError
)


class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""
    
    def test_circuit_breaker_initialization(self) -> None:
        """Test circuit breaker initialization with default values."""
        cb = CircuitBreaker()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.failure_threshold == 5
        assert cb.timeout == timedelta(minutes=1)
    
    def test_circuit_breaker_custom_initialization(self) -> None:
        """Test circuit breaker initialization with custom values."""
        cb = CircuitBreaker(
            failure_threshold=3,
            timeout=timedelta(seconds=30),
            recovery_timeout=timedelta(seconds=10)
        )
        
        assert cb.failure_threshold == 3
        assert cb.timeout == timedelta(seconds=30)
        assert cb.recovery_timeout == timedelta(seconds=10)
    
    def test_circuit_breaker_successful_calls(self) -> None:
        """Test circuit breaker with successful function calls."""
        cb = CircuitBreaker(failure_threshold=3)
        
        def successful_function() -> str:
            return "success"
        
        # Multiple successful calls should keep circuit closed
        for _ in range(10):
            result = cb.call(successful_function)
            assert result == "success"
            assert cb.state == CircuitState.CLOSED
            assert cb.failure_count == 0
    
    def test_circuit_breaker_failure_threshold(self) -> None:
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        def failing_function() -> str:
            raise MCPError("Service unavailable")
        
        # First few failures should keep circuit closed
        for i in range(2):
            with pytest.raises(MCPError):
                cb.call(failing_function)
            assert cb.state == CircuitState.CLOSED
            assert cb.failure_count == i + 1
        
        # Third failure should open the circuit
        with pytest.raises(MCPError):
            cb.call(failing_function)
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3
    
    def test_circuit_breaker_open_state_blocks_calls(self) -> None:
        """Test that open circuit breaker blocks function calls."""
        cb = CircuitBreaker(failure_threshold=2)
        
        def failing_function() -> str:
            raise MCPError("Service unavailable")
        
        # Trigger circuit to open
        for _ in range(2):
            with pytest.raises(MCPError):
                cb.call(failing_function)
        
        assert cb.state == CircuitState.OPEN
        
        # Now calls should be blocked without executing the function
        with pytest.raises(DataRetrievalError) as exc_info:
            cb.call(failing_function)
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    def test_circuit_breaker_half_open_transition(self) -> None:
        """Test circuit breaker transition to half-open state."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=timedelta(milliseconds=100)
        )
        
        def failing_function() -> str:
            raise MCPError("Service unavailable")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(MCPError):
                cb.call(failing_function)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Next call should transition to half-open
        with pytest.raises(MCPError):
            cb.call(failing_function)
        
        # Circuit should be open again after failure in half-open state
        assert cb.state == CircuitState.OPEN
    
    def test_circuit_breaker_recovery(self) -> None:
        """Test circuit breaker recovery after successful call in half-open state."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=timedelta(milliseconds=100)
        )
        
        call_count = 0
        
        def sometimes_failing_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise MCPError("Service unavailable")
            return "success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(MCPError):
                cb.call(sometimes_failing_function)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Successful call in half-open should close the circuit
        result = cb.call(sometimes_failing_function)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_with_different_exception_types(self) -> None:
        """Test circuit breaker behavior with different exception types."""
        cb = CircuitBreaker(failure_threshold=2)
        
        def function_with_auth_error() -> str:
            raise AuthenticationError("Auth failed")
        
        def function_with_mcp_error() -> str:
            raise MCPError("MCP failed")
        
        # Authentication errors should not count towards circuit breaker
        with pytest.raises(AuthenticationError):
            cb.call(function_with_auth_error)
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED
        
        # MCP errors should count
        with pytest.raises(MCPError):
            cb.call(function_with_mcp_error)
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED


class TestRetryPolicy:
    """Test cases for RetryPolicy class."""
    
    def test_retry_policy_initialization(self) -> None:
        """Test retry policy initialization."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff_factor == 2.0
    
    def test_retry_policy_successful_first_attempt(self) -> None:
        """Test retry policy with successful first attempt."""
        policy = RetryPolicy(max_attempts=3)
        
        call_count = 0
        
        def successful_function() -> str:
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = policy.execute(successful_function)
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_policy_eventual_success(self) -> None:
        """Test retry policy with eventual success after failures."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)  # Fast retry for testing
        
        call_count = 0
        
        def eventually_successful_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MCPError("Temporary failure")
            return "success"
        
        result = policy.execute(eventually_successful_function)
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_policy_max_attempts_exceeded(self) -> None:
        """Test retry policy when max attempts are exceeded."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.01)
        
        call_count = 0
        
        def always_failing_function() -> str:
            nonlocal call_count
            call_count += 1
            raise MCPError("Persistent failure")
        
        with pytest.raises(MCPError):
            policy.execute(always_failing_function)
        
        assert call_count == 2
    
    def test_retry_policy_exponential_backoff(self) -> None:
        """Test retry policy exponential backoff timing."""
        policy = RetryPolicy(
            max_attempts=4,
            base_delay=0.1,
            backoff_factor=2.0,
            max_delay=1.0
        )
        
        call_times = []
        
        def failing_function() -> str:
            call_times.append(time.time())
            raise MCPError("Always fails")
        
        start_time = time.time()
        
        with pytest.raises(MCPError):
            policy.execute(failing_function)
        
        # Verify exponential backoff timing
        assert len(call_times) == 4
        
        # Check delays between calls (approximately)
        delays = [call_times[i] - call_times[i-1] for i in range(1, len(call_times))]
        
        # First delay should be around base_delay (0.1s)
        assert 0.05 < delays[0] < 0.2
        
        # Second delay should be around base_delay * backoff_factor (0.2s)
        assert 0.15 < delays[1] < 0.3
        
        # Third delay should be around base_delay * backoff_factor^2 (0.4s)
        assert 0.3 < delays[2] < 0.6
    
    def test_retry_policy_with_jitter(self) -> None:
        """Test retry policy with jitter to avoid thundering herd."""
        policy = RetryPolicy(
            max_attempts=3,
            base_delay=0.1,
            jitter=True
        )
        
        call_times = []
        
        def failing_function() -> str:
            call_times.append(time.time())
            raise MCPError("Always fails")
        
        with pytest.raises(MCPError):
            policy.execute(failing_function)
        
        # With jitter, delays should vary
        delays = [call_times[i] - call_times[i-1] for i in range(1, len(call_times))]
        
        # Delays should be within reasonable bounds but with some variation
        for delay in delays:
            assert 0.05 < delay < 0.3  # Should be around base_delay with jitter
    
    def test_retry_policy_non_retryable_exceptions(self) -> None:
        """Test that certain exceptions are not retried."""
        policy = RetryPolicy(max_attempts=3)
        
        call_count = 0
        
        def function_with_auth_error() -> str:
            nonlocal call_count
            call_count += 1
            raise AuthenticationError("Auth failed")
        
        # Authentication errors should not be retried
        with pytest.raises(AuthenticationError):
            policy.execute(function_with_auth_error)
        
        assert call_count == 1  # Should only be called once


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_rate_limiter_initialization(self) -> None:
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_second=10)
        
        assert limiter.requests_per_second == 10
        assert limiter.bucket_size == 10
    
    def test_rate_limiter_allows_requests_within_limit(self) -> None:
        """Test rate limiter allows requests within the limit."""
        limiter = RateLimiter(requests_per_second=100)  # High limit for testing
        
        # Should allow multiple requests quickly
        for _ in range(10):
            assert limiter.acquire() is True
    
    def test_rate_limiter_blocks_requests_over_limit(self) -> None:
        """Test rate limiter blocks requests over the limit."""
        limiter = RateLimiter(requests_per_second=2, bucket_size=2)
        
        # First two requests should succeed
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        
        # Third request should be blocked
        assert limiter.acquire(timeout=0.1) is False
    
    def test_rate_limiter_token_bucket_refill(self) -> None:
        """Test rate limiter token bucket refills over time."""
        limiter = RateLimiter(requests_per_second=10, bucket_size=2)
        
        # Exhaust the bucket
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire(timeout=0.01) is False
        
        # Wait for refill
        time.sleep(0.2)  # Should refill ~2 tokens
        
        # Should be able to make requests again
        assert limiter.acquire() is True
    
    def test_rate_limiter_with_function_decorator(self) -> None:
        """Test rate limiter as function decorator."""
        limiter = RateLimiter(requests_per_second=5)
        
        call_count = 0
        
        @limiter.limit
        def limited_function() -> str:
            nonlocal call_count
            call_count += 1
            return f"call_{call_count}"
        
        # Should allow first few calls
        result1 = limited_function()
        result2 = limited_function()
        
        assert result1 == "call_1"
        assert result2 == "call_2"
        assert call_count == 2


class TestTimeoutManager:
    """Test cases for TimeoutManager class."""
    
    def test_timeout_manager_successful_execution(self) -> None:
        """Test timeout manager with successful execution."""
        manager = TimeoutManager(timeout=1.0)
        
        def quick_function() -> str:
            time.sleep(0.1)
            return "success"
        
        result = manager.execute(quick_function)
        assert result == "success"
    
    def test_timeout_manager_timeout_exceeded(self) -> None:
        """Test timeout manager when timeout is exceeded."""
        manager = TimeoutManager(timeout=0.1)
        
        def slow_function() -> str:
            time.sleep(0.5)
            return "success"
        
        with pytest.raises(DataRetrievalError) as exc_info:
            manager.execute(slow_function)
        
        assert "Operation timed out" in str(exc_info.value)
    
    def test_timeout_manager_with_context_manager(self) -> None:
        """Test timeout manager as context manager."""
        with TimeoutManager(timeout=0.5) as manager:
            def quick_function() -> str:
                time.sleep(0.1)
                return "success"
            
            result = manager.execute(quick_function)
            assert result == "success"
    
    def test_timeout_manager_cleanup_on_timeout(self) -> None:
        """Test timeout manager cleanup when timeout occurs."""
        cleanup_called = False
        
        def cleanup_function() -> None:
            nonlocal cleanup_called
            cleanup_called = True
        
        manager = TimeoutManager(timeout=0.1, cleanup_function=cleanup_function)
        
        def slow_function() -> str:
            time.sleep(0.5)
            return "success"
        
        with pytest.raises(DataRetrievalError):
            manager.execute(slow_function)
        
        # Cleanup should have been called
        assert cleanup_called is True


class TestBulkheadIsolation:
    """Test cases for BulkheadIsolation class."""
    
    def test_bulkhead_initialization(self) -> None:
        """Test bulkhead isolation initialization."""
        bulkhead = BulkheadIsolation(max_concurrent=3)
        
        assert bulkhead.max_concurrent == 3
        assert bulkhead.current_count == 0
    
    def test_bulkhead_allows_concurrent_requests(self) -> None:
        """Test bulkhead allows concurrent requests up to limit."""
        bulkhead = BulkheadIsolation(max_concurrent=2)
        
        def slow_function() -> str:
            time.sleep(0.2)
            return "success"
        
        import threading
        results = []
        
        def run_function():
            try:
                result = bulkhead.execute(slow_function)
                results.append(result)
            except Exception as e:
                results.append(str(e))
        
        # Start two concurrent threads (should both succeed)
        threads = [threading.Thread(target=run_function) for _ in range(2)]
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 2
        assert all(result == "success" for result in results)
    
    def test_bulkhead_blocks_excess_requests(self) -> None:
        """Test bulkhead blocks requests over the limit."""
        bulkhead = BulkheadIsolation(max_concurrent=1)
        
        def slow_function() -> str:
            time.sleep(0.3)
            return "success"
        
        import threading
        results = []
        
        def run_function():
            try:
                result = bulkhead.execute(slow_function, timeout=0.1)
                results.append(result)
            except Exception as e:
                results.append(str(e))
        
        # Start two concurrent threads (second should be blocked)
        threads = [threading.Thread(target=run_function) for _ in range(2)]
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 2
        # One should succeed, one should timeout
        success_count = sum(1 for result in results if result == "success")
        timeout_count = sum(1 for result in results if "timeout" in result.lower())
        
        assert success_count == 1
        assert timeout_count == 1


class TestResilienceIntegration:
    """Integration tests for resilience patterns working together."""
    
    def test_circuit_breaker_with_retry_policy(self) -> None:
        """Test circuit breaker combined with retry policy."""
        cb = CircuitBreaker(failure_threshold=2)
        retry = RetryPolicy(max_attempts=3, base_delay=0.01)
        
        call_count = 0
        
        def failing_function() -> str:
            nonlocal call_count
            call_count += 1
            raise MCPError("Service unavailable")
        
        # First attempt with retry should fail multiple times
        with pytest.raises(MCPError):
            retry.execute(lambda: cb.call(failing_function))
        
        # Circuit should still be closed after first retry sequence
        assert cb.state == CircuitState.CLOSED
        assert call_count == 3  # Retry policy attempted 3 times
        
        # Second attempt should open the circuit
        call_count = 0
        with pytest.raises(MCPError):
            retry.execute(lambda: cb.call(failing_function))
        
        assert cb.state == CircuitState.OPEN
        assert call_count == 1  # Only one attempt before circuit opened
    
    def test_rate_limiter_with_circuit_breaker(self) -> None:
        """Test rate limiter combined with circuit breaker."""
        limiter = RateLimiter(requests_per_second=2, bucket_size=2)
        cb = CircuitBreaker(failure_threshold=2)
        
        call_count = 0
        
        def rate_limited_failing_function() -> str:
            nonlocal call_count
            call_count += 1
            raise MCPError("Service unavailable")
        
        # First two calls should be rate limited and fail
        with pytest.raises(MCPError):
            limiter.execute(lambda: cb.call(rate_limited_failing_function))
        
        with pytest.raises(MCPError):
            limiter.execute(lambda: cb.call(rate_limited_failing_function))
        
        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
        
        # Third call should be blocked by circuit breaker, not rate limiter
        with pytest.raises(DataRetrievalError) as exc_info:
            limiter.execute(lambda: cb.call(rate_limited_failing_function))
        
        assert "Circuit breaker is open" in str(exc_info.value)
        assert call_count == 2  # Third call was blocked by circuit breaker
    
    def test_complete_resilience_stack(self) -> None:
        """Test complete resilience stack with all patterns."""
        # Setup resilience components
        timeout_mgr = TimeoutManager(timeout=1.0)
        rate_limiter = RateLimiter(requests_per_second=10)
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        retry_policy = RetryPolicy(max_attempts=2, base_delay=0.01)
        bulkhead = BulkheadIsolation(max_concurrent=2)
        
        call_count = 0
        
        def resilient_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise MCPError("Temporary failure")
            return "success"
        
        # Combine all resilience patterns
        def execute_with_resilience():
            return timeout_mgr.execute(
                lambda: rate_limiter.execute(
                    lambda: circuit_breaker.call(
                        lambda: retry_policy.execute(
                            lambda: bulkhead.execute(resilient_function)
                        )
                    )
                )
            )
        
        # Should eventually succeed after retries
        result = execute_with_resilience()
        assert result == "success"
        
        # Verify all components worked together
        assert call_count >= 2  # At least some retries occurred
        assert circuit_breaker.state == CircuitState.CLOSED  # Circuit remained closed
    
    def test_resilience_patterns_error_propagation(self) -> None:
        """Test proper error propagation through resilience patterns."""
        cb = CircuitBreaker(failure_threshold=1)
        retry = RetryPolicy(max_attempts=2, base_delay=0.01)
        
        def auth_error_function() -> str:
            raise AuthenticationError("Auth failed")
        
        # Authentication errors should propagate through without retries
        with pytest.raises(AuthenticationError):
            retry.execute(lambda: cb.call(auth_error_function))
        
        # Circuit breaker should not be affected by auth errors
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0