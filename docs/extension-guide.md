# Extension Guide

## Overview

The Ticket Analysis CLI is designed with extensibility in mind. This guide explains how to extend and customize the application by creating custom metrics calculators, report generators, data sources, and CLI commands.

## Table of Contents

1. [Extension Architecture](#extension-architecture)
2. [Custom Metrics Calculators](#custom-metrics-calculators)
3. [Custom Report Generators](#custom-report-generators)
4. [Custom Data Sources](#custom-data-sources)
5. [Custom CLI Commands](#custom-cli-commands)
6. [Plugin System](#plugin-system)
7. [Configuration Extensions](#configuration-extensions)
8. [Testing Extensions](#testing-extensions)

## Extension Architecture

### Extension Points

The application provides several extension points through well-defined interfaces:

```python
# Core extension interfaces
from ticket_analyzer.interfaces import (
    MetricsCalculator,        # Custom analysis metrics
    ReportingInterface,       # Custom report formats
    DataRetrievalInterface,   # Custom data sources
    ConfigurationInterface,   # Custom configuration sources
    AuthenticationInterface   # Custom authentication methods
)
```

### Registration Mechanism

Extensions are registered through the dependency injection container:

```python
from ticket_analyzer.container import DependencyContainer

def register_extensions(container: DependencyContainer) -> None:
    """Register custom extensions with the application."""
    
    # Register custom calculator
    analysis_service = container.get_analysis_service()
    analysis_service.add_calculator(CustomMetricsCalculator())
    
    # Register custom report generator
    report_service = container.get_report_service()
    report_service.register_generator('custom', CustomReportGenerator())
    
    # Register custom CLI command
    cli_app = container.get_cli_app()
    cli_app.add_command(custom_command)
```

## Custom Metrics Calculators

### Basic Calculator Implementation

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ticket_analyzer.interfaces import MetricsCalculator
from ticket_analyzer.models import Ticket

class TeamVelocityCalculator(MetricsCalculator):
    """Calculate team velocity metrics based on ticket throughput."""
    
    def __init__(self, sprint_days: int = 14):
        """Initialize calculator with sprint duration."""
        self._sprint_days = sprint_days
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate team velocity metrics.
        
        Args:
            tickets: List of tickets to analyze
            
        Returns:
            Dictionary containing velocity metrics
        """
        if not tickets:
            return self._empty_metrics()
        
        # Group tickets by time periods
        velocity_data = self._calculate_velocity_by_period(tickets)
        
        # Calculate trend analysis
        trend_analysis = self._analyze_velocity_trends(velocity_data)
        
        return {
            'team_velocity': {
                'current_sprint_velocity': velocity_data.get('current', 0),
                'average_velocity': velocity_data.get('average', 0),
                'velocity_trend': trend_analysis.get('trend', 'stable'),
                'velocity_consistency': trend_analysis.get('consistency', 0),
                'sprint_days': self._sprint_days
            },
            'throughput_metrics': {
                'tickets_per_day': self._calculate_daily_throughput(tickets),
                'completion_rate': self._calculate_completion_rate(tickets),
                'cycle_time_average': self._calculate_average_cycle_time(tickets)
            }
        }
    
    def get_metric_names(self) -> List[str]:
        """Get list of metrics provided by this calculator."""
        return [
            'team_velocity',
            'throughput_metrics'
        ]
    
    def _calculate_velocity_by_period(self, tickets: List[Ticket]) -> Dict[str, float]:
        """Calculate velocity for different time periods."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        sprint_duration = timedelta(days=self._sprint_days)
        
        # Current sprint tickets
        current_sprint_start = now - sprint_duration
        current_sprint_tickets = [
            t for t in tickets 
            if t.created_date >= current_sprint_start and t.is_resolved()
        ]
        
        # Historical sprints for average calculation
        historical_velocities = []
        for i in range(1, 6):  # Last 5 sprints
            sprint_start = now - (sprint_duration * (i + 1))
            sprint_end = now - (sprint_duration * i)
            
            sprint_tickets = [
                t for t in tickets
                if sprint_start <= t.created_date < sprint_end and t.is_resolved()
            ]
            historical_velocities.append(len(sprint_tickets))
        
        return {
            'current': len(current_sprint_tickets),
            'average': sum(historical_velocities) / len(historical_velocities) if historical_velocities else 0,
            'historical': historical_velocities
        }
    
    def _analyze_velocity_trends(self, velocity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze velocity trends and consistency."""
        historical = velocity_data.get('historical', [])
        current = velocity_data.get('current', 0)
        
        if len(historical) < 2:
            return {'trend': 'insufficient_data', 'consistency': 0}
        
        # Calculate trend
        recent_avg = sum(historical[:3]) / 3 if len(historical) >= 3 else sum(historical) / len(historical)
        older_avg = sum(historical[3:]) / len(historical[3:]) if len(historical) > 3 else recent_avg
        
        if recent_avg > older_avg * 1.1:
            trend = 'improving'
        elif recent_avg < older_avg * 0.9:
            trend = 'declining'
        else:
            trend = 'stable'
        
        # Calculate consistency (coefficient of variation)
        if historical:
            mean_velocity = sum(historical) / len(historical)
            variance = sum((v - mean_velocity) ** 2 for v in historical) / len(historical)
            std_dev = variance ** 0.5
            consistency = 1 - (std_dev / mean_velocity) if mean_velocity > 0 else 0
        else:
            consistency = 0
        
        return {
            'trend': trend,
            'consistency': max(0, min(1, consistency))  # Normalize to 0-1
        }
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'team_velocity': {
                'current_sprint_velocity': 0,
                'average_velocity': 0,
                'velocity_trend': 'no_data',
                'velocity_consistency': 0,
                'sprint_days': self._sprint_days
            },
            'throughput_metrics': {
                'tickets_per_day': 0,
                'completion_rate': 0,
                'cycle_time_average': 0
            }
        }
```

### Advanced Calculator with Configuration

```python
class SLAComplianceCalculator(MetricsCalculator):
    """Calculate SLA compliance metrics with configurable thresholds."""
    
    def __init__(self, sla_config: Optional[Dict[str, int]] = None):
        """Initialize with SLA configuration.
        
        Args:
            sla_config: Dictionary mapping severity levels to SLA hours
        """
        self._sla_config = sla_config or {
            'SEV_1': 4,   # 4 hours for critical
            'SEV_2': 24,  # 24 hours for high
            'SEV_3': 72,  # 72 hours for medium
            'SEV_4': 168, # 1 week for low
            'SEV_5': 720  # 1 month for informational
        }
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate SLA compliance metrics."""
        if not tickets:
            return {'sla_compliance': {'overall_rate': 0, 'by_severity': {}}}
        
        compliance_data = {}
        overall_compliant = 0
        total_tickets = len(tickets)
        
        # Group tickets by severity
        by_severity = {}
        for ticket in tickets:
            severity = ticket.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(ticket)
        
        # Calculate compliance for each severity
        for severity, severity_tickets in by_severity.items():
            sla_hours = self._sla_config.get(severity, 24)
            compliant_count = 0
            
            for ticket in severity_tickets:
                if self._is_sla_compliant(ticket, sla_hours):
                    compliant_count += 1
                    overall_compliant += 1
            
            compliance_rate = compliant_count / len(severity_tickets)
            compliance_data[severity] = {
                'compliance_rate': compliance_rate,
                'compliant_tickets': compliant_count,
                'total_tickets': len(severity_tickets),
                'sla_threshold_hours': sla_hours
            }
        
        # Calculate breach analysis
        breach_analysis = self._analyze_sla_breaches(tickets)
        
        return {
            'sla_compliance': {
                'overall_rate': overall_compliant / total_tickets,
                'by_severity': compliance_data,
                'breach_analysis': breach_analysis,
                'sla_configuration': self._sla_config
            }
        }
    
    def _is_sla_compliant(self, ticket: Ticket, sla_hours: int) -> bool:
        """Check if ticket meets SLA requirements."""
        if ticket.is_resolved():
            resolution_hours = ticket.resolution_time().total_seconds() / 3600
            return resolution_hours <= sla_hours
        else:
            # For open tickets, check if they're still within SLA
            age_hours = ticket.age().total_seconds() / 3600
            return age_hours <= sla_hours
    
    def _analyze_sla_breaches(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze patterns in SLA breaches."""
        breaches = []
        
        for ticket in tickets:
            sla_hours = self._sla_config.get(ticket.severity.value, 24)
            if not self._is_sla_compliant(ticket, sla_hours):
                if ticket.is_resolved():
                    breach_hours = ticket.resolution_time().total_seconds() / 3600 - sla_hours
                else:
                    breach_hours = ticket.age().total_seconds() / 3600 - sla_hours
                
                breaches.append({
                    'ticket_id': ticket.id,
                    'severity': ticket.severity.value,
                    'breach_hours': breach_hours,
                    'assignee': ticket.assignee,
                    'resolver_group': ticket.resolver_group
                })
        
        # Analyze breach patterns
        if breaches:
            avg_breach_hours = sum(b['breach_hours'] for b in breaches) / len(breaches)
            max_breach = max(breaches, key=lambda x: x['breach_hours'])
            
            # Group by assignee
            by_assignee = {}
            for breach in breaches:
                assignee = breach['assignee'] or 'Unassigned'
                if assignee not in by_assignee:
                    by_assignee[assignee] = 0
                by_assignee[assignee] += 1
        else:
            avg_breach_hours = 0
            max_breach = None
            by_assignee = {}
        
        return {
            'total_breaches': len(breaches),
            'average_breach_hours': avg_breach_hours,
            'worst_breach': max_breach,
            'breaches_by_assignee': by_assignee
        }
    
    def get_metric_names(self) -> List[str]:
        return ['sla_compliance']
```

## Custom Report Generators

### Basic Report Generator

```python
from ticket_analyzer.interfaces import ReportingInterface
import json
import csv
from pathlib import Path

class ExcelReportGenerator(ReportingInterface):
    """Generate Excel reports with multiple worksheets."""
    
    def __init__(self):
        """Initialize Excel report generator."""
        try:
            import openpyxl
            self._openpyxl = openpyxl
        except ImportError:
            raise ImportError("openpyxl is required for Excel report generation")
    
    def generate_report(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate Excel report with multiple worksheets.
        
        Args:
            data: Analysis data to include in report
            output_path: Path where report should be saved
            
        Returns:
            Path to generated Excel file
        """
        # Ensure .xlsx extension
        output_path = Path(output_path)
        if output_path.suffix.lower() != '.xlsx':
            output_path = output_path.with_suffix('.xlsx')
        
        # Create workbook
        workbook = self._openpyxl.Workbook()
        
        # Remove default worksheet
        workbook.remove(workbook.active)
        
        # Create worksheets
        self._create_summary_worksheet(workbook, data)
        self._create_metrics_worksheet(workbook, data)
        self._create_trends_worksheet(workbook, data)
        
        # Save workbook
        workbook.save(output_path)
        
        return str(output_path)
    
    def get_supported_formats(self) -> List[str]:
        """Get supported format names."""
        return ['excel', 'xlsx']
    
    def _create_summary_worksheet(self, workbook, data: Dict[str, Any]) -> None:
        """Create summary worksheet."""
        ws = workbook.create_sheet("Summary")
        
        # Add headers
        ws['A1'] = 'Ticket Analysis Summary'
        ws['A1'].font = self._openpyxl.styles.Font(bold=True, size=16)
        
        # Add summary data
        summary = data.get('summary', {})
        row = 3
        
        for key, value in summary.items():
            ws[f'A{row}'] = key.replace('_', ' ').title()
            ws[f'B{row}'] = value
            row += 1
        
        # Format columns
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 15
    
    def _create_metrics_worksheet(self, workbook, data: Dict[str, Any]) -> None:
        """Create metrics worksheet."""
        ws = workbook.create_sheet("Metrics")
        
        # Headers
        ws['A1'] = 'Metric Name'
        ws['B1'] = 'Value'
        ws['C1'] = 'Description'
        
        # Style headers
        for cell in ws[1]:
            cell.font = self._openpyxl.styles.Font(bold=True)
        
        # Add metrics data
        metrics = data.get('metrics', {})
        row = 2
        
        for metric_name, value in metrics.items():
            ws[f'A{row}'] = metric_name
            ws[f'B{row}'] = value
            ws[f'C{row}'] = self._get_metric_description(metric_name)
            row += 1
        
        # Auto-fit columns
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    def _create_trends_worksheet(self, workbook, data: Dict[str, Any]) -> None:
        """Create trends worksheet with charts."""
        ws = workbook.create_sheet("Trends")
        
        trends = data.get('trends', {})
        if not trends:
            ws['A1'] = 'No trend data available'
            return
        
        # Add trend data
        ws['A1'] = 'Trend Analysis'
        ws['A1'].font = self._openpyxl.styles.Font(bold=True, size=14)
        
        row = 3
        for trend_name, trend_data in trends.items():
            ws[f'A{row}'] = trend_name.replace('_', ' ').title()
            ws[f'A{row}'].font = self._openpyxl.styles.Font(bold=True)
            row += 1
            
            if isinstance(trend_data, dict):
                for key, value in trend_data.items():
                    ws[f'B{row}'] = key.replace('_', ' ').title()
                    ws[f'C{row}'] = value
                    row += 1
            row += 1  # Add spacing
    
    def _get_metric_description(self, metric_name: str) -> str:
        """Get description for metric."""
        descriptions = {
            'total_tickets': 'Total number of tickets analyzed',
            'avg_resolution_time': 'Average time to resolve tickets (hours)',
            'median_resolution_time': 'Median time to resolve tickets (hours)',
            'sla_compliance_rate': 'Percentage of tickets meeting SLA requirements',
            'team_velocity': 'Team velocity metrics and trends'
        }
        return descriptions.get(metric_name, 'Custom metric')
```

### Interactive HTML Report Generator

```python
class InteractiveHTMLReportGenerator(ReportingInterface):
    """Generate interactive HTML reports with JavaScript charts."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize with optional custom template directory."""
        self._template_dir = Path(template_dir) if template_dir else Path(__file__).parent / 'templates'
        
        try:
            from jinja2 import Environment, FileSystemLoader
            self._jinja_env = Environment(loader=FileSystemLoader(str(self._template_dir)))
        except ImportError:
            raise ImportError("jinja2 is required for HTML report generation")
    
    def generate_report(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate interactive HTML report."""
        # Prepare data for template
        template_data = self._prepare_template_data(data)
        
        # Load and render template
        template = self._jinja_env.get_template('interactive_report.html')
        html_content = template.render(**template_data)
        
        # Write to file
        output_path = Path(output_path)
        if output_path.suffix.lower() != '.html':
            output_path = output_path.with_suffix('.html')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def get_supported_formats(self) -> List[str]:
        return ['interactive_html', 'html_interactive']
    
    def _prepare_template_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Jinja2 template."""
        return {
            'title': 'Ticket Analysis Report',
            'generated_at': data.get('generated_at', datetime.now().isoformat()),
            'summary': data.get('summary', {}),
            'metrics': data.get('metrics', {}),
            'trends': data.get('trends', {}),
            'charts_data': self._prepare_charts_data(data),
            'ticket_count': data.get('ticket_count', 0)
        }
    
    def _prepare_charts_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for JavaScript charts."""
        charts = {}
        
        # Status distribution chart
        metrics = data.get('metrics', {})
        if 'status_counts' in metrics:
            charts['status_distribution'] = {
                'type': 'pie',
                'data': {
                    'labels': list(metrics['status_counts'].keys()),
                    'values': list(metrics['status_counts'].values())
                }
            }
        
        # Resolution time trend
        trends = data.get('trends', {})
        if 'resolution_time_trend' in trends:
            trend_data = trends['resolution_time_trend']
            charts['resolution_trend'] = {
                'type': 'line',
                'data': {
                    'labels': trend_data.get('dates', []),
                    'values': trend_data.get('values', [])
                }
            }
        
        return charts
```

## Custom Data Sources

### Custom Repository Implementation

```python
from ticket_analyzer.interfaces import DataRetrievalInterface
from ticket_analyzer.models import Ticket, SearchCriteria

class DatabaseTicketRepository(DataRetrievalInterface):
    """Repository implementation using direct database access."""
    
    def __init__(self, connection_string: str):
        """Initialize with database connection."""
        self._connection_string = connection_string
        self._connection = None
    
    def search_tickets(self, criteria: SearchCriteria) -> List[Ticket]:
        """Search tickets using database queries."""
        query = self._build_sql_query(criteria)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, self._get_query_params(criteria))
            
            tickets = []
            for row in cursor.fetchall():
                ticket = self._map_row_to_ticket(row)
                tickets.append(ticket)
            
            return tickets
    
    def get_ticket_details(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID from database."""
        query = """
            SELECT id, title, status, severity, created_date, updated_date,
                   resolved_date, assignee, resolver_group, description
            FROM tickets 
            WHERE id = ?
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (ticket_id,))
            row = cursor.fetchone()
            
            if row:
                return self._map_row_to_ticket(row)
            return None
    
    def count_by_status(self, status: str) -> int:
        """Count tickets by status."""
        query = "SELECT COUNT(*) FROM tickets WHERE status = ?"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (status,))
            return cursor.fetchone()[0]
    
    def _get_connection(self):
        """Get database connection."""
        if not self._connection:
            import sqlite3  # or your preferred database driver
            self._connection = sqlite3.connect(self._connection_string)
        return self._connection
    
    def _build_sql_query(self, criteria: SearchCriteria) -> str:
        """Build SQL query from search criteria."""
        base_query = """
            SELECT id, title, status, severity, created_date, updated_date,
                   resolved_date, assignee, resolver_group, description
            FROM tickets
            WHERE 1=1
        """
        
        conditions = []
        
        if criteria.status:
            placeholders = ','.join('?' * len(criteria.status))
            conditions.append(f"status IN ({placeholders})")
        
        if criteria.assignee:
            conditions.append("assignee = ?")
        
        if criteria.created_after:
            conditions.append("created_date >= ?")
        
        if criteria.created_before:
            conditions.append("created_date <= ?")
        
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        if criteria.max_results:
            base_query += f" LIMIT {criteria.max_results}"
        
        return base_query
    
    def _get_query_params(self, criteria: SearchCriteria) -> tuple:
        """Get query parameters from criteria."""
        params = []
        
        if criteria.status:
            params.extend(criteria.status)
        
        if criteria.assignee:
            params.append(criteria.assignee)
        
        if criteria.created_after:
            params.append(criteria.created_after.isoformat())
        
        if criteria.created_before:
            params.append(criteria.created_before.isoformat())
        
        return tuple(params)
    
    def _map_row_to_ticket(self, row) -> Ticket:
        """Map database row to Ticket object."""
        return Ticket(
            id=row[0],
            title=row[1],
            status=TicketStatus(row[2]),
            severity=TicketSeverity(row[3]),
            created_date=datetime.fromisoformat(row[4]),
            updated_date=datetime.fromisoformat(row[5]),
            resolved_date=datetime.fromisoformat(row[6]) if row[6] else None,
            assignee=row[7],
            resolver_group=row[8],
            description=row[9] or ""
        )
```

## Custom CLI Commands

### Basic Custom Command

```python
import click
from ticket_analyzer.models import SearchCriteria
from ticket_analyzer.container import DependencyContainer

@click.command()
@click.option('--team', required=True, help='Team name to analyze')
@click.option('--days', default=30, help='Number of days to analyze')
@click.option('--format', default='table', help='Output format')
@click.pass_context
def team_dashboard(ctx: click.Context, team: str, days: int, format: str) -> None:
    """Generate team dashboard with key metrics.
    
    This command provides a focused view of team performance including
    velocity, SLA compliance, and workload distribution.
    """
    try:
        # Get container from context
        container = ctx.obj.get('container') or DependencyContainer()
        
        # Build search criteria
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        criteria = SearchCriteria(
            resolver_group=team,
            created_after=start_date,
            created_before=end_date
        )
        
        # Get services
        analysis_service = container.get_analysis_service()
        
        # Add team-specific calculators
        team_calculator = TeamVelocityCalculator()
        sla_calculator = SLAComplianceCalculator()
        
        analysis_service.add_calculator(team_calculator)
        analysis_service.add_calculator(sla_calculator)
        
        # Perform analysis
        with click.progressbar(length=100, label=f'Analyzing {team} team') as bar:
            result = analysis_service.analyze_tickets(criteria)
            bar.update(100)
        
        # Display results
        if format == 'table':
            display_team_dashboard_table(result, team)
        elif format == 'json':
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            # Generate report file
            report_service = container.get_report_service()
            output_path = f"{team}_dashboard.{format}"
            report_path = report_service.generate_report(result, format, output_path)
            click.echo(f"Team dashboard saved to: {report_path}")
        
        click.echo(click.style(f"✓ Team dashboard generated for {team}", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"Dashboard generation failed: {e}", fg='red'), err=True)
        if ctx.obj.get('verbose'):
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()

def display_team_dashboard_table(result: AnalysisResult, team: str) -> None:
    """Display team dashboard in table format."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    # Team header
    console.print(Panel(f"[bold blue]{team} Team Dashboard[/bold blue]"))
    
    # Summary metrics
    summary_table = Table(title="Summary Metrics")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Tickets", str(result.ticket_count))
    summary_table.add_row("Analysis Period", f"{result.date_range[0].date()} to {result.date_range[1].date()}")
    
    # Add team velocity metrics
    velocity_metrics = result.get_metric('team_velocity')
    if velocity_metrics:
        summary_table.add_row("Current Sprint Velocity", str(velocity_metrics.get('current_sprint_velocity', 0)))
        summary_table.add_row("Average Velocity", f"{velocity_metrics.get('average_velocity', 0):.1f}")
        summary_table.add_row("Velocity Trend", velocity_metrics.get('velocity_trend', 'unknown'))
    
    # Add SLA compliance
    sla_metrics = result.get_metric('sla_compliance')
    if sla_metrics:
        compliance_rate = sla_metrics.get('overall_rate', 0) * 100
        summary_table.add_row("SLA Compliance", f"{compliance_rate:.1f}%")
    
    console.print(summary_table)
```

### Advanced Command with Subcommands

```python
@click.group()
@click.pass_context
def analytics(ctx: click.Context) -> None:
    """Advanced analytics commands for ticket data."""
    pass

@analytics.command()
@click.option('--metric', multiple=True, help='Specific metrics to calculate')
@click.option('--export', type=click.Path(), help='Export results to file')
@click.pass_context
def custom_metrics(ctx: click.Context, metric: tuple, export: Optional[str]) -> None:
    """Calculate custom metrics with flexible configuration."""
    
    available_calculators = {
        'velocity': TeamVelocityCalculator,
        'sla': SLAComplianceCalculator,
        'workload': WorkloadDistributionCalculator,
        'quality': QualityMetricsCalculator
    }
    
    # Build calculator list
    calculators = []
    if metric:
        for metric_name in metric:
            if metric_name in available_calculators:
                calculators.append(available_calculators[metric_name]())
            else:
                click.echo(f"Unknown metric: {metric_name}", err=True)
                return
    else:
        # Use all calculators
        calculators = [calc() for calc in available_calculators.values()]
    
    # Perform analysis with custom calculators
    container = ctx.obj.get('container') or DependencyContainer()
    analysis_service = container.get_analysis_service()
    
    for calculator in calculators:
        analysis_service.add_calculator(calculator)
    
    # Get default criteria or from parent context
    criteria = SearchCriteria()  # Could be enhanced to inherit from parent
    
    result = analysis_service.analyze_tickets(criteria)
    
    # Output results
    if export:
        with open(export, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        click.echo(f"Results exported to {export}")
    else:
        click.echo(json.dumps(result.metrics, indent=2, default=str))

@analytics.command()
@click.option('--config', type=click.Path(exists=True), help='Configuration file')
@click.pass_context
def batch_analysis(ctx: click.Context, config: Optional[str]) -> None:
    """Run batch analysis with configuration file."""
    
    if config:
        with open(config) as f:
            batch_config = json.load(f)
    else:
        batch_config = {
            'analyses': [
                {'name': 'weekly', 'days': 7},
                {'name': 'monthly', 'days': 30},
                {'name': 'quarterly', 'days': 90}
            ]
        }
    
    container = ctx.obj.get('container') or DependencyContainer()
    
    for analysis_config in batch_config['analyses']:
        click.echo(f"Running {analysis_config['name']} analysis...")
        
        # Configure analysis based on config
        days = analysis_config['days']
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        criteria = SearchCriteria(
            created_after=start_date,
            created_before=end_date
        )
        
        # Run analysis
        analysis_service = container.get_analysis_service()
        result = analysis_service.analyze_tickets(criteria)
        
        # Save results
        output_file = f"{analysis_config['name']}_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        click.echo(f"✓ {analysis_config['name']} analysis saved to {output_file}")

# Register command group
def register_analytics_commands(cli_app):
    """Register analytics command group."""
    cli_app.add_command(analytics)
```

## Plugin System

### Plugin Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class TicketAnalysisPlugin(ABC):
    """Base class for ticket analysis plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass
    
    @abstractmethod
    def initialize(self, container: DependencyContainer) -> None:
        """Initialize plugin with dependency container."""
        pass
    
    @abstractmethod
    def get_calculators(self) -> List[MetricsCalculator]:
        """Get metrics calculators provided by this plugin."""
        pass
    
    @abstractmethod
    def get_report_generators(self) -> Dict[str, ReportingInterface]:
        """Get report generators provided by this plugin."""
        pass
    
    @abstractmethod
    def get_cli_commands(self) -> List[click.Command]:
        """Get CLI commands provided by this plugin."""
        pass

class TeamAnalyticsPlugin(TicketAnalysisPlugin):
    """Plugin providing team-focused analytics."""
    
    @property
    def name(self) -> str:
        return "team_analytics"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def initialize(self, container: DependencyContainer) -> None:
        """Initialize team analytics plugin."""
        self._container = container
        
        # Register calculators
        analysis_service = container.get_analysis_service()
        for calculator in self.get_calculators():
            analysis_service.add_calculator(calculator)
        
        # Register report generators
        report_service = container.get_report_service()
        for format_name, generator in self.get_report_generators().items():
            report_service.register_generator(format_name, generator)
    
    def get_calculators(self) -> List[MetricsCalculator]:
        """Get team analytics calculators."""
        return [
            TeamVelocityCalculator(),
            WorkloadDistributionCalculator(),
            CollaborationMetricsCalculator()
        ]
    
    def get_report_generators(self) -> Dict[str, ReportingInterface]:
        """Get team report generators."""
        return {
            'team_dashboard': TeamDashboardGenerator(),
            'velocity_report': VelocityReportGenerator()
        }
    
    def get_cli_commands(self) -> List[click.Command]:
        """Get team analytics CLI commands."""
        return [team_dashboard, analytics]
```

### Plugin Manager

```python
class PluginManager:
    """Manages plugin loading and registration."""
    
    def __init__(self, container: DependencyContainer):
        self._container = container
        self._plugins: Dict[str, TicketAnalysisPlugin] = {}
    
    def load_plugin(self, plugin_class: type) -> None:
        """Load and register a plugin."""
        plugin = plugin_class()
        
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin {plugin.name} already loaded")
        
        # Initialize plugin
        plugin.initialize(self._container)
        
        # Store plugin
        self._plugins[plugin.name] = plugin
        
        logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
    
    def load_plugins_from_directory(self, plugin_dir: str) -> None:
        """Load all plugins from directory."""
        import importlib.util
        import sys
        
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            return
        
        for plugin_file in plugin_path.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            # Load module
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_file.stem] = module
            spec.loader.exec_module(module)
            
            # Find plugin classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, TicketAnalysisPlugin) and 
                    attr != TicketAnalysisPlugin):
                    
                    try:
                        self.load_plugin(attr)
                    except Exception as e:
                        logger.error(f"Failed to load plugin {attr_name}: {e}")
    
    def get_plugin(self, name: str) -> Optional[TicketAnalysisPlugin]:
        """Get plugin by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[str]:
        """List loaded plugin names."""
        return list(self._plugins.keys())
```

## Configuration Extensions

### Custom Configuration Sources

```python
class DatabaseConfigHandler(ConfigurationHandler):
    """Load configuration from database."""
    
    def __init__(self, connection_string: str):
        super().__init__()
        self._connection_string = connection_string
    
    def _get_config_value(self, key: str) -> Optional[Any]:
        """Get configuration value from database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM config WHERE key = ?", 
                    (key,)
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Database config error: {e}")
            return None

class RemoteConfigHandler(ConfigurationHandler):
    """Load configuration from remote service."""
    
    def __init__(self, config_url: str, api_key: str):
        super().__init__()
        self._config_url = config_url
        self._api_key = api_key
        self._cache = {}
        self._cache_expiry = None
    
    def _get_config_value(self, key: str) -> Optional[Any]:
        """Get configuration value from remote service."""
        if self._is_cache_valid():
            return self._cache.get(key)
        
        try:
            # Fetch configuration from remote service
            import requests
            
            response = requests.get(
                f"{self._config_url}/config",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10
            )
            
            if response.status_code == 200:
                self._cache = response.json()
                self._cache_expiry = datetime.now() + timedelta(minutes=5)
                return self._cache.get(key)
            
        except Exception as e:
            logger.error(f"Remote config error: {e}")
        
        return None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        return (self._cache_expiry and 
                datetime.now() < self._cache_expiry)
```

## Testing Extensions

### Testing Custom Calculators

```python
class TestCustomCalculators:
    """Test cases for custom calculators."""
    
    @pytest.fixture
    def sample_tickets(self):
        """Sample tickets for testing."""
        return [
            Ticket(
                id="T1",
                title="Test 1",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_2,
                created_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 2),
                resolved_date=datetime(2024, 1, 2)
            ),
            Ticket(
                id="T2",
                title="Test 2",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_1,
                created_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 1)
            )
        ]
    
    def test_sla_calculator_compliance(self, sample_tickets):
        """Test SLA compliance calculation."""
        calculator = SLAComplianceCalculator({
            'SEV_1': 4,
            'SEV_2': 24
        })
        
        result = calculator.calculate(sample_tickets)
        
        assert 'sla_compliance' in result
        compliance = result['sla_compliance']
        assert 'overall_rate' in compliance
        assert 'by_severity' in compliance
    
    def test_team_velocity_calculator(self, sample_tickets):
        """Test team velocity calculation."""
        calculator = TeamVelocityCalculator(sprint_days=14)
        
        result = calculator.calculate(sample_tickets)
        
        assert 'team_velocity' in result
        velocity = result['team_velocity']
        assert 'current_sprint_velocity' in velocity
        assert 'average_velocity' in velocity

class TestCustomReportGenerators:
    """Test cases for custom report generators."""
    
    def test_excel_generator(self, tmp_path):
        """Test Excel report generation."""
        generator = ExcelReportGenerator()
        
        test_data = {
            'summary': {'total_tickets': 100},
            'metrics': {'avg_resolution_time': 24.5},
            'trends': {}
        }
        
        output_path = tmp_path / "test_report.xlsx"
        result_path = generator.generate_report(test_data, str(output_path))
        
        assert Path(result_path).exists()
        assert Path(result_path).suffix == '.xlsx'
    
    def test_interactive_html_generator(self, tmp_path):
        """Test interactive HTML report generation."""
        generator = InteractiveHTMLReportGenerator()
        
        test_data = {
            'summary': {'total_tickets': 50},
            'metrics': {'status_counts': {'Open': 20, 'Resolved': 30}},
            'trends': {}
        }
        
        output_path = tmp_path / "test_report.html"
        result_path = generator.generate_report(test_data, str(output_path))
        
        assert Path(result_path).exists()
        
        # Verify HTML content
        with open(result_path) as f:
            content = f.read()
            assert 'Ticket Analysis Report' in content
            assert 'total_tickets' in content
```

This extension guide provides comprehensive examples for extending the Ticket Analysis CLI with custom functionality. Each extension type includes practical examples and testing approaches to ensure reliable implementations.