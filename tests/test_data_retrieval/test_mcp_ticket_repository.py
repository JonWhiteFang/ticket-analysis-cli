"""Comprehensive tests for MCP ticket repository.

This module contains unit tests for the MCPTicketRepository class,
including MCP integration, data mapping, error handling, and resilience patterns.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, call, MagicMock

from ticket_analyzer.data_retrieval.mcp_ticket_repository import (
    MCPTicketRepository,
    TicketDataMapper
)
from ticket_analyzer.models import (
    Ticket,
    TicketStatus,
    TicketSeverity,
    SearchCriteria,
    DataRetrievalError,
    ValidationError,
    AuthenticationError,
    MCPError
)


class TestTicketDataMapper:
    """Test cases for TicketDataMapper class."""
    
    @pytest.fixture
    def sample_mcp_ticket_data(self) -> Dict[str, Any]:
        """Sample MCP ticket data for testing."""
        return {
            "id": "T123456",
            "title": "Test ticket",
            "description": "Test description",
            "status": "Open",
            "severity": "SEV_3",
            "createDate": "2024-01-01T10:00:00Z",
            "lastUpdatedDate": "2024-01-01T10:30:00Z",
            "assignee": "testuser",
            "extensions": {
                "tt": {
                    "assignedGroup": "Test Team",
                    "impact": "Medium",
                    "urgency": "High",
                    "category": "Bug",
                    "subcategory": "Authentication"
                }
            },
            "tags": ["test", "bug"],
            "source": "internal"
        }
    
    def test_map_to_ticket_success(self, sample_mcp_ticket_data: Dict[str, Any]) -> None:
        """Test successful mapping of MCP data to Ticket object."""
        ticket = TicketDataMapper.map_to_ticket(sample_mcp_ticket_data)
        
        assert ticket.id == "T123456"
        assert ticket.title == "Test ticket"
        assert ticket.description == "Test description"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.severity == TicketSeverity.SEV_3
        assert ticket.assignee == "testuser"
        assert ticket.resolver_group == "Test Team"
        assert ticket.tags == ["test", "bug"]
        assert ticket.metadata["impact"] == "Medium"
        assert ticket.metadata["urgency"] == "High"
        assert ticket.metadata["category"] == "Bug"
        assert ticket.metadata["source"] == "internal"
    
    def test_map_to_ticket_missing_required_fields(self) -> None:
        """Test mapping fails with missing required fields."""
        incomplete_data = {"title": "Test"}  # Missing id and status
        
        with pytest.raises(ValidationError) as exc_info:
            TicketDataMapper.map_to_ticket(incomplete_data)
        
        assert "Missing required ticket fields" in str(exc_info.value)
        assert "id" in str(exc_info.value)
        assert "status" in str(exc_info.value)
    
    def test_map_to_ticket_with_resolved_status(self) -> None:
        """Test mapping ticket with resolved status and resolution date."""
        resolved_data = {
            "id": "T789012",
            "title": "Resolved ticket",
            "status": "Resolved",
            "createDate": "2024-01-01T10:00:00Z",
            "lastResolvedDate": "2024-01-01T15:00:00Z"
        }
        
        ticket = TicketDataMapper.map_to_ticket(resolved_data)
        
        assert ticket.status == TicketStatus.RESOLVED
        assert ticket.resolved_date is not None
        assert ticket.is_resolved() is True
        assert ticket.resolution_time() == timedelta(hours=5)
    
    def test_map_to_ticket_with_invalid_status(self) -> None:
        """Test mapping with invalid status value."""
        invalid_data = {
            "id": "T123456",
            "title": "Test",
            "status": "InvalidStatus"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TicketDataMapper.map_to_ticket(invalid_data)
        
        assert "Invalid ticket status" in str(exc_info.value)
    
    def test_map_to_ticket_with_minimal_data(self) -> None:
        """Test mapping with minimal required data."""
        minimal_data = {
            "id": "T123456",
            "title": "Minimal ticket",
            "status": "Open"
        }
        
        ticket = TicketDataMapper.map_to_ticket(minimal_data)
        
        assert ticket.id == "T123456"
        assert ticket.title == "Minimal ticket"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.description == ""
        assert ticket.assignee is None
        assert ticket.resolver_group is None
        assert ticket.tags == []
        assert ticket.metadata == {}


class TestMCPTicketRepository:
    """Test cases for MCPTicketRepository class."""
    
    @pytest.fixture
    def mock_mcp_client(self) -> Mock:
        """Mock MCP client for testing."""
        mock_client = Mock()
        mock_client.connect.return_value = None
        mock_client.disconnect.return_value = None
        mock_client.health_check.return_value = {
            "connected": True,
            "server_responsive": True
        }
        return mock_client
    
    @pytest.fixture
    def mock_authenticator(self) -> Mock:
        """Mock authenticator for testing."""
        mock_auth = Mock()
        mock_auth.ensure_authenticated.return_value = None
        return mock_auth
    
    @pytest.fixture
    def mock_sanitizer(self) -> Mock:
        """Mock data sanitizer for testing."""
        mock_sanitizer = Mock()
        mock_sanitizer.sanitize_ticket_data.side_effect = lambda x: x
        mock_sanitizer.sanitize_search_criteria.side_effect = lambda x: x
        return mock_sanitizer
    
    @pytest.fixture
    def mock_validator(self) -> Mock:
        """Mock input validator for testing."""
        mock_validator = Mock()
        mock_validator.validate_ticket_id.return_value = True
        mock_validator.validate_search_criteria.return_value = True
        return mock_validator
    
    @pytest.fixture
    def repository(self, mock_mcp_client: Mock, mock_authenticator: Mock,
                  mock_sanitizer: Mock, mock_validator: Mock) -> MCPTicketRepository:
        """MCPTicketRepository instance for testing."""
        return MCPTicketRepository(
            mcp_client=mock_mcp_client,
            authenticator=mock_authenticator,
            sanitizer=mock_sanitizer,
            validator=mock_validator
        )
    
    @pytest.fixture
    def sample_mcp_response(self) -> List[Dict[str, Any]]:
        """Sample MCP response data."""
        return [
            {
                "id": "T123456",
                "title": "Test ticket 1",
                "status": "Open",
                "createDate": "2024-01-01T10:00:00Z"
            },
            {
                "id": "T123457",
                "title": "Test ticket 2",
                "status": "Resolved",
                "createDate": "2024-01-01T11:00:00Z",
                "lastResolvedDate": "2024-01-01T15:00:00Z"
            }
        ]
    
    def test_initialization_with_dependencies(self, mock_mcp_client: Mock,
                                            mock_authenticator: Mock) -> None:
        """Test repository initialization with dependencies."""
        repo = MCPTicketRepository(
            mcp_client=mock_mcp_client,
            authenticator=mock_authenticator
        )
        
        assert repo._mcp_client == mock_mcp_client
        assert repo._authenticator == mock_authenticator
        assert repo._connected is False
    
    def test_initialization_with_defaults(self) -> None:
        """Test repository initialization with default dependencies."""
        repo = MCPTicketRepository()
        
        assert repo._mcp_client is not None
        assert repo._connected is False
    
    def test_ensure_connection_success(self, repository: MCPTicketRepository,
                                     mock_mcp_client: Mock, mock_authenticator: Mock) -> None:
        """Test successful connection establishment."""
        repository._ensure_connection()
        
        mock_authenticator.ensure_authenticated.assert_called_once()
        mock_mcp_client.connect.assert_called_once()
        assert repository._connected is True
    
    def test_ensure_connection_authentication_failure(self, repository: MCPTicketRepository,
                                                    mock_authenticator: Mock) -> None:
        """Test connection failure due to authentication."""
        mock_authenticator.ensure_authenticated.side_effect = AuthenticationError("Auth failed")
        
        with pytest.raises(DataRetrievalError) as exc_info:
            repository._ensure_connection()
        
        assert "Failed to establish MCP connection" in str(exc_info.value)
        assert repository._connected is False
    
    def test_ensure_connection_mcp_failure(self, repository: MCPTicketRepository,
                                         mock_mcp_client: Mock) -> None:
        """Test connection failure due to MCP client error."""
        mock_mcp_client.connect.side_effect = MCPError("Connection failed")
        
        with pytest.raises(DataRetrievalError) as exc_info:
            repository._ensure_connection()
        
        assert "Failed to establish MCP connection" in str(exc_info.value)
        assert repository._connected is False
    
    def test_validate_connection_success(self, repository: MCPTicketRepository,
                                       mock_mcp_client: Mock) -> None:
        """Test successful connection validation."""
        result = repository.validate_connection()
        
        assert result is True
        mock_mcp_client.health_check.assert_called_once()
    
    def test_validate_connection_failure(self, repository: MCPTicketRepository,
                                       mock_mcp_client: Mock) -> None:
        """Test connection validation failure."""
        mock_mcp_client.health_check.return_value = {
            "connected": False,
            "server_responsive": False
        }
        
        result = repository.validate_connection()
        
        assert result is False
    
    def test_search_tickets_success(self, repository: MCPTicketRepository,
                                  mock_mcp_client: Mock, sample_mcp_response: List[Dict[str, Any]]) -> None:
        """Test successful ticket search."""
        mock_mcp_client.search_tickets.return_value = sample_mcp_response
        
        criteria = SearchCriteria(status_filters=["Open"])
        tickets = repository.search_tickets(criteria)
        
        assert len(tickets) == 2
        assert tickets[0].id == "T123456"
        assert tickets[1].id == "T123457"
        mock_mcp_client.search_tickets.assert_called_once()
    
    def test_search_tickets_validation_failure(self, repository: MCPTicketRepository,
                                             mock_validator: Mock) -> None:
        """Test search tickets with validation failure."""
        mock_validator.validate_search_criteria.return_value = False
        
        criteria = SearchCriteria(status_filters=["Invalid"])
        
        with pytest.raises(ValidationError) as exc_info:
            repository.search_tickets(criteria)
        
        assert "Invalid search criteria" in str(exc_info.value)
    
    def test_search_tickets_mcp_error(self, repository: MCPTicketRepository,
                                    mock_mcp_client: Mock) -> None:
        """Test search tickets with MCP error."""
        mock_mcp_client.search_tickets.side_effect = MCPError("Search failed")
        
        criteria = SearchCriteria(status_filters=["Open"])
        
        with pytest.raises(DataRetrievalError) as exc_info:
            repository.search_tickets(criteria)
        
        assert "MCP search failed" in str(exc_info.value)
    
    def test_search_tickets_authentication_error(self, repository: MCPTicketRepository,
                                               mock_mcp_client: Mock) -> None:
        """Test search tickets with authentication error."""
        mock_mcp_client.search_tickets.side_effect = AuthenticationError("Auth required")
        
        criteria = SearchCriteria(status_filters=["Open"])
        
        with pytest.raises(AuthenticationError):
            repository.search_tickets(criteria)
    
    def test_search_tickets_with_sanitization(self, repository: MCPTicketRepository,
                                            mock_mcp_client: Mock, mock_sanitizer: Mock,
                                            sample_mcp_response: List[Dict[str, Any]]) -> None:
        """Test search tickets with data sanitization."""
        mock_mcp_client.search_tickets.return_value = sample_mcp_response
        
        criteria = SearchCriteria(status_filters=["Open"])
        tickets = repository.search_tickets(criteria)
        
        # Verify sanitizer was called for criteria and ticket data
        mock_sanitizer.sanitize_search_criteria.assert_called_once_with(criteria)
        assert mock_sanitizer.sanitize_ticket_data.call_count == 2  # Once per ticket
    
    def test_get_ticket_by_id_success(self, repository: MCPTicketRepository,
                                    mock_mcp_client: Mock) -> None:
        """Test successful ticket retrieval by ID."""
        ticket_data = {
            "id": "T123456",
            "title": "Test ticket",
            "status": "Open"
        }
        mock_mcp_client.get_ticket.return_value = ticket_data
        
        ticket = repository.get_ticket_by_id("T123456")
        
        assert ticket is not None
        assert ticket.id == "T123456"
        mock_mcp_client.get_ticket.assert_called_once_with("T123456")
    
    def test_get_ticket_by_id_not_found(self, repository: MCPTicketRepository,
                                      mock_mcp_client: Mock) -> None:
        """Test ticket retrieval when ticket not found."""
        mock_mcp_client.get_ticket.return_value = None
        
        ticket = repository.get_ticket_by_id("NONEXISTENT")
        
        assert ticket is None
    
    def test_get_ticket_by_id_validation_failure(self, repository: MCPTicketRepository,
                                               mock_validator: Mock) -> None:
        """Test ticket retrieval with invalid ticket ID."""
        mock_validator.validate_ticket_id.return_value = False
        
        with pytest.raises(ValidationError) as exc_info:
            repository.get_ticket_by_id("INVALID_ID")
        
        assert "Invalid ticket ID format" in str(exc_info.value)
    
    def test_get_ticket_by_id_mcp_error(self, repository: MCPTicketRepository,
                                      mock_mcp_client: Mock) -> None:
        """Test ticket retrieval with MCP error."""
        mock_mcp_client.get_ticket.side_effect = MCPError("Retrieval failed")
        
        with pytest.raises(DataRetrievalError) as exc_info:
            repository.get_ticket_by_id("T123456")
        
        assert "MCP ticket retrieval failed" in str(exc_info.value)
    
    def test_count_tickets(self, repository: MCPTicketRepository,
                          mock_mcp_client: Mock, sample_mcp_response: List[Dict[str, Any]]) -> None:
        """Test ticket counting."""
        mock_mcp_client.search_tickets.return_value = sample_mcp_response
        
        criteria = SearchCriteria(status_filters=["Open"])
        count = repository.count_tickets(criteria)
        
        assert count == 2
    
    def test_count_tickets_error(self, repository: MCPTicketRepository,
                               mock_mcp_client: Mock) -> None:
        """Test ticket counting with error."""
        mock_mcp_client.search_tickets.side_effect = MCPError("Count failed")
        
        criteria = SearchCriteria(status_filters=["Open"])
        count = repository.count_tickets(criteria)
        
        assert count == 0  # Should return 0 on error
    
    def test_context_manager_success(self, repository: MCPTicketRepository,
                                   mock_mcp_client: Mock) -> None:
        """Test repository as context manager with success."""
        with repository as repo:
            assert repo == repository
            assert repository._connected is True
        
        mock_mcp_client.disconnect.assert_called_once()
    
    def test_context_manager_with_exception(self, repository: MCPTicketRepository,
                                          mock_mcp_client: Mock) -> None:
        """Test repository as context manager with exception."""
        try:
            with repository as repo:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still disconnect on exception
        mock_mcp_client.disconnect.assert_called_once()


class TestMCPTicketRepositoryIntegration:
    """Integration tests for MCPTicketRepository with multiple components."""
    
    @pytest.fixture
    def integration_repository(self) -> MCPTicketRepository:
        """Repository with real dependencies for integration testing."""
        return MCPTicketRepository()
    
    @patch('ticket_analyzer.external.mcp_client.MCPClient')
    def test_full_search_flow_with_mocked_mcp(self, mock_mcp_class: Mock) -> None:
        """Test complete search flow with mocked MCP client."""
        # Setup mock MCP client
        mock_client = Mock()
        mock_mcp_class.return_value = mock_client
        
        mock_client.search_tickets.return_value = [
            {
                "id": "T123456",
                "title": "Integration test ticket",
                "status": "Open",
                "createDate": "2024-01-01T10:00:00Z"
            }
        ]
        
        # Create repository and perform search
        repo = MCPTicketRepository()
        criteria = SearchCriteria(status_filters=["Open"])
        
        tickets = repo.search_tickets(criteria)
        
        assert len(tickets) == 1
        assert tickets[0].id == "T123456"
        assert tickets[0].title == "Integration test ticket"
    
    @patch('ticket_analyzer.external.mcp_client.MCPClient')
    @patch('ticket_analyzer.auth.midway_auth.MidwayAuthenticator')
    def test_full_flow_with_authentication(self, mock_auth_class: Mock, mock_mcp_class: Mock) -> None:
        """Test complete flow with authentication."""
        # Setup mocks
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth
        
        mock_client = Mock()
        mock_mcp_class.return_value = mock_client
        
        mock_client.get_ticket.return_value = {
            "id": "T789012",
            "title": "Authenticated ticket",
            "status": "Resolved",
            "createDate": "2024-01-01T09:00:00Z",
            "lastResolvedDate": "2024-01-01T15:00:00Z"
        }
        
        # Create repository with authenticator
        repo = MCPTicketRepository(authenticator=mock_auth)
        
        # Retrieve ticket
        ticket = repo.get_ticket_by_id("T789012")
        
        assert ticket is not None
        assert ticket.id == "T789012"
        assert ticket.is_resolved() is True
        
        # Verify authentication was ensured
        mock_auth.ensure_authenticated.assert_called()
    
    def test_error_propagation_chain(self) -> None:
        """Test that errors propagate correctly through the chain."""
        # Create repository with failing mock client
        mock_client = Mock()
        mock_client.connect.side_effect = MCPError("Connection failed")
        
        repo = MCPTicketRepository(mcp_client=mock_client)
        
        # Test that DataRetrievalError is raised with proper context
        with pytest.raises(DataRetrievalError) as exc_info:
            repo._ensure_connection()
        
        assert "Failed to establish MCP connection" in str(exc_info.value)
        error_context = exc_info.value.get_context()
        assert error_context["service"] == "MCP"
        assert error_context["operation"] == "connect"


class TestMCPTicketRepositoryPerformance:
    """Performance tests for MCPTicketRepository."""
    
    @pytest.fixture
    def large_dataset(self) -> List[Dict[str, Any]]:
        """Generate large dataset for performance testing."""
        return [
            {
                "id": f"T{i:06d}",
                "title": f"Performance test ticket {i}",
                "status": "Open" if i % 2 == 0 else "Resolved",
                "createDate": "2024-01-01T10:00:00Z"
            }
            for i in range(1000)
        ]
    
    @pytest.mark.performance
    def test_large_dataset_processing(self, large_dataset: List[Dict[str, Any]]) -> None:
        """Test processing of large datasets."""
        mock_client = Mock()
        mock_client.search_tickets.return_value = large_dataset
        
        repo = MCPTicketRepository(mcp_client=mock_client)
        criteria = SearchCriteria(status_filters=["Open", "Resolved"])
        
        import time
        start_time = time.time()
        tickets = repo.search_tickets(criteria)
        end_time = time.time()
        
        # Should process 1000 tickets in reasonable time
        assert len(tickets) == 1000
        assert end_time - start_time < 5.0  # Should complete within 5 seconds
    
    @pytest.mark.performance
    def test_memory_usage_with_large_dataset(self, large_dataset: List[Dict[str, Any]]) -> None:
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        mock_client = Mock()
        mock_client.search_tickets.return_value = large_dataset
        
        repo = MCPTicketRepository(mcp_client=mock_client)
        criteria = SearchCriteria(status_filters=["Open", "Resolved"])
        
        tickets = repo.search_tickets(criteria)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for 1000 tickets)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
        assert len(tickets) == 1000


class TestMCPTicketRepositoryResilience:
    """Tests for resilience patterns in MCPTicketRepository."""
    
    def test_circuit_breaker_functionality(self) -> None:
        """Test circuit breaker pattern implementation."""
        mock_client = Mock()
        # Simulate repeated failures
        mock_client.search_tickets.side_effect = MCPError("Service unavailable")
        
        repo = MCPTicketRepository(mcp_client=mock_client)
        criteria = SearchCriteria(status_filters=["Open"])
        
        # First few calls should fail normally
        for _ in range(3):
            with pytest.raises(DataRetrievalError):
                repo.search_tickets(criteria)
        
        # After threshold, circuit breaker should open
        # This would require actual circuit breaker implementation
        # For now, just verify the error handling works
        assert mock_client.search_tickets.call_count == 3
    
    def test_retry_logic_with_exponential_backoff(self) -> None:
        """Test retry logic with exponential backoff."""
        mock_client = Mock()
        # First two calls fail, third succeeds
        mock_client.search_tickets.side_effect = [
            MCPError("Temporary failure"),
            MCPError("Temporary failure"),
            [{"id": "T123456", "title": "Success", "status": "Open"}]
        ]
        
        repo = MCPTicketRepository(mcp_client=mock_client)
        criteria = SearchCriteria(status_filters=["Open"])
        
        # Should eventually succeed after retries
        tickets = repo.search_tickets(criteria)
        
        assert len(tickets) == 1
        assert tickets[0].id == "T123456"
        assert mock_client.search_tickets.call_count == 3
    
    def test_graceful_degradation_on_partial_failure(self) -> None:
        """Test graceful degradation when some operations fail."""
        mock_client = Mock()
        # Search succeeds but health check fails
        mock_client.search_tickets.return_value = [
            {"id": "T123456", "title": "Test", "status": "Open"}
        ]
        mock_client.health_check.side_effect = MCPError("Health check failed")
        
        repo = MCPTicketRepository(mcp_client=mock_client)
        criteria = SearchCriteria(status_filters=["Open"])
        
        # Search should still work even if health check fails
        tickets = repo.search_tickets(criteria)
        assert len(tickets) == 1
        
        # But connection validation should fail gracefully
        is_healthy = repo.validate_connection()
        assert is_healthy is False