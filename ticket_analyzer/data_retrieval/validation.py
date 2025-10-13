"""Data validation and sanitization for ticket data retrieval.

This module provides comprehensive input validation, data sanitization,
and security measures for ticket data processing. It includes validation
for search criteria, ticket data, and protection against injection attacks.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Pattern, Union
from dataclasses import dataclass

from ..interfaces import (
    InputValidatorInterface,
    DataValidationInterface,
    DataSanitizerInterface
)
from ..models import (
    SearchCriteria,
    ValidationError,
    SecurityError,
    Ticket
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Validation rule configuration."""
    pattern: Pattern[str]
    max_length: int
    min_length: int = 0
    required: bool = False
    description: str = ""


class InputValidator(InputValidatorInterface):
    """Comprehensive input validator for security and data integrity.
    
    This validator implements security-focused validation to prevent
    injection attacks, ensure data integrity, and maintain system security.
    """
    
    # Maximum lengths for different input types
    MAX_LENGTHS = {
        'ticket_id': 50,
        'username': 100,
        'search_term': 500,
        'description': 10000,
        'title': 500,
        'status': 50,
        'tag': 100,
        'lucene_query': 1000,
        'assignee': 100,
        'resolver_group': 200
    }
    
    # Validation patterns for different input types
    VALIDATION_PATTERNS = {
        'ticket_id': re.compile(r'^[A-Z]{1,10}-?\d{1,15}$', re.IGNORECASE),
        'username': re.compile(r'^[a-zA-Z0-9._-]{1,100}$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'date_iso': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'datetime_iso': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})?$'),
        'status': re.compile(r'^[a-zA-Z\s_-]{1,50}$'),
        'tag': re.compile(r'^[a-zA-Z0-9\s._-]{1,100}$'),
        'safe_text': re.compile(r'^[a-zA-Z0-9\s.,!?()_-]{1,500}$'),
        'assignee': re.compile(r'^[a-zA-Z0-9._-]{1,100}$'),
        'resolver_group': re.compile(r'^[a-zA-Z0-9\s._-]{1,200}$')
    }
    
    # Dangerous patterns that indicate potential injection attacks
    INJECTION_PATTERNS = [
        # SQL injection patterns
        r"('|(\\')|(;)|(\\;))",  # Single quotes and semicolons
        r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or
        r"(union(\s|\+)+select)",  # union select
        r"(drop(\s|\+)+table)",  # drop table
        r"(insert(\s|\+)+into)",  # insert into
        r"(delete(\s|\+)+from)",  # delete from
        r"(exec(\s|\+)+(s|x)p\w+)",  # exec sp_
        
        # Script injection patterns
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>',  # Iframes
        r'<object[^>]*>',  # Objects
        r'<embed[^>]*>',  # Embeds
        
        # Code injection patterns
        r'eval\s*\(',  # eval() calls
        r'exec\s*\(',  # exec() calls
        r'\$\{.*\}',  # Template injection
        r'\{\{.*\}\}',  # Template injection
        r'<%.*%>',  # Server-side includes
        
        # Command injection patterns
        r'[;&|`$]',  # Command separators and substitution
        r'\.\./.*',  # Path traversal
        r'\\x[0-9a-fA-F]{2}',  # Hex encoding
        r'%[0-9a-fA-F]{2}',  # URL encoding of dangerous chars
    ]
    
    def __init__(self) -> None:
        """Initialize input validator."""
        self._compiled_injection_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.INJECTION_PATTERNS
        ]
    
    def validate_input(self, value: str, input_type: str) -> bool:
        """Validate input value against type-specific constraints.
        
        Args:
            value: Input value to validate.
            input_type: Type of input for validation rules.
            
        Returns:
            True if input is valid, False otherwise.
        """
        if not isinstance(value, str):
            logger.warning(f"Input value is not a string: {type(value)}")
            return False
        
        # Check length constraints
        max_length = self.MAX_LENGTHS.get(input_type, 1000)
        if len(value) > max_length:
            logger.warning(f"Input exceeds maximum length for {input_type}: {len(value)} > {max_length}")
            return False
        
        # Check for empty values where not allowed
        if not value.strip() and input_type in ['ticket_id', 'username']:
            logger.warning(f"Empty value not allowed for {input_type}")
            return False
        
        # Check pattern validation
        if input_type in self.VALIDATION_PATTERNS:
            pattern = self.VALIDATION_PATTERNS[input_type]
            if not pattern.match(value):
                logger.warning(f"Input does not match pattern for {input_type}: {value}")
                return False
        
        # Check for injection attempts
        if self.detect_injection_attempt(value):
            logger.error(f"Injection attempt detected in {input_type}: {value}")
            return False
        
        return True
    
    def sanitize_input(self, value: str, input_type: str) -> str:
        """Sanitize input value for safe processing.
        
        Args:
            value: Input value to sanitize.
            input_type: Type of input for sanitization rules.
            
        Returns:
            Sanitized input value safe for processing.
        """
        if not isinstance(value, str):
            return str(value)
        
        # Basic sanitization
        sanitized = value.strip()
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Input-type specific sanitization
        if input_type == 'search_term':
            # Remove potentially dangerous characters for search
            sanitized = re.sub(r'[<>{}$`\\]', '', sanitized)
        elif input_type == 'lucene_query':
            # Allow Lucene query syntax but remove dangerous patterns
            sanitized = self._sanitize_lucene_query(sanitized)
        elif input_type in ['ticket_id', 'username', 'assignee']:
            # Keep only alphanumeric, dots, hyphens, underscores
            sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', sanitized)
        
        # Limit length
        max_length = self.MAX_LENGTHS.get(input_type, 1000)
        sanitized = sanitized[:max_length]
        
        return sanitized
    
    def _sanitize_lucene_query(self, query: str) -> str:
        """Sanitize Lucene query while preserving valid syntax.
        
        Args:
            query: Lucene query to sanitize.
            
        Returns:
            Sanitized Lucene query.
        """
        # Remove dangerous patterns while preserving Lucene operators
        sanitized = query
        
        # Remove script tags and JavaScript
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove SQL injection patterns
        sanitized = re.sub(r'\b(union|select|drop|insert|delete|exec)\b', '', sanitized, flags=re.IGNORECASE)
        
        # Remove command injection characters
        sanitized = re.sub(r'[;&|`$]', '', sanitized)
        
        # Preserve Lucene operators: AND, OR, NOT, +, -, ", (, ), [, ], {, }, ~, *, ?, \, :
        # Remove other potentially dangerous characters
        sanitized = re.sub(r'[<>]', '', sanitized)
        
        return sanitized
    
    def validate_search_criteria(self, criteria: SearchCriteria) -> bool:
        """Validate search criteria for security and correctness.
        
        Args:
            criteria: Search criteria to validate.
            
        Returns:
            True if criteria is valid and safe, False otherwise.
            
        Raises:
            ValidationError: If criteria contains invalid or dangerous content.
        """
        try:
            # Validate status filters
            if criteria.status_filters:
                for status in criteria.status_filters:
                    if not self.validate_input(status, 'status'):
                        raise ValidationError(f"Invalid status filter: {status}")
            
            # Validate assignee
            if criteria.assignee:
                if not self.validate_input(criteria.assignee, 'assignee'):
                    raise ValidationError(f"Invalid assignee: {criteria.assignee}")
            
            # Validate date range
            if criteria.start_date and criteria.end_date:
                if not self.validate_date_range(
                    criteria.start_date.isoformat(),
                    criteria.end_date.isoformat()
                ):
                    raise ValidationError("Invalid date range")
            
            # Validate search text
            if criteria.search_text:
                if not self.validate_input(criteria.search_text, 'search_term'):
                    raise ValidationError(f"Invalid search text: {criteria.search_text}")
            
            # Validate Lucene query
            if criteria.lucene_query:
                if not self.validate_input(criteria.lucene_query, 'lucene_query'):
                    raise ValidationError(f"Invalid Lucene query: {criteria.lucene_query}")
            
            # Validate limits
            if criteria.max_results and criteria.max_results > 10000:
                raise ValidationError("Max results exceeds limit (10000)")
            
            if criteria.offset and criteria.offset < 0:
                raise ValidationError("Offset cannot be negative")
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Search criteria validation failed: {e}")
            return False
    
    def validate_ticket_id(self, ticket_id: str) -> bool:
        """Validate ticket ID format and security.
        
        Args:
            ticket_id: Ticket ID to validate.
            
        Returns:
            True if ticket ID is valid, False otherwise.
        """
        return self.validate_input(ticket_id, 'ticket_id')
    
    def validate_date_range(self, start_date: str, end_date: str) -> bool:
        """Validate date range for search operations.
        
        Args:
            start_date: Start date in ISO format.
            end_date: End date in ISO format.
            
        Returns:
            True if date range is valid, False otherwise.
        """
        try:
            # Parse dates
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Check logical order
            if start > end:
                logger.warning("Start date is after end date")
                return False
            
            # Check reasonable range (not more than 5 years)
            if end - start > timedelta(days=1825):  # ~5 years
                logger.warning("Date range exceeds maximum allowed period")
                return False
            
            # Check dates are not in the far future
            now = datetime.now()
            if start > now + timedelta(days=30):
                logger.warning("Start date is too far in the future")
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date format: {e}")
            return False
    
    def detect_injection_attempt(self, value: str) -> bool:
        """Detect potential injection attacks in input.
        
        Args:
            value: Input value to check for injection patterns.
            
        Returns:
            True if injection attempt detected, False otherwise.
        """
        for pattern in self._compiled_injection_patterns:
            if pattern.search(value):
                logger.error(f"Injection pattern detected: {pattern.pattern}")
                return True
        
        return False
    
    def get_validation_errors(self, value: str, input_type: str) -> List[str]:
        """Get detailed validation errors for input value.
        
        Args:
            value: Input value to validate.
            input_type: Type of input for validation rules.
            
        Returns:
            List of validation error messages.
        """
        errors = []
        
        if not isinstance(value, str):
            errors.append(f"Value must be a string, got {type(value).__name__}")
            return errors
        
        # Check length
        max_length = self.MAX_LENGTHS.get(input_type, 1000)
        if len(value) > max_length:
            errors.append(f"Value exceeds maximum length of {max_length} characters")
        
        # Check empty values
        if not value.strip() and input_type in ['ticket_id', 'username']:
            errors.append(f"Value cannot be empty for {input_type}")
        
        # Check pattern
        if input_type in self.VALIDATION_PATTERNS:
            pattern = self.VALIDATION_PATTERNS[input_type]
            if not pattern.match(value):
                errors.append(f"Value does not match required format for {input_type}")
        
        # Check for injection
        if self.detect_injection_attempt(value):
            errors.append("Value contains potentially dangerous content")
        
        return errors


