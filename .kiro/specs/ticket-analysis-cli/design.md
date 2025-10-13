# Design Document

## Overview

The Ticket Analysis CLI Application is designed as a modular Python application that follows clean architecture principles. The system integrates with Amazon's internal ticketing infrastructure through the Builder MCP (Model Context Protocol) to provide comprehensive ticket analysis and reporting capabilities. The architecture emphasizes security, testability, and maintainability while ensuring strict compatibility with Python 3.7 and Node.js 16 for any JavaScript components.

### Version Compatibility Requirements

- **Python 3.7**: All Python code must be compatible with Python 3.7 syntax and standard library
- **Node.js 16**: Any JavaScript components or MCP integrations must support Node.js 16
- **Dependency Constraints**: All dependencies must support the target Python and Node.js versions

## Architecture

The application follows Clean Architecture principles with a layered approach that ensures separation of concerns, testability, and maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                CLI Layer (Presentation)                     │
│    ├── commands/                                            │
│    │   ├── analyze.py                                       │
│    │   └── report.py                                        │
│    └── Click framework with color-coded output              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            Application Layer (Use Cases)                    │
│    ├── services/                                            │
│    │   ├── analysis_service.py                              │
│    │   └── report_service.py                                │
│    └── Orchestration & Workflow Management                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│             Domain Layer (Business Logic)                   │
│    ├── models/                                              │
│    │   ├── ticket.py                                        │
│    │   └── analysis_result.py                               │
│    └── Core business rules and entities                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│        Infrastructure Layer (External Concerns)             │
│    ├── repositories/                                        │
│    │   ├── mcp_ticket_repository.py                         │
│    │   └── file_repository.py                               │
│    └── external/                                            │
│        ├── mcp_client.py                                    │
│        └── auth_service.py                                  │
└─────────────────────────────────────────────────────────────┘
```

### Design Patterns Implementation

The architecture implements several key design patterns for maintainability and extensibility:

- **Repository Pattern**: For data access abstraction (ticket retrieval)
- **Strategy Pattern**: For different analysis types and metrics calculators
- **Template Method Pattern**: For report generation in multiple formats
- **Chain of Responsibility**: For configuration hierarchy management
- **Circuit Breaker Pattern**: For external service resilience and fault tolerance
- **Dependency Injection**: For testability and loose coupling

## Components and Interfaces

### Core Interfaces (interfaces.py)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class AuthenticationInterface(ABC):
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with Amazon's internal systems"""
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        pass

class DataRetrievalInterface(ABC):
    @abstractmethod
    def search_tickets(self, query: str, date_range: tuple) -> List[Dict[str, Any]]:
        """Search tickets using Lucene query syntax"""
        pass
    
    @abstractmethod
    def get_ticket_details(self, ticket_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific ticket"""
        pass

class AnalysisInterface(ABC):
    @abstractmethod
    def calculate_metrics(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate key performance metrics from ticket data"""
        pass
    
    @abstractmethod
    def generate_trends(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trend analysis from ticket data"""
        pass

class ReportingInterface(ABC):
    @abstractmethod
    def generate_report(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate report and return the output file path"""
        pass

class ConfigurationInterface(ABC):
    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from various sources"""
        pass
    
    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration setting"""
        pass
```

### Authentication Module (auth/)

**Design Pattern:** Adapter Pattern with secure session management and timeout handling

```python
# midway_auth.py
from __future__ import annotations
import subprocess
import signal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import contextmanager

@dataclass
class AuthenticationConfig:
    """Configuration for authentication settings."""
    timeout_seconds: int = 60
    max_retry_attempts: int = 3
    check_interval_seconds: int = 300  # 5 minutes

class SecureMidwayAuthenticator(AuthenticationInterface):
    """Secure Midway authentication with session management"""
    
    def __init__(self, config: AuthenticationConfig) -> None:
        self._config = config
        self._session = AuthenticationSession()
        self._last_auth_check: Optional[float] = None
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """Execute mwinit subprocess with security measures"""
        for attempt in range(self._config.max_retry_attempts):
            try:
                with self._authentication_timeout(self._config.timeout_seconds):
                    result = self._execute_secure_mwinit()
                    if result:
                        self._session.start_session()
                        return True
            except AuthenticationTimeoutError:
                logger.error(f"Authentication timeout on attempt {attempt + 1}")
                continue
        return False
    
    def _execute_secure_mwinit(self) -> bool:
        """Securely execute mwinit with proper environment isolation"""
        try:
            result = subprocess.run(
                ["mwinit", "-o"],
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
                env=self._get_secure_env()
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            raise AuthenticationTimeoutError("mwinit command timed out")
        except FileNotFoundError:
            raise AuthenticationError("mwinit command not found")
    
    def _get_secure_env(self) -> Dict[str, str]:
        """Get minimal secure environment for subprocess"""
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "KRB5_CONFIG": os.environ.get("KRB5_CONFIG", ""),
            "KRB5CCNAME": os.environ.get("KRB5CCNAME", ""),
        }
    
    @contextmanager
    def _authentication_timeout(self, seconds: int):
        """Context manager for authentication timeout handling"""
        def timeout_handler(signum: int, frame: Any) -> None:
            raise AuthenticationTimeoutError(f"Authentication timed out after {seconds} seconds")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

class AuthenticationSession:
    """Manage authentication session lifecycle with automatic expiry"""
    
    def __init__(self, session_duration: timedelta = timedelta(hours=8)) -> None:
        self._session_duration = session_duration
        self._session_start: Optional[datetime] = None
        self._authenticated = False
    
    def start_session(self) -> None:
        """Start new authentication session"""
        self._session_start = datetime.now()
        self._authenticated = True
        logger.info("Authentication session started")
    
    def is_session_valid(self) -> bool:
        """Check if current session is still valid"""
        if not self._authenticated or not self._session_start:
            return False
        
        session_age = datetime.now() - self._session_start
        if session_age > self._session_duration:
            logger.info("Authentication session expired")
            self._invalidate_session()
            return False
        
        return True
```

