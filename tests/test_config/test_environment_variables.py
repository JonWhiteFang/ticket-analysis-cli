"""Comprehensive tests for environment variable handling.

This module contains unit tests for environment variable configuration
handling, including variable parsing, type conversion, nested key handling,
and integration with the configuration system.
"""

from __future__ import annotations
import pytest
import os
from typing import Dict, Any
from unittest.mock import patch

from ticket_analyzer.config.handlers import EnvironmentConfigHandler
from ticket_analyzer.config.config_manager import ConfigurationManager


class TestEnvironmentVariableHandling:
    """Test cases for environment variable configuration handling."""
    
    def test_basic_environment_variable_loading(self) -> None:
        """Test loading basic environment variables."""
        env_vars = {
            "TICKET_ANALYZER_DEBUG_MODE": "true",
            "TICKET_ANALYZER_MAX_CONCURRENT_REQUESTS": "25"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["debug_mode"] is True
            assert config["max_concurrent_requests"] == 25
    
    def test_nested_environment_variables(self) -> None:
        """Test loading nested environment variables with double underscores."""
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "180",
            "TICKET_ANALYZER_AUTH__MAX_RETRY_ATTEMPTS": "5",
            "TICKET_ANALYZER_REPORT__FORMAT": "html",
            "TICKET_ANALYZER_REPORT__MAX_RESULTS_DISPLAY": "500",
            "TICKET_ANALYZER_MCP__CONNECTION_TIMEOUT": "45",
            "TICKET_ANALYZER_LOGGING__LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            # Check nested structure
            assert config["auth"]["timeout_seconds"] == 180
            assert config["auth"]["max_retry_attempts"] == 5
            assert config["report"]["format"] == "html"
            assert config["report"]["max_results_display"] == 500
            assert config["mcp"]["connection_timeout"] == 45
            assert config["logging"]["level"] == "DEBUG"
    
    def test_deeply_nested_environment_variables(self) -> None:
        """Test loading deeply nested environment variables."""
        env_vars = {
            "TICKET_ANALYZER_SECTION__SUBSECTION__KEY": "value1",
            "TICKET_ANALYZER_DEEP__NESTED__VERY__DEEP__KEY": "value2",
            "TICKET_ANALYZER_A__B__C__D__E": "deep_value"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["section"]["subsection"]["key"] == "value1"
            assert config["deep"]["nested"]["very"]["deep"]["key"] == "value2"
            assert config["a"]["b"]["c"]["d"]["e"] == "deep_value"
    
    def test_environment_variable_type_conversion_booleans(self) -> None:
        """Test boolean type conversion from environment variables."""
        # Test true values
        true_env_vars = {
            "TICKET_ANALYZER_BOOL1": "true",
            "TICKET_ANALYZER_BOOL2": "TRUE",
            "TICKET_ANALYZER_BOOL3": "yes",
            "TICKET_ANALYZER_BOOL4": "YES",
            "TICKET_ANALYZER_BOOL5": "1"
        }
        
        with patch.dict(os.environ, true_env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["bool1"] is True
            assert config["bool2"] is True
            assert config["bool3"] is True
            assert config["bool4"] is True
            assert config["bool5"] is True
        
        # Test false values
        false_env_vars = {
            "TICKET_ANALYZER_BOOL1": "false",
            "TICKET_ANALYZER_BOOL2": "FALSE",
            "TICKET_ANALYZER_BOOL3": "no",
            "TICKET_ANALYZER_BOOL4": "NO",
            "TICKET_ANALYZER_BOOL5": "0"
        }
        
        with patch.dict(os.environ, false_env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["bool1"] is False
            assert config["bool2"] is False
            assert config["bool3"] is False
            assert config["bool4"] is False
            assert config["bool5"] is False
    
    def test_environment_variable_type_conversion_numbers(self) -> None:
        """Test numeric type conversion from environment variables."""
        env_vars = {
            "TICKET_ANALYZER_INT_POSITIVE": "42",
            "TICKET_ANALYZER_INT_NEGATIVE": "-10",
            "TICKET_ANALYZER_INT_ZERO": "0",
            "TICKET_ANALYZER_FLOAT_POSITIVE": "3.14",
            "TICKET_ANALYZER_FLOAT_NEGATIVE": "-2.5",
            "TICKET_ANALYZER_FLOAT_ZERO": "0.0"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["int_positive"] == 42
            assert config["int_negative"] == -10
            assert config["int_zero"] == 0
            assert config["float_positive"] == 3.14
            assert config["float_negative"] == -2.5
            assert config["float_zero"] == 0.0
    
    def test_environment_variable_type_conversion_json(self) -> None:
        """Test JSON type conversion from environment variables."""
        env_vars = {
            "TICKET_ANALYZER_JSON_OBJECT": '{"key": "value", "number": 42}',
            "TICKET_ANALYZER_JSON_ARRAY": '["item1", "item2", "item3"]',
            "TICKET_ANALYZER_JSON_STRING": '"quoted_string"',
            "TICKET_ANALYZER_JSON_NUMBER": "123",
            "TICKET_ANALYZER_JSON_BOOLEAN": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["json_object"] == {"key": "value", "number": 42}
            assert config["json_array"] == ["item1", "item2", "item3"]
            assert config["json_string"] == "quoted_string"
            assert config["json_number"] == 123
            assert config["json_boolean"] is True
    
    def test_environment_variable_type_conversion_invalid_json(self) -> None:
        """Test handling of invalid JSON in environment variables."""
        env_vars = {
            "TICKET_ANALYZER_INVALID_JSON1": '{"invalid": json}',
            "TICKET_ANALYZER_INVALID_JSON2": '[invalid, array]',
            "TICKET_ANALYZER_INVALID_JSON3": '{incomplete'
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            # Invalid JSON should fall back to string
            assert config["invalid_json1"] == '{"invalid": json}'
            assert config["invalid_json2"] == '[invalid, array]'
            assert config["invalid_json3"] == '{incomplete'
    
    def test_environment_variable_comma_separated_lists(self) -> None:
        """Test comma-separated list conversion from environment variables."""
        env_vars = {
            "TICKET_ANALYZER_LIST_SIMPLE": "item1,item2,item3",
            "TICKET_ANALYZER_LIST_SPACES": "item1, item2 , item3",
            "TICKET_ANALYZER_LIST_SINGLE": "single_item",
            "TICKET_ANALYZER_LIST_EMPTY_ITEMS": "item1,,item3",
            "TICKET_ANALYZER_LIST_TRAILING_COMMA": "item1,item2,"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["list_simple"] == ["item1", "item2", "item3"]
            assert config["list_spaces"] == ["item1", "item2", "item3"]
            assert config["list_single"] == "single_item"  # No comma, so string
            assert config["list_empty_items"] == ["item1", "", "item3"]
            assert config["list_trailing_comma"] == ["item1", "item2", ""]
    
    def test_environment_variable_prefix_filtering(self) -> None:
        """Test that only variables with correct prefix are loaded."""
        env_vars = {
            "TICKET_ANALYZER_VALID_VAR": "should_be_loaded",
            "OTHER_PREFIX_VAR": "should_be_ignored",
            "TICKET_ANALYZER_ANOTHER_VALID": "should_be_loaded",
            "RANDOM_VAR": "should_be_ignored",
            "TICKET_ANALYZER_": "empty_suffix",  # Edge case
            "TICKET_ANALYZER": "no_underscore"  # Edge case
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["valid_var"] == "should_be_loaded"
            assert config["another_valid"] == "should_be_loaded"
            assert config[""] == "empty_suffix"  # Edge case result
            
            # Should not contain non-matching variables
            assert "other_prefix_var" not in config
            assert "random_var" not in config
            assert "ticket_analyzer" not in config  # No underscore after prefix
    
    def test_environment_variable_custom_prefix(self) -> None:
        """Test environment variable handler with custom prefix."""
        env_vars = {
            "CUSTOM_PREFIX_AUTH__TIMEOUT": "120",
            "CUSTOM_PREFIX_DEBUG_MODE": "true",
            "TICKET_ANALYZER_IGNORED": "should_be_ignored",
            "OTHER_PREFIX_IGNORED": "should_be_ignored"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler("CUSTOM_PREFIX_")
            config = handler.load_all()
            
            assert config["auth"]["timeout"] == 120
            assert config["debug_mode"] is True
            
            # Should not contain variables with other prefixes
            assert "ignored" not in config
            assert "ticket_analyzer_ignored" not in config
    
    def test_environment_variable_case_conversion(self) -> None:
        """Test case conversion of environment variable names."""
        env_vars = {
            "TICKET_ANALYZER_UPPER_CASE_VAR": "value1",
            "TICKET_ANALYZER_MixedCase_VAR": "value2",
            "TICKET_ANALYZER_lower_case_var": "value3"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            # All should be converted to lowercase
            assert config["upper_case_var"] == "value1"
            assert config["mixedcase_var"] == "value2"
            assert config["lower_case_var"] == "value3"
    
    def test_environment_variable_special_characters(self) -> None:
        """Test handling of special characters in environment variable values."""
        env_vars = {
            "TICKET_ANALYZER_SPECIAL_CHARS": "value with spaces",
            "TICKET_ANALYZER_QUOTES": 'value with "quotes"',
            "TICKET_ANALYZER_NEWLINES": "line1\nline2\nline3",
            "TICKET_ANALYZER_UNICODE": "café 测试 🎫",
            "TICKET_ANALYZER_SYMBOLS": "!@#$%^&*()_+-=[]{}|;:,.<>?"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["special_chars"] == "value with spaces"
            assert config["quotes"] == 'value with "quotes"'
            assert config["newlines"] == "line1\nline2\nline3"
            assert config["unicode"] == "café 测试 🎫"
            assert config["symbols"] == "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    def test_environment_variable_empty_values(self) -> None:
        """Test handling of empty environment variable values."""
        env_vars = {
            "TICKET_ANALYZER_EMPTY_STRING": "",
            "TICKET_ANALYZER_WHITESPACE": "   ",
            "TICKET_ANALYZER_TAB": "\t",
            "TICKET_ANALYZER_NEWLINE": "\n"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["empty_string"] == ""
            assert config["whitespace"] == "   "
            assert config["tab"] == "\t"
            assert config["newline"] == "\n"


class TestEnvironmentVariableIntegration:
    """Test cases for environment variable integration with configuration manager."""
    
    def test_environment_variables_in_configuration_hierarchy(self, tmp_path) -> None:
        """Test environment variables in complete configuration hierarchy."""
        # Set environment variables
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "200",
            "TICKET_ANALYZER_REPORT__FORMAT": "yaml",
            "TICKET_ANALYZER_DEBUG_MODE": "true",
            "TICKET_ANALYZER_MCP__MAX_RETRIES": "7"
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # Environment values should override defaults
            assert config["auth"]["timeout_seconds"] == 200
            assert config["report"]["format"] == "yaml"
            assert config["debug_mode"] is True
            assert config["mcp"]["max_retries"] == 7
            
            # Default values should be preserved where no env var exists
            assert config["auth"]["max_retry_attempts"] == 3  # Default
            assert config["report"]["max_results_display"] == 100  # Default
    
    def test_environment_variables_overridden_by_file_config(self, tmp_path) -> None:
        """Test that file configuration overrides environment variables."""
        # Set environment variables
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "300",
            "TICKET_ANALYZER_REPORT__FORMAT": "csv",
            "TICKET_ANALYZER_DEBUG_MODE": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            # Create config file that should override env vars
            import json
            config_file = tmp_path / "config.json"
            file_config = {
                "auth": {"timeout_seconds": 150},  # Should override env
                "report": {"format": "html"},  # Should override env
                # debug_mode not in file, should use env value
            }
            config_file.write_text(json.dumps(file_config))
            
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # File should override env
            assert config["auth"]["timeout_seconds"] == 150
            assert config["report"]["format"] == "html"
            
            # Env should be used where file doesn't specify
            assert config["debug_mode"] is True
    
    def test_environment_variables_overridden_by_cli_args(self, tmp_path) -> None:
        """Test that CLI arguments override environment variables."""
        # Set environment variables
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "240",
            "TICKET_ANALYZER_REPORT__FORMAT": "json",
            "TICKET_ANALYZER_REPORT__VERBOSE": "false"
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigurationManager(config_dir=tmp_path)
            
            # Set CLI args that should override env vars
            cli_handler = manager._config_chain
            cli_handler.set_cli_args({
                "timeout": 90,  # Should override env
                "format": "csv",  # Should override env
                # verbose not in CLI, should use env value
            })
            
            config = manager.load_config()
            
            # CLI should override env
            assert config["auth"]["timeout_seconds"] == 90
            assert config["report"]["format"] == "csv"
            
            # Env should be used where CLI doesn't specify
            assert config["report"]["verbose"] is False
    
    def test_environment_variables_with_validation(self, tmp_path) -> None:
        """Test environment variables with configuration validation."""
        # Set valid environment variables
        valid_env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "120",
            "TICKET_ANALYZER_AUTH__MAX_RETRY_ATTEMPTS": "5",
            "TICKET_ANALYZER_REPORT__FORMAT": "html",
            "TICKET_ANALYZER_REPORT__MAX_RESULTS_DISPLAY": "500"
        }
        
        with patch.dict(os.environ, valid_env_vars):
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # Should validate successfully
            assert manager.validate_config(config) is True
        
        # Set invalid environment variables
        invalid_env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "-1",  # Invalid: negative
            "TICKET_ANALYZER_REPORT__FORMAT": "xml",  # Invalid: not supported
            "TICKET_ANALYZER_REPORT__MAX_RESULTS_DISPLAY": "0"  # Invalid: zero
        }
        
        with patch.dict(os.environ, invalid_env_vars):
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # Should fail validation
            with pytest.raises(Exception):  # ConfigurationError or validation error
                manager.validate_config(config)
    
    def test_environment_variables_real_world_scenario(self, tmp_path) -> None:
        """Test environment variables in a real-world deployment scenario."""
        # Simulate production environment variables
        production_env_vars = {
            # Authentication settings
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "180",
            "TICKET_ANALYZER_AUTH__MAX_RETRY_ATTEMPTS": "5",
            "TICKET_ANALYZER_AUTH__SESSION_DURATION_HOURS": "12",
            "TICKET_ANALYZER_AUTH__AUTO_REFRESH": "true",
            
            # Report settings
            "TICKET_ANALYZER_REPORT__FORMAT": "json",
            "TICKET_ANALYZER_REPORT__SANITIZE_OUTPUT": "true",
            "TICKET_ANALYZER_REPORT__MAX_RESULTS_DISPLAY": "1000",
            "TICKET_ANALYZER_REPORT__SHOW_PROGRESS": "false",
            
            # MCP settings
            "TICKET_ANALYZER_MCP__CONNECTION_TIMEOUT": "60",
            "TICKET_ANALYZER_MCP__REQUEST_TIMEOUT": "120",
            "TICKET_ANALYZER_MCP__MAX_RETRIES": "5",
            "TICKET_ANALYZER_MCP__RETRY_DELAY": "2.0",
            
            # Logging settings
            "TICKET_ANALYZER_LOGGING__LEVEL": "WARNING",
            "TICKET_ANALYZER_LOGGING__FILE_PATH": "/var/log/ticket_analyzer.log",
            "TICKET_ANALYZER_LOGGING__MAX_FILE_SIZE": "52428800",  # 50MB
            "TICKET_ANALYZER_LOGGING__SANITIZE_LOGS": "true",
            
            # Application settings
            "TICKET_ANALYZER_DEBUG_MODE": "false",
            "TICKET_ANALYZER_MAX_CONCURRENT_REQUESTS": "50"
        }
        
        with patch.dict(os.environ, production_env_vars):
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # Verify all environment settings are loaded correctly
            assert config["auth"]["timeout_seconds"] == 180
            assert config["auth"]["max_retry_attempts"] == 5
            assert config["auth"]["session_duration_hours"] == 12
            assert config["auth"]["auto_refresh"] is True
            
            assert config["report"]["format"] == "json"
            assert config["report"]["sanitize_output"] is True
            assert config["report"]["max_results_display"] == 1000
            assert config["report"]["show_progress"] is False
            
            assert config["mcp"]["connection_timeout"] == 60
            assert config["mcp"]["request_timeout"] == 120
            assert config["mcp"]["max_retries"] == 5
            assert config["mcp"]["retry_delay"] == 2.0
            
            assert config["logging"]["level"] == "WARNING"
            assert config["logging"]["file_path"] == "/var/log/ticket_analyzer.log"
            assert config["logging"]["max_file_size"] == 52428800
            assert config["logging"]["sanitize_logs"] is True
            
            assert config["debug_mode"] is False
            assert config["max_concurrent_requests"] == 50
            
            # Verify configuration validates successfully
            assert manager.validate_config(config) is True
    
    def test_environment_variables_docker_scenario(self, tmp_path) -> None:
        """Test environment variables in a Docker container scenario."""
        # Simulate Docker environment with minimal config
        docker_env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "300",
            "TICKET_ANALYZER_REPORT__FORMAT": "json",
            "TICKET_ANALYZER_LOGGING__LEVEL": "INFO",
            "TICKET_ANALYZER_DEBUG_MODE": "false"
        }
        
        with patch.dict(os.environ, docker_env_vars, clear=True):
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # Environment overrides should be applied
            assert config["auth"]["timeout_seconds"] == 300
            assert config["report"]["format"] == "json"
            assert config["logging"]["level"] == "INFO"
            assert config["debug_mode"] is False
            
            # Defaults should be used for unspecified values
            assert config["auth"]["max_retry_attempts"] == 3  # Default
            assert config["report"]["max_results_display"] == 100  # Default
            assert config["mcp"]["connection_timeout"] == 30  # Default