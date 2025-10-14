---
inclusion: fileMatch
fileMatchPattern: '*sanitiz*'
---

# Data Sanitization

## Ticket Data Sanitization in Logs and Outputs

### Sensitive Data Detection and Removal
```python
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

@dataclass
class SanitizationRule:
    """Rule for data sanitization."""
    pattern: str
    replacement: str = "[REDACTED]"
    field_names: Optional[List[str]] = None
    case_sensitive: bool = False

class TicketDataSanitizer:
    """Sanitizer for ticket data to remove sensitive information."""
    
    # Common sensitive patterns in ticket data
    SENSITIVE_PATTERNS = [
        # Email addresses
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            replacement='[EMAIL_REDACTED]'
        ),
        # Phone numbers (various formats)
        SanitizationRule(
            pattern=r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            replacement='[PHONE_REDACTED]'
        ),
        # Social Security Numbers
        SanitizationRule(
            pattern=r'\b\d{3}-?\d{2}-?\d{4}\b',
            replacement='[SSN_REDACTED]'
        ),
        # Credit card numbers
        SanitizationRule(
            pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            replacement='[CARD_REDACTED]'
        ),
        # IP addresses
        SanitizationRule(
            pattern=r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            replacement='[IP_REDACTED]'
        ),
        # AWS account IDs
        SanitizationRule(
            pattern=r'\b\d{12}\b',
            replacement='[ACCOUNT_REDACTED]'
        ),
        # API keys and tokens (base64-like strings)
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9+/]{20,}={0,2}\b',
            replacement='[TOKEN_REDACTED]'
        ),
    ]
    
    # Sensitive field names
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'auth', 'credential',
        'private_notes', 'internal_comments', 'confidential',
        'personal_info', 'contact_info', 'phone', 'email',
        'ssn', 'social_security', 'credit_card', 'payment_info'
    }
    
    def __init__(self, custom_rules: Optional[List[SanitizationRule]] = None) -> None:
        self._rules = self.SENSITIVE_PATTERNS.copy()
        if custom_rules:
            self._rules.extend(custom_rules)
    
    def sanitize_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ticket data dictionary."""
        sanitized = {}
        
        for key, value in ticket_data.items():
            if self._is_sensitive_field(key):
                sanitized[key] = "[FIELD_REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_ticket_data(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field name indicates sensitive data."""
        return field_name.lower() in self.SENSITIVE_FIELDS
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content using defined rules."""
        sanitized = text
        
        for rule in self._rules:
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            sanitized = re.sub(rule.pattern, rule.replacement, sanitized, flags=flags)
        
        return sanitized
    
    def _sanitize_list(self, data_list: List[Any]) -> List[Any]:
        """Sanitize list of data."""
        sanitized = []
        
        for item in data_list:
            if isinstance(item, str):
                sanitized.append(self._sanitize_text(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_ticket_data(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
```

### PII Detection and Removal Patterns
```python
import re
from typing import Pattern, Dict, List

class PIIDetector:
    """Detect and classify Personally Identifiable Information."""
    
    # Compiled regex patterns for better performance
    PII_PATTERNS: Dict[str, Pattern] = {
        'email': re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        'phone_us': re.compile(
            r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        ),
        'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        'mac_address': re.compile(
            r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'
        ),
        'aws_account': re.compile(r'\b\d{12}\b'),
        'uuid': re.compile(
            r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
            re.IGNORECASE
        ),
        'api_key': re.compile(r'\b[A-Za-z0-9+/]{32,}={0,2}\b'),
    }
    
    @classmethod
    def detect_pii_types(cls, text: str) -> List[str]:
        """Detect types of PII present in text."""
        detected_types = []
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            if pattern.search(text):
                detected_types.append(pii_type)
        
        return detected_types
    
    @classmethod
    def has_pii(cls, text: str) -> bool:
        """Check if text contains any PII."""
        return len(cls.detect_pii_types(text)) > 0
    
    @classmethod
    def remove_all_pii(cls, text: str) -> str:
        """Remove all detected PII from text."""
        sanitized = text
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            replacement = f'[{pii_type.upper()}_REDACTED]'
            sanitized = pattern.sub(replacement, sanitized)
        
        return sanitized

class AdvancedPIISanitizer(TicketDataSanitizer):
    """Enhanced sanitizer with PII detection capabilities."""
    
    def sanitize_with_pii_detection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data with PII detection and classification."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                if PIIDetector.has_pii(value):
                    pii_types = PIIDetector.detect_pii_types(value)
                    logger.warning(f"PII detected in field '{key}': {pii_types}")
                    sanitized[key] = PIIDetector.remove_all_pii(value)
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_with_pii_detection(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list_with_pii(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_list_with_pii(self, data_list: List[Any]) -> List[Any]:
        """Sanitize list with PII detection."""
        sanitized = []
        
        for item in data_list:
            if isinstance(item, str) and PIIDetector.has_pii(item):
                sanitized.append(PIIDetector.remove_all_pii(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_with_pii_detection(item))
            else:
                sanitized.append(item)
        
        return sanitized
```