### Data Retrieval Module (data_retrieval/)

**Design Pattern:** Repository Pattern with Circuit Breaker, Retry Logic, and Input Validation

```python
# mcp_ticket_repository.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, 
                 timeout: timedelta = timedelta(minutes=1)) -> None:
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED

class MCPTicketRepository(DataRetrievalInterface):
    """Repository for ticket data access via Builder MCP with resilience patterns"""
    
    def __init__(self, mcp_client: MCPClient, 
                 auth_service: AuthenticationInterface,
                 validator: InputValidator) -> None:
        self._client = mcp_client
        self._auth_service = auth_service
        self._validator = validator
        self._circuit_breaker = CircuitBreaker()
        self._retry_policy = MCPRetryPolicy(max_attempts=3, base_delay=1.0)
        self._sanitizer = TicketDataSanitizer()
    
    @with_retry(retry_policy)
    def search_tickets(self, criteria: SearchCriteria) -> List[Ticket]:
        """Search tickets with comprehensive validation and error handling"""
        # Validate search criteria
        validated_filters = self._validator.validate_ticket_filters(criteria.to_dict())
        
        # Ensure authentication
        self._auth_service.ensure_authenticated()
        
        # Execute search with circuit breaker protection
        raw_data = self._circuit_breaker.call(
            self._client.search_tickets, 
            validated_filters
        )
        
        # Sanitize and convert to domain objects
        sanitized_data = [
            self._sanitizer.sanitize_ticket_data(item) 
            for item in raw_data
        ]
        
        return [self._map_to_ticket(item) for item in sanitized_data]
    
    def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Find ticket by ID with validation and sanitization"""
        # Validate ticket ID format
        if not self._validator.validate_input(ticket_id, 'ticket_id'):
            raise ValueError(f"Invalid ticket ID format: {ticket_id}")
        
        try:
            self._auth_service.ensure_authenticated()
            data = self._client.get_ticket(ticket_id)
            
            if data:
                sanitized_data = self._sanitizer.sanitize_ticket_data(data)
                return self._map_to_ticket(sanitized_data)
            return None
            
        except MCPError as e:
            logger.error(f"Failed to retrieve ticket {ticket_id}: {e}")
            return None
    
    def _map_to_ticket(self, data: Dict[str, Any]) -> Ticket:
        """Map raw ticket data to domain model with validation"""
        # Validate required fields
        required_fields = {"id", "title", "status"}
        if not all(field in data for field in required_fields):
            raise DataProcessingError(f"Missing required fields in ticket data")
        
        return Ticket(
            id=data["id"],
            title=data["title"],
            status=TicketStatus(data["status"]),
            severity=TicketSeverity(data.get("severity", "SEV_5")),
            created_date=self._parse_date(data.get("created_date")),
            updated_date=self._parse_date(data.get("updated_date")),
            resolved_date=self._parse_date(data.get("resolved_date")),
            assignee=data.get("assignee"),
            resolver_group=data.get("resolver_group"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )

class MCPRetryPolicy:
    """Retry policy for MCP operations with exponential backoff"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 10.0, backoff_factor: float = 2.0) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry logic and exponential backoff"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except (MCPConnectionError, MCPTimeoutError) as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    time.sleep(delay)
                    continue
                break
            except MCPError:
                # Don't retry on non-recoverable errors
                raise
        
        raise last_exception
```

### Analysis Module (analysis/)

**Design Pattern:** Strategy Pattern with Template Method for extensible analysis types

