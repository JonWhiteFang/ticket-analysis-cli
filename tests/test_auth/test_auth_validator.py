"""Comprehensive tests for authentication validation and error handling.

This module contains unit tests for the AuthenticationValidator and
SecureAuthenticationValidator classes, covering validation logic,
error message sanitization, and secure logging.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch

from ticket_analyzer.auth.auth_validator import (
    AuthenticationValidator,
    SecureAuthenticationValidator,
    ValidationResult,
)
from ticket_analyzer.models.config import AuthConfig
from ticket_analyzer.models.exceptions import (
    AuthenticationError,
    ValidationError,
    SecurityError,
)


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""

    def test_validation_result_creation_minimal(self) -> None:
        """Test ValidationResult creation with minimal parameters."""
        result = ValidationResult(is_valid=True, errors=[])

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.details == {}

    def test_validation_result_creation_complete(self) -> None:
        """Test ValidationResult creation with all parameters."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]
        details = {"field": "value"}

        result = ValidationResult(
            is_valid=False, errors=errors, warnings=warnings, details=details
        )

        assert result.is_valid is False
        assert result.errors == errors
        assert result.warnings == warnings
        assert result.details == details

    def test_validation_result_post_init(self) -> None:
        """Test ValidationResult __post_init__ sets defaults."""
        result = ValidationResult(is_valid=True, errors=[])

        # Should initialize empty lists and dict
        assert isinstance(result.warnings, list)
        assert isinstance(result.details, dict)
        assert len(result.warnings) == 0
        assert len(result.details) == 0


