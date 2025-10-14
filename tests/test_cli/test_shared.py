"""Tests for shared CLI utilities and decorators.

This module tests the shared utilities, option groups, and decorators
that are used across multiple CLI commands.
"""

import pytest
import sys
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path
import click
from click.testing import CliRunner

from ticket_analyzer.cli.shared import (
    time_period_options, output_options, configuration_options, authentication_options,
    add_option_groups, validate_date_range, handle_cli_errors
)
from ticket_analyzer.models.exceptions import (
    TicketAnalysisError, AuthenticationError, ConfigurationError, DataRetrievalError
)


class TestOptionGroups:
    """Test cases for CLI option groups."""
    
    def test_time_period_options_group(self):
        """Test time period options group."""
        assert isinstance(time_period_options, list)
        assert len(time_period_options) > 0
        
        # Should contain Click options
        for option in time_period_options:
            assert hasattr(option, '__call__')  # Should be decorators
    
    def test_output_options_group(self):
        """Test output options group."""
        assert isinstance(output_options, list)
        assert len(output_options) > 0
        
        # Should contain Click options
        for option in output_options:
            assert hasattr(option, '__call__')  # Should be decorators
    
    def test_configuration_options_group(self):
        """Test configuration options group."""
        assert isinstance(configuration_options, list)
        assert len(configuration_options) > 0
        
        # Should contain Click options
        for option in configuration_options:
            assert hasattr(option, '__call__')  # Should be decorators
    
    def test_authentication_options_group(self):
        """Test authentication options group."""
        assert isinstance(authentication_options, list)
        assert len(authentication_options) > 0
        
        # Should contain Click options
        for option in authentication_options:
            assert hasattr(option, '__call__')  # Should be decorators


class TestAddOptionGroups:
    """Test cases for add_option_groups decorator."""
    
    def test_add_single_option_group(self):
        """Test adding single option group to command."""
        # Create a simple option group
        test_options = [
            click.option('--test1', help='Test option 1'),
            click.option('--test2', help='Test option 2')
        ]
        
        @add_option_groups(test_options)
        @click.command()
        def test_command(test1, test2):
            return f"{test1}-{test2}"
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--test1', 'value1', '--test2', 'value2'])
        
        assert result.exit_code == 0
    
    def test_add_multiple_option_groups(self):
        """Test adding multiple option groups to command."""
        group1 = [click.option('--opt1', help='Option 1')]
        group2 = [click.option('--opt2', help='Option 2')]
        group3 = [click.option('--opt3', help='Option 3')]
        
        @add_option_groups(group1, group2, group3)
        @click.command()
        def test_command(opt1, opt2, opt3):
            return f"{opt1}-{opt2}-{opt3}"
        
        runner = CliRunner()
        result = runner.invoke(test_command, [
            '--opt1', 'val1',
            '--opt2', 'val2', 
            '--opt3', 'val3'
        ])
        
        assert result.exit_code == 0
    
    def test_add_option_groups_with_real_groups(self):
        """Test adding real option groups from the module."""
        @add_option_groups(time_period_options, output_options)
        @click.command()
        def test_command(**kwargs):
            return "success"
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--help'])
        
        assert result.exit_code == 0
        # Should contain options from both groups
        assert '--start-date' in result.output
        assert '--format' in result.output
    
    def test_add_option_groups_empty(self):
        """Test adding empty option groups."""
        @add_option_groups()
        @click.command()
        def test_command():
            return "success"
        
        runner = CliRunner()
        result = runner.invoke(test_command, [])
        
        assert result.exit_code == 0
    
    def test_add_option_groups_order(self):
        """Test that option groups are added in correct order."""
        # Options should be applied in reverse order to maintain correct precedence
        group1 = [click.option('--first', help='First option')]
        group2 = [click.option('--second', help='Second option')]
        
        @add_option_groups(group1, group2)
        @click.command()
        def test_command(first, second):
            click.echo(f"first={first}, second={second}")
        
        runner = CliRunner()
        result = runner.invoke(test_command, ['--first', 'A', '--second', 'B'])
        
        assert result.exit_code == 0
        assert "first=A, second=B" in result.output