```python
# analysis_service.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta

class MetricsCalculator(ABC):
    """Abstract strategy for calculating metrics"""
    
    @abstractmethod
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics from tickets"""
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides"""
        pass

class ResolutionTimeCalculator(MetricsCalculator):
    """Strategy for calculating resolution time metrics"""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate resolution time statistics with comprehensive analysis"""
        resolved_tickets = [t for t in tickets if t.is_resolved()]
        if not resolved_tickets:
            return {
                "avg_resolution_time_hours": 0,
                "median_resolution_time_hours": 0,
                "total_resolved": 0,
                "by_severity": {}
            }
        
        # Convert to pandas for efficient analysis
        df = pd.DataFrame([
            {
                'resolution_time_hours': t.resolution_time().total_seconds() / 3600,
                'severity': t.severity.value,
                'created_date': t.created_date
            }
            for t in resolved_tickets
        ])
        
        return {
            "avg_resolution_time_hours": df['resolution_time_hours'].mean(),
            "median_resolution_time_hours": df['resolution_time_hours'].median(),
            "total_resolved": len(resolved_tickets),
            "by_severity": df.groupby('severity')['resolution_time_hours'].mean().to_dict(),
            "percentiles": {
                "p90": df['resolution_time_hours'].quantile(0.9),
                "p95": df['resolution_time_hours'].quantile(0.95),
                "p99": df['resolution_time_hours'].quantile(0.99)
            }
        }
    
    def get_metric_names(self) -> List[str]:
        return ["avg_resolution_time_hours", "median_resolution_time_hours", 
                "total_resolved", "by_severity", "percentiles"]

class StatusDistributionCalculator(MetricsCalculator):
    """Strategy for calculating status distribution with trend analysis"""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate status distribution with time-based trends"""
        if not tickets:
            return {"status_counts": {}, "status_percentages": {}, "trends": {}}
        
        df = pd.DataFrame([
            {
                'status': t.status.value,
                'created_date': t.created_date,
                'severity': t.severity.value
            }
            for t in tickets
        ])
        
        total = len(tickets)
        status_counts = df['status'].value_counts().to_dict()
        status_percentages = {
            status: (count / total) * 100 
            for status, count in status_counts.items()
        }
        
        # Calculate weekly trends
        df['week'] = df['created_date'].dt.to_period('W')
        weekly_trends = df.groupby(['week', 'status']).size().unstack(fill_value=0)
        
        return {
            "status_counts": status_counts,
            "status_percentages": status_percentages,
            "by_severity": df.groupby(['severity', 'status']).size().unstack(fill_value=0).to_dict(),
            "weekly_trends": weekly_trends.to_dict()
        }

class AnalysisEngine:
    """Context class using different calculation strategies with template method"""
    
    def __init__(self) -> None:
        self._calculators: List[MetricsCalculator] = []
        self._data_processor = TicketDataProcessor()
    
    def add_calculator(self, calculator: MetricsCalculator) -> None:
        """Add a metrics calculator strategy"""
        self._calculators.append(calculator)
    
    def analyze(self, tickets: List[Ticket]) -> AnalysisResult:
        """Template method for comprehensive ticket analysis"""
        # Validate input data
        validated_tickets = self._validate_tickets(tickets)
        
        # Process data for analysis
        processed_data = self._data_processor.process(validated_tickets)
        
        # Calculate metrics using all strategies
        metrics = self._calculate_all_metrics(processed_data)
        
        # Generate summary insights
        summary = self._generate_summary(metrics, processed_data)
        
        return AnalysisResult(
            metrics=metrics,
            summary=summary,
            generated_at=datetime.now(),
            ticket_count=len(validated_tickets),
            date_range=self._get_date_range(validated_tickets)
        )
    
    def _validate_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """Validate ticket data before analysis"""
        valid_tickets = []
        for ticket in tickets:
            if self._is_valid_ticket(ticket):
                valid_tickets.append(ticket)
            else:
                logger.warning(f"Invalid ticket data for ID: {ticket.id}")
        return valid_tickets
    
    def _calculate_all_metrics(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics using all registered calculators"""
        metrics = {}
        for calculator in self._calculators:
            try:
                calculator_metrics = calculator.calculate(tickets)
                metrics.update(calculator_metrics)
            except Exception as e:
                logger.error(f"Error in {calculator.__class__.__name__}: {e}")
                # Continue with other calculators
        return metrics
    
    def _generate_summary(self, metrics: Dict[str, Any], 
                         tickets: List[Ticket]) -> Dict[str, Any]:
        """Generate high-level summary insights"""
        return {
            "total_tickets": len(tickets),
            "analysis_period": self._get_date_range(tickets),
            "key_insights": self._extract_key_insights(metrics),
            "recommendations": self._generate_recommendations(metrics)
        }

class TicketDataProcessor:
    """Responsible for processing and cleaning ticket data for analysis"""
    
    def process(self, tickets: List[Ticket]) -> List[Ticket]:
        """Process ticket data with cleaning and validation"""
        processed = []
        for ticket in tickets:
            # Clean and normalize data
            cleaned_ticket = self._clean_ticket_data(ticket)
            if cleaned_ticket:
                processed.append(cleaned_ticket)
        return processed
    
    def _clean_ticket_data(self, ticket: Ticket) -> Optional[Ticket]:
        """Clean individual ticket data"""
        # Implement data cleaning logic
        # Handle missing dates, normalize status values, etc.
        return ticket
```

### Reporting Module (reporting/)

**Design Pattern:** Template Method Pattern for different report formats

```python
# cli_reporter.py
class CLIReporter(ReportingInterface):
    """Generates formatted CLI reports with color coding"""
    
    def __init__(self):
        self.colorama_init = True
        self.table_formatter = TableFormatter()
    
    def generate_report(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate colorized CLI report"""
        # Uses colorama for cross-platform color support
        # Formats data in tabular structure
        # Provides summary statistics and key insights

# html_reporter.py
class HTMLReporter(ReportingInterface):
    """Generates HTML reports with embedded visualizations"""
    
    def __init__(self):
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        self.chart_generator = ChartGenerator()
    
    def generate_report(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate HTML report with embedded charts"""
        # Uses Jinja2 templates for HTML structure
        # Embeds matplotlib charts as base64 images
        # Includes interactive elements with embedded JavaScript
```

