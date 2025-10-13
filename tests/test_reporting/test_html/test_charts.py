"""Tests for chart generation module.

This module contains comprehensive tests for the ChartGenerator class,
covering chart creation, base64 embedding, visualization accuracy,
and matplotlib integration according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
import base64
import io

from ticket_analyzer.reporting.charts import ChartGenerator
from ticket_analyzer.models.analysis import AnalysisResult
from ticket_analyzer.models.config import ReportConfig
from ticket_analyzer.models.exceptions import ReportGenerationError


class TestChartGenerator:
    """Test cases for ChartGenerator class."""
    
    def test_generator_initialization_default(self):
        """Test chart generator initialization with default settings."""
        generator = ChartGenerator()
        
        assert generator._config is not None
        assert generator._figure_size == (10, 6)
        assert generator._dpi == 100
    
    def test_generator_initialization_with_config(self):
        """Test chart generator initialization with custom config."""
        config = ReportConfig(
            chart_width=12,
            chart_height=8,
            chart_dpi=150,
            chart_style="seaborn"
        )
        
        generator = ChartGenerator(config)
        
        assert generator._config == config
        assert generator._figure_size == (12, 8)
        assert generator._dpi == 150
    
    @patch('matplotlib.pyplot.style.use')
    def test_generator_initialization_with_style(self, mock_style):
        """Test chart generator initialization with custom style."""
        config = ReportConfig(chart_style="ggplot")
        
        generator = ChartGenerator(config)
        
        mock_style.assert_called_with("ggplot")
    
    def test_generate_all_charts_success(self, sample_analysis_result):
        """Test successful generation of all charts."""
        generator = ChartGenerator()
        
        with patch.object(generator, '_generate_status_distribution_chart') as mock_status, \
             patch.object(generator, '_generate_resolution_time_chart') as mock_resolution, \
             patch.object(generator, '_generate_volume_trends_chart') as mock_volume, \
             patch.object(generator, '_generate_severity_distribution_chart') as mock_severity:
            
            mock_status.return_value = "base64_status_chart"
            mock_resolution.return_value = "base64_resolution_chart"
            mock_volume.return_value = "base64_volume_chart"
            mock_severity.return_value = "base64_severity_chart"
            
            charts = generator.generate_all_charts(sample_analysis_result)
        
        assert isinstance(charts, dict)
        assert "status_distribution" in charts
        assert "resolution_time" in charts
        assert "volume_trends" in charts
        assert "severity_distribution" in charts
        
        assert charts["status_distribution"] == "base64_status_chart"
        assert charts["resolution_time"] == "base64_resolution_chart"
        assert charts["volume_trends"] == "base64_volume_chart"
        assert charts["severity_distribution"] == "base64_severity_chart"
    
    def test_generate_all_charts_empty_data(self):
        """Test chart generation with empty analysis data."""
        generator = ChartGenerator()
        
        empty_result = AnalysisResult(
            metrics={},
            trends={},
            summary={},
            ticket_count=0,
            analysis_date=datetime.now()
        )
        
        charts = generator.generate_all_charts(empty_result)
        
        # Should return empty dict or charts with "no data" messages
        assert isinstance(charts, dict)
    
    def test_generate_all_charts_partial_data(self):
        """Test chart generation with partial data."""
        generator = ChartGenerator()
        
        partial_result = AnalysisResult(
            metrics={"total_tickets": 100},  # Only basic metrics
            trends={},
            summary={},
            ticket_count=100,
            analysis_date=datetime.now()
        )
        
        with patch.object(generator, '_generate_status_distribution_chart') as mock_status:
            mock_status.return_value = "base64_chart"
            
            charts = generator.generate_all_charts(partial_result)
        
        assert isinstance(charts, dict)
    
    def test_generate_status_distribution_chart(self):
        """Test status distribution chart generation."""
        generator = ChartGenerator()
        
        metrics = {
            "status_counts": {"OPEN": 25, "RESOLVED": 75, "IN_PROGRESS": 10},
            "status_percentages": {"OPEN": 22.7, "RESOLVED": 68.2, "IN_PROGRESS": 9.1}
        }
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.pie') as mock_pie, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_pie_chart"
            
            result = generator._generate_status_distribution_chart(metrics)
        
        assert result == "base64_pie_chart"
        mock_figure.assert_called_once()
        mock_pie.assert_called_once()
        mock_convert.assert_called_once()
    
    def test_generate_status_distribution_chart_no_data(self):
        """Test status distribution chart with no data."""
        generator = ChartGenerator()
        
        empty_metrics = {"status_counts": {}}
        
        result = generator._generate_status_distribution_chart(empty_metrics)
        
        # Should return None or empty string for no data
        assert result is None or result == ""
    
    def test_generate_resolution_time_chart(self):
        """Test resolution time chart generation."""
        generator = ChartGenerator()
        
        metrics = {
            "resolution_time_by_severity": {"HIGH": 2.5, "MEDIUM": 8.0, "LOW": 24.0},
            "avg_resolution_time_hours": 11.5
        }
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.bar') as mock_bar, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_bar_chart"
            
            result = generator._generate_resolution_time_chart(metrics)
        
        assert result == "base64_bar_chart"
        mock_figure.assert_called_once()
        mock_bar.assert_called_once()
        mock_convert.assert_called_once()
    
    def test_generate_volume_trends_chart(self):
        """Test volume trends chart generation."""
        generator = ChartGenerator()
        
        trends = {
            "daily_trends": {
                "2024-01-01": 10,
                "2024-01-02": 15,
                "2024-01-03": 12,
                "2024-01-04": 18,
                "2024-01-05": 14
            }
        }
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.plot') as mock_plot, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_line_chart"
            
            result = generator._generate_volume_trends_chart(trends)
        
        assert result == "base64_line_chart"
        mock_figure.assert_called_once()
        mock_plot.assert_called_once()
        mock_convert.assert_called_once()
    
    def test_generate_severity_distribution_chart(self):
        """Test severity distribution chart generation."""
        generator = ChartGenerator()
        
        metrics = {
            "severity_counts": {"HIGH": 15, "MEDIUM": 60, "LOW": 25},
            "severity_percentages": {"HIGH": 15.0, "MEDIUM": 60.0, "LOW": 25.0}
        }
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.bar') as mock_bar, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_severity_chart"
            
            result = generator._generate_severity_distribution_chart(metrics)
        
        assert result == "base64_severity_chart"
        mock_figure.assert_called_once()
        mock_bar.assert_called_once()
        mock_convert.assert_called_once()
    
    def test_convert_figure_to_base64(self):
        """Test figure to base64 conversion."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.gcf') as mock_gcf, \
             patch('io.BytesIO') as mock_bytesio, \
             patch('base64.b64encode') as mock_b64encode:
            
            # Mock figure and buffer
            mock_figure = Mock()
            mock_gcf.return_value = mock_figure
            
            mock_buffer = Mock()
            mock_bytesio.return_value = mock_buffer
            mock_buffer.getvalue.return_value = b'fake_image_data'
            
            mock_b64encode.return_value = b'ZmFrZV9pbWFnZV9kYXRh'  # base64 of 'fake_image_data'
            
            result = generator._convert_figure_to_base64()
        
        expected = "data:image/png;base64,ZmFrZV9pbWFnZV9kYXRh"
        assert result == expected
        
        mock_figure.savefig.assert_called_once()
        mock_b64encode.assert_called_once_with(b'fake_image_data')
    
    def test_convert_figure_to_base64_error_handling(self):
        """Test error handling in figure to base64 conversion."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.gcf') as mock_gcf:
            mock_figure = Mock()
            mock_figure.savefig.side_effect = Exception("Save failed")
            mock_gcf.return_value = mock_figure
            
            with pytest.raises(ReportGenerationError, match="Failed to convert chart"):
                generator._convert_figure_to_base64()
    
    def test_prepare_chart_data_status_distribution(self):
        """Test chart data preparation for status distribution."""
        generator = ChartGenerator()
        
        metrics = {
            "status_counts": {"OPEN": 25, "RESOLVED": 75, "IN_PROGRESS": 10}
        }
        
        labels, values = generator._prepare_chart_data_status_distribution(metrics)
        
        assert labels == ["OPEN", "RESOLVED", "IN_PROGRESS"]
        assert values == [25, 75, 10]
    
    def test_prepare_chart_data_status_distribution_empty(self):
        """Test chart data preparation with empty status data."""
        generator = ChartGenerator()
        
        metrics = {"status_counts": {}}
        
        labels, values = generator._prepare_chart_data_status_distribution(metrics)
        
        assert labels == []
        assert values == []
    
    def test_prepare_chart_data_resolution_time(self):
        """Test chart data preparation for resolution time."""
        generator = ChartGenerator()
        
        metrics = {
            "resolution_time_by_severity": {"HIGH": 2.5, "MEDIUM": 8.0, "LOW": 24.0}
        }
        
        severities, times = generator._prepare_chart_data_resolution_time(metrics)
        
        assert severities == ["HIGH", "MEDIUM", "LOW"]
        assert times == [2.5, 8.0, 24.0]
    
    def test_prepare_chart_data_volume_trends(self):
        """Test chart data preparation for volume trends."""
        generator = ChartGenerator()
        
        trends = {
            "daily_trends": {
                "2024-01-01": 10,
                "2024-01-02": 15,
                "2024-01-03": 12
            }
        }
        
        dates, volumes = generator._prepare_chart_data_volume_trends(trends)
        
        assert len(dates) == 3
        assert volumes == [10, 15, 12]
        
        # Dates should be converted to datetime objects
        assert all(isinstance(date, datetime) for date in dates)
    
    def test_apply_chart_styling(self):
        """Test chart styling application."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.title') as mock_title, \
             patch('matplotlib.pyplot.xlabel') as mock_xlabel, \
             patch('matplotlib.pyplot.ylabel') as mock_ylabel, \
             patch('matplotlib.pyplot.grid') as mock_grid:
            
            generator._apply_chart_styling(
                title="Test Chart",
                xlabel="X Axis",
                ylabel="Y Axis",
                grid=True
            )
        
        mock_title.assert_called_once_with("Test Chart")
        mock_xlabel.assert_called_once_with("X Axis")
        mock_ylabel.assert_called_once_with("Y Axis")
        mock_grid.assert_called_once_with(True)
    
    def test_get_color_palette(self):
        """Test color palette generation."""
        generator = ChartGenerator()
        
        # Test default palette
        colors = generator._get_color_palette()
        assert isinstance(colors, list)
        assert len(colors) > 0
        assert all(isinstance(color, str) for color in colors)
        
        # Test custom count
        colors_5 = generator._get_color_palette(count=5)
        assert len(colors_5) == 5
    
    def test_format_chart_labels(self):
        """Test chart label formatting."""
        generator = ChartGenerator()
        
        test_cases = [
            (["OPEN", "RESOLVED", "IN_PROGRESS"], ["Open", "Resolved", "In Progress"]),
            (["HIGH", "MEDIUM", "LOW"], ["High", "Medium", "Low"]),
            (["status_count", "avg_time"], ["Status Count", "Avg Time"])
        ]
        
        for input_labels, expected in test_cases:
            result = generator._format_chart_labels(input_labels)
            assert result == expected
    
    def test_add_chart_annotations(self):
        """Test chart annotation addition."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.annotate') as mock_annotate:
            values = [25, 75, 10]
            positions = [(0, 25), (1, 75), (2, 10)]
            
            generator._add_chart_annotations(values, positions)
        
        # Should call annotate for each value
        assert mock_annotate.call_count == len(values)
    
    def test_set_chart_limits(self):
        """Test chart axis limits setting."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.xlim') as mock_xlim, \
             patch('matplotlib.pyplot.ylim') as mock_ylim:
            
            generator._set_chart_limits(x_min=0, x_max=10, y_min=0, y_max=100)
        
        mock_xlim.assert_called_once_with(0, 10)
        mock_ylim.assert_called_once_with(0, 100)


