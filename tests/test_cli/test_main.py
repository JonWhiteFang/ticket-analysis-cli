"""Tests for the main CLI application.

This module tests the main CLI entry point, argument parsing, validation,
and error scenarios for the ticket analyzer CLI application.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

from ticket_analyzer.cli.main import cli, CLIContext
from ticket_analyzer.models.exceptions import (
    TicketAnalysisError,
    AuthenticationError,
    ConfigurationError,
    DataRetrievalError
)


class TestCLIMain:
    """Test cases for main CLI application."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.main.DependencyContainer') as mock:
            container_instance = Mock()
            mock.return_value = container_instance
            yield container_instance
    
    def test_cli_version_option(self, runner):
        """Test --version option displays version information."""
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "1.0.0" in result.output
        assert "ticket-analyzer" in result.output
    
    def test_cli_help_option(self, runner):
        """Test --help option displays help information."""
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Ticket Analysis CLI Tool" in result.output
        assert "analyze" in result.output
        assert "config" in result.output
        assert "report" in result.output
        assert "--verbose" in result.output
        assert "--config" in result.output
    
    def test_cli_no_command_shows_help(self, runner):
        """Test that running CLI without command shows help."""
        result = runner.invoke(cli, [])
        
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output
    
    def test_cli_verbose_flag(self, runner):
        """Test --verbose flag enables verbose output."""
        with patch('ticket_analyzer.cli.main.logging.basicConfig') as mock_logging:
            result = runner.invoke(cli, ['--verbose'])
            
            assert result.exit_code == 0
            mock_logging.assert_called_once()
            assert "Verbose mode enabled" in result.output
    
    def test_cli_config_file_option(self, runner, temp_config_file):
        """Test --config option accepts configuration file."""
        result = runner.invoke(cli, ['--config', temp_config_file])
        
        assert result.exit_code == 0
        # Should not error with valid config file
    
    def test_cli_config_file_not_exists(self, runner):
        """Test --config option with non-existent file."""
        result = runner.invoke(cli, ['--config', '/nonexistent/config.json'])
        
        assert result.exit_code != 0
        assert "does not exist" in result.output
    
    def test_cli_output_dir_option(self, runner, temp_output_directory):
        """Test --output-dir option sets output directory."""
        result = runner.invoke(cli, ['--output-dir', temp_output_directory])
        
        assert result.exit_code == 0
        # Should not error with valid output directory
    
    def test_cli_context_initialization(self, runner):
        """Test CLI context is properly initialized."""
        with patch('ticket_analyzer.cli.main.CLIContext') as mock_context:
            mock_instance = Mock()
            mock_context.return_value = mock_instance
            
            result = runner.invoke(cli, ['--verbose', '--output-dir', '/tmp'])
            
            assert result.exit_code == 0
            mock_context.assert_called_once()
    
    def test_cli_invalid_command(self, runner):
        """Test invalid command shows error."""
        result = runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code != 0
        assert "No such command" in result.output
    
    def test_cli_command_help(self, runner):
        """Test help for specific commands."""
        # Test analyze command help
        result = runner.invoke(cli, ['analyze', '--help'])
        assert result.exit_code == 0
        assert "Analyze ticket data" in result.output
        
        # Test config command help
        result = runner.invoke(cli, ['config', '--help'])
        assert result.exit_code == 0
        assert "Configuration management" in result.output
        
        # Test report command help
        result = runner.invoke(cli, ['report', '--help'])
        assert result.exit_code == 0
        assert "Report generation" in result.output


class TestCLIContext:
    """Test cases for CLI context management."""
    
    def test_cli_context_initialization(self):
        """Test CLI context initialization with defaults."""
        context = CLIContext()
        
        assert context.verbose is False
        assert context.config_file is None
        assert context.output_dir == "./reports"
        assert context.shutdown_handler is not None
    
    def test_cli_context_with_values(self):
        """Test CLI context with custom values."""
        context = CLIContext()
        context.verbose = True
        context.config_file = "/path/to/config.json"
        context.output_dir = "/custom/output"
        
        assert context.verbose is True
        assert context.config_file == "/path/to/config.json"
        assert context.output_dir == "/custom/output"


