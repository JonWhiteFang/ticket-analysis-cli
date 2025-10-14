---
inclusion: fileMatch
fileMatchPattern: '*auth*'
---

# Authentication Security

## Midway Authentication Best Practices

### Secure Authentication Flow
```python
from __future__ import annotations
import subprocess
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AuthenticationConfig:
    """Configuration for authentication settings."""
    timeout_seconds: int = 60
    max_retry_attempts: int = 3
    check_interval_seconds: int = 300  # 5 minutes
    
class SecureMidwayAuthenticator:
    """Secure Midway authentication handler."""
    
    def __init__(self, config: AuthenticationConfig) -> None:
        self._config = config
        self._last_auth_check: Optional[float] = None
        self._authenticated = False
    
    def ensure_authenticated(self) -> None:
        """Ensure user is authenticated with proper security checks."""
        if not self._is_authentication_current():
            self._perform_secure_authentication()
    
    def _is_authentication_current(self) -> bool:
        """Check if current authentication is still valid."""
        import time
        
        current_time = time.time()
        if (self._last_auth_check and 
            current_time - self._last_auth_check < self._config.check_interval_seconds):
            return self._authenticated
        
        # Perform fresh authentication check
        self._authenticated = self._check_auth_status()
        self._last_auth_check = current_time
        return self._authenticated
    
    def _check_auth_status(self) -> bool:
        """Securely check authentication status."""
        try:
            # Use -s flag for silent check to avoid credential exposure
            result = subprocess.run(
                ["mwinit", "-s"],
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
                env=self._get_secure_env()
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning("Authentication status check timed out")
            return False
        except FileNotFoundError:
            logger.error("mwinit command not found")
            raise AuthenticationError("mwinit not available")
        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False
```

### Subprocess Security for mwinit Calls
```python
import subprocess
import shlex
from typing import List, Dict, str, Optional

class SecureSubprocessManager:
    """Secure subprocess execution for authentication commands."""
    
    @staticmethod
    def _get_secure_env() -> Dict[str, str]:
        """Get secure environment variables for subprocess."""
        # Start with minimal environment
        secure_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "C"),
        }
        
        # Add only necessary authentication-related variables
        auth_vars = ["KRB5_CONFIG", "KRB5CCNAME", "MIDWAY_CONFIG"]
        for var in auth_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]
        
        return secure_env
    
    @staticmethod
    def execute_auth_command(command: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
        """Execute authentication command securely."""
        # Validate command to prevent injection
        if not command or not isinstance(command, list):
            raise ValueError("Command must be a non-empty list")
        
        # Whitelist allowed authentication commands
        allowed_commands = {"mwinit", "kinit", "klist"}
        if command[0] not in allowed_commands:
            raise ValueError(f"Command '{command[0]}' not allowed")
        
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=SecureSubprocessManager._get_secure_env(),
                check=False  # Don't raise on non-zero exit
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {' '.join(command)}")
            raise AuthenticationError(f"Authentication command timed out: {e}")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise AuthenticationError(f"Authentication command failed: {e}")

class SecureAuthenticator(SecureMidwayAuthenticator):
    """Enhanced authenticator with secure subprocess handling."""
    
    def _perform_secure_authentication(self) -> None:
        """Perform authentication with security measures."""
        for attempt in range(self._config.max_retry_attempts):
            try:
                # Use -o flag for one-time authentication
                result = SecureSubprocessManager.execute_auth_command(
                    ["mwinit", "-o"],
                    timeout=self._config.timeout_seconds
                )
                
                if result.returncode == 0:
                    self._authenticated = True
                    logger.info("Authentication successful")
                    return
                else:
                    # Log error without exposing sensitive information
                    logger.warning(f"Authentication attempt {attempt + 1} failed")
                    if attempt == self._config.max_retry_attempts - 1:
                        raise AuthenticationError("Authentication failed after all attempts")
                        
            except AuthenticationError:
                if attempt == self._config.max_retry_attempts - 1:
                    raise
                continue
```

### Credential Isolation and Logging Security
```python
import re
from typing import Any, Dict, List

class SecureLogger:
    """Logger with credential sanitization."""
    
    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = [
        r'password["\s]*[:=]["\s]*[^\s"]+',
        r'token["\s]*[:=]["\s]*[^\s"]+',
        r'secret["\s]*[:=]["\s]*[^\s"]+',
        r'key["\s]*[:=]["\s]*[^\s"]+',
        r'auth["\s]*[:=]["\s]*[^\s"]+',
        r'credential["\s]*[:=]["\s]*[^\s"]+',
        r'ticket["\s]*[:=]["\s]*[A-Za-z0-9+/=]{20,}',  # Base64-like tokens
    ]
    
    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """Remove sensitive information from log messages."""
        sanitized = message
        for pattern in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data for logging."""
        sensitive_keys = {
            'password', 'token', 'secret', 'key', 'auth', 'credential',
            'ticket', 'session', 'cookie', 'authorization'
        }
        
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_message(value)
            else:
                sanitized[key] = value
        
        return sanitized

# Usage in authentication classes
class LoggingSecureAuthenticator(SecureAuthenticator):
    """Authenticator with secure logging."""
    
    def _log_auth_attempt(self, success: bool, details: Dict[str, Any]) -> None:
        """Log authentication attempt with sanitization."""
        sanitized_details = SecureLogger.sanitize_dict(details)
        
        if success:
            logger.info(f"Authentication successful: {sanitized_details}")
        else:
            logger.warning(f"Authentication failed: {sanitized_details}")
```

