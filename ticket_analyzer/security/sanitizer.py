"""Data sanitization system for ticket analyzer.

This module provides comprehensive data sanitization capabilities including:
- PII detection and removal
- Sensitive data pattern matching
- Secure data cleaning for logs and outputs
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional, Union, Pattern
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Sensitivity levels for data sanitization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SanitizationRule:
    """Rule for data sanitization."""
    pattern: str
    replacement: str = "[REDACTED]"
    field_names: Optional[List[str]] = None
    case_sensitive: bool = False
    sensitivity_level: SensitivityLevel = SensitivityLevel.MEDIUM
    description: str = ""

    def __post_init__(self) -> None:
        """Compile regex pattern for performance."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self.compiled_pattern: Pattern[str] = re.compile(self.pattern, flags)


class PIIDetector:
    """Detect and classify Personally Identifiable Information."""
    
    # Compiled regex patterns for better performance
    PII_PATTERNS: Dict[str, Pattern[str]] = {
        'email': re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        'phone_us': re.compile(
            r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        ),
        'phone_international': re.compile(
            r'\+[1-9]\d{1,14}'
        ),
        'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        'ipv6_address': re.compile(
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
        ),
        'mac_address': re.compile(
            r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'
        ),
        'aws_account': re.compile(r'\b\d{12}\b'),
        'uuid': re.compile(
            r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
            re.IGNORECASE
        ),
        'api_key': re.compile(r'\b[A-Za-z0-9+/]{32,}={0,2}\b'),
        'base64_token': re.compile(r'\b[A-Za-z0-9+/]{20,}={0,2}\b'),
        'aws_access_key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
        'aws_secret_key': re.compile(r'\b[A-Za-z0-9/+=]{40}\b'),
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
    
    @classmethod
    def get_pii_summary(cls, text: str) -> Dict[str, int]:
        """Get summary of PII types and counts in text."""
        summary = {}
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                summary[pii_type] = len(matches)
        
        return summary


