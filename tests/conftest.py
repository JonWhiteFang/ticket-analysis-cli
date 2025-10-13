"""Shared test fixtures and configuration for the test suite.

This module provides common fixtures and pytest configuration that can be
used across all test modules in the ticket analyzer test suite.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.analysis import SearchCriteria, AnalysisResult
from ticket_analyzer.models.config import (
    ReportConfig, AuthConfig, MCPConfig, LoggingConfig, ApplicationConfig,
    OutputFormat, LogLevel
)


@pytest.fixture
def sample_ticket_data() -> Dict[str, Any]:
    """Sample ticket data for testing."""
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
def resolved_ticket_data() -> Dict[str, Any]:
    """Sample resolved ticket data for testing."""
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


@pytest.fixture
def sample_ticket(sample_ticket_data: Dict[str, Any]) -> Ticket:
    """Sample Ticket instance for testing."""
    return Ticket.from_dict(sample_ticket_data)


@pytest.fixture
def resolved_ticket(resolved_ticket_data: Dict[str, Any]) -> Ticket:
    """Sample resolved Ticket instance for testing."""
    return Ticket.from_dict(resolved_ticket_data)


@pytest.fixture
def multiple_tickets() -> List[Ticket]:
    """Multiple ticket instances for testing."""
    tickets = []
    
    # Create tickets with different statuses and severities
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    for i in range(5):
        created_time = base_time + timedelta(hours=i)
        updated_time = created_time + timedelta(minutes=30)
        resolved_time = updated_time + timedelta(hours=2) if i % 2 == 0 else None
        
        ticket = Ticket(
            id=f"T{123456 + i}",
            title=f"Test ticket {i + 1}",
            description=f"Description for ticket {i + 1}",
            status=TicketStatus.RESOLVED if resolved_time else TicketStatus.OPEN,
            severity=list(TicketSeverity)[i % len(TicketSeverity)],
            created_date=created_time,
            updated_date=updated_time,
            resolved_date=resolved_time,
            assignee=f"user{i + 1}",
            resolver_group=f"Team {(i % 2) + 1}",
            tags=[f"tag{i + 1}", "test"],
            metadata={"priority": "normal" if i % 2 == 0 else "high"}
        )
        tickets.append(ticket)
    
    return tickets


@pytest.fixture
def sample_search_criteria() -> SearchCriteria:
    """Sample SearchCriteria for testing."""
    return SearchCriteria(
        status=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS],
        severity=[TicketSeverity.SEV_1, TicketSeverity.SEV_2],
        assignee="testuser",
        resolver_group="Test Team",
        created_after=datetime(2024, 1, 1),
        created_before=datetime(2024, 1, 31),
        tags=["urgent", "bug"],
        search_text="authentication error",
        max_results=100,
        offset=0
    )


@pytest.fixture
def sample_analysis_result() -> AnalysisResult:
    """Sample AnalysisResult for testing."""
    metrics = {
        "total_tickets": 150,
        "avg_resolution_time": 24.5,
        "status_distribution": {
            "Open": 50,
            "Resolved": 100
        }
    }
    
    trends = {
        "weekly_trend": [10, 15, 12, 18, 20],
        "monthly_trend": [100, 120, 150]
    }
    
    summary = {
        "key_insight": "Tickets are increasing",
        "recommendation": "Add more resources"
    }
    
    return AnalysisResult(
        metrics=metrics,
        trends=trends,
        summary=summary,
        generated_at=datetime(2024, 1, 15, 10, 30, 0),
        ticket_count=150,
        date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
        analysis_duration=45.2,
        metadata={"analysis_version": "1.0"}
    )


@pytest.fixture
def sample_report_config() -> ReportConfig:
    """Sample ReportConfig for testing."""
    return ReportConfig(
        format=OutputFormat.JSON,
        output_path="/tmp/test_report.json",
        include_charts=True,
        color_output=True,
        sanitize_output=True,
        max_results_display=100,
        show_progress=True,
        verbose=False,
        theme="auto"
    )


@pytest.fixture
def sample_auth_config() -> AuthConfig:
    """Sample AuthConfig for testing."""
    return AuthConfig(
        timeout_seconds=60,
        max_retry_attempts=3,
        check_interval_seconds=300,
        session_duration_hours=8,
        auto_refresh=True,
        require_auth=True,
        auth_method="midway",
        cache_credentials=False
    )


@pytest.fixture
def sample_mcp_config() -> MCPConfig:
    """Sample MCPConfig for testing."""
    return MCPConfig(
        server_command=["node", "mcp-server.js"],
        connection_timeout=30,
        request_timeout=60,
        max_retries=3,
        retry_delay=1.0,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60,
        enable_logging=False
    )


@pytest.fixture
def sample_logging_config() -> LoggingConfig:
    """Sample LoggingConfig for testing."""
    return LoggingConfig(
        level=LogLevel.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        file_path=None,
        max_file_size=10 * 1024 * 1024,  # 10MB
        backup_count=5,
        sanitize_logs=True,
        include_timestamps=True,
        include_caller_info=False
    )


@pytest.fixture
def sample_application_config(
    sample_auth_config: AuthConfig,
    sample_report_config: ReportConfig,
    sample_mcp_config: MCPConfig,
    sample_logging_config: LoggingConfig
) -> ApplicationConfig:
    """Sample ApplicationConfig for testing."""
    return ApplicationConfig(
        auth=sample_auth_config,
        report=sample_report_config,
        mcp=sample_mcp_config,
        logging=sample_logging_config,
        data_dir="/tmp/data",
        config_dir="/tmp/config",
        cache_dir="/tmp/cache",
        temp_dir="/tmp/temp",
        debug_mode=False,
        max_concurrent_requests=10
    )


@pytest.fixture
def mock_datetime_now():
    """Mock datetime.now() to return a fixed time for testing."""
    fixed_time = datetime(2024, 1, 15, 12, 0, 0)
    
    with patch('ticket_analyzer.models.ticket.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_time
        mock_dt.fromisoformat = datetime.fromisoformat
        yield mock_dt


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    mock_client = Mock()
    
    # Configure default return values
    mock_client.search_tickets.return_value = []
    mock_client.get_ticket.return_value = None
    mock_client.connect.return_value = None
    mock_client.disconnect.return_value = None
    
    return mock_client


@pytest.fixture
def mock_authenticator():
    """Mock authenticator for testing."""
    mock_auth = Mock()
    
    # Configure default return values
    mock_auth.ensure_authenticated.return_value = None
    mock_auth.is_authenticated.return_value = True
    mock_auth.authenticate.return_value = True
    
    return mock_auth


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file for testing."""
    config_file = tmp_path / "test_config.json"
    config_data = {
        "auth": {
            "timeout_seconds": 30,
            "auth_method": "midway"
        },
        "report": {
            "format": "json",
            "max_results_display": 50
        },
        "debug_mode": True
    }
    
    import json
    config_file.write_text(json.dumps(config_data, indent=2))
    return str(config_file)


