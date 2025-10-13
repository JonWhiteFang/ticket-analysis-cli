"""Comprehensive tests for ticket data models.

This module contains unit tests for the Ticket model, TicketStatus enum,
and TicketSeverity enum, covering dataclass instantiation, validation,
edge cases, and helper methods.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity


class TestTicketStatus:
    """Test cases for TicketStatus enum."""
    
    def test_enum_values(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = {
            "Open", "In Progress", "Resolved", "Closed", 
            "Pending", "Assigned", "Researching", "Work In Progress"
        }
        actual_values = {status.value for status in TicketStatus}
        assert actual_values == expected_values
    
    def test_enum_creation_from_string(self) -> None:
        """Test creating enum instances from string values."""
        assert TicketStatus("Open") == TicketStatus.OPEN
        assert TicketStatus("In Progress") == TicketStatus.IN_PROGRESS
        assert TicketStatus("Resolved") == TicketStatus.RESOLVED
        assert TicketStatus("Closed") == TicketStatus.CLOSED
    
    def test_enum_invalid_value(self) -> None:
        """Test that invalid enum values raise ValueError."""
        with pytest.raises(ValueError, match="'Invalid Status' is not a valid TicketStatus"):
            TicketStatus("Invalid Status")
    
    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            TicketStatus("open")  # lowercase should fail
        
        with pytest.raises(ValueError):
            TicketStatus("OPEN")  # uppercase should fail
    
    def test_enum_string_representation(self) -> None:
        """Test string representation of enum values."""
        assert str(TicketStatus.OPEN) == "TicketStatus.OPEN"
        assert TicketStatus.OPEN.value == "Open"
    
    def test_enum_equality(self) -> None:
        """Test enum equality comparisons."""
        status1 = TicketStatus.OPEN
        status2 = TicketStatus.OPEN
        status3 = TicketStatus.CLOSED
        
        assert status1 == status2
        assert status1 != status3
        assert status1 is status2  # Same enum instance


class TestTicketSeverity:
    """Test cases for TicketSeverity enum."""
    
    def test_enum_values(self) -> None:
        """Test that all expected severity values exist."""
        expected_values = {"SEV_1", "SEV_2", "SEV_2.5", "SEV_3", "SEV_4", "SEV_5"}
        actual_values = {severity.value for severity in TicketSeverity}
        assert actual_values == expected_values
    
    def test_enum_creation_from_string(self) -> None:
        """Test creating severity enum from string values."""
        assert TicketSeverity("SEV_1") == TicketSeverity.SEV_1
        assert TicketSeverity("SEV_2") == TicketSeverity.SEV_2
        assert TicketSeverity("SEV_2.5") == TicketSeverity.SEV_2_5
        assert TicketSeverity("SEV_3") == TicketSeverity.SEV_3
        assert TicketSeverity("SEV_4") == TicketSeverity.SEV_4
        assert TicketSeverity("SEV_5") == TicketSeverity.SEV_5
    
    def test_enum_invalid_severity(self) -> None:
        """Test that invalid severity values raise ValueError."""
        with pytest.raises(ValueError, match="'SEV_0' is not a valid TicketSeverity"):
            TicketSeverity("SEV_0")
        
        with pytest.raises(ValueError, match="'SEV_6' is not a valid TicketSeverity"):
            TicketSeverity("SEV_6")
    
    def test_business_hours_severity(self) -> None:
        """Test the special SEV_2.5 business hours severity."""
        sev_2_5 = TicketSeverity.SEV_2_5
        assert sev_2_5.value == "SEV_2.5"
        assert sev_2_5 != TicketSeverity.SEV_2
        assert sev_2_5 != TicketSeverity.SEV_3


class TestTicket:
    """Test cases for Ticket dataclass."""
    
    @pytest.fixture
    def sample_ticket_data(self) -> Dict[str, Any]:
        """Provide sample ticket data for testing."""
        return {
            "id": "T123456",
            "title": "Test ticket",
            "description": "This is a test ticket description",
            "status": "Open",
            "severity": "SEV_3",
            "created_date": "2024-01-01T10:00:00Z",
            "updated_date": "2024-01-01T10:30:00Z",
            "assignee": "testuser",
            "resolver_group": "Test Team",
            "tags": ["test", "sample"],
            "metadata": {"priority": "normal", "category": "bug"}
        }
    
    @pytest.fixture
    def resolved_ticket_data(self) -> Dict[str, Any]:
        """Provide resolved ticket data for testing."""
        return {
            "id": "T789012",
            "title": "Resolved ticket",
            "description": "This ticket has been resolved",
            "status": "Resolved",
            "severity": "SEV_4",
            "created_date": "2024-01-01T09:00:00Z",
            "updated_date": "2024-01-01T15:00:00Z",
            "resolved_date": "2024-01-01T15:00:00Z",
            "assignee": "resolver",
            "resolver_group": "Resolution Team"
        }
    
    def test_ticket_creation_with_required_fields(self) -> None:
        """Test ticket creation with only required fields."""
        created_date = datetime(2024, 1, 1, 10, 0, 0)
        updated_date = datetime(2024, 1, 1, 10, 30, 0)
        
        ticket = Ticket(
            id="T123456",
            title="Test ticket",
            description="Test description",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=created_date,
            updated_date=updated_date
        )
        
        assert ticket.id == "T123456"
        assert ticket.title == "Test ticket"
        assert ticket.description == "Test description"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.severity == TicketSeverity.SEV_3
        assert ticket.created_date == created_date
        assert ticket.updated_date == updated_date
        assert ticket.resolved_date is None
        assert ticket.assignee is None
        assert ticket.resolver_group is None
        assert ticket.tags == []
        assert ticket.metadata == {}
    
    def test_ticket_creation_with_all_fields(self) -> None:
        """Test ticket creation with all fields populated."""
        created_date = datetime(2024, 1, 1, 10, 0, 0)
        updated_date = datetime(2024, 1, 1, 10, 30, 0)
        resolved_date = datetime(2024, 1, 1, 15, 0, 0)
        
        ticket = Ticket(
            id="T123456",
            title="Complete ticket",
            description="Complete description",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_2,
            created_date=created_date,
            updated_date=updated_date,
            resolved_date=resolved_date,
            assignee="testuser",
            resolver_group="Test Team",
            tags=["urgent", "bug"],
            metadata={"priority": "high", "component": "auth"}
        )
        
        assert ticket.resolved_date == resolved_date
        assert ticket.assignee == "testuser"
        assert ticket.resolver_group == "Test Team"
        assert ticket.tags == ["urgent", "bug"]
        assert ticket.metadata == {"priority": "high", "component": "auth"}
    
    def test_is_resolved_when_status_resolved_with_date(self) -> None:
        """Test is_resolved returns True for resolved tickets with resolved_date."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            resolved_date=datetime.now()
        )
        assert ticket.is_resolved() is True
    
    def test_is_resolved_when_status_closed_with_date(self) -> None:
        """Test is_resolved returns True for closed tickets with resolved_date."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.CLOSED,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            resolved_date=datetime.now()
        )
        assert ticket.is_resolved() is True
    
    def test_is_resolved_when_status_resolved_without_date(self) -> None:
        """Test is_resolved returns False for resolved status without resolved_date."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            resolved_date=None
        )
        assert ticket.is_resolved() is False
    
    def test_is_resolved_when_status_open(self) -> None:
        """Test is_resolved returns False for open tickets."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        assert ticket.is_resolved() is False
    
    def test_resolution_time_calculation(self) -> None:
        """Test resolution time calculation for resolved tickets."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        resolved = datetime(2024, 1, 2, 14, 30, 0)
        
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_3,
            created_date=created,
            updated_date=resolved,
            resolved_date=resolved
        )
        
        expected_time = timedelta(days=1, hours=4, minutes=30)
        assert ticket.resolution_time() == expected_time
    
    def test_resolution_time_for_unresolved_ticket(self) -> None:
        """Test resolution time returns None for unresolved tickets."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        assert ticket.resolution_time() is None
    
    def test_resolution_time_for_resolved_status_without_date(self) -> None:
        """Test resolution time returns None when status is resolved but no date."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            resolved_date=None
        )
        assert ticket.resolution_time() is None
    
    def test_age_calculation(self) -> None:
        """Test ticket age calculation."""
        # Create ticket 2 hours ago
        created_date = datetime.now() - timedelta(hours=2)
        
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=created_date,
            updated_date=datetime.now()
        )
        
        age = ticket.age()
        # Age should be approximately 2 hours (allow some tolerance for test execution time)
        assert timedelta(hours=1, minutes=59) <= age <= timedelta(hours=2, minutes=1)
    
    def test_from_dict_with_complete_data(self, sample_ticket_data: Dict[str, Any]) -> None:
        """Test creating ticket from complete dictionary data."""
        ticket = Ticket.from_dict(sample_ticket_data)
        
        assert ticket.id == "T123456"
        assert ticket.title == "Test ticket"
        assert ticket.description == "This is a test ticket description"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.severity == TicketSeverity.SEV_3
        assert ticket.assignee == "testuser"
        assert ticket.resolver_group == "Test Team"
        assert ticket.tags == ["test", "sample"]
        assert ticket.metadata == {"priority": "normal", "category": "bug"}
    
    def test_from_dict_with_minimal_data(self) -> None:
        """Test creating ticket from minimal dictionary data."""
        minimal_data = {
            "id": "T123",
            "title": "Minimal ticket",
            "status": "Open",
            "created_date": "2024-01-01T10:00:00Z",
            "updated_date": "2024-01-01T10:00:00Z"
        }
        
        ticket = Ticket.from_dict(minimal_data)
        
        assert ticket.id == "T123"
        assert ticket.title == "Minimal ticket"
        assert ticket.description == ""  # Default empty string
        assert ticket.status == TicketStatus.OPEN
        assert ticket.severity == TicketSeverity.SEV_5  # Default severity
        assert ticket.assignee is None
        assert ticket.resolver_group is None
        assert ticket.tags == []
        assert ticket.metadata == {}
    
    def test_from_dict_missing_required_field(self) -> None:
        """Test that missing required fields raise KeyError."""
        incomplete_data = {
            "title": "Incomplete ticket",
            "status": "Open"
            # Missing id, created_date, updated_date
        }
        
        with pytest.raises(KeyError):
            Ticket.from_dict(incomplete_data)
    
    def test_from_dict_invalid_status(self) -> None:
        """Test that invalid status values raise ValueError."""
        invalid_data = {
            "id": "T123",
            "title": "Invalid ticket",
            "status": "Invalid Status",
            "created_date": "2024-01-01T10:00:00Z",
            "updated_date": "2024-01-01T10:00:00Z"
        }
        
        with pytest.raises(ValueError):
            Ticket.from_dict(invalid_data)
    
    def test_from_dict_invalid_severity(self) -> None:
        """Test that invalid severity values raise ValueError."""
        invalid_data = {
            "id": "T123",
            "title": "Invalid ticket",
            "status": "Open",
            "severity": "SEV_INVALID",
            "created_date": "2024-01-01T10:00:00Z",
            "updated_date": "2024-01-01T10:00:00Z"
        }
        
        with pytest.raises(ValueError):
            Ticket.from_dict(invalid_data)
    
    def test_parse_datetime_iso_format(self) -> None:
        """Test parsing ISO format datetime strings."""
        # Test with Z suffix
        dt1 = Ticket._parse_datetime("2024-01-01T10:00:00Z")
        expected1 = datetime.fromisoformat("2024-01-01T10:00:00+00:00")
        assert dt1 == expected1
        
        # Test without Z suffix
        dt2 = Ticket._parse_datetime("2024-01-01T10:00:00")
        expected2 = datetime.fromisoformat("2024-01-01T10:00:00")
        assert dt2 == expected2
        
        # Test with timezone offset
        dt3 = Ticket._parse_datetime("2024-01-01T10:00:00+05:00")
        expected3 = datetime.fromisoformat("2024-01-01T10:00:00+05:00")
        assert dt3 == expected3
    
    def test_parse_datetime_invalid_format(self) -> None:
        """Test that invalid datetime formats raise ValueError."""
        with pytest.raises(ValueError):
            Ticket._parse_datetime("invalid-date")
        
        with pytest.raises(ValueError):
            Ticket._parse_datetime("2024-13-01T10:00:00Z")  # Invalid month
    
    def test_to_dict_conversion(self) -> None:
        """Test converting ticket to dictionary representation."""
        created_date = datetime(2024, 1, 1, 10, 0, 0)
        updated_date = datetime(2024, 1, 1, 10, 30, 0)
        resolved_date = datetime(2024, 1, 1, 15, 0, 0)
        
        ticket = Ticket(
            id="T123456",
            title="Test ticket",
            description="Test description",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_2,
            created_date=created_date,
            updated_date=updated_date,
            resolved_date=resolved_date,
            assignee="testuser",
            resolver_group="Test Team",
            tags=["test", "resolved"],
            metadata={"priority": "high"}
        )
        
        result = ticket.to_dict()
        
        expected = {
            "id": "T123456",
            "title": "Test ticket",
            "description": "Test description",
            "status": "Resolved",
            "severity": "SEV_2",
            "created_date": "2024-01-01T10:00:00",
            "updated_date": "2024-01-01T10:30:00",
            "resolved_date": "2024-01-01T15:00:00",
            "assignee": "testuser",
            "resolver_group": "Test Team",
            "tags": ["test", "resolved"],
            "metadata": {"priority": "high"}
        }
        
        assert result == expected
    
    def test_to_dict_with_none_resolved_date(self) -> None:
        """Test to_dict with None resolved_date."""
        ticket = Ticket(
            id="T123",
            title="Open ticket",
            description="Still open",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime(2024, 1, 1, 10, 0, 0),
            updated_date=datetime(2024, 1, 1, 10, 30, 0)
        )
        
        result = ticket.to_dict()
        assert result["resolved_date"] is None
    
    def test_dataclass_field_defaults(self) -> None:
        """Test that dataclass fields have correct default values."""
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        # Test default values
        assert ticket.resolved_date is None
        assert ticket.assignee is None
        assert ticket.resolver_group is None
        assert ticket.tags == []
        assert ticket.metadata == {}
        
        # Test that default collections are independent instances
        ticket2 = Ticket(
            id="T456",
            title="Test2",
            description="Test2",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        ticket.tags.append("test")
        ticket.metadata["key"] = "value"
        
        # ticket2 should not be affected
        assert ticket2.tags == []
        assert ticket2.metadata == {}
    
    def test_ticket_equality(self) -> None:
        """Test ticket equality comparison."""
        created_date = datetime(2024, 1, 1, 10, 0, 0)
        updated_date = datetime(2024, 1, 1, 10, 30, 0)
        
        ticket1 = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=created_date,
            updated_date=updated_date
        )
        
        ticket2 = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=created_date,
            updated_date=updated_date
        )
        
        ticket3 = Ticket(
            id="T456",  # Different ID
            title="Test",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=created_date,
            updated_date=updated_date
        )
        
        assert ticket1 == ticket2  # Same data
        assert ticket1 != ticket3  # Different ID
    
    def test_ticket_string_representation(self) -> None:
        """Test ticket string representation."""
        ticket = Ticket(
            id="T123456",
            title="Test ticket",
            description="Test description",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime(2024, 1, 1, 10, 0, 0),
            updated_date=datetime(2024, 1, 1, 10, 30, 0)
        )
        
        str_repr = str(ticket)
        assert "T123456" in str_repr
        assert "Test ticket" in str_repr
        assert "Open" in str_repr
        assert "SEV_3" in str_repr
    
    def test_edge_case_empty_strings(self) -> None:
        """Test handling of empty string values."""
        ticket_data = {
            "id": "T123",
            "title": "",  # Empty title
            "description": "",  # Empty description
            "status": "Open",
            "created_date": "2024-01-01T10:00:00Z",
            "updated_date": "2024-01-01T10:00:00Z",
            "assignee": "",  # Empty assignee
            "resolver_group": ""  # Empty resolver group
        }
        
        ticket = Ticket.from_dict(ticket_data)
        
        assert ticket.title == ""
        assert ticket.description == ""
        assert ticket.assignee == ""
        assert ticket.resolver_group == ""
    
    def test_edge_case_very_long_strings(self) -> None:
        """Test handling of very long string values."""
        long_string = "x" * 10000
        
        ticket = Ticket(
            id="T123",
            title=long_string,
            description=long_string,
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            assignee=long_string,
            resolver_group=long_string
        )
        
        assert len(ticket.title) == 10000
        assert len(ticket.description) == 10000
        assert len(ticket.assignee) == 10000
        assert len(ticket.resolver_group) == 10000
    
    def test_edge_case_special_characters(self) -> None:
        """Test handling of special characters in string fields."""
        special_chars = "!@#$%^&*()[]{}|;':\",./<>?`~"
        unicode_chars = "αβγδε中文日本語한국어"
        
        ticket = Ticket(
            id="T123",
            title=f"Test {special_chars} {unicode_chars}",
            description=f"Description with {special_chars} and {unicode_chars}",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert special_chars in ticket.title
        assert unicode_chars in ticket.title
        assert special_chars in ticket.description
        assert unicode_chars in ticket.description
    
    def test_edge_case_future_dates(self) -> None:
        """Test handling of future dates."""
        future_date = datetime.now() + timedelta(days=365)
        
        ticket = Ticket(
            id="T123",
            title="Future ticket",
            description="Created in the future",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=future_date,
            updated_date=future_date
        )
        
        # Age should be negative for future tickets
        age = ticket.age()
        assert age.total_seconds() < 0
    
    def test_edge_case_same_created_and_resolved_time(self) -> None:
        """Test resolution time when created and resolved at same time."""
        same_time = datetime(2024, 1, 1, 10, 0, 0)
        
        ticket = Ticket(
            id="T123",
            title="Instant resolution",
            description="Resolved immediately",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_3,
            created_date=same_time,
            updated_date=same_time,
            resolved_date=same_time
        )
        
        resolution_time = ticket.resolution_time()
        assert resolution_time == timedelta(0)