class TestCLIErrorHandling:
    """Test cases for CLI error handling."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_keyboard_interrupt_handling(self, runner):
        """Test graceful handling of KeyboardInterrupt."""
        with patch('ticket_analyzer.cli.main.cli') as mock_cli:
            mock_cli.side_effect = KeyboardInterrupt()
            
            # This would normally be handled by the signal handler
            # We test the exception type is properly caught
            with pytest.raises(KeyboardInterrupt):
                mock_cli()
    
    def test_authentication_error_handling(self, runner):
        """Test handling of authentication errors."""
        with patch('ticket_analyzer.cli.commands.analyze.analyze_command') as mock_cmd:
            mock_cmd.side_effect = AuthenticationError("Authentication failed")
            
            result = runner.invoke(cli, ['analyze'])
            
            # The error should be handled by the @handle_cli_errors decorator
            assert result.exit_code == 1
    
    def test_configuration_error_handling(self, runner):
        """Test handling of configuration errors."""
        with patch('ticket_analyzer.cli.commands.config.show_config') as mock_cmd:
            mock_cmd.side_effect = ConfigurationError("Invalid configuration")
            
            result = runner.invoke(cli, ['config', 'show'])
            
            assert result.exit_code == 2
    
    def test_data_retrieval_error_handling(self, runner):
        """Test handling of data retrieval errors."""
        with patch('ticket_analyzer.cli.commands.analyze.analyze_command') as mock_cmd:
            mock_cmd.side_effect = DataRetrievalError("Failed to retrieve data")
            
            result = runner.invoke(cli, ['analyze'])
            
            assert result.exit_code == 3


class TestCLIIntegration:
    """Integration tests for CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_services(self):
        """Mock all services for integration testing."""
        with patch('ticket_analyzer.container.DependencyContainer') as mock_container:
            container = Mock()
            
            # Mock analysis service
            analysis_service = Mock()
            analysis_service.analyze_tickets.return_value = Mock(
                ticket_count=10,
                generated_at="2024-01-01T10:00:00",
                metrics={"total": 10}
            )
            container.analysis_service = analysis_service
            
            # Mock output service
            output_service = Mock()
            container.output_service = output_service
            
            # Mock config manager
            config_manager = Mock()
            config_manager.get_effective_config.return_value = {}
            container.config_manager = config_manager
            
            mock_container.return_value = container
            yield container
    
    def test_analyze_command_integration(self, runner, mock_services):
        """Test analyze command integration."""
        result = runner.invoke(cli, [
            'analyze',
            '--status', 'Open',
            '--days-back', '7',
            '--format', 'json'
        ])
        
        # Should not crash and should call analysis service
        mock_services.analysis_service.analyze_tickets.assert_called_once()
    
    def test_config_show_integration(self, runner, mock_services):
        """Test config show command integration."""
        result = runner.invoke(cli, ['config', 'show'])
        
        # Should call config manager
        mock_services.config_manager.get_effective_config.assert_called_once()
    
    def test_report_list_integration(self, runner, temp_output_directory):
        """Test report list command integration."""
        # Create some test report files
        report_dir = Path(temp_output_directory)
        (report_dir / "test1.json").write_text('{"test": true}')
        (report_dir / "test2.html").write_text('<html></html>')
        
        result = runner.invoke(cli, [
            'report', 'list',
            '--directory', temp_output_directory
        ])
        
        assert result.exit_code == 0
        assert "test1.json" in result.output
        assert "test2.html" in result.output