class TestValidateDateRange:
    """Test cases for date range validation."""
    
    def test_validate_date_range_valid_combinations(self):
        """Test valid date range parameter combinations."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Valid combinations (should not raise exceptions)
        validate_date_range(start_date, end_date, None, None)
        validate_date_range(None, None, 30, None)
        validate_date_range(None, None, None, "week")
        validate_date_range(start_date, None, None, None)
        validate_date_range(None, end_date, None, None)
        validate_date_range(None, None, None, None)
    
    def test_validate_date_range_too_many_parameters(self):
        """Test validation with too many date parameters."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        with pytest.raises(click.BadParameter):
            validate_date_range(start_date, end_date, 30, "week")
        
        with pytest.raises(click.BadParameter):
            validate_date_range(start_date, end_date, 30, None)
        
        with pytest.raises(click.BadParameter):
            validate_date_range(start_date, None, 30, "week")
    
    def test_validate_date_range_invalid_order(self):
        """Test validation with start date after end date."""
        start_date = datetime(2024, 1, 31)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(click.BadParameter):
            validate_date_range(start_date, end_date, None, None)
    
    def test_validate_date_range_same_dates(self):
        """Test validation with same start and end dates."""
        same_date = datetime(2024, 1, 15)
        
        with pytest.raises(click.BadParameter):
            validate_date_range(same_date, same_date, None, None)
    
    def test_validate_date_range_none_values(self):
        """Test validation handles None values correctly."""
        # Should not count None values as provided parameters
        validate_date_range(None, None, None, None)
        validate_date_range(datetime(2024, 1, 1), None, None, None)


