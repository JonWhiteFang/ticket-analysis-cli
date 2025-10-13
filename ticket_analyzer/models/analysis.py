"""Analysis-related data models."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .ticket import TicketStatus, TicketSeverity


@dataclass
class SearchCriteria:
    """Search criteria for ticket queries."""
    status: Optional[List[TicketStatus]] = None
    severity: Optional[List[TicketSeverity]] = None
    assignee: Optional[str] = None
    resolver_group: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    tags: Optional[List[str]] = None
    max_results: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search criteria to dictionary for API calls."""
        criteria = {}
        
        if self.status:
            criteria["status"] = [s.value for s in self.status]
        if self.severity:
            criteria["severity"] = [s.value for s in self.severity]
        if self.assignee:
            criteria["assignee"] = self.assignee
        if self.resolver_group:
            criteria["resolver_group"] = self.resolver_group
        if self.created_after:
            criteria["created_after"] = self.created_after.isoformat()
        if self.created_before:
            criteria["created_before"] = self.created_before.isoformat()
        if self.tags:
            criteria["tags"] = self.tags
        
        criteria["max_results"] = self.max_results
        return criteria


@dataclass
class AnalysisResult:
    """Results from ticket analysis operations."""
    metrics: Dict[str, Any]
    trends: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    ticket_count: int = 0
    date_range: Optional[tuple] = None
    
    def get_metric(self, metric_name: str, default: Any = None) -> Any:
        """Get a specific metric value."""
        return self.metrics.get(metric_name, default)
    
    def has_metric(self, metric_name: str) -> bool:
        """Check if a specific metric exists."""
        return metric_name in self.metrics