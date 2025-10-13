"""Core data models and exceptions for ticket analysis.

This module contains all the core data structures used throughout the application,
including ticket models, analysis results, and custom exception hierarchy.
All models are Python 3.7 compatible using dataclasses and proper type hints.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum


# Enums for ticket properties
class TicketStatus(Enum):
    """Enumeration of possible ticket statuses."""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    PENDING = "Pending"
    ASSIGNED = "Assigned"
    RESEARCHING = "Researching"
    WORK_IN_PROGRESS = "Work In Progress"


class TicketSeverity(Enum):
    """Enumeration of ticket severity levels."""
    SEV_1 = "SEV_1"
    SEV_2 = "SEV_2"
    SEV_2_5 = "SEV_2.5"  # Business hours high severity
    SEV_3 = "SEV_3"
    SEV_4 = "SEV_4"
    SEV_5 = "SEV_5"


# Core data models
@dataclass
class Ticket:
    """Core ticket data model with Python 3.7 compatibility.
    
    Represents a single ticket with all its properties and provides
    helper methods for common operations like resolution time calculation.
    """
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
    
    def is_resolved(self) -> bool:
        """Check if the ticket is resolved."""
        return (self.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] 
                and self.resolved_date is not None)
    
    def resolution_time(self) -> Optional[timedelta]:
        """Calculate resolution time if ticket is resolved."""
        if self.is_resolved() and self.resolved_date:
            return self.resolved_date - self.created_date
        return None
    
    def age(self) -> timedelta:
        """Calculate current age of the ticket."""
        return datetime.now() - self.created_date
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ticket:
        """Create Ticket instance from dictionary data."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TicketStatus(data["status"]),
            severity=TicketSeverity(data.get("severity", "SEV_5")),
            created_date=datetime.fromisoformat(data["created_date"].replace('Z', '+00:00')),
            updated_date=datetime.fromisoformat(data["updated_date"].replace('Z', '+00:00')),
            resolved_date=(
                datetime.fromisoformat(data["resolved_date"].replace('Z', '+00:00'))
                if data.get("resolved_date") else None
            ),
            assignee=data.get("assignee"),
            resolver_group=data.get("resolver_group"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


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


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    format: str = "table"  # 'table', 'json', 'csv', 'html'
    output_path: Optional[str] = None
    include_charts: bool = True
    color_output: bool = True
    template_name: Optional[str] = None
    sanitize_output: bool = True
    max_results_display: int = 100


@dataclass
class AuthConfig:
    """Configuration for authentication settings."""
    timeout_seconds: int = 60
    max_retry_attempts: int = 3
    check_interval_seconds: int = 300  # 5 minutes
    session_duration_hours: int = 8


# Custom Exception Hierarchy
class TicketAnalysisError(Exception):
    """Base exception for all ticket analysis errors.
    
    This is the root exception class that all other custom exceptions
    inherit from. It provides a consistent interface for error handling
    throughout the application.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class AuthenticationError(TicketAnalysisError):
    """Raised when authentication operations fail.
    
    This includes failures in Midway authentication, session timeouts,
    and credential validation errors.
    """
    pass


class ConfigurationError(TicketAnalysisError):
    """Raised when configuration is invalid or missing.
    
    This includes malformed configuration files, missing required settings,
    and invalid configuration values.
    """
    pass


class DataRetrievalError(TicketAnalysisError):
    """Raised when data retrieval operations fail.
    
    This includes MCP connection failures, API errors, network timeouts,
    and data parsing errors.
    """
    pass


class AnalysisError(TicketAnalysisError):
    """Raised when analysis operations fail.
    
    This includes calculation errors, invalid data for analysis,
    and processing failures.
    """
    pass


class ValidationError(TicketAnalysisError):
    """Raised when data validation fails.
    
    This includes input validation errors, data format issues,
    and security validation failures.
    """
    pass


class MCPError(DataRetrievalError):
    """Raised when MCP operations fail."""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operations timeout."""
    pass


class MCPAuthenticationError(MCPError):
    """Raised when MCP authentication fails."""
    pass


class CircuitBreakerOpenError(DataRetrievalError):
    """Raised when circuit breaker is open."""
    pass


class DataProcessingError(AnalysisError):
    """Raised when data processing fails."""
    pass


class ReportGenerationError(TicketAnalysisError):
    """Raised when report generation fails."""
    pass


class SecurityError(TicketAnalysisError):
    """Raised when security violations are detected."""
    pass