"""Authentication validation and error handling with comprehensive security measures.

This module provides comprehensive authentication validation, error handling,
and user-friendly error messages with proper credential sanitization and
logging security measures.
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..models.exceptions import (
    AuthenticationError,
    ValidationError,
    SecurityError,
    AuthenticationTimeoutError
)
from ..models.config import AuthConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of authentication validation.
    
    Attributes:
        is_valid: Whether validation passed
        errors: List of validation error messages
        warnings: List of validation warning messages
        details: Additional validation details
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []
        if self.details is None:
            self.details = {}


class AuthenticationValidator:
    """Comprehensive authentication validation and error handling.
    
    Provides validation for authentication operations, user-friendly
    error messages, and secure logging with credential sanitization.
    
    Features:
    - Authentication status validation
    - Configuration validation
    - Error message sanitization
    - User-friendly error reporting
    - Security-aware logging
    - Timeout and retry validation
    """
    
    # Sensitive patterns to sanitize from logs and error messages
    SENSITIVE_PATTERNS = [
        (r'password["\s]*[:=]["\s]*[^\s"]+', '[PASSWORD_REDACTED]'),
        (r'token["\s]*[:=]["\s]*[^\s"]+', '[TOKEN_REDACTED]'),
        (r'secret["\s]*[:=]["\s]*[^\s"]+', '[SECRET_REDACTED]'),
        (r'key["\s]*[:=]["\s]*[^\s"]+', '[KEY_REDACTED]'),
        (r'credential["\s]*[:=]["\s]*[^\s"]+', '[CREDENTIAL_REDACTED]'),
        (r'\b[A-Za-z0-9+/]{20,}={0,2}\b', '[TOKEN_REDACTED]'),  # Base64-like tokens
        (r'mwinit[^\s]*\s+[^\s]+', 'mwinit [ARGS_REDACTED]'),  # mwinit command args
    ]    
 
   def __init__(self, config: Optional[AuthConfig] = None) -> None:
        """Initialize authentication validator.
        
        Args:
            config: Authentication configuration for validation rules.
        """
        self._config = config or AuthConfig()
        logger.debug("AuthenticationValidator initialized")
    
    def validate_authentication_status(self, auth_result: Dict[str, Any]) -> ValidationResult:
        """Validate authentication status and results.
        
        Args:
            auth_result: Authentication result dictionary containing status info.
            
        Returns:
            ValidationResult with validation outcome and details.
        """
        errors = []
        warnings = []
        details = {}
        
        try:
            # Check if authentication was successful
            if not auth_result.get("authenticated", False):
                errors.append("Authentication failed")
                details["auth_status"] = "failed"
            
            # Validate session information if present
            if "session_info" in auth_result:
                session_validation = self._validate_session_info(auth_result["session_info"])
                if not session_validation.is_valid:
                    errors.extend(session_validation.errors)
                warnings.extend(session_validation.warnings)
                details.update(session_validation.details)
            
            # Check for timeout issues
            if auth_result.get("timeout_occurred"):
                warnings.append("Authentication timeout occurred")
                details["timeout_duration"] = auth_result.get("timeout_duration")
            
            # Validate authentication method
            auth_method = auth_result.get("auth_method", "unknown")
            if auth_method not in ["midway", "kerberos"]:
                warnings.append(f"Unknown authentication method: {auth_method}")
            
            is_valid = len(errors) == 0
            
            logger.debug("Authentication status validation: %s (%d errors, %d warnings)",
                        "valid" if is_valid else "invalid", len(errors), len(warnings))
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            logger.error("Error during authentication validation: %s", e)
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                details={"validation_error": str(e)}
            )
    
    def validate_configuration(self, config: AuthConfig) -> ValidationResult:
        """Validate authentication configuration.
        
        Args:
            config: Authentication configuration to validate.
            
        Returns:
            ValidationResult with validation outcome and details.
        """
        errors = []
        warnings = []
        details = {}
        
        try:
            # Use the config's built-in validation
            config.validate()
            
            # Additional validation checks
            if config.timeout_seconds < 10:
                warnings.append("Very short timeout may cause authentication failures")
            
            if config.timeout_seconds > 120:
                warnings.append("Very long timeout may cause poor user experience")
            
            if config.max_retry_attempts > 5:
                warnings.append("High retry count may cause delays")
            
            if config.session_duration_hours > 12:
                warnings.append("Long session duration may pose security risks")
            
            # Check authentication method
            if config.auth_method == "none" and config.require_auth:
                errors.append("Authentication required but method set to 'none'")
            
            details["config_valid"] = True
            
        except ValueError as e:
            errors.append(f"Configuration validation failed: {e}")
            details["config_valid"] = False
        except Exception as e:
            errors.append(f"Unexpected configuration error: {e}")
            details["config_valid"] = False
        
        is_valid = len(errors) == 0
        
        logger.debug("Configuration validation: %s (%d errors, %d warnings)",
                    "valid" if is_valid else "invalid", len(errors), len(warnings))
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            details=details
        )
    
    def _validate_session_info(self, session_info: Dict[str, Any]) -> ValidationResult:
        """Validate session information.
        
        Args:
            session_info: Session information dictionary.
            
        Returns:
            ValidationResult for session validation.
        """
        errors = []
        warnings = []
        details = {}
        
        # Check session expiry
        if "expiry_time" in session_info:
            try:
                expiry_str = session_info["expiry_time"]
                expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                
                if expiry_time <= datetime.now():
                    errors.append("Session has expired")
                    details["session_expired"] = True
                elif expiry_time <= datetime.now() + timedelta(minutes=15):
                    warnings.append("Session expires soon")
                    details["session_near_expiry"] = True
                    
            except (ValueError, TypeError) as e:
                warnings.append(f"Invalid session expiry format: {e}")
        
        # Check session age
        if "start_time" in session_info:
            try:
                start_str = session_info["start_time"]
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                session_age = datetime.now() - start_time
                
                if session_age > timedelta(hours=24):
                    warnings.append("Session is very old")
                    details["session_age_hours"] = session_age.total_seconds() / 3600
                    
            except (ValueError, TypeError) as e:
                warnings.append(f"Invalid session start time format: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details=details
        )
    
    def sanitize_error_message(self, message: str) -> str:
        """Sanitize error message to remove sensitive information.
        
        Args:
            message: Raw error message that may contain sensitive data.
            
        Returns:
            Sanitized error message safe for logging and display.
        """
        sanitized = message
        
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def sanitize_log_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize log data to remove sensitive information.
        
        Args:
            data: Dictionary that may contain sensitive information.
            
        Returns:
            Sanitized dictionary safe for logging.
        """
        sanitized = {}
        
        for key, value in data.items():
            # Check if key indicates sensitive data
            if any(sensitive in key.lower() for sensitive in 
                   ['password', 'token', 'secret', 'key', 'credential', 'auth']):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_error_message(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_log_data(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def create_user_friendly_error(self, error: Exception, 
                                 context: Optional[Dict[str, Any]] = None) -> str:
        """Create user-friendly error message from exception.
        
        Args:
            error: Exception that occurred.
            context: Additional context information.
            
        Returns:
            User-friendly error message with actionable guidance.
        """
        context = context or {}
        
        # Map specific errors to user-friendly messages
        if isinstance(error, AuthenticationTimeoutError):
            return self._create_timeout_error_message(error, context)
        elif isinstance(error, AuthenticationError):
            return self._create_auth_error_message(error, context)
        elif isinstance(error, ValidationError):
            return self._create_validation_error_message(error, context)
        elif isinstance(error, SecurityError):
            return self._create_security_error_message(error, context)
        else:
            return self._create_generic_error_message(error, context)
    
    def _create_timeout_error_message(self, error: AuthenticationTimeoutError, 
                                    context: Dict[str, Any]) -> str:
        """Create user-friendly timeout error message."""
        timeout_duration = error.get_detail("timeout_duration", "unknown")
        
        message = f"Authentication timed out after {timeout_duration} seconds.\n\n"
        message += "Possible solutions:\n"
        message += "1. Check your network connection\n"
        message += "2. Try again during off-peak hours\n"
        message += "3. Contact IT support if the problem persists\n"
        
        if context.get("retry_count", 0) > 0:
            message += f"4. This was attempt {context['retry_count']} - consider waiting before retrying"
        
        return message
    
    def _create_auth_error_message(self, error: AuthenticationError, 
                                 context: Dict[str, Any]) -> str:
        """Create user-friendly authentication error message."""
        auth_method = error.get_detail("auth_method", "unknown")
        
        message = "Authentication failed.\n\n"
        
        if auth_method == "midway":
            message += "Midway authentication troubleshooting:\n"
            message += "1. Run 'mwinit -o' manually to check for issues\n"
            message += "2. Ensure you have valid Midway credentials\n"
            message += "3. Check if your credentials have expired\n"
            message += "4. Verify network connectivity to internal systems\n"
        else:
            message += "Authentication troubleshooting:\n"
            message += "1. Verify your credentials are correct\n"
            message += "2. Check if your account is locked or expired\n"
            message += "3. Ensure you have proper permissions\n"
        
        if context.get("last_success"):
            message += f"5. Last successful authentication: {context['last_success']}"
        
        return message
    
    def _create_validation_error_message(self, error: ValidationError, 
                                       context: Dict[str, Any]) -> str:
        """Create user-friendly validation error message."""
        field_name = error.get_detail("field_name", "unknown field")
        validation_rule = error.get_detail("validation_rule", "unknown rule")
        
        message = f"Validation failed for {field_name}.\n\n"
        message += f"Validation rule: {validation_rule}\n"
        message += "Please check your input and try again.\n"
        
        return message
    
    def _create_security_error_message(self, error: SecurityError, 
                                     context: Dict[str, Any]) -> str:
        """Create user-friendly security error message."""
        security_rule = error.get_detail("security_rule", "unknown rule")
        
        message = "Security validation failed.\n\n"
        message += f"Security rule violated: {security_rule}\n"
        message += "This operation cannot be completed for security reasons.\n"
        message += "Please contact your system administrator if you believe this is an error."
        
        return message
    
    def _create_generic_error_message(self, error: Exception, 
                                    context: Dict[str, Any]) -> str:
        """Create user-friendly generic error message."""
        error_type = type(error).__name__
        sanitized_message = self.sanitize_error_message(str(error))
        
        message = f"An error occurred during authentication ({error_type}).\n\n"
        message += f"Error details: {sanitized_message}\n\n"
        message += "Troubleshooting steps:\n"
        message += "1. Try the operation again\n"
        message += "2. Check your network connection\n"
        message += "3. Verify your credentials and permissions\n"
        message += "4. Contact support if the problem persists"
        
        return message
    
    def log_authentication_event(self, event_type: str, details: Dict[str, Any], 
                               level: str = "info") -> None:
        """Log authentication event with proper sanitization.
        
        Args:
            event_type: Type of authentication event.
            details: Event details (will be sanitized).
            level: Log level (debug, info, warning, error).
        """
        sanitized_details = self.sanitize_log_data(details)
        
        log_message = f"Authentication event: {event_type}"
        
        # Get appropriate logger method
        log_method = getattr(logger, level.lower(), logger.info)
        log_method("%s - Details: %s", log_message, sanitized_details)
    
    def validate_retry_logic(self, attempt: int, max_attempts: int, 
                           last_error: Optional[Exception] = None) -> Tuple[bool, str]:
        """Validate retry logic and provide guidance.
        
        Args:
            attempt: Current attempt number (1-based).
            max_attempts: Maximum number of attempts allowed.
            last_error: Last error that occurred.
            
        Returns:
            Tuple of (should_retry, message).
        """
        if attempt >= max_attempts:
            message = f"Maximum retry attempts ({max_attempts}) reached. Stopping retries."
            return False, message
        
        # Check if error type suggests retrying is worthless
        if last_error:
            if isinstance(last_error, SecurityError):
                message = "Security error - retrying will not help."
                return False, message
            elif isinstance(last_error, ValidationError):
                message = "Validation error - retrying with same input will not help."
                return False, message
        
        # Calculate delay suggestion
        delay_seconds = min(2 ** (attempt - 1), 30)  # Exponential backoff, max 30s
        
        message = f"Retry attempt {attempt}/{max_attempts}. Suggested delay: {delay_seconds}s"
        return True, message


class SecureAuthenticationValidator(AuthenticationValidator):
    """Enhanced authentication validator with additional security features.
    
    Extends the base validator with enhanced security measures and
    more comprehensive validation and error handling.
    """
    
    def __init__(self, config: Optional[AuthConfig] = None) -> None:
        """Initialize secure authentication validator.
        
        Args:
            config: Authentication configuration.
        """
        super().__init__(config)
        self._security_level = "enhanced"
        logger.info("SecureAuthenticationValidator initialized with enhanced security")
    
    def validate_authentication_status(self, auth_result: Dict[str, Any]) -> ValidationResult:
        """Validate authentication status with enhanced security checks.
        
        Args:
            auth_result: Authentication result dictionary.
            
        Returns:
            ValidationResult with enhanced validation.
        """
        # Perform base validation
        result = super().validate_authentication_status(auth_result)
        
        # Add enhanced security validations
        security_validation = self._perform_security_validation(auth_result)
        
        # Merge results
        result.errors.extend(security_validation.errors)
        result.warnings.extend(security_validation.warnings)
        result.details.update(security_validation.details)
        result.is_valid = result.is_valid and security_validation.is_valid
        
        return result
    
    def _perform_security_validation(self, auth_result: Dict[str, Any]) -> ValidationResult:
        """Perform enhanced security validation.
        
        Args:
            auth_result: Authentication result to validate.
            
        Returns:
            ValidationResult for security checks.
        """
        errors = []
        warnings = []
        details = {"security_level": self._security_level}
        
        # Check for security indicators
        if auth_result.get("security_level") != "enhanced":
            warnings.append("Authentication not using enhanced security")
        
        # Validate session security
        session_info = auth_result.get("session_info", {})
        if session_info.get("credential_protection") != "enabled":
            warnings.append("Credential protection not enabled")
        
        # Check for suspicious activity indicators
        if auth_result.get("retry_count", 0) > 3:
            warnings.append("High number of authentication retries detected")
            details["retry_count"] = auth_result["retry_count"]
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details=details
        )