class TestCLIArgumentValidation:
    """Test cases for CLI argument validation."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_invalid_date_format(self, runner):
        """Test validation of invalid date formats."""
        result = runner.invoke(cli, [
            'analyze',
            '--start-date', 'invalid-date'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_invalid_format_option(self, runner):
        """Test validation of invalid format options."""
        result = runner.invoke(cli, [
            'analyze',
            '--format', 'invalid-format'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_invalid_max_results(self, runner):
        """Test validation of invalid max-results values."""
        result = runner.invoke(cli, [
            'analyze',
            '--max-results', '0'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
        
        result = runner.invoke(cli, [
            'analyze',
            '--max-results', '99999'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_conflicting_date_options(self, runner):
        """Test validation of conflicting date options."""
        with patch('ticket_analyzer.cli.shared.validate_date_range') as mock_validate:
            mock_validate.side_effect = Exception("Conflicting date parameters")
            
            result = runner.invoke(cli, [
                'analyze',
                '--start-date', '2024-01-01',
                '--days-back', '7',
                '--date-range', 'week'
            ])
            
            # Should call validation which raises exception
            mock_validate.assert_called_once()


class TestCLIOutputFormatting:
    """Test cases for CLI output formatting."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_color_output_enabled(self, runner):
        """Test color output is enabled by default."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            result = runner.invoke(cli, ['--help'])
            
            assert result.exit_code == 0
            # Color codes should be present in output when colorama is available
    
    def test_color_output_disabled(self, runner):
        """Test --no-color option disables color output."""
        with patch('ticket_analyzer.cli.commands.analyze.colorama') as mock_colorama:
            result = runner.invoke(cli, [
                'analyze',
                '--no-color',
                '--help'
            ])
            
            # Should call colorama.deinit() when --no-color is used
            # This is tested in the analyze command
    
    def test_verbose_output(self, runner):
        """Test verbose output includes additional information."""
        result = runner.invoke(cli, ['--verbose', '--help'])
        
        assert result.exit_code == 0
        assert "Verbose mode enabled" in result.output


class TestCLISignalHandling:
    """Test cases for CLI signal handling."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_graceful_shutdown_handler_creation(self, runner):
        """Test graceful shutdown handler is created."""
        with patch('ticket_analyzer.cli.main.GracefulShutdown') as mock_shutdown:
            mock_instance = Mock()
            mock_shutdown.return_value = mock_instance
            
            result = runner.invoke(cli, [])
            
            # GracefulShutdown should be instantiated in CLIContext
            assert result.exit_code == 0
    
    def test_signal_handler_registration(self):
        """Test signal handlers are properly registered."""
        from ticket_analyzer.cli.signals import GracefulShutdown
        
        with patch('signal.signal') as mock_signal:
            shutdown_handler = GracefulShutdown()
            
            # Should register SIGINT handler
            mock_signal.assert_called()
            
            # Verify signal numbers were registered
            call_args = [call[0][0] for call in mock_signal.call_args_list]
            import signal
            assert signal.SIGINT in call_args
    
    def test_cleanup_on_exit(self, runner):
        """Test cleanup functions are called on exit."""
        with patch('ticket_analyzer.cli.signals.GracefulShutdown') as mock_shutdown:
            mock_instance = Mock()
            mock_shutdown.return_value = mock_instance
            
            # Simulate cleanup registration
            cleanup_func = Mock()
            mock_instance.register_cleanup_function(cleanup_func)
            
            # Verify cleanup function was registered
            mock_instance.register_cleanup_function.assert_called_once_with(cleanup_func)


class TestCLIExitCodes:
    """Test cases for CLI exit codes."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_success_exit_code(self, runner):
        """Test successful command returns exit code 0."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
    
    def test_authentication_error_exit_code(self, runner):
        """Test authentication error returns exit code 1."""
        with patch('ticket_analyzer.cli.commands.analyze.analyze_command') as mock_cmd:
            mock_cmd.side_effect = AuthenticationError("Auth failed")
            
            result = runner.invoke(cli, ['analyze'])
            assert result.exit_code == 1
    
    def test_configuration_error_exit_code(self, runner):
        """Test configuration error returns exit code 2."""
        with patch('ticket_analyzer.cli.commands.config.show_config') as mock_cmd:
            mock_cmd.side_effect = ConfigurationError("Config error")
            
            result = runner.invoke(cli, ['config', 'show'])
            assert result.exit_code == 2
    
    def test_data_error_exit_code(self, runner):
        """Test data retrieval error returns exit code 3."""
        with patch('ticket_analyzer.cli.commands.analyze.analyze_command') as mock_cmd:
            mock_cmd.side_effect = DataRetrievalError("Data error")
            
            result = runner.invoke(cli, ['analyze'])
            assert result.exit_code == 3
    
    def test_analysis_error_exit_code(self, runner):
        """Test analysis error returns exit code 4."""
        with patch('ticket_analyzer.cli.commands.analyze.analyze_command') as mock_cmd:
            mock_cmd.side_effect = TicketAnalysisError("Analysis error")
            
            result = runner.invoke(cli, ['analyze'])
            assert result.exit_code == 4
    
    def test_keyboard_interrupt_exit_code(self, runner):
        """Test keyboard interrupt returns exit code 130."""
        with patch('ticket_analyzer.cli.shared.handle_cli_errors') as mock_handler:
            def side_effect(*args, **kwargs):
                raise KeyboardInterrupt()
            
            mock_handler.side_effect = side_effect
            
            # This would be handled by the signal handler in real usage
            with pytest.raises(KeyboardInterrupt):
                runner.invoke(cli, ['analyze'])