class TicketDataSanitizer:
    """Sanitizer for ticket data to remove sensitive information."""
    
    # Common sensitive patterns in ticket data
    DEFAULT_PATTERNS = [
        # Email addresses
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            replacement='[EMAIL_REDACTED]',
            sensitivity_level=SensitivityLevel.HIGH,
            description="Email addresses"
        ),
        # Phone numbers (US format)
        SanitizationRule(
            pattern=r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            replacement='[PHONE_REDACTED]',
            sensitivity_level=SensitivityLevel.HIGH,
            description="US phone numbers"
        ),
        # International phone numbers
        SanitizationRule(
            pattern=r'\+[1-9]\d{1,14}',
            replacement='[PHONE_REDACTED]',
            sensitivity_level=SensitivityLevel.HIGH,
            description="International phone numbers"
        ),
        # Social Security Numbers
        SanitizationRule(
            pattern=r'\b\d{3}-?\d{2}-?\d{4}\b',
            replacement='[SSN_REDACTED]',
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="Social Security Numbers"
        ),
        # Credit card numbers
        SanitizationRule(
            pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            replacement='[CARD_REDACTED]',
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="Credit card numbers"
        ),
        # IP addresses (IPv4)
        SanitizationRule(
            pattern=r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            replacement='[IP_REDACTED]',
            sensitivity_level=SensitivityLevel.MEDIUM,
            description="IPv4 addresses"
        ),
        # IPv6 addresses
        SanitizationRule(
            pattern=r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
            replacement='[IPV6_REDACTED]',
            sensitivity_level=SensitivityLevel.MEDIUM,
            description="IPv6 addresses"
        ),
        # MAC addresses
        SanitizationRule(
            pattern=r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
            replacement='[MAC_REDACTED]',
            sensitivity_level=SensitivityLevel.MEDIUM,
            description="MAC addresses"
        ),
        # AWS account IDs
        SanitizationRule(
            pattern=r'\b\d{12}\b',
            replacement='[ACCOUNT_REDACTED]',
            sensitivity_level=SensitivityLevel.HIGH,
            description="AWS account IDs"
        ),
        # UUIDs
        SanitizationRule(
            pattern=r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
            replacement='[UUID_REDACTED]',
            sensitivity_level=SensitivityLevel.MEDIUM,
            description="UUIDs"
        ),
        # API keys and tokens (base64-like strings)
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9+/]{32,}={0,2}\b',
            replacement='[TOKEN_REDACTED]',
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="API keys and tokens"
        ),
        # AWS Access Keys
        SanitizationRule(
            pattern=r'\bAKIA[0-9A-Z]{16}\b',
            replacement='[AWS_ACCESS_KEY_REDACTED]',
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="AWS access keys"
        ),
        # AWS Secret Keys
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9/+=]{40}\b',
            replacement='[AWS_SECRET_REDACTED]',
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="AWS secret keys"
        ),
        # File paths that might contain sensitive info
        SanitizationRule(
            pattern=r'/home/[^/\s]+/[^\s]*',
            replacement='[HOME_PATH_REDACTED]',
            sensitivity_level=SensitivityLevel.LOW,
            description="Home directory paths"
        ),
        # Passwords in various formats
        SanitizationRule(
            pattern=r'password["\s]*[:=]["\s]*[^\s"]+',
            replacement='password=[PASSWORD_REDACTED]',
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="Password fields"
        ),
    ]
    
    # Sensitive field names
    SENSITIVE_FIELDS = {
        'password', 'passwd', 'pwd', 'token', 'secret', 'key', 'auth', 
        'credential', 'private_notes', 'internal_comments', 'confidential',
        'personal_info', 'contact_info', 'phone', 'email', 'ssn', 
        'social_security', 'credit_card', 'payment_info', 'api_key',
        'access_token', 'refresh_token', 'session_id', 'cookie',
        'authorization', 'bearer', 'private_key', 'public_key'
    }
    
    def __init__(self, 
                 custom_rules: Optional[List[SanitizationRule]] = None,
                 sensitivity_threshold: SensitivityLevel = SensitivityLevel.LOW) -> None:
        """Initialize sanitizer with rules and sensitivity threshold."""
        self._rules = self.DEFAULT_PATTERNS.copy()
        if custom_rules:
            self._rules.extend(custom_rules)
        
        self._sensitivity_threshold = sensitivity_threshold
        self._pii_detector = PIIDetector()
        
        # Compile all patterns for performance
        for rule in self._rules:
            if not hasattr(rule, 'compiled_pattern'):
                rule.__post_init__()
    
    def sanitize_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ticket data dictionary."""
        if not isinstance(ticket_data, dict):
            logger.warning(f"Expected dict, got {type(ticket_data)}")
            return ticket_data
        
        sanitized = {}
        
        for key, value in ticket_data.items():
            if self._is_sensitive_field(key):
                sanitized[key] = "[FIELD_REDACTED]"
                logger.debug(f"Redacted sensitive field: {key}")
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_ticket_data(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def sanitize_log_message(self, message: str) -> str:
        """Sanitize log message to remove sensitive information."""
        return self._sanitize_text(message)
    
    def sanitize_error_message(self, error_message: str) -> str:
        """Sanitize error message to prevent information leakage."""
        sanitized = self._sanitize_text(error_message)
        
        # Additional sanitization for error messages
        # Remove file paths that might contain sensitive information
        sanitized = re.sub(
            r'/[^\s]*/(ticket_analyzer|\.ticket-analyzer)/[^\s]*',
            '[PATH_REDACTED]',
            sanitized
        )
        
        # Remove stack trace information that might be sensitive
        sanitized = re.sub(
            r'File "[^"]*", line \d+',
            'File "[REDACTED]", line [REDACTED]',
            sanitized
        )
        
        return sanitized
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field name indicates sensitive data."""
        return field_name.lower() in self.SENSITIVE_FIELDS
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content using defined rules."""
        if not isinstance(text, str):
            return text
        
        sanitized = text
        
        # Apply sanitization rules based on sensitivity threshold
        for rule in self._rules:
            if rule.sensitivity_level.value >= self._sensitivity_threshold.value:
                continue  # Skip rules below threshold
            
            try:
                sanitized = rule.compiled_pattern.sub(rule.replacement, sanitized)
            except Exception as e:
                logger.warning(f"Error applying sanitization rule '{rule.description}': {e}")
                continue
        
        return sanitized
    
    def _sanitize_list(self, data_list: List[Any]) -> List[Any]:
        """Sanitize list of data."""
        if not isinstance(data_list, list):
            return data_list
        
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
    
    def add_custom_rule(self, rule: SanitizationRule) -> None:
        """Add a custom sanitization rule."""
        if not hasattr(rule, 'compiled_pattern'):
            rule.__post_init__()
        self._rules.append(rule)
        logger.info(f"Added custom sanitization rule: {rule.description}")
    
    def get_sanitization_summary(self, text: str) -> Dict[str, Any]:
        """Get summary of what would be sanitized in the text."""
        summary = {
            'pii_detected': self._pii_detector.get_pii_summary(text),
            'rules_triggered': [],
            'sensitive_fields': []
        }
        
        for rule in self._rules:
            if rule.compiled_pattern.search(text):
                summary['rules_triggered'].append({
                    'description': rule.description,
                    'sensitivity_level': rule.sensitivity_level.value,
                    'pattern_matches': len(rule.compiled_pattern.findall(text))
                })
        
        return summary


class AdvancedPIISanitizer(TicketDataSanitizer):
    """Enhanced sanitizer with advanced PII detection capabilities."""
    
    def sanitize_with_pii_detection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data with PII detection and classification."""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                if self._pii_detector.has_pii(value):
                    pii_types = self._pii_detector.detect_pii_types(value)
                    logger.warning(f"PII detected in field '{key}': {pii_types}")
                    sanitized[key] = self._pii_detector.remove_all_pii(value)
                else:
                    sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_with_pii_detection(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list_with_pii(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_list_with_pii(self, data_list: List[Any]) -> List[Any]:
        """Sanitize list with PII detection."""
        if not isinstance(data_list, list):
            return data_list
        
        sanitized = []
        
        for item in data_list:
            if isinstance(item, str) and self._pii_detector.has_pii(item):
                sanitized.append(self._pii_detector.remove_all_pii(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_with_pii_detection(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list_with_pii(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    def generate_pii_report(self, data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Generate a comprehensive PII detection report."""
        if isinstance(data, str):
            text_data = data
        elif isinstance(data, dict):
            # Convert dict to string for analysis
            import json
            text_data = json.dumps(data, default=str)
        else:
            text_data = str(data)
        
        pii_summary = self._pii_detector.get_pii_summary(text_data)
        sanitization_summary = self.get_sanitization_summary(text_data)
        
        return {
            'pii_detected': pii_summary,
            'total_pii_instances': sum(pii_summary.values()),
            'sanitization_rules_triggered': len(sanitization_summary['rules_triggered']),
            'risk_level': self._assess_risk_level(pii_summary),
            'recommendations': self._generate_recommendations(pii_summary)
        }
    
    def _assess_risk_level(self, pii_summary: Dict[str, int]) -> str:
        """Assess risk level based on PII types detected."""
        critical_pii = {'ssn', 'credit_card', 'aws_secret_key', 'api_key'}
        high_pii = {'email', 'phone_us', 'phone_international', 'aws_access_key'}
        
        if any(pii_type in critical_pii for pii_type in pii_summary):
            return 'CRITICAL'
        elif any(pii_type in high_pii for pii_type in pii_summary):
            return 'HIGH'
        elif pii_summary:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_recommendations(self, pii_summary: Dict[str, int]) -> List[str]:
        """Generate recommendations based on PII detected."""
        recommendations = []
        
        if 'ssn' in pii_summary:
            recommendations.append("Remove Social Security Numbers immediately")
        if 'credit_card' in pii_summary:
            recommendations.append("Remove credit card numbers immediately")
        if any(key in pii_summary for key in ['aws_secret_key', 'api_key']):
            recommendations.append("Rotate compromised API keys/secrets")
        if any(key in pii_summary for key in ['email', 'phone_us', 'phone_international']):
            recommendations.append("Consider masking contact information")
        
        if not recommendations:
            recommendations.append("No critical PII detected, but continue monitoring")
        
        return recommendations