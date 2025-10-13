"""Data formatters for various output types and presentations.

This module provides comprehensive formatting capabilities for ticket analysis data,
including table formatting, responsive layouts, color schemes, and data presentation
utilities for different contexts and output formats.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum

try:
    import colorama
    from colorama import Fore, Back, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color constants
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

from ..interfaces import FormatterInterface
from ..models.exceptions import ReportGenerationError


class ColorType(Enum):
    """Enumeration of color types for consistent theming."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HEADER = "header"
    SUBHEADER = "subheader"
    METRIC_VALUE = "metric_value"
    METRIC_LABEL = "metric_label"
    SEV_1 = "sev_1"
    SEV_2 = "sev_2"
    SEV_3 = "sev_3"
    SEV_4 = "sev_4"
    SEV_5 = "sev_5"
    STATUS_OPEN = "status_open"
    STATUS_IN_PROGRESS = "status_in_progress"
    STATUS_RESOLVED = "status_resolved"
    STATUS_CLOSED = "status_closed"


class ColorScheme:
    """Comprehensive color scheme for different data types and contexts."""
    
    def __init__(self, use_colors: bool = True) -> None:
        """Initialize color scheme.
        
        Args:
            use_colors: Whether to use colors (default: True).
        """
        self._use_colors = use_colors and COLORAMA_AVAILABLE
        self._init_colors()
    
    def _init_colors(self) -> None:
        """Initialize color mappings."""
        if self._use_colors:
            self._colors = {
                ColorType.SUCCESS: Fore.GREEN + Style.BRIGHT,
                ColorType.ERROR: Fore.RED + Style.BRIGHT,
                ColorType.WARNING: Fore.YELLOW + Style.BRIGHT,
                ColorType.INFO: Fore.BLUE + Style.BRIGHT,
                ColorType.HEADER: Fore.CYAN + Style.BRIGHT,
                ColorType.SUBHEADER: Fore.MAGENTA + Style.BRIGHT,
                ColorType.METRIC_VALUE: Fore.WHITE + Style.BRIGHT,
                ColorType.METRIC_LABEL: Fore.CYAN,
                ColorType.SEV_1: Fore.RED + Back.WHITE + Style.BRIGHT,
                ColorType.SEV_2: Fore.RED + Style.BRIGHT,
                ColorType.SEV_3: Fore.YELLOW + Style.BRIGHT,
                ColorType.SEV_4: Fore.BLUE,
                ColorType.SEV_5: Fore.WHITE,
                ColorType.STATUS_OPEN: Fore.RED,
                ColorType.STATUS_IN_PROGRESS: Fore.YELLOW,
                ColorType.STATUS_RESOLVED: Fore.GREEN,
                ColorType.STATUS_CLOSED: Fore.BLUE,
            }
            self._reset = Style.RESET_ALL
        else:
            # No colors - all empty strings
            self._colors = {color_type: "" for color_type in ColorType}
            self._reset = ""
    
    def get_color(self, color_type: ColorType) -> str:
        """Get color code for specified type.
        
        Args:
            color_type: Type of color to retrieve.
            
        Returns:
            Color code string (empty if colors disabled).
        """
        return self._colors.get(color_type, "")
    
    def get_reset(self) -> str:
        """Get reset color code.
        
        Returns:
            Reset color code string.
        """
        return self._reset
    
    def colorize(self, text: str, color_type: ColorType) -> str:
        """Apply color to text.
        
        Args:
            text: Text to colorize.
            color_type: Type of color to apply.
            
        Returns:
            Colorized text string.
        """
        color = self.get_color(color_type)
        reset = self.get_reset()
        return f"{color}{text}{reset}"


