---
inclusion: fileMatch
fileMatchPattern: '*{service,repository,model,domain}*'
---

# Clean Architecture Patterns

## Layer Structure
```
CLI Layer (commands/) → Application Layer (services/) → Domain Layer (models/) → Infrastructure Layer (repositories/, external/)
```

## Dependency Injection
```python
from typing import Protocol

class TicketRepository(Protocol):
    def get_tickets(self, filters: Dict[str, Any]) -> List[Ticket]: ...

class AnalysisService:
    def __init__(self, ticket_repo: TicketRepository) -> None:
        self._ticket_repo = ticket_repo
    
    def analyze_tickets(self, criteria: AnalysisCriteria) -> AnalysisResult:
        tickets = self._ticket_repo.get_tickets(criteria.filters)
        return self._perform_analysis(tickets)
```

## Single Responsibility Classes
```python
class TicketMetricsCalculator:
    """Only calculates metrics."""
    def calculate_resolution_time(self, tickets: List[Ticket]) -> Dict[str, float]: ...

class TicketDataValidator:
    """Only validates data."""
    def validate_ticket_format(self, ticket_data: Dict[str, Any]) -> bool: ...

class TicketReportGenerator:
    """Only generates reports."""
    def generate_summary_report(self, analysis: AnalysisResult) -> str: ...
```

## Domain Model Example
```python
@dataclass
class Ticket:
    id: str
    title: str
    status: str
    created_date: datetime
    resolved_date: Optional[datetime] = None
    
    def is_resolved(self) -> bool:
        return self.status == 'Resolved' and self.resolved_date is not None
    
    def resolution_time(self) -> Optional[timedelta]:
        if self.is_resolved():
            return self.resolved_date - self.created_date
        return None
```