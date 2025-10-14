"""Tests for the config CLI command.

This module tests the config command functionality including show, set, unset,
validate, and init subcommands with comprehensive validation and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

from ticket_analyzer.cli.commands.config import (
    config_command, show_config, set_config, unset_config, 
    validate_config, init_config, _convert_config_value
)
from ticket_analyzer.models.exceptions import ConfigurationError


class TestConfigCommand:
    """Test cases for config command group."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_config_help(self, runner):
        """Test config command help text."""
        result = runner.invoke(config_command, ['--help'])
        
        assert result.exit_code == 0
        assert "Configuration management commands" in result.output
        assert "show" in result.output
        assert "set" in result.output
        assert "unset" in result.output
        assert "validate" in result.output
        assert "init" in result.output
    
    def test_config_no_subcommand(self, runner):
        """Test config command without subcommand shows help."""
        result = runner.invoke(config_command, [])
        
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestShowConfigCommand:
    """Test cases for config show command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.config.DependencyContainer') as mock:
            container = Mock()
            config_manager = Mock()
            config_manager.get_effective_config.return_value = {
                'auth': {'timeout_seconds': 60},
                'report': {'format': 'json'},
                'debug_mode': False
            }
            config_manager.get_config_file_path.return_value = Path('/test/config.json')
            container.config_manager = config_manager
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    def test_show_config_basic(self, runner, mock_container, mock_cli_context):
        """Test basic config show command."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, [])
            
            assert result.exit_code == 0
            mock_container.config_manager.get_effective_config.assert_called_once()
    
    def test_show_config_with_file(self, runner, mock_container, mock_cli_context, temp_config_file):
        """Test config show with specific file."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, ['--config-file', temp_config_file])
            
            assert result.exit_code == 0
            mock_container.config_manager.load_from_file.assert_called_once()
    
    def test_show_config_with_section(self, runner, mock_container, mock_cli_context):
        """Test config show with specific section."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, ['--section', 'auth'])
            
            assert result.exit_code == 0
            # Should filter to auth section only
    
    def test_show_config_json_format(self, runner, mock_container, mock_cli_context):
        """Test config show with JSON format."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, ['--format', 'json'])
            
            assert result.exit_code == 0
            # Should output JSON format
    
    def test_show_config_yaml_format(self, runner, mock_container, mock_cli_context):
        """Test config show with YAML format."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('yaml.dump') as mock_yaml:
                mock_yaml.return_value = "test: yaml"
                
                result = runner.invoke(show_config, ['--format', 'yaml'])
                
                assert result.exit_code == 0
                mock_yaml.assert_called_once()
    
    def test_show_config_with_defaults(self, runner, mock_container, mock_cli_context):
        """Test config show with defaults included."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, ['--show-defaults'])
            
            assert result.exit_code == 0
            mock_container.config_manager.get_default_config.assert_called_once()
            mock_container.config_manager.merge_with_defaults.assert_called_once()
    
    def test_show_config_with_sources(self, runner, mock_container, mock_cli_context):
        """Test config show with source information."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, ['--show-sources'])
            
            assert result.exit_code == 0
            mock_container.config_manager.add_source_info.assert_called_once()
    
    def test_show_config_section_not_found(self, runner, mock_container, mock_cli_context):
        """Test config show with non-existent section."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, ['--section', 'nonexistent'])
            
            assert result.exit_code == 0
            assert "Section 'nonexistent' not found" in result.output
    
    def test_show_config_verbose(self, runner, mock_container, mock_cli_context):
        """Test config show with verbose output."""
        mock_cli_context.verbose = True
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, [])
            
            assert result.exit_code == 0
            assert "Configuration loaded from:" in result.output
    
    def test_show_config_error_handling(self, runner, mock_container, mock_cli_context):
        """Test config show error handling."""
        mock_container.config_manager.get_effective_config.side_effect = ConfigurationError("Config error")
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(show_config, [])
            
            assert result.exit_code == 2
            assert "Configuration error" in result.output


class TestSetConfigCommand:
    """Test cases for config set command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.config.DependencyContainer') as mock:
            container = Mock()
            config_manager = Mock()
            config_manager.get_default_config_file.return_value = Path('/test/config.json')
            container.config_manager = config_manager
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    def test_set_config_basic(self, runner, mock_container, mock_cli_context):
        """Test basic config set command."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(set_config, ['output_format', 'json'])
            
            assert result.exit_code == 0
            assert "Configuration updated" in result.output
            mock_container.config_manager.set_config_value.assert_called_once()
    
    def test_set_config_with_section(self, runner, mock_container, mock_cli_context):
        """Test config set with section."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(set_config, [
                'timeout', '120',
                '--section', 'auth',
                '--type', 'int'
            ])
            
            assert result.exit_code == 0
            
            # Verify correct parameters passed
            call_args = mock_container.config_manager.set_config_value.call_args
            assert call_args[1]['key'] == 'timeout'
            assert call_args[1]['value'] == 120  # Should be converted to int
            assert call_args[1]['section'] == 'auth'
    
    def test_set_config_with_file(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config set with specific file."""
        config_file = tmp_path / "custom_config.json"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(set_config, [
                'debug_mode', 'true',
                '--config-file', str(config_file),
                '--type', 'bool'
            ])
            
            assert result.exit_code == 0
            
            # Verify correct file path passed
            call_args = mock_container.config_manager.set_config_value.call_args
            assert call_args[1]['config_file'] == config_file
    
    def test_set_config_type_conversions(self, runner, mock_container, mock_cli_context):
        """Test config set with different type conversions."""
        test_cases = [
            ('string_val', 'test', 'string', 'test'),
            ('int_val', '42', 'int', 42),
            ('float_val', '3.14', 'float', 3.14),
            ('bool_val', 'true', 'bool', True),
            ('list_val', 'a,b,c', 'list', ['a', 'b', 'c'])
        ]
        
        for key, value, type_name, expected in test_cases:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(set_config, [key, value, '--type', type_name])
                
                assert result.exit_code == 0
                
                # Verify conversion
                call_args = mock_container.config_manager.set_config_value.call_args
                assert call_args[1]['value'] == expected
    
    def test_set_config_with_backup(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config set creates backup."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('shutil.copy2') as mock_copy:
                result = runner.invoke(set_config, ['key', 'value', '--create-backup'])
                
                assert result.exit_code == 0
                mock_copy.assert_called_once()
    
    def test_set_config_verbose(self, runner, mock_container, mock_cli_context):
        """Test config set with verbose output."""
        mock_cli_context.verbose = True
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(set_config, ['key', 'value'])
            
            assert result.exit_code == 0
            assert "Updated file:" in result.output
    
    def test_set_config_error_handling(self, runner, mock_container, mock_cli_context):
        """Test config set error handling."""
        mock_container.config_manager.set_config_value.side_effect = ConfigurationError("Set error")
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(set_config, ['key', 'value'])
            
            assert result.exit_code == 2
            assert "Configuration error" in result.output


class TestUnsetConfigCommand:
    """Test cases for config unset command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.config.DependencyContainer') as mock:
            container = Mock()
            config_manager = Mock()
            config_manager.get_default_config_file.return_value = Path('/test/config.json')
            container.config_manager = config_manager
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    def test_unset_config_basic(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test basic config unset command."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(unset_config, ['test'])
            
            assert result.exit_code == 0
            assert "Configuration removed" in result.output
            mock_container.config_manager.unset_config_value.assert_called_once()
    
    def test_unset_config_with_section(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config unset with section."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"auth": {"timeout": 60}}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(unset_config, ['timeout', '--section', 'auth'])
            
            assert result.exit_code == 0
            
            # Verify correct parameters
            call_args = mock_container.config_manager.unset_config_value.call_args
            assert call_args[1]['key'] == 'timeout'
            assert call_args[1]['section'] == 'auth'
    
    def test_unset_config_file_not_exists(self, runner, mock_container, mock_cli_context):
        """Test config unset with non-existent file."""
        mock_container.config_manager.get_default_config_file.return_value = Path('/nonexistent.json')
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(unset_config, ['key'])
            
            assert result.exit_code == 2
            assert "Configuration file not found" in result.output
    
    def test_unset_config_with_backup(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config unset creates backup."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('shutil.copy2') as mock_copy:
                result = runner.invoke(unset_config, ['test', '--create-backup'])
                
                assert result.exit_code == 0
                mock_copy.assert_called_once()


class TestValidateConfigCommand:
    """Test cases for config validate command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.config.DependencyContainer') as mock:
            container = Mock()
            config_manager = Mock()
            config_manager.get_default_config_file.return_value = Path('/test/config.json')
            container.config_manager = config_manager
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    def test_validate_config_success(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test successful config validation."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        # Mock successful validation
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        mock_container.config_manager.validate_config.return_value = validation_result
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(validate_config, [])
            
            assert result.exit_code == 0
            assert "Configuration validation passed" in result.output
    
    def test_validate_config_with_errors(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config validation with errors."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        # Mock validation with errors
        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.errors = ["Invalid timeout value", "Missing required field"]
        validation_result.warnings = ["Deprecated setting"]
        validation_result.fixable_issues = []
        mock_container.config_manager.validate_config.return_value = validation_result
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(validate_config, [])
            
            assert result.exit_code == 2
            assert "Configuration validation failed" in result.output
            assert "Invalid timeout value" in result.output
            assert "Deprecated setting" in result.output
    
    def test_validate_config_with_fixes(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config validation with automatic fixes."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        # Mock validation with fixable issues
        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.errors = []
        validation_result.warnings = ["Fixable issue"]
        validation_result.fixable_issues = ["timeout_format"]
        mock_container.config_manager.validate_config.return_value = validation_result
        mock_container.config_manager.fix_config_issues.return_value = True
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(validate_config, ['--fix-issues'])
            
            assert result.exit_code == 0
            assert "Configuration issues fixed" in result.output
    
    def test_validate_config_file_not_exists(self, runner, mock_container, mock_cli_context):
        """Test config validation with non-existent file."""
        mock_container.config_manager.get_default_config_file.return_value = Path('/nonexistent.json')
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(validate_config, [])
            
            assert result.exit_code == 0
            assert "Configuration file not found" in result.output
            assert "Using default configuration values" in result.output
    
    def test_validate_config_strict_mode(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config validation in strict mode."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        mock_container.config_manager.get_default_config_file.return_value = config_file
        
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        mock_container.config_manager.validate_config.return_value = validation_result
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(validate_config, ['--strict'])
            
            assert result.exit_code == 0
            
            # Verify strict mode was passed
            call_args = mock_container.config_manager.validate_config.call_args
            assert call_args[1]['strict_mode'] is True


class TestInitConfigCommand:
    """Test cases for config init command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.config.DependencyContainer') as mock:
            container = Mock()
            config_manager = Mock()
            container.config_manager = config_manager
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    def test_init_config_basic(self, runner, mock_container, mock_cli_context):
        """Test basic config init command."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                result = runner.invoke(init_config, [])
                
                assert result.exit_code == 0
                assert "Configuration file created" in result.output
                mock_container.config_manager.create_config_file.assert_called_once()
    
    def test_init_config_with_format(self, runner, mock_container, mock_cli_context):
        """Test config init with specific format."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('pathlib.Path.mkdir'):
                result = runner.invoke(init_config, ['--format', 'ini'])
                
                assert result.exit_code == 0
                
                # Verify format parameter
                call_args = mock_container.config_manager.create_config_file.call_args
                assert call_args[1]['format'] == 'ini'
    
    def test_init_config_with_template(self, runner, mock_container, mock_cli_context):
        """Test config init with specific template."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('pathlib.Path.mkdir'):
                result = runner.invoke(init_config, ['--template', 'comprehensive'])
                
                assert result.exit_code == 0
                
                # Verify template parameter
                call_args = mock_container.config_manager.create_config_file.call_args
                assert call_args[1]['template'] == 'comprehensive'
    
    def test_init_config_file_exists(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config init with existing file."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"existing": "config"}')
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(init_config, ['--config-file', str(config_file)])
            
            assert result.exit_code == 2
            assert "Configuration file already exists" in result.output
    
    def test_init_config_overwrite(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test config init with overwrite option."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"existing": "config"}')
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(init_config, [
                '--config-file', str(config_file),
                '--overwrite'
            ])
            
            assert result.exit_code == 0
            assert "Configuration file created" in result.output
    
    def test_init_config_verbose(self, runner, mock_container, mock_cli_context):
        """Test config init with verbose output."""
        mock_cli_context.verbose = True
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            with patch('pathlib.Path.mkdir'):
                result = runner.invoke(init_config, [])
                
                assert result.exit_code == 0
                assert "Format:" in result.output
                assert "Template:" in result.output


class TestConfigValueConversion:
    """Test cases for configuration value conversion."""
    
    def test_convert_string_value(self):
        """Test string value conversion."""
        result = _convert_config_value("test_string", "string")
        assert result == "test_string"
        assert isinstance(result, str)
    
    def test_convert_int_value(self):
        """Test integer value conversion."""
        result = _convert_config_value("42", "int")
        assert result == 42
        assert isinstance(result, int)
    
    def test_convert_float_value(self):
        """Test float value conversion."""
        result = _convert_config_value("3.14", "float")
        assert result == 3.14
        assert isinstance(result, float)
    
    def test_convert_bool_values(self):
        """Test boolean value conversion."""
        true_values = ["true", "True", "TRUE", "yes", "Yes", "1", "on", "On"]
        false_values = ["false", "False", "FALSE", "no", "No", "0", "off", "Off"]
        
        for value in true_values:
            result = _convert_config_value(value, "bool")
            assert result is True
        
        for value in false_values:
            result = _convert_config_value(value, "bool")
            assert result is False
    
    def test_convert_list_value(self):
        """Test list value conversion."""
        result = _convert_config_value("item1,item2,item3", "list")
        assert result == ["item1", "item2", "item3"]
        assert isinstance(result, list)
        
        # Test with spaces
        result = _convert_config_value("item1, item2 , item3", "list")
        assert result == ["item1", "item2", "item3"]
    
    def test_convert_invalid_int(self):
        """Test invalid integer conversion raises error."""
        with pytest.raises(ValueError):
            _convert_config_value("not_a_number", "int")
    
    def test_convert_invalid_float(self):
        """Test invalid float conversion raises error."""
        with pytest.raises(ValueError):
            _convert_config_value("not_a_float", "float")


class TestConfigCommandIntegration:
    """Integration tests for config commands."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_config_workflow_integration(self, runner, tmp_path):
        """Test complete config workflow: init -> set -> show -> validate."""
        config_file = tmp_path / "test_config.json"
        
        with patch('ticket_analyzer.cli.commands.config.DependencyContainer') as mock_container:
            container = Mock()
            config_manager = Mock()
            
            # Mock for init
            config_manager.create_config_file.return_value = None
            
            # Mock for set
            config_manager.get_default_config_file.return_value = config_file
            config_manager.set_config_value.return_value = None
            
            # Mock for show
            config_manager.get_effective_config.return_value = {
                'test_key': 'test_value'
            }
            
            # Mock for validate
            validation_result = Mock()
            validation_result.is_valid = True
            validation_result.errors = []
            validation_result.warnings = []
            config_manager.validate_config.return_value = validation_result
            
            container.config_manager = config_manager
            mock_container.return_value = container
            
            # 1. Initialize config
            result = runner.invoke(init_config, ['--config-file', str(config_file)])
            assert result.exit_code == 0
            
            # 2. Set a value
            result = runner.invoke(set_config, ['test_key', 'test_value'])
            assert result.exit_code == 0
            
            # 3. Show config
            result = runner.invoke(show_config, [])
            assert result.exit_code == 0
            
            # 4. Validate config
            result = runner.invoke(validate_config, [])
            assert result.exit_code == 0