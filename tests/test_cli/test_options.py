"""Tests for CLI options and custom parameter types.

This module tests the reusable CLI options, custom parameter types,
and validation functions for consistent CLI behavior across commands.
"""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pathlib import Path
import click
from click.testing import CliRunner

from ticket_analyzer.cli.options import (
    TicketIDType, DateRangeType, ConfigFileType, OutputFormatType,
    EnvVarOption, ticket_ids_option, date_range_option, config_file_option,
    output_format_option, output_file_option, verbose_option, max_results_option,
    timeout_option, validate_ticket_id_format, validate_date_range_consistency,
    validate_output_consistency, add_help_examples, HELP_EXAMPLES
)


class TestTicketIDType:
    """Test cases for TicketIDType parameter type."""
    
    @pytest.fixture
    def ticket_id_type(self):
        """Create TicketIDType instance."""
        return TicketIDType()
    
    def test_valid_ticket_ids(self, ticket_id_type):
        """Test conversion of valid ticket IDs."""
        valid_ids = [
            ("ABC-123456", "ABC-123456"),
            ("defgh-789012", "DEFGH-789012"),  # Should normalize to uppercase
            ("T123456", "T123456"),
            ("t1234567890", "T1234567890"),
            ("P123456", "P123456"),
            ("p1234567890", "P1234567890"),
            ("V1234567890", "V1234567890")
        ]
        
        for input_id, expected in valid_ids:
            result = ticket_id_type.convert(input_id, None, None)
            assert result == expected
    
    def test_invalid_ticket_ids(self, ticket_id_type):
        """Test conversion of invalid ticket IDs."""
        invalid_ids = [
            "",
            "INVALID",
            "123456",
            "ABC-",
            "T12345",  # Too short
            "X123456"  # Invalid prefix
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(click.BadParameter):
                ticket_id_type.convert(invalid_id, None, None)
    
    def test_ticket_id_type_name(self, ticket_id_type):
        """Test TicketIDType name property."""
        assert ticket_id_type.name == "ticket_id"


class TestDateRangeType:
    """Test cases for DateRangeType parameter type."""
    
    @pytest.fixture
    def date_range_type(self):
        """Create DateRangeType instance."""
        return DateRangeType()
    
    def test_predefined_date_ranges(self, date_range_type):
        """Test conversion of predefined date ranges."""
        predefined_ranges = ["today", "yesterday", "week", "month", "quarter"]
        
        for range_name in predefined_ranges:
            result = date_range_type.convert(range_name, None, None)
            
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], datetime)
            assert isinstance(result[1], datetime)
            assert result[0] < result[1]
    
    def test_custom_date_range(self, date_range_type):
        """Test conversion of custom date range."""
        date_range = "2024-01-01:2024-01-31"
        
        result = date_range_type.convert(date_range, None, None)
        
        assert isinstance(result, tuple)
        assert result[0] == datetime(2024, 1, 1)
        assert result[1] == datetime(2024, 1, 31)
    
    def test_invalid_date_range_order(self, date_range_type):
        """Test invalid date range with end before start."""
        date_range = "2024-01-31:2024-01-01"
        
        with pytest.raises(click.BadParameter):
            date_range_type.convert(date_range, None, None)
    
    def test_invalid_date_format(self, date_range_type):
        """Test invalid date format in range."""
        invalid_ranges = [
            "invalid-date:2024-01-31",
            "2024-01-01:invalid-date",
            "2024-13-01:2024-01-31",  # Invalid month
            "not-a-range"
        ]
        
        for invalid_range in invalid_ranges:
            with pytest.raises(click.BadParameter):
                date_range_type.convert(invalid_range, None, None)
    
    def test_empty_date_range(self, date_range_type):
        """Test empty date range."""
        with pytest.raises(click.BadParameter):
            date_range_type.convert("", None, None)
    
    def test_date_range_type_name(self, date_range_type):
        """Test DateRangeType name property."""
        assert date_range_type.name == "date_range"


