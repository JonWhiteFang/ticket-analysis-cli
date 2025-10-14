---
inclusion: fileMatch
fileMatchPattern: 'test*'
---

# Testing Standards

## Pytest Framework Usage and Organization

### Test Structure and Organization
```python
# tests/conftest.py
import pytest
from typing import Generator, Dict, Any
from unittest.mock import Mock, patch

@pytest.fixture
def sample_ticket_data() -> Dict[str, Any]:
    """Sample ticket data for testing."""
    return {
        "id": "T123456",
        "title": "Test ticket",
        "status": "Open",
        "created_date": "2024-01-01T00:00:00Z",
        "assignee": "testuser"
    }

@pytest.fixture
def mock_mcp_client() -> Generator[Mock, None, None]:
    """Mock MCP client for testing."""
    with patch('ticket_analyzer.external.mcp_client.MCPClient') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def temp_config_file(tmp_path) -> str:
    """Create temporary configuration file."""
    config_file = tmp_path / "config.json"
    config_data = {
        "output_format": "json",
        "max_results": 50
    }
    config_file.write_text(json.dumps(config_data))
    return str(config_file)
```

### Unit Test Patterns
```python
# tests/test_models.py
import pytest
from datetime import datetime, timedelta
from ticket_analyzer.models.ticket import Ticket

class TestTicket:
    """Test cases for Ticket model."""
    
    def test_ticket_creation(self, sample_ticket_data):
        """Test ticket creation from data."""
        ticket = Ticket.from_dict(sample_ticket_data)
        assert ticket.id == "T123456"
        assert ticket.title == "Test ticket"
        assert ticket.status == "Open"
    
    def test_is_resolved_when_status_resolved(self):
        """Test is_resolved returns True for resolved tickets."""
        ticket = Ticket(
            id="T123",
            title="Test",
            status="Resolved",
            created_date=datetime.now(),
            resolved_date=datetime.now()
        )
        assert ticket.is_resolved() is True
    
    def test_is_resolved_when_status_open(self):
        """Test is_resolved returns False for open tickets."""
        ticket = Ticket(
            id="T123",
            title="Test",
            status="Open",
            created_date=datetime.now()
        )
        assert ticket.is_resolved() is False
    
    def test_resolution_time_calculation(self):
        """Test resolution time calculation."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        resolved = datetime(2024, 1, 2, 14, 30, 0)
        
        ticket = Ticket(
            id="T123",
            title="Test",
            status="Resolved",
            created_date=created,
            resolved_date=resolved
        )
        
        expected_time = timedelta(days=1, hours=4, minutes=30)
        assert ticket.resolution_time() == expected_time
```

### Mock Patterns for External Dependencies
```python
# tests/test_repositories.py
import pytest
from unittest.mock import Mock, patch, call
from ticket_analyzer.repositories.mcp_ticket_repository import MCPTicketRepository
from ticket_analyzer.models.search_criteria import SearchCriteria

class TestMCPTicketRepository:
    """Test cases for MCP ticket repository."""
    
    def test_find_by_id_success(self, mock_mcp_client, sample_ticket_data):
        """Test successful ticket retrieval by ID."""
        # Arrange
        mock_mcp_client.get_ticket.return_value = sample_ticket_data
        repo = MCPTicketRepository(mock_mcp_client)
        
        # Act
        ticket = repo.find_by_id("T123456")
        
        # Assert
        assert ticket is not None
        assert ticket.id == "T123456"
        mock_mcp_client.get_ticket.assert_called_once_with("T123456")
    
    def test_find_by_id_not_found(self, mock_mcp_client):
        """Test ticket not found scenario."""
        # Arrange
        mock_mcp_client.get_ticket.return_value = None
        repo = MCPTicketRepository(mock_mcp_client)
        
        # Act
        ticket = repo.find_by_id("NONEXISTENT")
        
        # Assert
        assert ticket is None
    
    @patch('ticket_analyzer.repositories.mcp_ticket_repository.logger')
    def test_find_by_id_mcp_error(self, mock_logger, mock_mcp_client):
        """Test MCP error handling."""
        # Arrange
        mock_mcp_client.get_ticket.side_effect = MCPError("Connection failed")
        repo = MCPTicketRepository(mock_mcp_client)
        
        # Act
        ticket = repo.find_by_id("T123456")
        
        # Assert
        assert ticket is None
        mock_logger.error.assert_called_once()
```

