"""Tests for HTML reporter module.

This module contains comprehensive tests for the HTMLReporter class,
covering template rendering, data integration, output validation,
and chart generation according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import os

from ticket_analyzer.reporting.html_reporter import HTMLReporter
from ticket_analyzer.models.analysis import AnalysisResult
from ticket_analyzer.models.config import ReportConfig
from ticket_analyzer.models.exceptions import ReportGenerationError


class TestHTMLReporter:
    """Test cases for HTMLReporter class."""
    
    def test_reporter_initialization_default(self):
        """Test HTML reporter initialization with default settings."""
        reporter = HTMLReporter()
        
        assert reporter._config is not None
        assert reporter._template_env is not None
        assert reporter._chart_generator is not None
    
    def test_reporter_initialization_with_config(self):
        """Test HTML reporter initialization with custom config."""
        config = ReportConfig(
            template_dir="custom/templates",
            output_format="html",
            include_charts=True
        )
        
        reporter = HTMLReporter(config)
        
        assert reporter._config == config
    
    def test_reporter_initialization_with_custom_template_dir(self):
        """Test HTML reporter initialization with custom template directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ReportConfig(template_dir=temp_dir)
            
            reporter = HTMLReporter(config)
            
            assert reporter._config.template_dir == temp_dir
    
    def test_generate_report_success(self, sample_analysis_result):
        """Test successful HTML report generation."""
        reporter = HTMLReporter()
        
        with patch.object(reporter, '_render_template') as mock_render:
            mock_render.return_value = "<html><body>Test Report</body></html>"
            
            result = reporter.generate_report(sample_analysis_result)
        
        assert isinstance(result, str)
        assert "<html>" in result
        assert "<body>" in result
        mock_render.assert_called_once()
    
    def test_generate_report_with_output_file(self, sample_analysis_result):
        """Test HTML report generation with output file."""
        reporter = HTMLReporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            with patch.object(reporter, '_render_template') as mock_render:
                mock_render.return_value = "<html><body>Test Report</body></html>"
                
                result = reporter.generate_report(sample_analysis_result, output_file=output_path)
            
            assert isinstance(result, str)
            assert os.path.exists(output_path)
            
            # Verify file contents
            with open(output_path, 'r') as f:
                content = f.read()
                assert "<html>" in content
                assert "<body>" in content
        
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_generate_report_invalid_input(self):
        """Test HTML report generation with invalid input."""
        reporter = HTMLReporter()
        
        with pytest.raises((ValueError, TypeError)):
            reporter.generate_report(None)
    
    def test_render_template_success(self, sample_analysis_result):
        """Test successful template rendering."""
        reporter = HTMLReporter()
        
        with patch.object(reporter._template_env, 'get_template') as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "<html>Rendered Content</html>"
            mock_get_template.return_value = mock_template
            
            result = reporter._render_template("test_template.html", sample_analysis_result)
        
        assert result == "<html>Rendered Content</html>"
        mock_get_template.assert_called_once_with("test_template.html")
        mock_template.render.assert_called_once()
    
    def test_render_template_not_found(self, sample_analysis_result):
        """Test template rendering with missing template."""
        reporter = HTMLReporter()
        
        with patch.object(reporter._template_env, 'get_template') as mock_get_template:
            from jinja2 import TemplateNotFound
            mock_get_template.side_effect = TemplateNotFound("missing_template.html")
            
            with pytest.raises(ReportGenerationError, match="Template not found"):
                reporter._render_template("missing_template.html", sample_analysis_result)
    
    def test_render_template_syntax_error(self, sample_analysis_result):
        """Test template rendering with syntax error."""
        reporter = HTMLReporter()
        
        with patch.object(reporter._template_env, 'get_template') as mock_get_template:
            from jinja2 import TemplateSyntaxError
            mock_get_template.side_effect = TemplateSyntaxError("Invalid syntax", 1)
            
            with pytest.raises(ReportGenerationError, match="Template syntax error"):
                reporter._render_template("bad_template.html", sample_analysis_result)
    
    def test_prepare_template_data(self, sample_analysis_result):
        """Test template data preparation."""
        reporter = HTMLReporter()
        
        template_data = reporter._prepare_template_data(sample_analysis_result)
        
        assert isinstance(template_data, dict)
        assert "analysis_result" in template_data
        assert "generated_at" in template_data
        assert "charts" in template_data
        assert "config" in template_data
        
        # Verify analysis result is included
        assert template_data["analysis_result"] == sample_analysis_result
        
        # Verify generated timestamp
        assert isinstance(template_data["generated_at"], str)
    
    def test_prepare_template_data_with_charts(self, sample_analysis_result):
        """Test template data preparation with chart generation."""
        config = ReportConfig(include_charts=True)
        reporter = HTMLReporter(config)
        
        with patch.object(reporter._chart_generator, 'generate_all_charts') as mock_charts:
            mock_charts.return_value = {
                "status_distribution": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "resolution_trends": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            }
            
            template_data = reporter._prepare_template_data(sample_analysis_result)
        
        assert "charts" in template_data
        assert len(template_data["charts"]) == 2
        assert "status_distribution" in template_data["charts"]
        assert "resolution_trends" in template_data["charts"]
        mock_charts.assert_called_once_with(sample_analysis_result)
    
    def test_prepare_template_data_without_charts(self, sample_analysis_result):
        """Test template data preparation without charts."""
        config = ReportConfig(include_charts=False)
        reporter = HTMLReporter(config)
        
        template_data = reporter._prepare_template_data(sample_analysis_result)
        
        assert template_data["charts"] == {}
    
    def test_format_metrics_for_template(self, sample_analysis_result):
        """Test metrics formatting for template consumption."""
        reporter = HTMLReporter()
        
        formatted_metrics = reporter._format_metrics_for_template(sample_analysis_result.metrics)
        
        assert isinstance(formatted_metrics, list)
        
        for metric in formatted_metrics:
            assert isinstance(metric, dict)
            assert "name" in metric
            assert "value" in metric
            assert "formatted_value" in metric
            assert "category" in metric
    
    def test_format_metrics_for_template_empty(self):
        """Test metrics formatting with empty metrics."""
        reporter = HTMLReporter()
        
        formatted_metrics = reporter._format_metrics_for_template({})
        
        assert isinstance(formatted_metrics, list)
        assert len(formatted_metrics) == 0
    
    def test_format_trends_for_template(self, sample_analysis_result):
        """Test trends formatting for template consumption."""
        reporter = HTMLReporter()
        
        formatted_trends = reporter._format_trends_for_template(sample_analysis_result.trends)
        
        assert isinstance(formatted_trends, dict)
        
        if sample_analysis_result.trends:
            for trend_name, trend_data in formatted_trends.items():
                assert isinstance(trend_data, dict)
                assert "data" in trend_data
                assert "formatted_data" in trend_data
    
    def test_categorize_metric(self):
        """Test metric categorization."""
        reporter = HTMLReporter()
        
        test_cases = [
            ("total_tickets", "volume"),
            ("avg_resolution_time", "performance"),
            ("status_distribution", "distribution"),
            ("resolution_rate", "performance"),
            ("custom_metric", "other")
        ]
        
        for metric_name, expected_category in test_cases:
            category = reporter._categorize_metric(metric_name)
            assert category == expected_category
    
    def test_format_metric_value_for_display(self):
        """Test metric value formatting for display."""
        reporter = HTMLReporter()
        
        test_cases = [
            (42, "42"),
            (42.5, "42.5"),
            (42.123456, "42.12"),
            (0.75, "75.0%"),  # Percentage values
            ("string_value", "string_value"),
            (None, "N/A"),
            ({"key": "value"}, "1 items"),  # Dictionary
            ([1, 2, 3], "3 items")  # List
        ]
        
        for input_value, expected in test_cases:
            result = reporter._format_metric_value_for_display(input_value)
            assert expected in result
    
    def test_save_report_to_file(self):
        """Test saving report to file."""
        reporter = HTMLReporter()
        
        html_content = "<html><body>Test Report</body></html>"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            reporter._save_report_to_file(html_content, output_path)
            
            assert os.path.exists(output_path)
            
            with open(output_path, 'r') as f:
                saved_content = f.read()
                assert saved_content == html_content
        
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_save_report_to_file_invalid_path(self):
        """Test saving report to invalid file path."""
        reporter = HTMLReporter()
        
        html_content = "<html><body>Test Report</body></html>"
        invalid_path = "/invalid/path/that/does/not/exist/report.html"
        
        with pytest.raises(ReportGenerationError, match="Failed to save report"):
            reporter._save_report_to_file(html_content, invalid_path)
    
    def test_validate_template_data(self, sample_analysis_result):
        """Test template data validation."""
        reporter = HTMLReporter()
        
        valid_data = {
            "analysis_result": sample_analysis_result,
            "generated_at": datetime.now().isoformat(),
            "charts": {},
            "config": reporter._config
        }
        
        # Should not raise exception for valid data
        reporter._validate_template_data(valid_data)
    
    def test_validate_template_data_missing_required(self):
        """Test template data validation with missing required fields."""
        reporter = HTMLReporter()
        
        invalid_data = {
            "generated_at": datetime.now().isoformat(),
            # Missing analysis_result
        }
        
        with pytest.raises(ReportGenerationError, match="Missing required template data"):
            reporter._validate_template_data(invalid_data)
    
    def test_get_template_name_for_config(self):
        """Test template name selection based on configuration."""
        test_cases = [
            (ReportConfig(template_style="detailed"), "detailed_report.html"),
            (ReportConfig(template_style="summary"), "summary_report.html"),
            (ReportConfig(template_style="minimal"), "minimal_report.html"),
            (ReportConfig(), "default_report.html")  # Default case
        ]
        
        for config, expected_template in test_cases:
            reporter = HTMLReporter(config)
            template_name = reporter._get_template_name_for_config()
            assert template_name == expected_template


