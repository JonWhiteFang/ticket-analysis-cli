"""Data processing and edge case handling for ticket analysis.

This module implements comprehensive data processing capabilities including
data validation, cleaning, normalization, and edge case handling for ticket
analysis operations. It provides robust error recovery and fallback
mechanisms for incomplete or malformed data.

The TicketDataProcessor class handles various data quality issues and
ensures that analysis operations can proceed even with imperfect data
by implementing graceful degradation and intelligent defaults.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import re

from ..models.ticket import Ticket, TicketStatus, TicketSeverity
from ..models.exceptions import DataProcessingError, ValidationError
from ..interfaces import DataValidationInterface

logger = logging.getLogger(__name__)


class TicketDataProcessor(DataValidationInterface):
    """Comprehensive data processor for ticket analysis with edge case handling.
    
    This class provides robust data processing capabilities including:
    - Data validation and quality assessment
    - Data cleaning and normalization
    - Edge case handling and error recovery
    - Fallback calculations for incomplete data
    - Data enrichment and derived field calculation
    
    The processor is designed to handle real-world data quality issues
    gracefully while maintaining data integrity and analysis accuracy.
    """
    
    def __init__(self) -> None:
        """Initialize data processor with default settings."""
        self._validation_rules = ValidationRuleEngine()
        self._data_cleaner = DataCleaner()
        self._edge_case_handler = EdgeCaseHandler()
        self._quality_assessor = DataQualityAssessor()
    
    def process_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """Process and validate tickets with comprehensive error handling.
        
        Args:
            tickets: Raw tickets to process.
            
        Returns:
            List of processed and validated tickets.
            
        Raises:
            DataProcessingError: If processing fails critically.
        """
        if not tickets:
            logger.info("No tickets provided for processing")
            return []
        
        logger.info(f"Processing {len(tickets)} tickets")
        
        try:
            # Step 1: Initial validation and filtering
            valid_tickets = self._initial_validation(tickets)
            
            # Step 2: Data cleaning and normalization
            cleaned_tickets = self._clean_and_normalize(valid_tickets)
            
            # Step 3: Edge case handling
            processed_tickets = self._handle_edge_cases(cleaned_tickets)
            
            # Step 4: Data enrichment
            enriched_tickets = self._enrich_data(processed_tickets)
            
            # Step 5: Final validation
            final_tickets = self._final_validation(enriched_tickets)
            
            logger.info(f"Successfully processed {len(final_tickets)} tickets from {len(tickets)} input")
            
            return final_tickets
            
        except Exception as e:
            logger.error(f"Ticket processing failed: {e}")
            raise DataProcessingError(f"Failed to process tickets: {e}") from e
    
    def validate_ticket_data(self, ticket_data: Dict[str, Any]) -> bool:
        """Validate ticket data structure and content.
        
        Args:
            ticket_data: Ticket data dictionary to validate.
            
        Returns:
            True if ticket data is valid, False otherwise.
        """
        return self._validation_rules.validate_ticket_structure(ticket_data)
    
    def validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate MCP response format and structure.
        
        Args:
            response: MCP response to validate.
            
        Returns:
            True if response format is valid, False otherwise.
        """
        return self._validation_rules.validate_response_structure(response)
    
    def clean_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize ticket data.
        
        Args:
            ticket_data: Raw ticket data to clean.
            
        Returns:
            Cleaned and normalized ticket data.
        """
        return self._data_cleaner.clean_ticket_dict(ticket_data)
    
    def assess_data_quality(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess overall data quality of ticket collection.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary containing data quality metrics and recommendations.
        """
        return self._quality_assessor.assess_quality(tickets)
    
    def handle_empty_datasets(self, operation_name: str) -> Dict[str, Any]:
        """Handle empty dataset scenarios with appropriate defaults.
        
        Args:
            operation_name: Name of the operation being performed.
            
        Returns:
            Dictionary with appropriate default values and messaging.
        """
        return self._edge_case_handler.handle_empty_dataset(operation_name)
    
    def handle_missing_fields(self, tickets: List[Ticket], required_fields: List[str]) -> List[Ticket]:
        """Handle tickets with missing required fields.
        
        Args:
            tickets: List of tickets to process.
            required_fields: List of field names that are required.
            
        Returns:
            List of tickets with missing fields handled appropriately.
        """
        return self._edge_case_handler.handle_missing_fields(tickets, required_fields)
    
    def _initial_validation(self, tickets: List[Ticket]) -> List[Ticket]:
        """Perform initial validation and filtering of tickets.
        
        Args:
            tickets: Raw tickets to validate.
            
        Returns:
            List of tickets that pass initial validation.
        """
        valid_tickets = []
        validation_stats = {
            'total_input': len(tickets),
            'valid': 0,
            'invalid': 0,
            'issues': defaultdict(int)
        }
        
        for ticket in tickets:
            validation_result = self._validation_rules.validate_ticket(ticket)
            
            if validation_result['is_valid']:
                valid_tickets.append(ticket)
                validation_stats['valid'] += 1
            else:
                validation_stats['invalid'] += 1
                for issue in validation_result['issues']:
                    validation_stats['issues'][issue] += 1
        
        logger.debug(f"Initial validation: {validation_stats['valid']}/{validation_stats['total_input']} tickets valid")
        
        if validation_stats['issues']:
            logger.warning(f"Validation issues found: {dict(validation_stats['issues'])}")
        
        return valid_tickets
    
    def _clean_and_normalize(self, tickets: List[Ticket]) -> List[Ticket]:
        """Clean and normalize ticket data.
        
        Args:
            tickets: Tickets to clean and normalize.
            
        Returns:
            List of cleaned and normalized tickets.
        """
        cleaned_tickets = []
        
        for ticket in tickets:
            try:
                cleaned_ticket = self._data_cleaner.clean_ticket(ticket)
                if cleaned_ticket:
                    cleaned_tickets.append(cleaned_ticket)
            except Exception as e:
                logger.warning(f"Failed to clean ticket {ticket.id}: {e}")
                # Continue with original ticket if cleaning fails
                cleaned_tickets.append(ticket)
        
        return cleaned_tickets
    
    def _handle_edge_cases(self, tickets: List[Ticket]) -> List[Ticket]:
        """Handle various edge cases in ticket data.
        
        Args:
            tickets: Tickets to process for edge cases.
            
        Returns:
            List of tickets with edge cases handled.
        """
        processed_tickets = []
        
        for ticket in tickets:
            try:
                processed_ticket = self._edge_case_handler.process_ticket(ticket)
                processed_tickets.append(processed_ticket)
            except Exception as e:
                logger.warning(f"Edge case handling failed for ticket {ticket.id}: {e}")
                # Continue with original ticket
                processed_tickets.append(ticket)
        
        return processed_tickets
    
    def _enrich_data(self, tickets: List[Ticket]) -> List[Ticket]:
        """Enrich ticket data with derived fields and calculations.
        
        Args:
            tickets: Tickets to enrich.
            
        Returns:
            List of enriched tickets.
        """
        enriched_tickets = []
        
        for ticket in tickets:
            try:
                # Add any derived fields or calculations here
                # For now, just pass through the ticket
                enriched_tickets.append(ticket)
            except Exception as e:
                logger.warning(f"Data enrichment failed for ticket {ticket.id}: {e}")
                enriched_tickets.append(ticket)
        
        return enriched_tickets
    
    def _final_validation(self, tickets: List[Ticket]) -> List[Ticket]:
        """Perform final validation after processing.
        
        Args:
            tickets: Processed tickets to validate.
            
        Returns:
            List of tickets that pass final validation.
        """
        final_tickets = []
        
        for ticket in tickets:
            if self._validation_rules.validate_processed_ticket(ticket):
                final_tickets.append(ticket)
            else:
                logger.warning(f"Ticket {ticket.id} failed final validation")
        
        return final_tickets


