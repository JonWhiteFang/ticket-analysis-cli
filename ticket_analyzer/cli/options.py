"""Reusable CLI options and custom parameter types.

This module provides reusable Click options, custom parameter types,
and validation functions for consistent CLI behavior across commands.
"""

from __future__ import annotations
import re
import os
from datetime import datetime, timedelta
from typing import Optional, List, Any, Union
from pathlib import Path

import click


# Custom Parameter Types
class TicketIDType(click.ParamType):
    """Custom parameter type for ticket ID validation."""
    
    name = "ticket_id"
    
    # Ticket ID patterns for different systems
    PATTERNS = [
        r'^[A-Z]{1,5}-?\d{1,10}$',  # Standard format: ABC-123456
        r'^T\d{6,10}$',             # T-format: T123456
        r'^P\d{6,10}$',             # P-format: P123456
        r'^V\d{10}$',               # V-format: V1234567890
    ]
    
    def convert(self, value: str, param: Optional[click.Parameter], 
                ctx: Optional[click.Context]) -> str:
        """Convert and validate ticket ID."""
        if not value:
            self.fail("Ticket ID cannot be empty", param, ctx)
        
        # Check against known patterns
        for pattern in self.PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                return value.upper()  # Normalize to uppercase
        
        self.fail(f"Invalid ticket ID format: {value}", param, ctx)


class DateRangeType(click.ParamType):
    """Custom parameter type for date range validation."""
    
    name = "date_range"
    
    def convert(self, value: str, param: Optional[click.Parameter], 
                ctx: Optional[click.Context]) -> tuple[datetime, datetime]:
        """Convert date range string to datetime tuple."""
        if not value:
            self.fail("Date range cannot be empty", param, ctx)
        
        # Handle predefined ranges
        predefined_ranges = {
            "today": self._get_today_range(),
            "yesterday": self._get_yesterday_range(),
            "week": self._get_week_range(),
            "month": self._get_month_range(),
            "quarter": self._get_quarter_range(),
        }
        
        if value.lower() in predefined_ranges:
            return predefined_ranges[value.lower()]
        
        # Handle custom range format: "YYYY-MM-DD:YYYY-MM-DD"
        if ":" in value:
            try:
                start_str, end_str = value.split(":", 1)
                start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
                end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
                
                if start_date >= end_date:
                    self.fail("Start date must be before end date", param, ctx)
                
                return start_date, end_date
            except ValueError as e:
                self.fail(f"Invalid date format: {e}", param, ctx)
        
        self.fail(f"Invalid date range format: {value}", param, ctx)
    
    def _get_today_range(self) -> tuple[datetime, datetime]:
        """Get today's date range."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    
    def _get_yesterday_range(self) -> tuple[datetime, datetime]:
        """Get yesterday's date range."""
        yesterday = datetime.now() - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end
    
    def _get_week_range(self) -> tuple[datetime, datetime]:
        """Get last week's date range."""
        now = datetime.now()
        start = now - timedelta(days=7)
        return start, now
    
    def _get_month_range(self) -> tuple[datetime, datetime]:
        """Get last month's date range."""
        now = datetime.now()
        start = now - timedelta(days=30)
        return start, now
    
    def _get_quarter_range(self) -> tuple[datetime, datetime]:
        """Get last quarter's date range."""
        now = datetime.now()
        start = now - timedelta(days=90)
        return start, now


class ConfigFileType(click.Path):
    """Custom parameter type for configuration file validation."""
    
    def __init__(self) -> None:
        super().__init__(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            path_type=Path
        )
    
    def convert(self, value: Any, param: Optional[click.Parameter], 
                ctx: Optional[click.Context]) -> Path:
        """Convert and validate configuration file path."""
        path = super().convert(value, param, ctx)
        
        if isinstance(path, str):
            path = Path(path)
        
        # Check file extension
        valid_extensions = {".json", ".ini", ".yaml", ".yml", ".toml"}
        if path.suffix.lower() not in valid_extensions:
            self.fail(
                f"Configuration file must have one of these extensions: "
                f"{', '.join(valid_extensions)}",
                param, ctx
            )
        
        # Check if file exists and is readable
        if path.exists():
            if not path.is_file():
                self.fail(f"Path is not a file: {path}", param, ctx)
            
            if not os.access(path, os.R_OK):
                self.fail(f"File is not readable: {path}", param, ctx)
        
        return path


