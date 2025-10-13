"""Report command implementation.

This module implements report generation and management commands for
saved analysis results and custom reporting.
"""

from __future__ import annotations
import sys
from datetime import datetime
from typing import Optional, List
from pathlib import Path

import click

from ...models.exceptions import TicketAnalysisError, ConfigurationError
from ..utils import (
    success_message,
    error_message,
    info_message,
    warning_message,
    list_files_with_details
)
from ..shared import handle_cli_errors


@click.group("report")
@click.pass_context
def report_command(ctx: click.Context) -> None:
    """Report generation and management commands.
    
    Manage saved analysis results, generate custom reports, and convert
    between different output formats.
    """
    pass


@report_command.command("list")
@click.option(
    "--directory", "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory to list reports from (default: ./reports)"
)
@click.option(
    "--format-filter",
    type=click.Choice(["json", "csv", "html", "all"]),
    default="all",
    help="Filter by report format"
)
@click.option(
    "--sort-by",
    type=click.Choice(["name", "date", "size"]),
    default="date",
    help="Sort reports by criteria"
)
@click.option(
    "--limit",
    type=click.IntRange(min=1, max=100),
    default=20,
    help="Maximum number of reports to show"
)
@click.pass_context
@handle_cli_errors
def list_reports(
    ctx: click.Context,
    directory: Optional[Path],
    format_filter: str,
    sort_by: str,
    limit: int
) -> None:
    """List available analysis reports.
    
    Shows saved analysis reports with details including creation date,
    file size, and format information.
    
    Examples:
        ticket-analyzer report list
        ticket-analyzer report list --format-filter html --sort-by size
    """
    report_dir = directory or Path(ctx.obj.output_dir)
    
    if not report_dir.exists():
        warning_message(f"Report directory does not exist: {report_dir}")
        return
    
    # Get report files
    patterns = {
        "json": "*.json",
        "csv": "*.csv", 
        "html": "*.html",
        "all": "*"
    }
    
    pattern = patterns[format_filter]
    report_files = list(report_dir.glob(pattern))
    
    if not report_files:
        info_message(f"No reports found in {report_dir}")
        return
    
    # Sort files
    if sort_by == "name":
        report_files.sort(key=lambda f: f.name)
    elif sort_by == "date":
        report_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    elif sort_by == "size":
        report_files.sort(key=lambda f: f.stat().st_size, reverse=True)
    
    # Limit results
    report_files = report_files[:limit]
    
    # Display results
    info_message(f"Reports in {report_dir} (showing {len(report_files)} of {len(list(report_dir.iterdir()))} files):")
    
    file_details = list_files_with_details(report_files)
    click.echo(file_details)


@report_command.command("convert")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output file path (auto-generated if not specified)"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "csv", "html"]),
    required=True,
    help="Target output format"
)
@click.option(
    "--include-charts",
    is_flag=True,
    help="Include charts in HTML output (if applicable)"
)
@click.option(
    "--template",
    help="Custom template for HTML output"
)
@click.pass_context
@handle_cli_errors
def convert_report(
    ctx: click.Context,
    input_file: Path,
    output: Optional[Path],
    format: str,
    include_charts: bool,
    template: Optional[str]
) -> None:
    """Convert analysis report between formats.
    
    Convert existing analysis reports from one format to another,
    preserving data integrity and adding format-specific features.
    
    Examples:
        ticket-analyzer report convert analysis.json --format html
        ticket-analyzer report convert data.csv --format json --output results.json
    """
    if ctx.obj.verbose:
        info_message(f"Converting {input_file} to {format} format")
    
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        conversion_service = container.conversion_service
        
        # Generate output path if not specified
        if not output:
            output = input_file.parent / f"{input_file.stem}_converted.{format}"
        
        # Perform conversion
        conversion_service.convert_report(
            input_path=input_file,
            output_path=output,
            target_format=format,
            include_charts=include_charts,
            template=template
        )
        
        success_message(f"Report converted successfully: {output}")
        
        if ctx.obj.verbose:
            input_size = input_file.stat().st_size
            output_size = output.stat().st_size
            info_message(f"Input size: {input_size:,} bytes")
            info_message(f"Output size: {output_size:,} bytes")
    
    except Exception as e:
        error_message(f"Conversion failed: {e}")
        sys.exit(1)


