"""Comprehensive tests for custom exception hierarchy.

This module contains unit tests for all custom exceptions including
the base TicketAnalysisError and all derived exception classes,
covering exception instantiation, inheritance, error message formatting,
and context information handling.
"""

import pytest
from typing import Dict, Any, Optional

from ticket_analyzer.models.exceptions import (
    TicketAnalysisError, AuthenticationError, ConfigurationError,
    DataRetrievalError, AnalysisError, ValidationError, MCPError,
    MCPConnectionError, MCPTimeoutError, MCPAuthenticationError,
    MCPResponseError, CircuitBreakerOpenError, DataProcessingError,
    ReportGenerationError, SecurityError, CLIError, FileOperationError,
    create_error_context, wrap_exception
)


class TestTicketAnalysisError:
    """Test cases for base TicketAnalysisError class."""
    
    def test_basic_initialization(self) -> None:
        """Test basic exception initialization with message only."""
        error = TicketAnalysisError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}
        assert error.error_code is None
    
    def test_initialization_with_details(self) -> None:
        """Test exception initialization with details."""
        details = {"operation": "test", "value": 42}
        error = TicketAnalysisError("Test error", details=details)
        
        assert error.message == "Test error"
        assert error.details == details
        assert error.error_code is None
    
    def test_initialization_with_error_code(self) -> None:
        """Test exception initialization with error code."""
        error = TicketAnalysisError("Test error", error_code="TEST_ERROR")
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
    
    def test_initialization_with_all_parameters(self) -> None:
        """Test exception initialization with all parameters."""
        details = {"context": "test"}
        error = TicketAnalysisError(
            "Complete error",
            details=details,
            error_code="COMPLETE_ERROR"
        )
        
        assert error.message == "Complete error"
        assert error.details == details
        assert error.error_code == "COMPLETE_ERROR"
    
    def test_str_representation_with_details(self) -> None:
        """Test string representation includes details when present."""
        details = {"operation": "test", "count": 5}
        error = TicketAnalysisError("Error with details", details=details)
        
        str_repr = str(error)
        assert "Error with details" in str_repr
        assert "Details:" in str_repr
        assert "operation" in str_repr
        assert "count" in str_repr
    
    def test_str_representation_without_details(self) -> None:
        """Test string representation without details."""
        error = TicketAnalysisError("Simple error")
        
        str_repr = str(error)
        assert str_repr == "Simple error"
        assert "Details:" not in str_repr
    
    def test_repr_representation(self) -> None:
        """Test detailed repr representation."""
        details = {"key": "value"}
        error = TicketAnalysisError("Test", details=details, error_code="TEST")
        
        repr_str = repr(error)
        assert "TicketAnalysisError" in repr_str
        assert "message='Test'" in repr_str
        assert "details={'key': 'value'}" in repr_str
        assert "error_code='TEST'" in repr_str
    
    def test_add_detail(self) -> None:
        """Test adding detail information to exception."""
        error = TicketAnalysisError("Test error")
        
        error.add_detail("operation", "test_op")
        error.add_detail("timestamp", "2024-01-01")
        
        assert error.details["operation"] == "test_op"
        assert error.details["timestamp"] == "2024-01-01"
        assert len(error.details) == 2
    
    def test_get_detail_existing(self) -> None:
        """Test getting existing detail value."""
        details = {"operation": "test", "count": 42}
        error = TicketAnalysisError("Test", details=details)
        
        assert error.get_detail("operation") == "test"
        assert error.get_detail("count") == 42
    
    def test_get_detail_nonexistent_with_default(self) -> None:
        """Test getting nonexistent detail with default value."""
        error = TicketAnalysisError("Test")
        
        assert error.get_detail("nonexistent", "default") == "default"
        assert error.get_detail("missing", 0) == 0
    
    def test_get_detail_nonexistent_without_default(self) -> None:
        """Test getting nonexistent detail without default value."""
        error = TicketAnalysisError("Test")
        
        assert error.get_detail("nonexistent") is None
    
    def test_inheritance_from_exception(self) -> None:
        """Test that TicketAnalysisError inherits from Exception."""
        error = TicketAnalysisError("Test")
        
        assert isinstance(error, Exception)
        assert isinstance(error, TicketAnalysisError)
    
    def test_exception_raising_and_catching(self) -> None:
        """Test raising and catching the exception."""
        with pytest.raises(TicketAnalysisError) as exc_info:
            raise TicketAnalysisError("Test exception")
        
        assert str(exc_info.value) == "Test exception"
        assert exc_info.value.message == "Test exception"