class TestConfigFileType:
    """Test cases for ConfigFileType parameter type."""
    
    @pytest.fixture
    def config_file_type(self):
        """Create ConfigFileType instance."""
        return ConfigFileType()
    
    def test_valid_config_file_extensions(self, config_file_type, tmp_path):
        """Test valid configuration file extensions."""
        valid_extensions = [".json", ".ini", ".yaml", ".yml", ".toml"]
        
        for ext in valid_extensions:
            config_file = tmp_path / f"config{ext}"
            config_file.write_text("{}")
            
            result = config_file_type.convert(str(config_file), None, None)
            
            assert isinstance(result, Path)
            assert result == config_file
    
    def test_invalid_config_file_extension(self, config_file_type, tmp_path):
        """Test invalid configuration file extension."""
        config_file = tmp_path / "config.txt"
        config_file.write_text("{}")
        
        with pytest.raises(click.BadParameter):
            config_file_type.convert(str(config_file), None, None)
    
    def test_nonexistent_config_file(self, config_file_type):
        """Test non-existent configuration file."""
        # Should not raise error for non-existent file (exists=False in constructor)
        result = config_file_type.convert("/nonexistent/config.json", None, None)
        
        assert isinstance(result, Path)
        assert result == Path("/nonexistent/config.json")
    
    def test_config_file_not_readable(self, config_file_type, tmp_path):
        """Test configuration file that's not readable."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        
        # Mock os.access to return False for read permission
        with patch('os.access') as mock_access:
            mock_access.return_value = False
            
            with pytest.raises(click.BadParameter):
                config_file_type.convert(str(config_file), None, None)
    
    def test_config_file_is_directory(self, config_file_type, tmp_path):
        """Test configuration file path that's a directory."""
        config_dir = tmp_path / "config.json"
        config_dir.mkdir()
        
        with pytest.raises(click.BadParameter):
            config_file_type.convert(str(config_dir), None, None)


class TestOutputFormatType:
    """Test cases for OutputFormatType parameter type."""
    
    @pytest.fixture
    def output_format_type(self):
        """Create OutputFormatType instance."""
        return OutputFormatType()
    
    def test_valid_output_formats(self, output_format_type):
        """Test valid output formats."""
        valid_formats = ["table", "json", "csv", "html", "yaml"]
        
        for format_name in valid_formats:
            result = output_format_type.convert(format_name, None, None)
            assert result == format_name.lower()
    
    def test_case_insensitive_formats(self, output_format_type):
        """Test case insensitive format conversion."""
        test_cases = [
            ("TABLE", "table"),
            ("Json", "json"),
            ("CSV", "csv"),
            ("Html", "html"),
            ("YAML", "yaml")
        ]
        
        for input_format, expected in test_cases:
            result = output_format_type.convert(input_format, None, None)
            assert result == expected
    
    def test_invalid_output_format(self, output_format_type):
        """Test invalid output format."""
        with pytest.raises(click.BadParameter):
            output_format_type.convert("invalid_format", None, None)
    
    def test_format_extension_mismatch_warning(self, output_format_type, tmp_path):
        """Test warning for format/extension mismatch."""
        output_file = tmp_path / "output.html"
        
        # Create mock context with output parameter
        mock_ctx = Mock()
        mock_ctx.params = {'output': output_file}
        
        with patch('ticket_analyzer.cli.options.click.echo') as mock_echo:
            result = output_format_type.convert("json", None, mock_ctx)
            
            assert result == "json"
            mock_echo.assert_called_once()
            assert "Warning:" in mock_echo.call_args[0][0]


class TestEnvVarOption:
    """Test cases for EnvVarOption class."""
    
    def test_env_var_option_with_prefix(self):
        """Test EnvVarOption with automatic prefix."""
        option = EnvVarOption(["--test"], envvar="TEST_VAR")
        
        assert option.envvar == "TICKET_ANALYZER_TEST_VAR"
    
    def test_env_var_option_with_existing_prefix(self):
        """Test EnvVarOption with existing prefix."""
        option = EnvVarOption(["--test"], envvar="TICKET_ANALYZER_TEST_VAR")
        
        assert option.envvar == "TICKET_ANALYZER_TEST_VAR"
    
    def test_env_var_option_custom_prefix(self):
        """Test EnvVarOption with custom prefix."""
        option = EnvVarOption(["--test"], envvar="TEST_VAR", envvar_prefix="CUSTOM_")
        
        assert option.envvar == "CUSTOM_TEST_VAR"
    
    def test_env_var_option_help_record(self):
        """Test EnvVarOption help record includes environment variable."""
        option = EnvVarOption(["--test"], help="Test option", envvar="TEST_VAR")
        
        mock_ctx = Mock()
        help_record = option.get_help_record(mock_ctx)
        
        assert help_record is not None
        opts, help_text = help_record
        assert "[env var: TICKET_ANALYZER_TEST_VAR]" in help_text