### Subprocess Mocking for Authentication
```python
# tests/test_auth_service.py
import pytest
from unittest.mock import patch, Mock
import subprocess
from ticket_analyzer.external.auth_service import MidwayAuthenticator

class TestMidwayAuthenticator:
    """Test cases for Midway authentication."""
    
    @patch('subprocess.run')
    def test_is_authenticated_success(self, mock_run):
        """Test successful authentication check."""
        # Arrange
        mock_run.return_value = Mock(returncode=0)
        authenticator = MidwayAuthenticator()
        
        # Act
        result = authenticator._is_authenticated()
        
        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["mwinit", "-s"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_is_authenticated_failure(self, mock_run):
        """Test failed authentication check."""
        # Arrange
        mock_run.return_value = Mock(returncode=1)
        authenticator = MidwayAuthenticator()
        
        # Act
        result = authenticator._is_authenticated()
        
        # Assert
        assert result is False
    
    @patch('subprocess.run')
    def test_perform_authentication_timeout(self, mock_run):
        """Test authentication timeout."""
        # Arrange
        mock_run.side_effect = subprocess.TimeoutExpired("mwinit", 60)
        authenticator = MidwayAuthenticator()
        
        # Act & Assert
        with pytest.raises(AuthenticationError, match="Authentication timeout"):
            authenticator._perform_authentication()
```

### Pandas DataFrame Testing
```python
# tests/test_analysis_service.py
import pytest
import pandas as pd
from ticket_analyzer.services.analysis_service import AnalysisService

class TestAnalysisService:
    """Test cases for analysis service."""
    
    def test_create_dataframe_from_tickets(self):
        """Test DataFrame creation from ticket data."""
        # Arrange
        tickets = [
            Ticket(id="T1", title="Test 1", status="Open", 
                  created_date=datetime(2024, 1, 1)),
            Ticket(id="T2", title="Test 2", status="Resolved", 
                  created_date=datetime(2024, 1, 2))
        ]
        service = AnalysisService()
        
        # Act
        df = service._create_dataframe(tickets)
        
        # Assert
        assert len(df) == 2
        assert list(df.columns) == ["id", "title", "status", "created_date"]
        assert df.iloc[0]["id"] == "T1"
        assert df.iloc[1]["status"] == "Resolved"
    
    def test_calculate_status_distribution(self):
        """Test status distribution calculation."""
        # Arrange
        df = pd.DataFrame({
            "status": ["Open", "Open", "Resolved", "In Progress", "Open"]
        })
        service = AnalysisService()
        
        # Act
        distribution = service._calculate_status_distribution(df)
        
        # Assert
        expected = {"Open": 3, "Resolved": 1, "In Progress": 1}
        assert distribution == expected
```

### Test Coverage Requirements
```python
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = 
    --cov=ticket_analyzer
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    --strict-markers
    --disable-warnings
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Coverage configuration in pyproject.toml
[tool.coverage.run]
source = ["ticket_analyzer"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
    "*/migrations/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:"
]
```

### Integration Test Boundaries
```python
# tests/integration/test_ticket_analysis_flow.py
import pytest
from unittest.mock import patch
from ticket_analyzer.cli.commands.analyze import analyze_command

class TestTicketAnalysisIntegration:
    """Integration tests for ticket analysis flow."""
    
    @patch('ticket_analyzer.external.mcp_client.MCPClient')
    @patch('ticket_analyzer.external.auth_service.MidwayAuthenticator')
    def test_full_analysis_flow(self, mock_auth, mock_mcp_client, 
                               sample_ticket_data, tmp_path):
        """Test complete analysis flow from CLI to output."""
        # Arrange
        mock_auth.return_value.ensure_authenticated.return_value = None
        mock_mcp_client.return_value.search_tickets.return_value = [sample_ticket_data]
        
        output_file = tmp_path / "results.json"
        
        # Act
        result = analyze_command(
            format="json",
            output=str(output_file),
            status=["Open"],
            max_results=10
        )
        
        # Assert
        assert result.exit_code == 0
        assert output_file.exists()
        
        # Verify output content
        import json
        with open(output_file) as f:
            data = json.load(f)
        
        assert "metrics" in data
        assert "total_tickets" in data
        assert data["total_tickets"] == 1
```

### Performance Testing
```python
# tests/performance/test_large_dataset_processing.py
import pytest
import time
from ticket_analyzer.services.analysis_service import AnalysisService

class TestPerformance:
    """Performance tests for large datasets."""
    
    @pytest.mark.performance
    def test_large_dataset_processing_time(self):
        """Test processing time for large datasets."""
        # Arrange
        large_dataset = self._create_large_ticket_dataset(10000)
        service = AnalysisService()
        
        # Act
        start_time = time.time()
        result = service.analyze_tickets(large_dataset)
        end_time = time.time()
        
        # Assert
        processing_time = end_time - start_time
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert result.ticket_count == 10000
    
    def _create_large_ticket_dataset(self, count: int) -> List[Ticket]:
        """Create large dataset for performance testing."""
        tickets = []
        for i in range(count):
            tickets.append(Ticket(
                id=f"T{i:06d}",
                title=f"Test ticket {i}",
                status="Open" if i % 2 == 0 else "Resolved",
                created_date=datetime.now() - timedelta(days=i % 365)
            ))
        return tickets
```