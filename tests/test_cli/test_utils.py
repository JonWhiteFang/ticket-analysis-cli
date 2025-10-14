"""Tests for CLI utility functions.

This module tests the CLI utility functions including color-coded output,
input validation, user confirmation prompts, and error handling.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from ticket_analyzer.cli.utils import (
    success_message, error_message, info_message, warning_message, debug_message,
    highlight_text, validate_ticket_id_format, validate_email_format,
    validate_date_format, sanitize_filename, confirm_action, prompt_for_input,
    select_from_options, format_table_output, list_files_with_details,
    format_config_display, format_exception_message, format_validation_errors,
    show_spinner, SpinnerContext, get_terminal_width, truncate_text, wrap_text,
    format_duration, create_progress_callback
)


class TestColoredOutput:
    """Test cases for colored output functions."""
    
    def test_success_message_with_colorama(self):
        """Test success message with colorama available."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                success_message("Test success")
                
                mock_echo.assert_called_once()
                call_args = mock_echo.call_args[0][0]
                assert "✓ Test success" in call_args
    
    def test_success_message_without_colorama(self):
        """Test success message without colorama."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', False):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                with patch('ticket_analyzer.cli.utils.click.style') as mock_style:
                    mock_style.return_value = "styled text"
                    
                    success_message("Test success")
                    
                    mock_style.assert_called_once_with("✓ Test success", fg='green', bold=False)
                    mock_echo.assert_called_once_with("styled text")
    
    def test_error_message_with_colorama(self):
        """Test error message with colorama available."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                error_message("Test error")
                
                mock_echo.assert_called_once()
                call_args = mock_echo.call_args[0][0]
                assert "✗ Test error" in call_args
                # Should use err=True
                assert mock_echo.call_args[1]['err'] is True
    
    def test_info_message_with_colorama(self):
        """Test info message with colorama available."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                info_message("Test info")
                
                mock_echo.assert_called_once()
                call_args = mock_echo.call_args[0][0]
                assert "ℹ Test info" in call_args
    
    def test_warning_message_with_colorama(self):
        """Test warning message with colorama available."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                warning_message("Test warning")
                
                mock_echo.assert_called_once()
                call_args = mock_echo.call_args[0][0]
                assert "⚠ Test warning" in call_args
                # Should use err=True
                assert mock_echo.call_args[1]['err'] is True
    
    def test_debug_message_with_colorama(self):
        """Test debug message with colorama available."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                debug_message("Test debug")
                
                mock_echo.assert_called_once()
                call_args = mock_echo.call_args[0][0]
                assert "🔍 Test debug" in call_args
                # Should use err=True
                assert mock_echo.call_args[1]['err'] is True
    
    def test_highlight_text_with_colorama(self):
        """Test text highlighting with colorama available."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', True):
            result = highlight_text("test text", "red", bold=True)
            
            # Should contain color codes
            assert result != "test text"
            assert "test text" in result
    
    def test_highlight_text_without_colorama(self):
        """Test text highlighting without colorama."""
        with patch('ticket_analyzer.cli.utils.COLORAMA_AVAILABLE', False):
            with patch('ticket_analyzer.cli.utils.click.style') as mock_style:
                mock_style.return_value = "styled text"
                
                result = highlight_text("test text", "blue", bold=False)
                
                mock_style.assert_called_once_with("test text", fg="blue", bold=False)
                assert result == "styled text"