class TestChartGeneratorAdvancedCharts:
    """Test advanced chart generation features."""
    
    def test_generate_heatmap_chart(self):
        """Test heatmap chart generation."""
        generator = ChartGenerator()
        
        # Mock data for heatmap (e.g., tickets by day of week and hour)
        heatmap_data = [
            [5, 8, 12, 15, 18, 20, 15, 10],  # Monday
            [6, 9, 14, 16, 19, 22, 16, 11],  # Tuesday
            [4, 7, 11, 14, 17, 19, 14, 9],   # Wednesday
            [5, 8, 13, 15, 18, 21, 15, 10],  # Thursday
            [7, 10, 15, 17, 20, 23, 17, 12], # Friday
            [2, 3, 5, 7, 8, 9, 6, 4],        # Saturday
            [1, 2, 4, 6, 7, 8, 5, 3]         # Sunday
        ]
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.imshow') as mock_imshow, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_heatmap"
            
            result = generator._generate_heatmap_chart(heatmap_data)
        
        assert result == "base64_heatmap"
        mock_figure.assert_called_once()
        mock_imshow.assert_called_once()
    
    def test_generate_scatter_plot(self):
        """Test scatter plot generation."""
        generator = ChartGenerator()
        
        # Mock data for scatter plot (e.g., resolution time vs ticket age)
        x_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y_data = [2, 4, 3, 6, 5, 8, 7, 9, 8, 10]
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.scatter') as mock_scatter, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_scatter"
            
            result = generator._generate_scatter_plot(x_data, y_data)
        
        assert result == "base64_scatter"
        mock_figure.assert_called_once()
        mock_scatter.assert_called_once()
    
    def test_generate_stacked_bar_chart(self):
        """Test stacked bar chart generation."""
        generator = ChartGenerator()
        
        # Mock data for stacked bar chart (e.g., status by severity)
        categories = ["HIGH", "MEDIUM", "LOW"]
        open_counts = [5, 15, 10]
        resolved_counts = [10, 45, 15]
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.bar') as mock_bar, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_stacked_bar"
            
            result = generator._generate_stacked_bar_chart(categories, open_counts, resolved_counts)
        
        assert result == "base64_stacked_bar"
        mock_figure.assert_called_once()
        # Should call bar twice for stacked bars
        assert mock_bar.call_count == 2


