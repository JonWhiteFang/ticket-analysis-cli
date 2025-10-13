"""Analyze command implementation.

This module implements the primary analysis command with all filtering and
output options for ticket data analysis.
"""

from __future__ import annotations
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

import click
from tqdm import tqdm

from ...models.exceptions import (
    TicketAnalysisError,
    AuthenticationError,
    DataRetrievalError
)
from ...models.ticket import TicketStatus, TicketSeverity
from ...models.analysis import SearchCriteria
from ..utils import (
    success_message,
    error_message,
    info_message,
    warning_message,
    format_table_output,
    validate_ticket_id_format
)
from ..shared import (
    add_option_groups,
    time_period_options,
    output_options,
    configuration_options,
    authentication_options,
    validate_date_range,
    handle_cli_errors
)


@click.command("analyze")
@add_option_groups(
    time_period_options,
    output_options,
    configuration_options,
    authentication_options
)
@click.option(
    "--ticket-ids",
    multiple=True,
    help="Specific ticket IDs to analyze (can be used multiple times)"
)
@click.option(
    "--status",
    multiple=True,
    type=click.Choice([status.value for status in TicketStatus]),
    help="Filter by ticket status (can be used multiple times)"
)
@click.option(
    "--severity",
    multiple=True,
    type=click.Choice([sev.value for sev in TicketSeverity]),
    help="Filter by ticket severity (can be used multiple times)"
)
@click.option(
    "--assignee",
    multiple=True,
    help="Filter by assignee username (can be used multiple times)"
)
@click.option(
    "--resolver-group",
    multiple=True,
    help="Filter by resolver group (can be used multiple times)"
)
@click.option(
    "--tags",
    multiple=True,
    help="Filter by tags (can be used multiple times)"
)
@click.option(
    "--search-term",
    help="Search term for ticket title/description"
)
@click.option(
    "--include-resolved",
    is_flag=True,
    help="Include resolved tickets in analysis"
)
@click.option(
    "--exclude-automated",
    is_flag=True,
    help="Exclude automated tickets from analysis"
)
@click.option(
    "--priority-analysis",
    is_flag=True,
    help="Include priority-based analysis"
)
@click.option(
    "--trend-analysis",
    is_flag=True,
    help="Include trend analysis over time"
)
@click.option(
    "--team-performance",
    is_flag=True,
    help="Include team performance metrics"
)
@click.option(
    "--export-raw-data",
    is_flag=True,
    help="Export raw ticket data along with analysis"
)
@click.pass_context
@handle_cli_errors
def analyze_command(
    ctx: click.Context,
    # Time period options
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    days_back: int,
    date_range: Optional[str],
    # Output options
    format: str,
    output: Optional[Path],
    max_results: int,
    include_charts: bool,
    no_color: bool,
    # Configuration options
    config_file: Optional[Path],
    timeout: int,
    batch_size: int,
    # Authentication options
    auth_timeout: int,
    force_auth: bool,
    skip_auth_check: bool,
    # Analysis options
    ticket_ids: tuple,
    status: tuple,
    severity: tuple,
    assignee: tuple,
    resolver_group: tuple,
    tags: tuple,
    search_term: Optional[str],
    include_resolved: bool,
    exclude_automated: bool,
    priority_analysis: bool,
    trend_analysis: bool,
    team_performance: bool,
    export_raw_data: bool
) -> None:
    """Analyze ticket data with comprehensive filtering and reporting options.
    
    This command retrieves ticket data based on specified criteria and generates
    detailed analysis including metrics, trends, and performance indicators.
    
    Examples:
        # Analyze open tickets from last 7 days
        ticket-analyzer analyze --status Open --days-back 7
        
        # Analyze specific tickets with JSON output
        ticket-analyzer analyze --ticket-ids T123456 T789012 --format json
        
        # Generate HTML report with charts
        ticket-analyzer analyze --format html --include-charts --output report.html
        
        # Team performance analysis
        ticket-analyzer analyze --team-performance --resolver-group "My Team"
    """
    # Validate date range parameters
    validate_date_range(start_date, end_date, days_back, date_range)
    
    # Validate ticket IDs if provided
    if ticket_ids:
        for ticket_id in ticket_ids:
            if not validate_ticket_id_format(ticket_id):
                raise click.BadParameter(f"Invalid ticket ID format: {ticket_id}")
    
    # Set up color output
    if no_color:
        import colorama
        colorama.deinit()
    
    # Display analysis configuration
    if ctx.obj.verbose:
        info_message("Analysis Configuration:")
        info_message(f"  Format: {format}")
        info_message(f"  Max Results: {max_results}")
        info_message(f"  Batch Size: {batch_size}")
        if ticket_ids:
            info_message(f"  Specific Tickets: {len(ticket_ids)} tickets")
        if status:
            info_message(f"  Status Filter: {', '.join(status)}")
        if severity:
            info_message(f"  Severity Filter: {', '.join(severity)}")
    
    try:
        # Initialize services
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        # Configure container based on CLI options
        container.configure({
            'config_file': str(config_file) if config_file else ctx.obj.config_file,
            'timeout': timeout,
            'batch_size': batch_size,
            'auth_timeout': auth_timeout,
            'force_auth': force_auth,
            'skip_auth_check': skip_auth_check,
            'verbose': ctx.obj.verbose
        })
        
        analysis_service = container.analysis_service
        
        # Build search criteria
        search_criteria = _build_search_criteria(
            ticket_ids=ticket_ids,
            status=status,
            severity=severity,
            assignee=assignee,
            resolver_group=resolver_group,
            tags=tags,
            search_term=search_term,
            start_date=start_date,
            end_date=end_date,
            days_back=days_back,
            date_range=date_range,
            max_results=max_results,
            include_resolved=include_resolved,
            exclude_automated=exclude_automated
        )
        
        if ctx.obj.verbose:
            info_message(f"Search criteria: {search_criteria}")
        
        # Perform analysis with progress tracking
        with tqdm(desc="Analyzing tickets", unit="tickets") as pbar:
            analysis_result = analysis_service.analyze_tickets(
                criteria=search_criteria,
                include_priority_analysis=priority_analysis,
                include_trend_analysis=trend_analysis,
                include_team_performance=team_performance,
                progress_callback=lambda current, total: pbar.update(1)
            )
        
        success_message(f"Analysis completed: {analysis_result.ticket_count} tickets processed")
        
        # Generate output
        output_service = container.output_service
        
        if format == "table":
            # Display results in table format
            table_output = format_table_output(analysis_result)
            click.echo(table_output)
        else:
            # Generate file output
            output_path = output or Path(ctx.obj.output_dir) / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
            
            output_service.generate_output(
                analysis_result=analysis_result,
                format=format,
                output_path=output_path,
                include_charts=include_charts,
                export_raw_data=export_raw_data
            )
            
            success_message(f"Analysis saved to: {output_path}")
        
        # Display summary
        _display_analysis_summary(analysis_result, ctx.obj.verbose)
        
    except AuthenticationError as e:
        error_message(f"Authentication failed: {e}")
        if not skip_auth_check:
            error_message("Try running 'mwinit -o' to refresh authentication")
        sys.exit(1)
    except DataRetrievalError as e:
        error_message(f"Data retrieval failed: {e}")
        if ctx.obj.verbose:
            error_message("Check your network connection and MCP configuration")
        sys.exit(3)
    except TicketAnalysisError as e:
        error_message(f"Analysis failed: {e}")
        sys.exit(4)


