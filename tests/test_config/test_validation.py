"""Comprehensive tests for configuration validation.

This module contains unit tests for configuration validation scenarios,
including schema validation, error handling, and edge cases for the
ConfigurationValidator class and validation integration.
"""

from __future__ import annotations
import pytest
from typing import Dict, Any, List

from ticket_analyzer.config.handlers import ConfigurationValidator
from ticket_analyzer.models.config import (
    ApplicationConfig, ReportConfig, AuthConfig, MCPConfig, LoggingConfig,
    OutputFormat, LogLevel
)
from ticket_analyzer.models.exceptions import ConfigurationError


class TestConfigurationValidatorSchema:
    """Test cases for ConfigurationValidator schema definition."""
    
    def test_schema_structure(self) -> None:
        """Test that validation schema has expected structure."""
        validator = ConfigurationValidator()
        schema = validator.get_schema()
        
        # Check top-level sections
        expected_sections = ["auth", "report", "mcp", "logging"]
        for section in expected_sections:
            assert section in schema
            assert isinstance(schema[section], dict)
        
        # Check top-level settings
        assert "debug_mode" in schema
        assert "max_concurrent_requests" in schema
    
    def test_auth_schema_definition(self) -> None:
        """Test authentication section schema definition."""
        validator = ConfigurationValidator()
        schema = validator.get_schema()
        auth_schema = schema["auth"]
        
        # Check required fields
        required_fields = [
            "timeout_seconds", "max_retry_attempts", "check_interval_seconds",
            "session_duration_hours", "auto_refresh", "require_auth",
            "auth_method", "cache_credentials"
        ]
        
        for field in required_fields:
            assert field in auth_schema
        
        # Check specific constraints
        timeout_def = auth_schema["timeout_seconds"]
        assert timeout_def["type"] is int
        assert timeout_def["min"] == 1
        assert timeout_def["max"] == 300
        
        retry_def = auth_schema["max_retry_attempts"]
        assert retry_def["type"] is int
        assert retry_def["min"] == 0
        assert retry_def["max"] == 10
        
        method_def = auth_schema["auth_method"]
        assert method_def["type"] is str
        assert "choices" in method_def
        assert "midway" in method_def["choices"]
        assert "kerberos" in method_def["choices"]
        assert "none" in method_def["choices"]
    
    def test_report_schema_definition(self) -> None:
        """Test report section schema definition."""
        validator = ConfigurationValidator()
        schema = validator.get_schema()
        report_schema = schema["report"]
        
        # Check format field
        format_def = report_schema["format"]
        assert format_def["type"] is str
        assert "choices" in format_def
        expected_formats = ["table", "json", "csv", "html", "yaml"]
        for fmt in expected_formats:
            assert fmt in format_def["choices"]
        
        # Check optional fields
        output_def = report_schema["output_path"]
        assert output_def["type"] is str
        assert output_def.get("optional", False) is True
        
        # Check numeric constraints
        max_results_def = report_schema["max_results_display"]
        assert max_results_def["type"] is int
        assert max_results_def["min"] == 1
        assert max_results_def["max"] == 10000
    
    def test_mcp_schema_definition(self) -> None:
        """Test MCP section schema definition."""
        validator = ConfigurationValidator()
        schema = validator.get_schema()
        mcp_schema = schema["mcp"]
        
        # Check server command
        server_def = mcp_schema["server_command"]
        assert server_def["type"] is list
        
        # Check timeout constraints
        conn_timeout_def = mcp_schema["connection_timeout"]
        assert conn_timeout_def["type"] is int
        assert conn_timeout_def["min"] == 1
        
        req_timeout_def = mcp_schema["request_timeout"]
        assert req_timeout_def["type"] is int
        assert req_timeout_def["min"] == 1
        
        # Check retry settings
        retries_def = mcp_schema["max_retries"]
        assert retries_def["type"] is int
        assert retries_def["min"] == 0
        
        delay_def = mcp_schema["retry_delay"]
        assert delay_def["type"] is float
        assert delay_def["min"] == 0
    
    def test_logging_schema_definition(self) -> None:
        """Test logging section schema definition."""
        validator = ConfigurationValidator()
        schema = validator.get_schema()
        logging_schema = schema["logging"]
        
        # Check log level
        level_def = logging_schema["level"]
        assert level_def["type"] is str
        assert "choices" in level_def
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in expected_levels:
            assert level in level_def["choices"]
        
        # Check file path (optional)
        file_def = logging_schema["file_path"]
        assert file_def["type"] is str
        assert file_def.get("optional", False) is True
        
        # Check size constraints
        size_def = logging_schema["max_file_size"]
        assert size_def["type"] is int
        assert size_def["min"] == 1
        
        backup_def = logging_schema["backup_count"]
        assert backup_def["type"] is int
        assert backup_def["min"] == 0