class TestHandleCLIErrors:
    """Test cases for CLI error handling decorator."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_handle_cli_errors_success(self, runner):
        """Test error handler with successful function."""
        @handle_cli_errors
        @click.command()
        def test_command():
            click.echo("Success")
        
        result = runner.invoke(test_command, [])
        
        assert result.exit_code == 0
        assert "Success" in result.output
    
    def test_handle_cli_errors_authentication_error(self, runner):
        """Test error handler with authentication error."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise AuthenticationError("Auth failed")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 1
            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "Authentication failed" in call_args
    
    def test_handle_cli_errors_configuration_error(self, runner):
        """Test error handler with configuration error."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise ConfigurationError("Config error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 2
            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "Configuration error" in call_args
    
    def test_handle_cli_errors_data_retrieval_error(self, runner):
        """Test error handler with data retrieval error."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise DataRetrievalError("Data error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 3
            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "Data retrieval failed" in call_args
    
    def test_handle_cli_errors_ticket_analysis_error(self, runner):
        """Test error handler with ticket analysis error."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise TicketAnalysisError("Analysis error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 4
            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "Analysis error" in call_args
    
    def test_handle_cli_errors_keyboard_interrupt(self, runner):
        """Test error handler with keyboard interrupt."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise KeyboardInterrupt()
        
        with patch('ticket_analyzer.cli.shared.warning_message') as mock_warning:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 130
            mock_warning.assert_called()
            call_args = mock_warning.call_args[0][0]
            assert "Operation cancelled" in call_args
    
    def test_handle_cli_errors_unexpected_error(self, runner):
        """Test error handler with unexpected error."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise ValueError("Unexpected error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 5
            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "Unexpected error" in call_args
    
    def test_handle_cli_errors_verbose_mode(self, runner):
        """Test error handler in verbose mode."""
        @handle_cli_errors
        @click.command()
        @click.pass_context
        def test_command(ctx):
            ctx.obj = Mock()
            ctx.obj.verbose = True
            raise AuthenticationError("Auth failed")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj.verbose = True
                
                result = runner.invoke(test_command, [])
                
                assert result.exit_code == 1
                # Should show additional verbose information
                assert mock_error.call_count >= 2
    
    def test_handle_cli_errors_no_context(self, runner):
        """Test error handler without click context."""
        @handle_cli_errors
        @click.command()
        def test_command():
            raise AuthenticationError("Auth failed")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value = None
                
                result = runner.invoke(test_command, [])
                
                assert result.exit_code == 1
                mock_error.assert_called()
    
    def test_handle_cli_errors_verbose_with_traceback(self, runner):
        """Test error handler shows traceback in verbose mode."""
        @handle_cli_errors
        @click.command()
        @click.pass_context
        def test_command(ctx):
            ctx.obj = Mock()
            ctx.obj.verbose = True
            raise ValueError("Test error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj.verbose = True
                
                with patch('traceback.format_exc') as mock_traceback:
                    mock_traceback.return_value = "Traceback info"
                    
                    result = runner.invoke(test_command, [])
                    
                    assert result.exit_code == 5
                    # Should include traceback in verbose mode
                    mock_traceback.assert_called_once()


class TestOptionGroupsIntegration:
    """Integration tests for option groups."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_time_period_options_integration(self, runner):
        """Test time period options integration."""
        @add_option_groups(time_period_options)
        @click.command()
        def test_command(**kwargs):
            for key, value in kwargs.items():
                if value is not None:
                    click.echo(f"{key}: {value}")
        
        result = runner.invoke(test_command, [
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-31',
            '--days-back', '30'
        ])
        
        assert result.exit_code == 0
        assert "start_date:" in result.output
        assert "end_date:" in result.output
        assert "days_back:" in result.output
    
    def test_output_options_integration(self, runner):
        """Test output options integration."""
        @add_option_groups(output_options)
        @click.command()
        def test_command(**kwargs):
            for key, value in kwargs.items():
                if value is not None:
                    click.echo(f"{key}: {value}")
        
        result = runner.invoke(test_command, [
            '--format', 'json',
            '--max-results', '100',
            '--no-color'
        ])
        
        assert result.exit_code == 0
        assert "format: json" in result.output
        assert "max_results: 100" in result.output
        assert "no_color: True" in result.output
    
    def test_configuration_options_integration(self, runner, tmp_path):
        """Test configuration options integration."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{}')
        
        @add_option_groups(configuration_options)
        @click.command()
        def test_command(**kwargs):
            for key, value in kwargs.items():
                if value is not None:
                    click.echo(f"{key}: {value}")
        
        result = runner.invoke(test_command, [
            '--config-file', str(config_file),
            '--timeout', '120',
            '--batch-size', '50'
        ])
        
        assert result.exit_code == 0
        assert "config_file:" in result.output
        assert "timeout: 120" in result.output
        assert "batch_size: 50" in result.output
    
    def test_authentication_options_integration(self, runner):
        """Test authentication options integration."""
        @add_option_groups(authentication_options)
        @click.command()
        def test_command(**kwargs):
            for key, value in kwargs.items():
                if value is not None:
                    click.echo(f"{key}: {value}")
        
        result = runner.invoke(test_command, [
            '--auth-timeout', '90',
            '--force-auth',
            '--skip-auth-check'
        ])
        
        assert result.exit_code == 0
        assert "auth_timeout: 90" in result.output
        assert "force_auth: True" in result.output
        assert "skip_auth_check: True" in result.output
    
    def test_combined_option_groups_integration(self, runner, tmp_path):
        """Test combining multiple option groups."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{}')
        
        @add_option_groups(
            time_period_options,
            output_options,
            configuration_options,
            authentication_options
        )
        @click.command()
        def test_command(**kwargs):
            non_none_args = {k: v for k, v in kwargs.items() if v is not None}
            click.echo(f"Received {len(non_none_args)} arguments")
        
        result = runner.invoke(test_command, [
            '--start-date', '2024-01-01',
            '--format', 'json',
            '--config-file', str(config_file),
            '--force-auth'
        ])
        
        assert result.exit_code == 0
        assert "Received 4 arguments" in result.output


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_error_handling_with_option_groups(self, runner):
        """Test error handling combined with option groups."""
        @handle_cli_errors
        @add_option_groups(time_period_options)
        @click.command()
        def test_command(**kwargs):
            if kwargs.get('start_date') and kwargs.get('end_date'):
                validate_date_range(
                    kwargs['start_date'], 
                    kwargs['end_date'], 
                    kwargs.get('days_back'), 
                    kwargs.get('date_range')
                )
            raise AuthenticationError("Test auth error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [
                '--start-date', '2024-01-01',
                '--end-date', '2024-01-31'
            ])
            
            assert result.exit_code == 1
            mock_error.assert_called()
    
    def test_validation_error_in_decorated_command(self, runner):
        """Test validation error in decorated command."""
        @handle_cli_errors
        @add_option_groups(time_period_options)
        @click.command()
        def test_command(**kwargs):
            # This should raise a validation error
            validate_date_range(
                datetime(2024, 1, 31),  # Start after end
                datetime(2024, 1, 1),
                None,
                None
            )
        
        result = runner.invoke(test_command, [])
        
        # Should be handled by the error decorator
        assert result.exit_code != 0
    
    def test_nested_error_handling(self, runner):
        """Test nested error handling scenarios."""
        @handle_cli_errors
        @click.command()
        def outer_command():
            @handle_cli_errors
            @click.command()
            def inner_command():
                raise ConfigurationError("Inner error")
            
            # This would normally be called differently, but for testing
            try:
                inner_command.callback()
            except SystemExit as e:
                # Re-raise as different error type
                raise DataRetrievalError("Outer error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(outer_command, [])
            
            assert result.exit_code == 3  # DataRetrievalError exit code
            mock_error.assert_called()


class TestSharedUtilitiesEdgeCases:
    """Test edge cases for shared utilities."""
    
    def test_add_option_groups_with_none(self):
        """Test add_option_groups with None values."""
        @add_option_groups(None)
        @click.command()
        def test_command():
            return "success"
        
        # Should handle None gracefully
        runner = CliRunner()
        result = runner.invoke(test_command, [])
        assert result.exit_code == 0
    
    def test_validate_date_range_edge_cases(self):
        """Test date range validation edge cases."""
        # Very close dates (1 second apart)
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 1)
        
        # Should be valid (end is after start)
        validate_date_range(start, end, None, None)
        
        # Test with microsecond precision
        start_micro = datetime(2024, 1, 1, 12, 0, 0, 0)
        end_micro = datetime(2024, 1, 1, 12, 0, 0, 1)
        
        validate_date_range(start_micro, end_micro, None, None)
    
    def test_handle_cli_errors_with_custom_context(self, runner):
        """Test error handler with custom context object."""
        class CustomContext:
            def __init__(self):
                self.verbose = True
                self.custom_attr = "test"
        
        @handle_cli_errors
        @click.command()
        @click.pass_context
        def test_command(ctx):
            ctx.obj = CustomContext()
            raise AuthenticationError("Custom context error")
        
        with patch('ticket_analyzer.cli.shared.error_message') as mock_error:
            result = runner.invoke(test_command, [])
            
            assert result.exit_code == 1
            mock_error.assert_called()
    
    def test_option_groups_parameter_precedence(self, runner):
        """Test parameter precedence in option groups."""
        # Test that later options don't override earlier ones
        group1 = [click.option('--shared', default='group1', help='From group 1')]
        group2 = [click.option('--shared', default='group2', help='From group 2')]
        
        @add_option_groups(group1, group2)
        @click.command()
        def test_command(shared):
            click.echo(f"shared: {shared}")
        
        result = runner.invoke(test_command, [])
        
        # The last applied option should take precedence
        assert result.exit_code == 0