class TestChartGeneratorSeabornIntegration:
    """Test Seaborn integration for advanced visualizations."""
    
    @patch('seaborn.set_style')
    def test_seaborn_style_application(self, mock_set_style):
        """Test Seaborn style application."""
        config = ReportConfig(chart_style="seaborn", seaborn_style="whitegrid")
        generator = ChartGenerator(config)
        
        mock_set_style.assert_called_with("whitegrid")
    
    def test_generate_seaborn_distribution_plot(self):
        """Test Seaborn distribution plot generation."""
        generator = ChartGenerator()
        
        # Mock resolution time data
        resolution_times = [2.5, 4.0, 1.5, 8.0, 6.5, 3.0, 12.0, 5.5, 7.0, 9.5]
        
        with patch('seaborn.histplot') as mock_histplot, \
             patch('matplotlib.pyplot.figure') as mock_figure, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_seaborn_dist"
            
            result = generator._generate_seaborn_distribution_plot(resolution_times)
        
        assert result == "base64_seaborn_dist"
        mock_figure.assert_called_once()
        mock_histplot.assert_called_once()
    
    def test_generate_seaborn_box_plot(self):
        """Test Seaborn box plot generation."""
        generator = ChartGenerator()
        
        # Mock data for box plot (resolution times by severity)
        data = {
            "HIGH": [1.0, 1.5, 2.0, 2.5, 3.0],
            "MEDIUM": [4.0, 5.0, 6.0, 7.0, 8.0],
            "LOW": [10.0, 12.0, 15.0, 18.0, 20.0]
        }
        
        with patch('seaborn.boxplot') as mock_boxplot, \
             patch('matplotlib.pyplot.figure') as mock_figure, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_seaborn_box"
            
            result = generator._generate_seaborn_box_plot(data)
        
        assert result == "base64_seaborn_box"
        mock_figure.assert_called_once()
        mock_boxplot.assert_called_once()


