"""Comprehensive tests for ConfigurationManager.

This module contains unit tests for the ConfigurationManager class,
covering configuration hierarchy, precedence, override behavior,
validation, and error scenarios.
"""

from __future__ import annotations
import pytest
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

from ticket_analyzer.config.config_manager import ConfigurationManager
from ticket_analyzer.config.handlers import (
    CommandLineConfigHandler,
    FileConfigHandler,
    EnvironmentConfigHandler,
    DefaultConfigHandler,
    ConfigurationValidator
)
from ticket_analyzer.models.config import ApplicationConfig, OutputFormat, LogLevel
from ticket_analyzer.models.exceptions import ConfigurationError


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""
    
    def test_initialization_default_config_dir(self) -> None:
        """Test ConfigurationManager initialization with default config directory."""
        manager = ConfigurationManager()
        
        expected_dir = Path.home() / ".ticket-analyzer"
        assert manager._config_dir == expected_dir
        assert manager._config_dir.exists()
        assert manager._config_dir.is_dir()
        
        # Check permissions (should be 0o700)
        stat_info = manager._config_dir.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "700"
    
    def test_initialization_custom_config_dir(self, tmp_path: Path) -> None:
        """Test ConfigurationManager initialization with custom config directory."""
        custom_dir = tmp_path / "custom_config"
        manager = ConfigurationManager(config_dir=custom_dir)
        
        assert manager._config_dir == custom_dir
        assert custom_dir.exists()
        assert custom_dir.is_dir()
    
    def test_setup_configuration_chain(self) -> None:
        """Test that configuration chain is properly set up."""
        manager = ConfigurationManager()
        
        # Check that chain is initialized
        assert manager._config_chain is not None
        assert isinstance(manager._config_chain, CommandLineConfigHandler)
        
        # Check source order
        expected_sources = ["cli", "file", "environment", "default"]
        assert manager._config_sources == expected_sources
    
    def test_load_config_default_values(self) -> None:
        """Test loading configuration with only default values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            config = manager.load_config()
            
            # Should contain default values
            assert isinstance(config, dict)
            assert "auth" in config
            assert "report" in config
            assert "mcp" in config
            assert "logging" in config
            
            # Check some default values
            assert config["auth"]["timeout_seconds"] == 60
            assert config["report"]["format"] == "table"
            assert config["debug_mode"] is False
    
    def test_load_config_caching(self) -> None:
        """Test that configuration is cached after first load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # First load
            config1 = manager.load_config()
            
            # Second load should return cached version
            config2 = manager.load_config()
            
            # Should be equal but different objects (copy)
            assert config1 == config2
            assert config1 is not config2
    
    def test_get_setting_existing_key(self) -> None:
        """Test getting an existing configuration setting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Get a known default setting
            timeout = manager.get_setting("auth.timeout_seconds")
            assert timeout == 60
    
    def test_get_setting_nested_key(self) -> None:
        """Test getting nested configuration setting using dot notation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Test nested key access
            format_value = manager.get_setting("report.format")
            assert format_value == "table"
            
            log_level = manager.get_setting("logging.level")
            assert log_level == "INFO"
    
    def test_get_setting_nonexistent_key(self) -> None:
        """Test getting non-existent configuration setting returns default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Non-existent key should return default
            value = manager.get_setting("nonexistent.key", "default_value")
            assert value == "default_value"
    
    def test_get_setting_without_default(self) -> None:
        """Test getting non-existent setting without default returns None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            value = manager.get_setting("nonexistent.key")
            assert value is None
    
    def test_set_setting_simple_key(self) -> None:
        """Test setting a simple configuration value."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Set a new value
            manager.set_setting("debug_mode", True)
            
            # Verify it was set
            assert manager.get_setting("debug_mode") is True
    
    def test_set_setting_nested_key(self) -> None:
        """Test setting a nested configuration value."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Set nested value
            manager.set_setting("auth.timeout_seconds", 120)
            
            # Verify it was set
            assert manager.get_setting("auth.timeout_seconds") == 120
    
    def test_set_setting_creates_nested_structure(self) -> None:
        """Test that setting nested key creates intermediate dictionaries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Set deeply nested value
            manager.set_setting("new.nested.deep.key", "value")
            
            # Verify structure was created
            assert manager.get_setting("new.nested.deep.key") == "value"
            
            # Verify intermediate dictionaries exist
            config = manager.load_config()
            assert isinstance(config["new"], dict)
            assert isinstance(config["new"]["nested"], dict)
            assert isinstance(config["new"]["nested"]["deep"], dict)
    
    def test_set_setting_invalidates_cache(self) -> None:
        """Test that setting a value invalidates the configuration cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Load config to populate cache
            original_config = manager.load_config()
            original_timeout = original_config["auth"]["timeout_seconds"]
            
            # Set new value
            manager.set_setting("auth.timeout_seconds", 999)
            
            # Load config again - should reflect new value
            new_config = manager.load_config()
            assert new_config["auth"]["timeout_seconds"] == 999
            assert new_config["auth"]["timeout_seconds"] != original_timeout
    
    def test_has_setting_existing_key(self) -> None:
        """Test checking for existing configuration setting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Check existing keys
            assert manager.has_setting("auth.timeout_seconds") is True
            assert manager.has_setting("report.format") is True
            assert manager.has_setting("debug_mode") is True
    
    def test_has_setting_nonexistent_key(self) -> None:
        """Test checking for non-existent configuration setting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Check non-existent keys
            assert manager.has_setting("nonexistent.key") is False
            assert manager.has_setting("auth.nonexistent") is False
    
    def test_get_all_settings(self) -> None:
        """Test getting all configuration settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            all_settings = manager.get_all_settings()
            
            # Should be a dictionary with expected sections
            assert isinstance(all_settings, dict)
            assert "auth" in all_settings
            assert "report" in all_settings
            assert "mcp" in all_settings
            assert "logging" in all_settings
            
            # Should contain expected values
            assert all_settings["auth"]["timeout_seconds"] == 60
            assert all_settings["report"]["format"] == "table"
    
    def test_reload_config(self) -> None:
        """Test reloading configuration clears cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Load initial config
            config1 = manager.load_config()
            
            # Verify cache is populated
            assert manager._cached_config is not None
            
            # Reload config
            config2 = manager.reload_config()
            
            # Should get fresh config
            assert config1 == config2
            assert config1 is not config2
    
    def test_get_config_sources(self) -> None:
        """Test getting configuration sources list."""
        manager = ConfigurationManager()
        
        sources = manager.get_config_sources()
        expected = ["cli", "file", "environment", "default"]
        
        assert sources == expected
        assert sources is not manager._config_sources  # Should be a copy
    
    def test_get_config_info(self) -> None:
        """Test getting configuration information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            info = manager.get_config_info()
            
            # Check expected fields
            assert "config_dir" in info
            assert "sources" in info
            assert "cached" in info
            assert "validator_set" in info
            assert "handlers" in info
            
            # Check values
            assert info["config_dir"] == str(manager._config_dir)
            assert info["sources"] == ["cli", "file", "environment", "default"]
            assert isinstance(info["cached"], bool)
            assert isinstance(info["validator_set"], bool)
            assert isinstance(info["handlers"], dict)
    
    def test_validate_config_success(self) -> None:
        """Test successful configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            config = manager.load_config()
            
            # Should validate successfully
            assert manager.validate_config(config) is True
    
    def test_validate_config_with_validator(self) -> None:
        """Test configuration validation with custom validator."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Set up mock validator
            mock_validator = Mock()
            mock_validator.validate_schema.return_value = True
            manager.set_validator(mock_validator)
            
            config = {"test": "value"}
            
            # Validate
            result = manager.validate_config(config)
            
            assert result is True
            mock_validator.validate_schema.assert_called_once_with(config)
    
    def test_validate_config_failure(self) -> None:
        """Test configuration validation failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Invalid config (negative timeout)
            invalid_config = {
                "auth": {
                    "timeout_seconds": -1
                }
            }
            
            with pytest.raises(ConfigurationError, match="Configuration validation failed"):
                manager.validate_config(invalid_config)
    
    def test_set_validator(self) -> None:
        """Test setting configuration validator."""
        manager = ConfigurationManager()
        
        mock_validator = Mock()
        manager.set_validator(mock_validator)
        
        assert manager._validator is mock_validator
    
    def test_export_config_json(self, tmp_path: Path) -> None:
        """Test exporting configuration to JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            output_file = tmp_path / "exported_config.json"
            
            # Export configuration
            manager.export_config(output_file, "json")
            
            # Verify file was created
            assert output_file.exists()
            
            # Verify content
            with open(output_file, 'r') as f:
                exported_data = json.load(f)
            
            # Should contain expected sections
            assert "auth" in exported_data
            assert "report" in exported_data
            assert exported_data["auth"]["timeout_seconds"] == 60
    
    def test_export_config_unsupported_format(self, tmp_path: Path) -> None:
        """Test exporting configuration with unsupported format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            output_file = tmp_path / "config.xml"
            
            with pytest.raises(ConfigurationError, match="Unsupported export format: xml"):
                manager.export_config(output_file, "xml")


