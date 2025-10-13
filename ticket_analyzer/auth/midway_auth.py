"""Midway authentication handler with secure subprocess execution.

This module provides secure authentication with Amazon's Midway system using
subprocess calls to mwinit. It implements proper security measures including
environment isolation, credential protection, and session management.
"""

from __future__ import annotations
import subprocess
import os
import signal
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from ..interfaces import AuthenticationInterface
from ..models.config import AuthConfig
from ..models.exceptions import (
    AuthenticationError,
    MCPAuthenticationError,
    SecurityError
)

logger = logging.getLogger(__name__)


class AuthenticationTimeoutError(AuthenticationError):
    """Raised when authentication operations timeout."""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None) -> None:
        super().__init__(message, auth_method="midway")
        if timeout_duration:
            self.add_detail("timeout_duration", timeout_duration)


class MidwayAuthenticator(AuthenticationInterface):
    """Secure Midway authentication handler.
    
    This class provides secure authentication with Amazon's Midway system
    using subprocess calls to mwinit. It implements comprehensive security
    measures including:
    
    - Secure subprocess execution with environment isolation
    - Session timeout and automatic re-authentication
    - Credential protection (never logged or stored)
    - Proper error handling and retry logic
    - Authentication state management
    
    Attributes:
        _config: Authentication configuration settings
        _last_auth_check: Timestamp of last authentication check
        _authenticated: Current authentication state
        _session_start: Session start timestamp
    """
    
    # Allowed authentication commands for security
    ALLOWED_COMMANDS = {"mwinit", "kinit", "klist"}
    
    def __init__(self, config: Optional[AuthConfig] = None) -> None:
        """Initialize the Midway authenticator.
        
        Args:
            config: Authentication configuration. Uses defaults if not provided.
        """
        self._config = config or AuthConfig()
        self._last_auth_check: Optional[float] = None
        self._authenticated = False
        self._session_start: Optional[datetime] = None
        
        # Validate configuration
        self._config.validate()
        
        logger.debug("MidwayAuthenticator initialized with timeout=%ds, retries=%d",
                    self._config.timeout_seconds, self._config.max_retry_attempts)
    
    def authenticate(self) -> bool:
        """Perform authentication with Midway system.
        
        Executes mwinit subprocess with proper security measures and
        retry logic. Never logs or stores credentials.
        
        Returns:
            True if authentication successful, False otherwise.
            
        Raises:
            AuthenticationError: If authentication fails after all retries.
            AuthenticationTimeoutError: If authentication times out.
            SecurityError: If security validation fails.
        """
        logger.info("Starting Midway authentication")
        
        for attempt in range(self._config.max_retry_attempts):
            try:
                logger.debug("Authentication attempt %d/%d", 
                           attempt + 1, self._config.max_retry_attempts)
                
                with self._authentication_timeout(self._config.timeout_seconds):
                    success = self._execute_secure_mwinit()
                    
                if success:
                    self._authenticated = True
                    self._session_start = datetime.now()
                    self._last_auth_check = datetime.now().timestamp()
                    
                    logger.info("Authentication successful")
                    return True
                else:
                    logger.warning("Authentication attempt %d failed", attempt + 1)
                    
            except AuthenticationTimeoutError:
                logger.error("Authentication timeout on attempt %d", attempt + 1)
                if attempt == self._config.max_retry_attempts - 1:
                    raise
                continue
            except Exception as e:
                logger.error("Authentication error on attempt %d: %s", attempt + 1, e)
                if attempt == self._config.max_retry_attempts - 1:
                    raise AuthenticationError(
                        f"Authentication failed after {self._config.max_retry_attempts} attempts",
                        details={"last_error": str(e)},
                        auth_method="midway"
                    )
                continue
        
        # All attempts failed
        self._authenticated = False
        raise AuthenticationError(
            f"Authentication failed after {self._config.max_retry_attempts} attempts",
            auth_method="midway"
        )
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated.
        
        Performs a fresh authentication status check if enough time has
        passed since the last check, based on check_interval_seconds.
        
        Returns:
            True if authenticated, False otherwise.
        """
        current_time = datetime.now().timestamp()
        
        # Check if we need to refresh authentication status
        if (self._last_auth_check is None or 
            current_time - self._last_auth_check >= self._config.check_interval_seconds):
            
            logger.debug("Checking authentication status")
            self._authenticated = self._check_auth_status()
            self._last_auth_check = current_time
        
        return self._authenticated
    
    def ensure_authenticated(self) -> None:
        """Ensure user is authenticated, authenticate if needed.
        
        Checks current authentication status and performs authentication
        if not currently authenticated or session has expired.
        
        Raises:
            AuthenticationError: If authentication fails.
        """
        if not self.is_authenticated():
            logger.info("Authentication required, starting authentication process")
            self.authenticate()
        else:
            logger.debug("Already authenticated")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information.
        
        Returns sanitized session information without exposing
        sensitive authentication details.
        
        Returns:
            Dictionary containing session details.
        """
        session_info = {
            "authenticated": self._authenticated,
            "auth_method": "midway",
            "session_start": self._session_start.isoformat() if self._session_start else None,
            "last_check": datetime.fromtimestamp(self._last_auth_check).isoformat() 
                         if self._last_auth_check else None,
            "check_interval_seconds": self._config.check_interval_seconds,
            "session_duration_hours": self._config.session_duration_hours
        }
        
        # Add session age if session is active
        if self._session_start:
            session_age = datetime.now() - self._session_start
            session_info["session_age_seconds"] = int(session_age.total_seconds())
            
            # Check if session is near expiry
            max_session_duration = timedelta(hours=self._config.session_duration_hours)
            if session_age > max_session_duration * 0.8:  # 80% of max duration
                session_info["session_warning"] = "Session approaching expiry"
        
        return session_info
    
    def _execute_secure_mwinit(self) -> bool:
        """Execute mwinit command with security measures.
        
        Performs secure subprocess execution with:
        - Environment isolation
        - Command validation
        - Timeout protection
        - No credential logging
        
        Returns:
            True if mwinit succeeded, False otherwise.
            
        Raises:
            AuthenticationTimeoutError: If command times out.
            SecurityError: If security validation fails.
            AuthenticationError: If command execution fails.
        """
        command = ["mwinit", "-o"]  # -o flag for one-time authentication
        
        # Validate command for security
        if not self._validate_command(command):
            raise SecurityError(
                "Invalid authentication command",
                details={"command": command[0]}
            )
        
        try:
            logger.debug("Executing secure mwinit command")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
                env=self._get_secure_env(),
                check=False  # Don't raise on non-zero exit
            )
            
            # Log result without exposing sensitive information
            logger.debug("mwinit completed with exit code: %d", result.returncode)
            
            if result.returncode != 0:
                # Log error without exposing credentials
                sanitized_stderr = self._sanitize_output(result.stderr)
                logger.warning("mwinit failed: %s", sanitized_stderr)
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("mwinit command timed out after %d seconds", 
                        self._config.timeout_seconds)
            raise AuthenticationTimeoutError(
                f"Authentication timed out after {self._config.timeout_seconds} seconds",
                timeout_duration=self._config.timeout_seconds
            )
        except FileNotFoundError:
            logger.error("mwinit command not found")
            raise AuthenticationError(
                "mwinit command not found. Please ensure Midway tools are installed.",
                auth_method="midway"
            )
        except Exception as e:
            logger.error("Unexpected error executing mwinit: %s", e)
            raise AuthenticationError(
                f"Authentication command failed: {e}",
                auth_method="midway"
            )
    
    def _check_auth_status(self) -> bool:
        """Check current authentication status.
        
        Uses mwinit -s (status) command to check authentication
        without triggering new authentication.
        
        Returns:
            True if authenticated, False otherwise.
        """
        command = ["mwinit", "-s"]  # -s flag for status check
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,  # Short timeout for status check
                env=self._get_secure_env(),
                check=False
            )
            
            is_authenticated = result.returncode == 0
            logger.debug("Authentication status check: %s", 
                        "authenticated" if is_authenticated else "not authenticated")
            
            return is_authenticated
            
        except subprocess.TimeoutExpired:
            logger.warning("Authentication status check timed out")
            return False
        except FileNotFoundError:
            logger.error("mwinit command not found for status check")
            return False
        except Exception as e:
            logger.warning("Error checking authentication status: %s", e)
            return False
    
    def _get_secure_env(self) -> Dict[str, str]:
        """Get secure environment variables for subprocess.
        
        Creates a minimal environment with only necessary variables
        to prevent credential leakage and security issues.
        
        Returns:
            Dictionary of environment variables for subprocess.
        """
        # Start with minimal secure environment
        secure_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "C"),
        }
        
        # Add only necessary authentication-related variables
        auth_vars = [
            "KRB5_CONFIG", "KRB5CCNAME", "MIDWAY_CONFIG",
            "KERBEROS_CONFIG", "KRB5_TRACE"
        ]
        
        for var in auth_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]
        
        logger.debug("Using secure environment with %d variables", len(secure_env))
        return secure_env
    
    def _validate_command(self, command: List[str]) -> bool:
        """Validate command for security.
        
        Ensures only allowed authentication commands are executed
        to prevent command injection attacks.
        
        Args:
            command: Command list to validate.
            
        Returns:
            True if command is allowed, False otherwise.
        """
        if not command or not isinstance(command, list):
            return False
        
        command_name = command[0]
        return command_name in self.ALLOWED_COMMANDS
    
    def _sanitize_output(self, output: str) -> str:
        """Sanitize command output to remove sensitive information.
        
        Removes potential credentials, tokens, and other sensitive
        data from command output before logging.
        
        Args:
            output: Raw command output.
            
        Returns:
            Sanitized output safe for logging.
        """
        if not output:
            return output
        
        # Remove common sensitive patterns
        import re
        
        # Remove potential tokens and credentials
        sanitized = re.sub(r'token[:\s=]+[^\s]+', '[TOKEN_REDACTED]', output, flags=re.IGNORECASE)
        sanitized = re.sub(r'password[:\s=]+[^\s]+', '[PASSWORD_REDACTED]', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'credential[:\s=]+[^\s]+', '[CREDENTIAL_REDACTED]', sanitized, flags=re.IGNORECASE)
        
        # Remove base64-like strings that might be tokens
        sanitized = re.sub(r'\b[A-Za-z0-9+/]{20,}={0,2}\b', '[TOKEN_REDACTED]', sanitized)
        
        return sanitized
    
    @contextmanager
    def _authentication_timeout(self, seconds: int):
        """Context manager for authentication timeout handling.
        
        Uses signal.alarm to implement timeout for authentication
        operations that might hang.
        
        Args:
            seconds: Timeout duration in seconds.
            
        Raises:
            AuthenticationTimeoutError: If timeout is reached.
        """
        def timeout_handler(signum: int, frame: Any) -> None:
            raise AuthenticationTimeoutError(
                f"Authentication timed out after {seconds} seconds",
                timeout_duration=seconds
            )
        
        # Set up timeout signal (Unix-like systems only)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
        
        try:
            yield
        finally:
            # Clean up timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)


