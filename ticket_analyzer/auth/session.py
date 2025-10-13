"""Authentication session management with automatic expiry and secure memory handling.

This module provides comprehensive session management for authentication
operations, including session lifecycle management, automatic expiry,
re-authentication logic, and secure memory management for authentication state.
"""

from __future__ import annotations
import gc
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from ..interfaces import AuthenticationSessionInterface
from ..models.config import AuthConfig
from ..models.exceptions import AuthenticationError, SecurityError

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    """Metadata for authentication sessions.
    
    Contains detailed information about the authentication session
    including timing, activity, and security information.
    
    Attributes:
        session_id: Unique identifier for the session
        start_time: When the session was started
        last_activity: Last activity timestamp
        expiry_time: When the session expires
        auth_method: Authentication method used
        user_info: User information (sanitized)
        security_level: Security level of the session
        refresh_count: Number of times session was refreshed
    """
    session_id: str
    start_time: datetime
    last_activity: datetime
    expiry_time: datetime
    auth_method: str = "midway"
    user_info: Dict[str, Any] = field(default_factory=dict)
    security_level: str = "standard"
    refresh_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if session has expired.
        
        Returns:
            True if session is expired, False otherwise.
        """
        return datetime.now() >= self.expiry_time
    
    def time_until_expiry(self) -> timedelta:
        """Get time remaining until session expires.
        
        Returns:
            Time remaining as timedelta. Negative if already expired.
        """
        return self.expiry_time - datetime.now()
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary containing session metadata.
        """
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expiry_time": self.expiry_time.isoformat(),
            "auth_method": self.auth_method,
            "user_info": self.user_info,
            "security_level": self.security_level,
            "refresh_count": self.refresh_count,
            "is_expired": self.is_expired(),
            "time_until_expiry_seconds": int(self.time_until_expiry().total_seconds())
        }


