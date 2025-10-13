"""Chart generation and visualization system for HTML reports.

This module provides comprehensive chart generation capabilities using matplotlib
and seaborn for statistical visualizations. Charts are embedded as base64 images
in HTML reports for self-contained report files.
"""

from __future__ import annotations
import io
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import json

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
except ImportError:
    raise ImportError("matplotlib is required for chart generation. Install with: pip install matplotlib")

try:
    import seaborn as sns
    sns.set_style("whitegrid")
except ImportError:
    raise ImportError("seaborn is required for advanced visualizations. Install with: pip install seaborn")

try:
    import pandas as pd
except ImportError:
    raise ImportError("pandas is required for data processing. Install with: pip install pandas")

import numpy as np

from ..models.analysis import AnalysisResult
from ..models.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Chart generator for ticket analysis visualizations.
    
    Provides comprehensive chart generation capabilities including line charts,
    bar charts, pie charts, heatmaps, and scatter plots. Charts are optimized
    for HTML embedding with base64 encoding.
    
    Attributes:
        figure_size: Default figure size for charts (width, height)
        dpi: Resolution for chart images
        color_palette: Default color palette for charts
        style: Chart style configuration
    """
    
    def __init__(self, figure_size: Tuple[int, int] = (10, 6), dpi: int = 100) -> None:
        """Initialize chart generator with configuration.
        
        Args:
            figure_size: Default figure size (width, height) in inches.
            dpi: Resolution for generated images.
        """
        self.figure_size = figure_size
        self.dpi = dpi
        self.color_palette = sns.color_palette("husl", 10)
        self.style = {
            'font_size': 10,
            'title_size': 14,
            'label_size': 12,
            'legend_size': 10,
            'grid_alpha': 0.3
        }
        
        # Configure matplotlib defaults
        plt.rcParams.update({
            'font.size': self.style['font_size'],
            'axes.titlesize': self.style['title_size'],
            'axes.labelsize': self.style['label_size'],
            'legend.fontsize': self.style['legend_size'],
            'grid.alpha': self.style['grid_alpha']
        })
        
        logger.info("Chart generator initialized")
    
    def generate_charts_for_analysis(self, analysis: AnalysisResult) -> Dict[str, str]:
        """Generate all relevant charts for analysis results.
        
        Args:
            analysis: Analysis results to visualize.
            
        Returns:
            Dictionary mapping chart names to base64-encoded images.
            
        Raises:
            ReportGenerationError: If chart generation fails.
        """
        try:
            charts = {}
            
            # Generate charts based on available metrics
            if analysis.metrics:
                charts.update(self._generate_metrics_charts(analysis.metrics))
            
            if analysis.trends:
                charts.update(self._generate_trend_charts(analysis.trends))
            
            # Generate summary charts
            charts.update(self._generate_summary_charts(analysis))
            
            logger.info(f"Generated {len(charts)} charts for analysis")
            return charts
            
        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")
            raise ReportGenerationError(f"Chart generation failed: {e}")
    
    def create_line_chart(self, data: Dict[str, Any], title: str = "Line Chart",
                         x_label: str = "X", y_label: str = "Y") -> str:
        """Create line chart from data.
        
        Args:
            data: Dictionary with 'x' and 'y' keys containing data arrays.
            title: Chart title.
            x_label: X-axis label.
            y_label: Y-axis label.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            if isinstance(data, dict) and 'x' in data and 'y' in data:
                ax.plot(data['x'], data['y'], linewidth=2, color=self.color_palette[0])
            elif isinstance(data, dict):
                # Handle multiple series
                for i, (series_name, series_data) in enumerate(data.items()):
                    if isinstance(series_data, (list, np.ndarray)):
                        ax.plot(series_data, label=series_name, 
                               color=self.color_palette[i % len(self.color_palette)])
                ax.legend()
            
            ax.set_title(title, fontsize=self.style['title_size'], fontweight='bold')
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.grid(True, alpha=self.style['grid_alpha'])
            
            plt.tight_layout()
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create line chart: {e}")
            raise ReportGenerationError(f"Line chart creation failed: {e}")
        finally:
            plt.close(fig)
    
    def create_bar_chart(self, data: Dict[str, Union[int, float]], title: str = "Bar Chart",
                        x_label: str = "Categories", y_label: str = "Values",
                        horizontal: bool = False) -> str:
        """Create bar chart from data.
        
        Args:
            data: Dictionary mapping categories to values.
            title: Chart title.
            x_label: X-axis label.
            y_label: Y-axis label.
            horizontal: Whether to create horizontal bar chart.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            categories = list(data.keys())
            values = list(data.values())
            
            if horizontal:
                bars = ax.barh(categories, values, color=self.color_palette[:len(categories)])
                ax.set_xlabel(y_label)
                ax.set_ylabel(x_label)
            else:
                bars = ax.bar(categories, values, color=self.color_palette[:len(categories)])
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                
                # Rotate x-axis labels if they're long
                if any(len(str(cat)) > 10 for cat in categories):
                    plt.xticks(rotation=45, ha='right')
            
            ax.set_title(title, fontsize=self.style['title_size'], fontweight='bold')
            ax.grid(True, alpha=self.style['grid_alpha'])
            
            # Add value labels on bars
            for bar in bars:
                if horizontal:
                    width = bar.get_width()
                    ax.text(width, bar.get_y() + bar.get_height()/2, 
                           f'{width:.1f}', ha='left', va='center')
                else:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2, height,
                           f'{height:.1f}', ha='center', va='bottom')
            
            plt.tight_layout()
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create bar chart: {e}")
            raise ReportGenerationError(f"Bar chart creation failed: {e}")
        finally:
            plt.close(fig)
    
    def create_pie_chart(self, data: Dict[str, Union[int, float]], title: str = "Pie Chart",
                        show_percentages: bool = True) -> str:
        """Create pie chart from data.
        
        Args:
            data: Dictionary mapping categories to values.
            title: Chart title.
            show_percentages: Whether to show percentages on slices.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            labels = list(data.keys())
            values = list(data.values())
            
            # Filter out zero values
            non_zero_data = [(label, value) for label, value in zip(labels, values) if value > 0]
            if not non_zero_data:
                raise ValueError("No non-zero values for pie chart")
            
            labels, values = zip(*non_zero_data)
            
            autopct = '%1.1f%%' if show_percentages else None
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct=autopct,
                                             colors=self.color_palette[:len(labels)],
                                             startangle=90)
            
            ax.set_title(title, fontsize=self.style['title_size'], fontweight='bold')
            
            # Improve text readability
            if autotexts:
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
            
            plt.tight_layout()
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create pie chart: {e}")
            raise ReportGenerationError(f"Pie chart creation failed: {e}")
        finally:
            plt.close(fig)
    
    def create_heatmap(self, data: Union[Dict[str, Dict[str, float]], pd.DataFrame],
                      title: str = "Heatmap", x_label: str = "X", y_label: str = "Y") -> str:
        """Create heatmap from data.
        
        Args:
            data: 2D data structure for heatmap.
            title: Chart title.
            x_label: X-axis label.
            y_label: Y-axis label.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data
            
            # Create heatmap
            sns.heatmap(df, annot=True, cmap='YlOrRd', ax=ax, 
                       cbar_kws={'label': 'Value'}, fmt='.1f')
            
            ax.set_title(title, fontsize=self.style['title_size'], fontweight='bold')
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            
            plt.tight_layout()
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create heatmap: {e}")
            raise ReportGenerationError(f"Heatmap creation failed: {e}")
        finally:
            plt.close(fig)
    
    def create_scatter_plot(self, data: Dict[str, List[float]], title: str = "Scatter Plot",
                           x_label: str = "X", y_label: str = "Y") -> str:
        """Create scatter plot from data.
        
        Args:
            data: Dictionary with 'x' and 'y' keys containing coordinate arrays.
            title: Chart title.
            x_label: X-axis label.
            y_label: Y-axis label.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            x_data = data.get('x', [])
            y_data = data.get('y', [])
            
            if len(x_data) != len(y_data):
                raise ValueError("X and Y data must have same length")
            
            ax.scatter(x_data, y_data, alpha=0.6, color=self.color_palette[0], s=50)
            
            # Add trend line if enough points
            if len(x_data) > 2:
                z = np.polyfit(x_data, y_data, 1)
                p = np.poly1d(z)
                ax.plot(x_data, p(x_data), "r--", alpha=0.8, linewidth=2)
            
            ax.set_title(title, fontsize=self.style['title_size'], fontweight='bold')
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.grid(True, alpha=self.style['grid_alpha'])
            
            plt.tight_layout()
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create scatter plot: {e}")
            raise ReportGenerationError(f"Scatter plot creation failed: {e}")
        finally:
            plt.close(fig)
    
    def create_time_series_chart(self, data: Dict[str, List], title: str = "Time Series",
                               y_label: str = "Value") -> str:
        """Create time series chart from data.
        
        Args:
            data: Dictionary with 'timestamps' and 'values' keys.
            title: Chart title.
            y_label: Y-axis label.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])
            
            if len(timestamps) != len(values):
                raise ValueError("Timestamps and values must have same length")
            
            # Convert timestamps to datetime if they're strings
            if timestamps and isinstance(timestamps[0], str):
                timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) 
                             for ts in timestamps]
            
            ax.plot(timestamps, values, linewidth=2, color=self.color_palette[0], marker='o')
            
            # Format x-axis for dates
            if timestamps and isinstance(timestamps[0], datetime):
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(timestamps)//10)))
                plt.xticks(rotation=45)
            
            ax.set_title(title, fontsize=self.style['title_size'], fontweight='bold')
            ax.set_xlabel("Time")
            ax.set_ylabel(y_label)
            ax.grid(True, alpha=self.style['grid_alpha'])
            
            plt.tight_layout()
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create time series chart: {e}")
            raise ReportGenerationError(f"Time series chart creation failed: {e}")
        finally:
            plt.close(fig)
    
    def _generate_metrics_charts(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate charts for metrics data.
        
        Args:
            metrics: Metrics dictionary.
            
        Returns:
            Dictionary of chart names to base64 images.
        """
        charts = {}
        
        try:
            # Status distribution pie chart
            if 'status_counts' in metrics:
                charts['status_distribution'] = self.create_pie_chart(
                    metrics['status_counts'],
                    title="Ticket Status Distribution"
                )
            
            # Resolution time by severity bar chart
            if 'by_severity' in metrics and isinstance(metrics['by_severity'], dict):
                charts['resolution_by_severity'] = self.create_bar_chart(
                    metrics['by_severity'],
                    title="Average Resolution Time by Severity",
                    x_label="Severity",
                    y_label="Hours"
                )
            
            # Percentiles bar chart
            if 'percentiles' in metrics and isinstance(metrics['percentiles'], dict):
                charts['resolution_percentiles'] = self.create_bar_chart(
                    metrics['percentiles'],
                    title="Resolution Time Percentiles",
                    x_label="Percentile",
                    y_label="Hours"
                )
            
        except Exception as e:
            logger.warning(f"Failed to generate some metrics charts: {e}")
        
        return charts
    
    def _generate_trend_charts(self, trends: Dict[str, Any]) -> Dict[str, str]:
        """Generate charts for trend data.
        
        Args:
            trends: Trends dictionary.
            
        Returns:
            Dictionary of chart names to base64 images.
        """
        charts = {}
        
        try:
            # Weekly trends line chart
            if 'weekly_trends' in trends and isinstance(trends['weekly_trends'], dict):
                charts['weekly_trends'] = self._create_weekly_trends_chart(trends['weekly_trends'])
            
            # Volume trends over time
            if 'volume_trends' in trends:
                charts['volume_trends'] = self._create_volume_trends_chart(trends['volume_trends'])
            
        except Exception as e:
            logger.warning(f"Failed to generate some trend charts: {e}")
        
        return charts
    
    def _generate_summary_charts(self, analysis: AnalysisResult) -> Dict[str, str]:
        """Generate summary charts for analysis.
        
        Args:
            analysis: Analysis results.
            
        Returns:
            Dictionary of chart names to base64 images.
        """
        charts = {}
        
        try:
            # Create a summary metrics bar chart
            summary_metrics = {}
            if analysis.metrics:
                if 'total_resolved' in analysis.metrics:
                    summary_metrics['Resolved'] = analysis.metrics['total_resolved']
                if 'avg_resolution_time_hours' in analysis.metrics:
                    summary_metrics['Avg Resolution (hrs)'] = analysis.metrics['avg_resolution_time_hours']
                if analysis.ticket_count:
                    summary_metrics['Total Tickets'] = analysis.ticket_count
            
            if summary_metrics:
                charts['summary_metrics'] = self.create_bar_chart(
                    summary_metrics,
                    title="Key Metrics Summary",
                    x_label="Metrics",
                    y_label="Value"
                )
            
        except Exception as e:
            logger.warning(f"Failed to generate summary charts: {e}")
        
        return charts
    
    def _create_weekly_trends_chart(self, weekly_data: Dict[str, Any]) -> str:
        """Create weekly trends chart.
        
        Args:
            weekly_data: Weekly trend data.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)
            
            # Convert weekly data to plottable format
            weeks = []
            status_data = {}
            
            for status, week_counts in weekly_data.items():
                if isinstance(week_counts, dict):
                    for week, count in week_counts.items():
                        if week not in weeks:
                            weeks.append(week)
                        if status not in status_data:
                            status_data[status] = []
            
            weeks.sort()
            
            # Fill in data for each status
            for status in status_data:
                counts = []
                for week in weeks:
                    count = weekly_data.get(status, {}).get(week, 0)
                    counts.append(count)
                status_data[status] = counts
            
            # Plot lines for each status
            for i, (status, counts) in enumerate(status_data.items()):
                ax.plot(weeks, counts, label=status, 
                       color=self.color_palette[i % len(self.color_palette)],
                       marker='o', linewidth=2)
            
            ax.set_title("Weekly Ticket Trends by Status", 
                        fontsize=self.style['title_size'], fontweight='bold')
            ax.set_xlabel("Week")
            ax.set_ylabel("Ticket Count")
            ax.legend()
            ax.grid(True, alpha=self.style['grid_alpha'])
            
            # Rotate x-axis labels
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            return self._figure_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create weekly trends chart: {e}")
            raise ReportGenerationError(f"Weekly trends chart creation failed: {e}")
        finally:
            plt.close(fig)
    
    def _create_volume_trends_chart(self, volume_data: Any) -> str:
        """Create volume trends chart.
        
        Args:
            volume_data: Volume trend data.
            
        Returns:
            Base64-encoded chart image.
        """
        try:
            # This is a placeholder implementation
            # In a real scenario, you'd process the volume_data appropriately
            sample_data = {
                'timestamps': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
                'values': [10, 15, 12, 18]
            }
            
            return self.create_time_series_chart(
                sample_data,
                title="Ticket Volume Trends",
                y_label="Ticket Count"
            )
            
        except Exception as e:
            logger.error(f"Failed to create volume trends chart: {e}")
            raise ReportGenerationError(f"Volume trends chart creation failed: {e}")
    
    def _figure_to_base64(self, fig: Figure) -> str:
        """Convert matplotlib figure to base64 string.
        
        Args:
            fig: Matplotlib figure to convert.
            
        Returns:
            Base64-encoded image string.
        """
        try:
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=self.dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            buffer.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Failed to convert figure to base64: {e}")
            raise ReportGenerationError(f"Figure conversion failed: {e}")
    
    def set_style(self, style_config: Dict[str, Any]) -> None:
        """Update chart style configuration.
        
        Args:
            style_config: Dictionary containing style parameters.
        """
        self.style.update(style_config)
        
        # Update matplotlib parameters
        plt.rcParams.update({
            'font.size': self.style.get('font_size', 10),
            'axes.titlesize': self.style.get('title_size', 14),
            'axes.labelsize': self.style.get('label_size', 12),
            'legend.fontsize': self.style.get('legend_size', 10),
            'grid.alpha': self.style.get('grid_alpha', 0.3)
        })
        
        logger.info("Chart style updated")
    
    def set_color_palette(self, palette: Union[str, List[str]]) -> None:
        """Set color palette for charts.
        
        Args:
            palette: Seaborn palette name or list of color codes.
        """
        if isinstance(palette, str):
            self.color_palette = sns.color_palette(palette, 10)
        else:
            self.color_palette = palette
        
        logger.info(f"Color palette updated: {palette}")