### Configuration Module (config/)

**Design Pattern:** Chain of Responsibility for configuration hierarchy

```python
# config_manager.py
class ConfigurationManager(ConfigurationInterface):
    """Manages configuration from multiple sources with priority hierarchy"""
    
    def __init__(self):
        self.config_chain = [
            CommandLineConfigHandler(),
            ConfigFileHandler(),
            EnvironmentVariableHandler(),
            DefaultConfigHandler()
        ]
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration following priority hierarchy"""
        # 1. Command-line arguments (highest priority)
        # 2. Configuration files (config.json, config.ini)
        # 3. Environment variables
        # 4. Default values (lowest priority)
```

## Data Models

### Core Data Models (models.py)

**Python 3.7 Compatibility Notes**: 
- Uses `from __future__ import annotations` for forward references
- Dataclasses available in Python 3.7
- Type hints compatible with Python 3.7 typing module

```python
from __future__ import annotations  # Python 3.7 forward compatibility
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TicketStatus(Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

class TicketSeverity(Enum):
    SEV_1 = "SEV_1"
    SEV_2 = "SEV_2"
    SEV_3 = "SEV_3"
    SEV_4 = "SEV_4"
    SEV_5 = "SEV_5"

@dataclass
class Ticket:
    """Core ticket data model - Python 3.7 compatible"""
    id: str
    title: str
    description: str
    status: TicketStatus
    severity: TicketSeverity
    created_date: datetime
    updated_date: datetime
    resolved_date: Optional[datetime] = None
    assignee: Optional[str] = None
    resolver_group: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalysisResult:
    """Analysis results data model"""
    metrics: Dict[str, Any]
    trends: Dict[str, Any]
    summary: Dict[str, Any]
    generated_at: datetime
    date_range: tuple
    ticket_count: int

@dataclass
class ReportConfig:
    """Report generation configuration"""
    format: str  # 'cli' or 'html'
    output_path: str
    include_charts: bool = True
    color_output: bool = True
    template_name: Optional[str] = None

# Custom Exceptions
class TicketAnalysisError(Exception):
    """Base exception for ticket analysis errors"""
    pass

class AuthenticationError(TicketAnalysisError):
    """Authentication-related errors"""
    pass

class ConfigurationError(TicketAnalysisError):
    """Configuration-related errors"""
    pass

class DataRetrievalError(TicketAnalysisError):
    """Data retrieval errors"""
    pass

class AnalysisError(TicketAnalysisError):
    """Analysis processing errors"""
    pass
```

## Error Handling

### Error Handling Strategy

1. **Graceful Degradation**: System continues operation with reduced functionality when non-critical components fail
2. **Circuit Breaker Pattern**: Prevents cascading failures in external service calls
3. **Retry Logic**: Exponential backoff with jitter for transient failures
4. **User-Friendly Messages**: Technical errors are translated to actionable user messages
5. **Logging Strategy**: Structured logging with different levels (DEBUG, INFO, WARNING, ERROR)

### Error Handling Implementation

```python
# Error handling decorator for service methods
def handle_service_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise TicketAnalysisError("Please run 'mwinit' to authenticate")
        except DataRetrievalError as e:
            logger.error(f"Data retrieval failed: {e}")
            raise TicketAnalysisError("Unable to retrieve ticket data. Please try again later.")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise TicketAnalysisError("An unexpected error occurred. Please check logs for details.")
    return wrapper
```

## Testing Strategy

### Testing Architecture

1. **Unit Tests**: Test individual components in isolation with mocked dependencies
2. **Integration Tests**: Test component interactions and external service integration
3. **End-to-End Tests**: Test complete CLI workflows
4. **Contract Tests**: Verify MCP integration contracts

### Testing Implementation

```python
# Example test structure
class TestTicketAnalyzer:
    @pytest.fixture
    def sample_tickets(self):
        """Provide sample ticket data for testing"""
        return [
            Ticket(id="T123", title="Test Ticket", ...),
            # Additional test data
        ]
    
    @pytest.fixture
    def mock_data_retriever(self):
        """Mock data retrieval service"""
        mock = Mock(spec=DataRetrievalInterface)
        return mock
    
    def test_calculate_metrics_success(self, sample_tickets):
        """Test successful metrics calculation"""
        analyzer = TicketAnalyzer()
        result = analyzer.calculate_metrics(sample_tickets)
        assert 'resolution_time' in result
        assert 'volume_trends' in result
    
    def test_calculate_metrics_empty_data(self):
        """Test metrics calculation with empty dataset"""
        analyzer = TicketAnalyzer()
        result = analyzer.calculate_metrics([])
        assert result['ticket_count'] == 0
```

### Test Coverage Requirements and Standards

- **Core Modules**: Minimum 80% code coverage using pytest-cov
- **Critical Paths**: 100% coverage for authentication and data retrieval
- **Error Scenarios**: All custom exceptions must be tested
- **CLI Interface**: Integration tests for all command combinations using Click testing utilities

### Testing Framework Implementation

