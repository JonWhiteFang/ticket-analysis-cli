# Testing Guide

## Overview

This document provides comprehensive guidance for testing the Ticket Analysis CLI tool. It covers testing strategies, frameworks, coverage requirements, and best practices for maintaining high-quality, reliable code.

## Testing Philosophy

### Testing Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation
2. **Comprehensive Coverage**: Aim for 80%+ code coverage on core modules
3. **Fast Feedback**: Tests should run quickly to enable rapid development
4. **Isolation**: Tests should be independent and not rely on external services
5. **Maintainability**: Tests should be easy to read, understand, and maintain

### Testing Pyramid

```
    ┌─────────────────┐
    │   E2E Tests     │  ← Few, slow, high confidence
    │   (Integration) │
    ├─────────────────┤
    │ Integration     │  ← Some, medium speed
    │ Tests           │
    ├─────────────────┤
    │   Unit Tests    │  ← Many, fast, focused
    │                 │
    └─────────────────┘
```

## Testing Framework and Tools

### Core Testing Stack

- **pytest**: Primary testing framework
- **pytest-cov**: Code coverage reporting
- **pytest-mock**: Mocking and patching
- **pytest-asyncio**: Async testing support
- **factory_boy**: Test data factories
- **freezegun**: Time mocking for date/time tests
- **responses**: HTTP request mocking

### Installation

```bash
pip install -r requirements-dev.txt
```

### Configuration Files

#### pytest.ini
```ini
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
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    security: Security-related tests
    performance: Performance tests
```###
# Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["ticket_analyzer"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
    "*/migrations/*",
    "ticket_analyzer/__main__.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:"
]
show_missing = true
skip_covered = false
```

## Unit Testing

### Unit Test Structure

```python
# tests/test_models/test_ticket.py
import pytest
from datetime import datetime, timedelta
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.exceptions import ValidationError

class TestTicket:
    """Test cases for Ticket model."""
    
    def test_ticket_creation_with_valid_data(self):
        """Test ticket creation with valid data."""
        ticket = Ticket(
            id="T123456",
            title="Test ticket",
            description="Test description",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert ticket.id == "T123456"
        assert ticket.title == "Test ticket"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.severity == TicketSeverity.SEV_3
    
    def test_is_resolved_when_status_resolved(self):
        """Test is_resolved returns True for resolved tickets."""
        resolved_date = datetime.now()
        ticket = Ticket(
            id="T123",
            title="Test",
            description="Test",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now() - timedelta(days=1),
            updated_date=datetime.now(),
            resolved_date=resolved_date
        )
        
        assert ticket.is_resolved() is True
    
    def test_is_resolved_when_status_open(self):
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
    
    def test_resolution_time_calculation(self):
        """Test resolution time calculation."""
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
    
    def test_resolution_time_for_unresolved_ticket(self):
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
```### T
est Fixtures and Factories

```python
# tests/conftest.py
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import factory
from factory import fuzzy

from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.config import AuthConfig, ReportConfig

# Test Factories
class TicketFactory(factory.Factory):
    """Factory for creating test tickets."""
    
    class Meta:
        model = Ticket
    
    id = factory.Sequence(lambda n: f"T{n:06d}")
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=200)
    status = fuzzy.FuzzyChoice([status for status in TicketStatus])
    severity = fuzzy.FuzzyChoice([severity for severity in TicketSeverity])
    created_date = factory.Faker('date_time_this_year')
    updated_date = factory.LazyAttribute(lambda obj: obj.created_date + timedelta(hours=1))
    assignee = factory.Faker('user_name')
    resolver_group = factory.Faker('company')

class ResolvedTicketFactory(TicketFactory):
    """Factory for resolved tickets."""
    
    status = TicketStatus.RESOLVED
    resolved_date = factory.LazyAttribute(lambda obj: obj.updated_date + timedelta(hours=2))

# Fixtures
@pytest.fixture
def sample_ticket() -> Ticket:
    """Provide a sample ticket for testing."""
    return TicketFactory()

@pytest.fixture
def sample_tickets() -> List[Ticket]:
    """Provide multiple sample tickets for testing."""
    return TicketFactory.build_batch(10)

@pytest.fixture
def resolved_tickets() -> List[Ticket]:
    """Provide resolved tickets for testing."""
    return ResolvedTicketFactory.build_batch(5)