class TestConfigurationHierarchy:
    """Test cases for configuration hierarchy and precedence."""
    
    def test_configuration_precedence_cli_over_file(self, tmp_path: Path) -> None:
        """Test that CLI arguments override file configuration."""
        # Create config file
        config_file = tmp_path / "config.json"
        file_config = {
            "auth": {"timeout_seconds": 30},
            "report": {"format": "csv"}
        }
        config_file.write_text(json.dumps(file_config))
        
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Set CLI args that should override file
        cli_handler = manager._config_chain
        cli_handler.set_cli_args({
            "timeout": 120,  # Should override file's 30
            "format": "json"  # Should override file's csv
        })
        
        config = manager.load_config()
        
        # CLI values should take precedence
        assert config["auth"]["timeout_seconds"] == 120
        assert config["report"]["format"] == "json"
    
    def test_configuration_precedence_file_over_env(self, tmp_path: Path) -> None:
        """Test that file configuration overrides environment variables."""
        # Set environment variables
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "90",
            "TICKET_ANALYZER_REPORT__FORMAT": "yaml"
        }
        
        with patch.dict(os.environ, env_vars):
            # Create config file that should override env vars
            config_file = tmp_path / "config.json"
            file_config = {
                "auth": {"timeout_seconds": 45},
                "report": {"format": "html"}
            }
            config_file.write_text(json.dumps(file_config))
            
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # File values should take precedence over env vars
            assert config["auth"]["timeout_seconds"] == 45
            assert config["report"]["format"] == "html"
    
    def test_configuration_precedence_env_over_default(self) -> None:
        """Test that environment variables override default values."""
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "150",
            "TICKET_ANALYZER_DEBUG_MODE": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            with tempfile.TemporaryDirectory() as temp_dir:
                manager = ConfigurationManager(config_dir=Path(temp_dir))
                config = manager.load_config()
                
                # Env values should override defaults
                assert config["auth"]["timeout_seconds"] == 150
                assert config["debug_mode"] is True
    
    def test_configuration_precedence_full_hierarchy(self, tmp_path: Path) -> None:
        """Test complete configuration hierarchy: CLI > File > Env > Default."""
        # Set environment variables (lowest precedence of tested sources)
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "200",
            "TICKET_ANALYZER_REPORT__FORMAT": "yaml",
            "TICKET_ANALYZER_DEBUG_MODE": "true",
            "TICKET_ANALYZER_AUTH__MAX_RETRY_ATTEMPTS": "5"
        }
        
        with patch.dict(os.environ, env_vars):
            # Create config file (middle precedence)
            config_file = tmp_path / "config.json"
            file_config = {
                "auth": {"timeout_seconds": 100},  # Should override env
                "report": {"format": "csv"},  # Should override env
                "logging": {"level": "DEBUG"}  # New value not in env
            }
            config_file.write_text(json.dumps(file_config))
            
            manager = ConfigurationManager(config_dir=tmp_path)
            
            # Set CLI args (highest precedence)
            cli_handler = manager._config_chain
            cli_handler.set_cli_args({
                "timeout": 50,  # Should override file and env
                "verbose": True  # New value not in file or env
            })
            
            config = manager.load_config()
            
            # Check precedence:
            # CLI overrides everything
            assert config["auth"]["timeout_seconds"] == 50
            assert config["report"]["verbose"] is True
            
            # File overrides env and default
            assert config["report"]["format"] == "csv"
            assert config["logging"]["level"] == "DEBUG"
            
            # Env overrides default
            assert config["debug_mode"] is True
            assert config["auth"]["max_retry_attempts"] == 5
            
            # Default values where nothing else specified
            assert config["mcp"]["connection_timeout"] == 30  # Default value
    
    def test_deep_merge_behavior(self, tmp_path: Path) -> None:
        """Test that nested dictionaries are properly merged."""
        # Create config file with partial auth config
        config_file = tmp_path / "config.json"
        file_config = {
            "auth": {
                "timeout_seconds": 90,
                "auth_method": "kerberos"
                # Missing other auth fields
            }
        }
        config_file.write_text(json.dumps(file_config))
        
        manager = ConfigurationManager(config_dir=tmp_path)
        config = manager.load_config()
        
        # Should have file values
        assert config["auth"]["timeout_seconds"] == 90
        assert config["auth"]["auth_method"] == "kerberos"
        
        # Should have default values for missing fields
        assert config["auth"]["max_retry_attempts"] == 3  # Default
        assert config["auth"]["require_auth"] is True  # Default
    
    def test_configuration_override_behavior(self, tmp_path: Path) -> None:
        """Test that higher precedence sources completely override lower ones for conflicts."""
        env_vars = {
            "TICKET_ANALYZER_REPORT__MAX_RESULTS_DISPLAY": "500"
        }
        
        with patch.dict(os.environ, env_vars):
            # File config with different value
            config_file = tmp_path / "config.json"
            file_config = {
                "report": {"max_results_display": 200}
            }
            config_file.write_text(json.dumps(file_config))
            
            manager = ConfigurationManager(config_dir=tmp_path)
            config = manager.load_config()
            
            # File should override env completely
            assert config["report"]["max_results_display"] == 200