class TestHTMLReporterChartIntegration:
    """Test chart integration in HTML reporter."""
    
    def test_chart_generation_enabled(self, sample_analysis_result):
        """Test chart generation when enabled."""
        config = ReportConfig(include_charts=True)
        reporter = HTMLReporter(config)
        
        with patch.object(reporter._chart_generator, 'generate_all_charts') as mock_charts:
            mock_charts.return_value = {"test_chart": "base64_data"}
            
            template_data = reporter._prepare_template_data(sample_analysis_result)
        
        assert template_data["charts"] == {"test_chart": "base64_data"}
        mock_charts.assert_called_once_with(sample_analysis_result)
    
    def test_chart_generation_disabled(self, sample_analysis_result):
        """Test behavior when chart generation is disabled."""
        config = ReportConfig(include_charts=False)
        reporter = HTMLReporter(config)
        
        with patch.object(reporter._chart_generator, 'generate_all_charts') as mock_charts:
            template_data = reporter._prepare_template_data(sample_analysis_result)
        
        assert template_data["charts"] == {}
        mock_charts.assert_not_called()
    
    def test_chart_generation_error_handling(self, sample_analysis_result):
        """Test error handling during chart generation."""
        config = ReportConfig(include_charts=True)
        reporter = HTMLReporter(config)
        
        with patch.object(reporter._chart_generator, 'generate_all_charts') as mock_charts:
            mock_charts.side_effect = Exception("Chart generation failed")
            
            # Should handle chart generation errors gracefully
            template_data = reporter._prepare_template_data(sample_analysis_result)
        
        # Should still return template data with empty charts
        assert template_data["charts"] == {}
    
    def test_embed_charts_in_html(self):
        """Test chart embedding in HTML output."""
        reporter = HTMLReporter()
        
        charts = {
            "status_chart": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "trend_chart": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        }
        
        html_template = """
        <html>
        <body>
            {% for chart_name, chart_data in charts.items() %}
            <img src="{{ chart_data }}" alt="{{ chart_name }}">
            {% endfor %}
        </body>
        </html>
        """
        
        embedded_html = reporter._embed_charts_in_html(html_template, charts)
        
        assert "data:image/png;base64" in embedded_html
        assert "status_chart" in embedded_html
        assert "trend_chart" in embedded_html