class ValidationRuleEngine:
    """Engine for validating ticket data using configurable rules."""
    
    def __init__(self) -> None:
        """Initialize validation rule engine."""
        self._required_fields = ['id', 'created_date', 'status']
        self._optional_fields = ['title', 'description', 'severity', 'assignee', 'resolver_group']
    
    def validate_ticket(self, ticket: Ticket) -> Dict[str, Any]:
        """Validate a ticket object comprehensively.
        
        Args:
            ticket: Ticket to validate.
            
        Returns:
            Dictionary with validation results.
        """
        issues = []
        
        # Check required fields
        if not ticket.id or not isinstance(ticket.id, str):
            issues.append('missing_or_invalid_id')
        
        if not ticket.created_date or not isinstance(ticket.created_date, datetime):
            issues.append('missing_or_invalid_created_date')
        
        if not ticket.status:
            issues.append('missing_status')
        
        # Check date consistency
        if ticket.created_date and ticket.updated_date:
            if ticket.updated_date < ticket.created_date:
                issues.append('updated_date_before_created_date')
        
        if ticket.created_date and ticket.resolved_date:
            if ticket.resolved_date < ticket.created_date:
                issues.append('resolved_date_before_created_date')
        
        # Check future dates
        now = datetime.now()
        if ticket.created_date and ticket.created_date > now:
            issues.append('future_created_date')
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def validate_ticket_structure(self, ticket_data: Dict[str, Any]) -> bool:
        """Validate ticket data dictionary structure.
        
        Args:
            ticket_data: Ticket data dictionary.
            
        Returns:
            True if structure is valid.
        """
        if not isinstance(ticket_data, dict):
            return False
        
        # Check for required fields
        for field in self._required_fields:
            if field not in ticket_data:
                return False
        
        return True
    
    def validate_response_structure(self, response: Dict[str, Any]) -> bool:
        """Validate MCP response structure.
        
        Args:
            response: MCP response dictionary.
            
        Returns:
            True if structure is valid.
        """
        if not isinstance(response, dict):
            return False
        
        # Basic structure validation
        return True  # Placeholder for more specific validation
    
    def validate_processed_ticket(self, ticket: Ticket) -> bool:
        """Validate ticket after processing.
        
        Args:
            ticket: Processed ticket to validate.
            
        Returns:
            True if ticket is valid for analysis.
        """
        validation_result = self.validate_ticket(ticket)
        return validation_result['is_valid']