class OutputFormatType(click.Choice):
    """Custom parameter type for output format validation."""
    
    def __init__(self) -> None:
        super().__init__(
            choices=["table", "json", "csv", "html", "yaml"],
            case_sensitive=False
        )
    
    def convert(self, value: Any, param: Optional[click.Parameter], 
                ctx: Optional[click.Context]) -> str:
        """Convert and validate output format."""
        format_value = super().convert(value, param, ctx)
        
        # Validate format compatibility with output options
        if hasattr(ctx, 'params') and ctx.params:
            output_file = ctx.params.get('output')
            if output_file and isinstance(output_file, Path):
                file_ext = output_file.suffix.lower()
                format_ext_map = {
                    "json": ".json",
                    "csv": ".csv", 
                    "html": ".html",
                    "yaml": ".yaml"
                }
                
                expected_ext = format_ext_map.get(format_value)
                if expected_ext and file_ext != expected_ext:
                    click.echo(
                        f"Warning: Output format '{format_value}' doesn't match "
                        f"file extension '{file_ext}'",
                        err=True
                    )
        
        return format_value


# Environment Variable Support
class EnvVarOption(click.Option):
    """Click option that supports environment variables."""
    
    def __init__(self, *args, envvar: Optional[str] = None, 
                 envvar_prefix: str = "TICKET_ANALYZER_", **kwargs) -> None:
        if envvar and not envvar.startswith(envvar_prefix):
            envvar = f"{envvar_prefix}{envvar}"
        
        super().__init__(*args, envvar=envvar, **kwargs)
    
    def get_help_record(self, ctx: click.Context) -> Optional[tuple[str, str]]:
        """Add environment variable info to help text."""
        help_record = super().get_help_record(ctx)
        if help_record and self.envvar:
            opts, help_text = help_record
            help_text += f" [env var: {self.envvar}]"
            return opts, help_text
        return help_record


# Reusable Option Definitions
def ticket_ids_option(**kwargs):
    """Reusable option for ticket IDs."""
    return click.option(
        "--ticket-ids",
        multiple=True,
        type=TicketIDType(),
        help="Specific ticket IDs to analyze (can be used multiple times)",
        **kwargs
    )


def date_range_option(**kwargs):
    """Reusable option for date ranges."""
    return click.option(
        "--date-range",
        type=DateRangeType(),
        help="Date range (today, yesterday, week, month, quarter, or YYYY-MM-DD:YYYY-MM-DD)",
        **kwargs
    )


def config_file_option(**kwargs):
    """Reusable option for configuration files."""
    return click.option(
        "--config-file", "-c",
        type=ConfigFileType(),
        cls=EnvVarOption,
        envvar="CONFIG_FILE",
        help="Configuration file path (JSON, INI, YAML, or TOML)",
        **kwargs
    )


def output_format_option(**kwargs):
    """Reusable option for output format."""
    return click.option(
        "--format", "-f",
        type=OutputFormatType(),
        default="table",
        cls=EnvVarOption,
        envvar="OUTPUT_FORMAT",
        help="Output format (default: table)",
        **kwargs
    )


def output_file_option(**kwargs):
    """Reusable option for output file."""
    return click.option(
        "--output", "-o",
        type=click.Path(path_type=Path),
        cls=EnvVarOption,
        envvar="OUTPUT_FILE",
        help="Output file path (stdout if not specified)",
        **kwargs
    )


def verbose_option(**kwargs):
    """Reusable option for verbose output."""
    return click.option(
        "--verbose", "-v",
        is_flag=True,
        cls=EnvVarOption,
        envvar="VERBOSE",
        help="Enable verbose output with detailed logging",
        **kwargs
    )


def max_results_option(default: int = 1000, **kwargs):
    """Reusable option for maximum results."""
    return click.option(
        "--max-results",
        type=click.IntRange(min=1, max=10000),
        default=default,
        cls=EnvVarOption,
        envvar="MAX_RESULTS",
        help=f"Maximum number of results (default: {default}, max: 10000)",
        **kwargs
    )


def timeout_option(default: int = 60, **kwargs):
    """Reusable option for timeout settings."""
    return click.option(
        "--timeout",
        type=click.IntRange(min=10, max=300),
        default=default,
        cls=EnvVarOption,
        envvar="TIMEOUT",
        help=f"Request timeout in seconds (default: {default})",
        **kwargs
    )