```python
# conftest.py - Pytest configuration and fixtures
import pytest
from typing import Generator, Dict, Any
from unittest.mock import Mock, patch

@pytest.fixture
def sample_ticket_data() -> Dict[str, Any]:
    """Sample ticket data for testing"""
    return {
        "id": "T123456",
        "title": "Test ticket",
        "status": "Open",
        "created_date": "2024-01-01T00:00:00Z",
        "assignee": "testuser"
    }

@pytest.fixture
def mock_mcp_client() -> Generator[Mock, None, None]:
    """Mock MCP client for testing"""
    with patch('ticket_analyzer.external.mcp_client.MCPClient') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def temp_config_file(tmp_path) -> str:
    """Create temporary configuration file"""
    config_file = tmp_path / "config.json"
    config_data = {"output_format": "json", "max_results": 50}
    config_file.write_text(json.dumps(config_data))
    return str(config_file)

# Mock patterns for external dependencies
class TestMCPTicketRepository:
    """Test MCP ticket repository with comprehensive mocking"""
    
    def test_find_by_id_success(self, mock_mcp_client, sample_ticket_data):
        """Test successful ticket retrieval by ID"""
        mock_mcp_client.get_ticket.return_value = sample_ticket_data
        repo = MCPTicketRepository(mock_mcp_client)
        
        ticket = repo.find_by_id("T123456")
        
        assert ticket is not None
        assert ticket.id == "T123456"
        mock_mcp_client.get_ticket.assert_called_once_with("T123456")
    
    @patch('ticket_analyzer.repositories.mcp_ticket_repository.logger')
    def test_find_by_id_mcp_error(self, mock_logger, mock_mcp_client):
        """Test MCP error handling with logging verification"""
        mock_mcp_client.get_ticket.side_effect = MCPError("Connection failed")
        repo = MCPTicketRepository(mock_mcp_client)
        
        ticket = repo.find_by_id("T123456")
        
        assert ticket is None
        mock_logger.error.assert_called_once()

# Subprocess mocking for authentication
class TestMidwayAuthenticator:
    """Test Midway authentication with subprocess mocking"""
    
    @patch('subprocess.run')
    def test_is_authenticated_success(self, mock_run):
        """Test successful authentication check"""
        mock_run.return_value = Mock(returncode=0)
        authenticator = MidwayAuthenticator()
        
        result = authenticator._is_authenticated()
        
        assert result is True
        mock_run.assert_called_once_with(
            ["mwinit", "-s"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_perform_authentication_timeout(self, mock_run):
        """Test authentication timeout handling"""
        mock_run.side_effect = subprocess.TimeoutExpired("mwinit", 60)
        authenticator = MidwayAuthenticator()
        
        with pytest.raises(AuthenticationError, match="Authentication timeout"):
            authenticator._perform_authentication()

# Performance testing for large datasets
class TestPerformance:
    """Performance tests for large datasets"""
    
    @pytest.mark.performance
    def test_large_dataset_processing_time(self):
        """Test processing time for large datasets"""
        large_dataset = self._create_large_ticket_dataset(10000)
        service = AnalysisService()
        
        start_time = time.time()
        result = service.analyze_tickets(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert result.ticket_count == 10000
```

### Integration Testing Strategy

```python
# Integration tests for complete workflows
class TestTicketAnalysisIntegration:
    """Integration tests for ticket analysis flow"""
    
    @patch('ticket_analyzer.external.mcp_client.MCPClient')
    @patch('ticket_analyzer.external.auth_service.MidwayAuthenticator')
    def test_full_analysis_flow(self, mock_auth, mock_mcp_client, 
                               sample_ticket_data, tmp_path):
        """Test complete analysis flow from CLI to output"""
        mock_auth.return_value.ensure_authenticated.return_value = None
        mock_mcp_client.return_value.search_tickets.return_value = [sample_ticket_data]
        
        output_file = tmp_path / "results.json"
        
        result = analyze_command(
            format="json",
            output=str(output_file),
            status=["Open"],
            max_results=10
        )
        
        assert result.exit_code == 0
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert "metrics" in data
        assert "total_tickets" in data
        assert data["total_tickets"] == 1
```

## Security Considerations

### Authentication Security

1. **Credential Isolation**: No credentials stored in memory or logs
2. **Subprocess Security**: Secure subprocess execution for mwinit calls with minimal environment
3. **Session Management**: Automatic re-authentication on session expiry with timeout handling
4. **Environment Isolation**: Restricted environment variables for subprocess execution
5. **Timeout Protection**: Signal-based timeout handling to prevent hanging authentication

### Data Security and Sanitization

1. **PII Detection and Removal**: Comprehensive patterns for detecting and sanitizing personally identifiable information
2. **Secure Temporary Files**: Use secure temporary file creation with restricted permissions (0o600)
3. **Input Validation**: Comprehensive validation for all user inputs including SQL injection prevention
4. **Error Message Security**: Sanitized error messages to prevent information leakage
5. **Memory Management**: Secure handling of sensitive data in memory with explicit cleanup

### Implementation Security Patterns

