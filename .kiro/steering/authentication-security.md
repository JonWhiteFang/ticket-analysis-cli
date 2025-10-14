---
inclusion: fileMatch
fileMatchPattern: '*auth*'
---

# Authentication Security

## Midway Authentication Best Practices

### Core Authentication Pattern
```python
from __future__ import annotations
import subprocess
import time
from typing import Optional
from dataclasses import dataclass

@dataclass
class AuthConfig:
    timeout_seconds: int = 60
    max_retry_attempts: int = 3
    check_interval_seconds: int = 300

class SecureMidwayAuth:
    def __init__(self, config: AuthConfig) -> None:
        self._config = config
        self._last_check: Optional[float] = None
        self._authenticated = False
    
    def ensure_authenticated(self) -> None:
        if not self._is_current():
            self._authenticate()
    
    def _is_current(self) -> bool:
        if (self._last_check and 
            time.time() - self._last_check < self._config.check_interval_seconds):
            return self._authenticated
        
        self._authenticated = self._check_status()
        self._last_check = time.time()
        return self._authenticated
    
    def _check_status(self) -> bool:
        try:
            result = subprocess.run(
                ["mwinit", "-s"],
                capture_output=True,
                timeout=self._config.timeout_seconds,
                env=self._get_secure_env()
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _get_secure_env(self) -> Dict[str, str]:
        """Get secure environment for subprocess."""
        import os
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "KRB5_CONFIG": os.environ.get("KRB5_CONFIG", ""),
            "KRB5CCNAME": os.environ.get("KRB5CCNAME", ""),
        }

### Secure Logging and Data Sanitization
```python
import re
from typing import Dict, Any

class SecureLogger:
    SENSITIVE_PATTERNS = [
        r'password["\s]*[:=]["\s]*[^\s"]+',
        r'token["\s]*[:=]["\s]*[^\s"]+',
        r'secret["\s]*[:=]["\s]*[^\s"]+',
    ]
    
    @classmethod
    def sanitize_message(cls, message: str) -> str:
        sanitized = message
        for pattern in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        return sanitized

### Session Management
```python
from datetime import datetime, timedelta

class AuthSession:
    def __init__(self, duration: timedelta = timedelta(hours=8)) -> None:
        self._duration = duration
        self._start: Optional[datetime] = None
        self._authenticated = False
    
    def start(self) -> None:
        self._start = datetime.now()
        self._authenticated = True
    
    def is_valid(self) -> bool:
        if not self._authenticated or not self._start:
            return False
        return datetime.now() - self._start < self._duration
```