class TestConfigurationErrorHandling:
    """Test cases for configuration error handling scenarios."""
    
    def test_load_config_with_handler_failure(self, tmp_path: Path) -> None:
        """Test configuration loading when a handler fails."""
        # Create invalid JSON file
        invalid_config_file = tmp_path / "config.json"
        invalid_config_file.write_text("{ invalid json }")
        
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Should still load successfully with defaults (handler failure is logged but not fatal)
        config = manager.load_config()
        
        # Should contain default values
        assert config["auth"]["timeout_seconds"] == 60
        assert config["report"]["format"] == "table"
    
    def test_load_config_validation_failure(self, tmp_path: Path) -> None:
        """Test configuration loading with validation failure."""
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Set up validator that always fails
        mock_validator = Mock()
        mock_validator.validate_schema.return_value = False
        mock_validator.get_validation_errors.return_value = ["Test validation error"]
        manager.set_validator(mock_validator)
        
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            manager.load_config()
    
    def test_get_setting_with_load_failure(self, tmp_path: Path) -> None:
        """Test getting setting when config loading fails."""
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Mock load_config to raise exception
        with patch.object(manager, 'load_config', side_effect=ConfigurationError("Load failed")):
            # Should return default value
            value = manager.get_setting("test.key", "default")
            assert value == "default"
    
    def test_set_setting_with_invalid_nested_path(self, tmp_path: Path) -> None:
        """Test setting value when intermediate path is not a dictionary."""
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # First set a non-dict value
        manager.set_setting("test", "string_value")
        
        # Try to set nested value under string - should fail
        with pytest.raises(ConfigurationError, match="Cannot set nested key"):
            manager.set_setting("test.nested.key", "value")
    
    def test_has_setting_with_load_failure(self, tmp_path: Path) -> None:
        """Test checking setting existence when config loading fails."""
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Mock load_config to raise exception
        with patch.object(manager, 'load_config', side_effect=ConfigurationError("Load failed")):
            # Should return False
            assert manager.has_setting("test.key") is False
    
    def test_export_config_file_write_failure(self, tmp_path: Path) -> None:
        """Test export configuration when file write fails."""
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Try to write to read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        output_file = readonly_dir / "config.json"
        
        with pytest.raises(ConfigurationError, match="Failed to export configuration"):
            manager.export_config(output_file, "json")
    
    def test_configuration_with_missing_config_dir_permissions(self) -> None:
        """Test configuration manager with insufficient permissions."""
        # This test is platform-dependent and may not work on all systems
        # Skip on Windows or if running as root
        import platform
        if platform.system() == "Windows" or os.getuid() == 0:
            pytest.skip("Permission test not applicable on Windows or as root")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory with no write permissions
            no_write_dir = Path(temp_dir) / "no_write"
            no_write_dir.mkdir()
            no_write_dir.chmod(0o444)  # Read-only
            
            try:
                # Should handle permission error gracefully
                manager = ConfigurationManager(config_dir=no_write_dir)
                
                # Should still be able to load defaults
                config = manager.load_config()
                assert isinstance(config, dict)
                
            finally:
                # Restore permissions for cleanup
                no_write_dir.chmod(0o755)