### Session Management and Re-authentication
```python
import time
from datetime import datetime, timedelta
from typing import Optional

class AuthenticationSession:
    """Manage authentication session lifecycle."""
    
    def __init__(self, session_duration: timedelta = timedelta(hours=8)) -> None:
        self._session_duration = session_duration
        self._session_start: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None
        self._authenticated = False
    
    def start_session(self) -> None:
        """Start new authentication session."""
        now = datetime.now()
        self._session_start = now
        self._last_activity = now
        self._authenticated = True
        logger.info("Authentication session started")
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = datetime.now()
    
    def is_session_valid(self) -> bool:
        """Check if current session is still valid."""
        if not self._authenticated or not self._session_start:
            return False
        
        now = datetime.now()
        session_age = now - self._session_start
        
        # Check session timeout
        if session_age > self._session_duration:
            logger.info("Authentication session expired")
            self._invalidate_session()
            return False
        
        return True
    
    def _invalidate_session(self) -> None:
        """Invalidate current session."""
        self._session_start = None
        self._last_activity = None
        self._authenticated = False

class SessionManagedAuthenticator(SecureAuthenticator):
    """Authenticator with session management."""
    
    def __init__(self, config: AuthenticationConfig) -> None:
        super().__init__(config)
        self._session = AuthenticationSession()
    
    def ensure_authenticated(self) -> None:
        """Ensure authentication with session management."""
        if not self._session.is_session_valid():
            self._perform_secure_authentication()
            self._session.start_session()
        else:
            self._session.update_activity()
```

### Authentication Timeout Handling
```python
import signal
from contextlib import contextmanager
from typing import Generator

class AuthenticationTimeoutError(AuthenticationError):
    """Raised when authentication times out."""
    pass

@contextmanager
def authentication_timeout(seconds: int) -> Generator[None, None, None]:
    """Context manager for authentication timeout handling."""
    def timeout_handler(signum: int, frame: Any) -> None:
        raise AuthenticationTimeoutError(f"Authentication timed out after {seconds} seconds")
    
    # Set up timeout signal
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Clean up timeout
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class TimeoutAwareAuthenticator(SessionManagedAuthenticator):
    """Authenticator with timeout protection."""
    
    def _perform_secure_authentication(self) -> None:
        """Perform authentication with timeout protection."""
        try:
            with authentication_timeout(self._config.timeout_seconds):
                super()._perform_secure_authentication()
        except AuthenticationTimeoutError as e:
            logger.error(f"Authentication timeout: {e}")
            raise AuthenticationError("Authentication process timed out")
```

### Secure Configuration Management
```python
from pathlib import Path
import json
from typing import Dict, Any

class SecureConfigManager:
    """Secure configuration management for authentication."""
    
    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or Path.home() / ".ticket-analyzer"
        self._config_file = self._config_dir / "auth_config.json"
        self._ensure_secure_permissions()
    
    def _ensure_secure_permissions(self) -> None:
        """Ensure configuration directory has secure permissions."""
        self._config_dir.mkdir(mode=0o700, exist_ok=True)
        
        if self._config_file.exists():
            # Set restrictive permissions on config file
            self._config_file.chmod(0o600)
    
    def load_config(self) -> AuthenticationConfig:
        """Load authentication configuration securely."""
        if not self._config_file.exists():
            return AuthenticationConfig()  # Use defaults
        
        try:
            with open(self._config_file, 'r') as f:
                data = json.load(f)
            
            return AuthenticationConfig(
                timeout_seconds=data.get('timeout_seconds', 60),
                max_retry_attempts=data.get('max_retry_attempts', 3),
                check_interval_seconds=data.get('check_interval_seconds', 300)
            )
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load auth config: {e}")
            return AuthenticationConfig()
    
    def save_config(self, config: AuthenticationConfig) -> None:
        """Save authentication configuration securely."""
        config_data = {
            'timeout_seconds': config.timeout_seconds,
            'max_retry_attempts': config.max_retry_attempts,
            'check_interval_seconds': config.check_interval_seconds
        }
        
        try:
            with open(self._config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Ensure secure permissions
            self._config_file.chmod(0o600)
        except IOError as e:
            logger.error(f"Failed to save auth config: {e}")
            raise AuthenticationError("Failed to save authentication configuration")
```