class TestAuthenticationError:
    """Test cases for AuthenticationError class."""
    
    def test_inheritance(self) -> None:
        """Test that AuthenticationError inherits from TicketAnalysisError."""
        error = AuthenticationError("Auth failed")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, AuthenticationError)
    
    def test_initialization_with_auth_method(self) -> None:
        """Test initialization with auth_method parameter."""
        error = AuthenticationError("Auth failed", auth_method="midway")
        
        assert error.message == "Auth failed"
        assert error.error_code == "AUTH_ERROR"
        assert error.get_detail("auth_method") == "midway"
    
    def test_initialization_with_details_and_auth_method(self) -> None:
        """Test initialization with both details and auth_method."""
        details = {"timeout": 60}
        error = AuthenticationError(
            "Timeout error",
            details=details,
            auth_method="kerberos"
        )
        
        assert error.message == "Timeout error"
        assert error.error_code == "AUTH_ERROR"
        assert error.get_detail("timeout") == 60
        assert error.get_detail("auth_method") == "kerberos"
    
    def test_default_error_code(self) -> None:
        """Test that default error code is set."""
        error = AuthenticationError("Test")
        assert error.error_code == "AUTH_ERROR"


class TestConfigurationError:
    """Test cases for ConfigurationError class."""
    
    def test_inheritance(self) -> None:
        """Test that ConfigurationError inherits from TicketAnalysisError."""
        error = ConfigurationError("Config error")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, ConfigurationError)
    
    def test_initialization_with_config_file(self) -> None:
        """Test initialization with config_file parameter."""
        error = ConfigurationError("Invalid config", config_file="/path/config.json")
        
        assert error.message == "Invalid config"
        assert error.error_code == "CONFIG_ERROR"
        assert error.get_detail("config_file") == "/path/config.json"
    
    def test_initialization_with_config_key(self) -> None:
        """Test initialization with config_key parameter."""
        error = ConfigurationError("Invalid key", config_key="database.host")
        
        assert error.message == "Invalid key"
        assert error.get_detail("config_key") == "database.host"
    
    def test_initialization_with_all_config_params(self) -> None:
        """Test initialization with all configuration parameters."""
        error = ConfigurationError(
            "Config error",
            config_file="/etc/app.conf",
            config_key="auth.timeout"
        )
        
        assert error.get_detail("config_file") == "/etc/app.conf"
        assert error.get_detail("config_key") == "auth.timeout"


class TestDataRetrievalError:
    """Test cases for DataRetrievalError class."""
    
    def test_inheritance(self) -> None:
        """Test that DataRetrievalError inherits from TicketAnalysisError."""
        error = DataRetrievalError("Data error")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, DataRetrievalError)
    
    def test_initialization_with_service_and_operation(self) -> None:
        """Test initialization with service and operation parameters."""
        error = DataRetrievalError(
            "API failed",
            service="MCP",
            operation="search_tickets"
        )
        
        assert error.message == "API failed"
        assert error.error_code == "DATA_ERROR"
        assert error.get_detail("service") == "MCP"
        assert error.get_detail("operation") == "search_tickets"


class TestAnalysisError:
    """Test cases for AnalysisError class."""
    
    def test_inheritance(self) -> None:
        """Test that AnalysisError inherits from TicketAnalysisError."""
        error = AnalysisError("Analysis failed")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, AnalysisError)
    
    def test_initialization_with_analysis_params(self) -> None:
        """Test initialization with analysis-specific parameters."""
        error = AnalysisError(
            "Calculation failed",
            analysis_type="resolution_time",
            data_size=1000
        )
        
        assert error.message == "Calculation failed"
        assert error.error_code == "ANALYSIS_ERROR"
        assert error.get_detail("analysis_type") == "resolution_time"
        assert error.get_detail("data_size") == 1000


