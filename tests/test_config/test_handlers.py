"""Comprehensive tests for configuration handlers.

This module contains unit tests for all configuration handlers including
CommandLineConfigHandler, FileConfigHandler, EnvironmentConfigHandler,
DefaultConfigHandler, and ConfigurationValidator, covering file parsing,
validation, and error scenarios.
"""

from __future__ import annotations
import pytest
import os
import json
import configparser
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, mock_open

from ticket_analyzer.config.handlers import (
    BaseConfigurationHandler,
    CommandLineConfigHandler,
    FileConfigHandler,
    EnvironmentConfigHandler,
    DefaultConfigHandler,
    ConfigurationValidator
)
from ticket_analyzer.models.config import ApplicationConfig, OutputFormat, LogLevel
from ticket_analyzer.models.exceptions import ConfigurationError


class TestBaseConfigurationHandler:
    """Test cases for BaseConfigurationHandler abstract class."""
    
    def test_set_next_handler(self) -> None:
        """Test setting next handler in chain."""
        handler1 = DefaultConfigHandler()
        handler2 = DefaultConfigHandler()
        
        result = handler1.set_next(handler2)
        
        assert handler1._next_handler is handler2
        assert result is handler2
    
    def test_handle_with_value_found(self) -> None:
        """Test handle method when value is found in current handler."""
        handler = DefaultConfigHandler()
        
        # Default handler should have debug_mode
        result = handler.handle("debug_mode")
        
        assert result is False  # Default value
    
    def test_handle_with_value_not_found_no_next(self) -> None:
        """Test handle method when value not found and no next handler."""
        handler = DefaultConfigHandler()
        
        result = handler.handle("nonexistent_key")
        
        assert result is None
    
    def test_handle_with_value_not_found_with_next(self) -> None:
        """Test handle method when value not found but next handler has it."""
        handler1 = CommandLineConfigHandler()
        handler2 = DefaultConfigHandler()
        
        handler1.set_next(handler2)
        
        # CLI handler won't have debug_mode, but default handler will
        result = handler1.handle("debug_mode")
        
        assert result is False  # From default handler


class TestCommandLineConfigHandler:
    """Test cases for CommandLineConfigHandler."""
    
    def test_initialization_empty_args(self) -> None:
        """Test initialization with empty CLI arguments."""
        handler = CommandLineConfigHandler()
        
        assert handler._cli_args == {}
        assert handler._source_type == "cli"
    
    def test_initialization_with_args(self) -> None:
        """Test initialization with CLI arguments."""
        cli_args = {"format": "json", "verbose": True}
        handler = CommandLineConfigHandler(cli_args)
        
        assert handler._cli_args == cli_args
    
    def test_set_cli_args(self) -> None:
        """Test setting CLI arguments after initialization."""
        handler = CommandLineConfigHandler()
        cli_args = {"timeout": 120, "output": "/tmp/report.json"}
        
        handler.set_cli_args(cli_args)
        
        assert handler._cli_args == cli_args
    
    def test_load_all_empty_args(self) -> None:
        """Test loading configuration with empty CLI arguments."""
        handler = CommandLineConfigHandler()
        
        config = handler.load_all()
        
        assert config == {}
    
    def test_load_all_with_mapped_args(self) -> None:
        """Test loading configuration with mapped CLI arguments."""
        cli_args = {
            "format": "html",
            "output": "/tmp/output.html",
            "verbose": True,
            "color": False,
            "max_results": 500,
            "timeout": 90,
            "retry_attempts": 5,
            "debug": True,
            "config_file": "/custom/config.json"
        }
        
        handler = CommandLineConfigHandler(cli_args)
        config = handler.load_all()
        
        # Check mapped values
        assert config["report"]["format"] == "html"
        assert config["report"]["output_path"] == "/tmp/output.html"
        assert config["report"]["verbose"] is True
        assert config["report"]["color_output"] is False
        assert config["report"]["max_results_display"] == 500
        assert config["auth"]["timeout_seconds"] == 90
        assert config["auth"]["max_retry_attempts"] == 5
        assert config["debug_mode"] is True
        assert config["_config_file_override"] == "/custom/config.json"
    
    def test_load_all_with_none_values(self) -> None:
        """Test loading configuration with None values in CLI args."""
        cli_args = {
            "format": "json",
            "output": None,  # Should be ignored
            "verbose": True,
            "timeout": None  # Should be ignored
        }
        
        handler = CommandLineConfigHandler(cli_args)
        config = handler.load_all()
        
        # Only non-None values should be included
        assert config["report"]["format"] == "json"
        assert config["report"]["verbose"] is True
        assert "output_path" not in config.get("report", {})
        assert "timeout_seconds" not in config.get("auth", {})
    
    def test_can_handle_source_cli(self) -> None:
        """Test can_handle_source for CLI source type."""
        handler = CommandLineConfigHandler()
        
        assert handler.can_handle_source("cli") is True
        assert handler.can_handle_source("file") is False
        assert handler.can_handle_source("environment") is False


