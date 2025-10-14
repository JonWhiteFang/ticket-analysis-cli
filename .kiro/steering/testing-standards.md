---
inclusion: fileMatch
fileMatchPattern: 'test*'
---

# Testing Standards

## Pytest Configuration
```python
# pytest.ini
[tool:pytest]
addopts = --cov=ticket_analyzer --cov-fail-under=80
testpaths = tests
python_files = test_*.py
```

## Test Fixtures
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def sample_ticket_data():
    return {
        "id": "T123456",
        "title": "Test ticket",
        "status": "Open",
        "created_date": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def mock_mcp_client():
    with patch('ticket_analyzer.external.mcp_client.MCPClient') as mock:
        yield mock.return_value
```

## Unit Test Patterns
```python
class TestTicket:
    def test_ticket_creation(self, sample_ticket_data):
        ticket = Ticket.from_dict(sample_ticket_data)
        assert ticket.id == "T123456"
        assert ticket.status == "Open"
    
    def test_is_resolved_when_resolved(self):
        ticket = Ticket(id="T123", status="Resolved", resolved_date=datetime.now())
        assert ticket.is_resolved() is True
```

## Mock External Dependencies
```python
@patch('subprocess.run')
def test_authentication_success(self, mock_run):
    mock_run.return_value = Mock(returncode=0)
    authenticator = MidwayAuthenticator()
    assert authenticator._is_authenticated() is True
```

## Integration Tests
```python
@patch('ticket_analyzer.external.mcp_client.MCPClient')
def test_full_analysis_flow(self, mock_client, tmp_path):
    mock_client.return_value.search_tickets.return_value = [sample_data]
    output_file = tmp_path / "results.json"
    
    result = analyze_command(format="json", output=str(output_file))
    assert result.exit_code == 0
    assert output_file.exists()
```

## Coverage Requirements
- Minimum 80% code coverage
- Test all public methods
- Mock external dependencies
- Include edge cases and error conditions