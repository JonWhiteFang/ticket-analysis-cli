"""CLI reporter with color coding and tabular formatting.

This module provides the CLIReporter class for generating formatted CLI output
with color coding, tabular data presentation, and summary statistics display.
Uses colorama for cross-platform color support and rich formatting capabilities.
"""

from __future__ import annotations
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color constants
    class Fore:
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        WHITE = ""
        RESET = ""
    
    class Back:
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        WHITE = ""
        RESET = ""
    
    class Style:
        BRIGHT = ""
        DIM = ""
        NORMAL = ""
        RESET_ALL = ""

from ..interfaces import ReportingInterface, FormatterInterface
from ..models import AnalysisResult, ReportConfig
from ..models.exceptions import ReportGenerationError


class CLIColorScheme:
    """Color scheme definitions for CLI output."""
    
    # Status colors
    SUCCESS = Fore.GREEN + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    INFO = Fore.BLUE + Style.BRIGHT
    
    # Data type colors
    HEADER = Fore.CYAN + Style.BRIGHT
    SUBHEADER = Fore.MAGENTA + Style.BRIGHT
    METRIC_VALUE = Fore.WHITE + Style.BRIGHT
    METRIC_LABEL = Fore.CYAN
    
    # Severity colors
    SEV_1 = Fore.RED + Back.WHITE + Style.BRIGHT
    SEV_2 = Fore.RED + Style.BRIGHT
    SEV_3 = Fore.YELLOW + Style.BRIGHT
    SEV_4 = Fore.BLUE
    SEV_5 = Fore.WHITE
    
    # Status colors
    OPEN = Fore.RED
    IN_PROGRESS = Fore.YELLOW
    RESOLVED = Fore.GREEN
    CLOSED = Fore.BLUE
    
    # Reset
    RESET = Style.RESET_ALL


class CLITableFormatter:
    """Formatter for tabular data in CLI output."""
    
    def __init__(self, color_scheme: CLIColorScheme) -> None:
        self._colors = color_scheme
    
    def format_table(self, data: List[Dict[str, Any]], 
                    headers: List[str], 
                    title: Optional[str] = None,
                    max_width: int = 120) -> str:
        """Format data as a table with proper alignment and colors.
        
        Args:
            data: List of row data dictionaries.
            headers: List of column headers.
            title: Optional table title.
            max_width: Maximum table width in characters.
            
        Returns:
            Formatted table string.
        """
        if not data:
            return f"{self._colors.WARNING}No data to display{self._colors.RESET}\n"
        
        # Calculate column widths
        col_widths = self._calculate_column_widths(data, headers, max_width)
        
        # Build table
        lines = []
        
        # Add title if provided
        if title:
            title_line = f"{self._colors.HEADER}{title}{self._colors.RESET}"
            lines.append(title_line)
            lines.append("=" * len(title))
            lines.append("")
        
        # Add header row
        header_row = self._format_row(headers, col_widths, self._colors.HEADER)
        lines.append(header_row)
        
        # Add separator
        separator = "+" + "+".join("-" * (width + 2) for width in col_widths.values()) + "+"
        lines.append(separator)
        
        # Add data rows
        for row_data in data:
            row_values = [str(row_data.get(header, "")) for header in headers]
            colored_values = self._apply_row_colors(row_values, headers, row_data)
            row_line = self._format_row(colored_values, col_widths)
            lines.append(row_line)
        
        return "\n".join(lines) + "\n"
    
    def _calculate_column_widths(self, data: List[Dict[str, Any]], 
                               headers: List[str], 
                               max_width: int) -> Dict[str, int]:
        """Calculate optimal column widths."""
        col_widths = {}
        
        # Start with header widths
        for header in headers:
            col_widths[header] = len(header)
        
        # Check data widths
        for row in data:
            for header in headers:
                value_len = len(str(row.get(header, "")))
                col_widths[header] = max(col_widths[header], value_len)
        
        # Adjust for max width constraint
        total_width = sum(col_widths.values()) + len(headers) * 3 + 1
        if total_width > max_width:
            # Proportionally reduce column widths
            reduction_factor = (max_width - len(headers) * 3 - 1) / sum(col_widths.values())
            for header in headers:
                col_widths[header] = max(8, int(col_widths[header] * reduction_factor))
        
        return col_widths
    
    def _format_row(self, values: List[str], 
                   col_widths: Dict[str, int], 
                   color: str = "") -> str:
        """Format a single table row."""
        formatted_cells = []
        headers = list(col_widths.keys())
        
        for i, value in enumerate(values):
            header = headers[i] if i < len(headers) else f"col_{i}"
            width = col_widths.get(header, 10)
            
            # Truncate if too long
            if len(value) > width:
                value = value[:width-3] + "..."
            
            # Apply color and padding
            if color:
                cell = f"{color}{value:<{width}}{self._colors.RESET}"
            else:
                cell = f"{value:<{width}}"
            
            formatted_cells.append(cell)
        
        return "| " + " | ".join(formatted_cells) + " |"
    
    def _apply_row_colors(self, values: List[str], 
                         headers: List[str], 
                         row_data: Dict[str, Any]) -> List[str]:
        """Apply colors to row values based on content."""
        colored_values = []
        
        for i, value in enumerate(values):
            header = headers[i] if i < len(headers) else ""
            colored_value = self._colorize_value(value, header, row_data)
            colored_values.append(colored_value)
        
        return colored_values
    
    def _colorize_value(self, value: str, header: str, row_data: Dict[str, Any]) -> str:
        """Apply appropriate color to a cell value."""
        header_lower = header.lower()
        
        # Status coloring
        if "status" in header_lower:
            if value.lower() in ["open", "new"]:
                return f"{self._colors.OPEN}{value}{self._colors.RESET}"
            elif value.lower() in ["in progress", "assigned", "researching"]:
                return f"{self._colors.IN_PROGRESS}{value}{self._colors.RESET}"
            elif value.lower() in ["resolved", "fixed"]:
                return f"{self._colors.RESOLVED}{value}{self._colors.RESET}"
            elif value.lower() in ["closed", "done"]:
                return f"{self._colors.CLOSED}{value}{self._colors.RESET}"
        
        # Severity coloring
        elif "severity" in header_lower or "priority" in header_lower:
            if value.upper() in ["SEV_1", "CRITICAL", "HIGH"]:
                return f"{self._colors.SEV_1}{value}{self._colors.RESET}"
            elif value.upper() in ["SEV_2", "HIGH"]:
                return f"{self._colors.SEV_2}{value}{self._colors.RESET}"
            elif value.upper() in ["SEV_3", "MEDIUM"]:
                return f"{self._colors.SEV_3}{value}{self._colors.RESET}"
            elif value.upper() in ["SEV_4", "LOW"]:
                return f"{self._colors.SEV_4}{value}{self._colors.RESET}"
            elif value.upper() in ["SEV_5", "LOWEST"]:
                return f"{self._colors.SEV_5}{value}{self._colors.RESET}"
        
        # Numeric values
        elif header_lower in ["count", "total", "average", "median"]:
            return f"{self._colors.METRIC_VALUE}{value}{self._colors.RESET}"
        
        return value


