---
inclusion: fileMatch
fileMatchPattern: '*{security,secure,auth,valid}*'
---

# Secure Coding Practices

## Input Validation Patterns

### Comprehensive Input Validation
```python
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

class ValidationResult(Enum):
    """Validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"

@dataclass
class ValidationError:
    """Validation error details."""
    field: str
    message: str
    severity: str = "error"

class SecureInputValidator:
    """Comprehensive input validation for security."""
    
    # Maximum lengths for different input types
    MAX_LENGTHS = {
        'ticket_id': 20,
        'username': 50,
        'search_term': 200,
        'description': 5000,
        'title': 255,
        'status': 50,
        'tag': 100,
    }
    
    # Allowed character patterns
    PATTERNS = {
        'ticket_id': re.compile(r'^[A-Z]{1,10}-?\d{1,15}$'),
        'username': re.compile(r'^[a-zA-Z0-9._-]+$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'date_iso': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'datetime_iso': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?$'),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9\s]+$'),
        'safe_text': re.compile(r'^[a-zA-Z0-9\s.,!?()-]+$'),
    }
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>',  # Iframes
        r'<object[^>]*>',  # Objects
        r'<embed[^>]*>',  # Embeds
        r'eval\s*\(',  # eval() calls
        r'exec\s*\(',  # exec() calls
        r'\$\{.*\}',  # Template injection
        r'\{\{.*\}\}',  # Template injection
    ]
    
    def validate_field(self, field_name: str, value: Any, 
                      field_type: str) -> tuple[ValidationResult, List[ValidationError]]:
        """Validate a single field with comprehensive checks."""
        errors = []
        
        # Type validation
        if not isinstance(value, str):
            if field_type in ['ticket_id', 'username', 'search_term']:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Field must be a string, got {type(value).__name__}"
                ))
                return ValidationResult.INVALID, errors
            value = str(value)
        
        # Length validation
        max_length = self.MAX_LENGTHS.get(field_type, 1000)
        if len(value) > max_length:
            errors.append(ValidationError(
                field=field_name,
                message=f"Field exceeds maximum length of {max_length} characters"
            ))
        
        # Empty value check
        if not value.strip():
            if field_type in ['ticket_id', 'username']:
                errors.append(ValidationError(
                    field=field_name,
                    message="Field cannot be empty"
                ))
                return ValidationResult.INVALID, errors
        
        # Pattern validation
        if field_type in self.PATTERNS:
            pattern = self.PATTERNS[field_type]
            if not pattern.match(value):
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Field does not match required format for {field_type}"
                ))
        
        # Security validation
        security_result = self._check_security_patterns(field_name, value)
        if security_result == ValidationResult.SUSPICIOUS:
            errors.append(ValidationError(
                field=field_name,
                message="Field contains potentially dangerous content",
                severity="warning"
            ))
            return ValidationResult.SUSPICIOUS, errors
        elif security_result == ValidationResult.INVALID:
            errors.append(ValidationError(
                field=field_name,
                message="Field contains prohibited content",
                severity="error"
            ))
            return ValidationResult.INVALID, errors
        
        return ValidationResult.VALID if not errors else ValidationResult.INVALID, errors
    
    def _check_security_patterns(self, field_name: str, value: str) -> ValidationResult:
        """Check for dangerous security patterns."""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return ValidationResult.INVALID
        
        # Check for potential injection attempts
        suspicious_chars = ['<', '>', '{', '}', '$', '`', '\\']
        if any(char in value for char in suspicious_chars):
            return ValidationResult.SUSPICIOUS
        
        return ValidationResult.VALID
```

### Secure File Operations and Permissions
```python
import os
import stat
from pathlib import Path
from typing import Optional, Union