@pytest.fixture
def temp_output_directory(tmp_path):
    """Create a temporary output directory for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Custom pytest markers for test categorization
pytestmark = pytest.mark.unit  # Mark all tests in this module as unit tests


# Helper functions for tests
def create_test_ticket(
    ticket_id: str = "T123456",
    status: TicketStatus = TicketStatus.OPEN,
    severity: TicketSeverity = TicketSeverity.SEV_3,
    created_hours_ago: int = 1,
    resolved_hours_ago: int = None
) -> Ticket:
    """Helper function to create test tickets with custom parameters."""
    now = datetime.now()
    created_date = now - timedelta(hours=created_hours_ago)
    updated_date = created_date + timedelta(minutes=30)
    resolved_date = (
        now - timedelta(hours=resolved_hours_ago) 
        if resolved_hours_ago is not None else None
    )
    
    return Ticket(
        id=ticket_id,
        title=f"Test ticket {ticket_id}",
        description=f"Description for {ticket_id}",
        status=status,
        severity=severity,
        created_date=created_date,
        updated_date=updated_date,
        resolved_date=resolved_date,
        assignee="testuser",
        resolver_group="Test Team",
        tags=["test"],
        metadata={"test": True}
    )


def assert_ticket_equals(ticket1: Ticket, ticket2: Ticket) -> None:
    """Helper function to assert that two tickets are equal."""
    assert ticket1.id == ticket2.id
    assert ticket1.title == ticket2.title
    assert ticket1.description == ticket2.description
    assert ticket1.status == ticket2.status
    assert ticket1.severity == ticket2.severity
    assert ticket1.created_date == ticket2.created_date
    assert ticket1.updated_date == ticket2.updated_date
    assert ticket1.resolved_date == ticket2.resolved_date
    assert ticket1.assignee == ticket2.assignee
    assert ticket1.resolver_group == ticket2.resolver_group
    assert ticket1.tags == ticket2.tags
    assert ticket1.metadata == ticket2.metadata


def create_test_analysis_result(
    ticket_count: int = 100,
    metrics: Dict[str, Any] = None,
    trends: Dict[str, Any] = None
) -> AnalysisResult:
    """Helper function to create test analysis results."""
    if metrics is None:
        metrics = {
            "total_tickets": ticket_count,
            "avg_resolution_time": 24.0,
            "status_distribution": {"Open": 30, "Resolved": 70}
        }
    
    if trends is None:
        trends = {
            "weekly": [10, 15, 20, 25, 30],
            "monthly": [100, 120, 150]
        }
    
    return AnalysisResult(
        metrics=metrics,
        trends=trends,
        summary={"insight": "Test analysis"},
        ticket_count=ticket_count,
        generated_at=datetime.now()
    )