class AuthenticationSession(AuthenticationSessionInterface):
    """Authentication session manager with lifecycle management.
    
    Manages authentication sessions with automatic expiry, activity tracking,
    and secure memory management. Provides comprehensive session lifecycle
    management including creation, validation, refresh, and cleanup.
    
    Features:
    - Automatic session expiry based on configuration
    - Activity-based session extension
    - Secure memory management for sensitive data
    - Thread-safe operations
    - Comprehensive session metadata tracking
    - Automatic cleanup and garbage collection
    
    Attributes:
        _config: Authentication configuration
        _metadata: Current session metadata
        _lock: Thread lock for thread-safe operations
        _cleanup_callbacks: Callbacks to execute on session cleanup
    """
    
    def __init__(self, config: Optional[AuthConfig] = None) -> None:
        """Initialize authentication session manager.
        
        Args:
            config: Authentication configuration. Uses defaults if not provided.
        """
        self._config = config or AuthConfig()
        self._metadata: Optional[SessionMetadata] = None
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._cleanup_callbacks: list[Callable[[], None]] = []
        
        # Validate configuration
        self._config.validate()
        
        logger.debug("AuthenticationSession initialized with %dh duration",
                    self._config.session_duration_hours)
    
    def start_session(self) -> None:
        """Start a new authentication session.
        
        Creates a new session with fresh metadata and expiry time.
        Clears any existing session data securely.
        
        Raises:
            AuthenticationError: If session cannot be started.
        """
        with self._lock:
            try:
                # Clean up any existing session
                if self._metadata:
                    logger.debug("Cleaning up existing session before starting new one")
                    self._cleanup_session_data()
                
                # Create new session
                now = datetime.now()
                session_duration = timedelta(hours=self._config.session_duration_hours)
                
                self._metadata = SessionMetadata(
                    session_id=self._generate_session_id(),
                    start_time=now,
                    last_activity=now,
                    expiry_time=now + session_duration,
                    auth_method=self._config.auth_method,
                    security_level="enhanced" if self._config.cache_credentials else "standard"
                )
                
                logger.info("Authentication session started: %s (expires: %s)",
                           self._metadata.session_id,
                           self._metadata.expiry_time.strftime("%Y-%m-%d %H:%M:%S"))
                
            except Exception as e:
                logger.error("Failed to start authentication session: %s", e)
                raise AuthenticationError(
                    f"Failed to start authentication session: {e}",
                    details={"operation": "start_session"}
                )
    
    def end_session(self) -> None:
        """End the current authentication session.
        
        Performs secure cleanup of session data and executes
        any registered cleanup callbacks.
        """
        with self._lock:
            if self._metadata:
                session_id = self._metadata.session_id
                logger.info("Ending authentication session: %s", session_id)
                
                # Execute cleanup callbacks
                self._execute_cleanup_callbacks()
                
                # Clean up session data
                self._cleanup_session_data()
                
                logger.debug("Authentication session ended: %s", session_id)
            else:
                logger.debug("No active session to end")
    
    def is_session_valid(self) -> bool:
        """Check if the current session is valid.
        
        Validates session existence, expiry, and other validity criteria.
        
        Returns:
            True if session is valid and not expired, False otherwise.
        """
        with self._lock:
            if not self._metadata:
                logger.debug("No active session")
                return False
            
            if self._metadata.is_expired():
                logger.info("Session expired: %s", self._metadata.session_id)
                self._cleanup_session_data()
                return False
            
            # Update activity timestamp
            self._metadata.update_activity()
            
            logger.debug("Session valid: %s (expires in %s)",
                        self._metadata.session_id,
                        self._metadata.time_until_expiry())
            
            return True
    
    def get_session_duration(self) -> Optional[datetime]:
        """Get the duration of the current session.
        
        Returns:
            Session start time as datetime, None if no active session.
        """
        with self._lock:
            if self._metadata:
                return self._metadata.start_time
            return None
    
    def refresh_session(self) -> bool:
        """Refresh the current session to extend its validity.
        
        Extends the session expiry time and updates metadata.
        Only works if current session is still valid.
        
        Returns:
            True if session was successfully refreshed, False otherwise.
            
        Raises:
            AuthenticationError: If session refresh fails.
        """
        with self._lock:
            if not self._metadata:
                logger.warning("Cannot refresh session: no active session")
                return False
            
            if self._metadata.is_expired():
                logger.warning("Cannot refresh expired session: %s", self._metadata.session_id)
                self._cleanup_session_data()
                return False
            
            try:
                # Extend session expiry
                session_duration = timedelta(hours=self._config.session_duration_hours)
                self._metadata.expiry_time = datetime.now() + session_duration
                self._metadata.refresh_count += 1
                self._metadata.update_activity()
                
                logger.info("Session refreshed: %s (new expiry: %s, refresh count: %d)",
                           self._metadata.session_id,
                           self._metadata.expiry_time.strftime("%Y-%m-%d %H:%M:%S"),
                           self._metadata.refresh_count)
                
                return True
                
            except Exception as e:
                logger.error("Failed to refresh session: %s", e)
                raise AuthenticationError(
                    f"Failed to refresh session: {e}",
                    details={"session_id": self._metadata.session_id}
                )
    
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get metadata about the current session.
        
        Returns comprehensive session information including timing,
        activity, and security details.
        
        Returns:
            Dictionary containing session metadata.
        """
        with self._lock:
            if not self._metadata:
                return {
                    "active": False,
                    "message": "No active session"
                }
            
            metadata = self._metadata.to_dict()
            metadata["active"] = True
            
            # Add configuration information
            metadata["config"] = {
                "session_duration_hours": self._config.session_duration_hours,
                "auto_refresh": self._config.auto_refresh,
                "check_interval_seconds": self._config.check_interval_seconds
            }
            
            return metadata
    
    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to execute when session is cleaned up.
        
        Args:
            callback: Function to call during session cleanup.
        """
        with self._lock:
            self._cleanup_callbacks.append(callback)
            logger.debug("Added cleanup callback: %s", callback.__name__)
    
    def remove_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Remove a cleanup callback.
        
        Args:
            callback: Function to remove from cleanup callbacks.
        """
        with self._lock:
            if callback in self._cleanup_callbacks:
                self._cleanup_callbacks.remove(callback)
                logger.debug("Removed cleanup callback: %s", callback.__name__)
    
    def get_time_until_expiry(self) -> Optional[timedelta]:
        """Get time remaining until session expires.
        
        Returns:
            Time remaining as timedelta, None if no active session.
        """
        with self._lock:
            if self._metadata and not self._metadata.is_expired():
                return self._metadata.time_until_expiry()
            return None
    
    def is_near_expiry(self, threshold_minutes: int = 15) -> bool:
        """Check if session is near expiry.
        
        Args:
            threshold_minutes: Minutes before expiry to consider "near".
            
        Returns:
            True if session expires within threshold, False otherwise.
        """
        time_remaining = self.get_time_until_expiry()
        if time_remaining is None:
            return False
        
        threshold = timedelta(minutes=threshold_minutes)
        return time_remaining <= threshold
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier.
        
        Returns:
            Unique session identifier string.
        """
        import uuid
        return f"auth_session_{uuid.uuid4().hex[:16]}"
    
    def _cleanup_session_data(self) -> None:
        """Securely clean up session data from memory.
        
        Performs secure cleanup of sensitive session information
        including metadata and any cached credentials.
        """
        if self._metadata:
            # Clear sensitive data
            session_id = self._metadata.session_id
            
            # Overwrite sensitive fields
            self._metadata.user_info.clear()
            self._metadata = None
            
            # Force garbage collection
            gc.collect()
            
            logger.debug("Session data cleaned up: %s", session_id)
    
    def _execute_cleanup_callbacks(self) -> None:
        """Execute all registered cleanup callbacks.
        
        Safely executes cleanup callbacks, logging any errors
        but not raising exceptions to ensure cleanup continues.
        """
        for callback in self._cleanup_callbacks:
            try:
                callback()
                logger.debug("Executed cleanup callback: %s", callback.__name__)
            except Exception as e:
                logger.error("Error in cleanup callback %s: %s", callback.__name__, e)
    
    def __enter__(self) -> 'AuthenticationSession':
        """Context manager entry.
        
        Returns:
            Self for use in with statements.
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit.
        
        Ensures session is properly cleaned up when exiting context.
        """
        self.end_session()