class TestConfigurationManagerIntegration:
    """Integration tests for ConfigurationManager with real handlers."""
    
    def test_real_file_handler_json_integration(self, tmp_path: Path) -> None:
        """Test integration with real JSON file handler."""
        # Create JSON config file
        config_file = tmp_path / "config.json"
        config_data = {
            "auth": {
                "timeout_seconds": 75,
                "auth_method": "kerberos",
                "max_retry_attempts": 4
            },
            "report": {
                "format": "html",
                "include_charts": False,
                "max_results_display": 250
            },
            "debug_mode": True
        }
        config_file.write_text(json.dumps(config_data, indent=2))
        
        manager = ConfigurationManager(config_dir=tmp_path)
        config = manager.load_config()
        
        # Verify file values are loaded
        assert config["auth"]["timeout_seconds"] == 75
        assert config["auth"]["auth_method"] == "kerberos"
        assert config["auth"]["max_retry_attempts"] == 4
        assert config["report"]["format"] == "html"
        assert config["report"]["include_charts"] is False
        assert config["report"]["max_results_display"] == 250
        assert config["debug_mode"] is True
        
        # Verify defaults are preserved for unspecified values
        assert config["auth"]["require_auth"] is True  # Default
        assert config["mcp"]["connection_timeout"] == 30  # Default
    
    def test_real_file_handler_ini_integration(self, tmp_path: Path) -> None:
        """Test integration with real INI file handler."""
        # Create INI config file
        config_file = tmp_path / "config.ini"
        ini_content = """
[auth]
timeout_seconds = 45
auth_method = midway
auto_refresh = false

[report]
format = csv
color_output = false
max_results_display = 150

[logging]
level = WARNING
sanitize_logs = true
"""
        config_file.write_text(ini_content)
        
        manager = ConfigurationManager(config_dir=tmp_path)
        config = manager.load_config()
        
        # Verify INI values are loaded and converted
        assert config["auth"]["timeout_seconds"] == 45
        assert config["auth"]["auth_method"] == "midway"
        assert config["auth"]["auto_refresh"] is False
        assert config["report"]["format"] == "csv"
        assert config["report"]["color_output"] is False
        assert config["report"]["max_results_display"] == 150
        assert config["logging"]["level"] == "WARNING"
        assert config["logging"]["sanitize_logs"] is True
    
    def test_real_environment_handler_integration(self) -> None:
        """Test integration with real environment variable handler."""
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "180",
            "TICKET_ANALYZER_AUTH__AUTO_REFRESH": "false",
            "TICKET_ANALYZER_REPORT__FORMAT": "yaml",
            "TICKET_ANALYZER_REPORT__VERBOSE": "true",
            "TICKET_ANALYZER_DEBUG_MODE": "true",
            "TICKET_ANALYZER_MAX_CONCURRENT_REQUESTS": "25"
        }
        
        with patch.dict(os.environ, env_vars):
            with tempfile.TemporaryDirectory() as temp_dir:
                manager = ConfigurationManager(config_dir=Path(temp_dir))
                config = manager.load_config()
                
                # Verify environment values are loaded and converted
                assert config["auth"]["timeout_seconds"] == 180
                assert config["auth"]["auto_refresh"] is False
                assert config["report"]["format"] == "yaml"
                assert config["report"]["verbose"] is True
                assert config["debug_mode"] is True
                assert config["max_concurrent_requests"] == 25
    
    def test_multiple_config_files_precedence(self, tmp_path: Path) -> None:
        """Test precedence when multiple config files exist."""
        # Create multiple config files
        config_json = tmp_path / "config.json"
        config_json_data = {
            "auth": {"timeout_seconds": 100},
            "report": {"format": "json"}
        }
        config_json.write_text(json.dumps(config_json_data))
        
        config_ini = tmp_path / ".ticket-analyzer.ini"
        ini_content = """
[auth]
timeout_seconds = 200
max_retry_attempts = 5

[report]
format = csv
verbose = true
"""
        config_ini.write_text(ini_content)
        
        manager = ConfigurationManager(config_dir=tmp_path)
        config = manager.load_config()
        
        # Later files should override earlier ones
        # (based on the order in _config_files list)
        # .ticket-analyzer.ini comes after config.json, so it should win
        assert config["auth"]["timeout_seconds"] == 200
        assert config["auth"]["max_retry_attempts"] == 5
        assert config["report"]["format"] == "csv"
        assert config["report"]["verbose"] is True
    
    def test_configuration_validation_integration(self, tmp_path: Path) -> None:
        """Test integration with configuration validation."""
        # Create config with invalid values
        config_file = tmp_path / "config.json"
        invalid_config = {
            "auth": {
                "timeout_seconds": -1,  # Invalid: negative
                "max_retry_attempts": 15  # Invalid: too large
            },
            "report": {
                "max_results_display": 0  # Invalid: zero
            }
        }
        config_file.write_text(json.dumps(invalid_config))
        
        manager = ConfigurationManager(config_dir=tmp_path)
        
        # Set up real validator
        validator = ConfigurationValidator()
        manager.set_validator(validator)
        
        # Should raise validation error
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            manager.load_config()
    
    def test_end_to_end_configuration_workflow(self, tmp_path: Path) -> None:
        """Test complete end-to-end configuration workflow."""
        # Set up environment variables
        env_vars = {
            "TICKET_ANALYZER_AUTH__TIMEOUT_SECONDS": "300",
            "TICKET_ANALYZER_DEBUG_MODE": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            # Create config file
            config_file = tmp_path / "config.json"
            file_config = {
                "auth": {
                    "timeout_seconds": 120,  # Should override env
                    "auth_method": "kerberos"
                },
                "report": {
                    "format": "html",
                    "include_charts": True
                }
            }
            config_file.write_text(json.dumps(file_config))
            
            # Initialize manager
            manager = ConfigurationManager(config_dir=tmp_path)
            
            # Set CLI args
            cli_handler = manager._config_chain
            cli_handler.set_cli_args({
                "format": "json",  # Should override file
                "verbose": True
            })
            
            # Load and verify configuration
            config = manager.load_config()
            
            # Test getting individual settings
            assert manager.get_setting("auth.timeout_seconds") == 120  # File overrides env
            assert manager.get_setting("report.format") == "json"  # CLI overrides file
            assert manager.get_setting("debug_mode") is True  # From env
            assert manager.get_setting("report.verbose") is True  # From CLI
            
            # Test setting new values
            manager.set_setting("custom.new_setting", "test_value")
            assert manager.get_setting("custom.new_setting") == "test_value"
            
            # Test configuration info
            info = manager.get_config_info()
            assert info["cached"] is True
            assert len(info["handlers"]) == 4  # CLI, File, Env, Default
            
            # Test reload
            reloaded_config = manager.reload_config()
            assert reloaded_config == config
            
            # Test export
            export_file = tmp_path / "exported.json"
            manager.export_config(export_file, "json")
            assert export_file.exists()
            
            # Verify exported content
            with open(export_file, 'r') as f:
                exported = json.load(f)
            assert exported["auth"]["timeout_seconds"] == 120
            assert exported["report"]["format"] == "json"