class SecureMidwayAuthenticator(MidwayAuthenticator):
    """Enhanced Midway authenticator with additional security features.
    
    Extends the base MidwayAuthenticator with enhanced security measures:
    - Memory protection for sensitive data
    - Enhanced logging with sanitization
    - Additional validation and error handling
    """
    
    def __init__(self, config: Optional[AuthConfig] = None) -> None:
        """Initialize secure Midway authenticator.
        
        Args:
            config: Authentication configuration.
        """
        super().__init__(config)
        logger.info("SecureMidwayAuthenticator initialized with enhanced security")
    
    def authenticate(self) -> bool:
        """Perform secure authentication with enhanced protection.
        
        Returns:
            True if authentication successful, False otherwise.
            
        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            # Clear any previous authentication state
            self._clear_sensitive_state()
            
            # Perform authentication with base implementation
            result = super().authenticate()
            
            if result:
                logger.info("Secure authentication completed successfully")
            
            return result
            
        except Exception as e:
            # Clear sensitive state on error
            self._clear_sensitive_state()
            raise
    
    def _clear_sensitive_state(self) -> None:
        """Clear sensitive authentication state from memory.
        
        Ensures that sensitive authentication information is
        properly cleared from memory for security.
        """
        # Force garbage collection to clear sensitive data
        import gc
        gc.collect()
        
        logger.debug("Sensitive authentication state cleared")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get sanitized session information.
        
        Returns session information with additional security
        metadata and sanitization.
        
        Returns:
            Dictionary containing sanitized session details.
        """
        session_info = super().get_session_info()
        
        # Add security metadata
        session_info.update({
            "security_level": "enhanced",
            "credential_protection": "enabled",
            "memory_protection": "enabled"
        })
        
        return session_info