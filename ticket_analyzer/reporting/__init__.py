"""Reporting module for ticket analysis CLI.

This module provides comprehensive reporting capabilities including:
- CLI reporting with color coding and tabular formatting
- HTML reporting with Jinja2 templates and embedded charts
- Chart generation with matplotlib and seaborn
- Theme management and customization
- Advanced table formatters with responsive layouts
- Progress indicators and user feedback management
- Multiple output formats and presentation styles
"""

from .cli_reporter import CLIReporter, CLIColorScheme, CLITableFormatter
from .html_reporter import HTMLReporter
from .charts import ChartGenerator
from .themes import (
    ThemeManager, 
    Theme, 
    ColorPalette, 
    LayoutConfig, 
    BrandingConfig,
    ThemeType,
    ColorScheme as ThemeColorScheme,
    ReportCustomizer
)
from .formatters import (
    TableFormatter, 
    ColorScheme, 
    ColorType, 
    TableAlignment, 
    TableColumn,
    ResponsiveFormatter
)
from .progress import (
    ProgressManager, 
    StatusType, 
    SpinnerType, 
    OperationTimer,
    BatchProgressManager
)

__all__ = [
    # CLI Reporter
    'CLIReporter',
    'CLIColorScheme', 
    'CLITableFormatter',
    
    # HTML Reporter
    'HTMLReporter',
    
    # Charts
    'ChartGenerator',
    
    # Themes
    'ThemeManager',
    'Theme',
    'ColorPalette',
    'LayoutConfig',
    'BrandingConfig',
    'ThemeType',
    'ThemeColorScheme',
    'ReportCustomizer',
    
    # Formatters
    'TableFormatter',
    'ColorScheme',
    'ColorType',
    'TableAlignment',
    'TableColumn',
    'ResponsiveFormatter',
    
    # Progress Management
    'ProgressManager',
    'StatusType',
    'SpinnerType',
    'OperationTimer',
    'BatchProgressManager',
]