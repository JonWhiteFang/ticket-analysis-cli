# ADR-003: Implement Strategy Pattern for Analysis

## Status
Accepted

## Context

The Ticket Analysis CLI needs to support multiple types of analysis calculations:
- Resolution time metrics (average, median, percentiles)
- Status distribution analysis
- Team performance metrics
- SLA compliance tracking
- Custom business-specific calculations

We need an extensible system that allows:
- Adding new analysis types without modifying existing code
- Combining multiple analysis types in a single run
- Custom analysis implementations for specific teams or use cases
- Easy testing of individual analysis components

We evaluated several design patterns:
1. **Single Analysis Class**: One class with methods for all analysis types
2. **Strategy Pattern**: Separate strategy classes for each analysis type
3. **Plugin Architecture**: Dynamic loading of analysis modules
4. **Template Method**: Base class with overridable analysis steps

## Decision

We will implement the Strategy Pattern for analysis calculations with the following design:

```python
# Abstract strategy interface
class MetricsCalculator(ABC):
    @abstractmethod
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics from ticket data."""
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        pass

# Concrete strategy implementations
class ResolutionTimeCalculator(MetricsCalculator):
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        # Implementation for resolution time metrics
        pass

class StatusDistributionCalculator(MetricsCalculator):
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        # Implementation for status distribution
        pass

# Context class that uses strategies
class AnalysisEngine:
    def __init__(self):
        self._calculators: List[MetricsCalculator] = []
    
    def add_calculator(self, calculator: MetricsCalculator) -> None:
        self._calculators.append(calculator)
    
    def analyze(self, tickets: List[Ticket]) -> AnalysisResult:
        metrics = {}
        for calculator in self._calculators:
            metrics.update(calculator.calculate(tickets))
        return AnalysisResult(metrics=metrics)
```

## Consequences

### Positive
- **Extensibility**: New analysis types can be added without modifying existing code
- **Single Responsibility**: Each calculator has one focused purpose
- **Testability**: Individual calculators can be tested in isolation
- **Composability**: Multiple calculators can be combined for comprehensive analysis
- **Maintainability**: Changes to one analysis type don't affect others
- **Reusability**: Calculators can be reused across different contexts
- **Open/Closed Principle**: Open for extension, closed for modification

### Negative
- **Increased Complexity**: More classes and interfaces to manage
- **Potential Over-Engineering**: May be overkill for simple analysis needs
- **Interface Overhead**: Need to maintain consistent interfaces across strategies
- **Discovery Complexity**: Need mechanism to discover and register calculators

## Implementation Notes

### Core Calculator Implementations

**Resolution Time Calculator**
```python
class ResolutionTimeCalculator(MetricsCalculator):
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        resolved_tickets = [t for t in tickets if t.is_resolved()]
        
        if not resolved_tickets:
            return self._empty_metrics()
        
        times = [t.resolution_time().total_seconds() / 3600 for t in resolved_tickets]
        
        return {
            "avg_resolution_time_hours": sum(times) / len(times),
            "median_resolution_time_hours": sorted(times)[len(times) // 2],
            "p90_resolution_time_hours": sorted(times)[int(len(times) * 0.9)],
            "total_resolved": len(resolved_tickets)
        }
```

**Status Distribution Calculator**
```python
class StatusDistributionCalculator(MetricsCalculator):
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        from collections import Counter
        
        status_counts = Counter(ticket.status.value for ticket in tickets)
        total = len(tickets)
        
        return {
            "status_counts": dict(status_counts),
            "status_percentages": {
                status: (count / total) * 100 
                for status, count in status_counts.items()
            }
        }
```

### Registration and Discovery

**Default Calculator Registration**
```python
def create_default_analysis_engine() -> AnalysisEngine:
    """Create analysis engine with default calculators."""
    engine = AnalysisEngine()
    
    # Register default calculators
    engine.add_calculator(ResolutionTimeCalculator())
    engine.add_calculator(StatusDistributionCalculator())
    engine.add_calculator(VolumeAnalyzer())
    engine.add_calculator(SeverityAnalyzer())
    
    return engine
```