```python
# Comprehensive Data Sanitization
class TicketDataSanitizer:
    """Sanitizer for ticket data to remove sensitive information"""
    
    SENSITIVE_PATTERNS = [
        # Email addresses
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            replacement='[EMAIL_REDACTED]'
        ),
        # Phone numbers
        SanitizationRule(
            pattern=r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            replacement='[PHONE_REDACTED]'
        ),
        # Social Security Numbers
        SanitizationRule(
            pattern=r'\b\d{3}-?\d{2}-?\d{4}\b',
            replacement='[SSN_REDACTED]'
        ),
        # AWS account IDs
        SanitizationRule(
            pattern=r'\b\d{12}\b',
            replacement='[ACCOUNT_REDACTED]'
        ),
        # API keys and tokens
        SanitizationRule(
            pattern=r'\b[A-Za-z0-9+/]{20,}={0,2}\b',
            replacement='[TOKEN_REDACTED]'
        ),
    ]
    
    def sanitize_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ticket data dictionary recursively"""
        sanitized = {}
        for key, value in ticket_data.items():
            if self._is_sensitive_field(key):
                sanitized[key] = "[FIELD_REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_ticket_data(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        return sanitized

# Secure Subprocess Execution
class SecureSubprocessManager:
    """Secure subprocess execution for authentication commands"""
    
    ALLOWED_COMMANDS = {"mwinit", "kinit", "klist"}
    
    @staticmethod
    def execute_auth_command(command: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
        """Execute authentication command securely with validation"""
        # Validate command whitelist
        if command[0] not in SecureSubprocessManager.ALLOWED_COMMANDS:
            raise ValueError(f"Command '{command[0]}' not allowed")
        
        # Validate arguments for injection attempts
        for arg in command[1:]:
            if any(char in arg for char in [';', '&', '|', '`', '$']):
                raise ValueError(f"Potentially dangerous argument: {arg}")
        
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=SecureSubprocessManager._get_secure_env(),
            check=False
        )
    
    @staticmethod
    def _get_secure_env() -> Dict[str, str]:
        """Get minimal secure environment for subprocess"""
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "C"),
            "KRB5_CONFIG": os.environ.get("KRB5_CONFIG", ""),
            "KRB5CCNAME": os.environ.get("KRB5CCNAME", ""),
        }

# Input Validation and SQL Injection Prevention
class InputValidator:
    """Comprehensive input validation for security"""
    
    ALLOWED_PATTERNS = {
        'ticket_id': re.compile(r'^[A-Z]{1,5}-?\d{1,10}$'),
        'username': re.compile(r'^[a-zA-Z0-9._-]{1,50}$'),
        'status': re.compile(r'^[a-zA-Z\s]{1,30}$'),
        'date': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'search_term': re.compile(r'^[a-zA-Z0-9\s._-]{1,100}$'),
    }
    
    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(\\;))",  # Single quotes and semicolons
        r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or
        r"(union(\s|\+)+select)",  # union select
        r"(drop(\s|\+)+table)",  # drop table
    ]
    
    @classmethod
    def validate_input(cls, value: str, input_type: str) -> bool:
        """Validate input against allowed patterns"""
        if input_type not in cls.ALLOWED_PATTERNS:
            raise ValueError(f"Unknown input type: {input_type}")
        
        pattern = cls.ALLOWED_PATTERNS[input_type]
        return bool(pattern.match(value))
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        """Detect potential SQL injection attempts"""
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

# Secure Temporary File Management
class SecureTempFileManager:
    """Secure temporary file management for sensitive data"""
    
    @contextmanager
    def create_secure_temp_file(self, suffix: str = '.tmp', 
                               prefix: str = 'ticket_data_') -> Path:
        """Create secure temporary file with restricted permissions"""
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.chmod(temp_path, 0o600)  # Owner read/write only
            os.close(fd)
            
            temp_file_path = Path(temp_path)
            yield temp_file_path
            
        finally:
            self._secure_delete_file(temp_file_path)
    
    def _secure_delete_file(self, file_path: Path) -> None:
        """Securely delete file by overwriting before removal"""
        if file_path.exists():
            file_size = file_path.stat().st_size
            with open(file_path, 'r+b') as f:
                f.write(os.urandom(file_size))  # Overwrite with random data
                f.flush()
                os.fsync(f.fileno())
            file_path.unlink()