class TestChartGeneratorErrorHandling:
    """Test error handling in chart generation."""
    
    def test_matplotlib_import_error(self):
        """Test handling of matplotlib import errors."""
        with patch('matplotlib.pyplot.figure', side_effect=ImportError("matplotlib not available")):
            generator = ChartGenerator()
            
            with pytest.raises(ReportGenerationError, match="Chart generation requires matplotlib"):
                generator._generate_status_distribution_chart({})
    
    def test_chart_generation_memory_error(self):
        """Test handling of memory errors during chart generation."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.figure', side_effect=MemoryError("Out of memory")):
            with pytest.raises(ReportGenerationError, match="Insufficient memory"):
                generator._generate_status_distribution_chart({})
    
    def test_invalid_chart_data_handling(self):
        """Test handling of invalid chart data."""
        generator = ChartGenerator()
        
        # Test with invalid data types
        invalid_metrics = {
            "status_counts": "not_a_dict",
            "invalid_data": None
        }
        
        result = generator._generate_status_distribution_chart(invalid_metrics)
        
        # Should handle gracefully and return None or empty
        assert result is None or result == ""
    
    def test_figure_save_error_handling(self):
        """Test handling of figure save errors."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.gcf') as mock_gcf:
            mock_figure = Mock()
            mock_figure.savefig.side_effect = IOError("Cannot save figure")
            mock_gcf.return_value = mock_figure
            
            with pytest.raises(ReportGenerationError):
                generator._convert_figure_to_base64()
    
    @patch('ticket_analyzer.reporting.charts.logger')
    def test_error_logging_during_chart_generation(self, mock_logger):
        """Test error logging during chart generation."""
        generator = ChartGenerator()
        
        with patch('matplotlib.pyplot.figure', side_effect=Exception("Chart error")):
            with pytest.raises(ReportGenerationError):
                generator._generate_status_distribution_chart({})
        
        mock_logger.error.assert_called()


