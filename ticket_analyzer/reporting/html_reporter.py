"""HTML report generator with Jinja2 template system.

This module provides HTML report generation capabilities using Jinja2 templates
with embedded CSS/JS and matplotlib chart integration. Supports responsive
design and customizable themes.
"""

from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

try:
    from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
except ImportError:
    raise ImportError("jinja2 is required for HTML reporting. Install with: pip install jinja2")

from ..interfaces import ReportingInterface
from ..models.analysis import AnalysisResult
from ..models.config import ReportConfig, OutputFormat
from ..models.exceptions import ReportGenerationError
from .charts import ChartGenerator
from .themes import ThemeManager, Theme

logger = logging.getLogger(__name__)


class HTMLReporter(ReportingInterface):
    """HTML report generator with Jinja2 template system.
    
    Generates professional HTML reports with embedded CSS/JS, responsive design,
    and support for matplotlib chart embedding. Uses Jinja2 templates for
    flexible report customization and theming.
    
    Attributes:
        template_dir: Directory containing Jinja2 templates
        jinja_env: Jinja2 environment for template rendering
        default_template: Default template name for reports
    """
    
    def __init__(self, template_dir: Optional[str] = None, 
                 chart_generator: Optional[ChartGenerator] = None,
                 theme_manager: Optional[ThemeManager] = None) -> None:
        """Initialize HTML reporter with template system.
        
        Args:
            template_dir: Directory containing Jinja2 templates.
                         Defaults to 'templates' in project root.
            chart_generator: Chart generator for visualizations.
            theme_manager: Theme manager for customization.
        
        Raises:
            ReportGenerationError: If template directory setup fails.
        """
        self.template_dir = self._setup_template_directory(template_dir)
        self.jinja_env = self._setup_jinja_environment()
        self.default_template = "report.html"
        self.chart_generator = chart_generator or ChartGenerator()
        self.theme_manager = theme_manager or ThemeManager()
        
        logger.info(f"HTML reporter initialized with template directory: {self.template_dir}")
    
    def generate_report(self, analysis: AnalysisResult, config: ReportConfig) -> str:
        """Generate HTML report from analysis results.
        
        Args:
            analysis: Analysis results to include in report.
            config: Configuration for report generation.
            
        Returns:
            Path to generated HTML report file.
            
        Raises:
            ReportGenerationError: If report generation fails.
        """
        try:
            # Validate configuration
            if config.format != OutputFormat.HTML:
                raise ReportGenerationError(
                    f"HTML reporter requires HTML format, got {config.format.value}"
                )
            
            # Determine output path
            output_path = self._determine_output_path(config)
            
            # Generate charts if enabled
            charts = {}
            if config.include_charts:
                charts = self.chart_generator.generate_charts_for_analysis(analysis)
            
            # Get theme
            theme = self.theme_manager.get_theme(config.theme)
            
            # Prepare template data
            template_data = self._prepare_template_data(analysis, config, charts, theme)
            
            # Load and render template
            template_name = config.template_name or self.default_template
            template = self._load_template(template_name)
            
            # Render HTML content
            html_content = template.render(**template_data)
            
            # Write to file
            self._write_html_file(html_content, output_path)
            
            logger.info(f"HTML report generated successfully: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise ReportGenerationError(f"HTML report generation failed: {e}")
    
    def supports_format(self, format_type: str) -> bool:
        """Check if reporter supports the specified format.
        
        Args:
            format_type: Format type to check.
            
        Returns:
            True if format is HTML, False otherwise.
        """
        return format_type.lower() == "html"
    
    def format_summary(self, analysis: AnalysisResult) -> str:
        """Format analysis summary for HTML display.
        
        Args:
            analysis: Analysis results to summarize.
            
        Returns:
            HTML-formatted summary string.
        """
        summary_data = {
            "total_tickets": analysis.ticket_count,
            "analysis_date": analysis.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "date_range": self._format_date_range(analysis.date_range),
            "duration": f"{analysis.analysis_duration:.2f}s" if analysis.analysis_duration else "N/A"
        }
        
        html_parts = ["<div class='summary-section'>"]
        html_parts.append("<h3>Analysis Summary</h3>")
        html_parts.append("<ul>")
        
        for key, value in summary_data.items():
            formatted_key = key.replace("_", " ").title()
            html_parts.append(f"<li><strong>{formatted_key}:</strong> {value}</li>")
        
        html_parts.append("</ul>")
        html_parts.append("</div>")
        
        return "\n".join(html_parts)
    
    def format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics data for HTML display.
        
        Args:
            metrics: Metrics dictionary to format.
            
        Returns:
            HTML-formatted metrics string.
        """
        if not metrics:
            return "<p>No metrics available.</p>"
        
        html_parts = ["<div class='metrics-section'>"]
        html_parts.append("<h3>Key Metrics</h3>")
        
        # Group metrics by category
        categorized_metrics = self._categorize_metrics(metrics)
        
        for category, category_metrics in categorized_metrics.items():
            html_parts.append(f"<h4>{category.title()}</h4>")
            html_parts.append("<table class='metrics-table'>")
            html_parts.append("<thead><tr><th>Metric</th><th>Value</th></tr></thead>")
            html_parts.append("<tbody>")
            
            for metric_name, value in category_metrics.items():
                formatted_name = metric_name.replace("_", " ").title()
                formatted_value = self._format_metric_value(value)
                html_parts.append(f"<tr><td>{formatted_name}</td><td>{formatted_value}</td></tr>")
            
            html_parts.append("</tbody>")
            html_parts.append("</table>")
        
        html_parts.append("</div>")
        return "\n".join(html_parts)
    
    def format_trends(self, trends: Dict[str, Any]) -> str:
        """Format trend data for HTML display.
        
        Args:
            trends: Trends dictionary to format.
            
        Returns:
            HTML-formatted trends string.
        """
        if not trends:
            return "<p>No trend data available.</p>"
        
        html_parts = ["<div class='trends-section'>"]
        html_parts.append("<h3>Trend Analysis</h3>")
        
        for trend_name, trend_data in trends.items():
            formatted_name = trend_name.replace("_", " ").title()
            html_parts.append(f"<h4>{formatted_name}</h4>")
            
            if isinstance(trend_data, dict):
                html_parts.append("<ul>")
                for key, value in trend_data.items():
                    formatted_key = key.replace("_", " ").title()
                    formatted_value = self._format_metric_value(value)
                    html_parts.append(f"<li><strong>{formatted_key}:</strong> {formatted_value}</li>")
                html_parts.append("</ul>")
            else:
                formatted_value = self._format_metric_value(trend_data)
                html_parts.append(f"<p>{formatted_value}</p>")
        
        html_parts.append("</div>")
        return "\n".join(html_parts)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats.
        
        Returns:
            List containing 'html'.
        """
        return ["html"]
    
    def _setup_template_directory(self, template_dir: Optional[str]) -> Path:
        """Setup template directory and ensure it exists.
        
        Args:
            template_dir: Custom template directory path.
            
        Returns:
            Path to template directory.
            
        Raises:
            ReportGenerationError: If template directory cannot be created or accessed.
        """
        if template_dir:
            template_path = Path(template_dir)
        else:
            # Default to templates directory in project root
            current_dir = Path(__file__).parent.parent.parent
            template_path = current_dir / "templates"
        
        try:
            template_path.mkdir(parents=True, exist_ok=True)
            return template_path
        except Exception as e:
            raise ReportGenerationError(f"Failed to setup template directory: {e}")
    
    def _setup_jinja_environment(self) -> Environment:
        """Setup Jinja2 environment with proper configuration.
        
        Returns:
            Configured Jinja2 Environment.
            
        Raises:
            ReportGenerationError: If Jinja2 environment setup fails.
        """
        try:
            env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=True,  # Enable auto-escaping for security
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            # Add custom filters
            env.filters['format_number'] = self._format_number_filter
            env.filters['format_datetime'] = self._format_datetime_filter
            env.filters['format_duration'] = self._format_duration_filter
            
            return env
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to setup Jinja2 environment: {e}")
    
    def _determine_output_path(self, config: ReportConfig) -> Path:
        """Determine output path for HTML report.
        
        Args:
            config: Report configuration.
            
        Returns:
            Path where report should be written.
        """
        if config.output_path:
            output_path = Path(config.output_path)
        else:
            # Default to reports directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path("reports") / f"ticket_analysis_{timestamp}.html"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return output_path
    
    def _prepare_template_data(self, analysis: AnalysisResult, config: ReportConfig, 
                              charts: Dict[str, str], theme: Theme) -> Dict[str, Any]:
        """Prepare data for template rendering.
        
        Args:
            analysis: Analysis results.
            config: Report configuration.
            charts: Generated charts as base64 images.
            theme: Theme configuration.
            
        Returns:
            Dictionary containing template data.
        """
        return {
            "title": "Ticket Analysis Report",
            "generated_at": analysis.generated_at,
            "analysis": analysis,
            "config": config,
            "metrics": analysis.metrics,
            "trends": analysis.trends,
            "summary": analysis.summary,
            "ticket_count": analysis.ticket_count,
            "date_range": analysis.date_range,
            "analysis_duration": analysis.analysis_duration,
            "theme": config.theme,
            "include_charts": config.include_charts,
            "sanitize_output": config.sanitize_output,
            "verbose": config.verbose,
            "charts": charts,
            "theme_css": theme.to_css(),
            "branding": theme.branding,
            # Helper functions for templates
            "format_number": self._format_number_filter,
            "format_datetime": self._format_datetime_filter,
            "format_duration": self._format_duration_filter,
            "json_dumps": json.dumps
        }
    
    def _load_template(self, template_name: str) -> Template:
        """Load Jinja2 template by name.
        
        Args:
            template_name: Name of template to load.
            
        Returns:
            Loaded Jinja2 Template.
            
        Raises:
            ReportGenerationError: If template cannot be loaded.
        """
        try:
            return self.jinja_env.get_template(template_name)
        except TemplateNotFound:
            # Try to create a basic template if default doesn't exist
            if template_name == self.default_template:
                logger.warning(f"Default template not found, creating basic template")
                return self._create_basic_template()
            else:
                raise ReportGenerationError(f"Template not found: {template_name}")
        except Exception as e:
            raise ReportGenerationError(f"Failed to load template {template_name}: {e}")
    
    def _create_basic_template(self) -> Template:
        """Create a basic HTML template if none exists.
        
        Returns:
            Basic Jinja2 Template.
        """
        basic_template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; }
        .section { margin: 20px 0; }
        .metrics-table { border-collapse: collapse; width: 100%; }
        .metrics-table th, .metrics-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .metrics-table th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Generated on: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <p>Total Tickets: {{ ticket_count }}</p>
        {% if date_range %}
        <p>Date Range: {{ date_range[0] }} to {{ date_range[1] }}</p>
        {% endif %}
    </div>
    
    <div class="section">
        <h2>Metrics</h2>
        {% if metrics %}
        <table class="metrics-table">
            <thead>
                <tr><th>Metric</th><th>Value</th></tr>
            </thead>
            <tbody>
                {% for key, value in metrics.items() %}
                <tr>
                    <td>{{ key.replace('_', ' ').title() }}</td>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No metrics available.</p>
        {% endif %}
    </div>
