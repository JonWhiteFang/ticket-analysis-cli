# Developer Guide

## Overview

This guide provides comprehensive information for developers who want to contribute to, extend, or customize the Ticket Analysis CLI application. It covers development setup, coding standards, architecture patterns, and extension mechanisms.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Architecture Patterns](#architecture-patterns)
5. [Extension Development](#extension-development)
6. [Testing Guidelines](#testing-guidelines)
7. [Contributing Workflow](#contributing-workflow)
8. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## Development Environment Setup

### Prerequisites

- **Python 3.7+**: Required for core application
- **Node.js 16+**: Required for MCP components
- **Git**: For version control
- **mwinit**: Amazon authentication tool

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/ticket-analyzer.git
cd ticket-analyzer

# Create virtual environment
python3.7 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Verify installation
python -m ticket_analyzer --help
```

### Development Dependencies

```bash
# Core development tools
pip install pytest pytest-cov black flake8 isort mypy

# Additional tools
pip install bandit safety pre-commit

# Documentation tools
pip install sphinx sphinx-rtd-theme
```

### IDE Configuration

#### VS Code Settings

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### PyCharm Configuration

1. Set Python interpreter to `./venv/bin/python`
2. Enable Black formatter in Tools → External Tools
3. Configure flake8 in Settings → Tools → External Tools
4. Set up pytest as default test runner

## Project Structure

### Directory Layout

```
ticket-analyzer/
├── ticket_analyzer/              # Main package
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── app.py                   # Main application
│   ├── container.py             # Dependency injection
│   ├── interfaces.py            # Core interfaces
│   │
│   ├── cli/                     # CLI framework
│   │   ├── __init__.py
│   │   ├── main.py              # Click application
│   │   ├── commands/            # CLI commands
│   │   ├── options.py           # Reusable options
│   │   └── utils.py             # CLI utilities
│   │
│   ├── models/                  # Domain models
│   │   ├── __init__.py
│   │   ├── ticket.py            # Ticket model
│   │   ├── analysis.py          # Analysis models
│   │   ├── config.py            # Configuration models
│   │   └── exceptions.py        # Custom exceptions
│   │
│   ├── services/                # Application services
│   │   ├── __init__.py
│   │   └── analysis_service.py  # Analysis orchestration
│   │
│   ├── repositories/            # Data access layer
│   │   ├── __init__.py
│   │   └── mcp_ticket_repository.py
│   │
│   ├── external/                # External integrations
│   │   ├── __init__.py
│   │   ├── mcp_client.py        # MCP client
│   │   └── resilience.py        # Circuit breaker, retry
│   │
│   ├── auth/                    # Authentication
│   │   ├── __init__.py
│   │   ├── midway_auth.py       # Midway integration
│   │   └── session.py           # Session management
│   │
│   ├── analysis/                # Analysis engine
│   │   ├── __init__.py
│   │   ├── analysis_service.py  # Main analysis service
│   │   ├── calculators.py       # Metrics calculators
│   │   ├── strategies.py        # Analysis strategies
│   │   └── trends.py            # Trend analysis
│   │
│   ├── reporting/               # Report generation
│   │   ├── __init__.py
│   │   ├── cli_reporter.py      # CLI output
│   │   ├── html_reporter.py     # HTML reports
│   │   ├── formatters.py        # Data formatters
│   │   └── charts.py            # Chart generation
│   │
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── config_manager.py    # Configuration loader
│   │   └── handlers.py          # Config source handlers
│   │
│   ├── security/                # Security components
│   │   ├── __init__.py
│   │   ├── sanitizer.py         # Data sanitization
│   │   ├── validation.py        # Input validation
│   │   └── file_ops.py          # Secure file operations
│   │
│   └── logging/                 # Logging utilities
│       ├── __init__.py
│       └── logger.py            # Logging configuration
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test fixtures
│
├── docs/                        # Documentation
│   ├── api.md                   # API documentation
│   ├── architecture.md          # Architecture guide
│   ├── developer-guide.md       # This file
│   └── user-guide.md            # User documentation
│
├── examples/                    # Usage examples
│   ├── config-examples/         # Configuration samples
│   ├── scripts/                 # Automation scripts
│   └── integration/             # Integration examples
│
├── templates/                   # Report templates
│   ├── html/                    # HTML templates
│   └── css/                     # Stylesheets
│
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── pyproject.toml              # Project configuration
├── setup.py                    # Package setup
└── README.md                   # Project overview
```

### Module Organization Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Direction**: Dependencies flow inward (CLI → Services → Domain)
3. **Interface Segregation**: Small, focused interfaces
4. **Dependency Inversion**: Depend on abstractions, not concretions

## Coding Standards

### Python 3.7 Compatibility

```python
# Use future annotations for forward compatibility
from __future__ import annotations

# Type hints compatible with Python 3.7
from typing import Dict, List, Optional, Union, Any

# Dataclasses (available in Python 3.7)
from dataclasses import dataclass

@dataclass
class ExampleModel:
    id: str
    name: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
```

### Code Formatting

```bash
# Format code with Black
black ticket_analyzer tests

# Sort imports with isort
isort ticket_analyzer tests --profile black

# Lint with flake8
flake8 ticket_analyzer tests --max-line-length=88 --extend-ignore=E203,W503

# Type checking with mypy
mypy ticket_analyzer
```

### Documentation Standards

```python
def analyze_tickets(tickets: List[Ticket], 
                   options: AnalysisOptions) -> AnalysisResult:
    """Analyze ticket data with comprehensive metrics calculation.
    
    This function processes a list of tickets and calculates various
    performance metrics including resolution times, status distributions,
    and trend analysis. All sensitive data is automatically sanitized.
    
    Args:
        tickets: List of ticket objects to analyze. Each ticket must
            have valid id, status, and created_date fields.
        options: Analysis configuration including metric types,
            date ranges, and output preferences.
    
    Returns:
        AnalysisResult containing calculated metrics, trends, and
        summary information with generation timestamp.
    
    Raises:
        AnalysisError: If analysis processing fails due to invalid data
            or calculation errors.
        ValidationError: If input tickets or options are invalid.
    
    Example:
        >>> tickets = [Ticket(id="T123", status="Open", ...)]
        >>> options = AnalysisOptions(metrics=["resolution_time"])
        >>> result = analyze_tickets(tickets, options)
        >>> print(result.metrics["avg_resolution_time"])
        24.5
    
    Note:
        This function automatically sanitizes all ticket data to remove
        personally identifiable information before processing.
    
    Since:
        Version 1.0.0
    """
    pass
```

### Error Handling Patterns

```python
# Custom exception hierarchy
class TicketAnalysisError(Exception):
    """Base exception for ticket analysis operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

# Error handling in functions
def process_tickets(tickets: List[Dict[str, Any]]) -> List[Ticket]:
    """Process raw ticket data into domain objects."""
    processed_tickets = []
    
    for ticket_data in tickets:
        try:
            ticket = Ticket.from_dict(ticket_data)
            processed_tickets.append(ticket)
        except ValueError as e:
            logger.warning(f"Invalid ticket data: {e}")
            # Continue processing other tickets
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing ticket: {e}")
            raise TicketAnalysisError(f"Failed to process ticket: {e}")
    
    return processed_tickets
```

### Logging Standards

```python
import logging
from typing import Any, Dict

# Configure logger
logger = logging.getLogger(__name__)

def secure_log_operation(operation: str, data: Dict[str, Any]) -> None:
    """Log operation with sanitized data."""
    sanitized_data = sanitize_log_data(data)
    logger.info(f"Operation: {operation}", extra={"data": sanitized_data})

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from log data."""
    sensitive_keys = {'password', 'token', 'secret', 'key'}
    return {
        k: '***' if k.lower() in sensitive_keys else v 
        for k, v in data.items()
    }
```

## Architecture Patterns

### Repository Pattern Implementation

```python
# Abstract repository interface
class TicketRepository(ABC):
    """Abstract repository for ticket data access."""
    
    @abstractmethod
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets matching search criteria."""
        pass
    
    @abstractmethod
    def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Find ticket by unique identifier."""
        pass

# Concrete implementation
class MCPTicketRepository(TicketRepository):
    """MCP-based ticket repository implementation."""
    
    def __init__(self, mcp_client: MCPClient, sanitizer: DataSanitizer):
        self._client = mcp_client
        self._sanitizer = sanitizer
    
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets using MCP search."""
        raw_data = self._client.search_tickets(criteria.to_mcp_query())
        
        tickets = []
        for item in raw_data:
            sanitized_item = self._sanitizer.sanitize_ticket_data(item)
            ticket = Ticket.from_dict(sanitized_item)
            tickets.append(ticket)
        
        return tickets
```

### Strategy Pattern for Analysis

```python
# Strategy interface
class MetricsCalculator(ABC):
    """Abstract strategy for calculating metrics."""
    
    @abstractmethod
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics from ticket data."""
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get names of metrics this calculator provides."""
        pass

# Concrete strategies
class ResolutionTimeCalculator(MetricsCalculator):
    """Calculate resolution time metrics."""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        resolved_tickets = [t for t in tickets if t.is_resolved()]
        
        if not resolved_tickets:
            return {"avg_resolution_time": 0, "median_resolution_time": 0}
        
        times = [t.resolution_time().total_seconds() / 3600 for t in resolved_tickets]
        
        return {
            "avg_resolution_time": sum(times) / len(times),
            "median_resolution_time": sorted(times)[len(times) // 2],
            "total_resolved": len(resolved_tickets)
        }
    
    def get_metric_names(self) -> List[str]:
        return ["avg_resolution_time", "median_resolution_time", "total_resolved"]

# Context class
class AnalysisEngine:
    """Analysis engine using strategy pattern."""
    
    def __init__(self):
        self._calculators: List[MetricsCalculator] = []
    
    def add_calculator(self, calculator: MetricsCalculator) -> None:
        """Add metrics calculator strategy."""
        self._calculators.append(calculator)
    
    def analyze(self, tickets: List[Ticket]) -> AnalysisResult:
        """Perform analysis using all registered calculators."""
        metrics = {}
        
        for calculator in self._calculators:
            try:
                calculator_metrics = calculator.calculate(tickets)
                metrics.update(calculator_metrics)
            except Exception as e:
                logger.error(f"Calculator {calculator.__class__.__name__} failed: {e}")
        
        return AnalysisResult(metrics=metrics, ticket_count=len(tickets))
```

### Dependency Injection Container

```python
class DependencyContainer:
    """Dependency injection container for service management."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._instances: Dict[str, Any] = {}
    
    def get_auth_service(self) -> AuthenticationInterface:
        """Get authentication service instance."""
        if 'auth_service' not in self._instances:
            auth_config = AuthenticationConfig(**self._config.get('auth', {}))
            self._instances['auth_service'] = MidwayAuthenticator(auth_config)
        return self._instances['auth_service']
    
    def get_ticket_repository(self) -> TicketRepository:
        """Get ticket repository instance."""
        if 'ticket_repository' not in self._instances:
            mcp_client = self.get_mcp_client()
            auth_service = self.get_auth_service()
            sanitizer = self.get_data_sanitizer()
            
            self._instances['ticket_repository'] = MCPTicketRepository(
                mcp_client, auth_service, sanitizer
            )
        return self._instances['ticket_repository']
    
    def get_analysis_service(self) -> AnalysisService:
        """Get analysis service instance."""
        if 'analysis_service' not in self._instances:
            repository = self.get_ticket_repository()
            calculators = self._create_default_calculators()
            
            self._instances['analysis_service'] = AnalysisService(
                repository, calculators
            )
        return self._instances['analysis_service']
```

## Extension Development

### Creating Custom Metrics Calculators

```python
class CustomSLACalculator(MetricsCalculator):
    """Custom calculator for SLA compliance metrics."""
    
    def __init__(self, sla_hours: int = 24):
        self._sla_hours = sla_hours
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate SLA compliance metrics."""
        total_tickets = len(tickets)
        if total_tickets == 0:
            return {"sla_compliance_rate": 0, "sla_violations": 0}
        
        violations = 0
        for ticket in tickets:
            if ticket.is_resolved():
                resolution_hours = ticket.resolution_time().total_seconds() / 3600
                if resolution_hours > self._sla_hours:
                    violations += 1
            elif ticket.age().total_seconds() / 3600 > self._sla_hours:
                violations += 1
        
        compliance_rate = (total_tickets - violations) / total_tickets
        
        return {
            "sla_compliance_rate": compliance_rate,
            "sla_violations": violations,
            "sla_threshold_hours": self._sla_hours
        }
    
    def get_metric_names(self) -> List[str]:
        return ["sla_compliance_rate", "sla_violations", "sla_threshold_hours"]

# Register custom calculator
def register_custom_calculator(container: DependencyContainer):
    """Register custom calculator with the system."""
    analysis_service = container.get_analysis_service()
    sla_calculator = CustomSLACalculator(sla_hours=48)
    analysis_service.add_calculator(sla_calculator)
```

### Creating Custom Report Generators

```python
class CustomCSVReportGenerator(ReportingInterface):
    """Custom CSV report generator with specific formatting."""
    
    def generate_report(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate CSV report with custom format."""
        import csv
        
        # Extract metrics for CSV format
        metrics = data.get('metrics', {})
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Metric', 'Value', 'Description'])
            
            # Write metrics
            for metric_name, value in metrics.items():
                description = self._get_metric_description(metric_name)
                writer.writerow([metric_name, value, description])
        
        return output_path
    
    def get_supported_formats(self) -> List[str]:
        return ['custom_csv']
    
    def _get_metric_description(self, metric_name: str) -> str:
        """Get human-readable description for metric."""
        descriptions = {
            'avg_resolution_time': 'Average time to resolve tickets (hours)',
            'total_tickets': 'Total number of tickets analyzed',
            'sla_compliance_rate': 'Percentage of tickets meeting SLA'
        }
        return descriptions.get(metric_name, 'Custom metric')

# Register custom generator
def register_custom_generator(container: DependencyContainer):
    """Register custom report generator."""
    report_service = container.get_report_service()
    csv_generator = CustomCSVReportGenerator()
    report_service.register_generator('custom_csv', csv_generator)
```

### Creating Custom CLI Commands

```python
@click.command()
@click.option('--team', required=True, help='Team name to analyze')
@click.option('--period', default='30d', help='Analysis period (e.g., 30d, 1w)')
@click.pass_context
def team_report(ctx: click.Context, team: str, period: str) -> None:
    """Generate team-specific analysis report.
    
    This custom command provides detailed analysis for a specific team
    including productivity metrics, SLA compliance, and trend analysis.
    """
    try:
        # Parse period
        days = parse_period(period)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Build criteria for team
        criteria = SearchCriteria(
            resolver_group=team,
            created_after=start_date,
            created_before=end_date
        )
        
        # Get services from container
        container = ctx.obj.get('container')
        analysis_service = container.get_analysis_service()
        
        # Add team-specific calculators
        team_calculator = TeamProductivityCalculator()
        analysis_service.add_calculator(team_calculator)
        
        # Perform analysis
        result = analysis_service.analyze_tickets(criteria)
        
        # Display results
        display_team_report(result, team)
        
    except Exception as e:
        click.echo(click.style(f"Team report failed: {e}", fg='red'), err=True)
        raise click.Abort()

# Add command to CLI
def register_custom_command(cli_app):
    """Register custom command with CLI application."""
    cli_app.add_command(team_report)
```

## Testing Guidelines

### Unit Testing Patterns

```python
# Test class structure
class TestTicketAnalysisService:
    """Test cases for ticket analysis service."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock ticket repository for testing."""
        return Mock(spec=TicketRepository)
    
    @pytest.fixture
    def sample_tickets(self):
        """Sample ticket data for testing."""
        return [
            Ticket(
                id="T123",
                title="Test ticket",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 1)
            ),
            Ticket(
                id="T124",
                title="Resolved ticket",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_2,
                created_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 2),
                resolved_date=datetime(2024, 1, 2)
            )
        ]
    
    def test_analyze_tickets_success(self, mock_repository, sample_tickets):
        """Test successful ticket analysis."""
        # Arrange
        mock_repository.find_by_criteria.return_value = sample_tickets
        service = AnalysisService(mock_repository, [ResolutionTimeCalculator()])
        criteria = SearchCriteria(status=['Open'])
        
        # Act
        result = service.analyze_tickets(criteria)
        
        # Assert
        assert result.ticket_count == 2
        assert 'avg_resolution_time' in result.metrics
        mock_repository.find_by_criteria.assert_called_once_with(criteria)
    
    def test_analyze_empty_dataset(self, mock_repository):
        """Test analysis with empty dataset."""
        # Arrange
        mock_repository.find_by_criteria.return_value = []
        service = AnalysisService(mock_repository, [])
        
        # Act
        result = service.analyze_tickets(SearchCriteria())
        
        # Assert
        assert result.ticket_count == 0
        assert result.metrics == {}
```

### Integration Testing

```python
class TestMCPIntegration:
    """Integration tests for MCP ticket repository."""
    
    @pytest.fixture
    def mcp_client_mock(self):
        """Mock MCP client for integration testing."""
        with patch('ticket_analyzer.external.mcp_client.MCPClient') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance
    
    def test_search_tickets_integration(self, mcp_client_mock):
        """Test complete ticket search flow."""
        # Arrange
        mcp_client_mock.search_tickets.return_value = [
            {
                'id': 'T123',
                'title': 'Test ticket',
                'status': 'Open',
                'created_date': '2024-01-01T00:00:00Z'
            }
        ]
        
        auth_service = Mock(spec=AuthenticationInterface)
        validator = Mock(spec=InputValidator)
        repository = MCPTicketRepository(mcp_client_mock, auth_service, validator)
        
        criteria = SearchCriteria(status=['Open'])
        
        # Act
        tickets = repository.search_tickets(criteria)
        
        # Assert
        assert len(tickets) == 1
        assert tickets[0].id == 'T123'
        auth_service.ensure_authenticated.assert_called_once()
```

### CLI Testing

```python
from click.testing import CliRunner

class TestCLICommands:
    """Test CLI command functionality."""
    
    def test_analyze_command_success(self):
        """Test successful analyze command execution."""
        runner = CliRunner()
        
        with patch('ticket_analyzer.cli.commands.analyze.AnalysisService') as mock_service:
            # Mock successful analysis
            mock_result = AnalysisResult(
                metrics={'total_tickets': 10},
                ticket_count=10,
                generated_at=datetime.now()
            )
            mock_service.return_value.analyze_tickets.return_value = mock_result
            
            # Execute command
            result = runner.invoke(analyze, ['--format', 'json'])
            
            # Assert
            assert result.exit_code == 0
            assert 'total_tickets' in result.output
    
    def test_analyze_command_authentication_error(self):
        """Test analyze command with authentication error."""
        runner = CliRunner()
        
        with patch('ticket_analyzer.cli.commands.analyze.AnalysisService') as mock_service:
            mock_service.return_value.analyze_tickets.side_effect = AuthenticationError("Auth failed")
            
            result = runner.invoke(analyze)
            
            assert result.exit_code == 1
            assert 'Authentication failed' in result.output
```

### Test Coverage Requirements

- **Minimum Coverage**: 80% for core modules
- **Critical Paths**: 100% coverage for authentication and data retrieval
- **Error Scenarios**: All custom exceptions must be tested
- **Integration**: End-to-end workflow testing

## Contributing Workflow

### Git Workflow

```bash
# 1. Create feature branch
git checkout main
git pull origin main
git checkout -b feature/new-analysis-metric

# 2. Make changes with frequent commits
git add .
git commit -m "feat: add SLA compliance calculator

- Implement SLA threshold checking
- Add compliance rate calculation
- Include comprehensive test coverage

Closes #123"

# 3. Keep branch updated
git checkout main
git pull origin main
git checkout feature/new-analysis-metric
git rebase main

# 4. Run tests and checks
pytest
black ticket_analyzer tests
flake8 ticket_analyzer tests
mypy ticket_analyzer

# 5. Push and create PR
git push origin feature/new-analysis-metric
```

### Code Review Checklist

#### Before Requesting Review
- [ ] All tests pass locally
- [ ] Code follows style guidelines (Black, flake8, isort)
- [ ] Type hints added for new functions
- [ ] Documentation updated for new features
- [ ] No sensitive data in code or commits
- [ ] Error handling implemented appropriately

#### Review Criteria
- [ ] Code solves the intended problem
- [ ] Follows established architecture patterns
- [ ] Adequate test coverage
- [ ] Security considerations addressed
- [ ] Performance impact considered
- [ ] Documentation is clear and complete

### Release Process

```bash
# 1. Create release branch
git checkout main
git pull origin main
git checkout -b release/v1.2.0

# 2. Update version numbers
# Update __version__ in __init__.py
# Update version in pyproject.toml
# Update CHANGELOG.md

# 3. Final testing
pytest --cov=ticket_analyzer --cov-fail-under=80
python -m ticket_analyzer --help

# 4. Commit and tag
git add .
git commit -m "chore(release): bump version to 1.2.0"
git tag -a v1.2.0 -m "Release version 1.2.0"

# 5. Merge and push
git checkout main
git merge release/v1.2.0
git push origin main v1.2.0
```

## Debugging and Troubleshooting

### Common Development Issues

#### Authentication Problems
```bash
# Check mwinit status
mwinit -s

# Refresh authentication
mwinit -o

# Debug authentication in code
import logging
logging.getLogger('ticket_analyzer.auth').setLevel(logging.DEBUG)
```

#### MCP Connection Issues
```python
# Enable MCP debug logging
import logging
logging.getLogger('ticket_analyzer.external.mcp_client').setLevel(logging.DEBUG)

# Test MCP connection manually
from ticket_analyzer.external.mcp_client import MCPClient
client = MCPClient(['node', 'mcp-server.js'])
client.connect()
```

#### Data Processing Errors
```python
# Enable data processing debug logs
import logging
logging.getLogger('ticket_analyzer.analysis').setLevel(logging.DEBUG)

# Test with small dataset first
criteria = SearchCriteria(max_results=10)
result = analysis_service.analyze_tickets(criteria)
```

### Performance Debugging

```python
# Profile analysis performance
import cProfile
import pstats

def profile_analysis():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run analysis
    result = analysis_service.analyze_tickets(criteria)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

# Memory usage monitoring
import tracemalloc

tracemalloc.start()
result = analysis_service.analyze_tickets(criteria)
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
```

### Debugging Tools

#### VS Code Debug Configuration
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug CLI",
            "type": "python",
            "request": "launch",
            "module": "ticket_analyzer",
            "args": ["analyze", "--verbose", "--max-results", "10"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

#### Logging Configuration for Development
```python
# Development logging setup
import logging

def setup_development_logging():
    """Configure detailed logging for development."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug.log')
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('ticket_analyzer.auth').setLevel(logging.DEBUG)
    logging.getLogger('ticket_analyzer.external').setLevel(logging.DEBUG)
    logging.getLogger('ticket_analyzer.analysis').setLevel(logging.INFO)
```

This developer guide provides the foundation for contributing to and extending the Ticket Analysis CLI. For specific questions or advanced topics, refer to the API documentation and architecture guide, or reach out to the development team.