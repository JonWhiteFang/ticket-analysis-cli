"""Tests for data processor module.

This module contains comprehensive tests for the TicketDataProcessor class,
covering data validation, cleaning, normalization, and edge case handling
according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from ticket_analyzer.analysis.data_processor import TicketDataProcessor
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.exceptions import DataProcessingError


class TestTicketDataProcessor:
    """Test cases for TicketDataProcessor class."""
    
    def test_processor_initialization(self):
        """Test data processor initialization."""
        processor = TicketDataProcessor()
        
        assert processor._validation_rules is not None
        assert processor._cleaning_rules is not None
        assert processor._normalization_rules is not None
    
    def test_validate_ticket_success(self):
        """Test successful ticket validation."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Valid ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor.validate_ticket(ticket)
        
        assert result is True
    
    def test_validate_ticket_missing_required_fields(self):
        """Test ticket validation with missing required fields."""
        processor = TicketDataProcessor()
        
        # Create ticket with missing title
        ticket = Ticket(
            id="T123456",
            title="",  # Empty title
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor.validate_ticket(ticket)
        
        assert result is False
    
    def test_validate_ticket_invalid_id_format(self):
        """Test ticket validation with invalid ID format."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="INVALID_ID",  # Invalid format
            title="Valid title",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor.validate_ticket(ticket)
        
        assert result is False
    
    def test_validate_ticket_future_created_date(self):
        """Test ticket validation with future created date."""
        processor = TicketDataProcessor()
        
        future_date = datetime.now() + timedelta(days=1)
        ticket = Ticket(
            id="T123456",
            title="Future ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=future_date
        )
        
        result = processor.validate_ticket(ticket)
        
        assert result is False
    
    def test_validate_ticket_invalid_resolution_date(self):
        """Test ticket validation with invalid resolution date."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Invalid resolution",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 2, 10, 0),
            resolved_date=datetime(2024, 1, 1, 10, 0)  # Before created date
        )
        
        result = processor.validate_ticket(ticket)
        
        assert result is False
    
    def test_validate_ticket_none_input(self):
        """Test ticket validation with None input."""
        processor = TicketDataProcessor()
        
        result = processor.validate_ticket(None)
        
        assert result is False
    
    def test_process_ticket_success(self):
        """Test successful ticket processing."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="t123456",  # Lowercase ID
            title="  Test Ticket  ",  # Extra whitespace
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        processed_ticket = processor.process_ticket(ticket)
        
        assert processed_ticket.id == "T123456"  # Normalized to uppercase
        assert processed_ticket.title == "Test Ticket"  # Trimmed whitespace
        assert processed_ticket.status == TicketStatus.OPEN
        assert processed_ticket.severity == TicketSeverity.MEDIUM
    
    def test_process_ticket_clean_title(self):
        """Test ticket processing with title cleaning."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Test\nTicket\twith\rSpecial\x00Characters",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        processed_ticket = processor.process_ticket(ticket)
        
        # Should clean special characters
        assert "\n" not in processed_ticket.title
        assert "\t" not in processed_ticket.title
        assert "\r" not in processed_ticket.title
        assert "\x00" not in processed_ticket.title
    
    def test_process_ticket_normalize_assignee(self):
        """Test ticket processing with assignee normalization."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Test ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0),
            assignee="  USER@DOMAIN.COM  "  # Mixed case with whitespace
        )
        
        processed_ticket = processor.process_ticket(ticket)
        
        assert processed_ticket.assignee == "user@domain.com"  # Normalized
    
    def test_process_ticket_handle_missing_optional_fields(self):
        """Test ticket processing with missing optional fields."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Minimal ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
            # No assignee, resolved_date, etc.
        )
        
        processed_ticket = processor.process_ticket(ticket)
        
        assert processed_ticket.id == "T123456"
        assert processed_ticket.title == "Minimal ticket"
        assert processed_ticket.assignee is None
        assert processed_ticket.resolved_date is None
    
    def test_clean_text_field_basic(self):
        """Test basic text field cleaning."""
        processor = TicketDataProcessor()
        
        dirty_text = "  Test\nText\twith\rSpecial\x00Chars  "
        
        cleaned_text = processor._clean_text_field(dirty_text)
        
        assert cleaned_text == "Test Text with Special Chars"
    
    def test_clean_text_field_empty_input(self):
        """Test text cleaning with empty input."""
        processor = TicketDataProcessor()
        
        assert processor._clean_text_field("") == ""
        assert processor._clean_text_field("   ") == ""
        assert processor._clean_text_field(None) == ""
    
    def test_clean_text_field_unicode_handling(self):
        """Test text cleaning with Unicode characters."""
        processor = TicketDataProcessor()
        
        unicode_text = "Test with émojis 🎉 and ñoñó"
        
        cleaned_text = processor._clean_text_field(unicode_text)
        
        # Should preserve valid Unicode characters
        assert "émojis" in cleaned_text
        assert "ñoñó" in cleaned_text
        assert "🎉" in cleaned_text
    
    def test_normalize_id_format(self):
        """Test ID format normalization."""
        processor = TicketDataProcessor()
        
        test_cases = [
            ("t123456", "T123456"),
            ("T123456", "T123456"),
            ("abc-123", "ABC-123"),
            ("  t123  ", "T123"),
        ]
        
        for input_id, expected in test_cases:
            result = processor._normalize_id_format(input_id)
            assert result == expected
    
    def test_normalize_id_format_invalid_input(self):
        """Test ID normalization with invalid input."""
        processor = TicketDataProcessor()
        
        invalid_ids = ["", "   ", None, "123", "TOOLONG123456789012345"]
        
        for invalid_id in invalid_ids:
            result = processor._normalize_id_format(invalid_id)
            assert result == invalid_id  # Should return as-is for invalid input
    
    def test_normalize_assignee_format(self):
        """Test assignee format normalization."""
        processor = TicketDataProcessor()
        
        test_cases = [
            ("USER@DOMAIN.COM", "user@domain.com"),
            ("  user@domain.com  ", "user@domain.com"),
            ("User.Name@Company.Com", "user.name@company.com"),
            ("", ""),
            (None, None),
        ]
        
        for input_assignee, expected in test_cases:
            result = processor._normalize_assignee_format(input_assignee)
            assert result == expected
    
    def test_validate_date_fields_success(self):
        """Test successful date field validation."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Valid dates",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0),
            resolved_date=datetime(2024, 1, 2, 14, 0)
        )
        
        result = processor._validate_date_fields(ticket)
        
        assert result is True
    
    def test_validate_date_fields_future_created_date(self):
        """Test date validation with future created date."""
        processor = TicketDataProcessor()
        
        future_date = datetime.now() + timedelta(days=1)
        ticket = Ticket(
            id="T123456",
            title="Future ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=future_date
        )
        
        result = processor._validate_date_fields(ticket)
        
        assert result is False
    
    def test_validate_date_fields_resolution_before_creation(self):
        """Test date validation with resolution before creation."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Invalid resolution",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 2, 10, 0),
            resolved_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor._validate_date_fields(ticket)
        
        assert result is False
    
    def test_validate_required_fields_success(self):
        """Test successful required fields validation."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Valid ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor._validate_required_fields(ticket)
        
        assert result is True
    
    def test_validate_required_fields_missing_id(self):
        """Test required fields validation with missing ID."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="",  # Empty ID
            title="Valid title",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor._validate_required_fields(ticket)
        
        assert result is False
    
    def test_validate_required_fields_missing_title(self):
        """Test required fields validation with missing title."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="",  # Empty title
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        result = processor._validate_required_fields(ticket)
        
        assert result is False
    
    def test_validate_business_rules_resolved_ticket_without_date(self):
        """Test business rules validation for resolved ticket without date."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Resolved without date",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
            # No resolved_date
        )
        
        result = processor._validate_business_rules(ticket)
        
        assert result is False
    
    def test_validate_business_rules_open_ticket_with_resolution_date(self):
        """Test business rules validation for open ticket with resolution date."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Open with resolution date",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0),
            resolved_date=datetime(2024, 1, 2, 10, 0)  # Shouldn't have this
        )
        
        result = processor._validate_business_rules(ticket)
        
        assert result is False
    
    def test_handle_missing_data_with_defaults(self):
        """Test handling missing data with default values."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="Ticket with missing data",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
            # Missing optional fields
        )
        
        processed_ticket = processor._handle_missing_data(ticket)
        
        # Should set appropriate defaults
        assert processed_ticket.assignee is None
        assert processed_ticket.resolved_date is None
        assert processed_ticket.description is None
    
    def test_detect_data_quality_issues(self):
        """Test data quality issue detection."""
        processor = TicketDataProcessor()
        
        # Create ticket with potential quality issues
        ticket = Ticket(
            id="T123456",
            title="a",  # Very short title
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0),
            assignee="invalid-email-format"  # Invalid email
        )
        
        issues = processor._detect_data_quality_issues(ticket)
        
        assert isinstance(issues, list)
        assert len(issues) > 0
        
        # Should detect short title and invalid email
        issue_types = [issue['type'] for issue in issues]
        assert 'short_title' in issue_types
        assert 'invalid_assignee_format' in issue_types
    
    def test_detect_data_quality_issues_clean_ticket(self):
        """Test data quality detection with clean ticket."""
        processor = TicketDataProcessor()
        
        ticket = Ticket(
            id="T123456",
            title="This is a properly formatted ticket title",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0),
            assignee="user@company.com"
        )
        
        issues = processor._detect_data_quality_issues(ticket)
        
        assert isinstance(issues, list)
        assert len(issues) == 0
    
    def test_batch_process_tickets(self):
        """Test batch processing of multiple tickets."""
        processor = TicketDataProcessor()
        
        tickets = [
            Ticket(
                id="t123456",  # Needs normalization
                title="  Ticket 1  ",  # Needs cleaning
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1, 10, 0)
            ),
            Ticket(
                id="T789012",
                title="Ticket 2",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.HIGH,
                created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 2, 10, 0)
            ),
            Ticket(
                id="",  # Invalid ticket
                title="Invalid ticket",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1, 10, 0)
            )
        ]
        
        processed_tickets = processor.batch_process_tickets(tickets)
        
        # Should return only valid, processed tickets
        assert len(processed_tickets) == 2  # Invalid ticket filtered out
        assert processed_tickets[0].id == "T123456"  # Normalized
        assert processed_tickets[0].title == "Ticket 1"  # Cleaned
        assert processed_tickets[1].id == "T789012"
    
    def test_batch_process_tickets_empty_list(self):
        """Test batch processing with empty list."""
        processor = TicketDataProcessor()
        
        result = processor.batch_process_tickets([])
        
        assert result == []
    
    def test_batch_process_tickets_all_invalid(self):
        """Test batch processing where all tickets are invalid."""
        processor = TicketDataProcessor()
        
        invalid_tickets = [
            Ticket(
                id="",  # Invalid
                title="",  # Invalid
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1, 10, 0)
            ),
            Ticket(
                id="INVALID",  # Invalid format
                title="Valid title",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime.now() + timedelta(days=1)  # Future date
            )
        ]
        
        result = processor.batch_process_tickets(invalid_tickets)
        
        assert result == []