@report_command.command("merge")
@click.argument("input_files", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file for merged report"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "csv", "html"]),
    default="json",
    help="Output format for merged report"
)
@click.option(
    "--merge-strategy",
    type=click.Choice(["combine", "compare", "aggregate"]),
    default="combine",
    help="Strategy for merging reports"
)
@click.pass_context
@handle_cli_errors
def merge_reports(
    ctx: click.Context,
    input_files: tuple,
    output: Path,
    format: str,
    merge_strategy: str
) -> None:
    """Merge multiple analysis reports into a single report.
    
    Combine data from multiple analysis reports using different strategies:
    - combine: Concatenate all data
    - compare: Side-by-side comparison
    - aggregate: Statistical aggregation
    
    Examples:
        ticket-analyzer report merge report1.json report2.json --output combined.json
        ticket-analyzer report merge *.json --output summary.html --merge-strategy aggregate
    """
    if len(input_files) < 2:
        error_message("At least 2 input files are required for merging")
        sys.exit(1)
    
    if ctx.obj.verbose:
        info_message(f"Merging {len(input_files)} reports using '{merge_strategy}' strategy")
        for file in input_files:
            info_message(f"  Input: {file}")
    
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        merge_service = container.merge_service
        
        # Perform merge
        merge_service.merge_reports(
            input_paths=list(input_files),
            output_path=output,
            output_format=format,
            strategy=merge_strategy
        )
        
        success_message(f"Reports merged successfully: {output}")
        
        if ctx.obj.verbose:
            output_size = output.stat().st_size
            info_message(f"Merged report size: {output_size:,} bytes")
    
    except Exception as e:
        error_message(f"Merge failed: {e}")
        sys.exit(1)


@report_command.command("clean")
@click.option(
    "--directory", "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory to clean (default: ./reports)"
)
@click.option(
    "--older-than",
    type=click.IntRange(min=1),
    default=30,
    help="Remove reports older than N days (default: 30)"
)
@click.option(
    "--format-filter",
    type=click.Choice(["json", "csv", "html", "all"]),
    default="all",
    help="Only clean specific format files"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting"
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt"
)
@click.pass_context
@handle_cli_errors
def clean_reports(
    ctx: click.Context,
    directory: Optional[Path],
    older_than: int,
    format_filter: str,
    dry_run: bool,
    force: bool
) -> None:
    """Clean up old analysis reports.
    
    Remove analysis reports older than specified number of days.
    Use --dry-run to preview what would be deleted.
    
    Examples:
        ticket-analyzer report clean --older-than 7 --dry-run
        ticket-analyzer report clean --format-filter html --force
    """
    report_dir = directory or Path(ctx.obj.output_dir)
    
    if not report_dir.exists():
        warning_message(f"Report directory does not exist: {report_dir}")
        return
    
    # Calculate cutoff date
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=older_than)
    
    # Find files to clean
    patterns = {
        "json": "*.json",
        "csv": "*.csv",
        "html": "*.html", 
        "all": "*"
    }
    
    pattern = patterns[format_filter]
    all_files = list(report_dir.glob(pattern))
    
    old_files = [
        f for f in all_files
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_date
    ]
    
    if not old_files:
        info_message(f"No files older than {older_than} days found")
        return
    
    # Display files to be cleaned
    info_message(f"Found {len(old_files)} files older than {older_than} days:")
    for file in old_files:
        file_date = datetime.fromtimestamp(file.stat().st_mtime)
        info_message(f"  {file.name} ({file_date.strftime('%Y-%m-%d %H:%M')})")
    
    if dry_run:
        info_message("Dry run - no files were deleted")
        return
    
    # Confirm deletion
    if not force:
        if not click.confirm(f"Delete {len(old_files)} files?"):
            info_message("Cleanup cancelled")
            return
    
    # Delete files
    deleted_count = 0
    for file in old_files:
        try:
            file.unlink()
            deleted_count += 1
            if ctx.obj.verbose:
                info_message(f"Deleted: {file.name}")
        except Exception as e:
            error_message(f"Failed to delete {file.name}: {e}")
    
    success_message(f"Cleanup completed: {deleted_count} files deleted")


# Register commands with the report group from main.py
def register_report_commands(report_group):
    """Register report commands with the CLI group."""
    report_group.add_command(list_reports)
    report_group.add_command(convert_report)
    report_group.add_command(merge_reports)
    report_group.add_command(clean_reports)