### Secure Temporary File Handling
```python
import tempfile
import os
from pathlib import Path
from typing import Optional, Any, Dict
from contextlib import contextmanager

class SecureTempFileManager:
    """Secure temporary file management for sensitive data."""
    
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir
        self._temp_files: List[Path] = []
    
    @contextmanager
    def create_secure_temp_file(self, suffix: str = '.tmp', 
                               prefix: str = 'ticket_data_') -> Path:
        """Create secure temporary file with restricted permissions."""
        try:
            # Create temporary file with secure permissions
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=self._base_dir
            )
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(temp_path, 0o600)
            os.close(fd)  # Close file descriptor, keep path
            
            temp_file_path = Path(temp_path)
            self._temp_files.append(temp_file_path)
            
            yield temp_file_path
            
        finally:
            # Secure cleanup
            self._secure_delete_file(temp_file_path)
            if temp_file_path in self._temp_files:
                self._temp_files.remove(temp_file_path)
    
    def _secure_delete_file(self, file_path: Path) -> None:
        """Securely delete file by overwriting before removal."""
        if not file_path.exists():
            return
        
        try:
            # Get file size
            file_size = file_path.stat().st_size
            
            # Overwrite with random data
            with open(file_path, 'r+b') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Remove file
            file_path.unlink()
            
        except Exception as e:
            logger.error(f"Failed to securely delete {file_path}: {e}")
    
    def cleanup_all(self) -> None:
        """Clean up all managed temporary files."""
        for temp_file in self._temp_files.copy():
            self._secure_delete_file(temp_file)
        self._temp_files.clear()

# Usage example
class SecureTicketProcessor:
    """Process tickets with secure temporary file handling."""
    
    def __init__(self) -> None:
        self._temp_manager = SecureTempFileManager()
        self._sanitizer = AdvancedPIISanitizer()
    
    def process_sensitive_tickets(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process tickets with secure temporary storage."""
        with self._temp_manager.create_secure_temp_file(suffix='.json') as temp_file:
            # Sanitize data before writing to temp file
            sanitized_tickets = [
                self._sanitizer.sanitize_with_pii_detection(ticket)
                for ticket in tickets
            ]
            
            # Write sanitized data to secure temp file
            import json
            with open(temp_file, 'w') as f:
                json.dump(sanitized_tickets, f, indent=2)
            
            # Process data from temp file
            return self._analyze_from_temp_file(temp_file)
    
    def _analyze_from_temp_file(self, temp_file: Path) -> Dict[str, Any]:
        """Analyze data from temporary file."""
        # Implementation would read and process the sanitized data
        pass
```