class TestTicketDataProcessorErrorHandling:
    """Test error handling for TicketDataProcessor."""
    
    def test_process_ticket_with_none_input(self):
        """Test processing with None input."""
        processor = TicketDataProcessor()
        
        with pytest.raises((ValueError, TypeError)):
            processor.process_ticket(None)
    
    def test_process_ticket_with_invalid_type(self):
        """Test processing with invalid input type."""
        processor = TicketDataProcessor()
        
        with pytest.raises((ValueError, TypeError)):
            processor.process_ticket("not a ticket")
    
    def test_batch_process_tickets_with_none_input(self):
        """Test batch processing with None input."""
        processor = TicketDataProcessor()
        
        with pytest.raises((ValueError, TypeError)):
            processor.batch_process_tickets(None)
    
    def test_batch_process_tickets_with_invalid_type(self):
        """Test batch processing with invalid input type."""
        processor = TicketDataProcessor()
        
        with pytest.raises((ValueError, TypeError)):
            processor.batch_process_tickets("not a list")
    
    @patch('ticket_analyzer.analysis.data_processor.logger')
    def test_error_logging_during_processing(self, mock_logger):
        """Test error logging during ticket processing."""
        processor = TicketDataProcessor()
        
        # Create ticket that will cause processing issues
        ticket = Ticket(
            id="T123456",
            title="Test ticket",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.MEDIUM,
            created_date=datetime(2024, 1, 1, 10, 0)
        )
        
        # Mock a method to raise an exception
        with patch.object(processor, '_clean_text_field', side_effect=Exception("Processing error")):
            with pytest.raises(DataProcessingError):
                processor.process_ticket(ticket)
        
        # Should log the error
        mock_logger.error.assert_called()


class TestTicketDataProcessorPerformance:
    """Test performance aspects of TicketDataProcessor."""
    
    def test_batch_processing_performance(self):
        """Test performance of batch processing with large dataset."""
        processor = TicketDataProcessor()
        
        # Create large dataset
        large_ticket_list = []
        for i in range(1000):
            ticket = Ticket(
                id=f"T{i:06d}",
                title=f"Test ticket {i}",
                status=TicketStatus.OPEN if i % 2 == 0 else TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1) + timedelta(hours=i)
            )
            large_ticket_list.append(ticket)
        
        # Should process without timeout
        result = processor.batch_process_tickets(large_ticket_list)
        
        assert len(result) == 1000
        assert all(isinstance(ticket, Ticket) for ticket in result)
    
    def test_memory_efficiency_large_dataset(self):
        """Test memory efficiency with large dataset."""
        processor = TicketDataProcessor()
        
        # Process tickets one by one to test memory usage
        for i in range(100):
            ticket = Ticket(
                id=f"T{i:06d}",
                title=f"Test ticket {i}",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1) + timedelta(hours=i)
            )
            
            processed = processor.process_ticket(ticket)
            assert processed.id == f"T{i:06d}"
        
        # Should complete without memory issues