class TestInputValidation:
    """Test cases for input validation functions."""
    
    def test_validate_ticket_id_format_valid(self):
        """Test validation of valid ticket ID formats."""
        valid_ids = [
            "ABC-123456",
            "DEFGH-789012",
            "T123456",
            "T1234567890",
            "P123456",
            "P1234567890",
            "V1234567890"
        ]
        
        for ticket_id in valid_ids:
            assert validate_ticket_id_format(ticket_id) is True
    
    def test_validate_ticket_id_format_invalid(self):
        """Test validation of invalid ticket ID formats."""
        invalid_ids = [
            "INVALID",
            "123456",
            "ABC-",
            "T12345",  # Too short
            "P12345678901",  # Too long for P format
            "X123456",  # Invalid prefix
            ""
        ]
        
        for ticket_id in invalid_ids:
            assert validate_ticket_id_format(ticket_id) is False
    
    def test_validate_email_format_valid(self):
        """Test validation of valid email formats."""
        valid_emails = [
            "user@example.com",
            "test.user@domain.org",
            "user+tag@example.co.uk",
            "123@example.com"
        ]
        
        for email in valid_emails:
            assert validate_email_format(email) is True
    
    def test_validate_email_format_invalid(self):
        """Test validation of invalid email formats."""
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user@.com",
            "user..name@example.com",
            ""
        ]
        
        for email in invalid_emails:
            assert validate_email_format(email) is False
    
    def test_validate_date_format_valid(self):
        """Test validation of valid date formats."""
        valid_dates = [
            ("2024-01-01", "%Y-%m-%d"),
            ("01/01/2024", "%m/%d/%Y"),
            ("2024-01-01 10:30:00", "%Y-%m-%d %H:%M:%S")
        ]
        
        for date_str, format_str in valid_dates:
            assert validate_date_format(date_str, format_str) is True
    
    def test_validate_date_format_invalid(self):
        """Test validation of invalid date formats."""
        invalid_dates = [
            ("2024-13-01", "%Y-%m-%d"),  # Invalid month
            ("2024-01-32", "%Y-%m-%d"),  # Invalid day
            ("invalid-date", "%Y-%m-%d"),
            ("", "%Y-%m-%d")
        ]
        
        for date_str, format_str in invalid_dates:
            assert validate_date_format(date_str, format_str) is False
    
    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file with spaces.txt"),
            ("file<>:\"/\\|?*.txt", "file_________.txt"),
            ("  .hidden_file.txt  ", "hidden_file.txt"),
            ("", "unnamed_file")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
    
    def test_sanitize_filename_long_name(self):
        """Test sanitization of very long filenames."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        
        assert len(result) <= 255
        assert result.endswith(".txt")


class TestUserInteraction:
    """Test cases for user interaction functions."""
    
    def test_confirm_action_yes(self):
        """Test confirm action with yes response."""
        with patch('ticket_analyzer.cli.utils.click.confirm') as mock_confirm:
            mock_confirm.return_value = True
            
            result = confirm_action("Continue?")
            
            assert result is True
            mock_confirm.assert_called_once()
    
    def test_confirm_action_no(self):
        """Test confirm action with no response."""
        with patch('ticket_analyzer.cli.utils.click.confirm') as mock_confirm:
            mock_confirm.return_value = False
            
            result = confirm_action("Continue?")
            
            assert result is False
    
    def test_confirm_action_abort(self):
        """Test confirm action with abort on no."""
        with patch('ticket_analyzer.cli.utils.click.confirm') as mock_confirm:
            mock_confirm.side_effect = Exception("Aborted")  # Click raises Abort
            
            with pytest.raises(Exception):
                confirm_action("Continue?", abort_on_no=True)
    
    def test_prompt_for_input_valid(self):
        """Test prompt for input with valid response."""
        with patch('ticket_analyzer.cli.utils.click.prompt') as mock_prompt:
            mock_prompt.return_value = "valid_input"
            
            result = prompt_for_input("Enter value:")
            
            assert result == "valid_input"
            mock_prompt.assert_called_once()
    
    def test_prompt_for_input_with_validation(self):
        """Test prompt for input with validation function."""
        def validate_func(value):
            return value.startswith("valid_")
        
        with patch('ticket_analyzer.cli.utils.click.prompt') as mock_prompt:
            mock_prompt.side_effect = ["invalid", "valid_input"]
            
            with patch('ticket_analyzer.cli.utils.error_message'):
                result = prompt_for_input("Enter value:", validation_func=validate_func)
                
                assert result == "valid_input"
                assert mock_prompt.call_count == 2
    
    def test_prompt_for_input_max_attempts(self):
        """Test prompt for input exceeding max attempts."""
        def validate_func(value):
            return False  # Always invalid
        
        with patch('ticket_analyzer.cli.utils.click.prompt') as mock_prompt:
            mock_prompt.return_value = "invalid"
            
            with patch('ticket_analyzer.cli.utils.error_message'):
                with pytest.raises(SystemExit):
                    prompt_for_input("Enter value:", validation_func=validate_func, max_attempts=2)
    
    def test_select_from_options_valid(self):
        """Test select from options with valid choice."""
        options = ["Option 1", "Option 2", "Option 3"]
        
        with patch('ticket_analyzer.cli.utils.click.prompt') as mock_prompt:
            mock_prompt.return_value = 2
            
            with patch('ticket_analyzer.cli.utils.click.echo'):
                result = select_from_options("Choose:", options)
                
                assert result == "Option 2"
    
    def test_select_from_options_invalid_then_valid(self):
        """Test select from options with invalid then valid choice."""
        options = ["Option 1", "Option 2"]
        
        with patch('ticket_analyzer.cli.utils.click.prompt') as mock_prompt:
            mock_prompt.side_effect = [5, 1]  # Invalid then valid
            
            with patch('ticket_analyzer.cli.utils.click.echo'):
                with patch('ticket_analyzer.cli.utils.error_message'):
                    result = select_from_options("Choose:", options)
                    
                    assert result == "Option 1"
                    assert mock_prompt.call_count == 2
    
    def test_select_from_options_empty_list(self):
        """Test select from options with empty list."""
        with patch('ticket_analyzer.cli.utils.error_message'):
            result = select_from_options("Choose:", [])
            
            assert result == ""


class TestTableFormatting:
    """Test cases for table formatting functions."""
    
    def test_format_table_output_with_tabulate(self):
        """Test table formatting with tabulate available."""
        data = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25}
        ]
        
        with patch('ticket_analyzer.cli.utils.tabulate') as mock_tabulate:
            mock_tabulate.return_value = "formatted_table"
            
            result = format_table_output(data)
            
            assert result == "formatted_table"
            mock_tabulate.assert_called_once()
    
    def test_format_table_output_without_tabulate(self):
        """Test table formatting without tabulate."""
        data = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25}
        ]
        
        with patch('ticket_analyzer.cli.utils.tabulate', side_effect=ImportError):
            result = format_table_output(data)
            
            # Should use fallback formatting
            assert "John" in result
            assert "Jane" in result
            assert "name" in result
            assert "age" in result
    
    def test_format_table_output_empty_data(self):
        """Test table formatting with empty data."""
        result = format_table_output([])
        assert result == "No data to display"
        
        result = format_table_output(None)
        assert result == "No data to display"
    
    def test_format_table_output_dict_data(self):
        """Test table formatting with dictionary data."""
        data = {"key1": "value1", "key2": "value2"}
        
        with patch('ticket_analyzer.cli.utils.tabulate', side_effect=ImportError):
            result = format_table_output(data)
            
            assert "key1" in result
            assert "value1" in result
            assert "key2" in result
            assert "value2" in result
    
    def test_list_files_with_details(self, tmp_path):
        """Test listing files with details."""
        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.json"
        file1.write_text("content1")
        file2.write_text("content2")
        
        files = [file1, file2]
        
        with patch('ticket_analyzer.cli.utils.format_table_output') as mock_format:
            mock_format.return_value = "formatted_files"
            
            result = list_files_with_details(files)
            
            assert result == "formatted_files"
            mock_format.assert_called_once()
            
            # Check that file details were passed
            call_args = mock_format.call_args[0][0]
            assert len(call_args) == 2
            assert call_args[0][0] == "file1.txt"
            assert call_args[1][0] == "file2.json"
    
    def test_list_files_with_details_empty(self):
        """Test listing files with empty list."""
        result = list_files_with_details([])
        assert result == "No files found"


class TestConfigFormatting:
    """Test cases for configuration formatting functions."""
    
    def test_format_config_display_basic(self):
        """Test basic configuration display formatting."""
        config_data = {
            "auth": {"timeout": 60},
            "report": {"format": "json"},
            "debug": True
        }
        
        result = format_config_display(config_data)
        
        assert "auth.timeout: 60" in result
        assert "report.format: json" in result
        assert "debug: True" in result
    
    def test_format_config_display_with_sources(self):
        """Test configuration display with source information."""
        config_data = {
            "setting1": {
                "value": "test",
                "_source": "file"
            },
            "setting2": "direct_value"
        }
        
        result = format_config_display(config_data, show_sources=True)
        
        assert "setting1" in result
        assert "setting2: direct_value" in result
    
    def test_format_config_display_nested(self):
        """Test configuration display with nested data."""
        config_data = {
            "level1": {
                "level2": {
                    "setting": "value"
                }
            }
        }
        
        result = format_config_display(config_data)
        
        assert "level1.level2.setting: value" in result


class TestErrorFormatting:
    """Test cases for error formatting functions."""
    
    def test_format_exception_message_basic(self):
        """Test basic exception message formatting."""
        exception = ValueError("Test error")
        
        result = format_exception_message(exception)
        
        assert result == "Test error"
    
    def test_format_exception_message_with_traceback(self):
        """Test exception message formatting with traceback."""
        exception = ValueError("Test error")
        
        with patch('traceback.format_exc') as mock_traceback:
            mock_traceback.return_value = "Traceback info"
            
            result = format_exception_message(exception, include_traceback=True)
            
            assert "Test error" in result
            assert "Traceback:" in result
            assert "Traceback info" in result
    
    def test_format_validation_errors_empty(self):
        """Test formatting empty validation errors."""
        result = format_validation_errors([])
        assert result == "No validation errors"
    
    def test_format_validation_errors_with_errors(self):
        """Test formatting validation errors with errors."""
        errors = ["Error 1", "Error 2", "Error 3"]
        
        result = format_validation_errors(errors)
        
        assert "Validation errors:" in result
        assert "1. Error 1" in result
        assert "2. Error 2" in result
        assert "3. Error 3" in result


class TestSpinnerContext:
    """Test cases for spinner context manager."""
    
    def test_spinner_context_basic(self):
        """Test basic spinner context usage."""
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            spinner = SpinnerContext("Testing...")
            
            with spinner:
                pass
            
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
    
    def test_show_spinner_function(self):
        """Test show_spinner function."""
        with patch('ticket_analyzer.cli.utils.SpinnerContext') as mock_spinner:
            mock_instance = Mock()
            mock_spinner.return_value = mock_instance
            
            result = show_spinner("Processing...")
            
            assert result == mock_instance
            mock_spinner.assert_called_once_with("Processing...")


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_get_terminal_width_success(self):
        """Test getting terminal width successfully."""
        with patch('ticket_analyzer.cli.utils.click.get_terminal_size') as mock_size:
            mock_size.return_value = (120, 40)
            
            result = get_terminal_width()
            
            assert result == 120
    
    def test_get_terminal_width_fallback(self):
        """Test getting terminal width with fallback."""
        with patch('ticket_analyzer.cli.utils.click.get_terminal_size') as mock_size:
            mock_size.side_effect = Exception("No terminal")
            
            result = get_terminal_width()
            
            assert result == 80  # Default fallback
    
    def test_truncate_text_short(self):
        """Test truncating text that's already short."""
        text = "Short text"
        result = truncate_text(text, 20)
        
        assert result == "Short text"
    
    def test_truncate_text_long(self):
        """Test truncating long text."""
        text = "This is a very long text that needs to be truncated"
        result = truncate_text(text, 20)
        
        assert len(result) == 20
        assert result.endswith("...")
        assert "This is a very" in result
    
    def test_wrap_text_basic(self):
        """Test basic text wrapping."""
        text = "This is a long line that should be wrapped to multiple lines"
        
        with patch('textwrap.fill') as mock_fill:
            mock_fill.return_value = "wrapped text"
            
            result = wrap_text(text, width=40)
            
            assert result == "wrapped text"
            mock_fill.assert_called_once_with(text, width=40)
    
    def test_wrap_text_default_width(self):
        """Test text wrapping with default width."""
        text = "Test text"
        
        with patch('ticket_analyzer.cli.utils.get_terminal_width') as mock_width:
            mock_width.return_value = 80
            
            with patch('textwrap.fill') as mock_fill:
                mock_fill.return_value = "wrapped"
                
                result = wrap_text(text)
                
                mock_fill.assert_called_once_with(text, width=76)  # 80 - 4 margin
    
    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        result = format_duration(45.5)
        assert result == "45.5s"
    
    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        result = format_duration(150.0)  # 2.5 minutes
        assert result == "2.5m"
    
    def test_format_duration_hours(self):
        """Test formatting duration in hours."""
        result = format_duration(7200.0)  # 2 hours
        assert result == "2.0h"
    
    def test_create_progress_callback_with_tqdm(self):
        """Test creating progress callback with tqdm available."""
        with patch('ticket_analyzer.cli.utils.tqdm') as mock_tqdm:
            mock_pbar = Mock()
            mock_tqdm.return_value = mock_pbar
            
            callback = create_progress_callback("Testing")
            
            # Test callback usage
            callback(5, 10)
            
            mock_tqdm.assert_called_once_with(desc="Testing", unit="items")
            mock_pbar.update.assert_called_once_with(1)
    
    def test_create_progress_callback_without_tqdm(self):
        """Test creating progress callback without tqdm."""
        with patch('ticket_analyzer.cli.utils.tqdm', side_effect=ImportError):
            with patch('ticket_analyzer.cli.utils.click.echo') as mock_echo:
                callback = create_progress_callback("Testing")
                
                # Test callback usage
                callback(5, 10)
                
                mock_echo.assert_called_once()
                call_args = mock_echo.call_args[0][0]
                assert "Testing: 5/10 (50.0%)" in call_args


class TestFileOperations:
    """Test cases for file operation utilities."""
    
    def test_format_file_size_bytes(self):
        """Test formatting file size in bytes."""
        from ticket_analyzer.cli.utils import _format_file_size
        
        assert _format_file_size(0) == "0 B"
        assert _format_file_size(512) == "512.0 B"
    
    def test_format_file_size_kb(self):
        """Test formatting file size in KB."""
        from ticket_analyzer.cli.utils import _format_file_size
        
        result = _format_file_size(1536)  # 1.5 KB
        assert "1.5 KB" in result
    
    def test_format_file_size_mb(self):
        """Test formatting file size in MB."""
        from ticket_analyzer.cli.utils import _format_file_size
        
        result = _format_file_size(1572864)  # 1.5 MB
        assert "1.5 MB" in result
    
    def test_format_file_size_gb(self):
        """Test formatting file size in GB."""
        from ticket_analyzer.cli.utils import _format_file_size
        
        result = _format_file_size(1610612736)  # 1.5 GB
        assert "1.5 GB" in result