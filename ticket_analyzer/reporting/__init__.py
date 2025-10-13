"""Reporting module for ticket analysis CLI.

This module provides comprehensive reporting capabilities including:
- CLI reporting with color coding and tabular formatting
- Advanced table formatters with responsive layouts
- Progress indicators and user feedback management
- Multiple output formats and presentation styles
"""

from .cli_reporter import CLIReporter, CLIColorScheme, CLITableFormatter
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