"""Tests for CLI reporter module.

This module contains comprehensive tests for the CLIReporter class,
covering output formatting, color coding, table generation, and
user feedback according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from ticket_analyzer.reporting.cli_reporter import CLIReporter
from ticket_analyzer.models.analysis import AnalysisResult
from ticket_analyzer.models.config import ReportConfig
from ticket_analyzer.models.exceptions import ReportGenerationError


class TestCLIReporter:
    """Test cases for CLIReporter class."""
    
    def test_reporter_initialization_default(self):
        """Test CLI reporter initialization with default settings."""
        reporter = CLIReporter()
        
        assert reporter._config is not None
        assert reporter._formatter is not None
        assert reporter._progress_manager is not None
    
    def test_reporter_initialization_with_config(self):
        """Test CLI reporter initialization with custom config."""
        config = ReportConfig(
            color_enabled=False,
            table_style="simple",
            max_table_width=120
        )
        
        reporter = CLIReporter(config)
        
        assert reporter._config == config
    
    def test_generate_report_success(self, sample_analysis_result):
        """Test successful report generation."""
        reporter = CLIReporter()
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reporter.generate_report(sample_analysis_result)
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Check that output was written to stdout
        output = mock_stdout.getvalue()
        assert len(output) > 0
    
    def test_generate_report_with_empty_result(self):
        """Test report generation with empty analysis result."""
        reporter = CLIReporter()
        
        empty_result = AnalysisResult(
            metrics={},
            trends={},
            summary={},
            ticket_count=0,
            analysis_date=datetime.now()
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reporter.generate_report(empty_result)
        
        assert isinstance(result, str)
        assert "No data" in result or "Empty" in result
    
    def test_generate_report_invalid_input(self):
        """Test report generation with invalid input."""
        reporter = CLIReporter()
        
        with pytest.raises((ValueError, TypeError)):
            reporter.generate_report(None)
    
    def test_generate_summary_section(self, sample_analysis_result):
        """Test summary section generation."""
        reporter = CLIReporter()
        
        summary = reporter._generate_summary_section(sample_analysis_result)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Analysis Summary" in summary or "Summary" in summary
        assert str(sample_analysis_result.ticket_count) in summary
    
    def test_generate_metrics_section(self, sample_analysis_result):
        """Test metrics section generation."""
        reporter = CLIReporter()
        
        metrics = reporter._generate_metrics_section(sample_analysis_result)
        
        assert isinstance(metrics, str)
        assert len(metrics) > 0
        
        # Should contain metric names and values
        for metric_name, metric_value in sample_analysis_result.metrics.items():
            assert metric_name in metrics
            assert str(metric_value) in metrics
    
    def test_generate_trends_section(self, sample_analysis_result):
        """Test trends section generation."""
        reporter = CLIReporter()
        
        trends = reporter._generate_trends_section(sample_analysis_result)
        
        assert isinstance(trends, str)
        
        if sample_analysis_result.trends:
            assert len(trends) > 0
            assert "Trends" in trends or "Trend" in trends
        else:
            # Should handle empty trends gracefully
            assert "No trend data" in trends or len(trends) == 0
    
    def test_format_metric_value_numeric(self):
        """Test metric value formatting for numeric values."""
        reporter = CLIReporter()
        
        test_cases = [
            (42, "42"),
            (42.5, "42.5"),
            (42.123456, "42.12"),  # Should round to 2 decimal places
            (0, "0"),
            (-5.5, "-5.5")
        ]
        
        for input_value, expected in test_cases:
            result = reporter._format_metric_value(input_value)
            assert expected in result
    
    def test_format_metric_value_string(self):
        """Test metric value formatting for string values."""
        reporter = CLIReporter()
        
        test_cases = [
            ("test_string", "test_string"),
            ("", "N/A"),
            ("   ", "N/A"),
        ]
        
        for input_value, expected in test_cases:
            result = reporter._format_metric_value(input_value)
            assert expected in result
    
    def test_format_metric_value_complex_types(self):
        """Test metric value formatting for complex types."""
        reporter = CLIReporter()
        
        # Dictionary
        dict_value = {"key1": "value1", "key2": "value2"}
        dict_result = reporter._format_metric_value(dict_value)
        assert isinstance(dict_result, str)
        
        # List
        list_value = ["item1", "item2", "item3"]
        list_result = reporter._format_metric_value(list_value)
        assert isinstance(list_result, str)
        
        # None
        none_result = reporter._format_metric_value(None)
        assert "N/A" in none_result
    
    def test_create_table_basic(self):
        """Test basic table creation."""
        reporter = CLIReporter()
        
        headers = ["Metric", "Value", "Description"]
        rows = [
            ["Total Tickets", "100", "Total number of tickets"],
            ["Open Tickets", "25", "Currently open tickets"],
            ["Resolved Tickets", "75", "Successfully resolved tickets"]
        ]
        
        table = reporter._create_table(headers, rows)
        
        assert isinstance(table, str)
        assert len(table) > 0
        
        # Check that headers and data are present
        for header in headers:
            assert header in table
        
        for row in rows:
            for cell in row:
                assert cell in table
    
    def test_create_table_empty_data(self):
        """Test table creation with empty data."""
        reporter = CLIReporter()
        
        headers = ["Column1", "Column2"]
        rows = []
        
        table = reporter._create_table(headers, rows)
        
        assert isinstance(table, str)
        # Should still show headers
        for header in headers:
            assert header in table
    
    def test_create_table_mismatched_columns(self):
        """Test table creation with mismatched column counts."""
        reporter = CLIReporter()
        
        headers = ["Col1", "Col2", "Col3"]
        rows = [
            ["A", "B"],  # Missing column
            ["C", "D", "E", "F"]  # Extra column
        ]
        
        # Should handle gracefully
        table = reporter._create_table(headers, rows)
        assert isinstance(table, str)
    
    def test_apply_color_formatting_enabled(self):
        """Test color formatting when colors are enabled."""
        config = ReportConfig(color_enabled=True)
        reporter = CLIReporter(config)
        
        text = "Test message"
        color_type = "success"
        
        colored_text = reporter._apply_color_formatting(text, color_type)
        
        assert isinstance(colored_text, str)
        assert text in colored_text
        
        # Should contain color codes when enabled
        if hasattr(reporter, '_colorama_available') and reporter._colorama_available:
            assert len(colored_text) >= len(text)  # Color codes add length
    
    def test_apply_color_formatting_disabled(self):
        """Test color formatting when colors are disabled."""
        config = ReportConfig(color_enabled=False)
        reporter = CLIReporter(config)
        
        text = "Test message"
        color_type = "error"
        
        colored_text = reporter._apply_color_formatting(text, color_type)
        
        # Should return original text when colors disabled
        assert colored_text == text
    
    def test_apply_color_formatting_types(self):
        """Test different color formatting types."""
        config = ReportConfig(color_enabled=True)
        reporter = CLIReporter(config)
        
        text = "Test"
        color_types = ["success", "error", "warning", "info", "header"]
        
        for color_type in color_types:
            result = reporter._apply_color_formatting(text, color_type)
            assert isinstance(result, str)
            assert text in result
    
    def test_format_percentage_value(self):
        """Test percentage value formatting."""
        reporter = CLIReporter()
        
        test_cases = [
            (0.5, "50.0%"),
            (0.123, "12.3%"),
            (1.0, "100.0%"),
            (0.0, "0.0%"),
            (50.0, "50.0%"),  # Already in percentage form
        ]
        
        for input_value, expected in test_cases:
            result = reporter._format_percentage_value(input_value)
            assert expected in result
    
    def test_format_duration_value(self):
        """Test duration value formatting."""
        reporter = CLIReporter()
        
        # Test with timedelta
        duration = timedelta(hours=2, minutes=30)
        result = reporter._format_duration_value(duration)
        assert "2" in result and "30" in result
        
        # Test with numeric hours
        hours = 24.5
        result = reporter._format_duration_value(hours)
        assert "24" in result and "30" in result
    
    def test_generate_key_insights(self, sample_analysis_result):
        """Test key insights generation."""
        reporter = CLIReporter()
        
        insights = reporter._generate_key_insights(sample_analysis_result)
        
        assert isinstance(insights, str)
        
        if sample_analysis_result.summary.get("key_insights"):
            assert len(insights) > 0
            assert "Insights" in insights or "Key" in insights
    
    def test_format_output_for_terminal_width(self):
        """Test output formatting for terminal width."""
        reporter = CLIReporter()
        
        long_text = "This is a very long line of text that should be wrapped to fit within the terminal width constraints."
        
        formatted_text = reporter._format_output_for_terminal_width(long_text, width=50)
        
        assert isinstance(formatted_text, str)
        # Should not exceed specified width per line
        lines = formatted_text.split('\n')
        for line in lines:
            # Remove color codes for length check
            clean_line = reporter._strip_color_codes(line)
            assert len(clean_line) <= 50
    
    def test_strip_color_codes(self):
        """Test color code stripping."""
        reporter = CLIReporter()
        
        # Test with ANSI color codes
        colored_text = "\033[31mRed text\033[0m"
        stripped = reporter._strip_color_codes(colored_text)
        assert stripped == "Red text"
        
        # Test with no color codes
        plain_text = "Plain text"
        stripped = reporter._strip_color_codes(plain_text)
        assert stripped == plain_text
    
    def test_calculate_table_column_widths(self):
        """Test table column width calculation."""
        reporter = CLIReporter()
        
        headers = ["Short", "Medium Length", "Very Long Header Name"]
        rows = [
            ["A", "B", "C"],
            ["Longer", "Data", "Short"],
            ["X", "Very Long Data Entry", "Y"]
        ]
        
        widths = reporter._calculate_table_column_widths(headers, rows, max_width=100)
        
        assert isinstance(widths, list)
        assert len(widths) == len(headers)
        assert all(isinstance(w, int) and w > 0 for w in widths)
        assert sum(widths) <= 100  # Should respect max width


class TestCLIReporterColorHandling:
    """Test color handling functionality."""
    
    @patch('ticket_analyzer.reporting.cli_reporter.COLORAMA_AVAILABLE', True)
    def test_colorama_available_true(self):
        """Test behavior when colorama is available."""
        config = ReportConfig(color_enabled=True)
        reporter = CLIReporter(config)
        
        text = "Test message"
        colored = reporter._apply_color_formatting(text, "success")
        
        # Should apply colors when available and enabled
        assert isinstance(colored, str)
    
    @patch('ticket_analyzer.reporting.cli_reporter.COLORAMA_AVAILABLE', False)
    def test_colorama_available_false(self):
        """Test behavior when colorama is not available."""
        config = ReportConfig(color_enabled=True)
        reporter = CLIReporter(config)
        
        text = "Test message"
        colored = reporter._apply_color_formatting(text, "success")
        
        # Should return plain text when colorama not available
        assert colored == text
    
    def test_color_scheme_consistency(self):
        """Test that color schemes are consistent."""
        config = ReportConfig(color_enabled=True)
        reporter = CLIReporter(config)
        
        # Test that same color type produces consistent results
        text = "Test"
        result1 = reporter._apply_color_formatting(text, "error")
        result2 = reporter._apply_color_formatting(text, "error")
        
        assert result1 == result2


class TestCLIReporterErrorHandling:
    """Test error handling in CLI reporter."""
    
    def test_generate_report_with_corrupted_data(self):
        """Test report generation with corrupted analysis data."""
        reporter = CLIReporter()
        
        # Create analysis result with problematic data
        corrupted_result = AnalysisResult(
            metrics={"invalid": float('inf'), "none_value": None},
            trends={"bad_data": "not_a_dict"},
            summary={},
            ticket_count=-1,  # Invalid count
            analysis_date=datetime.now()
        )
        
        # Should handle gracefully without crashing
        result = reporter.generate_report(corrupted_result)
        assert isinstance(result, str)
    
    def test_table_creation_with_none_values(self):
        """Test table creation with None values in data."""
        reporter = CLIReporter()
        
        headers = ["Col1", "Col2", "Col3"]
        rows = [
            ["A", None, "C"],
            [None, "B", None],
            ["X", "Y", "Z"]
        ]
        
        table = reporter._create_table(headers, rows)
        
        assert isinstance(table, str)
        assert "N/A" in table  # Should replace None with N/A
    
    def test_format_metric_value_with_exceptions(self):
        """Test metric value formatting with values that might cause exceptions."""
        reporter = CLIReporter()
        
        problematic_values = [
            float('inf'),
            float('-inf'),
            float('nan'),
            complex(1, 2),
            object(),
        ]
        
        for value in problematic_values:
            # Should not raise exceptions
            result = reporter._format_metric_value(value)
            assert isinstance(result, str)
    
    @patch('ticket_analyzer.reporting.cli_reporter.logger')
    def test_error_logging_during_report_generation(self, mock_logger):
        """Test error logging during report generation."""
        reporter = CLIReporter()
        
        # Mock a method to raise an exception
        with patch.object(reporter, '_generate_summary_section', side_effect=Exception("Test error")):
            with pytest.raises(ReportGenerationError):
                reporter.generate_report(Mock())
        
        # Should log the error
        mock_logger.error.assert_called()


class TestCLIReporterIntegration:
    """Integration tests for CLI reporter."""
    
    def test_full_report_generation_workflow(self, sample_analysis_result):
        """Test complete report generation workflow."""
        config = ReportConfig(
            color_enabled=True,
            table_style="grid",
            max_table_width=120,
            show_summary=True,
            show_metrics=True,
            show_trends=True
        )
        
        reporter = CLIReporter(config)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reporter.generate_report(sample_analysis_result)
        
        # Verify complete report structure
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should contain all major sections
        assert "Summary" in result or "Analysis" in result
        assert any(metric in result for metric in sample_analysis_result.metrics.keys())
        
        # Should have written to stdout
        stdout_output = mock_stdout.getvalue()
        assert len(stdout_output) > 0
    
    def test_report_generation_with_different_configs(self, sample_analysis_result):
        """Test report generation with different configuration options."""
        configs = [
            ReportConfig(color_enabled=True, table_style="simple"),
            ReportConfig(color_enabled=False, table_style="grid"),
            ReportConfig(max_table_width=80, show_trends=False),
            ReportConfig(show_summary=False, show_metrics=True)
        ]
        
        for config in configs:
            reporter = CLIReporter(config)
            result = reporter.generate_report(sample_analysis_result)
            
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_report_output_consistency(self, sample_analysis_result):
        """Test that report output is consistent across multiple generations."""
        reporter = CLIReporter()
        
        result1 = reporter.generate_report(sample_analysis_result)
        result2 = reporter.generate_report(sample_analysis_result)
        
        # Results should be identical for same input
        assert result1 == result2
    
    def test_large_dataset_report_performance(self):
        """Test report generation performance with large dataset."""
        # Create analysis result with large amount of data
        large_metrics = {f"metric_{i}": i * 1.5 for i in range(100)}
        large_trends = {f"trend_{i}": {"data": list(range(50))} for i in range(20)}
        
        large_result = AnalysisResult(
            metrics=large_metrics,
            trends=large_trends,
            summary={"total_tickets": 10000, "key_insights": ["Insight 1", "Insight 2"]},
            ticket_count=10000,
            analysis_date=datetime.now()
        )
        
        reporter = CLIReporter()
        
        # Should complete without timeout
        result = reporter.generate_report(large_result)
        
        assert isinstance(result, str)
        assert len(result) > 0


class TestCLIReporterAccessibility:
    """Test accessibility features of CLI reporter."""
    
    def test_screen_reader_friendly_output(self, sample_analysis_result):
        """Test that output is screen reader friendly."""
        config = ReportConfig(
            color_enabled=False,  # No colors for screen readers
            table_style="simple"  # Simple table format
        )
        
        reporter = CLIReporter(config)
        result = reporter.generate_report(sample_analysis_result)
        
        # Should not contain color codes
        assert '\033[' not in result  # ANSI escape sequences
        
        # Should have clear section headers
        assert "Summary" in result or "Analysis" in result
    
    def test_high_contrast_color_scheme(self, sample_analysis_result):
        """Test high contrast color scheme for accessibility."""
        config = ReportConfig(
            color_enabled=True,
            color_scheme="high_contrast"
        )
        
        reporter = CLIReporter(config)
        
        # Should not raise exceptions with high contrast scheme
        result = reporter.generate_report(sample_analysis_result)
        assert isinstance(result, str)
    
    def test_text_only_mode(self, sample_analysis_result):
        """Test text-only mode without special formatting."""
        config = ReportConfig(
            color_enabled=False,
            table_style="plain",
            use_unicode=False
        )
        
        reporter = CLIReporter(config)
        result = reporter.generate_report(sample_analysis_result)
        
        # Should only contain basic ASCII characters
        assert all(ord(char) < 128 for char in result if char.isprintable())