class TestChartGeneratorPerformance:
    """Test performance aspects of chart generation."""
    
    def test_large_dataset_chart_generation(self):
        """Test chart generation with large datasets."""
        generator = ChartGenerator()
        
        # Create large dataset
        large_trends = {
            "daily_trends": {
                f"2024-01-{i:02d}": i * 10 for i in range(1, 32)  # 31 days
            }
        }
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.plot') as mock_plot, \
             patch.object(generator, '_convert_figure_to_base64') as mock_convert:
            
            mock_convert.return_value = "base64_large_chart"
            
            # Should complete without timeout
            result = generator._generate_volume_trends_chart(large_trends)
        
        assert result == "base64_large_chart"
        mock_figure.assert_called_once()
        mock_plot.assert_called_once()
    
    def test_memory_efficient_chart_generation(self):
        """Test memory efficiency during chart generation."""
        generator = ChartGenerator()
        
        # Generate multiple charts to test memory usage
        for i in range(10):
            metrics = {
                "status_counts": {"OPEN": i * 5, "RESOLVED": i * 10}
            }
            
            with patch('matplotlib.pyplot.figure'), \
                 patch('matplotlib.pyplot.pie'), \
                 patch.object(generator, '_convert_figure_to_base64') as mock_convert:
                
                mock_convert.return_value = f"base64_chart_{i}"
                
                result = generator._generate_status_distribution_chart(metrics)
                assert result == f"base64_chart_{i}"
        
        # Should complete without memory issues
    
    def test_chart_generation_timeout_handling(self):
        """Test handling of chart generation timeouts."""
        generator = ChartGenerator()
        
        # Mock a slow chart generation process
        def slow_savefig(*args, **kwargs):
            import time
            time.sleep(0.1)  # Simulate slow operation
        
        with patch('matplotlib.pyplot.gcf') as mock_gcf, \
             patch('io.BytesIO') as mock_bytesio, \
             patch('base64.b64encode') as mock_b64encode:
            
            mock_figure = Mock()
            mock_figure.savefig = slow_savefig
            mock_gcf.return_value = mock_figure
            
            mock_buffer = Mock()
            mock_bytesio.return_value = mock_buffer
            mock_buffer.getvalue.return_value = b'chart_data'
            
            mock_b64encode.return_value = b'Y2hhcnRfZGF0YQ=='
            
            # Should complete even with slow operations
            result = generator._convert_figure_to_base64()
            assert "data:image/png;base64," in result


class TestChartGeneratorCustomization:
    """Test chart customization features."""
    
    def test_custom_color_schemes(self):
        """Test custom color scheme application."""
        config = ReportConfig(color_scheme="custom")
        generator = ChartGenerator(config)
        
        custom_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
        
        with patch.object(generator, '_get_custom_color_palette', return_value=custom_colors):
            colors = generator._get_color_palette()
        
        assert colors == custom_colors
    
    def test_chart_theme_application(self):
        """Test chart theme application."""
        themes = ["default", "dark", "minimal", "colorful"]
        
        for theme in themes:
            config = ReportConfig(chart_theme=theme)
            generator = ChartGenerator(config)
            
            # Should initialize without errors
            assert generator._config.chart_theme == theme
    
    def test_custom_figure_size(self):
        """Test custom figure size configuration."""
        config = ReportConfig(chart_width=15, chart_height=10)
        generator = ChartGenerator(config)
        
        assert generator._figure_size == (15, 10)
    
    def test_custom_dpi_setting(self):
        """Test custom DPI configuration."""
        config = ReportConfig(chart_dpi=200)
        generator = ChartGenerator(config)
        
        assert generator._dpi == 200