class TestAuthenticationValidator:
    """Test cases for AuthenticationValidator class."""

    @pytest.fixture
    def validator_config(self) -> AuthConfig:
        """Provide test validator configuration."""
        return AuthConfig(
            timeout_seconds=60,
            max_retry_attempts=3,
            session_duration_hours=8,
            auth_method="midway",
        )

    @pytest.fixture
    def validator(self, validator_config: AuthConfig) -> AuthenticationValidator:
        """Provide AuthenticationValidator instance for testing."""
        return AuthenticationValidator(validator_config)

    def test_initialization_with_config(self, validator_config: AuthConfig) -> None:
        """Test validator initialization with configuration."""
        validator = AuthenticationValidator(validator_config)

        assert validator._config == validator_config

    def test_initialization_with_default_config(self) -> None:
        """Test validator initialization with default configuration."""
        validator = AuthenticationValidator()

        assert validator._config is not None
        assert validator._config.timeout_seconds == 60  # Default value

    def test_validate_authentication_status_success(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of successful authentication status."""
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "session_info": {
                "expiry_time": (datetime.now() + timedelta(hours=2)).isoformat(),
                "start_time": datetime.now().isoformat(),
            },
        }

        result = validator.validate_authentication_status(auth_result)

        assert result.is_valid is True
        assert len(result.errors) == 0
        # Check that auth_status is not set to "failed" (it may not be set at all for success)
        assert result.details.get("auth_status") != "failed"

    def test_validate_authentication_status_failure(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of failed authentication status."""
        auth_result = {"authenticated": False, "auth_method": "midway"}

        result = validator.validate_authentication_status(auth_result)

        assert result.is_valid is False
        assert "Authentication failed" in result.errors
        assert result.details["auth_status"] == "failed"

    def test_validate_authentication_status_with_timeout(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation with timeout information."""
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "timeout_occurred": True,
            "timeout_duration": 30,
        }

        result = validator.validate_authentication_status(auth_result)

        assert result.is_valid is True
        assert "Authentication timeout occurred" in result.warnings
        assert result.details["timeout_duration"] == 30

    def test_validate_authentication_status_unknown_method(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation with unknown authentication method."""
        auth_result = {"authenticated": True, "auth_method": "unknown_method"}

        result = validator.validate_authentication_status(auth_result)

        assert result.is_valid is True
        assert any(
            "Unknown authentication method" in warning for warning in result.warnings
        )

    def test_validate_authentication_status_with_session_validation(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation includes session validation."""
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "session_info": {
                "expiry_time": (
                    datetime.now() - timedelta(hours=1)
                ).isoformat(),  # Expired
                "start_time": datetime.now().isoformat(),
            },
        }

        result = validator.validate_authentication_status(auth_result)

        assert result.is_valid is False
        assert "Session has expired" in result.errors
        assert result.details.get("session_expired") is True

    def test_validate_authentication_status_handles_exceptions(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation handles exceptions gracefully."""
        # Invalid auth_result that will cause an exception
        auth_result = None

        result = validator.validate_authentication_status(auth_result)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "Validation error" in result.errors[0]

    def test_validate_configuration_valid_config(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of valid configuration."""
        config = AuthConfig(
            timeout_seconds=60,
            max_retry_attempts=3,
            session_duration_hours=8,
            auth_method="midway",
            require_auth=True,
        )

        result = validator.validate_configuration(config)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.details["config_valid"] is True

    def test_validate_configuration_warnings(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation generates appropriate warnings."""
        config = AuthConfig(
            timeout_seconds=5,  # Very short
            max_retry_attempts=10,  # High retry count
            session_duration_hours=24,  # Long session
            auth_method="midway",
        )

        result = validator.validate_configuration(config)

        assert result.is_valid is True
        assert any("Very short timeout" in warning for warning in result.warnings)
        assert any("High retry count" in warning for warning in result.warnings)
        assert any("Long session duration" in warning for warning in result.warnings)

    def test_validate_configuration_invalid_config(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of invalid configuration."""
        config = AuthConfig(
            timeout_seconds=60,
            auth_method="none",
            require_auth=True,  # Conflicting settings
        )

        result = validator.validate_configuration(config)

        assert result.is_valid is False
        assert "Authentication required but method set to 'none'" in result.errors

    def test_validate_configuration_handles_validation_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test configuration validation handles ValueError from config.validate()."""
        config = AuthConfig(timeout_seconds=-1)  # Invalid timeout

        result = validator.validate_configuration(config)

        assert result.is_valid is False
        assert "Configuration validation failed" in result.errors[0]
        assert result.details["config_valid"] is False

    def test_validate_session_info_valid_session(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of valid session information."""
        session_info = {
            "expiry_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
        }

        result = validator._validate_session_info(session_info)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_session_info_expired_session(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of expired session."""
        session_info = {
            "expiry_time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "start_time": (datetime.now() - timedelta(hours=2)).isoformat(),
        }

        result = validator._validate_session_info(session_info)

        assert result.is_valid is False
        assert "Session has expired" in result.errors
        assert result.details["session_expired"] is True

    def test_validate_session_info_near_expiry(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of session near expiry."""
        session_info = {
            "expiry_time": (datetime.now() + timedelta(minutes=10)).isoformat(),
            "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
        }

        result = validator._validate_session_info(session_info)

        assert result.is_valid is True
        assert "Session expires soon" in result.warnings
        assert result.details["session_near_expiry"] is True

    def test_validate_session_info_old_session(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation of very old session."""
        session_info = {
            "expiry_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "start_time": (
                datetime.now() - timedelta(hours=25)
            ).isoformat(),  # 25 hours old
        }

        result = validator._validate_session_info(session_info)

        assert result.is_valid is True
        assert "Session is very old" in result.warnings
        assert result.details["session_age_hours"] > 24

    def test_validate_session_info_invalid_date_format(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test validation with invalid date formats."""
        session_info = {
            "expiry_time": "invalid-date-format",
            "start_time": "also-invalid",
        }

        result = validator._validate_session_info(session_info)

        assert result.is_valid is True  # Warnings, not errors
        assert any(
            "Invalid session expiry format" in warning for warning in result.warnings
        )
        assert any(
            "Invalid session start time format" in warning
            for warning in result.warnings
        )

    def test_sanitize_error_message_removes_sensitive_patterns(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test error message sanitization removes sensitive patterns."""
        sensitive_message = """
        Authentication failed with password: secret123
        Token: abc123def456ghi789
        Secret: my_secret_key
        Credential: user:password
        Base64 token: YWJjZGVmZ2hpams=
        mwinit -o --user testuser
        """

        sanitized = validator.sanitize_error_message(sensitive_message)

        assert "secret123" not in sanitized
        assert "abc123def456ghi789" not in sanitized
        assert "my_secret_key" not in sanitized
        assert "user:password" not in sanitized
        assert "YWJjZGVmZ2hpams=" not in sanitized
        assert "mwinit -o" not in sanitized  # The mwinit command should be sanitized

        assert "[PASSWORD_REDACTED]" in sanitized
        assert "[TOKEN_REDACTED]" in sanitized
        assert "[SECRET_REDACTED]" in sanitized
        assert "[CREDENTIAL_REDACTED]" in sanitized
        assert "[ARGS_REDACTED]" in sanitized

    def test_sanitize_error_message_preserves_safe_content(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test error message sanitization preserves safe content."""
        safe_message = "Authentication failed. Please check your network connection."

        sanitized = validator.sanitize_error_message(safe_message)

        assert sanitized == safe_message

    def test_sanitize_log_data_removes_sensitive_fields(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test log data sanitization removes sensitive fields."""
        log_data = {
            "username": "testuser",
            "password": "secret123",
            "token": "abc123",
            "auth_header": "Bearer xyz789",
            "message": "Authentication successful",
            "nested": {"credential": "nested_secret", "safe_field": "safe_value"},
        }

        sanitized = validator.sanitize_log_data(log_data)

        assert sanitized["username"] == "testuser"  # Safe field preserved
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["auth_header"] == "[REDACTED]"
        assert sanitized["message"] == "Authentication successful"
        assert sanitized["nested"]["credential"] == "[REDACTED]"
        assert sanitized["nested"]["safe_field"] == "safe_value"

    def test_sanitize_log_data_handles_string_values(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test log data sanitization handles string values with sensitive patterns."""
        log_data = {
            "error_message": "Failed with token: abc123def456",
            "debug_info": "Safe debug information",
        }

        sanitized = validator.sanitize_log_data(log_data)

        assert "abc123def456" not in sanitized["error_message"]
        assert "[TOKEN_REDACTED]" in sanitized["error_message"]
        assert sanitized["debug_info"] == "Safe debug information"

    def test_create_user_friendly_error_timeout_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test creation of user-friendly timeout error message."""
        error = AuthenticationError("Timeout")
        error.error_code = "AUTH_TIMEOUT"
        error.add_detail("timeout_duration", 30)

        context = {"retry_count": 2}

        message = validator.create_user_friendly_error(error, context)

        assert "Authentication timed out after 30 seconds" in message
        assert "Possible solutions:" in message
        assert "Check your network connection" in message
        assert "attempt 2" in message

    def test_create_user_friendly_error_auth_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test creation of user-friendly authentication error message."""
        error = AuthenticationError("Auth failed")
        error.add_detail("auth_method", "midway")

        context = {"last_success": "2024-01-01 10:00:00"}

        message = validator.create_user_friendly_error(error, context)

        assert "Authentication failed" in message
        assert "Midway authentication troubleshooting:" in message
        assert "Run 'mwinit -o' manually" in message
        assert "Last successful authentication: 2024-01-01 10:00:00" in message

    def test_create_user_friendly_error_validation_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test creation of user-friendly validation error message."""
        error = ValidationError("Invalid input")
        error.add_detail("field_name", "username")
        error.add_detail("validation_rule", "alphanumeric_only")

        message = validator.create_user_friendly_error(error)

        assert "Validation failed for username" in message
        assert "Validation rule: alphanumeric_only" in message
        assert "Please check your input" in message

    def test_create_user_friendly_error_security_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test creation of user-friendly security error message."""
        error = SecurityError("Security violation")
        error.add_detail("security_rule", "credential_protection")

        message = validator.create_user_friendly_error(error)

        assert "Security validation failed" in message
        assert "Security rule violated: credential_protection" in message
        assert "contact your system administrator" in message

    def test_create_user_friendly_error_generic_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test creation of user-friendly generic error message."""
        error = Exception("Generic error with token: abc123")
        # Add error_code attribute for testing
        error.error_code = None

        message = validator.create_user_friendly_error(error)

        assert "An error occurred during authentication (Exception)" in message
        assert "abc123" not in message  # Should be sanitized
        assert "[TOKEN_REDACTED]" in message
        assert "Troubleshooting steps:" in message

    @patch("ticket_analyzer.auth.auth_validator.logger")
    def test_log_authentication_event(
        self, mock_logger: Mock, validator: AuthenticationValidator
    ) -> None:
        """Test authentication event logging with sanitization."""
        details = {"username": "testuser", "password": "secret123", "result": "success"}

        validator.log_authentication_event("login_attempt", details, "info")

        # Verify logger was called
        mock_logger.info.assert_called_once()

        # Get the logged message and details
        call_args = mock_logger.info.call_args
        format_string = call_args[0][0]
        logged_message = call_args[0][1]
        logged_details = call_args[0][2]

        assert format_string == "%s - Details: %s"
        assert "Authentication event: login_attempt" in logged_message
        assert logged_details["username"] == "testuser"
        assert logged_details["password"] == "[REDACTED]"
        assert logged_details["result"] == "success"

    @patch("ticket_analyzer.auth.auth_validator.logger")
    def test_log_authentication_event_different_levels(
        self, mock_logger: Mock, validator: AuthenticationValidator
    ) -> None:
        """Test authentication event logging with different log levels."""
        details = {"event": "test"}

        # Test different log levels
        validator.log_authentication_event("test_event", details, "debug")
        mock_logger.debug.assert_called_once()

        validator.log_authentication_event("test_event", details, "warning")
        mock_logger.warning.assert_called_once()

        validator.log_authentication_event("test_event", details, "error")
        mock_logger.error.assert_called_once()

        # Test invalid level defaults to info (should not raise exception)
        try:
            validator.log_authentication_event("test_event", details, "invalid_level")
            # If we get here, the method handled the invalid level gracefully
            assert True
        except Exception:
            # Should not raise an exception
            assert False, "Should handle invalid log levels gracefully"

    def test_validate_retry_logic_should_retry(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test retry logic validation when retry should continue."""
        should_retry, message = validator.validate_retry_logic(1, 3)

        assert should_retry is True
        assert "Retry attempt 1/3" in message
        assert "Suggested delay: 1s" in message

    def test_validate_retry_logic_max_attempts_reached(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test retry logic validation when max attempts reached."""
        should_retry, message = validator.validate_retry_logic(3, 3)

        assert should_retry is False
        assert "Maximum retry attempts (3) reached" in message

    def test_validate_retry_logic_security_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test retry logic validation with security error."""
        security_error = SecurityError("Security violation")

        should_retry, message = validator.validate_retry_logic(1, 3, security_error)

        assert should_retry is False
        assert "Security error - retrying will not help" in message

    def test_validate_retry_logic_validation_error(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test retry logic validation with validation error."""
        validation_error = ValidationError("Invalid input")

        should_retry, message = validator.validate_retry_logic(1, 3, validation_error)

        assert should_retry is False
        assert "Validation error - retrying with same input will not help" in message

    def test_validate_retry_logic_exponential_backoff(
        self, validator: AuthenticationValidator
    ) -> None:
        """Test retry logic calculates exponential backoff correctly."""
        # Test different attempt numbers
        _, message1 = validator.validate_retry_logic(1, 5)
        assert "Suggested delay: 1s" in message1

        _, message2 = validator.validate_retry_logic(2, 5)
        assert "Suggested delay: 2s" in message2

        _, message3 = validator.validate_retry_logic(3, 5)
        assert "Suggested delay: 4s" in message3

        _, message4 = validator.validate_retry_logic(4, 5)
        assert "Suggested delay: 8s" in message4

        # Test max delay cap
        _, message5 = validator.validate_retry_logic(10, 15)
        assert "Suggested delay: 30s" in message5  # Capped at 30s


class TestSecureAuthenticationValidator:
    """Test cases for SecureAuthenticationValidator class."""

    @pytest.fixture
    def secure_validator(self) -> SecureAuthenticationValidator:
        """Provide SecureAuthenticationValidator instance for testing."""
        config = AuthConfig(timeout_seconds=60, auth_method="midway")
        return SecureAuthenticationValidator(config)

    def test_initialization_sets_security_level(
        self, secure_validator: SecureAuthenticationValidator
    ) -> None:
        """Test initialization sets enhanced security level."""
        assert secure_validator._security_level == "enhanced"

    def test_validate_authentication_status_includes_security_validation(
        self, secure_validator: SecureAuthenticationValidator
    ) -> None:
        """Test validation includes enhanced security checks."""
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "security_level": "standard",  # Not enhanced
            "session_info": {"credential_protection": "disabled"},
        }

        result = secure_validator.validate_authentication_status(auth_result)

        assert result.is_valid is True  # Base validation passes
        assert "Authentication not using enhanced security" in result.warnings
        assert "Credential protection not enabled" in result.warnings
        assert result.details["security_level"] == "enhanced"

    def test_validate_authentication_status_high_retry_count_warning(
        self, secure_validator: SecureAuthenticationValidator
    ) -> None:
        """Test validation warns about high retry counts."""
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "retry_count": 5,  # High retry count
        }

        result = secure_validator.validate_authentication_status(auth_result)

        assert result.is_valid is True
        assert "High number of authentication retries detected" in result.warnings
        assert result.details["retry_count"] == 5

    def test_perform_security_validation_enhanced_security(
        self, secure_validator: SecureAuthenticationValidator
    ) -> None:
        """Test security validation with enhanced security features."""
        auth_result = {
            "security_level": "enhanced",
            "session_info": {"credential_protection": "enabled"},
            "retry_count": 1,
        }

        result = secure_validator._perform_security_validation(auth_result)

        assert result.is_valid is True
        assert len(result.warnings) == 0
        assert result.details["security_level"] == "enhanced"

    def test_perform_security_validation_security_warnings(
        self, secure_validator: SecureAuthenticationValidator
    ) -> None:
        """Test security validation generates appropriate warnings."""
        auth_result = {
            "security_level": "basic",
            "session_info": {"credential_protection": "disabled"},
            "retry_count": 4,
        }

        result = secure_validator._perform_security_validation(auth_result)

        assert result.is_valid is True
        assert len(result.warnings) == 3  # Three security warnings
        assert "Authentication not using enhanced security" in result.warnings
        assert "Credential protection not enabled" in result.warnings
        assert "High number of authentication retries detected" in result.warnings


class TestValidationIntegration:
    """Integration tests for authentication validation."""

    @pytest.fixture
    def integration_validator(self) -> AuthenticationValidator:
        """Provide validator for integration testing."""
        config = AuthConfig(
            timeout_seconds=30,
            max_retry_attempts=2,
            session_duration_hours=4,
            auth_method="midway",
        )
        return AuthenticationValidator(config)

    def test_complete_validation_flow_success(
        self, integration_validator: AuthenticationValidator
    ) -> None:
        """Test complete validation flow with successful authentication."""
        # Simulate successful authentication result
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "session_info": {
                "expiry_time": (datetime.now() + timedelta(hours=3)).isoformat(),
                "start_time": (datetime.now() - timedelta(minutes=30)).isoformat(),
            },
            "retry_count": 1,
        }

        # Validate authentication status
        status_result = integration_validator.validate_authentication_status(
            auth_result
        )
        assert status_result.is_valid is True

        # Validate configuration
        config_result = integration_validator.validate_configuration(
            integration_validator._config
        )
        assert config_result.is_valid is True

        # Test retry logic
        should_retry, retry_message = integration_validator.validate_retry_logic(1, 2)
        assert should_retry is True

    def test_complete_validation_flow_with_issues(
        self, integration_validator: AuthenticationValidator
    ) -> None:
        """Test complete validation flow with various issues."""
        # Simulate authentication result with issues
        auth_result = {
            "authenticated": False,  # Failed authentication
            "auth_method": "unknown_method",
            "timeout_occurred": True,
            "timeout_duration": 30,
            "session_info": {
                "expiry_time": (
                    datetime.now() - timedelta(hours=1)
                ).isoformat(),  # Expired
                "start_time": (datetime.now() - timedelta(hours=2)).isoformat(),
            },
            "retry_count": 3,
        }

        # Validate authentication status
        status_result = integration_validator.validate_authentication_status(
            auth_result
        )
        assert status_result.is_valid is False
        assert "Authentication failed" in status_result.errors
        assert "Session has expired" in status_result.errors
        assert "Authentication timeout occurred" in status_result.warnings
        assert any(
            "Unknown authentication method" in warning
            for warning in status_result.warnings
        )

    def test_error_handling_and_sanitization_integration(
        self, integration_validator: AuthenticationValidator
    ) -> None:
        """Test error handling and sanitization integration."""
        # Create error with sensitive information
        error = AuthenticationError("Authentication failed with password: secret123")
        error.add_detail("auth_method", "midway")

        # Create user-friendly error message
        friendly_message = integration_validator.create_user_friendly_error(error)

        # Verify sanitization
        assert "secret123" not in friendly_message
        assert "Authentication failed" in friendly_message
        assert "Midway authentication troubleshooting:" in friendly_message

    @patch("ticket_analyzer.auth.auth_validator.logger")
    def test_logging_integration(
        self, mock_logger: Mock, integration_validator: AuthenticationValidator
    ) -> None:
        """Test logging integration with sanitization."""
        # Log authentication event with sensitive data
        details = {
            "username": "testuser",
            "password": "secret123",
            "token": "abc123def456",
            "result": "failed",
            "error": "Invalid credentials",
        }

        integration_validator.log_authentication_event(
            "login_failed", details, "warning"
        )

        # Verify logging was called with sanitized data
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        logged_details = call_args[0][2]  # Third argument is the sanitized details

        assert logged_details["username"] == "testuser"
        assert logged_details["password"] == "[REDACTED]"
        assert logged_details["token"] == "[REDACTED]"
        assert logged_details["result"] == "failed"
        assert logged_details["error"] == "Invalid credentials"

    def test_retry_logic_integration_with_different_errors(
        self, integration_validator: AuthenticationValidator
    ) -> None:
        """Test retry logic integration with different error types."""
        # Test with recoverable error
        auth_error = AuthenticationError("Network timeout")
        should_retry, message = integration_validator.validate_retry_logic(
            1, 3, auth_error
        )
        assert should_retry is True

        # Test with security error (non-recoverable)
        security_error = SecurityError("Invalid credentials")
        should_retry, message = integration_validator.validate_retry_logic(
            1, 3, security_error
        )
        assert should_retry is False

        # Test with validation error (non-recoverable)
        validation_error = ValidationError("Invalid input format")
        should_retry, message = integration_validator.validate_retry_logic(
            1, 3, validation_error
        )
        assert should_retry is False

    def test_secure_validator_integration(self) -> None:
        """Test secure validator integration with enhanced features."""
        config = AuthConfig(timeout_seconds=60, auth_method="midway")
        secure_validator = SecureAuthenticationValidator(config)

        # Test with security-aware authentication result
        auth_result = {
            "authenticated": True,
            "auth_method": "midway",
            "security_level": "enhanced",
            "session_info": {
                "credential_protection": "enabled",
                "expiry_time": (datetime.now() + timedelta(hours=2)).isoformat(),
                "start_time": datetime.now().isoformat(),
            },
            "retry_count": 1,
        }

        result = secure_validator.validate_authentication_status(auth_result)

        assert result.is_valid is True
        assert result.details["security_level"] == "enhanced"
        assert len(result.warnings) == 0  # No security warnings
