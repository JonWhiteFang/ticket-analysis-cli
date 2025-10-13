# Design Patterns

## Repository Pattern for Data Access

### Abstract Repository Interface
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class TicketRepository(ABC):
    """Abstract repository for ticket data access."""
    
    @abstractmethod
    def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Find ticket by ID."""
        pass
    
    @abstractmethod
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets matching criteria."""
        pass
    
    @abstractmethod
    def count_by_status(self, status: str) -> int:
        """Count tickets by status."""
        pass

class MCPTicketRepository(TicketRepository):
    """MCP-based ticket repository implementation."""
    
    def __init__(self, mcp_client: MCPClient) -> None:
        self._client = mcp_client
    
    def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Find ticket by ID using MCP."""
        try:
            data = self._client.get_ticket(ticket_id)
            return self._map_to_ticket(data) if data else None
        except MCPError as e:
            logger.error(f"Failed to retrieve ticket {ticket_id}: {e}")
            return None
    
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets using MCP search."""
        raw_data = self._client.search_tickets(criteria.to_mcp_query())
        return [self._map_to_ticket(item) for item in raw_data]
```

## Strategy Pattern for Analysis Types

### Analysis Strategy Interface
```python
from abc import ABC, abstractmethod

class MetricsCalculator(ABC):
    """Abstract strategy for calculating metrics."""
    
    @abstractmethod
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics from tickets."""
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        pass

class ResolutionTimeCalculator(MetricsCalculator):
    """Strategy for calculating resolution time metrics."""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate resolution time statistics."""
        resolved_tickets = [t for t in tickets if t.is_resolved()]
        if not resolved_tickets:
            return {"avg_resolution_time": 0, "median_resolution_time": 0}
        
        times = [t.resolution_time().total_seconds() for t in resolved_tickets]
        return {
            "avg_resolution_time": sum(times) / len(times),
            "median_resolution_time": sorted(times)[len(times) // 2],
            "total_resolved": len(resolved_tickets)
        }
    
    def get_metric_names(self) -> List[str]:
        return ["avg_resolution_time", "median_resolution_time", "total_resolved"]

class StatusDistributionCalculator(MetricsCalculator):
    """Strategy for calculating status distribution."""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate status distribution."""
        from collections import Counter
        status_counts = Counter(ticket.status for ticket in tickets)
        total = len(tickets)
        
        return {
            "status_counts": dict(status_counts),
            "status_percentages": {
                status: (count / total) * 100 
                for status, count in status_counts.items()
            }
        }
    
    def get_metric_names(self) -> List[str]:
        return ["status_counts", "status_percentages"]

# Strategy context
class AnalysisEngine:
    """Context class that uses different calculation strategies."""
    
    def __init__(self) -> None:
        self._calculators: List[MetricsCalculator] = []
    
    def add_calculator(self, calculator: MetricsCalculator) -> None:
        """Add a metrics calculator strategy."""
        self._calculators.append(calculator)
    
    def analyze(self, tickets: List[Ticket]) -> AnalysisResult:
        """Run analysis using all registered calculators."""
        metrics = {}
        for calculator in self._calculators:
            metrics.update(calculator.calculate(tickets))
        
        return AnalysisResult(metrics=metrics, ticket_count=len(tickets))
```

## Template Method Pattern for Reporting

### Report Template Base Class
```python
from abc import ABC, abstractmethod

class ReportGenerator(ABC):
    """Template method pattern for report generation."""
    
    def generate_report(self, analysis: AnalysisResult) -> str:
        """Template method for generating reports."""
        header = self._generate_header(analysis)
        summary = self._generate_summary(analysis)
        details = self._generate_details(analysis)
        footer = self._generate_footer(analysis)
        
        return self._format_report(header, summary, details, footer)
    
    @abstractmethod
    def _generate_header(self, analysis: AnalysisResult) -> str:
        """Generate report header."""
        pass
    
    @abstractmethod
    def _generate_summary(self, analysis: AnalysisResult) -> str:
        """Generate report summary."""
        pass
    
    @abstractmethod
    def _generate_details(self, analysis: AnalysisResult) -> str:
        """Generate detailed metrics."""
        pass
    
    def _generate_footer(self, analysis: AnalysisResult) -> str:
        """Generate report footer (default implementation)."""
        from datetime import datetime
        return f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    @abstractmethod
    def _format_report(self, header: str, summary: str, 
                      details: str, footer: str) -> str:
        """Format the complete report."""
        pass

class JSONReportGenerator(ReportGenerator):
    """JSON format report generator."""
    
    def _generate_header(self, analysis: AnalysisResult) -> str:
        return f'"report_type": "ticket_analysis"'
    
    def _generate_summary(self, analysis: AnalysisResult) -> str:
        return f'"total_tickets": {analysis.ticket_count}'
    
    def _generate_details(self, analysis: AnalysisResult) -> str:
        import json
        return f'"metrics": {json.dumps(analysis.metrics)}'
    
    def _format_report(self, header: str, summary: str, 
                      details: str, footer: str) -> str:
        return f'{{{header}, {summary}, {details}, "timestamp": "{footer}"}}'
```

## Chain of Responsibility for Configuration

### Configuration Chain
```python
from abc import ABC, abstractmethod
from typing import Optional, Any

class ConfigurationHandler(ABC):
    """Abstract handler in configuration chain."""
    
    def __init__(self) -> None:
        self._next_handler: Optional[ConfigurationHandler] = None
    
    def set_next(self, handler: 'ConfigurationHandler') -> 'ConfigurationHandler':
        """Set the next handler in the chain."""
        self._next_handler = handler
        return handler
    
    def handle(self, key: str) -> Optional[Any]:
        """Handle configuration request."""
        result = self._get_config_value(key)
        if result is not None:
            return result
        
        if self._next_handler:
            return self._next_handler.handle(key)
        
        return None
    
    @abstractmethod
    def _get_config_value(self, key: str) -> Optional[Any]:
        """Get configuration value from this handler."""
        pass

class EnvironmentConfigHandler(ConfigurationHandler):
    """Handler for environment variables."""
    
    def _get_config_value(self, key: str) -> Optional[Any]:
        import os
        return os.getenv(key.upper())

class FileConfigHandler(ConfigurationHandler):
    """Handler for configuration files."""
    
    def __init__(self, config_file: str) -> None:
        super().__init__()
        self._config_file = config_file
        self._config = self._load_config()
    
    def _get_config_value(self, key: str) -> Optional[Any]:
        return self._config.get(key)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        # Implementation depends on file format (JSON, YAML, etc.)
        pass

class DefaultConfigHandler(ConfigurationHandler):
    """Handler for default values."""
    
    def __init__(self, defaults: Dict[str, Any]) -> None:
        super().__init__()
        self._defaults = defaults
    
    def _get_config_value(self, key: str) -> Optional[Any]:
        return self._defaults.get(key)

# Usage
def create_config_chain() -> ConfigurationHandler:
    """Create configuration handler chain."""
    env_handler = EnvironmentConfigHandler()
    file_handler = FileConfigHandler("config.json")
    default_handler = DefaultConfigHandler({
        "output_format": "table",
        "max_results": 100,
        "timeout": 30
    })
    
    env_handler.set_next(file_handler).set_next(default_handler)
    return env_handler
```

## Circuit Breaker Pattern for External Services

### Circuit Breaker Implementation
```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, 
                 timeout: timedelta = timedelta(minutes=1)) -> None:
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED
    
    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (self._last_failure_time and 
                datetime.now() - self._last_failure_time > self._timeout)
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

# Usage with MCP client
class ResilientMCPClient:
    """MCP client with circuit breaker protection."""
    
    def __init__(self, mcp_client: MCPClient) -> None:
        self._client = mcp_client
        self._circuit_breaker = CircuitBreaker()
    
    def search_tickets(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search tickets with circuit breaker protection."""
        return self._circuit_breaker.call(self._client.search_tickets, query)
```