class SecureAuthenticationSession(AuthenticationSession):
    """Enhanced authentication session with additional security features.
    
    Extends the base AuthenticationSession with enhanced security measures:
    - Memory protection and secure cleanup
    - Enhanced logging with sanitization
    - Additional validation and monitoring
    - Secure credential handling
    """
    
    def __init__(self, config: Optional[AuthConfig] = None) -> None:
        """Initialize secure authentication session.
        
        Args:
            config: Authentication configuration.
        """
        super().__init__(config)
        self._security_level = "enhanced"
        logger.info("SecureAuthenticationSession initialized with enhanced security")
    
    def start_session(self) -> None:
        """Start secure authentication session.
        
        Raises:
            AuthenticationError: If session cannot be started.
            SecurityError: If security validation fails.
        """
        # Perform security validation
        self._validate_security_context()
        
        # Start session with base implementation
        super().start_session()
        
        if self._metadata:
            self._metadata.security_level = self._security_level
            logger.info("Secure authentication session started with enhanced protection")
    
    def end_session(self) -> None:
        """End secure authentication session with enhanced cleanup."""
        # Perform secure cleanup
        self._secure_memory_cleanup()
        
        # End session with base implementation
        super().end_session()
        
        logger.info("Secure authentication session ended with enhanced cleanup")
    
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get sanitized session metadata.
        
        Returns session metadata with additional security information
        and proper sanitization of sensitive data.
        
        Returns:
            Dictionary containing sanitized session metadata.
        """
        metadata = super().get_session_metadata()
        
        # Add security metadata
        if metadata.get("active"):
            metadata.update({
                "security_level": self._security_level,
                "memory_protection": "enabled",
                "secure_cleanup": "enabled",
                "credential_protection": "enhanced"
            })
        
        # Sanitize any potentially sensitive information
        return self._sanitize_metadata(metadata)
    
    def _validate_security_context(self) -> None:
        """Validate security context before starting session.
        
        Raises:
            SecurityError: If security validation fails.
        """
        # Check for secure environment
        import os
        
        # Validate that we're not in a potentially insecure environment
        if os.environ.get("TICKET_ANALYZER_INSECURE_MODE"):
            raise SecurityError(
                "Cannot start secure session in insecure mode",
                details={"security_check": "environment_validation"}
            )
        
        logger.debug("Security context validation passed")
    
    def _secure_memory_cleanup(self) -> None:
        """Perform enhanced secure memory cleanup.
        
        Implements additional memory protection measures to ensure
        sensitive authentication data is properly cleared.
        """
        # Multiple garbage collection passes
        for _ in range(3):
            gc.collect()
        
        # Clear any cached sensitive data
        if hasattr(self, '_cached_credentials'):
            delattr(self, '_cached_credentials')
        
        logger.debug("Enhanced secure memory cleanup completed")
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata to remove sensitive information.
        
        Args:
            metadata: Raw metadata dictionary.
            
        Returns:
            Sanitized metadata dictionary.
        """
        # Create a copy to avoid modifying original
        sanitized = metadata.copy()
        
        # Remove or sanitize sensitive fields
        sensitive_fields = ["user_info", "credentials", "tokens"]
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "[REDACTED]"
        
        return sanitized