def _build_search_criteria(
    ticket_ids: tuple,
    status: tuple,
    severity: tuple,
    assignee: tuple,
    resolver_group: tuple,
    tags: tuple,
    search_term: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    days_back: int,
    date_range: Optional[str],
    max_results: int,
    include_resolved: bool,
    exclude_automated: bool
) -> SearchCriteria:
    """Build search criteria from CLI options."""
    
    # Calculate date range
    if start_date and end_date:
        date_from = start_date
        date_to = end_date
    elif date_range:
        date_from, date_to = _calculate_predefined_date_range(date_range)
    else:
        # Use days_back
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days_back)
    
    # Build status list
    status_list = list(status) if status else None
    if not include_resolved and status_list:
        # Remove resolved statuses if not explicitly included
        resolved_statuses = [TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]
        status_list = [s for s in status_list if s not in resolved_statuses]
    
    return SearchCriteria(
        ticket_ids=list(ticket_ids) if ticket_ids else None,
        status=status_list,
        severity=list(severity) if severity else None,
        assignee=list(assignee) if assignee else None,
        resolver_group=list(resolver_group) if resolver_group else None,
        tags=list(tags) if tags else None,
        search_term=search_term,
        created_after=date_from,
        created_before=date_to,
        max_results=max_results,
        exclude_automated=exclude_automated
    )


def _calculate_predefined_date_range(date_range: str) -> tuple[datetime, datetime]:
    """Calculate date range for predefined options."""
    now = datetime.now()
    
    if date_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif date_range == "yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_range == "week":
        start = now - timedelta(days=7)
        end = now
    elif date_range == "month":
        start = now - timedelta(days=30)
        end = now
    elif date_range == "quarter":
        start = now - timedelta(days=90)
        end = now
    else:
        raise ValueError(f"Unknown date range: {date_range}")
    
    return start, end


def _display_analysis_summary(analysis_result, verbose: bool) -> None:
    """Display analysis summary."""
    info_message("\nAnalysis Summary:")
    info_message(f"  Total Tickets: {analysis_result.ticket_count}")
    info_message(f"  Date Range: {analysis_result.date_range[0]} to {analysis_result.date_range[1]}")
    
    if hasattr(analysis_result, 'metrics') and analysis_result.metrics:
        if 'status_distribution' in analysis_result.metrics:
            info_message("  Status Distribution:")
            for status, count in analysis_result.metrics['status_distribution'].items():
                info_message(f"    {status}: {count}")
        
        if 'avg_resolution_time' in analysis_result.metrics:
            avg_time = analysis_result.metrics['avg_resolution_time']
            info_message(f"  Average Resolution Time: {avg_time:.1f} hours")
    
    if verbose and hasattr(analysis_result, 'summary'):
        info_message("\nKey Insights:")
        for insight in analysis_result.summary.get('key_insights', []):
            info_message(f"  • {insight}")


# Register command with the analyze group from main.py
def register_analyze_commands(analyze_group):
    """Register analyze commands with the CLI group."""
    analyze_group.add_command(analyze_command)