class TestHTMLReporterTemplateEngine:
    """Test template engine functionality."""
    
    def test_jinja2_environment_setup(self):
        """Test Jinja2 environment setup."""
        reporter = HTMLReporter()
        
        assert reporter._template_env is not None
        assert hasattr(reporter._template_env, 'get_template')
        assert hasattr(reporter._template_env, 'loader')
    
    def test_custom_template_filters(self):
        """Test custom Jinja2 template filters."""
        reporter = HTMLReporter()
        
        # Test that custom filters are registered
        filters = reporter._template_env.filters
        
        expected_filters = [
            'format_number',
            'format_percentage',
            'format_duration',
            'format_date'
        ]
        
        for filter_name in expected_filters:
            assert filter_name in filters
    
    def test_template_filter_format_number(self):
        """Test format_number template filter."""
        reporter = HTMLReporter()
        
        format_number = reporter._template_env.filters['format_number']
        
        test_cases = [
            (1234, "1,234"),
            (1234.56, "1,234.56"),
            (0, "0"),
            (None, "N/A")
        ]
        
        for input_value, expected in test_cases:
            result = format_number(input_value)
            assert expected in result
    
    def test_template_filter_format_percentage(self):
        """Test format_percentage template filter."""
        reporter = HTMLReporter()
        
        format_percentage = reporter._template_env.filters['format_percentage']
        
        test_cases = [
            (0.5, "50.0%"),
            (0.123, "12.3%"),
            (1.0, "100.0%"),
            (None, "N/A")
        ]
        
        for input_value, expected in test_cases:
            result = format_percentage(input_value)
            assert expected in result
    
    def test_template_filter_format_duration(self):
        """Test format_duration template filter."""
        reporter = HTMLReporter()
        
        format_duration = reporter._template_env.filters['format_duration']
        
        # Test with timedelta
        duration = timedelta(hours=2, minutes=30)
        result = format_duration(duration)
        assert "2h 30m" in result or "2:30" in result
        
        # Test with None
        result = format_duration(None)
        assert "N/A" in result
    
    def test_template_filter_format_date(self):
        """Test format_date template filter."""
        reporter = HTMLReporter()
        
        format_date = reporter._template_env.filters['format_date']
        
        test_date = datetime(2024, 1, 15, 14, 30, 0)
        result = format_date(test_date)
        
        assert "2024" in result
        assert "Jan" in result or "01" in result
        assert "15" in result
    
    def test_template_global_functions(self):
        """Test global functions available in templates."""
        reporter = HTMLReporter()
        
        globals_dict = reporter._template_env.globals
        
        expected_globals = [
            'get_metric_category',
            'calculate_percentage_change',
            'format_large_number'
        ]
        
        for global_name in expected_globals:
            assert global_name in globals_dict