class TestValidationError:
    """Test cases for ValidationError class."""
    
    def test_inheritance(self) -> None:
        """Test that ValidationError inherits from TicketAnalysisError."""
        error = ValidationError("Validation failed")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, ValidationError)
    
    def test_initialization_with_validation_params(self) -> None:
        """Test initialization with validation-specific parameters."""
        error = ValidationError(
            "Invalid field",
            field_name="email",
            validation_rule="email_format"
        )
        
        assert error.message == "Invalid field"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.get_detail("field_name") == "email"
        assert error.get_detail("validation_rule") == "email_format"


class TestMCPError:
    """Test cases for MCPError class."""
    
    def test_inheritance(self) -> None:
        """Test that MCPError inherits from DataRetrievalError."""
        error = MCPError("MCP failed")
        
        assert isinstance(error, DataRetrievalError)
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, MCPError)
    
    def test_initialization_with_mcp_method(self) -> None:
        """Test initialization with mcp_method parameter."""
        error = MCPError("Request failed", mcp_method="search")
        
        assert error.message == "Request failed"
        assert error.error_code == "MCP_ERROR"
        assert error.get_detail("service") == "MCP"
        assert error.get_detail("operation") == "search"  # mcp_method becomes operation
    
    def test_default_service_setting(self) -> None:
        """Test that service is automatically set to MCP."""
        error = MCPError("Test error")
        assert error.get_detail("service") == "MCP"


class TestMCPConnectionError:
    """Test cases for MCPConnectionError class."""
    
    def test_inheritance(self) -> None:
        """Test that MCPConnectionError inherits from MCPError."""
        error = MCPConnectionError("Connection failed")
        
        assert isinstance(error, MCPError)
        assert isinstance(error, DataRetrievalError)
        assert isinstance(error, MCPConnectionError)
    
    def test_initialization_with_server_command(self) -> None:
        """Test initialization with server_command parameter."""
        error = MCPConnectionError(
            "Server start failed",
            server_command="node server.js"
        )
        
        assert error.message == "Server start failed"
        assert error.error_code == "MCP_CONNECTION_ERROR"
        assert error.get_detail("server_command") == "node server.js"
    
    def test_default_operation_setting(self) -> None:
        """Test that operation is set to 'connect'."""
        error = MCPConnectionError("Test")
        assert error.get_detail("operation") == "connect"


class TestMCPTimeoutError:
    """Test cases for MCPTimeoutError class."""
    
    def test_inheritance(self) -> None:
        """Test that MCPTimeoutError inherits from MCPError."""
        error = MCPTimeoutError("Timeout")
        
        assert isinstance(error, MCPError)
        assert isinstance(error, MCPTimeoutError)
    
    def test_initialization_with_timeout_duration(self) -> None:
        """Test initialization with timeout_duration parameter."""
        error = MCPTimeoutError("Request timeout", timeout_duration=30.5)
        
        assert error.message == "Request timeout"
        assert error.error_code == "MCP_TIMEOUT_ERROR"
        assert error.get_detail("timeout_duration") == 30.5
    
    def test_default_operation_setting(self) -> None:
        """Test that operation is set to 'timeout'."""
        error = MCPTimeoutError("Test")
        assert error.get_detail("operation") == "timeout"


class TestMCPAuthenticationError:
    """Test cases for MCPAuthenticationError class."""
    
    def test_inheritance(self) -> None:
        """Test that MCPAuthenticationError inherits from MCPError."""
        error = MCPAuthenticationError("Auth failed")
        
        assert isinstance(error, MCPError)
        assert isinstance(error, MCPAuthenticationError)
    
    def test_default_values(self) -> None:
        """Test default error code and operation values."""
        error = MCPAuthenticationError("Auth failed")
        
        assert error.error_code == "MCP_AUTH_ERROR"
        assert error.get_detail("operation") == "authenticate"