class TestConfigurationValidatorValidation:
    """Test cases for configuration validation logic."""
    
    def test_validate_setting_valid_values(self) -> None:
        """Test validation of valid setting values."""
        validator = ConfigurationValidator()
        
        # Test various valid values
        test_cases = [
            ("auth.timeout_seconds", 60),
            ("auth.max_retry_attempts", 3),
            ("auth.auth_method", "midway"),
            ("auth.auto_refresh", True),
            ("report.format", "json"),
            ("report.max_results_display", 500),
            ("report.output_path", None),  # Optional
            ("mcp.server_command", ["node", "server.js"]),
            ("mcp.retry_delay", 1.5),
            ("logging.level", "INFO"),
            ("debug_mode", False),
            ("max_concurrent_requests", 25)
        ]
        
        for key, value in test_cases:
            assert validator.validate_setting(key, value) is True
    
    def test_validate_setting_type_errors(self) -> None:
        """Test validation failures for incorrect types."""
        validator = ConfigurationValidator()
        
        test_cases = [
            ("auth.timeout_seconds", "not_a_number"),
            ("auth.auto_refresh", "not_a_boolean"),
            ("report.max_results_display", 3.14),  # Should be int, not float
            ("mcp.server_command", "not_a_list"),
            ("debug_mode", 1)  # Should be bool, not int
        ]
        
        for key, value in test_cases:
            with pytest.raises(ConfigurationError, match="must be of type"):
                validator.validate_setting(key, value)
    
    def test_validate_setting_choice_errors(self) -> None:
        """Test validation failures for invalid choices."""
        validator = ConfigurationValidator()
        
        test_cases = [
            ("auth.auth_method", "invalid_method"),
            ("report.format", "xml"),
            ("logging.level", "TRACE"),
            ("report.theme", "invalid_theme")
        ]
        
        for key, value in test_cases:
            with pytest.raises(ConfigurationError, match="must be one of"):
                validator.validate_setting(key, value)
    
    def test_validate_setting_range_errors(self) -> None:
        """Test validation failures for out-of-range values."""
        validator = ConfigurationValidator()
        
        # Test minimum constraints
        min_test_cases = [
            ("auth.timeout_seconds", 0),
            ("auth.max_retry_attempts", -1),
            ("report.max_results_display", 0),
            ("mcp.connection_timeout", 0),
            ("logging.max_file_size", 0)
        ]
        
        for key, value in min_test_cases:
            with pytest.raises(ConfigurationError, match="must be >="):
                validator.validate_setting(key, value)
        
        # Test maximum constraints
        max_test_cases = [
            ("auth.timeout_seconds", 301),
            ("auth.max_retry_attempts", 11),
            ("report.max_results_display", 10001),
            ("max_concurrent_requests", 101)
        ]
        
        for key, value in max_test_cases:
            with pytest.raises(ConfigurationError, match="must be <="):
                validator.validate_setting(key, value)
    
    def test_validate_setting_optional_values(self) -> None:
        """Test validation of optional settings."""
        validator = ConfigurationValidator()
        
        # Optional settings should accept None
        optional_cases = [
            ("report.output_path", None),
            ("report.template_name", None),
            ("logging.file_path", None)
        ]
        
        for key, value in optional_cases:
            assert validator.validate_setting(key, value) is True
        
        # Optional settings should also accept valid values
        assert validator.validate_setting("report.output_path", "/tmp/report.json") is True
        assert validator.validate_setting("logging.file_path", "/var/log/app.log") is True
    
    def test_validate_setting_unknown_keys(self) -> None:
        """Test validation of unknown setting keys."""
        validator = ConfigurationValidator()
        
        # Unknown keys should pass validation (no schema defined)
        unknown_cases = [
            ("unknown.setting", "any_value"),
            ("custom.config.deep.nested", 42),
            ("new_section.new_key", True)
        ]
        
        for key, value in unknown_cases:
            assert validator.validate_setting(key, value) is True
    
    def test_validate_schema_complete_valid_config(self) -> None:
        """Test validation of complete valid configuration."""
        validator = ConfigurationValidator()
        
        valid_config = {
            "auth": {
                "timeout_seconds": 90,
                "max_retry_attempts": 4,
                "check_interval_seconds": 600,
                "session_duration_hours": 12,
                "auto_refresh": True,
                "require_auth": True,
                "auth_method": "kerberos",
                "cache_credentials": False
            },
            "report": {
                "format": "html",
                "output_path": "/tmp/report.html",
                "include_charts": True,
                "color_output": False,
                "template_name": "custom",
                "sanitize_output": True,
                "max_results_display": 500,
                "show_progress": False,
                "verbose": True,
                "theme": "dark"
            },
            "mcp": {
                "server_command": ["python", "mcp_server.py"],
                "connection_timeout": 45,
                "request_timeout": 120,
                "max_retries": 5,
                "retry_delay": 2.0,
                "circuit_breaker_threshold": 10,
                "circuit_breaker_timeout": 120,
                "enable_logging": True
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "file_path": "/var/log/ticket_analyzer.log",
                "max_file_size": 5242880,  # 5MB
                "backup_count": 3,
                "sanitize_logs": False,
                "include_timestamps": True,
                "include_caller_info": True
            },
            "debug_mode": True,
            "max_concurrent_requests": 50
        }
        
        assert validator.validate_schema(valid_config) is True
    
    def test_validate_schema_multiple_errors(self) -> None:
        """Test validation with multiple errors in configuration."""
        validator = ConfigurationValidator()
        
        invalid_config = {
            "auth": {
                "timeout_seconds": -1,  # Invalid: negative
                "max_retry_attempts": 15,  # Invalid: too large
                "auth_method": "invalid",  # Invalid: not in choices
                "auto_refresh": "not_bool"  # Invalid: wrong type
            },
            "report": {
                "format": "xml",  # Invalid: not in choices
                "max_results_display": 0,  # Invalid: zero
                "theme": "invalid_theme"  # Invalid: not in choices
            },
            "mcp": {
                "server_command": "not_a_list",  # Invalid: wrong type
                "connection_timeout": 0,  # Invalid: zero
                "retry_delay": -1.0  # Invalid: negative
            },
            "logging": {
                "level": "INVALID",  # Invalid: not in choices
                "max_file_size": -1  # Invalid: negative
            },
            "max_concurrent_requests": 101  # Invalid: too large
        }
        
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            validator.validate_schema(invalid_config)
    
    def test_get_validation_errors_detailed(self) -> None:
        """Test getting detailed validation errors."""
        validator = ConfigurationValidator()
        
        invalid_config = {
            "auth": {
                "timeout_seconds": -5,
                "max_retry_attempts": 20,
                "auth_method": "unknown_method"
            },
            "report": {
                "format": "unsupported_format",
                "max_results_display": 15000
            }
        }
        
        errors = validator.get_validation_errors(invalid_config)
        
        # Should have multiple specific errors
        assert len(errors) >= 5
        
        # Check for specific error messages
        error_text = " ".join(errors)
        assert "timeout_seconds" in error_text
        assert "must be >=" in error_text
        assert "max_retry_attempts" in error_text
        assert "must be <=" in error_text
        assert "auth_method" in error_text
        assert "must be one of" in error_text
        assert "format" in error_text
        assert "max_results_display" in error_text
    
    def test_validate_schema_nested_object_errors(self) -> None:
        """Test validation errors for incorrect nested object structure."""
        validator = ConfigurationValidator()
        
        invalid_config = {
            "auth": "should_be_object",  # Wrong type
            "report": {
                "format": "json"  # This is valid
            }
        }
        
        errors = validator.get_validation_errors(invalid_config)
        
        assert len(errors) > 0
        assert any("must be an object" in error for error in errors)
        assert any("auth" in error for error in errors)
    
    def test_validate_schema_partial_config(self) -> None:
        """Test validation of partial configuration (missing sections)."""
        validator = ConfigurationValidator()
        
        partial_config = {
            "auth": {
                "timeout_seconds": 120
                # Missing other auth fields - should be OK
            },
            "debug_mode": True
            # Missing other sections - should be OK
        }
        
        # Partial config should validate successfully
        assert validator.validate_schema(partial_config) is True
    
    def test_validate_schema_empty_config(self) -> None:
        """Test validation of empty configuration."""
        validator = ConfigurationValidator()
        
        empty_config = {}
        
        # Empty config should validate successfully
        assert validator.validate_schema(empty_config) is True