class DataCleaner:
    """Data cleaner for normalizing and cleaning ticket data."""
    
    def __init__(self) -> None:
        """Initialize data cleaner."""
        self._status_mappings = self._create_status_mappings()
        self._severity_mappings = self._create_severity_mappings()
    
    def clean_ticket(self, ticket: Ticket) -> Optional[Ticket]:
        """Clean and normalize a ticket object.
        
        Args:
            ticket: Ticket to clean.
            
        Returns:
            Cleaned ticket or None if cleaning fails.
        """
        try:
            # Clean and normalize status
            if ticket.status:
                normalized_status = self._normalize_status(str(ticket.status))
                if normalized_status:
                    ticket.status = normalized_status
            
            # Clean and normalize severity
            if ticket.severity:
                normalized_severity = self._normalize_severity(str(ticket.severity))
                if normalized_severity:
                    ticket.severity = normalized_severity
            
            # Clean text fields
            if ticket.title:
                ticket.title = self._clean_text_field(ticket.title)
            
            if ticket.description:
                ticket.description = self._clean_text_field(ticket.description)
            
            # Clean assignee field
            if ticket.assignee:
                ticket.assignee = self._clean_assignee_field(ticket.assignee)
            
            return ticket
            
        except Exception as e:
            logger.error(f"Failed to clean ticket {ticket.id}: {e}")
            return None
    
    def clean_ticket_dict(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean ticket data dictionary.
        
        Args:
            ticket_data: Raw ticket data dictionary.
            
        Returns:
            Cleaned ticket data dictionary.
        """
        cleaned_data = ticket_data.copy()
        
        # Clean status field
        if 'status' in cleaned_data:
            cleaned_data['status'] = self._normalize_status(str(cleaned_data['status']))
        
        # Clean severity field
        if 'severity' in cleaned_data:
            cleaned_data['severity'] = self._normalize_severity(str(cleaned_data['severity']))
        
        # Clean text fields
        text_fields = ['title', 'description']
        for field in text_fields:
            if field in cleaned_data and cleaned_data[field]:
                cleaned_data[field] = self._clean_text_field(str(cleaned_data[field]))
        
        return cleaned_data
    
    def _create_status_mappings(self) -> Dict[str, str]:
        """Create status normalization mappings.
        
        Returns:
            Dictionary mapping various status formats to normalized values.
        """
        return {
            # Common variations
            'open': 'Open',
            'opened': 'Open',
            'new': 'Open',
            'created': 'Open',
            'in progress': 'In Progress',
            'in-progress': 'In Progress',
            'inprogress': 'In Progress',
            'working': 'In Progress',
            'assigned': 'In Progress',
            'resolved': 'Resolved',
            'fixed': 'Resolved',
            'completed': 'Resolved',
            'done': 'Resolved',
            'closed': 'Closed',
            'cancelled': 'Closed',
            'canceled': 'Closed',
            'rejected': 'Closed'
        }
    
    def _create_severity_mappings(self) -> Dict[str, str]:
        """Create severity normalization mappings.
        
        Returns:
            Dictionary mapping various severity formats to normalized values.
        """
        return {
            # Numeric mappings
            '1': 'SEV_1',
            '2': 'SEV_2',
            '3': 'SEV_3',
            '4': 'SEV_4',
            '5': 'SEV_5',
            # Text mappings
            'critical': 'SEV_1',
            'high': 'SEV_2',
            'medium': 'SEV_3',
            'low': 'SEV_4',
            'lowest': 'SEV_5',
            'urgent': 'SEV_1',
            'normal': 'SEV_3',
            'minor': 'SEV_4'
        }
    
    def _normalize_status(self, status: str) -> str:
        """Normalize status value.
        
        Args:
            status: Raw status value.
            
        Returns:
            Normalized status value.
        """
        if not status:
            return 'Open'  # Default status
        
        status_lower = status.lower().strip()
        return self._status_mappings.get(status_lower, status)
    
    def _normalize_severity(self, severity: str) -> str:
        """Normalize severity value.
        
        Args:
            severity: Raw severity value.
            
        Returns:
            Normalized severity value.
        """
        if not severity:
            return 'SEV_3'  # Default severity
        
        severity_lower = severity.lower().strip()
        return self._severity_mappings.get(severity_lower, severity)
    
    def _clean_text_field(self, text: str) -> str:
        """Clean and normalize text fields.
        
        Args:
            text: Raw text to clean.
            
        Returns:
            Cleaned text.
        """
        if not text:
            return ''
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned
    
    def _clean_assignee_field(self, assignee: str) -> str:
        """Clean assignee field.
        
        Args:
            assignee: Raw assignee value.
            
        Returns:
            Cleaned assignee value.
        """
        if not assignee:
            return ''
        
        # Remove email domain if present
        if '@' in assignee:
            assignee = assignee.split('@')[0]
        
        # Clean whitespace
        return assignee.strip()


class EdgeCaseHandler:
    """Handler for various edge cases in ticket data processing."""
    
    def __init__(self) -> None:
        """Initialize edge case handler."""
        pass
    
    def process_ticket(self, ticket: Ticket) -> Ticket:
        """Process ticket to handle edge cases.
        
        Args:
            ticket: Ticket to process.
            
        Returns:
            Processed ticket with edge cases handled.
        """
        # Handle missing dates
        ticket = self._handle_missing_dates(ticket)
        
        # Handle invalid date ranges
        ticket = self._handle_invalid_date_ranges(ticket)
        
        # Handle missing or invalid status
        ticket = self._handle_missing_status(ticket)
        
        # Handle missing severity
        ticket = self._handle_missing_severity(ticket)
        
        return ticket
    
    def handle_empty_dataset(self, operation_name: str) -> Dict[str, Any]:
        """Handle empty dataset scenarios.
        
        Args:
            operation_name: Name of the operation.
            
        Returns:
            Dictionary with appropriate defaults for empty datasets.
        """
        return {
            'message': f'No data available for {operation_name}',
            'data_available': False,
            'sample_size': 0,
            'recommendations': [
                'Ensure ticket data is available and accessible',
                'Check date range filters and search criteria',
                'Verify authentication and permissions'
            ]
        }
    
    def handle_missing_fields(self, tickets: List[Ticket], required_fields: List[str]) -> List[Ticket]:
        """Handle tickets with missing required fields.
        
        Args:
            tickets: List of tickets to process.
            required_fields: List of required field names.
            
        Returns:
            List of tickets with missing fields handled.
        """
        processed_tickets = []
        
        for ticket in tickets:
            # Check each required field and provide defaults if missing
            if 'created_date' in required_fields and not ticket.created_date:
                # Skip tickets without creation date as it's critical
                logger.warning(f"Skipping ticket {ticket.id} - missing creation date")
                continue
            
            if 'status' in required_fields and not ticket.status:
                ticket.status = 'Open'  # Default status
            
            if 'severity' in required_fields and not ticket.severity:
                ticket.severity = 'SEV_3'  # Default severity
            
            processed_tickets.append(ticket)
        
        return processed_tickets
    
    def _handle_missing_dates(self, ticket: Ticket) -> Ticket:
        """Handle missing date fields.
        
        Args:
            ticket: Ticket to process.
            
        Returns:
            Ticket with missing dates handled.
        """
        # If updated_date is missing, use created_date
        if not ticket.updated_date and ticket.created_date:
            ticket.updated_date = ticket.created_date
        
        return ticket
    
    def _handle_invalid_date_ranges(self, ticket: Ticket) -> Ticket:
        """Handle invalid date ranges.
        
        Args:
            ticket: Ticket to process.
            
        Returns:
            Ticket with invalid date ranges corrected.
        """
        if not ticket.created_date:
            return ticket
        
        # Ensure updated_date is not before created_date
        if ticket.updated_date and ticket.updated_date < ticket.created_date:
            logger.warning(f"Ticket {ticket.id}: updated_date before created_date, correcting")
            ticket.updated_date = ticket.created_date
        
        # Ensure resolved_date is not before created_date
        if ticket.resolved_date and ticket.resolved_date < ticket.created_date:
            logger.warning(f"Ticket {ticket.id}: resolved_date before created_date, correcting")
            ticket.resolved_date = ticket.created_date
        
        # Handle future dates
        now = datetime.now()
        if ticket.created_date > now:
            logger.warning(f"Ticket {ticket.id}: future created_date, using current time")
            ticket.created_date = now
        
        return ticket
    
    def _handle_missing_status(self, ticket: Ticket) -> Ticket:
        """Handle missing or invalid status.
        
        Args:
            ticket: Ticket to process.
            
        Returns:
            Ticket with status handled.
        """
        if not ticket.status:
            ticket.status = 'Open'  # Default status
            logger.debug(f"Ticket {ticket.id}: missing status, defaulting to 'Open'")
        
        return ticket
    
    def _handle_missing_severity(self, ticket: Ticket) -> Ticket:
        """Handle missing severity.
        
        Args:
            ticket: Ticket to process.
            
        Returns:
            Ticket with severity handled.
        """
        if not ticket.severity:
            ticket.severity = 'SEV_3'  # Default severity (medium)
            logger.debug(f"Ticket {ticket.id}: missing severity, defaulting to 'SEV_3'")
        
        return ticket


class DataQualityAssessor:
    """Assessor for evaluating data quality of ticket collections."""
    
    def __init__(self) -> None:
        """Initialize data quality assessor."""
        pass
    
    def assess_quality(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess overall data quality of ticket collection.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary containing comprehensive data quality assessment.
        """
        if not tickets:
            return {
                'quality_score': 0,
                'total_tickets': 0,
                'issues': ['No tickets available for assessment'],
                'recommendations': ['Ensure ticket data is available']
            }
        
        assessment = {
            'total_tickets': len(tickets),
            'completeness': self._assess_completeness(tickets),
            'consistency': self._assess_consistency(tickets),
            'validity': self._assess_validity(tickets),
            'timeliness': self._assess_timeliness(tickets),
            'overall_quality_score': 0,
            'issues': [],
            'recommendations': []
        }
        
        # Calculate overall quality score
        scores = [
            assessment['completeness']['score'],
            assessment['consistency']['score'],
            assessment['validity']['score'],
            assessment['timeliness']['score']
        ]
        assessment['overall_quality_score'] = sum(scores) / len(scores)
        
        # Generate issues and recommendations
        assessment['issues'] = self._identify_issues(assessment)
        assessment['recommendations'] = self._generate_recommendations(assessment)
        
        return assessment
    
    def _assess_completeness(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess data completeness.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary with completeness assessment.
        """
        total = len(tickets)
        completeness_stats = {
            'id': 0,
            'created_date': 0,
            'status': 0,
            'title': 0,
            'severity': 0,
            'assignee': 0,
            'resolver_group': 0
        }
        
        for ticket in tickets:
            if ticket.id:
                completeness_stats['id'] += 1
            if ticket.created_date:
                completeness_stats['created_date'] += 1
            if ticket.status:
                completeness_stats['status'] += 1
            if ticket.title:
                completeness_stats['title'] += 1
            if ticket.severity:
                completeness_stats['severity'] += 1
            if ticket.assignee:
                completeness_stats['assignee'] += 1
            if ticket.resolver_group:
                completeness_stats['resolver_group'] += 1
        
        # Calculate completeness percentages
        completeness_percentages = {
            field: (count / total) * 100 if total > 0 else 0
            for field, count in completeness_stats.items()
        }
        
        # Calculate overall completeness score
        critical_fields = ['id', 'created_date', 'status']
        critical_completeness = sum(
            completeness_percentages[field] for field in critical_fields
        ) / len(critical_fields)
        
        return {
            'score': critical_completeness,
            'field_completeness': completeness_percentages,
            'critical_fields_complete': critical_completeness >= 95
        }
    
    def _assess_consistency(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess data consistency.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary with consistency assessment.
        """
        consistency_issues = 0
        total_checks = 0
        
        for ticket in tickets:
            # Check date consistency
            if ticket.created_date and ticket.updated_date:
                total_checks += 1
                if ticket.updated_date < ticket.created_date:
                    consistency_issues += 1
            
            if ticket.created_date and ticket.resolved_date:
                total_checks += 1
                if ticket.resolved_date < ticket.created_date:
                    consistency_issues += 1
            
            # Check status-resolution consistency
            if ticket.status and ticket.resolved_date:
                total_checks += 1
                is_resolved_status = str(ticket.status).lower() in ['resolved', 'closed']
                has_resolution_date = ticket.resolved_date is not None
                
                if is_resolved_status != has_resolution_date:
                    consistency_issues += 1
        
        consistency_score = (
            ((total_checks - consistency_issues) / total_checks) * 100
            if total_checks > 0 else 100
        )
        
        return {
            'score': consistency_score,
            'issues_found': consistency_issues,
            'total_checks': total_checks,
            'consistent': consistency_score >= 95
        }
    
    def _assess_validity(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess data validity.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary with validity assessment.
        """
        validity_issues = 0
        total_tickets = len(tickets)
        
        for ticket in tickets:
            # Check for future dates
            now = datetime.now()
            if ticket.created_date and ticket.created_date > now:
                validity_issues += 1
            
            # Check for reasonable date ranges
            if ticket.created_date and ticket.resolved_date:
                resolution_time = ticket.resolved_date - ticket.created_date
                # Flag if resolution time is more than 2 years (likely data error)
                if resolution_time.days > 730:
                    validity_issues += 1
        
        validity_score = (
            ((total_tickets - validity_issues) / total_tickets) * 100
            if total_tickets > 0 else 100
        )
        
        return {
            'score': validity_score,
            'issues_found': validity_issues,
            'total_tickets': total_tickets,
            'valid': validity_score >= 95
        }
    
    def _assess_timeliness(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess data timeliness.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary with timeliness assessment.
        """
        if not tickets:
            return {'score': 0, 'recent_data': False}
        
        # Check how recent the data is
        now = datetime.now()
        recent_threshold = now - timedelta(days=30)  # Data within last 30 days
        
        recent_tickets = sum(
            1 for ticket in tickets
            if ticket.created_date and ticket.created_date >= recent_threshold
        )
        
        timeliness_score = (recent_tickets / len(tickets)) * 100
        
        return {
            'score': timeliness_score,
            'recent_tickets': recent_tickets,
            'total_tickets': len(tickets),
            'recent_data': timeliness_score >= 50
        }
    
    def _identify_issues(self, assessment: Dict[str, Any]) -> List[str]:
        """Identify data quality issues from assessment.
        
        Args:
            assessment: Quality assessment results.
            
        Returns:
            List of identified issues.
        """
        issues = []
        
        if assessment['completeness']['score'] < 90:
            issues.append('Low data completeness - missing critical fields')
        
        if assessment['consistency']['score'] < 90:
            issues.append('Data consistency issues - conflicting field values')
        
        if assessment['validity']['score'] < 90:
            issues.append('Data validity issues - invalid or unreasonable values')
        
        if assessment['timeliness']['score'] < 50:
            issues.append('Data timeliness issues - mostly old data')
        
        return issues
    
    def _generate_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on assessment.
        
        Args:
            assessment: Quality assessment results.
            
        Returns:
            List of recommendations.
        """
        recommendations = []
        
        if assessment['completeness']['score'] < 90:
            recommendations.append('Improve data collection processes to ensure all critical fields are populated')
        
        if assessment['consistency']['score'] < 90:
            recommendations.append('Implement data validation rules to prevent inconsistent field values')
        
        if assessment['validity']['score'] < 90:
            recommendations.append('Add data validation checks to prevent invalid dates and values')
        
        if assessment['timeliness']['score'] < 50:
            recommendations.append('Ensure regular data updates and consider filtering to recent data')
        
        if assessment['overall_quality_score'] >= 90:
            recommendations.append('Data quality is good - continue current data management practices')
        
        return recommendations