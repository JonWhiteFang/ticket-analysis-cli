"""Ticket data models with Python 3.7 compatibility.

This module contains the core Ticket model and related enums for representing
ticket data throughout the application. All models use dataclasses and proper
type hints for Python 3.7 compatibility.
"""

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
    
    Attributes:
        id: Unique ticket identifier
        title: Ticket title/summary
        description: Detailed ticket description
        status: Current ticket status
        severity: Ticket severity level
        created_date: When the ticket was created
        updated_date: When the ticket was last updated
        resolved_date: When the ticket was resolved (if applicable)
        assignee: Current assignee username
        resolver_group: Resolver group responsible for the ticket
        tags: List of tags associated with the ticket
        metadata: Additional metadata as key-value pairs
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
        """Check if the ticket is resolved.
        
        A ticket is considered resolved if its status is either RESOLVED or CLOSED
        and it has a resolved_date set.
        
        Returns:
            True if ticket is resolved, False otherwise.
        """
        return (self.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] 
                and self.resolved_date is not None)
    
    def resolution_time(self) -> Optional[timedelta]:
        """Calculate resolution time if ticket is resolved.
        
        Returns the time difference between creation and resolution dates.
        Only returns a value if the ticket is actually resolved.
        
        Returns:
            Time delta between creation and resolution, or None if not resolved.
        """
        if self.is_resolved() and self.resolved_date:
            return self.resolved_date - self.created_date
        return None
    
    def age(self) -> timedelta:
        """Calculate current age of the ticket.
        
        Returns the time difference between creation date and current time.
        
        Returns:
            Time delta representing the ticket's age.
        """
        return datetime.now() - self.created_date
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ticket:
        """Create Ticket instance from dictionary data.
        
        Converts raw dictionary data (typically from API responses) into
        a properly typed Ticket instance with validation.
        
        Args:
            data: Dictionary containing ticket data with required fields.
            
        Returns:
            New Ticket instance created from the data.
            
        Raises:
            KeyError: If required fields are missing from data.
            ValueError: If enum values are invalid.
        """
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TicketStatus(data["status"]),
            severity=TicketSeverity(data.get("severity", "SEV_5")),
            created_date=cls._parse_datetime(data["created_date"]),
            updated_date=cls._parse_datetime(data["updated_date"]),
            resolved_date=(
                cls._parse_datetime(data["resolved_date"])
                if data.get("resolved_date") else None
            ),
            assignee=data.get("assignee"),
            resolver_group=data.get("resolver_group"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
    
    @staticmethod
    def _parse_datetime(date_str: str) -> datetime:
        """Parse datetime string handling various formats.
        
        Args:
            date_str: ISO format datetime string.
            
        Returns:
            Parsed datetime object.
        """
        # Handle ISO format with 'Z' suffix
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(date_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary representation.
        
        Returns:
            Dictionary representation of the ticket.
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "severity": self.severity.value,
            "created_date": self.created_date.isoformat(),
            "updated_date": self.updated_date.isoformat(),
            "resolved_date": self.resolved_date.isoformat() if self.resolved_date else None,
            "assignee": self.assignee,
            "resolver_group": self.resolver_group,
            "tags": self.tags,
            "metadata": self.metadata
        }