@pytest.fixture
def sample_ticket_data() -> Dict[str, Any]:
    """Provide sample ticket data dictionary."""
    return {
        "id": "T123456",
        "title": "Test ticket",
        "description": "Test description",
        "status": "Open",
        "severity": "SEV_3",
        "created_date": "2024-01-01T10:00:00Z",
        "updated_date": "2024-01-01T11:00:00Z",
        "assignee": "testuser",
        "resolver_group": "Test Team"
    }

@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    with patch('ticket_analyzer.external.mcp_client.MCPClient') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_authenticator():
    """Mock authenticator for testing."""
    with patch('ticket_analyzer.auth.midway_auth.MidwayAuthenticator') as mock:
        mock_instance = Mock()
        mock_instance.is_authenticated.return_value = True
        mock_instance.authenticate.return_value = True
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary configuration file."""
    config_file = tmp_path / "config.json"
    config_data = {
        "authentication": {
            "timeout_seconds": 60,
            "max_retry_attempts": 3
        },
        "output": {
            "default_format": "json",
            "max_results": 100
        }
    }
    
    import json
    config_file.write_text(json.dumps(config_data))
    return str(config_file)
```###
 Mocking External Dependencies

```python
# tests/test_repositories/test_mcp_ticket_repository.py
import pytest
from unittest.mock import Mock, patch, call
from ticket_analyzer.data_retrieval.mcp_ticket_repository import MCPTicketRepository
from ticket_analyzer.models.search_criteria import SearchCriteria
from ticket_analyzer.models.exceptions import DataRetrievalError

class TestMCPTicketRepository:
    """Test cases for MCP ticket repository."""
    
    def test_find_by_id_success(self, mock_mcp_client, sample_ticket_data):
        """Test successful ticket retrieval by ID."""
        # Arrange
        mock_mcp_client.get_ticket.return_value = sample_ticket_data
        mock_validator = Mock()
        mock_sanitizer = Mock()
        mock_sanitizer.sanitize_ticket_data.return_value = sample_ticket_data
        
        repo = MCPTicketRepository(
            mcp_client=mock_mcp_client,
            validator=mock_validator,
            sanitizer=mock_sanitizer
        )
        
        # Act
        ticket = repo.find_by_id("T123456")
        
        # Assert
        assert ticket is not None
        assert ticket.id == "T123456"
        mock_mcp_client.get_ticket.assert_called_once_with("T123456")
        mock_sanitizer.sanitize_ticket_data.assert_called_once_with(sample_ticket_data)
    
    def test_find_by_id_not_found(self, mock_mcp_client):
        """Test ticket not found scenario."""
        # Arrange
        mock_mcp_client.get_ticket.return_value = None
        mock_validator = Mock()
        mock_sanitizer = Mock()
        
        repo = MCPTicketRepository(
            mcp_client=mock_mcp_client,
            validator=mock_validator,
            sanitizer=mock_sanitizer
        )
        
        # Act
        ticket = repo.find_by_id("NONEXISTENT")
        
        # Assert
        assert ticket is None
        mock_mcp_client.get_ticket.assert_called_once_with("NONEXISTENT")
    
    @patch('ticket_analyzer.data_retrieval.mcp_ticket_repository.logger')
    def test_find_by_id_mcp_error(self, mock_logger, mock_mcp_client):
        """Test MCP error handling."""
        # Arrange
        from ticket_analyzer.external.mcp_client import MCPError
        mock_mcp_client.get_ticket.side_effect = MCPError("Connection failed")
        mock_validator = Mock()
        mock_sanitizer = Mock()
        
        repo = MCPTicketRepository(
            mcp_client=mock_mcp_client,
            validator=mock_validator,
            sanitizer=mock_sanitizer
        )
        
        # Act
        ticket = repo.find_by_id("T123456")
        
        # Assert
        assert ticket is None
        mock_logger.error.assert_called_once()
    
    def test_search_tickets_with_criteria(self, mock_mcp_client, sample_ticket_data):
        """Test ticket search with criteria."""
        # Arrange
        mock_mcp_client.search_tickets.return_value = [sample_ticket_data]
        mock_validator = Mock()
        mock_validator.validate_ticket_filters.return_value = {"status": ["Open"]}
        mock_sanitizer = Mock()
        mock_sanitizer.sanitize_ticket_data.return_value = sample_ticket_data
        
        repo = MCPTicketRepository(
            mcp_client=mock_mcp_client,
            validator=mock_validator,
            sanitizer=mock_sanitizer
        )
        
        criteria = SearchCriteria(status=["Open"], max_results=10)
        
        # Act
        tickets = repo.search_tickets(criteria)
        
        # Assert
        assert len(tickets) == 1
        assert tickets[0].id == "T123456"
        mock_validator.validate_ticket_filters.assert_called_once()
        mock_mcp_client.search_tickets.assert_called_once()
```## Inte
gration Testing

### Integration Test Structure

```python
# tests/integration/test_ticket_analysis_flow.py
import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
from ticket_analyzer.cli.main import cli
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity

class TestTicketAnalysisIntegration:
    """Integration tests for ticket analysis flow."""
    
    @patch('ticket_analyzer.external.mcp_client.MCPClient')
    @patch('ticket_analyzer.auth.midway_auth.MidwayAuthenticator')
    def test_full_analysis_flow(self, mock_auth, mock_mcp_client, 
                               sample_ticket_data, tmp_path):
        """Test complete analysis flow from CLI to output."""
        # Arrange
        mock_auth_instance = Mock()
        mock_auth_instance.ensure_authenticated.return_value = None
        mock_auth.return_value = mock_auth_instance
        
        mock_client_instance = Mock()
        mock_client_instance.search_tickets.return_value = [sample_ticket_data]
        mock_mcp_client.return_value = mock_client_instance
        
        output_file = tmp_path / "results.json"
        
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, [
            'analyze',
            '--format', 'json',
            '--output', str(output_file),
            '--status', 'Open',
            '--max-results', '10'
        ])
        
        # Assert
        assert result.exit_code == 0
        assert output_file.exists()
        
        # Verify output content
        import json
        with open(output_file) as f:
            data = json.load(f)
        
        assert "metrics" in data
        assert "total_tickets" in data
        assert data["total_tickets"] >= 0
    
    @patch('ticket_analyzer.external.mcp_client.MCPClient')
    @patch('ticket_analyzer.auth.midway_auth.MidwayAuthenticator')
    def test_authentication_failure_handling(self, mock_auth, mock_mcp_client):
        """Test handling of authentication failures."""
        # Arrange
        from ticket_analyzer.models.exceptions import AuthenticationError
        mock_auth_instance = Mock()
        mock_auth_instance.ensure_authenticated.side_effect = AuthenticationError("Auth failed")
        mock_auth.return_value = mock_auth_instance
        
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, ['analyze', '--status', 'Open'])
        
        # Assert
        assert result.exit_code != 0
        assert "Authentication" in result.output or "Auth" in result.output
    
    def test_configuration_loading_integration(self, temp_config_file):
        """Test configuration loading integration."""
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, [
            'config',
            'validate',
            '--config-file', temp_config_file
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

class TestServiceIntegration:
    """Integration tests for service layer."""
    
    def test_analysis_service_integration(self, sample_tickets, mock_mcp_client):
        """Test analysis service with real data processing."""
        from ticket_analyzer.analysis.analysis_service import AnalysisService
        from ticket_analyzer.analysis.calculators import ResolutionTimeCalculator
        
        # Arrange
        service = AnalysisService()
        service.add_calculator(ResolutionTimeCalculator())
        
        # Act
        result = service.analyze_tickets(sample_tickets)
        
        # Assert
        assert result is not None
        assert hasattr(result, 'metrics')
        assert hasattr(result, 'ticket_count')
        assert result.ticket_count == len(sample_tickets)
    
    def test_report_generation_integration(self, sample_tickets, tmp_path):
        """Test report generation integration."""
        from ticket_analyzer.analysis.analysis_service import AnalysisService
        from ticket_analyzer.reporting.html_reporter import HTMLReporter
        from ticket_analyzer.analysis.calculators import ResolutionTimeCalculator
        
        # Arrange
        analysis_service = AnalysisService()
        analysis_service.add_calculator(ResolutionTimeCalculator())
        
        reporter = HTMLReporter()
        output_file = tmp_path / "report.html"
        
        # Act
        analysis_result = analysis_service.analyze_tickets(sample_tickets)
        report_path = reporter.generate_report(analysis_result, str(output_file))
        
        # Assert
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Verify HTML content
        content = output_file.read_text()
        assert "<html" in content
        assert "ticket" in content.lower()
```## 
Security Testing

### Security Test Patterns

```python
# tests/security/test_input_validation.py
import pytest
from ticket_analyzer.security.validation import SecurityValidator, ValidationResult

class TestSecurityValidator:
    """Security validation tests."""
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        malicious_inputs = [
            "'; DROP TABLE tickets; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "admin'/*",
            "1; DELETE FROM tickets"
        ]
        
        for malicious_input in malicious_inputs:
            result = SecurityValidator.validate_input(
                malicious_input, 
                "search_term", 
                "test_field"
            )
            assert not result.is_valid
            assert any("Security issue" in error for error in result.errors)
    
    def test_xss_prevention(self):
        """Test XSS attack prevention."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "onmouseover=alert('xss')"
        ]
        
        for xss_input in xss_inputs:
            result = SecurityValidator.validate_input(
                xss_input, 
                "description", 
                "test_field"
            )
            assert not result.is_valid
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention."""
        path_traversal_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f",
            "....//....//",
            "..%252f..%252f"
        ]
        
        for traversal_input in path_traversal_inputs:
            result = SecurityValidator.validate_input(
                traversal_input, 
                "filename", 
                "test_field"
            )
            assert not result.is_valid
    
    def test_valid_input_acceptance(self):
        """Test that valid inputs are accepted."""
        valid_inputs = {
            "ticket_id": "T123456",
            "username": "john.doe",
            "search_term": "error in production",
            "date_iso": "2024-01-01"
        }
        
        for input_type, valid_input in valid_inputs.items():
            result = SecurityValidator.validate_input(
                valid_input, 
                input_type, 
                "test_field"
            )
            assert result.is_valid

# tests/security/test_data_sanitization.py
class TestDataSanitization:
    """Data sanitization security tests."""
    
    def test_pii_detection_and_removal(self):
        """Test PII detection and sanitization."""
        from ticket_analyzer.security.sanitizer import AdvancedPIIDetector
        
        text_with_pii = """
        Contact John Doe at john.doe@company.com or call 555-123-4567.
        His SSN is 123-45-6789 and credit card is 4532-1234-5678-9012.
        AWS Account: 123456789012
        """
        
        # Detect PII
        pii_detections = AdvancedPIIDetector.detect_pii_with_context(text_with_pii)
        
        assert len(pii_detections) > 0
        detected_types = {detection['type'] for detection in pii_detections}
        expected_types = {'email', 'phone', 'ssn', 'credit_card', 'aws_account'}
        assert detected_types.intersection(expected_types)
        
        # Sanitize PII
        sanitized_text = AdvancedPIIDetector.sanitize_with_preservation(text_with_pii)
        
        # Verify PII is removed
        assert "john.doe@company.com" not in sanitized_text
        assert "555-123-4567" not in sanitized_text
        assert "123-45-6789" not in sanitized_text
        assert "4532-1234-5678-9012" not in sanitized_text
        assert "123456789012" not in sanitized_text
    
    def test_log_sanitization(self):
        """Test log message sanitization."""
        from ticket_analyzer.security.logging import LogSanitizer
        
        sanitizer = LogSanitizer()
        
        log_message = "User login failed for password=secret123 token=abc123xyz"
        sanitized = sanitizer.sanitize_text(log_message)
        
        assert "secret123" not in sanitized
        assert "abc123xyz" not in sanitized
        assert "[REDACTED]" in sanitized
```## P
erformance Testing

### Performance Test Framework

```python
# tests/performance/test_large_dataset_processing.py
import pytest
import time
from typing import List
from ticket_analyzer.analysis.analysis_service import AnalysisService
from ticket_analyzer.models.ticket import Ticket

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
    
    @pytest.mark.performance
    def test_memory_usage_large_dataset(self):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        # Arrange
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        large_dataset = self._create_large_ticket_dataset(50000)
        service = AnalysisService()
        
        # Act
        result = service.analyze_tickets(large_dataset)
        
        # Assert
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB for 50k tickets)
        assert memory_increase < 500
        assert result.ticket_count == 50000
    
    @pytest.mark.performance
    def test_concurrent_processing_performance(self):
        """Test performance under concurrent load."""
        import concurrent.futures
        import threading
        
        def process_batch(batch_id: int) -> float:
            dataset = self._create_large_ticket_dataset(1000)
            service = AnalysisService()
            
            start_time = time.time()
            service.analyze_tickets(dataset)
            return time.time() - start_time
        
        # Act - Process 10 batches concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_batch, i) for i in range(10)]
            processing_times = [future.result() for future in futures]
        
        # Assert
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        
        assert avg_processing_time < 2.0  # Average should be under 2 seconds
        assert max_processing_time < 5.0  # No single batch should take over 5 seconds
    
    def _create_large_ticket_dataset(self, count: int) -> List[Ticket]:
        """Create large dataset for performance testing."""
        from tests.conftest import TicketFactory
        return TicketFactory.build_batch(count)

# tests/performance/test_memory_profiling.py
@pytest.mark.performance
class TestMemoryProfiling:
    """Memory profiling tests."""
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        service = AnalysisService()
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss
        
        # Perform repeated operations
        for i in range(100):
            dataset = self._create_small_dataset(100)
            result = service.analyze_tickets(dataset)
            
            # Force cleanup
            del dataset
            del result
            
            if i % 10 == 0:
                gc.collect()
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss
        memory_growth = (final_memory - baseline_memory) / 1024 / 1024  # MB
        
        # Memory growth should be minimal (less than 50MB)
        assert memory_growth < 50
    
    def _create_small_dataset(self, count: int) -> List[Ticket]:
        """Create small dataset for repeated testing."""
        from tests.conftest import TicketFactory
        return TicketFactory.build_batch(count)
```#
# Test Execution and Coverage

### Running Tests

#### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m "not slow"             # Exclude slow tests
pytest -m security               # Security tests only

# Run tests with coverage
pytest --cov=ticket_analyzer --cov-report=html

# Run tests in parallel (with pytest-xdist)
pytest -n auto

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_models/test_ticket.py

# Run specific test method
pytest tests/test_models/test_ticket.py::TestTicket::test_ticket_creation
```

#### Continuous Integration

```bash
# CI test script
#!/bin/bash
set -e

echo "Running linting..."
flake8 ticket_analyzer tests

echo "Running type checking..."
mypy ticket_analyzer

echo "Running security checks..."
bandit -r ticket_analyzer

echo "Running unit tests..."
pytest -m "unit and not slow" --cov=ticket_analyzer --cov-report=xml

echo "Running integration tests..."
pytest -m integration --cov=ticket_analyzer --cov-append --cov-report=xml

echo "Checking coverage threshold..."
coverage report --fail-under=80

echo "All tests passed!"
```

### Coverage Requirements

#### Coverage Targets

| Module Type | Minimum Coverage | Target Coverage |
|-------------|------------------|-----------------|
| Core Models | 95% | 100% |
| Business Logic | 85% | 95% |
| CLI Commands | 80% | 90% |
| External Integrations | 70% | 85% |
| Utilities | 80% | 90% |

#### Coverage Analysis

```bash
# Generate detailed coverage report
pytest --cov=ticket_analyzer --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html

# Check coverage for specific module
pytest --cov=ticket_analyzer.models --cov-report=term-missing

# Generate coverage badge
coverage-badge -o coverage.svg
```

### Test Data Management

#### Test Data Strategies

```python
# tests/data/test_data_manager.py
import json
from pathlib import Path
from typing import Dict, Any, List

class TestDataManager:
    """Manage test data files and fixtures."""
    
    def __init__(self, data_dir: Path = None):
        self._data_dir = data_dir or Path(__file__).parent / "fixtures"
        self._data_dir.mkdir(exist_ok=True)
    
    def load_test_data(self, filename: str) -> Dict[str, Any]:
        """Load test data from JSON file."""
        file_path = self._data_dir / f"{filename}.json"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def save_test_data(self, filename: str, data: Dict[str, Any]) -> None:
        """Save test data to JSON file."""
        file_path = self._data_dir / f"{filename}.json"
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def create_sample_tickets(self, count: int = 10) -> List[Dict[str, Any]]:
        """Create sample ticket data for testing."""
        from tests.conftest import TicketFactory
        
        tickets = TicketFactory.build_batch(count)
        return [
            {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status.value,
                "severity": ticket.severity.value,
                "created_date": ticket.created_date.isoformat(),
                "updated_date": ticket.updated_date.isoformat(),
                "assignee": ticket.assignee,
                "resolver_group": ticket.resolver_group
            }
            for ticket in tickets
        ]

# Usage in tests
@pytest.fixture
def test_data_manager():
    """Provide test data manager."""
    return TestDataManager()

@pytest.fixture
def sample_api_response(test_data_manager):
    """Load sample API response data."""
    return test_data_manager.load_test_data("sample_api_response")
```