class TableAlignment(Enum):
    """Table column alignment options."""
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class TableColumn:
    """Configuration for a table column."""
    
    def __init__(self, 
                 header: str,
                 key: str,
                 width: Optional[int] = None,
                 alignment: TableAlignment = TableAlignment.LEFT,
                 color_type: Optional[ColorType] = None,
                 formatter: Optional[callable] = None) -> None:
        """Initialize table column configuration.
        
        Args:
            header: Column header text.
            key: Data key for this column.
            width: Fixed column width (None for auto-sizing).
            alignment: Column alignment.
            color_type: Color type for column values.
            formatter: Optional value formatter function.
        """
        self.header = header
        self.key = key
        self.width = width
        self.alignment = alignment
        self.color_type = color_type
        self.formatter = formatter


class TableFormatter(FormatterInterface):
    """Advanced table formatter with responsive layouts and color coding.
    
    This class provides comprehensive table formatting capabilities including:
    - Responsive column width management
    - Color coding based on data types and values
    - Multiple alignment options
    - Custom formatters for specific data types
    - Automatic truncation and wrapping
    """
    
    def __init__(self, 
                 color_scheme: Optional[ColorScheme] = None,
                 max_width: int = 120,
                 min_col_width: int = 8,
                 padding: int = 1) -> None:
        """Initialize table formatter.
        
        Args:
            color_scheme: Color scheme to use (creates default if None).
            max_width: Maximum table width in characters.
            min_col_width: Minimum column width.
            padding: Cell padding (spaces on each side).
        """
        self._color_scheme = color_scheme or ColorScheme()
        self._max_width = max_width
        self._min_col_width = min_col_width
        self._padding = padding
    
    def format_data(self, data: Dict[str, Any]) -> str:
        """Format dictionary data as key-value pairs.
        
        Args:
            data: Data dictionary to format.
            
        Returns:
            Formatted string representation.
        """
        if not data:
            return self._color_scheme.colorize("No data available", ColorType.WARNING)
        
        lines = []
        max_key_length = max(len(str(key)) for key in data.keys())
        
        for key, value in data.items():
            key_str = f"{key}:".ljust(max_key_length + 1)
            key_colored = self._color_scheme.colorize(key_str, ColorType.METRIC_LABEL)
            value_colored = self._color_scheme.colorize(str(value), ColorType.METRIC_VALUE)
            lines.append(f"{key_colored} {value_colored}")
        
        return "\n".join(lines)
    
    def format_table(self, 
                    data: List[Dict[str, Any]], 
                    headers: List[str],
                    title: Optional[str] = None,
                    columns: Optional[List[TableColumn]] = None) -> str:
        """Format data as a comprehensive table with advanced features.
        
        Args:
            data: List of row data dictionaries.
            headers: List of column headers.
            title: Optional table title.
            columns: Optional column configurations.
            
        Returns:
            Formatted table string.
        """
        if not data:
            return self._color_scheme.colorize("No data to display", ColorType.WARNING)
        
        # Create column configurations if not provided
        if columns is None:
            columns = [TableColumn(header, header) for header in headers]
        
        # Calculate column widths
        col_widths = self._calculate_column_widths(data, columns)
        
        # Build table components
        lines = []
        
        # Add title if provided
        if title:
            title_colored = self._color_scheme.colorize(title, ColorType.HEADER)
            lines.append(title_colored)
            lines.append("=" * len(title))
            lines.append("")
        
        # Add header
        header_line = self._format_header_row(columns, col_widths)
        lines.append(header_line)
        
        # Add separator
        separator = self._create_separator(col_widths)
        lines.append(separator)
        
        # Add data rows
        for row_data in data:
            row_line = self._format_data_row(row_data, columns, col_widths)
            lines.append(row_line)
        
        # Add bottom separator
        lines.append(separator)
        
        return "\n".join(lines)
    
    def format_key_value_pairs(self, data: Dict[str, Any]) -> str:
        """Format key-value pairs with proper alignment and colors.
        
        Args:
            data: Dictionary of key-value pairs.
            
        Returns:
            Formatted key-value string.
        """
        return self.format_data(data)
    
    def apply_color_coding(self, text: str, color_type: str) -> str:
        """Apply color coding to text based on type.
        
        Args:
            text: Text to colorize.
            color_type: Type of color to apply.
            
        Returns:
            Colorized text string.
        """
        try:
            color_enum = ColorType(color_type)
            return self._color_scheme.colorize(text, color_enum)
        except ValueError:
            # Unknown color type, return text as-is
            return text
    
    def format_metrics_summary(self, 
                              metrics: Dict[str, Any],
                              title: str = "Metrics Summary") -> str:
        """Format metrics data with specialized formatting.
        
        Args:
            metrics: Metrics dictionary to format.
            title: Title for the metrics section.
            
        Returns:
            Formatted metrics string.
        """
        lines = []
        
        # Title
        title_colored = self._color_scheme.colorize(title, ColorType.HEADER)
        lines.append(title_colored)
        lines.append("-" * len(title))
        lines.append("")
        
        # Group metrics by category
        categorized_metrics = self._categorize_metrics(metrics)
        
        for category, category_metrics in categorized_metrics.items():
            if category_metrics:
                # Category header
                category_header = self._color_scheme.colorize(
                    category.replace('_', ' ').title(), 
                    ColorType.SUBHEADER
                )
                lines.append(category_header)
                
                # Format metrics in this category
                for key, value in category_metrics.items():
                    formatted_value = self._format_metric_value(key, value)
                    key_colored = self._color_scheme.colorize(f"  {key}:", ColorType.METRIC_LABEL)
                    lines.append(f"{key_colored} {formatted_value}")
                
                lines.append("")  # Empty line between categories
        
        return "\n".join(lines)
    
    def format_trend_data(self, 
                         trends: Dict[str, Any],
                         title: str = "Trend Analysis") -> str:
        """Format trend data with time-series presentation.
        
        Args:
            trends: Trends dictionary to format.
            title: Title for the trends section.
            
        Returns:
            Formatted trends string.
        """
        lines = []
        
        # Title
        title_colored = self._color_scheme.colorize(title, ColorType.HEADER)
        lines.append(title_colored)
        lines.append("-" * len(title))
        lines.append("")
        
        for trend_name, trend_data in trends.items():
            # Trend name
            trend_header = self._color_scheme.colorize(
                trend_name.replace('_', ' ').title(),
                ColorType.SUBHEADER
            )
            lines.append(trend_header)
            
            if isinstance(trend_data, dict):
                # Format as key-value pairs
                for key, value in trend_data.items():
                    formatted_value = self._format_trend_value(key, value)
                    key_colored = self._color_scheme.colorize(f"  {key}:", ColorType.METRIC_LABEL)
                    lines.append(f"{key_colored} {formatted_value}")
            elif isinstance(trend_data, list):
                # Format as list items
                for item in trend_data:
                    item_colored = self._color_scheme.colorize(f"  • {item}", ColorType.INFO)
                    lines.append(item_colored)
            else:
                # Format as single value
                value_colored = self._color_scheme.colorize(f"  {trend_data}", ColorType.METRIC_VALUE)
                lines.append(value_colored)
            
            lines.append("")  # Empty line between trends
        
        return "\n".join(lines)
    
    def _calculate_column_widths(self, 
                               data: List[Dict[str, Any]], 
                               columns: List[TableColumn]) -> Dict[str, int]:
        """Calculate optimal column widths with responsive behavior."""
        col_widths = {}
        
        # Start with header widths or fixed widths
        for column in columns:
            if column.width:
                col_widths[column.key] = column.width
            else:
                col_widths[column.key] = max(len(column.header), self._min_col_width)
        
        # Check data widths for auto-sized columns
        for column in columns:
            if not column.width:  # Only for auto-sized columns
                max_data_width = 0
                for row in data:
                    value = row.get(column.key, "")
                    formatted_value = self._format_cell_value(value, column)
                    # Remove color codes for width calculation
                    clean_value = self._strip_color_codes(str(formatted_value))
                    max_data_width = max(max_data_width, len(clean_value))
                
                col_widths[column.key] = max(col_widths[column.key], max_data_width)
        
        # Apply responsive sizing if total width exceeds maximum
        total_width = sum(col_widths.values()) + len(columns) * (2 * self._padding + 1) + 1
        
        if total_width > self._max_width:
            # Calculate available width for columns
            available_width = self._max_width - len(columns) * (2 * self._padding + 1) - 1
            
            # Proportionally reduce auto-sized columns
            auto_sized_columns = [col for col in columns if not col.width]
            if auto_sized_columns:
                auto_width_total = sum(col_widths[col.key] for col in auto_sized_columns)
                fixed_width_total = sum(col_widths[col.key] for col in columns if col.width)
                
                available_for_auto = available_width - fixed_width_total
                
                if available_for_auto > 0 and auto_width_total > 0:
                    reduction_factor = available_for_auto / auto_width_total
                    
                    for column in auto_sized_columns:
                        new_width = max(self._min_col_width, 
                                      int(col_widths[column.key] * reduction_factor))
                        col_widths[column.key] = new_width
        
        return col_widths
    
    def _format_header_row(self, 
                          columns: List[TableColumn], 
                          col_widths: Dict[str, int]) -> str:
        """Format table header row with colors and alignment."""
        cells = []
        
        for column in columns:
            width = col_widths[column.key]
            header_text = self._align_text(column.header, width, column.alignment)
            header_colored = self._color_scheme.colorize(header_text, ColorType.HEADER)
            cells.append(self._pad_cell(header_colored, width))
        
        return "|" + "|".join(cells) + "|"
    
    def _format_data_row(self, 
                        row_data: Dict[str, Any], 
                        columns: List[TableColumn], 
                        col_widths: Dict[str, int]) -> str:
        """Format table data row with colors and formatting."""
        cells = []
        
        for column in columns:
            width = col_widths[column.key]
            value = row_data.get(column.key, "")
            
            # Format the cell value
            formatted_value = self._format_cell_value(value, column)
            
            # Apply alignment
            aligned_value = self._align_text(str(formatted_value), width, column.alignment)
            
            # Apply column-specific coloring
            if column.color_type:
                colored_value = self._color_scheme.colorize(aligned_value, column.color_type)
            else:
                # Apply contextual coloring based on content
                colored_value = self._apply_contextual_coloring(aligned_value, column.key, row_data)
            
            cells.append(self._pad_cell(colored_value, width))
        
        return "|" + "|".join(cells) + "|"
    
    def _format_cell_value(self, value: Any, column: TableColumn) -> str:
        """Format individual cell value using column formatter if available."""
        if column.formatter:
            try:
                return column.formatter(value)
            except Exception:
                # Fallback to string conversion if formatter fails
                pass
        
        # Default formatting based on value type
        if isinstance(value, float):
            return f"{value:.2f}"
        elif isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        elif isinstance(value, timedelta):
            return self._format_timedelta(value)
        else:
            return str(value)
    
    def _format_timedelta(self, td: timedelta) -> str:
        """Format timedelta in human-readable format."""
        total_seconds = int(td.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    def _apply_contextual_coloring(self, 
                                  value: str, 
                                  column_key: str, 
                                  row_data: Dict[str, Any]) -> str:
        """Apply contextual coloring based on column type and value."""
        column_lower = column_key.lower()
        value_lower = value.lower().strip()
        
        # Status coloring
        if "status" in column_lower:
            if value_lower in ["open", "new"]:
                return self._color_scheme.colorize(value, ColorType.STATUS_OPEN)
            elif value_lower in ["in progress", "assigned", "researching", "work in progress"]:
                return self._color_scheme.colorize(value, ColorType.STATUS_IN_PROGRESS)
            elif value_lower in ["resolved", "fixed", "completed"]:
                return self._color_scheme.colorize(value, ColorType.STATUS_RESOLVED)
            elif value_lower in ["closed", "done"]:
                return self._color_scheme.colorize(value, ColorType.STATUS_CLOSED)
        
        # Severity coloring
        elif "severity" in column_lower or "priority" in column_lower:
            if value_lower in ["sev_1", "critical", "1"]:
                return self._color_scheme.colorize(value, ColorType.SEV_1)
            elif value_lower in ["sev_2", "high", "2"]:
                return self._color_scheme.colorize(value, ColorType.SEV_2)
            elif value_lower in ["sev_3", "medium", "3"]:
                return self._color_scheme.colorize(value, ColorType.SEV_3)
            elif value_lower in ["sev_4", "low", "4"]:
                return self._color_scheme.colorize(value, ColorType.SEV_4)
            elif value_lower in ["sev_5", "lowest", "5"]:
                return self._color_scheme.colorize(value, ColorType.SEV_5)
        
        # Numeric values
        elif column_lower in ["count", "total", "average", "median", "percentage"]:
            return self._color_scheme.colorize(value, ColorType.METRIC_VALUE)
        
        return value
    
    def _align_text(self, text: str, width: int, alignment: TableAlignment) -> str:
        """Align text within specified width."""
        # Strip color codes for length calculation
        clean_text = self._strip_color_codes(text)
        
        if len(clean_text) > width:
            # Truncate if too long
            if width > 3:
                truncated = clean_text[:width-3] + "..."
            else:
                truncated = clean_text[:width]
            return truncated
        
        if alignment == TableAlignment.LEFT:
            return text + " " * (width - len(clean_text))
        elif alignment == TableAlignment.RIGHT:
            return " " * (width - len(clean_text)) + text
        elif alignment == TableAlignment.CENTER:
            padding = width - len(clean_text)
            left_pad = padding // 2
            right_pad = padding - left_pad
            return " " * left_pad + text + " " * right_pad
        
        return text
    
    def _pad_cell(self, content: str, width: int) -> str:
        """Add padding to cell content."""
        padding_str = " " * self._padding
        return f"{padding_str}{content}{padding_str}"
    
    def _create_separator(self, col_widths: Dict[str, int]) -> str:
        """Create table separator line."""
        separators = []
        for width in col_widths.values():
            total_width = width + 2 * self._padding
            separators.append("-" * total_width)
        
        return "+" + "+".join(separators) + "+"
    
    def _strip_color_codes(self, text: str) -> str:
        """Remove ANSI color codes from text for length calculation."""
        import re
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _categorize_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Categorize metrics by type for better organization."""
        categories = {
            'resolution_metrics': {},
            'status_metrics': {},
            'volume_metrics': {},
            'team_metrics': {},
            'other_metrics': {}
        }
        
        for key, value in metrics.items():
            key_lower = key.lower()
            
            if any(term in key_lower for term in ['resolution', 'resolve', 'time']):
                categories['resolution_metrics'][key] = value
            elif any(term in key_lower for term in ['status', 'state']):
                categories['status_metrics'][key] = value
            elif any(term in key_lower for term in ['volume', 'count', 'total']):
                categories['volume_metrics'][key] = value
            elif any(term in key_lower for term in ['team', 'assignee', 'user']):
                categories['team_metrics'][key] = value
            else:
                categories['other_metrics'][key] = value
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _format_metric_value(self, key: str, value: Any) -> str:
        """Format metric value with appropriate styling."""
        if isinstance(value, float):
            if 'percentage' in key.lower() or 'percent' in key.lower():
                formatted = f"{value:.1f}%"
            elif 'time' in key.lower() and 'hours' in key.lower():
                formatted = f"{value:.1f} hours"
            else:
                formatted = f"{value:.2f}"
        elif isinstance(value, int):
            formatted = f"{value:,}"  # Add thousands separators
        else:
            formatted = str(value)
        
        return self._color_scheme.colorize(formatted, ColorType.METRIC_VALUE)
    
    def _format_trend_value(self, key: str, value: Any) -> str:
        """Format trend value with appropriate styling."""
        if isinstance(value, (int, float)):
            # Determine if this is a positive or negative trend
            if value > 0:
                color_type = ColorType.SUCCESS if 'improvement' in key.lower() else ColorType.WARNING
                formatted = f"+{value}"
            elif value < 0:
                color_type = ColorType.ERROR if 'improvement' in key.lower() else ColorType.SUCCESS
                formatted = str(value)
            else:
                color_type = ColorType.INFO
                formatted = str(value)
            
            return self._color_scheme.colorize(formatted, color_type)
        else:
            return self._color_scheme.colorize(str(value), ColorType.METRIC_VALUE)


class ResponsiveFormatter:
    """Responsive formatter that adapts to different terminal sizes."""
    
    def __init__(self, color_scheme: Optional[ColorScheme] = None) -> None:
        """Initialize responsive formatter.
        
        Args:
            color_scheme: Color scheme to use.
        """
        self._color_scheme = color_scheme or ColorScheme()
        self._table_formatter = TableFormatter(self._color_scheme)
    
    def format_for_width(self, 
                        data: List[Dict[str, Any]], 
                        headers: List[str],
                        terminal_width: int) -> str:
        """Format data responsively based on terminal width.
        
        Args:
            data: Data to format.
            headers: Column headers.
            terminal_width: Available terminal width.
            
        Returns:
            Formatted output optimized for terminal width.
        """
        if terminal_width < 60:
            # Very narrow - use vertical layout
            return self._format_vertical_layout(data, headers)
        elif terminal_width < 100:
            # Medium width - use compact table
            return self._format_compact_table(data, headers, terminal_width)
        else:
            # Full width - use standard table
            self._table_formatter._max_width = terminal_width
            return self._table_formatter.format_table(data, headers)
    
    def _format_vertical_layout(self, 
                              data: List[Dict[str, Any]], 
                              headers: List[str]) -> str:
        """Format data in vertical layout for narrow terminals."""
        lines = []
        
        for i, row in enumerate(data):
            if i > 0:
                lines.append("")  # Separator between records
            
            record_header = self._color_scheme.colorize(f"Record {i + 1}:", ColorType.HEADER)
            lines.append(record_header)
            lines.append("-" * 20)
            
            for header in headers:
                value = row.get(header, "")
                key_colored = self._color_scheme.colorize(f"{header}:", ColorType.METRIC_LABEL)
                value_colored = self._color_scheme.colorize(str(value), ColorType.METRIC_VALUE)
                lines.append(f"  {key_colored} {value_colored}")
        
        return "\n".join(lines)
    
    def _format_compact_table(self, 
                            data: List[Dict[str, Any]], 
                            headers: List[str],
                            width: int) -> str:
        """Format data as compact table for medium-width terminals."""
        # Select most important columns that fit
        important_headers = self._select_important_headers(headers, width)
        
        # Use table formatter with reduced width
        self._table_formatter._max_width = width
        return self._table_formatter.format_table(data, important_headers)
    
    def _select_important_headers(self, headers: List[str], width: int) -> List[str]:
        """Select most important headers that fit in available width."""
        # Priority order for common headers
        priority_order = [
            'id', 'title', 'status', 'severity', 'priority',
            'assignee', 'created_date', 'updated_date', 'resolved_date'
        ]
        
        selected = []
        estimated_width = 0
        
        # First, add high-priority headers
        for priority_header in priority_order:
            for header in headers:
                if header.lower() == priority_header and header not in selected:
                    # Estimate column width (header + some data)
                    col_width = max(len(header), 15) + 3  # padding
                    if estimated_width + col_width < width:
                        selected.append(header)
                        estimated_width += col_width
                    break
        
        # Then add remaining headers if space allows
        for header in headers:
            if header not in selected:
                col_width = max(len(header), 10) + 3
                if estimated_width + col_width < width:
                    selected.append(header)
                    estimated_width += col_width
        
        return selected or headers[:3]  # Fallback to first 3 headers