class SecureFileOperations:
    """Secure file operations with proper permissions."""
    
    @staticmethod
    def create_secure_directory(path: Union[str, Path], 
                               mode: int = 0o700) -> Path:
        """Create directory with secure permissions."""
        dir_path = Path(path)
        
        # Create directory with restrictive permissions
        dir_path.mkdir(mode=mode, parents=True, exist_ok=True)
        
        # Ensure permissions are set correctly
        dir_path.chmod(mode)
        
        return dir_path
    
    @staticmethod
    def write_secure_file(file_path: Union[str, Path], 
                         content: str, 
                         mode: int = 0o600) -> None:
        """Write file with secure permissions."""
        path = Path(file_path)
        
        # Ensure parent directory exists with secure permissions
        SecureFileOperations.create_secure_directory(path.parent)
        
        # Write file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Set secure permissions
        path.chmod(mode)
    
    @staticmethod
    def read_secure_file(file_path: Union[str, Path]) -> str:
        """Read file with security checks."""
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Check file permissions
        file_stat = path.stat()
        if file_stat.st_mode & stat.S_IROTH:
            raise PermissionError(f"File {path} is world-readable")
        
        # Read file
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def validate_file_path(file_path: Union[str, Path], 
                          allowed_dirs: Optional[List[Path]] = None) -> bool:
        """Validate file path for security."""
        path = Path(file_path).resolve()
        
        # Check for path traversal attempts
        if '..' in str(path):
            return False
        
        # Check against allowed directories
        if allowed_dirs:
            return any(
                path.is_relative_to(allowed_dir.resolve())
                for allowed_dir in allowed_dirs
            )
        
        return True