</body>
</html>
        """.strip()
        
        return self.jinja_env.from_string(basic_template_content)
    
    def _write_html_file(self, content: str, output_path: Path) -> None:
        """Write HTML content to file.
        
        Args:
            content: HTML content to write.
            output_path: Path where file should be written.
            
        Raises:
            ReportGenerationError: If file writing fails.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise ReportGenerationError(f"Failed to write HTML file {output_path}: {e}")
    
    def _categorize_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Categorize metrics for better organization.
        
        Args:
            metrics: Metrics dictionary.
            
        Returns:
            Dictionary of categorized metrics.
        """
        categories = {
            "resolution": {},
            "status": {},
            "volume": {},
            "performance": {},
            "general": {}
        }
        
        for key, value in metrics.items():
            key_lower = key.lower()
            if "resolution" in key_lower or "time" in key_lower:
                categories["resolution"][key] = value
            elif "status" in key_lower or "distribution" in key_lower:
                categories["status"][key] = value
            elif "count" in key_lower or "total" in key_lower or "volume" in key_lower:
                categories["volume"][key] = value
            elif "performance" in key_lower or "percentile" in key_lower:
                categories["performance"][key] = value
            else:
                categories["general"][key] = value
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _format_metric_value(self, value: Any) -> str:
        """Format metric value for display.
        
        Args:
            value: Value to format.
            
        Returns:
            Formatted string representation.
        """
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            else:
                return f"{value:.2f}"
        elif isinstance(value, dict):
            return json.dumps(value, indent=2)
        elif isinstance(value, list):
            return ", ".join(str(item) for item in value)
        else:
            return str(value)
    
    def _format_date_range(self, date_range: Optional[tuple]) -> str:
        """Format date range for display.
        
        Args:
            date_range: Tuple of start and end dates.
            
        Returns:
            Formatted date range string.
        """
        if not date_range or len(date_range) != 2:
            return "N/A"
        
        start_date, end_date = date_range
        if isinstance(start_date, datetime) and isinstance(end_date, datetime):
            return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        else:
            return f"{start_date} to {end_date}"
    
    # Jinja2 filter functions
    def _format_number_filter(self, value: Any) -> str:
        """Jinja2 filter for formatting numbers.
        
        Args:
            value: Number to format.
            
        Returns:
            Formatted number string.
        """
        if isinstance(value, (int, float)):
            if isinstance(value, float) and value.is_integer():
                return f"{int(value):,}"
            elif isinstance(value, float):
                return f"{value:,.2f}"
            else:
                return f"{value:,}"
        return str(value)
    
    def _format_datetime_filter(self, value: Any, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Jinja2 filter for formatting datetime objects.
        
        Args:
            value: Datetime to format.
            format_str: Format string for datetime.
            
        Returns:
            Formatted datetime string.
        """
        if isinstance(value, datetime):
            return value.strftime(format_str)
        return str(value)
    
    def _format_duration_filter(self, value: Any) -> str:
        """Jinja2 filter for formatting duration values.
        
        Args:
            value: Duration in seconds.
            
        Returns:
            Formatted duration string.
        """
        if isinstance(value, (int, float)):
            if value < 60:
                return f"{value:.1f}s"
            elif value < 3600:
                minutes = value / 60
                return f"{minutes:.1f}m"
            else:
                hours = value / 3600
                return f"{hours:.1f}h"
        return str(value)