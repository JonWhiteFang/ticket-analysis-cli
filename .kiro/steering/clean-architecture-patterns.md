---
inclusion: fileMatch
fileMatchPattern: '*{service,repository,model,domain}*'
---

# Clean Architecture Patterns

## Layered Architecture Implementation

### Layer Structure
```
CLI Layer (Presentation)
├── commands/
│   ├── analyze.py
│   └── report.py
│
Application Layer (Use Cases)
├── services/
│   ├── analysis_service.py
│   └── report_service.py
│
Domain Layer (Business Logic)
├── models/
│   ├── ticket.py
│   └── analysis_result.py
│
Infrastructure Layer (External Concerns)
├── repositories/
│   ├── mcp_ticket_repository.py
│   └── file_repository.py
└── external/
    ├── mcp_client.py
    └── auth_service.py
```

### Dependency Injection Patterns
```python
from abc import ABC, abstractmethod
from typing import Protocol

class TicketRepository(Protocol):
    """Repository interface for ticket data access."""
    
    def get_tickets(self, filters: Dict[str, Any]) -> List[Ticket]:
        """Retrieve tickets based on filters."""
        ...

class AnalysisService:
    """Application service for ticket analysis."""
    
    def __init__(self, ticket_repo: TicketRepository) -> None:
        self._ticket_repo = ticket_repo
    
    def analyze_tickets(self, criteria: AnalysisCriteria) -> AnalysisResult:
        """Analyze tickets based on criteria."""
        tickets = self._ticket_repo.get_tickets(criteria.filters)
        return self._perform_analysis(tickets)

# Dependency injection container
class Container:
    def __init__(self) -> None:
        self._ticket_repo = MCPTicketRepository()
        self._analysis_service = AnalysisService(self._ticket_repo)
    
    @property
    def analysis_service(self) -> AnalysisService:
        return self._analysis_service
```

### Interface-Based Design
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DataProcessor(ABC):
    """Abstract base class for data processors."""
    
    @abstractmethod
    def process(self, data: List[Dict[str, Any]]) -> ProcessedData:
        """Process raw data into structured format."""
        pass
    
    @abstractmethod
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """Validate input data format."""
        pass

class TicketDataProcessor(DataProcessor):
    """Concrete implementation for ticket data processing."""
    
    def process(self, data: List[Dict[str, Any]]) -> ProcessedData:
        """Process ticket data."""
        validated_data = self._validate_and_clean(data)
        return ProcessedData(validated_data)
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """Validate ticket data structure."""
        required_fields = {'id', 'title', 'status'}
        return all(required_fields.issubset(item.keys()) for item in data)
```

### Single Responsibility Principle
```python
class TicketMetricsCalculator:
    """Responsible only for calculating ticket metrics."""
    
    def calculate_resolution_time(self, tickets: List[Ticket]) -> Dict[str, float]:
        """Calculate average resolution time by category."""
        pass
    
    def calculate_status_distribution(self, tickets: List[Ticket]) -> Dict[str, int]:
        """Calculate ticket status distribution."""
        pass

class TicketDataValidator:
    """Responsible only for validating ticket data."""
    
    def validate_ticket_format(self, ticket_data: Dict[str, Any]) -> bool:
        """Validate individual ticket data format."""
        pass
    
    def sanitize_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ticket data for processing."""
        pass

class TicketReportGenerator:
    """Responsible only for generating reports."""
    
    def generate_summary_report(self, analysis: AnalysisResult) -> str:
        """Generate summary report from analysis results."""
        pass
```

### Separation of Concerns
```python
# Domain Model (Business Logic)
@dataclass
class Ticket:
    id: str
    title: str
    status: str
    created_date: datetime
    resolved_date: Optional[datetime] = None
    
    def is_resolved(self) -> bool:
        """Check if ticket is resolved."""
        return self.status == 'Resolved' and self.resolved_date is not None
    
    def resolution_time(self) -> Optional[timedelta]:
        """Calculate resolution time."""
        if self.is_resolved():
            return self.resolved_date - self.created_date
        return None

# Application Service (Use Case)
class TicketAnalysisUseCase:
    """Use case for analyzing tickets."""
    
    def __init__(self, repo: TicketRepository, calculator: MetricsCalculator) -> None:
        self._repo = repo
        self._calculator = calculator
    
    def execute(self, request: AnalysisRequest) -> AnalysisResponse:
        """Execute ticket analysis use case."""
        tickets = self._repo.find_by_criteria(request.criteria)
        metrics = self._calculator.calculate_metrics(tickets)
        return AnalysisResponse(metrics)

# Infrastructure (External Concerns)
class MCPTicketRepository:
    """MCP-based ticket repository implementation."""
    
    def __init__(self, mcp_client: MCPClient) -> None:
        self._client = mcp_client
    
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets using MCP client."""
        raw_data = self._client.search_tickets(criteria.to_dict())
        return [self._map_to_ticket(item) for item in raw_data]
```

### Module Organization
```python
# models/__init__.py
from .ticket import Ticket
from .analysis_result import AnalysisResult
from .search_criteria import SearchCriteria

__all__ = ['Ticket', 'AnalysisResult', 'SearchCriteria']

# services/__init__.py
from .analysis_service import AnalysisService
from .report_service import ReportService

__all__ = ['AnalysisService', 'ReportService']

# repositories/__init__.py
from .ticket_repository import TicketRepository
from .mcp_ticket_repository import MCPTicketRepository

__all__ = ['TicketRepository', 'MCPTicketRepository']
```