```

### Security Configuration Management

```python
class SecureConfigManager:
    """Secure configuration management with proper file permissions"""
    
    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or Path.home() / ".ticket-analyzer"
        self._config_file = self._config_dir / "auth_config.json"
        self._ensure_secure_permissions()
    
    def _ensure_secure_permissions(self) -> None:
        """Ensure configuration directory has secure permissions"""
        self._config_dir.mkdir(mode=0o700, exist_ok=True)
        if self._config_file.exists():
            self._config_file.chmod(0o600)
    
    def save_config(self, config: AuthenticationConfig) -> None:
        """Save configuration with secure permissions"""
        config_data = {
            'timeout_seconds': config.timeout_seconds,
            'max_retry_attempts': config.max_retry_attempts,
            'check_interval_seconds': config.check_interval_seconds
        }
        
        with open(self._config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        self._config_file.chmod(0o600)  # Ensure secure permissions == 0
    except subprocess.TimeoutExpired:
        logger.error("Authentication timeout")
        return False
    except Exception as e:
        logger.error(f"Authentication error: {type(e).__name__}")
        return False
```

## Performance Considerations

### Data Processing Performance

1. **Pandas Optimization**: Use efficient pandas operations for large datasets
2. **Memory Management**: Process data in chunks for large result sets
3. **Caching Strategy**: Cache frequently accessed configuration and metadata
4. **Lazy Loading**: Load data only when needed

### API Performance

1. **Connection Pooling**: Reuse HTTP connections for MCP calls
2. **Batch Processing**: Group API calls where possible
3. **Rate Limiting**: Respect API rate limits with exponential backoff
4. **Timeout Management**: Appropriate timeouts for different operation types

## MCP Integration Architecture

### Node.js 16 Compatibility for MCP Components

The application integrates with Amazon's Builder MCP which may have Node.js components:

```python
# mcp_client.py - Python wrapper for Node.js MCP components
class MCPClient:
    """Python client for Node.js 16 compatible MCP server"""
    
    def __init__(self):
        self.node_version_check()
        self.mcp_server_path = self.locate_mcp_server()
    
    def node_version_check(self):
        """Verify Node.js 16 compatibility"""
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            version = result.stdout.strip()
            if not version.startswith('v16.'):
                logger.warning(f"Node.js 16 recommended, found: {version}")
        except FileNotFoundError:
            raise ConfigurationError("Node.js 16 required for MCP integration")
    
    def execute_mcp_command(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP command via Node.js subprocess"""
        # Ensures compatibility with Node.js 16 MCP server
        # Uses subprocess to communicate with Node.js components
```

### Python 3.7 Specific Considerations

1. **Import Statements**: Use `from __future__ import annotations` for forward references
2. **Type Hints**: Compatible with Python 3.7 typing module (no union operator `|`)
3. **Dataclasses**: Available in Python 3.7 standard library
4. **f-strings**: Supported in Python 3.7
5. **Subprocess**: Use Python 3.7 compatible subprocess methods

### Dependency Version Constraints

```python
# requirements.txt - Python 3.7 compatible versions
requests>=2.25.0,<3.0.0      # Python 3.7 compatible
pandas>=1.3.0,<2.0.0         # Last version supporting Python 3.7
matplotlib>=3.3.0,<3.6.0     # Python 3.7 compatible
seaborn>=0.11.0,<0.12.0      # Compatible with pandas 1.3.x
jinja2>=3.0.0,<4.0.0         # Python 3.7 compatible
click>=8.0.0,<9.0.0          # Python 3.7 compatible
tqdm>=4.60.0,<5.0.0          # Python 3.7 compatible
colorama>=0.4.0,<1.0.0       # Python 3.7 compatible
pytest>=6.0.0,<7.0.0         # Python 3.7 compatible
```

## Deployment and Configuration

### Runtime Environment Requirements

- **Python**: Exactly Python 3.7 (`python3` command must point to Python 3.7.x)
- **Node.js**: Version 16.x for MCP server components
- **Operating System**: Linux with bash shell
- **Authentication**: Midway authentication tools (`mwinit`) must be available

### Configuration Management

The application supports multiple configuration sources with the following priority:

1. **Command-line arguments** (highest priority)
2. **Configuration files** (config.json, config.ini)
3. **Environment variables**
4. **Default values** (lowest priority)

### Example Configuration Files

```json
// config.json.example
{
  "output_directory": "./reports/",
  "default_days": 30,
  "mcp_timeout": 30,
  "retry_attempts": 3,
  "log_level": "INFO",
  "report_formats": ["cli", "html"],
  "chart_settings": {
    "width": 800,
    "height": 600,
    "dpi": 100
  }
}
```

```ini
# config.ini.example
[general]
output_directory = ./reports/
default_days = 30
log_level = INFO

[mcp]
timeout = 30
retry_attempts = 3

[reporting]
formats = cli,html
include_charts = true
```

### Environment Variables

- `TICKET_ANALYZER_OUTPUT_DIR`: Override default output directory
- `TICKET_ANALYZER_LOG_LEVEL`: Set logging level
- `TICKET_ANALYZER_CONFIG_FILE`: Specify custom configuration file path

## CLI Development Standards

### Click Framework Implementation

The CLI follows Click framework best practices with comprehensive argument validation and color-coded output:

```python
# CLI command structure with Click
import click
from typing import Optional, List

@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """Ticket Analysis CLI Tool with comprehensive ticket analysis capabilities."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config'] = config

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'table']), 
              default='table', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), 
              help='Start date for analysis (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), 
              help='End date for analysis (YYYY-MM-DD)')
@click.option('--status', multiple=True, help='Filter by ticket status')
@click.option('--max-results', type=int, default=1000, help='Maximum results to return')
@click.pass_context
def analyze(ctx: click.Context, format: str, output: Optional[str], 
           start_date: Optional[str], end_date: Optional[str],
           status: tuple, max_results: int) -> None:
    """Analyze ticket data with comprehensive metrics and reporting."""
    
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise click.BadParameter('Start date must be before end date')
    
    # Validate max results
    if max_results <= 0 or max_results > 10000:
        raise click.BadParameter('Max results must be between 1 and 10000')
    
    try:
        # Execute analysis with error handling
        result = execute_analysis(
            format=format,
            output=output,
            start_date=start_date,
            end_date=end_date,
            status=list(status),
            max_results=max_results,
            verbose=ctx.obj['verbose']
        )
        
        success_message(f"Analysis completed successfully. Results: {result}")
        
    except AuthenticationError:
        error_message("Authentication required. Please run 'mwinit' to authenticate.")
        raise click.Abort()
    except DataRetrievalError as e:
        error_message(f"Data retrieval failed: {e}")
        raise click.Abort()
    except Exception as e:
        error_message(f"Analysis failed: {e}")
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()