class TestFileConfigHandler:
    """Test cases for FileConfigHandler."""
    
    def test_initialization(self, tmp_path: Path) -> None:
        """Test FileConfigHandler initialization."""
        handler = FileConfigHandler(tmp_path)
        
        assert handler._config_dir == tmp_path
        assert handler._source_type == "file"
        assert len(handler._config_files) == 4
        expected_files = [
            "config.json",
            "config.ini", 
            ".ticket-analyzer.json",
            ".ticket-analyzer.ini"
        ]
        assert handler._config_files == expected_files
    
    def test_load_all_no_config_files(self, tmp_path: Path) -> None:
        """Test loading configuration when no config files exist."""
        handler = FileConfigHandler(tmp_path)
        
        config = handler.load_all()
        
        assert config == {}
    
    def test_load_all_json_config(self, tmp_path: Path) -> None:
        """Test loading JSON configuration file."""
        config_data = {
            "auth": {
                "timeout_seconds": 120,
                "auth_method": "kerberos"
            },
            "report": {
                "format": "html",
                "max_results_display": 200
            },
            "debug_mode": True
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        
        handler = FileConfigHandler(tmp_path)
        config = handler.load_all()
        
        assert config == config_data
    
    def test_load_all_ini_config(self, tmp_path: Path) -> None:
        """Test loading INI configuration file."""
        ini_content = """
[auth]
timeout_seconds = 90
auth_method = midway
auto_refresh = false
max_retry_attempts = 4

[report]
format = csv
color_output = true
max_results_display = 300
verbose = true

[logging]
level = DEBUG
sanitize_logs = false
"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        config = handler.load_all()
        
        # Check converted values
        assert config["auth"]["timeout_seconds"] == 90
        assert config["auth"]["auth_method"] == "midway"
        assert config["auth"]["auto_refresh"] is False
        assert config["auth"]["max_retry_attempts"] == 4
        assert config["report"]["format"] == "csv"
        assert config["report"]["color_output"] is True
        assert config["report"]["max_results_display"] == 300
        assert config["report"]["verbose"] is True
        assert config["logging"]["level"] == "DEBUG"
        assert config["logging"]["sanitize_logs"] is False    

    def test_load_all_multiple_config_files(self, tmp_path: Path) -> None:
        """Test loading configuration when multiple files exist."""
        # Create first config file
        config1_data = {
            "auth": {"timeout_seconds": 60},
            "report": {"format": "json"}
        }
        config1_file = tmp_path / "config.json"
        config1_file.write_text(json.dumps(config1_data))
        
        # Create second config file (should override first)
        ini_content = """
[auth]
timeout_seconds = 120
max_retry_attempts = 5

[report]
format = html
verbose = true
"""
        config2_file = tmp_path / ".ticket-analyzer.ini"
        config2_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        config = handler.load_all()
        
        # Later files should override earlier ones
        assert config["auth"]["timeout_seconds"] == 120  # From INI
        assert config["auth"]["max_retry_attempts"] == 5  # From INI
        assert config["report"]["format"] == "html"  # From INI
        assert config["report"]["verbose"] is True  # From INI
    
    def test_load_json_config_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON configuration file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json content }")
        
        handler = FileConfigHandler(tmp_path)
        
        # Should handle error gracefully and return empty config
        config = handler.load_all()
        assert config == {}
    
    def test_load_json_config_non_object(self, tmp_path: Path) -> None:
        """Test loading JSON file that doesn't contain an object."""
        config_file = tmp_path / "config.json"
        config_file.write_text('["array", "instead", "of", "object"]')
        
        handler = FileConfigHandler(tmp_path)
        
        # Should handle error gracefully
        config = handler.load_all()
        assert config == {}
    
    def test_load_ini_config_invalid_format(self, tmp_path: Path) -> None:
        """Test loading invalid INI configuration file."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("invalid ini content without sections")
        
        handler = FileConfigHandler(tmp_path)
        
        # Should handle error gracefully
        config = handler.load_all()
        assert config == {}
    
    def test_convert_ini_value_booleans(self) -> None:
        """Test INI value conversion for boolean values."""
        handler = FileConfigHandler(Path("/tmp"))
        
        # Test true values
        assert handler._convert_ini_value("true") is True
        assert handler._convert_ini_value("yes") is True
        assert handler._convert_ini_value("1") is True
        assert handler._convert_ini_value("on") is True
        assert handler._convert_ini_value("TRUE") is True  # Case insensitive
        
        # Test false values
        assert handler._convert_ini_value("false") is False
        assert handler._convert_ini_value("no") is False
        assert handler._convert_ini_value("0") is False
        assert handler._convert_ini_value("off") is False
        assert handler._convert_ini_value("FALSE") is False  # Case insensitive
    
    def test_convert_ini_value_numbers(self) -> None:
        """Test INI value conversion for numeric values."""
        handler = FileConfigHandler(Path("/tmp"))
        
        # Test integers
        assert handler._convert_ini_value("42") == 42
        assert handler._convert_ini_value("-10") == -10
        
        # Test floats
        assert handler._convert_ini_value("3.14") == 3.14
        assert handler._convert_ini_value("-2.5") == -2.5
    
    def test_convert_ini_value_lists(self) -> None:
        """Test INI value conversion for comma-separated lists."""
        handler = FileConfigHandler(Path("/tmp"))
        
        # Test simple list
        result = handler._convert_ini_value("item1,item2,item3")
        assert result == ["item1", "item2", "item3"]
        
        # Test list with spaces
        result = handler._convert_ini_value("item1, item2 , item3")
        assert result == ["item1", "item2", "item3"]
    
    def test_convert_ini_value_strings(self) -> None:
        """Test INI value conversion for string values."""
        handler = FileConfigHandler(Path("/tmp"))
        
        # Test regular strings
        assert handler._convert_ini_value("hello") == "hello"
        assert handler._convert_ini_value("path/to/file") == "path/to/file"
        
        # Test strings that look like numbers but aren't
        assert handler._convert_ini_value("not_a_number") == "not_a_number"
    
    def test_can_handle_source_file(self) -> None:
        """Test can_handle_source for file source type."""
        handler = FileConfigHandler(Path("/tmp"))
        
        assert handler.can_handle_source("file") is True
        assert handler.can_handle_source("cli") is False
        assert handler.can_handle_source("environment") is False


class TestEnvironmentConfigHandler:
    """Test cases for EnvironmentConfigHandler."""
    
    def test_initialization_default_prefix(self) -> None:
        """Test initialization with default prefix."""
        handler = EnvironmentConfigHandler()
        
        assert handler._prefix == "TICKET_ANALYZER_"
        assert handler._source_type == "environment"
    
    def test_initialization_custom_prefix(self) -> None:
        """Test initialization with custom prefix."""
        handler = EnvironmentConfigHandler("CUSTOM_PREFIX_")
        
        assert handler._prefix == "CUSTOM_PREFIX_"
    
    def test_load_all_no_env_vars(self) -> None:
        """Test loading configuration with no relevant environment variables."""
        handler = EnvironmentConfigHandler()
        
        # Clear any existing env vars
        with patch.dict(os.environ, {}, clear=True):
            config = handler.load_all()
            assert config == {}
    
    def test_load_all_with_env_vars(self) -> None:
        """Test loading configuration with environment variables."""
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "180",
            "TICKET_ANALYZER_AUTH__AUTO_REFRESH": "false",
            "TICKET_ANALYZER_REPORT__FORMAT": "yaml",
            "TICKET_ANALYZER_REPORT__VERBOSE": "true",
            "TICKET_ANALYZER_DEBUG_MODE": "true",
            "TICKET_ANALYZER_MAX_CONCURRENT_REQUESTS": "25",
            "OTHER_PREFIX_VALUE": "ignored"  # Should be ignored
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            # Check converted values
            assert config["auth"]["timeout_seconds"] == 180
            assert config["auth"]["auto_refresh"] is False
            assert config["report"]["format"] == "yaml"
            assert config["report"]["verbose"] is True
            assert config["debug_mode"] is True
            assert config["max_concurrent_requests"] == 25
            
            # Should not include non-matching prefix
            assert "other_prefix_value" not in config
    
    def test_convert_env_value_booleans(self) -> None:
        """Test environment value conversion for booleans."""
        handler = EnvironmentConfigHandler()
        
        # Test true values
        assert handler._convert_env_value("true") is True
        assert handler._convert_env_value("yes") is True
        assert handler._convert_env_value("1") is True
        assert handler._convert_env_value("TRUE") is True  # Case insensitive
        
        # Test false values
        assert handler._convert_env_value("false") is False
        assert handler._convert_env_value("no") is False
        assert handler._convert_env_value("0") is False
        assert handler._convert_env_value("FALSE") is False  # Case insensitive
    
    def test_convert_env_value_numbers(self) -> None:
        """Test environment value conversion for numbers."""
        handler = EnvironmentConfigHandler()
        
        # Test integers
        assert handler._convert_env_value("42") == 42
        assert handler._convert_env_value("-10") == -10
        
        # Test floats
        assert handler._convert_env_value("3.14") == 3.14
        assert handler._convert_env_value("-2.5") == -2.5
    
    def test_convert_env_value_json(self) -> None:
        """Test environment value conversion for JSON values."""
        handler = EnvironmentConfigHandler()
        
        # Test JSON object
        json_obj = '{"key": "value", "number": 42}'
        result = handler._convert_env_value(json_obj)
        assert result == {"key": "value", "number": 42}
        
        # Test JSON array
        json_array = '["item1", "item2", "item3"]'
        result = handler._convert_env_value(json_array)
        assert result == ["item1", "item2", "item3"]
        
        # Test JSON string
        json_string = '"quoted_string"'
        result = handler._convert_env_value(json_string)
        assert result == "quoted_string"
    
    def test_convert_env_value_invalid_json(self) -> None:
        """Test environment value conversion for invalid JSON."""
        handler = EnvironmentConfigHandler()
        
        # Invalid JSON should fall back to string
        invalid_json = '{"invalid": json}'
        result = handler._convert_env_value(invalid_json)
        assert result == '{"invalid": json}'
    
    def test_convert_env_value_comma_separated_lists(self) -> None:
        """Test environment value conversion for comma-separated lists."""
        handler = EnvironmentConfigHandler()
        
        # Test simple list
        result = handler._convert_env_value("item1,item2,item3")
        assert result == ["item1", "item2", "item3"]
        
        # Test list with spaces
        result = handler._convert_env_value("item1, item2 , item3")
        assert result == ["item1", "item2", "item3"]
    
    def test_convert_env_value_strings(self) -> None:
        """Test environment value conversion for regular strings."""
        handler = EnvironmentConfigHandler()
        
        assert handler._convert_env_value("simple_string") == "simple_string"
        assert handler._convert_env_value("path/to/file") == "path/to/file"
    
    def test_nested_key_conversion(self) -> None:
        """Test conversion of double underscores to nested keys."""
        env_vars = {
            "TICKET_ANALYZER_SECTION__SUBSECTION__KEY": "value",
            "TICKET_ANALYZER_DEEP__NESTED__VERY__DEEP": "deep_value"
        }
        
        with patch.dict(os.environ, env_vars):
            handler = EnvironmentConfigHandler()
            config = handler.load_all()
            
            assert config["section"]["subsection"]["key"] == "value"
            assert config["deep"]["nested"]["very"]["deep"] == "deep_value"
    
    def test_can_handle_source_environment(self) -> None:
        """Test can_handle_source for environment source type."""
        handler = EnvironmentConfigHandler()
        
        assert handler.can_handle_source("environment") is True
        assert handler.can_handle_source("cli") is False
        assert handler.can_handle_source("file") is False


class TestDefaultConfigHandler:
    """Test cases for DefaultConfigHandler."""
    
    def test_initialization(self) -> None:
        """Test DefaultConfigHandler initialization."""
        handler = DefaultConfigHandler()
        
        assert handler._source_type == "default"
        assert isinstance(handler._defaults, dict)
    
    def test_load_all_returns_defaults(self) -> None:
        """Test that load_all returns default configuration."""
        handler = DefaultConfigHandler()
        
        config = handler.load_all()
        
        # Should contain expected default sections
        assert isinstance(config, dict)
        assert "auth" in config
        assert "report" in config
        assert "mcp" in config
        assert "logging" in config
        
        # Check some default values
        assert config["auth"]["timeout_seconds"] == 60
        assert config["auth"]["max_retry_attempts"] == 3
        assert config["report"]["format"] == "table"
        assert config["report"]["max_results_display"] == 100
        assert config["debug_mode"] is False
        assert config["max_concurrent_requests"] == 10
    
    def test_load_all_returns_copy(self) -> None:
        """Test that load_all returns a copy of defaults."""
        handler = DefaultConfigHandler()
        
        config1 = handler.load_all()
        config2 = handler.load_all()
        
        # Should be equal but different objects
        assert config1 == config2
        assert config1 is not config2
        
        # Modifying one shouldn't affect the other
        config1["debug_mode"] = True
        assert config2["debug_mode"] is False
    
    def test_can_handle_source_default(self) -> None:
        """Test can_handle_source for default source type."""
        handler = DefaultConfigHandler()
        
        assert handler.can_handle_source("default") is True
        assert handler.can_handle_source("cli") is False
        assert handler.can_handle_source("file") is False


class TestConfigurationValidator:
    """Test cases for ConfigurationValidator."""
    
    def test_initialization(self) -> None:
        """Test ConfigurationValidator initialization."""
        validator = ConfigurationValidator()
        
        assert isinstance(validator._schema, dict)
        schema = validator.get_schema()
        
        # Check that schema contains expected sections
        assert "auth" in schema
        assert "report" in schema
        assert "mcp" in schema
        assert "logging" in schema
    
    def test_validate_setting_success(self) -> None:
        """Test successful validation of individual settings."""
        validator = ConfigurationValidator()
        
        # Test valid values
        assert validator.validate_setting("auth.timeout_seconds", 60) is True
        assert validator.validate_setting("report.format", "json") is True
        assert validator.validate_setting("debug_mode", True) is True
        assert validator.validate_setting("mcp.max_retries", 3) is True
    
    def test_validate_setting_type_error(self) -> None:
        """Test validation failure for wrong type."""
        validator = ConfigurationValidator()
        
        with pytest.raises(ConfigurationError, match="must be of type int"):
            validator.validate_setting("auth.timeout_seconds", "not_a_number")
    
    def test_validate_setting_choice_error(self) -> None:
        """Test validation failure for invalid choice."""
        validator = ConfigurationValidator()
        
        with pytest.raises(ConfigurationError, match="must be one of"):
            validator.validate_setting("report.format", "invalid_format")
    
    def test_validate_setting_range_error(self) -> None:
        """Test validation failure for out-of-range values."""
        validator = ConfigurationValidator()
        
        # Test minimum constraint
        with pytest.raises(ConfigurationError, match="must be >= 1"):
            validator.validate_setting("auth.timeout_seconds", 0)
        
        # Test maximum constraint
        with pytest.raises(ConfigurationError, match="must be <= 300"):
            validator.validate_setting("auth.timeout_seconds", 301)
    
    def test_validate_setting_optional_none(self) -> None:
        """Test validation of optional settings with None value."""
        validator = ConfigurationValidator()
        
        # Optional settings should accept None
        assert validator.validate_setting("report.output_path", None) is True
    
    def test_validate_setting_unknown_key(self) -> None:
        """Test validation of unknown setting key."""
        validator = ConfigurationValidator()
        
        # Unknown keys should pass validation (no schema defined)
        assert validator.validate_setting("unknown.key", "any_value") is True
    
    def test_validate_schema_success(self) -> None:
        """Test successful validation of complete configuration schema."""
        validator = ConfigurationValidator()
        
        valid_config = {
            "auth": {
                "timeout_seconds": 60,
                "max_retry_attempts": 3,
                "auth_method": "midway"
            },
            "report": {
                "format": "json",
                "max_results_display": 100
            },
            "debug_mode": False
        }
        
        assert validator.validate_schema(valid_config) is True
    
    def test_validate_schema_failure(self) -> None:
        """Test validation failure for invalid configuration schema."""
        validator = ConfigurationValidator()
        
        invalid_config = {
            "auth": {
                "timeout_seconds": -1,  # Invalid: negative
                "max_retry_attempts": 15  # Invalid: too large
            }
        }
        
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            validator.validate_schema(invalid_config)
    
    def test_get_validation_errors(self) -> None:
        """Test getting list of validation errors."""
        validator = ConfigurationValidator()
        
        invalid_config = {
            "auth": {
                "timeout_seconds": -1,
                "max_retry_attempts": 15,
                "auth_method": "invalid_method"
            },
            "report": {
                "format": "invalid_format",
                "max_results_display": 0
            }
        }
        
        errors = validator.get_validation_errors(invalid_config)
        
        # Should have multiple errors
        assert len(errors) > 0
        assert any("timeout_seconds" in error for error in errors)
        assert any("max_retry_attempts" in error for error in errors)
        assert any("auth_method" in error for error in errors)
        assert any("format" in error for error in errors)
        assert any("max_results_display" in error for error in errors)
    
    def test_get_validation_errors_nested_objects(self) -> None:
        """Test validation errors for nested object structure."""
        validator = ConfigurationValidator()
        
        invalid_config = {
            "auth": "not_an_object"  # Should be dict
        }
        
        errors = validator.get_validation_errors(invalid_config)
        
        assert len(errors) > 0
        assert any("must be an object" in error for error in errors)
    
    def test_get_schema(self) -> None:
        """Test getting validation schema."""
        validator = ConfigurationValidator()
        
        schema = validator.get_schema()
        
        # Should be a copy of the internal schema
        assert isinstance(schema, dict)
        assert schema is not validator._schema
        
        # Should contain expected structure
        assert "auth" in schema
        assert "report" in schema
        assert "mcp" in schema
        assert "logging" in schema
        
        # Check some specific schema definitions
        assert schema["auth"]["timeout_seconds"]["type"] is int
        assert schema["auth"]["timeout_seconds"]["min"] == 1
        assert schema["auth"]["timeout_seconds"]["max"] == 300
        
        assert "choices" in schema["report"]["format"]
        assert "table" in schema["report"]["format"]["choices"]


class TestHandlerChainIntegration:
    """Integration tests for handler chain functionality."""
    
    def test_handler_chain_setup(self, tmp_path: Path) -> None:
        """Test setting up a complete handler chain."""
        # Create handlers
        cli_handler = CommandLineConfigHandler()
        file_handler = FileConfigHandler(tmp_path)
        env_handler = EnvironmentConfigHandler()
        default_handler = DefaultConfigHandler()
        
        # Chain them together
        cli_handler.set_next(file_handler)
        file_handler.set_next(env_handler)
        env_handler.set_next(default_handler)
        
        # Test chain traversal
        result = cli_handler.handle("debug_mode")
        assert result is False  # Should come from default handler
    
    def test_handler_chain_precedence(self, tmp_path: Path) -> None:
        """Test that handler chain respects precedence order."""
        # Set up environment variable
        env_vars = {"TICKET_ANALYZER_DEBUG_MODE": "true"}
        
        with patch.dict(os.environ, env_vars):
            # Create config file
            config_data = {"debug_mode": False}
            config_file = tmp_path / "config.json"
            config_file.write_text(json.dumps(config_data))
            
            # Set up handlers
            cli_handler = CommandLineConfigHandler({"debug": True})
            file_handler = FileConfigHandler(tmp_path)
            env_handler = EnvironmentConfigHandler()
            default_handler = DefaultConfigHandler()
            
            # Chain in precedence order: CLI > File > Env > Default
            cli_handler.set_next(file_handler)
            file_handler.set_next(env_handler)
            env_handler.set_next(default_handler)
            
            # CLI should win
            result = cli_handler.handle("debug_mode")
            assert result is True  # From CLI
    
    def test_handler_chain_fallback(self, tmp_path: Path) -> None:
        """Test that handler chain falls back through the chain."""
        # Create handlers with different capabilities
        cli_handler = CommandLineConfigHandler()  # Empty
        file_handler = FileConfigHandler(tmp_path)  # No files
        env_handler = EnvironmentConfigHandler()  # No env vars
        default_handler = DefaultConfigHandler()  # Has defaults
        
        # Chain them
        cli_handler.set_next(file_handler)
        file_handler.set_next(env_handler)
        env_handler.set_next(default_handler)
        
        # Should fall back to default
        result = cli_handler.handle("debug_mode")
        assert result is False  # Default value
    
    def test_handler_error_recovery(self, tmp_path: Path) -> None:
        """Test that handler chain recovers from individual handler errors."""
        # Create invalid config file
        invalid_config = tmp_path / "config.json"
        invalid_config.write_text("{ invalid json }")
        
        # Set up handlers
        cli_handler = CommandLineConfigHandler()
        file_handler = FileConfigHandler(tmp_path)  # Will fail on invalid JSON
        env_handler = EnvironmentConfigHandler()
        default_handler = DefaultConfigHandler()
        
        # Chain them
        cli_handler.set_next(file_handler)
        file_handler.set_next(env_handler)
        env_handler.set_next(default_handler)
        
        # Should still work despite file handler error
        result = cli_handler.handle("debug_mode")
        assert result is False  # From default handler