class CLIReporter(ReportingInterface):
    """CLI reporter with color coding and rich formatting.
    
    This class generates formatted CLI output with color coding, tabular data
    presentation, and summary statistics display. Uses colorama for cross-platform
    color support and provides comprehensive formatting for analysis results.
    """
    
    def __init__(self, use_colors: bool = True, max_width: int = 120) -> None:
        """Initialize CLI reporter.
        
        Args:
            use_colors: Whether to use color output (default: True).
            max_width: Maximum output width in characters (default: 120).
        """
        self._use_colors = use_colors and COLORAMA_AVAILABLE
        self._max_width = max_width
        self._colors = CLIColorScheme()
        self._table_formatter = CLITableFormatter(self._colors)
        
        # Disable colors if not supported or requested
        if not self._use_colors:
            self._disable_colors()
    
    def _disable_colors(self) -> None:
        """Disable color output by setting all colors to empty strings."""
        for attr in dir(self._colors):
            if not attr.startswith('_'):
                setattr(self._colors, attr, "")
    
    def generate_report(self, analysis: AnalysisResult, config: ReportConfig) -> str:
        """Generate comprehensive CLI report from analysis results.
        
        Args:
            analysis: Analysis results to include in report.
            config: Configuration for report generation.
            
        Returns:
            Generated CLI report as string.
            
        Raises:
            ReportGenerationError: If report generation fails.
        """
        try:
            report_sections = []
            
            # Report header
            report_sections.append(self._generate_header(analysis))
            
            # Summary section
            report_sections.append(self._generate_summary_section(analysis))
            
            # Metrics section
            if analysis.metrics:
                report_sections.append(self._generate_metrics_section(analysis.metrics))
            
            # Trends section
            if hasattr(analysis, 'trends') and analysis.trends:
                report_sections.append(self._generate_trends_section(analysis.trends))
            
            # Key insights section
            if hasattr(analysis, 'summary') and analysis.summary:
                report_sections.append(self._generate_insights_section(analysis.summary))
            
            # Report footer
            report_sections.append(self._generate_footer(analysis))
            
            return "\n\n".join(report_sections)
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate CLI report: {e}")
    
    def supports_format(self, format_type: str) -> bool:
        """Check if reporter supports the specified format.
        
        Args:
            format_type: Format type to check.
            
        Returns:
            True if format is 'cli' or 'table', False otherwise.
        """
        return format_type.lower() in ['cli', 'table', 'console']
    
    def format_summary(self, analysis: AnalysisResult) -> str:
        """Format analysis summary for display.
        
        Args:
            analysis: Analysis results to summarize.
            
        Returns:
            Formatted summary string.
        """
        return self._generate_summary_section(analysis)
    
    def format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics data for display.
        
        Args:
            metrics: Metrics dictionary to format.
            
        Returns:
            Formatted metrics string.
        """
        return self._generate_metrics_section(metrics)
    
    def format_trends(self, trends: Dict[str, Any]) -> str:
        """Format trend data for display.
        
        Args:
            trends: Trends dictionary to format.
            
        Returns:
            Formatted trends string.
        """
        return self._generate_trends_section(trends)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats.
        
        Returns:
            List of supported format strings.
        """
        return ['cli', 'table', 'console']
    
    def _generate_header(self, analysis: AnalysisResult) -> str:
        """Generate report header with title and metadata."""
        header_lines = []
        
        # Main title
        title = "TICKET ANALYSIS REPORT"
        title_line = f"{self._colors.HEADER}{title}{self._colors.RESET}"
        header_lines.append(title_line)
        header_lines.append("=" * len(title))
        
        # Metadata
        metadata = [
            f"Generated: {analysis.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Tickets: {self._colors.METRIC_VALUE}{analysis.ticket_count}{self._colors.RESET}",
        ]
        
        if hasattr(analysis, 'date_range') and analysis.date_range:
            start_date, end_date = analysis.date_range
            metadata.append(f"Date Range: {start_date} to {end_date}")
        
        header_lines.extend(metadata)
        
        return "\n".join(header_lines)
    
    def _generate_summary_section(self, analysis: AnalysisResult) -> str:
        """Generate summary statistics section."""
        section_lines = []
        
        # Section title
        section_lines.append(f"{self._colors.SUBHEADER}SUMMARY{self._colors.RESET}")
        section_lines.append("-" * 20)
        
        # Basic statistics
        summary_data = [
            ("Total Tickets Analyzed", analysis.ticket_count),
            ("Analysis Generated", analysis.generated_at.strftime('%Y-%m-%d %H:%M:%S')),
        ]
        
        # Add date range if available
        if hasattr(analysis, 'date_range') and analysis.date_range:
            start_date, end_date = analysis.date_range
            summary_data.append(("Date Range", f"{start_date} to {end_date}"))
        
        # Format as key-value pairs
        for label, value in summary_data:
            formatted_line = f"{self._colors.METRIC_LABEL}{label}:{self._colors.RESET} {self._colors.METRIC_VALUE}{value}{self._colors.RESET}"
            section_lines.append(formatted_line)
        
        return "\n".join(section_lines)
    
    def _generate_metrics_section(self, metrics: Dict[str, Any]) -> str:
        """Generate metrics section with formatted data."""
        section_lines = []
        
        # Section title
        section_lines.append(f"{self._colors.SUBHEADER}METRICS{self._colors.RESET}")
        section_lines.append("-" * 20)
        
        # Resolution time metrics
        if 'resolution_time' in metrics or any('resolution' in key for key in metrics.keys()):
            section_lines.append(self._format_resolution_metrics(metrics))
        
        # Status distribution
        if 'status_distribution' in metrics or 'status_counts' in metrics:
            section_lines.append(self._format_status_metrics(metrics))
        
        # Volume metrics
        if 'volume_trends' in metrics or 'ticket_volume' in metrics:
            section_lines.append(self._format_volume_metrics(metrics))
        
        # Team performance
        if 'team_performance' in metrics or 'assignee_workload' in metrics:
            section_lines.append(self._format_team_metrics(metrics))
        
        return "\n".join(section_lines)
    
    def _format_resolution_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format resolution time metrics."""
        lines = []
        lines.append(f"{self._colors.HEADER}Resolution Time Analysis{self._colors.RESET}")
        
        # Extract resolution metrics
        resolution_data = []
        
        if 'avg_resolution_time_hours' in metrics:
            avg_hours = metrics['avg_resolution_time_hours']
            resolution_data.append(("Average Resolution Time", f"{avg_hours:.1f} hours"))
        
        if 'median_resolution_time_hours' in metrics:
            median_hours = metrics['median_resolution_time_hours']
            resolution_data.append(("Median Resolution Time", f"{median_hours:.1f} hours"))
        
        if 'total_resolved' in metrics:
            total = metrics['total_resolved']
            resolution_data.append(("Total Resolved Tickets", str(total)))
        
        # Format as table if we have data
        if resolution_data:
            for label, value in resolution_data:
                line = f"  {self._colors.METRIC_LABEL}{label}:{self._colors.RESET} {self._colors.METRIC_VALUE}{value}{self._colors.RESET}"
                lines.append(line)
        
        return "\n".join(lines)
    
    def _format_status_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format status distribution metrics."""
        lines = []
        lines.append(f"{self._colors.HEADER}Status Distribution{self._colors.RESET}")
        
        # Get status data
        status_counts = metrics.get('status_counts', {})
        status_percentages = metrics.get('status_percentages', {})
        
        if status_counts:
            # Create table data
            table_data = []
            for status, count in status_counts.items():
                percentage = status_percentages.get(status, 0)
                table_data.append({
                    'Status': status,
                    'Count': str(count),
                    'Percentage': f"{percentage:.1f}%"
                })
            
            # Format as table
            table_str = self._table_formatter.format_table(
                table_data, 
                ['Status', 'Count', 'Percentage'],
                max_width=60
            )
            lines.append(table_str)
        
        return "\n".join(lines)
    
    def _format_volume_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format volume trend metrics."""
        lines = []
        lines.append(f"{self._colors.HEADER}Volume Trends{self._colors.RESET}")
        
        # Add volume-related metrics
        volume_data = []
        
        for key, value in metrics.items():
            if 'volume' in key.lower() or 'count' in key.lower():
                if isinstance(value, (int, float)):
                    volume_data.append((key.replace('_', ' ').title(), str(value)))
        
        for label, value in volume_data:
            line = f"  {self._colors.METRIC_LABEL}{label}:{self._colors.RESET} {self._colors.METRIC_VALUE}{value}{self._colors.RESET}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_team_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format team performance metrics."""
        lines = []
        lines.append(f"{self._colors.HEADER}Team Performance{self._colors.RESET}")
        
        # Get team/assignee data
        assignee_workload = metrics.get('assignee_workload', {})
        team_performance = metrics.get('team_performance', {})
        
        if assignee_workload:
            # Create table for top assignees
            table_data = []
            sorted_assignees = sorted(assignee_workload.items(), key=lambda x: x[1], reverse=True)
            
            for assignee, count in sorted_assignees[:10]:  # Top 10
                table_data.append({
                    'Assignee': assignee,
                    'Tickets': str(count)
                })
            
            if table_data:
                table_str = self._table_formatter.format_table(
                    table_data,
                    ['Assignee', 'Tickets'],
                    title="Top Assignees by Ticket Count",
                    max_width=60
                )
                lines.append(table_str)
        
        return "\n".join(lines)
    
    def _generate_trends_section(self, trends: Dict[str, Any]) -> str:
        """Generate trends analysis section."""
        section_lines = []
        
        # Section title
        section_lines.append(f"{self._colors.SUBHEADER}TRENDS ANALYSIS{self._colors.RESET}")
        section_lines.append("-" * 20)
        
        # Format trend data
        for trend_name, trend_data in trends.items():
            if isinstance(trend_data, dict):
                section_lines.append(f"{self._colors.HEADER}{trend_name.replace('_', ' ').title()}{self._colors.RESET}")
                
                for key, value in trend_data.items():
                    if isinstance(value, (int, float)):
                        line = f"  {self._colors.METRIC_LABEL}{key}:{self._colors.RESET} {self._colors.METRIC_VALUE}{value}{self._colors.RESET}"
                        section_lines.append(line)
        
        return "\n".join(section_lines)
    
    def _generate_insights_section(self, summary: Dict[str, Any]) -> str:
        """Generate key insights section."""
        section_lines = []
        
        # Section title
        section_lines.append(f"{self._colors.SUBHEADER}KEY INSIGHTS{self._colors.RESET}")
        section_lines.append("-" * 20)
        
        # Extract insights
        insights = summary.get('key_insights', [])
        recommendations = summary.get('recommendations', [])
        
        if insights:
            section_lines.append(f"{self._colors.HEADER}Insights:{self._colors.RESET}")
            for insight in insights:
                section_lines.append(f"  • {insight}")
        
        if recommendations:
            section_lines.append(f"\n{self._colors.HEADER}Recommendations:{self._colors.RESET}")
            for recommendation in recommendations:
                section_lines.append(f"  • {recommendation}")
        
        return "\n".join(section_lines)
    
    def _generate_footer(self, analysis: AnalysisResult) -> str:
        """Generate report footer."""
        footer_lines = []
        
        footer_lines.append("-" * 50)
        footer_lines.append(f"{self._colors.INFO}Report generated by Ticket Analysis CLI{self._colors.RESET}")
        footer_lines.append(f"{self._colors.INFO}Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{self._colors.RESET}")
        
        return "\n".join(footer_lines)