class TestMCPResponseError:
    """Test cases for MCPResponseError class."""
    
    def test_inheritance(self) -> None:
        """Test that MCPResponseError inherits from MCPError."""
        error = MCPResponseError("Invalid response")
        
        assert isinstance(error, MCPError)
        assert isinstance(error, MCPResponseError)
    
    def test_initialization_with_response_data(self) -> None:
        """Test initialization with response_data parameter."""
        response_data = {"error": "invalid_format", "code": 400}
        error = MCPResponseError("Bad response", response_data=response_data)
        
        assert error.message == "Bad response"
        assert error.error_code == "MCP_RESPONSE_ERROR"
        assert error.get_detail("response_data") == response_data
    
    def test_default_operation_setting(self) -> None:
        """Test that operation is set to 'parse_response'."""
        error = MCPResponseError("Test")
        assert error.get_detail("operation") == "parse_response"


class TestCircuitBreakerOpenError:
    """Test cases for CircuitBreakerOpenError class."""
    
    def test_inheritance(self) -> None:
        """Test that CircuitBreakerOpenError inherits from DataRetrievalError."""
        error = CircuitBreakerOpenError()
        
        assert isinstance(error, DataRetrievalError)
        assert isinstance(error, CircuitBreakerOpenError)
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = CircuitBreakerOpenError()
        
        assert error.message == "Circuit breaker is open"
        assert error.error_code == "CIRCUIT_BREAKER_OPEN"
    
    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = CircuitBreakerOpenError("Custom message")
        
        assert error.message == "Custom message"
    
    def test_initialization_with_failure_count(self) -> None:
        """Test initialization with failure_count parameter."""
        error = CircuitBreakerOpenError(failure_count=5)
        
        assert error.get_detail("failure_count") == 5
        assert error.get_detail("service") == "circuit_breaker"
        assert error.get_detail("operation") == "open"


class TestDataProcessingError:
    """Test cases for DataProcessingError class."""
    
    def test_inheritance(self) -> None:
        """Test that DataProcessingError inherits from AnalysisError."""
        error = DataProcessingError("Processing failed")
        
        assert isinstance(error, AnalysisError)
        assert isinstance(error, DataProcessingError)
    
    def test_initialization_with_processing_stage(self) -> None:
        """Test initialization with processing_stage parameter."""
        error = DataProcessingError("Stage failed", processing_stage="validation")
        
        assert error.message == "Stage failed"
        assert error.error_code == "DATA_PROCESSING_ERROR"
        assert error.get_detail("processing_stage") == "validation"
        assert error.get_detail("analysis_type") == "data_processing"


class TestReportGenerationError:
    """Test cases for ReportGenerationError class."""
    
    def test_inheritance(self) -> None:
        """Test that ReportGenerationError inherits from TicketAnalysisError."""
        error = ReportGenerationError("Report failed")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, ReportGenerationError)
    
    def test_initialization_with_report_params(self) -> None:
        """Test initialization with report-specific parameters."""
        error = ReportGenerationError(
            "Template error",
            report_format="html",
            template_name="custom.html"
        )
        
        assert error.message == "Template error"
        assert error.error_code == "REPORT_ERROR"
        assert error.get_detail("report_format") == "html"
        assert error.get_detail("template_name") == "custom.html"


class TestSecurityError:
    """Test cases for SecurityError class."""
    
    def test_inheritance(self) -> None:
        """Test that SecurityError inherits from TicketAnalysisError."""
        error = SecurityError("Security violation")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, SecurityError)
    
    def test_initialization_with_security_rule(self) -> None:
        """Test initialization with security_rule parameter."""
        error = SecurityError("Access denied", security_rule="admin_only")
        
        assert error.message == "Access denied"
        assert error.error_code == "SECURITY_ERROR"
        assert error.get_detail("security_rule") == "admin_only"


