# Design Document

## Overview

The Ticket Analysis CLI Application is designed as a modular Python application that follows clean architecture principles. The system integrates with Amazon's internal ticketing infrastructure through the Builder MCP (Model Context Protocol) to provide comprehensive ticket analysis and reporting capabilities. The architecture emphasizes security, testability, and maintainability while ensuring strict compatibility with Python 3.7 and Node.js 16 for any JavaScript components.

### Version Compatibility Requirements

- **Python 3.7**: All Python code must be compatible with Python 3.7 syntax and standard library
- **Node.js 16**: Any JavaScript components or MCP integrations must support Node.js 16
- **Dependency Constraints**: All dependencies must support the target Python and Node.js versions

## Architecture

The application follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface Layer                      │
│                     (main.py, Click)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Application Layer                           │
│              (Orchestration & Workflow)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Service Layer                              │
│    ┌─────────────┬─────────────┬─────────────┬─────────────┐│
│    │    Auth     │    Data     │  Analysis   │  Reporting  ││
│    │   Service   │  Retrieval  │   Service   │   Service   ││
│    │             │   Service   │             │             ││
│    └─────────────┴─────────────┴─────────────┴─────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Infrastructure Layer                         │
│         (MCP Client, File System, Configuration)           │
└─────────────────────────────────────────────────────────────┘
```

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

**Design Pattern:** Adapter Pattern for external authentication system integration

```python
# midway_auth.py
class MidwayAuthenticator(AuthenticationInterface):
    """Handles Midway authentication via subprocess calls"""
    
    def __init__(self):
        self._authenticated = False
        self._auth_timestamp = None
        self._auth_timeout = 3600  # 1 hour
    
    def authenticate(self) -> bool:
        """Execute mwinit subprocess and validate authentication"""
        # Implementation uses subprocess.run() with security considerations
        # Never stores or logs credentials
        # Validates authentication success through return codes
        
    def is_authenticated(self) -> bool:
        """Check authentication status with timeout consideration"""
        # Checks both authentication flag and timestamp
        # Automatically re-authenticates if expired
```

### Data Retrieval Module (data_retrieval/)

**Design Pattern:** Repository Pattern with Circuit Breaker for resilience

```python
# mcp_ticket_retriever.py
class MCPTicketRetriever(DataRetrievalInterface):
    """Handles ticket data retrieval via Builder MCP"""
    
    def __init__(self, auth_service: AuthenticationInterface, config: ConfigurationInterface):
        self.auth_service = auth_service
        self.config = config
        self.circuit_breaker = CircuitBreaker()
        self.retry_strategy = ExponentialBackoffWithJitter()
    
    def search_tickets(self, query: str, date_range: tuple) -> List[Dict[str, Any]]:
        """Search tickets with full Lucene query support"""
        # Implements TicketingReadActions integration
        # Handles pagination for large result sets
        # Applies exponential backoff with jitter for rate limiting
        
    def get_ticket_details(self, ticket_id: str) -> Dict[str, Any]:
        """Retrieve detailed ticket information"""
        # Uses get-ticket action from TicketingReadActions
        # Includes error handling for missing or inaccessible tickets
```

### Analysis Module (analysis/)

**Design Pattern:** Strategy Pattern for different analysis types

```python
# ticket_analyzer.py
class TicketAnalyzer(AnalysisInterface):
    """Performs ticket data analysis using pandas"""
    
    def __init__(self):
        self.metrics_calculators = {
            'resolution_time': ResolutionTimeCalculator(),
            'volume_trends': VolumeTracker(),
            'severity_distribution': SeverityAnalyzer(),
            'team_performance': TeamPerformanceAnalyzer()
        }
    
    def calculate_metrics(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive metrics from ticket data"""
        # Converts ticket data to pandas DataFrame
        # Applies various metric calculations
        # Handles edge cases (empty data, missing fields)
        
    def generate_trends(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trend analysis with time-series data"""
        # Creates time-series analysis
        # Identifies patterns and anomalies
        # Generates statistical summaries
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

### Test Coverage Requirements

- **Core Modules**: Minimum 80% code coverage
- **Critical Paths**: 100% coverage for authentication and data retrieval
- **Error Scenarios**: All custom exceptions must be tested
- **CLI Interface**: Integration tests for all command combinations

## Security Considerations

### Authentication Security

1. **Credential Isolation**: No credentials stored in memory or logs
2. **Subprocess Security**: Secure subprocess execution for mwinit calls
3. **Session Management**: Automatic re-authentication on session expiry

### Data Security

1. **Data Sanitization**: Remove sensitive information from logs and outputs
2. **Secure Temporary Files**: Use secure temporary file creation for sensitive data
3. **Input Validation**: Validate all user inputs and API responses
4. **Error Message Security**: Prevent information leakage through error messages

### Implementation Security

```python
# Secure subprocess execution
def execute_mwinit():
    """Securely execute mwinit command"""
    try:
        result = subprocess.run(
            ['mwinit', '-o'],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        # Never log the output which may contain sensitive data
        return result.returncode == 0
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