# Color-coded output functions
def success_message(message: str) -> None:
    """Display success message in green"""
    click.echo(click.style(message, fg='green'))

def error_message(message: str) -> None:
    """Display error message in red"""
    click.echo(click.style(message, fg='red'), err=True)

def info_message(message: str) -> None:
    """Display info message in blue"""
    click.echo(click.style(message, fg='blue'))

def warning_message(message: str) -> None:
    """Display warning message in yellow"""
    click.echo(click.style(message, fg='yellow'))

# Progress indicator implementation
from tqdm import tqdm

def process_with_progress(items: List[Any], description: str) -> List[Any]:
    """Process items with progress bar"""
    results = []
    with tqdm(items, desc=description, unit='item') as pbar:
        for item in pbar:
            result = process_item(item)
            results.append(result)
            pbar.set_postfix({'status': 'processed'})
    return results

# Graceful shutdown handling
import signal
import sys

class GracefulShutdown:
    """Handle graceful shutdown for long-running operations"""
    
    def __init__(self) -> None:
        self.shutdown = False
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)
    
    def _exit_gracefully(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully"""
        self.shutdown = True
        warning_message('\nShutdown requested... cleaning up...')
        sys.exit(0)
```

## Development Workflow Standards

### Git Workflow and Branching Strategy

The project follows a structured Git workflow with conventional commits:

```bash
# Branch naming conventions
feature/ticket-analysis-metrics
bugfix/authentication-timeout
hotfix/security-vulnerability-fix
release/v1.0.0

# Conventional commit format
feat(auth): add Midway authentication support

Implement secure authentication flow with:
- Session management
- Automatic re-authentication
- Timeout handling

Closes #45

fix(cli): resolve argument parsing issue

The --output flag was not properly handling file paths
with spaces. Updated argument parser to handle quoted paths.

Fixes #67
```

### Code Review Requirements

- **Security Review**: All authentication and data handling code requires security review
- **Test Coverage**: New features must include comprehensive tests with 80% minimum coverage
- **Documentation**: All public APIs must have complete docstring documentation
- **Performance**: Large dataset processing must be performance tested
- **Compatibility**: All code must be tested with Python 3.7

### Release Management

```bash
# Semantic versioning strategy
MAJOR.MINOR.PATCH
1.2.3

# Release process
1. Create release branch: release/v1.2.0
2. Update version numbers and CHANGELOG.md
3. Run comprehensive test suite
4. Create pull request for review
5. Merge to main and create tag
6. Deploy with proper rollback procedures
```

## Documentation Standards

### API Documentation Requirements

All functions must include comprehensive docstrings following the established pattern:

```python
def analyze_ticket_metrics(
    tickets: List[Dict[str, Any]], 
    metric_types: Optional[List[str]] = None,
    date_range: Optional[tuple[datetime, datetime]] = None
) -> Dict[str, Any]:
    """Analyze ticket metrics with comprehensive calculations.
    
    This function processes a list of ticket data and calculates various
    metrics including resolution times, status distributions, and trend
    analysis. All sensitive data is automatically sanitized during processing.
    
    Args:
        tickets: List of ticket dictionaries containing ticket data.
            Each ticket must have 'id', 'status', and 'created_date' fields.
        metric_types: Optional list of specific metrics to calculate.
            Available types: ['resolution_time', 'status_distribution', 
            'assignee_workload', 'priority_analysis']. 
        date_range: Optional tuple of (start_date, end_date) to filter
            tickets by creation date.
    
    Returns:
        Dictionary containing calculated metrics with comprehensive structure
        including averages, medians, distributions, and trend analysis.
    
    Raises:
        ValueError: If tickets list is empty or contains invalid data.
        DataProcessingError: If metric calculation fails due to data issues.
        AuthenticationError: If authentication is required but not available.
    
    Example:
        >>> tickets = [{'id': 'T123456', 'status': 'Resolved', ...}]
        >>> result = analyze_ticket_metrics(tickets, ['resolution_time'])
        >>> print(result['metrics']['resolution_time']['average_hours'])
        28.5
    
    Security:
        - All input data is validated and sanitized
        - No sensitive information is logged
        - Memory is cleared after processing sensitive data
    
    Performance:
        - Optimized for datasets up to 100,000 tickets
        - Processing time: ~1-2 seconds per 10,000 tickets
    """
    pass
```

### User Documentation Structure

- **README.md**: Quick start guide with installation and basic usage
- **User Guide**: Comprehensive usage documentation with examples
- **API Documentation**: Complete API reference with examples
- **Troubleshooting Guide**: Common issues and solutions
- **Security Guide**: Security best practices and considerations

This comprehensive design document incorporates all the key patterns, standards, and best practices from the steering documents, ensuring a secure, maintainable, and well-tested ticket analysis CLI application.