class TestReusableOptions:
    """Test cases for reusable option functions."""
    
    def test_ticket_ids_option(self):
        """Test ticket_ids_option function."""
        @ticket_ids_option()
        def test_command(ticket_ids):
            return ticket_ids
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--ticket-ids', 'T123456', 'T789012'])
        
        assert result.exit_code == 0
    
    def test_date_range_option(self):
        """Test date_range_option function."""
        @date_range_option()
        def test_command(date_range):
            return date_range
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--date-range', 'week'])
        
        assert result.exit_code == 0
    
    def test_config_file_option(self, tmp_path):
        """Test config_file_option function."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{}')
        
        @config_file_option()
        def test_command(config_file):
            return config_file
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--config-file', str(config_file)])
        
        assert result.exit_code == 0
    
    def test_output_format_option(self):
        """Test output_format_option function."""
        @output_format_option()
        def test_command(format):
            return format
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--format', 'json'])
        
        assert result.exit_code == 0
    
    def test_output_file_option(self):
        """Test output_file_option function."""
        @output_file_option()
        def test_command(output):
            return output
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--output', 'test.json'])
        
        assert result.exit_code == 0
    
    def test_verbose_option(self):
        """Test verbose_option function."""
        @verbose_option()
        def test_command(verbose):
            return verbose
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--verbose'])
        
        assert result.exit_code == 0
    
    def test_max_results_option(self):
        """Test max_results_option function."""
        @max_results_option(default=500)
        def test_command(max_results):
            return max_results
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--max-results', '100'])
        
        assert result.exit_code == 0
    
    def test_timeout_option(self):
        """Test timeout_option function."""
        @timeout_option(default=30)
        def test_command(timeout):
            return timeout
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--timeout', '60'])
        
        assert result.exit_code == 0


class TestValidationFunctions:
    """Test cases for validation functions."""
    
    def test_validate_ticket_id_format_valid(self):
        """Test validate_ticket_id_format with valid IDs."""
        valid_ids = ["T123456", "ABC-123456", "P1234567890", "V1234567890"]
        
        for ticket_id in valid_ids:
            assert validate_ticket_id_format(ticket_id) is True
    
    def test_validate_ticket_id_format_invalid(self):
        """Test validate_ticket_id_format with invalid IDs."""
        invalid_ids = ["INVALID", "123456", "", "T12345"]
        
        for ticket_id in invalid_ids:
            assert validate_ticket_id_format(ticket_id) is False
    
    def test_validate_date_range_consistency_valid(self):
        """Test validate_date_range_consistency with valid parameters."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Should not raise exception
        validate_date_range_consistency(start_date, end_date, None, None)
        validate_date_range_consistency(None, None, 30, None)
        validate_date_range_consistency(None, None, None, "week")
    
    def test_validate_date_range_consistency_too_many_params(self):
        """Test validate_date_range_consistency with too many parameters."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        with pytest.raises(click.BadParameter):
            validate_date_range_consistency(start_date, end_date, 30, "week")
    
    def test_validate_date_range_consistency_invalid_order(self):
        """Test validate_date_range_consistency with invalid date order."""
        start_date = datetime(2024, 1, 31)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(click.BadParameter):
            validate_date_range_consistency(start_date, end_date, None, None)
    
    def test_validate_output_consistency_valid(self):
        """Test validate_output_consistency with valid parameters."""
        # Should not raise exception
        validate_output_consistency("html", None, True)
        validate_output_consistency("json", None, False)
        validate_output_consistency("table", None, False)
    
    def test_validate_output_consistency_invalid_charts(self):
        """Test validate_output_consistency with invalid chart option."""
        with pytest.raises(click.BadParameter):
            validate_output_consistency("json", None, True)
    
    def test_validate_output_consistency_extension_mismatch(self, tmp_path):
        """Test validate_output_consistency with extension mismatch."""
        output_file = tmp_path / "output.html"
        
        with patch('ticket_analyzer.cli.options.click.echo') as mock_echo:
            validate_output_consistency("json", output_file, False)
            
            mock_echo.assert_called_once()
            assert "Warning:" in mock_echo.call_args[0][0]


class TestHelpExamples:
    """Test cases for help examples functionality."""
    
    def test_add_help_examples_decorator(self):
        """Test add_help_examples decorator."""
        @add_help_examples("analyze")
        def test_command():
            """Original docstring."""
            pass
        
        assert "Original docstring." in test_command.__doc__
        assert "Examples:" in test_command.__doc__
        assert "ticket-analyzer analyze" in test_command.__doc__
    
    def test_add_help_examples_no_existing_docstring(self):
        """Test add_help_examples with no existing docstring."""
        @add_help_examples("config")
        def test_command():
            pass
        
        assert test_command.__doc__ is not None
        assert "Examples:" in test_command.__doc__
    
    def test_add_help_examples_unknown_command(self):
        """Test add_help_examples with unknown command."""
        @add_help_examples("unknown")
        def test_command():
            """Original docstring."""
            pass
        
        # Should not modify docstring for unknown commands
        assert test_command.__doc__ == "Original docstring."
    
    def test_help_examples_content(self):
        """Test help examples content."""
        assert "analyze" in HELP_EXAMPLES
        assert "config" in HELP_EXAMPLES
        assert "report" in HELP_EXAMPLES
        
        # Check that examples contain actual commands
        assert "ticket-analyzer analyze" in HELP_EXAMPLES["analyze"]
        assert "ticket-analyzer config" in HELP_EXAMPLES["config"]
        assert "ticket-analyzer report" in HELP_EXAMPLES["report"]


class TestOptionGroups:
    """Test cases for option groups."""
    
    def test_common_options_group(self):
        """Test COMMON_OPTIONS group."""
        from ticket_analyzer.cli.options import COMMON_OPTIONS
        
        assert len(COMMON_OPTIONS) > 0
        # Should contain verbose and config options
    
    def test_output_options_group(self):
        """Test OUTPUT_OPTIONS group."""
        from ticket_analyzer.cli.options import OUTPUT_OPTIONS
        
        assert len(OUTPUT_OPTIONS) > 0
        # Should contain format, output, and max_results options
    
    def test_time_period_options_group(self):
        """Test TIME_PERIOD_OPTIONS group."""
        from ticket_analyzer.cli.options import TIME_PERIOD_OPTIONS
        
        assert len(TIME_PERIOD_OPTIONS) > 0
        # Should contain date-related options
    
    def test_authentication_options_group(self):
        """Test AUTHENTICATION_OPTIONS group."""
        from ticket_analyzer.cli.options import AUTHENTICATION_OPTIONS
        
        assert len(AUTHENTICATION_OPTIONS) > 0
        # Should contain auth-related options


class TestEnvironmentVariableSupport:
    """Test cases for environment variable support."""
    
    def test_env_var_option_with_environment(self):
        """Test EnvVarOption reads from environment."""
        @click.command()
        @click.option('--test', cls=EnvVarOption, envvar='TEST_VAR')
        def test_command(test):
            click.echo(f"Value: {test}")
        
        runner = CliRunner()
        
        # Test with environment variable set
        result = runner.invoke(test_command, [], env={'TICKET_ANALYZER_TEST_VAR': 'env_value'})
        
        assert result.exit_code == 0
        assert "Value: env_value" in result.output
    
    def test_env_var_option_command_line_override(self):
        """Test command line overrides environment variable."""
        @click.command()
        @click.option('--test', cls=EnvVarOption, envvar='TEST_VAR')
        def test_command(test):
            click.echo(f"Value: {test}")
        
        runner = CliRunner()
        
        # Command line should override environment
        result = runner.invoke(
            test_command, 
            ['--test', 'cli_value'], 
            env={'TICKET_ANALYZER_TEST_VAR': 'env_value'}
        )
        
        assert result.exit_code == 0
        assert "Value: cli_value" in result.output


class TestParameterTypeIntegration:
    """Integration tests for parameter types."""
    
    def test_ticket_id_type_in_command(self):
        """Test TicketIDType integration in command."""
        @click.command()
        @click.option('--ticket-id', type=TicketIDType())
        def test_command(ticket_id):
            click.echo(f"Ticket: {ticket_id}")
        
        runner = CliRunner()
        
        # Valid ticket ID
        result = runner.invoke(test_command, ['--ticket-id', 't123456'])
        assert result.exit_code == 0
        assert "Ticket: T123456" in result.output
        
        # Invalid ticket ID
        result = runner.invoke(test_command, ['--ticket-id', 'invalid'])
        assert result.exit_code != 0
        assert "Invalid ticket ID format" in result.output
    
    def test_date_range_type_in_command(self):
        """Test DateRangeType integration in command."""
        @click.command()
        @click.option('--date-range', type=DateRangeType())
        def test_command(date_range):
            if date_range:
                start, end = date_range
                click.echo(f"Range: {start} to {end}")
        
        runner = CliRunner()
        
        # Valid predefined range
        result = runner.invoke(test_command, ['--date-range', 'week'])
        assert result.exit_code == 0
        assert "Range:" in result.output
        
        # Valid custom range
        result = runner.invoke(test_command, ['--date-range', '2024-01-01:2024-01-31'])
        assert result.exit_code == 0
        assert "Range:" in result.output
        
        # Invalid range
        result = runner.invoke(test_command, ['--date-range', 'invalid'])
        assert result.exit_code != 0
    
    def test_config_file_type_in_command(self, tmp_path):
        """Test ConfigFileType integration in command."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": true}')
        
        @click.command()
        @click.option('--config', type=ConfigFileType())
        def test_command(config):
            if config:
                click.echo(f"Config: {config}")
        
        runner = CliRunner()
        
        # Valid config file
        result = runner.invoke(test_command, ['--config', str(config_file)])
        assert result.exit_code == 0
        assert "Config:" in result.output
        
        # Invalid extension
        invalid_file = tmp_path / "config.txt"
        invalid_file.write_text("test")
        result = runner.invoke(test_command, ['--config', str(invalid_file)])
        assert result.exit_code != 0