### Error Message Sanitization
```python
import traceback
from typing import Optional

class SecureErrorHandler:
    """Handle errors with sanitized messages."""
    
    def __init__(self, sanitizer: TicketDataSanitizer) -> None:
        self._sanitizer = sanitizer
    
    def sanitize_exception_message(self, exception: Exception) -> str:
        """Sanitize exception message to prevent information leakage."""
        message = str(exception)
        return self._sanitizer._sanitize_text(message)
    
    def sanitize_traceback(self, tb: Optional[str] = None) -> str:
        """Sanitize traceback information."""
        if tb is None:
            tb = traceback.format_exc()
        
        # Remove file paths that might contain sensitive information
        sanitized_tb = re.sub(
            r'/[^\s]*/(ticket_analyzer|\.ticket-analyzer)/[^\s]*',
            '[PATH_REDACTED]',
            tb
        )
        
        # Sanitize any other sensitive data in traceback
        return self._sanitizer._sanitize_text(sanitized_tb)
    
    def log_sanitized_error(self, exception: Exception, 
                           context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with sanitized information."""
        sanitized_message = self.sanitize_exception_message(exception)
        sanitized_tb = self.sanitize_traceback()
        
        error_info = {
            'error_type': type(exception).__name__,
            'message': sanitized_message,
            'traceback': sanitized_tb
        }
        
        if context:
            sanitized_context = self._sanitizer.sanitize_ticket_data(context)
            error_info['context'] = sanitized_context
        
        logger.error(f"Sanitized error: {error_info}")

# Integration with CLI error handling
class SanitizedClickException(click.ClickException):
    """Click exception with sanitized messages."""
    
    def __init__(self, message: str, sanitizer: Optional[TicketDataSanitizer] = None) -> None:
        if sanitizer:
            sanitized_message = sanitizer._sanitize_text(message)
        else:
            # Use basic sanitization if no sanitizer provided
            sanitized_message = self._basic_sanitize(message)
        
        super().__init__(sanitized_message)
    
    def _basic_sanitize(self, message: str) -> str:
        """Basic sanitization for error messages."""
        # Remove common sensitive patterns
        patterns = [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
            (r'\b\d{3}-?\d{2}-?\d{4}\b', '[SSN]'),
            (r'/[^\s]*/\.ticket-analyzer/[^\s]*', '[CONFIG_PATH]'),
        ]
        
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
```

### Input Validation and SQL Injection Prevention
```python
import re
from typing import Any, List, Dict, Union

class InputValidator:
    """Validate and sanitize user inputs."""
    
    # Allowed characters for different input types
    ALLOWED_PATTERNS = {
        'ticket_id': re.compile(r'^[A-Z]{1,5}-?\d{1,10}$'),
        'username': re.compile(r'^[a-zA-Z0-9._-]{1,50}$'),
        'status': re.compile(r'^[a-zA-Z\s]{1,30}$'),
        'date': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'search_term': re.compile(r'^[a-zA-Z0-9\s._-]{1,100}$'),
    }
    
    # SQL injection patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(\\;))",  # Single quotes and semicolons
        r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or
        r"((\%27)|(\'))((\%75)|u|(\%55))((\%6E)|n|(\%4E))((\%69)|i|(\%49))((\%6F)|o|(\%4F))((\%6E)|n|(\%4E))",  # 'union
        r"(exec(\s|\+)+(s|x)p\w+)",  # exec sp_
        r"(union(\s|\+)+select)",  # union select
        r"(drop(\s|\+)+table)",  # drop table
        r"(insert(\s|\+)+into)",  # insert into
        r"(delete(\s|\+)+from)",  # delete from
    ]
    
    @classmethod
    def validate_input(cls, value: str, input_type: str) -> bool:
        """Validate input against allowed patterns."""
        if input_type not in cls.ALLOWED_PATTERNS:
            raise ValueError(f"Unknown input type: {input_type}")
        
        pattern = cls.ALLOWED_PATTERNS[input_type]
        return bool(pattern.match(value))
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        """Detect potential SQL injection attempts."""
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_search_input(cls, search_term: str) -> str:
        """Sanitize search input to prevent injection attacks."""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[^\w\s.-]', '', search_term)
        
        # Limit length
        sanitized = sanitized[:100]
        
        # Check for injection patterns
        if cls.detect_sql_injection(sanitized):
            raise ValueError("Invalid search term detected")
        
        return sanitized.strip()
    
    @classmethod
    def validate_ticket_filters(cls, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize ticket filter parameters."""
        validated = {}
        
        for key, value in filters.items():
            if key == 'ticket_ids' and isinstance(value, list):
                validated[key] = [
                    ticket_id for ticket_id in value
                    if cls.validate_input(ticket_id, 'ticket_id')
                ]
            elif key == 'status' and isinstance(value, list):
                validated[key] = [
                    status for status in value
                    if cls.validate_input(status, 'status')
                ]
            elif key == 'assignee' and isinstance(value, str):
                if cls.validate_input(value, 'username'):
                    validated[key] = value
            elif key in ['start_date', 'end_date'] and isinstance(value, str):
                if cls.validate_input(value, 'date'):
                    validated[key] = value
            elif key == 'search_term' and isinstance(value, str):
                validated[key] = cls.sanitize_search_input(value)
        
        return validated
```