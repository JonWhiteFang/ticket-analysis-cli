---
inclusion: fileMatch
fileMatchPattern: '*sanitiz*'
---

# Data Sanitization

## Core Sanitization Patterns

### Basic Sanitizer
```python
import re
from typing import Dict, Any, List

class DataSanitizer:
    # Common PII patterns
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
        'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
        'ip': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        'aws_account': r'\b\d{12}\b',
        'token': r'\b[A-Za-z0-9+/]{20,}={0,2}\b',
    }
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'auth', 'credential',
        'private_notes', 'phone', 'email', 'ssn'
    }
    
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_FIELDS:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_item(item) for item in value]
            else:
                sanitized[key] = value
        return sanitized
    
    def _sanitize_text(self, text: str) -> str:
        for name, pattern in self.PATTERNS.items():
            text = re.sub(pattern, f'[{name.upper()}_REDACTED]', text, flags=re.IGNORECASE)
        return text
    
    def _sanitize_item(self, item: Any) -> Any:
        if isinstance(item, str):
            return self._sanitize_text(item)
        elif isinstance(item, dict):
            return self.sanitize_data(item)
        return item

### Secure File Operations
```python
import tempfile
import os
from pathlib import Path
from contextlib import contextmanager

class SecureTempFileManager:
    @contextmanager
    def create_secure_temp_file(self, suffix: str = '.tmp'):
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.chmod(temp_path, 0o600)
        os.close(fd)
        
        temp_file_path = Path(temp_path)
        try:
            yield temp_file_path
        finally:
            self._secure_delete(temp_file_path)
    
    def _secure_delete(self, file_path: Path):
        if file_path.exists():
            # Overwrite with random data before deletion
            file_size = file_path.stat().st_size
            with open(file_path, 'r+b') as f:
                f.write(os.urandom(file_size))
                f.flush()
            file_path.unlink()

### Input Validation
```python
import re

class InputValidator:
    PATTERNS = {
        'ticket_id': r'^[A-Z]{1,5}-?\d{1,10}$',
        'username': r'^[a-zA-Z0-9._-]{1,50}$',
        'search_term': r'^[a-zA-Z0-9\s._-]{1,100}$',
    }
    
    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(\\;))",
        r"(union(\s|\+)+select)",
        r"(drop(\s|\+)+table)",
    ]
    
    @classmethod
    def validate_input(cls, value: str, input_type: str) -> bool:
        pattern = cls.PATTERNS.get(input_type)
        return bool(re.match(pattern, value)) if pattern else False
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        return any(re.search(pattern, value, re.IGNORECASE) 
                  for pattern in cls.SQL_INJECTION_PATTERNS)