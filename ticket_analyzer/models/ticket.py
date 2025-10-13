"""Ticket data model and related enums."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum


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