**Dynamic Calculator Discovery**
```python
def discover_calculators(package_name: str) -> List[MetricsCalculator]:
    """Discover calculator implementations in a package."""
    calculators = []
    
    # Import package and find MetricsCalculator subclasses
    import importlib
    package = importlib.import_module(package_name)
    
    for attr_name in dir(package):
        attr = getattr(package, attr_name)
        if (isinstance(attr, type) and 
            issubclass(attr, MetricsCalculator) and 
            attr != MetricsCalculator):
            calculators.append(attr())
    
    return calculators
```

### Error Handling Strategy

**Graceful Degradation**: If one calculator fails, others continue
```python
def analyze(self, tickets: List[Ticket]) -> AnalysisResult:
    metrics = {}
    errors = []
    
    for calculator in self._calculators:
        try:
            calculator_metrics = calculator.calculate(tickets)
            metrics.update(calculator_metrics)
        except Exception as e:
            error_msg = f"Calculator {calculator.__class__.__name__} failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            # Continue with other calculators
    
    return AnalysisResult(
        metrics=metrics,
        errors=errors,
        ticket_count=len(tickets)
    )
```

### Configuration Support

**Calculator Configuration**
```python
class ConfigurableCalculator(MetricsCalculator):
    def __init__(self, config: Dict[str, Any]):
        self._config = config
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        # Use configuration to customize behavior
        threshold = self._config.get('threshold', 24)
        # Implementation using threshold
        pass

# Usage
sla_config = {"sev1_hours": 4, "sev2_hours": 24, "sev3_hours": 72}
sla_calculator = SLAComplianceCalculator(sla_config)
engine.add_calculator(sla_calculator)
```

### Testing Strategy

**Unit Testing Individual Calculators**
```python
class TestResolutionTimeCalculator:
    def test_calculate_with_resolved_tickets(self):
        calculator = ResolutionTimeCalculator()
        tickets = [create_resolved_ticket(hours=24), create_resolved_ticket(hours=48)]
        
        result = calculator.calculate(tickets)
        
        assert result["avg_resolution_time_hours"] == 36
        assert result["total_resolved"] == 2
    
    def test_calculate_with_no_resolved_tickets(self):
        calculator = ResolutionTimeCalculator()
        tickets = [create_open_ticket(), create_open_ticket()]
        
        result = calculator.calculate(tickets)
        
        assert result["avg_resolution_time_hours"] == 0
        assert result["total_resolved"] == 0
```

**Integration Testing Analysis Engine**
```python
class TestAnalysisEngine:
    def test_multiple_calculators(self):
        engine = AnalysisEngine()
        engine.add_calculator(ResolutionTimeCalculator())
        engine.add_calculator(StatusDistributionCalculator())
        
        tickets = [create_sample_ticket(), create_sample_ticket()]
        result = engine.analyze(tickets)
        
        assert "avg_resolution_time_hours" in result.metrics
        assert "status_counts" in result.metrics
```

### Extension Examples

**Custom Team Metrics Calculator**
```python
class TeamProductivityCalculator(MetricsCalculator):
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        # Group by assignee
        by_assignee = {}
        for ticket in tickets:
            assignee = ticket.assignee or "Unassigned"
            if assignee not in by_assignee:
                by_assignee[assignee] = []
            by_assignee[assignee].append(ticket)
        
        # Calculate productivity metrics
        productivity = {}
        for assignee, assignee_tickets in by_assignee.items():
            resolved_count = sum(1 for t in assignee_tickets if t.is_resolved())
            productivity[assignee] = {
                "total_tickets": len(assignee_tickets),
                "resolved_tickets": resolved_count,
                "resolution_rate": resolved_count / len(assignee_tickets)
            }
        
        return {"team_productivity": productivity}
```

## Date
2024-01-17

## Participants
- Development Team
- Product Owner
- QA Team