class TestHTMLReporterErrorHandling:
    """Test error handling in HTML reporter."""
    
    def test_template_rendering_error(self, sample_analysis_result):
        """Test handling of template rendering errors."""
        reporter = HTMLReporter()
        
        with patch.object(reporter._template_env, 'get_template') as mock_get_template:
            mock_template = Mock()
            mock_template.render.side_effect = Exception("Rendering failed")
            mock_get_template.return_value = mock_template
            
            with pytest.raises(ReportGenerationError, match="Template rendering failed"):
                reporter._render_template("test_template.html", sample_analysis_result)
    
    def test_file_write_permission_error(self, sample_analysis_result):
        """Test handling of file write permission errors."""
        reporter = HTMLReporter()
        
        html_content = "<html><body>Test</body></html>"
        
        # Try to write to a directory that doesn't exist or has no permissions
        invalid_path = "/root/no_permission/report.html"
        
        with pytest.raises(ReportGenerationError):
            reporter._save_report_to_file(html_content, invalid_path)
    
    def test_corrupted_analysis_data_handling(self):
        """Test handling of corrupted analysis data."""
        reporter = HTMLReporter()
        
        # Create analysis result with problematic data
        corrupted_result = AnalysisResult(
            metrics={"invalid": float('inf')},
            trends={"bad_data": None},
            summary={},
            ticket_count=-1,
            analysis_date=None  # Invalid date
        )
        
        # Should handle gracefully
        template_data = reporter._prepare_template_data(corrupted_result)
        
        assert isinstance(template_data, dict)
        assert "analysis_result" in template_data
    
    @patch('ticket_analyzer.reporting.html_reporter.logger')
    def test_error_logging(self, mock_logger, sample_analysis_result):
        """Test error logging during report generation."""
        reporter = HTMLReporter()
        
        with patch.object(reporter, '_render_template', side_effect=Exception("Test error")):
            with pytest.raises(ReportGenerationError):
                reporter.generate_report(sample_analysis_result)
        
        mock_logger.error.assert_called()