class DataValidator(DataValidationInterface):
    """Validator for ticket data structure and content."""
    
    def __init__(self) -> None:
        """Initialize data validator."""
        self._input_validator = InputValidator()
    
    def validate_ticket_data(self, ticket_data: Dict[str, Any]) -> bool:
        """Validate ticket data structure and content.
        
        Args:
            ticket_data: Ticket data to validate.
            
        Returns:
            True if ticket data is valid, False otherwise.
        """
        try:
            # Check required fields
            required_fields = {'id', 'title', 'status'}
            missing_fields = required_fields - set(ticket_data.keys())
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                return False
            
            # Validate field values
            if not self._input_validator.validate_input(ticket_data['id'], 'ticket_id'):
                return False
            
            if not self._input_validator.validate_input(ticket_data['title'], 'title'):
                return False
            
            if not self._input_validator.validate_input(ticket_data['status'], 'status'):
                return False
            
            # Validate optional fields
            if 'assignee' in ticket_data and ticket_data['assignee']:
                if not self._input_validator.validate_input(ticket_data['assignee'], 'assignee'):
                    return False
            
            if 'description' in ticket_data and ticket_data['description']:
                if len(ticket_data['description']) > 10000:
                    logger.warning("Description exceeds maximum length")
                    return False
            
            # Validate dates
            date_fields = ['createDate', 'lastUpdatedDate', 'lastResolvedDate']
            for field in date_fields:
                if field in ticket_data and ticket_data[field]:
                    if not self._validate_date_string(ticket_data[field]):
                        logger.warning(f"Invalid date format in field {field}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ticket data validation failed: {e}")
            return False
    
    def validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate MCP response format and structure.
        
        Args:
            response: MCP response to validate.
            
        Returns:
            True if response format is valid, False otherwise.
        """
        try:
            # Check if response is a dictionary
            if not isinstance(response, dict):
                logger.warning(f"Response is not a dictionary: {type(response)}")
                return False
            
            # Check for expected fields in ticket search response
            if 'tickets' in response:
                tickets = response['tickets']
                if not isinstance(tickets, list):
                    logger.warning("Tickets field is not a list")
                    return False
                
                # Validate each ticket
                for ticket in tickets:
                    if not self.validate_ticket_data(ticket):
                        return False
            
            # Check for single ticket response
            elif 'ticket' in response:
                return self.validate_ticket_data(response['ticket'])
            
            # Check for error response
            elif 'error' in response:
                error = response['error']
                if not isinstance(error, dict) or 'message' not in error:
                    logger.warning("Invalid error response format")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Response format validation failed: {e}")
            return False
    
    def clean_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize ticket data for processing.
        
        Args:
            ticket_data: Raw ticket data to clean.
            
        Returns:
            Cleaned and normalized ticket data.
        """
        cleaned = {}
        
        for key, value in ticket_data.items():
            if value is None:
                continue
            
            # Clean string values
            if isinstance(value, str):
                cleaned_value = value.strip()
                if cleaned_value:  # Only include non-empty strings
                    cleaned[key] = cleaned_value
            
            # Clean nested dictionaries
            elif isinstance(value, dict):
                cleaned_dict = self.clean_ticket_data(value)
                if cleaned_dict:  # Only include non-empty dictionaries
                    cleaned[key] = cleaned_dict
            
            # Clean lists
            elif isinstance(value, list):
                cleaned_list = [
                    item for item in value 
                    if item is not None and (not isinstance(item, str) or item.strip())
                ]
                if cleaned_list:  # Only include non-empty lists
                    cleaned[key] = cleaned_list
            
            # Keep other types as-is
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _validate_date_string(self, date_str: str) -> bool:
        """Validate date string format.
        
        Args:
            date_str: Date string to validate.
            
        Returns:
            True if date string is valid, False otherwise.
        """
        try:
            # Try parsing as ISO format
            if date_str.endswith('Z'):
                datetime.fromisoformat(date_str[:-1] + '+00:00')
            else:
                datetime.fromisoformat(date_str)
            return True
        except ValueError:
            return False