class SecureConfigHandler:
    """Handle configuration files securely."""
    
    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or Path.home() / '.ticket-analyzer'
        self._file_ops = SecureFileOperations()
    
    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """Save configuration securely."""
        config_file = self._config_dir / f"{config_name}.json"
        
        # Validate config name
        if not re.match(r'^[a-zA-Z0-9_-]+$', config_name):
            raise ValueError("Invalid configuration name")
        
        # Sanitize config data
        sanitized_data = self._sanitize_config_data(config_data)
        
        # Write securely
        import json
        content = json.dumps(sanitized_data, indent=2)
        self._file_ops.write_secure_file(config_file, content)
    
    def _sanitize_config_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration data."""
        sanitized = {}
        
        for key, value in data.items():
            # Skip sensitive keys
            if key.lower() in {'password', 'token', 'secret', 'key'}:
                continue
            
            # Validate key name
            if not re.match(r'^[a-zA-Z0-9_]+$', key):
                continue
            
            sanitized[key] = value
        
        return sanitized
```

### Environment Variable Handling
```python
import os
from typing import Optional, Dict, Any, List

class SecureEnvironmentManager:
    """Secure environment variable management."""
    
    # Allowed environment variables
    ALLOWED_ENV_VARS = {
        'TICKET_ANALYZER_CONFIG_DIR',
        'TICKET_ANALYZER_LOG_LEVEL',
        'TICKET_ANALYZER_MAX_RESULTS',
        'TICKET_ANALYZER_TIMEOUT',
        'MIDWAY_CONFIG',
        'KRB5_CONFIG',
        'KRB5CCNAME',
    }
    
    # Sensitive environment variables that should never be logged
    SENSITIVE_ENV_VARS = {
        'PASSWORD', 'TOKEN', 'SECRET', 'KEY', 'AUTH',
        'CREDENTIAL', 'PRIVATE', 'CONFIDENTIAL'
    }
    
    @classmethod
    def get_secure_env_var(cls, var_name: str, 
                          default: Optional[str] = None) -> Optional[str]:
        """Get environment variable securely."""
        if var_name not in cls.ALLOWED_ENV_VARS:
            raise ValueError(f"Environment variable '{var_name}' not allowed")
        
        return os.getenv(var_name, default)
    
    @classmethod
    def set_secure_env_var(cls, var_name: str, value: str) -> None:
        """Set environment variable securely."""
        if var_name not in cls.ALLOWED_ENV_VARS:
            raise ValueError(f"Environment variable '{var_name}' not allowed")
        
        # Validate value
        if not isinstance(value, str):
            raise ValueError("Environment variable value must be string")
        
        if len(value) > 1000:
            raise ValueError("Environment variable value too long")
        
        os.environ[var_name] = value
    
    @classmethod
    def get_sanitized_env(cls) -> Dict[str, str]:
        """Get sanitized environment variables for logging."""
        sanitized = {}
        
        for key, value in os.environ.items():
            if any(sensitive in key.upper() for sensitive in cls.SENSITIVE_ENV_VARS):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        
        return sanitized
```

### Subprocess Execution Security
```python
import subprocess
import shlex
from typing import List, Dict, Optional, Union

class SecureSubprocessExecutor:
    """Execute subprocesses securely."""
    
    # Allowed commands
    ALLOWED_COMMANDS = {
        'mwinit', 'kinit', 'klist', 'git', 'python', 'pip'
    }
    
    @classmethod
    def execute_command(cls, command: List[str], 
                       timeout: int = 30,
                       allowed_commands: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """Execute command securely."""
        if not command or not isinstance(command, list):
            raise ValueError("Command must be a non-empty list")
        
        # Validate command
        allowed = allowed_commands or cls.ALLOWED_COMMANDS
        if command[0] not in allowed:
            raise ValueError(f"Command '{command[0]}' not allowed")
        
        # Validate arguments
        for arg in command[1:]:
            if not isinstance(arg, str):
                raise ValueError("All command arguments must be strings")
            
            # Check for injection attempts
            if any(char in arg for char in [';', '&', '|', '`', '$']):
                raise ValueError(f"Potentially dangerous argument: {arg}")
        
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=cls._get_secure_env(),
                check=False
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Command timed out: {' '.join(command)}")
        except Exception as e:
            raise RuntimeError(f"Command execution failed: {e}")
    
    @classmethod
    def _get_secure_env(cls) -> Dict[str, str]:
        """Get secure environment for subprocess."""
        # Start with minimal environment
        secure_env = {
            'PATH': os.environ.get('PATH', ''),
            'HOME': os.environ.get('HOME', ''),
            'USER': os.environ.get('USER', ''),
            'LANG': os.environ.get('LANG', 'C'),
        }
        
        # Add specific allowed variables
        allowed_vars = ['KRB5_CONFIG', 'KRB5CCNAME', 'MIDWAY_CONFIG']
        for var in allowed_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]
        
        return secure_env
```

### Memory Management for Sensitive Data
```python
import gc
import sys
from typing import Any, Optional

class SecureMemoryManager:
    """Manage sensitive data in memory securely."""
    
    @staticmethod
    def clear_sensitive_variable(var_name: str, frame_locals: Dict[str, Any]) -> None:
        """Clear sensitive variable from memory."""
        if var_name in frame_locals:
            # Overwrite with random data if string
            if isinstance(frame_locals[var_name], str):
                frame_locals[var_name] = 'X' * len(frame_locals[var_name])
            
            # Delete reference
            del frame_locals[var_name]
    
    @staticmethod
    def secure_string_compare(str1: str, str2: str) -> bool:
        """Compare strings in constant time to prevent timing attacks."""
        if len(str1) != len(str2):
            return False
        
        result = 0
        for c1, c2 in zip(str1, str2):
            result |= ord(c1) ^ ord(c2)
        
        return result == 0
    
    @staticmethod
    def force_garbage_collection() -> None:
        """Force garbage collection to clear sensitive data."""
        gc.collect()
        gc.collect()  # Call twice to ensure cleanup

class SensitiveDataContext:
    """Context manager for handling sensitive data."""
    
    def __init__(self, data: Any) -> None:
        self._data = data
        self._cleared = False
    
    def __enter__(self) -> Any:
        return self._data
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.clear()
    
    def clear(self) -> None:
        """Clear sensitive data from memory."""
        if not self._cleared:
            if isinstance(self._data, str):
                # Overwrite string data
                self._data = 'X' * len(self._data)
            elif isinstance(self._data, (list, dict)):
                # Clear collections
                if hasattr(self._data, 'clear'):
                    self._data.clear()
            
            self._data = None
            self._cleared = True
            SecureMemoryManager.force_garbage_collection()

# Usage example
def process_sensitive_data(password: str) -> bool:
    """Example of secure sensitive data processing."""
    with SensitiveDataContext(password) as secure_password:
        # Process password securely
        result = authenticate_user(secure_password)
        
        # Password is automatically cleared when exiting context
        return result
```