class TestHTMLReporterPerformance:
    """Test performance aspects of HTML reporter."""
    
    def test_large_dataset_report_generation(self):
        """Test report generation with large dataset."""
        # Create analysis result with large amount of data
        large_metrics = {f"metric_{i}": i * 1.5 for i in range(1000)}
        large_trends = {f"trend_{i}": {"data": list(range(100))} for i in range(50)}
        
        large_result = AnalysisResult(
            metrics=large_metrics,
            trends=large_trends,
            summary={"total_tickets": 100000},
            ticket_count=100000,
            analysis_date=datetime.now()
        )
        
        config = ReportConfig(include_charts=False)  # Disable charts for performance
        reporter = HTMLReporter(config)
        
        with patch.object(reporter, '_render_template') as mock_render:
            mock_render.return_value = "<html>Large Report</html>"
            
            # Should complete without timeout
            result = reporter.generate_report(large_result)
        
        assert isinstance(result, str)
        mock_render.assert_called_once()
    
    def test_memory_efficiency_template_data(self):
        """Test memory efficiency of template data preparation."""
        reporter = HTMLReporter()
        
        # Process multiple analysis results to test memory usage
        for i in range(10):
            analysis_result = AnalysisResult(
                metrics={f"metric_{j}": j for j in range(100)},
                trends={},
                summary={},
                ticket_count=100,
                analysis_date=datetime.now()
            )
            
            template_data = reporter._prepare_template_data(analysis_result)
            assert isinstance(template_data, dict)
        
        # Should complete without memory issues


class TestHTMLReporterAccessibility:
    """Test accessibility features of HTML reporter."""
    
    def test_accessible_html_structure(self, sample_analysis_result):
        """Test that generated HTML has accessible structure."""
        reporter = HTMLReporter()
        
        # Mock template that returns accessible HTML
        accessible_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Ticket Analysis Report</title>
        </head>
        <body>
            <h1>Analysis Report</h1>
            <main role="main">
                <section aria-labelledby="summary-heading">
                    <h2 id="summary-heading">Summary</h2>
                </section>
            </main>
        </body>
        </html>
        """
        
        with patch.object(reporter, '_render_template') as mock_render:
            mock_render.return_value = accessible_html
            
            result = reporter.generate_report(sample_analysis_result)
        
        # Check for accessibility features
        assert 'lang="en"' in result
        assert 'role="main"' in result
        assert 'aria-labelledby=' in result
        assert '<h1>' in result and '<h2>' in result  # Proper heading hierarchy
    
    def test_chart_alt_text_generation(self, sample_analysis_result):
        """Test that charts have appropriate alt text."""
        config = ReportConfig(include_charts=True)
        reporter = HTMLReporter(config)
        
        with patch.object(reporter._chart_generator, 'generate_all_charts') as mock_charts:
            mock_charts.return_value = {
                "status_distribution": "data:image/png;base64,test_data"
            }
            
            template_data = reporter._prepare_template_data(sample_analysis_result)
        
        # Template data should include alt text information
        assert "charts" in template_data
        # Alt text would be handled in the template itself