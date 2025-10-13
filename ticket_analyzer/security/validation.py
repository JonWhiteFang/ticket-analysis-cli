"""Comprehensive input validation for ticket analyzer.

This module provides input validation and sanitization including:
- User input validation for all CLI parameters
- API response validation and sanitization
- SQL injection prevention
- XSS protection measures
- Command injection prevention
"""

from __future__ import annotations
import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union, Pattern, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, date

from .sanitizer import TicketDataSanitizer
from .logging import SecureLogger

logger = SecureLogger(__name__)


class ValidationResult(Enum):
    """Validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"


class InputType(Enum):
    """Types of input for validation."""
    TICKET_ID = "ticket_id"
    USERNAME = "username"
    EMAIL = "email"
    SEARCH_TERM = "search_term"
    STATUS = "status"
    DATE = "date"
    DATETIME = "datetime"
    URL = "url"
    FILE_PATH = "file_path"
    ALPHANUMERIC = "alphanumeric"
    SAFE_TEXT = "safe_text"
    JSON_DATA = "json_data"
    SQL_QUERY = "sql_query"
    COMMAND = "command"


@dataclass
class ValidationError:
    """Validation error details."""
    field: str
    message: str
    severity: str = "error"
    input_type: Optional[InputType] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationRule:
    """Validation rule configuration."""
    pattern: Pattern[str]
    max_length: int
    min_length: int = 0
    required: bool = True
    description: str = ""
    
    def __post_init__(self) -> None:
        """Validate rule configuration."""
        if self.max_length < self.min_length:
            raise ValueError("max_length must be >= min_length")


class InputValidator:
    """Comprehensive input validation for security."""
    
    # Maximum lengths for different input types
    MAX_LENGTHS = {
        InputType.TICKET_ID: 50,
        InputType.USERNAME: 100,
        InputType.EMAIL: 254,  # RFC 5321 limit
        InputType.SEARCH_TERM: 500,
        InputType.STATUS: 50,
        InputType.DATE: 10,
        InputType.DATETIME: 30,
        InputType.URL: 2048,
        InputType.FILE_PATH: 4096,
        InputType.ALPHANUMERIC: 255,
        InputType.SAFE_TEXT: 1000,
        InputType.JSON_DATA: 1024 * 1024,  # 1MB
        InputType.SQL_QUERY: 10000,
        InputType.COMMAND: 1000,
    }
    
    # Validation patterns for different input types
    VALIDATION_PATTERNS = {
        InputType.TICKET_ID: re.compile(r'^[A-Z]{1,10}-?\d{1,15}$'),
        InputType.USERNAME: re.compile(r'^[a-zA-Z0-9._-]+$'),
        InputType.EMAIL: re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        InputType.STATUS: re.compile(r'^[a-zA-Z\s]{1,50}$'),
        InputType.DATE: re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        InputType.DATETIME: re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?$'),
        InputType.URL: re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE),
        InputType.FILE_PATH: re.compile(r'^[a-zA-Z0-9._/\-\\:]+$'),
        InputType.ALPHANUMERIC: re.compile(r'^[a-zA-Z0-9\s]+$'),
        InputType.SAFE_TEXT: re.compile(r'^[a-zA-Z0-9\s.,!?()_-]+$'),
        InputType.SEARCH_TERM: re.compile(r'^[a-zA-Z0-9\s.,!?()_\-"\']+$'),
    }
    
    # Dangerous patterns to detect and block
    DANGEROUS_PATTERNS = [
        # Script injection patterns
        (r'<script[^>]*>.*?</script>', "Script tag injection"),
        (r'javascript:', "JavaScript URL injection"),
        (r'on\w+\s*=', "Event handler injection"),
        (r'<iframe[^>]*>', "Iframe injection"),
        (r'<object[^>]*>', "Object tag injection"),
        (r'<embed[^>]*>', "Embed tag injection"),
        
        # Code execution patterns
        (r'eval\s*\(', "eval() function call"),
        (r'exec\s*\(', "exec() function call"),
        (r'system\s*\(', "system() function call"),
        (r'shell_exec\s*\(', "shell_exec() function call"),
        
        # Template injection patterns
        (r'\$\{.*\}', "Template injection (${})"),
        (r'\{\{.*\}\}', "Template injection ({{}})"),
        (r'<%.*%>', "Template injection (<%%>)"),
        
        # SQL injection patterns
        (r"('|(\\')|(;)|(\\;))", "SQL injection characters"),
        (r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", "SQL 'or injection"),
        (r"union(\s|\+)+select", "SQL UNION SELECT"),
        (r"drop(\s|\+)+table", "SQL DROP TABLE"),
        (r"insert(\s|\+)+into", "SQL INSERT INTO"),
        (r"delete(\s|\+)+from", "SQL DELETE FROM"),
        (r"update(\s|\+)+.*set", "SQL UPDATE SET"),
        
        # Command injection patterns
        (r'[;&|`$]', "Command injection characters"),
        (r'\$\(.*\)', "Command substitution"),
        (r'`.*`', "Backtick command execution"),
        
        # Path traversal patterns
        (r'\.\./', "Path traversal (../)"),
        (r'\.\.\\', "Path traversal (..\\)"),
        (r'%2e%2e%2f', "Encoded path traversal"),
        (r'%2e%2e%5c', "Encoded path traversal (backslash)"),
        
        # LDAP injection patterns
        (r'[()&|!]', "LDAP injection characters"),
        
        # XML injection patterns
        (r'<!ENTITY', "XML entity injection"),
        (r'<!DOCTYPE', "XML DOCTYPE injection"),
        
        # NoSQL injection patterns
        (r'\$where', "NoSQL $where injection"),
        (r'\$ne', "NoSQL $ne injection"),
        (r'\$gt', "NoSQL $gt injection"),
        (r'\$regex', "NoSQL $regex injection"),
    ]
    
    def __init__(self, sanitizer: Optional[TicketDataSanitizer] = None) -> None:
        """Initialize input validator."""
        self._sanitizer = sanitizer or TicketDataSanitizer()
        self._compiled_dangerous_patterns = [
            (re.compile(pattern, re.IGNORECASE), description)
            for pattern, description in self.DANGEROUS_PATTERNS
        ]
    
    def validate_input(self, 
                      value: Any, 
                      input_type: InputType,
                      field_name: str = "input",
                      required: bool = True) -> Tuple[ValidationResult, List[ValidationError]]:
        """Validate input value against specified type and security rules."""
        errors = []
        
        # Handle None/empty values
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                errors.append(ValidationError(
                    field=field_name,
                    message="Field is required",
                    input_type=input_type
                ))
                return ValidationResult.INVALID, errors
            else:
                return ValidationResult.VALID, errors
        
        # Convert to string for validation
        if not isinstance(value, str):
            value = str(value)
        
        # Length validation
        max_length = self.MAX_LENGTHS.get(input_type, 1000)
        if len(value) > max_length:
            errors.append(ValidationError(
                field=field_name,
                message=f"Field exceeds maximum length of {max_length} characters",
                input_type=input_type,
                suggested_fix=f"Truncate to {max_length} characters"
            ))
        
        # Pattern validation
        if input_type in self.VALIDATION_PATTERNS:
            pattern = self.VALIDATION_PATTERNS[input_type]
            if not pattern.match(value):
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Field does not match required format for {input_type.value}",
                    input_type=input_type,
                    suggested_fix=f"Use format matching pattern: {pattern.pattern}"
                ))
        
        # Security validation
        security_result, security_errors = self._check_security_patterns(field_name, value, input_type)
        errors.extend(security_errors)
        
        # Determine overall result
        if any(error.severity == "error" for error in errors):
            return ValidationResult.INVALID, errors
        elif security_result == ValidationResult.SUSPICIOUS or any(error.severity == "warning" for error in errors):
            return ValidationResult.SUSPICIOUS, errors
        else:
            return ValidationResult.VALID, errors
    
    def validate_multiple_inputs(self, 
                                inputs: Dict[str, Tuple[Any, InputType]],
                                required_fields: Optional[List[str]] = None) -> Tuple[ValidationResult, Dict[str, List[ValidationError]]]:
        """Validate multiple inputs at once."""
        all_errors = {}
        overall_result = ValidationResult.VALID
        
        required_fields = required_fields or []
        
        for field_name, (value, input_type) in inputs.items():
            is_required = field_name in required_fields
            result, errors = self.validate_input(value, input_type, field_name, is_required)
            
            if errors:
                all_errors[field_name] = errors
            
            # Update overall result
            if result == ValidationResult.INVALID:
                overall_result = ValidationResult.INVALID
            elif result == ValidationResult.SUSPICIOUS and overall_result == ValidationResult.VALID:
                overall_result = ValidationResult.SUSPICIOUS
        
        return overall_result, all_errors
    
    def sanitize_input(self, 
                      value: str, 
                      input_type: InputType,
                      aggressive: bool = False) -> str:
        """Sanitize input value for safe processing."""
        if not isinstance(value, str):
            value = str(value)
        
        # Basic sanitization
        sanitized = value.strip()
        
        # Type-specific sanitization
        if input_type == InputType.SEARCH_TERM:
            sanitized = self._sanitize_search_term(sanitized, aggressive)
        elif input_type == InputType.SAFE_TEXT:
            sanitized = self._sanitize_safe_text(sanitized)
        elif input_type == InputType.URL:
            sanitized = self._sanitize_url(sanitized)
        elif input_type == InputType.FILE_PATH:
            sanitized = self._sanitize_file_path(sanitized)
        elif input_type == InputType.JSON_DATA:
            sanitized = self._sanitize_json_data(sanitized)
        elif input_type == InputType.SQL_QUERY:
            sanitized = self._sanitize_sql_query(sanitized)
        elif input_type == InputType.COMMAND:
            sanitized = self._sanitize_command(sanitized)
        
        # Apply general sanitization
        sanitized = self._sanitizer.sanitize_log_message(sanitized)
        
        return sanitized
    
    def validate_ticket_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize ticket filter parameters."""
        validated = {}
        
        input_mapping = {
            'ticket_ids': (InputType.TICKET_ID, True),  # (type, is_list)
            'status': (InputType.STATUS, True),
            'assignee': (InputType.USERNAME, False),
            'start_date': (InputType.DATE, False),
            'end_date': (InputType.DATE, False),
            'search_term': (InputType.SEARCH_TERM, False),
            'max_results': (InputType.ALPHANUMERIC, False),
        }
        
        for key, value in filters.items():
            if key not in input_mapping:
                logger.warning(f"Unknown filter parameter: {key}")
                continue
            
            input_type, is_list = input_mapping[key]
            
            try:
                if is_list and isinstance(value, list):
                    validated_items = []
                    for item in value:
                        result, errors = self.validate_input(item, input_type, key, False)
                        if result != ValidationResult.INVALID:
                            validated_items.append(self.sanitize_input(str(item), input_type))
                        else:
                            logger.warning(f"Invalid {key} item: {item}, errors: {errors}")
                    
                    if validated_items:
                        validated[key] = validated_items
                
                elif not is_list:
                    result, errors = self.validate_input(value, input_type, key, False)
                    if result != ValidationResult.INVALID:
                        validated[key] = self.sanitize_input(str(value), input_type)
                    else:
                        logger.warning(f"Invalid {key}: {value}, errors: {errors}")
                
            except Exception as e:
                logger.error(f"Error validating filter {key}: {e}")
        
        return validated
    
    def validate_api_response(self, response_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate API response data for security issues."""
        issues = []
        
        try:
            # Check for suspicious patterns in response
            response_str = str(response_data)
            
            for pattern, description in self._compiled_dangerous_patterns:
                if pattern.search(response_str):
                    issues.append(f"Suspicious pattern detected: {description}")
            
            # Check for required fields in ticket data
            if isinstance(response_data, dict) and 'tickets' in response_data:
                tickets = response_data['tickets']
                if isinstance(tickets, list):
                    for i, ticket in enumerate(tickets):
                        if not isinstance(ticket, dict):
                            issues.append(f"Ticket {i} is not a dictionary")
                            continue
                        
                        required_fields = {'id', 'title', 'status'}
                        missing_fields = required_fields - set(ticket.keys())
                        if missing_fields:
                            issues.append(f"Ticket {i} missing required fields: {missing_fields}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Error validating API response: {e}")
            return False, [f"Validation error: {e}"]
    
    def _check_security_patterns(self, 
                                field_name: str, 
                                value: str,
                                input_type: InputType) -> Tuple[ValidationResult, List[ValidationError]]:
        """Check for dangerous security patterns."""
        errors = []
        
        # Check dangerous patterns
        for pattern, description in self._compiled_dangerous_patterns:
            if pattern.search(value):
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Potentially dangerous content detected: {description}",
                    severity="error",
                    input_type=input_type,
                    suggested_fix="Remove or escape dangerous characters"
                ))
        
        # Check for suspicious character combinations
        suspicious_chars = ['<', '>', '{', '}', '$', '`', '\\', ';', '|', '&']
        found_suspicious = [char for char in suspicious_chars if char in value]
        
        if found_suspicious and input_type not in [InputType.SAFE_TEXT, InputType.JSON_DATA]:
            errors.append(ValidationError(
                field=field_name,
                message=f"Suspicious characters detected: {found_suspicious}",
                severity="warning",
                input_type=input_type,
                suggested_fix="Remove or escape suspicious characters"
            ))
        
        # Determine result
        if any(error.severity == "error" for error in errors):
            return ValidationResult.INVALID, errors
        elif any(error.severity == "warning" for error in errors):
            return ValidationResult.SUSPICIOUS, errors
        else:
            return ValidationResult.VALID, errors
    
    def _sanitize_search_term(self, value: str, aggressive: bool = False) -> str:
        """Sanitize search term input."""
        # Remove potentially dangerous characters
        if aggressive:
            # Aggressive sanitization - only allow alphanumeric and basic punctuation
            sanitized = re.sub(r'[^\w\s.,!?()-]', '', value)
        else:
            # Standard sanitization - remove known dangerous patterns
            sanitized = re.sub(r'[<>{}$`\\;|&]', '', value)
        
        # Limit length
        sanitized = sanitized[:self.MAX_LENGTHS[InputType.SEARCH_TERM]]
        
        return sanitized.strip()
    
    def _sanitize_safe_text(self, value: str) -> str:
        """Sanitize safe text input."""
        # HTML escape
        sanitized = html.escape(value)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        return sanitized.strip()
    
    def _sanitize_url(self, value: str) -> str:
        """Sanitize URL input."""
        # URL encode dangerous characters
        sanitized = urllib.parse.quote(value, safe=':/?#[]@!$&\'()*+,;=')
        
        # Ensure it starts with http/https
        if not sanitized.startswith(('http://', 'https://')):
            sanitized = 'https://' + sanitized
        
        return sanitized
    
    def _sanitize_file_path(self, value: str) -> str:
        """Sanitize file path input."""
        # Remove path traversal attempts
        sanitized = re.sub(r'\.\./', '', value)
        sanitized = re.sub(r'\.\.\\', '', sanitized)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize path separators
        sanitized = sanitized.replace('\\', '/')
        
        return sanitized.strip()
    
    def _sanitize_json_data(self, value: str) -> str:
        """Sanitize JSON data input."""
        try:
            import json
            # Parse and re-serialize to ensure valid JSON
            parsed = json.loads(value)
            sanitized = json.dumps(parsed, separators=(',', ':'))
            return sanitized
        except json.JSONDecodeError:
            # If not valid JSON, treat as string and escape
            return html.escape(value)
    
    def _sanitize_sql_query(self, value: str) -> str:
        """Sanitize SQL query input (for logging/display only - never execute user SQL)."""
        # This is for sanitizing SQL for logging purposes only
        # Never execute user-provided SQL queries
        
        # Remove dangerous SQL keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER',
            'EXEC', 'EXECUTE', 'TRUNCATE', 'GRANT', 'REVOKE'
        ]
        
        sanitized = value
        for keyword in dangerous_keywords:
            sanitized = re.sub(rf'\b{keyword}\b', '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def _sanitize_command(self, value: str) -> str:
        """Sanitize command input."""
        # Remove command injection characters
        sanitized = re.sub(r'[;&|`$()]', '', value)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        return sanitized.strip()


class AdvancedInputValidator(InputValidator):
    """Advanced input validator with additional security features."""
    
    def __init__(self, 
                 sanitizer: Optional[TicketDataSanitizer] = None,
                 strict_mode: bool = False) -> None:
        """Initialize advanced input validator."""
        super().__init__(sanitizer)
        self._strict_mode = strict_mode
        self._validation_cache = {}  # Cache validation results for performance
    
    def validate_with_context(self, 
                             value: Any,
                             input_type: InputType,
                             context: Dict[str, Any],
                             field_name: str = "input") -> Tuple[ValidationResult, List[ValidationError]]:
        """Validate input with additional context information."""
        # Standard validation first
        result, errors = self.validate_input(value, input_type, field_name)
        
        # Context-based validation
        if context.get('user_role') == 'admin' and input_type == InputType.COMMAND:
            # Allow more permissive validation for admin users
            pass
        elif context.get('source') == 'external_api':
            # Apply stricter validation for external sources
            if result == ValidationResult.SUSPICIOUS:
                result = ValidationResult.INVALID
                errors.append(ValidationError(
                    field=field_name,
                    message="Suspicious input not allowed from external sources",
                    severity="error",
                    input_type=input_type
                ))
        
        return result, errors
    
    def batch_validate(self, 
                      inputs: List[Tuple[Any, InputType, str]]) -> Dict[str, Tuple[ValidationResult, List[ValidationError]]]:
        """Validate multiple inputs efficiently."""
        results = {}
        
        for value, input_type, field_name in inputs:
            # Check cache first
            cache_key = f"{field_name}:{input_type.value}:{hash(str(value))}"
            if cache_key in self._validation_cache:
                results[field_name] = self._validation_cache[cache_key]
            else:
                result = self.validate_input(value, input_type, field_name)
                self._validation_cache[cache_key] = result
                results[field_name] = result
        
        return results
    
    def generate_validation_report(self, 
                                  validation_results: Dict[str, Tuple[ValidationResult, List[ValidationError]]]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        report = {
            'total_fields': len(validation_results),
            'valid_fields': 0,
            'invalid_fields': 0,
            'suspicious_fields': 0,
            'errors_by_type': {},
            'security_issues': [],
            'recommendations': []
        }
        
        for field_name, (result, errors) in validation_results.items():
            if result == ValidationResult.VALID:
                report['valid_fields'] += 1
            elif result == ValidationResult.INVALID:
                report['invalid_fields'] += 1
            elif result == ValidationResult.SUSPICIOUS:
                report['suspicious_fields'] += 1
            
            for error in errors:
                error_type = error.input_type.value if error.input_type else 'unknown'
                if error_type not in report['errors_by_type']:
                    report['errors_by_type'][error_type] = 0
                report['errors_by_type'][error_type] += 1
                
                if error.severity == 'error' and 'injection' in error.message.lower():
                    report['security_issues'].append({
                        'field': field_name,
                        'issue': error.message,
                        'severity': error.severity
                    })
        
        # Generate recommendations
        if report['invalid_fields'] > 0:
            report['recommendations'].append("Review and fix invalid input fields")
        if report['suspicious_fields'] > 0:
            report['recommendations'].append("Investigate suspicious input patterns")
        if report['security_issues']:
            report['recommendations'].append("Address security issues immediately")
        
        return report