class TestCLIError:
    """Test cases for CLIError class."""
    
    def test_inheritance(self) -> None:
        """Test that CLIError inherits from TicketAnalysisError."""
        error = CLIError("CLI failed")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, CLIError)
    
    def test_initialization_with_cli_params(self) -> None:
        """Test initialization with CLI-specific parameters."""
        error = CLIError("Command failed", command="analyze", exit_code=2)
        
        assert error.message == "Command failed"
        assert error.error_code == "CLI_ERROR"
        assert error.get_detail("command") == "analyze"
        assert error.get_detail("exit_code") == 2
    
    def test_default_exit_code(self) -> None:
        """Test default exit code is 1."""
        error = CLIError("Test")
        assert error.get_detail("exit_code") == 1


class TestFileOperationError:
    """Test cases for FileOperationError class."""
    
    def test_inheritance(self) -> None:
        """Test that FileOperationError inherits from TicketAnalysisError."""
        error = FileOperationError("File error")
        
        assert isinstance(error, TicketAnalysisError)
        assert isinstance(error, FileOperationError)
    
    def test_initialization_with_file_params(self) -> None:
        """Test initialization with file-specific parameters."""
        error = FileOperationError(
            "Read failed",
            file_path="/tmp/test.txt",
            operation="read"
        )
        
        assert error.message == "Read failed"
        assert error.error_code == "FILE_ERROR"
        assert error.get_detail("file_path") == "/tmp/test.txt"
        assert error.get_detail("operation") == "read"


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_create_error_context(self) -> None:
        """Test create_error_context function."""
        context = create_error_context("test_operation", user="testuser", count=5)
        
        expected = {
            "operation": "test_operation",
            "user": "testuser",
            "count": 5
        }
        
        assert context == expected
    
    def test_create_error_context_operation_only(self) -> None:
        """Test create_error_context with operation only."""
        context = create_error_context("simple_op")
        
        assert context == {"operation": "simple_op"}
    
    def test_wrap_exception_default_class(self) -> None:
        """Test wrap_exception with default exception class."""
        original = ValueError("Original error")
        
        wrapped = wrap_exception(original, "Wrapped error", user="test")
        
        assert isinstance(wrapped, TicketAnalysisError)
        assert wrapped.message == "Wrapped error"
        assert wrapped.get_detail("original_exception") == "Original error"
        assert wrapped.get_detail("original_type") == "ValueError"
        assert wrapped.get_detail("user") == "test"
        assert wrapped.get_detail("operation") == "exception_wrap"
    
    def test_wrap_exception_custom_class(self) -> None:
        """Test wrap_exception with custom exception class."""
        original = KeyError("Missing key")
        
        wrapped = wrap_exception(
            original,
            "Config error",
            error_class=ConfigurationError,
            config_file="test.json"
        )
        
        assert isinstance(wrapped, ConfigurationError)
        assert wrapped.message == "Config error"
        assert wrapped.get_detail("original_exception") == "Missing key"
        assert wrapped.get_detail("original_type") == "KeyError"
        assert wrapped.get_detail("config_file") == "test.json"
    
    def test_wrap_exception_preserves_context(self) -> None:
        """Test that wrap_exception preserves all context information."""
        original = RuntimeError("Runtime issue")
        
        wrapped = wrap_exception(
            original,
            "Wrapped runtime error",
            operation="test",
            timestamp="2024-01-01",
            severity="high"
        )
        
        assert wrapped.get_detail("operation") == "test"
        assert wrapped.get_detail("timestamp") == "2024-01-01"
        assert wrapped.get_detail("severity") == "high"
        assert wrapped.get_detail("original_exception") == "Runtime issue"
        assert wrapped.get_detail("original_type") == "RuntimeError"