class SearchCriteriaValidator:
    """Specialized validator for search criteria objects."""
    
    def __init__(self) -> None:
        """Initialize search criteria validator."""
        self._input_validator = InputValidator()
    
    def validate(self, criteria: SearchCriteria) -> bool:
        """Validate search criteria comprehensively.
        
        Args:
            criteria: Search criteria to validate.
            
        Returns:
            True if criteria is valid, False otherwise.
        """
        return self._input_validator.validate_search_criteria(criteria)
    
    def sanitize(self, criteria: SearchCriteria) -> SearchCriteria:
        """Sanitize search criteria for safe processing.
        
        Args:
            criteria: Search criteria to sanitize.
            
        Returns:
            Sanitized search criteria.
        """
        # Sanitize string fields
        sanitized_assignee = None
        if criteria.assignee:
            sanitized_assignee = self._input_validator.sanitize_input(criteria.assignee, 'assignee')
        
        sanitized_search_text = None
        if criteria.search_text:
            sanitized_search_text = self._input_validator.sanitize_input(criteria.search_text, 'search_term')
        
        sanitized_lucene_query = None
        if criteria.lucene_query:
            sanitized_lucene_query = self._input_validator.sanitize_input(criteria.lucene_query, 'lucene_query')
        
        # Sanitize status filters
        sanitized_status_filters = None
        if criteria.status_filters:
            sanitized_status_filters = [
                self._input_validator.sanitize_input(status, 'status')
                for status in criteria.status_filters
            ]
        
        # Create sanitized criteria
        return SearchCriteria(
            status_filters=sanitized_status_filters,
            assignee=sanitized_assignee,
            start_date=criteria.start_date,  # Dates don't need sanitization
            end_date=criteria.end_date,
            search_text=sanitized_search_text,
            lucene_query=sanitized_lucene_query,
            max_results=min(criteria.max_results or 1000, 10000),  # Cap at reasonable limit
            offset=max(criteria.offset or 0, 0)  # Ensure non-negative
        )
    
    def get_validation_report(self, criteria: SearchCriteria) -> Dict[str, List[str]]:
        """Get detailed validation report for search criteria.
        
        Args:
            criteria: Search criteria to validate.
            
        Returns:
            Dictionary mapping field names to validation error lists.
        """
        report = {}
        
        # Validate assignee
        if criteria.assignee:
            errors = self._input_validator.get_validation_errors(criteria.assignee, 'assignee')
            if errors:
                report['assignee'] = errors
        
        # Validate search text
        if criteria.search_text:
            errors = self._input_validator.get_validation_errors(criteria.search_text, 'search_term')
            if errors:
                report['search_text'] = errors
        
        # Validate Lucene query
        if criteria.lucene_query:
            errors = self._input_validator.get_validation_errors(criteria.lucene_query, 'lucene_query')
            if errors:
                report['lucene_query'] = errors
        
        # Validate status filters
        if criteria.status_filters:
            status_errors = []
            for status in criteria.status_filters:
                errors = self._input_validator.get_validation_errors(status, 'status')
                status_errors.extend(errors)
            if status_errors:
                report['status_filters'] = status_errors
        
        # Validate date range
        if criteria.start_date and criteria.end_date:
            if not self._input_validator.validate_date_range(
                criteria.start_date.isoformat(),
                criteria.end_date.isoformat()
            ):
                report['date_range'] = ['Invalid date range']
        
        # Validate limits
        limit_errors = []
        if criteria.max_results and criteria.max_results > 10000:
            limit_errors.append('Max results exceeds limit (10000)')
        
        if criteria.offset and criteria.offset < 0:
            limit_errors.append('Offset cannot be negative')
        
        if limit_errors:
            report['limits'] = limit_errors
        
        return report