class TestConfigurationValidatorEdgeCases:
    """Test cases for edge cases in configuration validation."""
    
    def test_validate_setting_boundary_values(self) -> None:
        """Test validation at boundary values."""
        validator = ConfigurationValidator()
        
        # Test minimum boundary values
        assert validator.validate_setting("auth.timeout_seconds", 1) is True
        assert validator.validate_setting("auth.max_retry_attempts", 0) is True
        assert validator.validate_setting("report.max_results_display", 1) is True
        
        # Test maximum boundary values
        assert validator.validate_setting("auth.timeout_seconds", 300) is True
        assert validator.validate_setting("auth.max_retry_attempts", 10) is True
        assert validator.validate_setting("report.max_results_display", 10000) is True
        assert validator.validate_setting("max_concurrent_requests", 100) is True
    
    def test_validate_setting_float_precision(self) -> None:
        """Test validation with float precision values."""
        validator = ConfigurationValidator()
        
        # Test various float values for retry_delay
        float_cases = [0.0, 0.1, 1.0, 1.5, 10.0, 100.5]
        
        for value in float_cases:
            assert validator.validate_setting("mcp.retry_delay", value) is True
    
    def test_validate_setting_empty_list(self) -> None:
        """Test validation with empty list values."""
        validator = ConfigurationValidator()
        
        # Empty list should fail for server_command (cannot be empty)
        with pytest.raises(ConfigurationError):
            # This would be caught by MCPConfig validation, not schema validation
            # But we can test the type validation
            assert validator.validate_setting("mcp.server_command", []) is True
    
    def test_validate_setting_very_long_strings(self) -> None:
        """Test validation with very long string values."""
        validator = ConfigurationValidator()
        
        # Very long strings should be accepted (no length limits in schema)
        long_string = "x" * 10000
        assert validator.validate_setting("report.output_path", long_string) is True
        assert validator.validate_setting("logging.format", long_string) is True
    
    def test_validate_setting_unicode_strings(self) -> None:
        """Test validation with unicode string values."""
        validator = ConfigurationValidator()
        
        # Unicode strings should be accepted
        unicode_cases = [
            "café",
            "测试",
            "🎫📊",
            "Ñoño",
            "Москва"
        ]
        
        for value in unicode_cases:
            assert validator.validate_setting("report.output_path", value) is True
    
    def test_validate_setting_case_sensitivity(self) -> None:
        """Test validation case sensitivity for choice values."""
        validator = ConfigurationValidator()
        
        # Valid choices (case sensitive)
        assert validator.validate_setting("auth.auth_method", "midway") is True
        assert validator.validate_setting("report.format", "json") is True
        assert validator.validate_setting("logging.level", "INFO") is True
        
        # Invalid case variations
        with pytest.raises(ConfigurationError):
            validator.validate_setting("auth.auth_method", "MIDWAY")
        
        with pytest.raises(ConfigurationError):
            validator.validate_setting("report.format", "JSON")
        
        with pytest.raises(ConfigurationError):
            validator.validate_setting("logging.level", "info")
    
    def test_validate_schema_deeply_nested_config(self) -> None:
        """Test validation with deeply nested configuration."""
        validator = ConfigurationValidator()
        
        # Create config with extra nesting (should be ignored)
        nested_config = {
            "auth": {
                "timeout_seconds": 60,
                "nested": {
                    "deep": {
                        "very_deep": "value"
                    }
                }
            },
            "custom_section": {
                "custom_key": "custom_value",
                "nested_custom": {
                    "key": "value"
                }
            }
        }
        
        # Should validate successfully (unknown nested structures ignored)
        assert validator.validate_schema(nested_config) is True
    
    def test_validate_schema_with_null_values(self) -> None:
        """Test validation with null/None values in config."""
        validator = ConfigurationValidator()
        
        config_with_nulls = {
            "auth": {
                "timeout_seconds": 60,
                "auth_method": None  # Invalid: required field
            },
            "report": {
                "format": "json",
                "output_path": None  # Valid: optional field
            }
        }
        
        # Should fail due to None in required field
        with pytest.raises(ConfigurationError):
            validator.validate_schema(config_with_nulls)
    
    def test_get_schema_immutability(self) -> None:
        """Test that returned schema cannot modify internal schema."""
        validator = ConfigurationValidator()
        
        schema1 = validator.get_schema()
        schema2 = validator.get_schema()
        
        # Should be different objects
        assert schema1 is not schema2
        
        # Modifying returned schema shouldn't affect internal schema
        schema1["auth"]["timeout_seconds"]["min"] = 999
        
        schema3 = validator.get_schema()
        assert schema3["auth"]["timeout_seconds"]["min"] == 1  # Original value
    
    def test_validation_error_message_formatting(self) -> None:
        """Test that validation error messages are properly formatted."""
        validator = ConfigurationValidator()
        
        # Test various error types for message formatting
        test_cases = [
            ("auth.timeout_seconds", "string", "must be of type int"),
            ("auth.timeout_seconds", -1, "must be >= 1"),
            ("auth.timeout_seconds", 500, "must be <= 300"),
            ("auth.auth_method", "invalid", "must be one of"),
            ("report.format", "xml", "must be one of")
        ]
        
        for key, value, expected_message in test_cases:
            try:
                validator.validate_setting(key, value)
                pytest.fail(f"Expected validation error for {key}={value}")
            except ConfigurationError as e:
                error_message = str(e)
                assert expected_message in error_message
                assert key in error_message