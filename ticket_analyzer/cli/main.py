"""Main CLI application with Click framework integration.

This module provides the main entry point for the ticket analyzer CLI application.
It implements argument groups for Time Period, Output Options, Configuration, and
Authentication with comprehensive validation and error handling.
"""

from __future__ import annotations
import sys
from typing import Optional, Dict, Any
import click
from pathlib import Path

from ..models.exceptions import (
    TicketAnalysisError,
    AuthenticationError,
    ConfigurationError,
    DataRetrievalError
)
from .utils import (
    success_message,
    error_message,
    info_message,
    warning_message,
    format_exception_message
)
from .signals import GracefulShutdown


# Global context for CLI state
class CLIContext:
    """Context object for CLI state management."""
    
    def __init__(self) -> None:
        self.verbose: bool = False
        self.config_file: Optional[str] = None
        self.output_dir: str = "./reports"
        self.shutdown_handler = GracefulShutdown()


@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0", prog_name="ticket-analyzer")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output with detailed logging"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file (JSON or INI format)"
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="./reports",
    help="Directory for output files (default: ./reports)"
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[Path], output_dir: Path) -> None:
    """Ticket Analysis CLI Tool.
    
    A secure, Python 3.7-compatible CLI tool for analyzing ticket data from
    Amazon's internal systems using MCP (Model Context Protocol) integration.
    
    Examples:
        ticket-analyzer analyze --status Open Resolved
        ticket-analyzer analyze --format json --output results.json
        ticket-analyzer config show
    """
    # Initialize CLI context
    ctx.ensure_object(CLIContext)
    ctx.obj.verbose = verbose
    ctx.obj.config_file = str(config) if config else None
    ctx.obj.output_dir = str(output_dir)
    
    # Set up logging level based on verbose flag
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        info_message("Verbose mode enabled")
    
    # If no command specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Time Period Options Group
time_period_options = [
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
    click.option(
        "--date-range",
        type=click.Choice(["today", "yesterday", "week", "month", "quarter"]),
        help="Predefined date range"
    )
]

# Output Options Group
output_options = [
    click.option(
        "--format", "-f",
        type=click.Choice(["table", "json", "csv", "html"]),
        default="table",
        help="Output format (default: table)"
    ),
    click.option(
        "--output", "-o",
        type=click.Path(path_type=Path),
        help="Output file path (stdout if not specified)"
    ),
    click.option(
        "--max-results",
        type=click.IntRange(min=1, max=10000),
        default=1000,
        help="Maximum number of results (default: 1000, max: 10000)"
    ),
    click.option(
        "--include-charts",
        is_flag=True,
        default=True,
        help="Include charts in HTML reports (default: enabled)"
    ),
    click.option(
        "--no-color",
        is_flag=True,
        help="Disable colored output"
    )
]

# Configuration Options Group
configuration_options = [
    click.option(
        "--config-file",
        type=click.Path(exists=True, path_type=Path),
        help="Override configuration file path"
    ),
    click.option(
        "--timeout",
        type=click.IntRange(min=10, max=300),
        default=60,
        help="Request timeout in seconds (default: 60)"
    ),
    click.option(
        "--batch-size",
        type=click.IntRange(min=10, max=1000),
        default=100,
        help="Batch size for data processing (default: 100)"
    )
]

# Authentication Options Group
authentication_options = [
    click.option(
        "--auth-timeout",
        type=click.IntRange(min=30, max=300),
        default=60,
        help="Authentication timeout in seconds (default: 60)"
    ),
    click.option(
        "--force-auth",
        is_flag=True,
        help="Force re-authentication even if already authenticated"
    ),
    click.option(
        "--skip-auth-check",
        is_flag=True,
        help="Skip initial authentication check (use with caution)"
    )
]


def add_option_groups(*option_groups):
    """Decorator to add multiple option groups to a command."""
    def decorator(func):
        for option_group in reversed(option_groups):
            for option in reversed(option_group):
                func = option(func)
        return func
    return decorator


# Import and register commands
from .commands.analyze import analyze_command
from .commands.config import config_command
from .commands.report import report_command

# Register commands with CLI
cli.add_command(analyze_command, name="analyze")
cli.add_command(config_command, name="config") 
cli.add_command(report_command, name="report")


def validate_date_range(start_date, end_date, days_back, date_range) -> None:
    """Validate date range parameters."""
    date_params = [start_date, end_date, days_back, date_range]
    provided_params = [p for p in date_params if p is not None]
    
    if len(provided_params) > 2:
        raise click.BadParameter(
            "Cannot specify more than two date range parameters simultaneously"
        )
    
    if start_date and end_date and start_date >= end_date:
        raise click.BadParameter("Start date must be before end date")


def handle_cli_errors(func):
    """Decorator for consistent CLI error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AuthenticationError as e:
            error_message(f"Authentication failed: {e}")
            ctx = click.get_current_context()
            if ctx.obj.verbose:
                error_message("Try running 'mwinit -o' to refresh authentication")
            sys.exit(1)
        except ConfigurationError as e:
            error_message(f"Configuration error: {e}")
            ctx = click.get_current_context()
            if ctx.obj.verbose:
                error_message("Check your configuration file and settings")
            sys.exit(2)
        except DataRetrievalError as e:
            error_message(f"Data retrieval failed: {e}")
            ctx = click.get_current_context()
            if ctx.obj.verbose:
                error_message("Check your network connection and permissions")
            sys.exit(3)
        except TicketAnalysisError as e:
            error_message(f"Analysis error: {e}")
            sys.exit(4)
        except KeyboardInterrupt:
            warning_message("\nOperation cancelled by user")
            sys.exit(130)  # Standard exit code for SIGINT
        except Exception as e:
            error_message(f"Unexpected error: {e}")
            ctx = click.get_current_context()
            if ctx.obj.verbose:
                import traceback
                error_message(traceback.format_exc())
            sys.exit(5)
    
    return wrapper


if __name__ == "__main__":
    cli()