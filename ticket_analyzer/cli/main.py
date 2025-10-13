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


# Import shared option groups and utilities
from .shared import (
    time_period_options,
    output_options,
    configuration_options,
    authentication_options,
    add_option_groups,
    validate_date_range,
    handle_cli_errors
)


# Import and register commands
from .commands.analyze import analyze_command
from .commands.config import config_command
from .commands.report import report_command

# Register commands with CLI
cli.add_command(analyze_command, name="analyze")
cli.add_command(config_command, name="config") 
cli.add_command(report_command, name="report")





if __name__ == "__main__":
    cli()