# Validation Functions
def validate_ticket_id_format(ticket_id: str) -> bool:
    """Validate ticket ID format."""
    ticket_type = TicketIDType()
    try:
        ticket_type.convert(ticket_id, None, None)
        return True
    except click.BadParameter:
        return False


def validate_date_range_consistency(start_date: Optional[datetime], 
                                  end_date: Optional[datetime],
                                  days_back: Optional[int],
                                  date_range: Optional[str]) -> None:
    """Validate date range parameter consistency."""
    date_params = [
        p for p in [start_date, end_date, days_back, date_range] 
        if p is not None
    ]
    
    if len(date_params) > 2:
        raise click.BadParameter(
            "Cannot specify more than two date range parameters simultaneously"
        )
    
    if start_date and end_date and start_date >= end_date:
        raise click.BadParameter("Start date must be before end date")


def validate_output_consistency(format: str, output: Optional[Path], 
                              include_charts: bool) -> None:
    """Validate output format and file consistency."""
    if include_charts and format not in ["html"]:
        raise click.BadParameter(
            "Charts can only be included in HTML format output"
        )
    
    if output:
        file_ext = output.suffix.lower()
        format_ext_map = {
            "json": ".json",
            "csv": ".csv",
            "html": ".html", 
            "yaml": ".yaml"
        }
        
        expected_ext = format_ext_map.get(format)
        if expected_ext and file_ext and file_ext != expected_ext:
            click.echo(
                f"Warning: Output format '{format}' may not match "
                f"file extension '{file_ext}'",
                err=True
            )


# Help Text Templates
HELP_EXAMPLES = {
    "analyze": """
Examples:
  # Analyze open tickets from last 7 days
  ticket-analyzer analyze --status Open --days-back 7
  
  # Analyze specific tickets with JSON output  
  ticket-analyzer analyze --ticket-ids T123456 T789012 --format json
  
  # Generate HTML report with charts
  ticket-analyzer analyze --format html --include-charts --output report.html
  
  # Team performance analysis
  ticket-analyzer analyze --team-performance --resolver-group "My Team"
""",
    
    "config": """
Examples:
  # Show current configuration
  ticket-analyzer config show
  
  # Set a configuration value
  ticket-analyzer config set output_format json
  
  # Initialize new configuration file
  ticket-analyzer config init --format json
""",
    
    "report": """
Examples:
  # List available reports
  ticket-analyzer report list
  
  # Convert report format
  ticket-analyzer report convert analysis.json --format html
  
  # Merge multiple reports
  ticket-analyzer report merge report1.json report2.json --output combined.json
"""
}


def add_help_examples(command_name: str):
    """Decorator to add help examples to commands."""
    def decorator(func):
        if command_name in HELP_EXAMPLES:
            if func.__doc__:
                func.__doc__ += HELP_EXAMPLES[command_name]
            else:
                func.__doc__ = HELP_EXAMPLES[command_name]
        return func
    return decorator


# Option Groups for Consistency
COMMON_OPTIONS = [
    verbose_option(),
    config_file_option(),
]

OUTPUT_OPTIONS = [
    output_format_option(),
    output_file_option(),
    max_results_option(),
]

TIME_PERIOD_OPTIONS = [
    click.option(
        "--start-date",
        type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
        help="Start date for analysis (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
    ),
    click.option(
        "--end-date", 
        type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
        help="End date for analysis (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
    ),
    click.option(
        "--days-back",
        type=click.IntRange(min=1, max=365),
        default=30,
        help="Number of days back from today (default: 30, max: 365)"
    ),
    date_range_option(),
]

AUTHENTICATION_OPTIONS = [
    click.option(
        "--auth-timeout",
        type=click.IntRange(min=30, max=300),
        default=60,
        cls=EnvVarOption,
        envvar="AUTH_TIMEOUT",
        help="Authentication timeout in seconds (default: 60)"
    ),
    click.option(
        "--force-auth",
        is_flag=True,
        cls=EnvVarOption,
        envvar="FORCE_AUTH",
        help="Force re-authentication even if already authenticated"
    ),
    click.option(
        "--skip-auth-check",
        is_flag=True,
        cls=EnvVarOption,
        envvar="SKIP_AUTH_CHECK",
        help="Skip initial authentication check (use with caution)"
    ),
]