class TestExceptionChaining:
    """Test cases for exception chaining and inheritance behavior."""
    
    def test_exception_chain_catching(self) -> None:
        """Test catching exceptions in inheritance chain."""
        # MCPConnectionError should be catchable as MCPError, DataRetrievalError, and TicketAnalysisError
        
        with pytest.raises(TicketAnalysisError):
            raise MCPConnectionError("Connection failed")
        
        with pytest.raises(DataRetrievalError):
            raise MCPConnectionError("Connection failed")
        
        with pytest.raises(MCPError):
            raise MCPConnectionError("Connection failed")
        
        with pytest.raises(MCPConnectionError):
            raise MCPConnectionError("Connection failed")
    
    def test_specific_exception_catching(self) -> None:
        """Test catching specific exception types."""
        try:
            raise AuthenticationError("Auth failed", auth_method="midway")
        except AuthenticationError as e:
            assert e.message == "Auth failed"
            assert e.get_detail("auth_method") == "midway"
            assert e.error_code == "AUTH_ERROR"
        except Exception:
            pytest.fail("Should have caught AuthenticationError specifically")
    
    def test_base_exception_catching(self) -> None:
        """Test catching various exceptions as base TicketAnalysisError."""
        exceptions = [
            AuthenticationError("Auth error"),
            ConfigurationError("Config error"),
            DataRetrievalError("Data error"),
            AnalysisError("Analysis error"),
            ValidationError("Validation error")
        ]
        
        for exc in exceptions:
            try:
                raise exc
            except TicketAnalysisError as e:
                assert isinstance(e, TicketAnalysisError)
                assert hasattr(e, 'message')
                assert hasattr(e, 'details')
                assert hasattr(e, 'error_code')
            except Exception:
                pytest.fail(f"Should have caught {type(exc).__name__} as TicketAnalysisError")


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""
    
    def test_empty_message(self) -> None:
        """Test exception with empty message."""
        error = TicketAnalysisError("")
        
        assert error.message == ""
        assert str(error) == ""
    
    def test_none_details(self) -> None:
        """Test exception with None details (should default to empty dict)."""
        error = TicketAnalysisError("Test", details=None)
        
        assert error.details == {}
    
    def test_very_long_message(self) -> None:
        """Test exception with very long message."""
        long_message = "x" * 10000
        error = TicketAnalysisError(long_message)
        
        assert error.message == long_message
        assert len(str(error)) == 10000
    
    def test_special_characters_in_message(self) -> None:
        """Test exception with special characters in message."""
        special_message = "Error: 'test' failed with \"quotes\" and \n newlines \t tabs"
        error = TicketAnalysisError(special_message)
        
        assert error.message == special_message
        assert special_message in str(error)
    
    def test_unicode_characters_in_message(self) -> None:
        """Test exception with unicode characters in message."""
        unicode_message = "Error: αβγδε 中文 日本語 한국어 🚨"
        error = TicketAnalysisError(unicode_message)
        
        assert error.message == unicode_message
        assert unicode_message in str(error)
    
    def test_complex_details_structure(self) -> None:
        """Test exception with complex nested details structure."""
        complex_details = {
            "nested": {
                "level1": {
                    "level2": ["item1", "item2"]
                }
            },
            "list": [1, 2, {"key": "value"}],
            "none_value": None,
            "boolean": True
        }
        
        error = TicketAnalysisError("Complex error", details=complex_details)
        
        assert error.details == complex_details
        assert error.get_detail("nested") == complex_details["nested"]
        assert error.get_detail("list") == complex_details["list"]
        assert error.get_detail("none_value") is None
        assert error.get_detail("boolean") is True
    
    def test_modifying_details_after_creation(self) -> None:
        """Test modifying details after exception creation."""
        error = TicketAnalysisError("Test")
        
        # Add details after creation
        error.add_detail("key1", "value1")
        error.add_detail("key2", {"nested": "value"})
        
        assert error.get_detail("key1") == "value1"
        assert error.get_detail("key2") == {"nested": "value"}
        
        # Modify existing detail
        error.add_detail("key1", "modified_value")
        assert error.get_detail("key1") == "modified_value"
    
    def test_error_code_overriding(self) -> None:
        """Test that error codes can be overridden in derived classes."""
        # AuthenticationError sets error_code to "AUTH_ERROR"
        auth_error = AuthenticationError("Test")
        assert auth_error.error_code == "AUTH_ERROR"
        
        # But it can be overridden
        custom_auth_error = AuthenticationError("Test")
        custom_auth_error.error_code = "CUSTOM_AUTH_ERROR"
        assert custom_auth_error.error_code == "CUSTOM_AUTH_ERROR"