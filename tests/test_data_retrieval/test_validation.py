"""Tests for data retrieval validation module.

This module contains unit tests for input validation, data sanitization,
and security measures in the data retrieval layer.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch

from ticket_analyzer.data_retrieval.validation import (
    InputValidator,
    SearchCriteriaValidator,
    TicketDataValidator
)
from ticket_analyzer.models import (
    SearchCriteria,
    ValidationError,
    TicketStatus,
    TicketSeverity
)


class TestInputValidator:
    """Test cases for InputValidator class."""
    
    def test_validate_ticket_id_valid_formats(self) -> None:
        """Test validation of valid ticket ID formats."""
        validator = InputValidator()
        
        valid_ids = [
            "T123456",
            "P789012",
            "CFN-12345",
            "SWIM-98765",
            "ABC-123"
        ]
        
        for ticket_id in valid_ids:
            assert validator.validate_ticket_id(ticket_id) is True
    
    def test_validate_ticket_id_invalid_formats(self) -> None:
        """Test validation of invalid ticket ID formats."""
        validator = InputValidator()
        
        invalid_ids = [
            "",  # Empty string
            "123456",  # No prefix
            "T",  # No number
            "T-",  # No number after dash
            "TOOLONG-123456789012345",  # Too long prefix
            "T123456789012345678901",  # Too long number
            "T123@456",  # Invalid characters
            "T 123456",  # Space in ID
            "t123456",  # Lowercase prefix
        ]
        
        for ticket_id in invalid_ids:
            assert validator.validate_ticket_id(ticket_id) is False
    
    def test_validate_username_valid_formats(self) -> None:
        """Test validation of valid username formats."""
        validator = InputValidator()
        
        valid_usernames = [
            "testuser",
            "test.user",
            "test_user",
            "test-user",
            "user123",
            "a",  # Single character
            "a" * 50  # Maximum length
        ]
        
        for username in valid_usernames:
            assert validator.validate_username(username) is True
    
    def test_validate_username_invalid_formats(self) -> None:
        """Test validation of invalid username formats."""
        validator = InputValidator()
        
        invalid_usernames = [
            "",  # Empty string
            "test user",  # Space
            "test@user",  # Invalid character
            "test#user",  # Invalid character
            "a" * 51,  # Too long
            "Test.User",  # Uppercase letters
        ]
        
        for username in invalid_usernames:
            assert validator.validate_username(username) is False
    
    def test_validate_date_string_valid_formats(self) -> None:
        """Test validation of valid date string formats."""
        validator = InputValidator()
        
        valid_dates = [
            "2024-01-01",
            "2024-12-31",
            "2023-02-28",
            "2024-02-29",  # Leap year
        ]
        
        for date_str in valid_dates:
            assert validator.validate_date_string(date_str) is True
    
    def test_validate_date_string_invalid_formats(self) -> None:
        """Test validation of invalid date string formats."""
        validator = InputValidator()
        
        invalid_dates = [
            "",  # Empty string
            "2024-1-1",  # Single digit month/day
            "24-01-01",  # Two digit year
            "2024/01/01",  # Wrong separator
            "2024-13-01",  # Invalid month
            "2024-01-32",  # Invalid day
            "2023-02-29",  # Not a leap year
            "not-a-date",  # Invalid format
        ]
        
        for date_str in invalid_dates:
            assert validator.validate_date_string(date_str) is False
    
    def test_sanitize_search_term_basic(self) -> None:
        """Test basic search term sanitization."""
        validator = InputValidator()
        
        test_cases = [
            ("normal search", "normal search"),
            ("search with-dashes", "search with-dashes"),
            ("search.with.dots", "search.with.dots"),
            ("search_with_underscores", "search_with_underscores"),
            ("search123", "search123"),
        ]
        
        for input_term, expected in test_cases:
            result = validator.sanitize_search_term(input_term)
            assert result == expected
    
    def test_sanitize_search_term_removes_dangerous_chars(self) -> None:
        """Test that dangerous characters are removed from search terms."""
        validator = InputValidator()
        
        test_cases = [
            ("search<script>", "searchscript"),
            ("search&amp;", "searchamp"),
            ("search'OR'1'='1", "searchOR11"),
            ("search;DROP TABLE", "searchDROP TABLE"),
            ("search%27", "search27"),
            ("search\\x00", "searchx00"),
        ]
        
        for input_term, expected in test_cases:
            result = validator.sanitize_search_term(input_term)
            assert result == expected
    
    def test_sanitize_search_term_length_limit(self) -> None:
        """Test search term length limiting."""
        validator = InputValidator()
        
        long_term = "a" * 300  # Longer than 200 character limit
        result = validator.sanitize_search_term(long_term)
        
        assert len(result) == 200
        assert result == "a" * 200
    
    def test_detect_sql_injection_attempts(self) -> None:
        """Test detection of SQL injection attempts."""
        validator = InputValidator()
        
        injection_attempts = [
            "'; DROP TABLE tickets; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO tickets VALUES --",
            "' OR 1=1 --",
            "admin'--",
            "' OR 'x'='x",
        ]
        
        for attempt in injection_attempts:
            assert validator.detect_sql_injection(attempt) is True
    
    def test_detect_sql_injection_safe_inputs(self) -> None:
        """Test that safe inputs are not flagged as SQL injection."""
        validator = InputValidator()
        
        safe_inputs = [
            "normal search term",
            "search for bug",
            "ticket about authentication",
            "error in production",
            "user reported issue",
        ]
        
        for safe_input in safe_inputs:
            assert validator.detect_sql_injection(safe_input) is False


class TestSearchCriteriaValidator:
    """Test cases for SearchCriteriaValidator class."""
    
    def test_validate_search_criteria_valid(self) -> None:
        """Test validation of valid search criteria."""
        validator = SearchCriteriaValidator()
        
        valid_criteria = SearchCriteria(
            status_filters=["Open", "Resolved"],
            severity_filters=["SEV_1", "SEV_2"],
            assignee_filter="testuser",
            resolver_group_filter="Test Team",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            max_results=100
        )
        
        assert validator.validate_search_criteria(valid_criteria) is True
    
    def test_validate_search_criteria_invalid_max_results(self) -> None:
        """Test validation fails for invalid max_results."""
        validator = SearchCriteriaValidator()
        
        # Too many results
        invalid_criteria = SearchCriteria(max_results=50000)
        assert validator.validate_search_criteria(invalid_criteria) is False
        
        # Zero results
        invalid_criteria = SearchCriteria(max_results=0)
        assert validator.validate_search_criteria(invalid_criteria) is False
        
        # Negative results
        invalid_criteria = SearchCriteria(max_results=-10)
        assert validator.validate_search_criteria(invalid_criteria) is False
    
    def test_validate_search_criteria_invalid_date_range(self) -> None:
        """Test validation fails for invalid date ranges."""
        validator = SearchCriteriaValidator()
        
        # End date before start date
        invalid_criteria = SearchCriteria(
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 1, 1)
        )
        assert validator.validate_search_criteria(invalid_criteria) is False
        
        # Date range too large (more than 1 year)
        invalid_criteria = SearchCriteria(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 6, 1)
        )
        assert validator.validate_search_criteria(invalid_criteria) is False
    
    def test_validate_search_criteria_invalid_status_filters(self) -> None:
        """Test validation fails for invalid status filters."""
        validator = SearchCriteriaValidator()
        
        invalid_criteria = SearchCriteria(
            status_filters=["InvalidStatus", "AnotherInvalid"]
        )
        assert validator.validate_search_criteria(invalid_criteria) is False
    
    def test_validate_search_criteria_invalid_severity_filters(self) -> None:
        """Test validation fails for invalid severity filters."""
        validator = SearchCriteriaValidator()
        
        invalid_criteria = SearchCriteria(
            severity_filters=["SEV_0", "SEV_10", "INVALID"]
        )
        assert validator.validate_search_criteria(invalid_criteria) is False
    
    def test_validate_search_criteria_invalid_assignee(self) -> None:
        """Test validation fails for invalid assignee format."""
        validator = SearchCriteriaValidator()
        
        invalid_criteria = SearchCriteria(
            assignee_filter="invalid@user"  # Contains invalid character
        )
        assert validator.validate_search_criteria(invalid_criteria) is False
    
    def test_validate_search_criteria_empty_filters(self) -> None:
        """Test validation of empty filter lists."""
        validator = SearchCriteriaValidator()
        
        # Empty status filters should be valid (means all statuses)
        valid_criteria = SearchCriteria(status_filters=[])
        assert validator.validate_search_criteria(valid_criteria) is True
        
        # Empty severity filters should be valid (means all severities)
        valid_criteria = SearchCriteria(severity_filters=[])
        assert validator.validate_search_criteria(valid_criteria) is True


class TestTicketDataValidator:
    """Test cases for TicketDataValidator class."""
    
    def test_validate_ticket_data_valid(self) -> None:
        """Test validation of valid ticket data."""
        validator = TicketDataValidator()
        
        valid_data = {
            "id": "T123456",
            "title": "Test ticket",
            "description": "Test description",
            "status": "Open",
            "severity": "SEV_3",
            "createDate": "2024-01-01T10:00:00Z",
            "assignee": "testuser",
            "extensions": {
                "tt": {
                    "assignedGroup": "Test Team"
                }
            }
        }
        
        assert validator.validate_ticket_data(valid_data) is True
    
    def test_validate_ticket_data_missing_required_fields(self) -> None:
        """Test validation fails for missing required fields."""
        validator = TicketDataValidator()
        
        # Missing ID
        invalid_data = {
            "title": "Test ticket",
            "status": "Open"
        }
        assert validator.validate_ticket_data(invalid_data) is False
        
        # Missing title
        invalid_data = {
            "id": "T123456",
            "status": "Open"
        }
        assert validator.validate_ticket_data(invalid_data) is False
        
        # Missing status
        invalid_data = {
            "id": "T123456",
            "title": "Test ticket"
        }
        assert validator.validate_ticket_data(invalid_data) is False
    
    def test_validate_ticket_data_invalid_field_values(self) -> None:
        """Test validation fails for invalid field values."""
        validator = TicketDataValidator()
        
        # Invalid ticket ID format
        invalid_data = {
            "id": "invalid-id",
            "title": "Test ticket",
            "status": "Open"
        }
        assert validator.validate_ticket_data(invalid_data) is False
        
        # Invalid status
        invalid_data = {
            "id": "T123456",
            "title": "Test ticket",
            "status": "InvalidStatus"
        }
        assert validator.validate_ticket_data(invalid_data) is False
        
        # Invalid severity
        invalid_data = {
            "id": "T123456",
            "title": "Test ticket",
            "status": "Open",
            "severity": "SEV_10"
        }
        assert validator.validate_ticket_data(invalid_data) is False
    
    def test_validate_ticket_data_invalid_date_formats(self) -> None:
        """Test validation fails for invalid date formats."""
        validator = TicketDataValidator()
        
        invalid_data = {
            "id": "T123456",
            "title": "Test ticket",
            "status": "Open",
            "createDate": "2024-01-01"  # Missing time component
        }
        assert validator.validate_ticket_data(invalid_data) is False
        
        invalid_data = {
            "id": "T123456",
            "title": "Test ticket",
            "status": "Open",
            "createDate": "invalid-date"
        }
        assert validator.validate_ticket_data(invalid_data) is False
    
    def test_sanitize_ticket_data_removes_sensitive_info(self) -> None:
        """Test that sensitive information is removed from ticket data."""
        validator = TicketDataValidator()
        
        sensitive_data = {
            "id": "T123456",
            "title": "Test ticket",
            "description": "User email: user@example.com, Phone: 555-123-4567",
            "status": "Open",
            "internal_notes": "Sensitive internal information",
            "private_data": "Private information"
        }
        
        sanitized = validator.sanitize_ticket_data(sensitive_data)
        
        # Sensitive fields should be removed or redacted
        assert "internal_notes" not in sanitized
        assert "private_data" not in sanitized
        
        # PII should be redacted in description
        assert "user@example.com" not in sanitized["description"]
        assert "555-123-4567" not in sanitized["description"]
        assert "[EMAIL_REDACTED]" in sanitized["description"]
        assert "[PHONE_REDACTED]" in sanitized["description"]
    
    def test_sanitize_ticket_data_preserves_safe_data(self) -> None:
        """Test that safe data is preserved during sanitization."""
        validator = TicketDataValidator()
        
        safe_data = {
            "id": "T123456",
            "title": "Test ticket",
            "description": "This is a safe description without PII",
            "status": "Open",
            "severity": "SEV_3",
            "assignee": "testuser",
            "tags": ["bug", "authentication"]
        }
        
        sanitized = validator.sanitize_ticket_data(safe_data)
        
        # All safe data should be preserved
        assert sanitized["id"] == "T123456"
        assert sanitized["title"] == "Test ticket"
        assert sanitized["description"] == "This is a safe description without PII"
        assert sanitized["status"] == "Open"
        assert sanitized["severity"] == "SEV_3"
        assert sanitized["assignee"] == "testuser"
        assert sanitized["tags"] == ["bug", "authentication"]
    
    def test_validate_ticket_list_data(self) -> None:
        """Test validation of ticket list data."""
        validator = TicketDataValidator()
        
        valid_list = [
            {
                "id": "T123456",
                "title": "Ticket 1",
                "status": "Open"
            },
            {
                "id": "T123457",
                "title": "Ticket 2",
                "status": "Resolved"
            }
        ]
        
        assert validator.validate_ticket_list_data(valid_list) is True
        
        # Invalid list with one bad ticket
        invalid_list = [
            {
                "id": "T123456",
                "title": "Ticket 1",
                "status": "Open"
            },
            {
                "id": "invalid-id",  # Invalid ID format
                "title": "Ticket 2",
                "status": "Open"
            }
        ]
        
        assert validator.validate_ticket_list_data(invalid_list) is False
    
    def test_validate_empty_ticket_list(self) -> None:
        """Test validation of empty ticket list."""
        validator = TicketDataValidator()
        
        # Empty list should be valid
        assert validator.validate_ticket_list_data([]) is True
        
        # None should be invalid
        assert validator.validate_ticket_list_data(None) is False


class TestValidationIntegration:
    """Integration tests for validation components."""
    
    def test_complete_validation_workflow(self) -> None:
        """Test complete validation workflow from search to results."""
        input_validator = InputValidator()
        criteria_validator = SearchCriteriaValidator()
        data_validator = TicketDataValidator()
        
        # 1. Validate search inputs
        ticket_id = "T123456"
        username = "testuser"
        search_term = "authentication bug"
        
        assert input_validator.validate_ticket_id(ticket_id) is True
        assert input_validator.validate_username(username) is True
        sanitized_term = input_validator.sanitize_search_term(search_term)
        assert sanitized_term == "authentication bug"
        
        # 2. Validate search criteria
        criteria = SearchCriteria(
            status_filters=["Open"],
            assignee_filter=username,
            search_term=sanitized_term,
            max_results=100
        )
        assert criteria_validator.validate_search_criteria(criteria) is True
        
        # 3. Validate ticket data results
        mock_results = [
            {
                "id": "T123456",
                "title": "Authentication bug",
                "status": "Open",
                "assignee": "testuser"
            }
        ]
        assert data_validator.validate_ticket_list_data(mock_results) is True
        
        # 4. Sanitize results
        sanitized_results = [
            data_validator.sanitize_ticket_data(ticket)
            for ticket in mock_results
        ]
        assert len(sanitized_results) == 1
        assert sanitized_results[0]["id"] == "T123456"
    
    def test_validation_error_handling(self) -> None:
        """Test proper error handling in validation chain."""
        input_validator = InputValidator()
        criteria_validator = SearchCriteriaValidator()
        
        # Test that validation errors are properly caught and handled
        with pytest.raises(ValidationError):
            # This should raise ValidationError for invalid ticket ID
            if not input_validator.validate_ticket_id("invalid-id"):
                raise ValidationError("Invalid ticket ID format")
        
        # Test that invalid criteria raises appropriate error
        invalid_criteria = SearchCriteria(max_results=-1)
        assert criteria_validator.validate_search_criteria(invalid_criteria) is False
    
    def test_performance_with_large_datasets(self) -> None:
        """Test validation performance with large datasets."""
        data_validator = TicketDataValidator()
        
        # Generate large dataset
        large_dataset = [
            {
                "id": f"T{i:06d}",
                "title": f"Test ticket {i}",
                "status": "Open",
                "description": f"Description for ticket {i}"
            }
            for i in range(1000)
        ]
        
        import time
        start_time = time.time()
        
        # Validate large dataset
        is_valid = data_validator.validate_ticket_list_data(large_dataset)
        
        # Sanitize large dataset
        sanitized = [
            data_validator.sanitize_ticket_data(ticket)
            for ticket in large_dataset
        ]
        
        end_time = time.time()
        
        assert is_valid is True
        assert len(sanitized) == 1000
        assert end_time - start_time < 5.0  # Should complete within 5 seconds