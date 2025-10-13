"""MCP-based ticket repository implementation.

This module implements the Repository pattern for ticket data access using
MCP (Model Context Protocol) integration. It provides comprehensive ticket
search, retrieval, and validation capabilities with built-in resilience
patterns and data sanitization.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..interfaces import (
    DataRetrievalInterface,
    TicketRepositoryInterface,
    MCPClientInterface,
    AuthenticationInterface,
    DataSanitizerInterface,
    InputValidatorInterface
)
from ..models import (
    Ticket,
    TicketStatus,
    TicketSeverity,
    SearchCriteria,
    DataRetrievalError,
    ValidationError,
    AuthenticationError,
    MCPError
)
from ..external import MCPClient

logger = logging.getLogger(__name__)


class TicketDataMapper:
    """Maps raw MCP ticket data to domain model objects."""
    
    @staticmethod
    def map_to_ticket(raw_data: Dict[str, Any]) -> Ticket:
        """Map raw ticket data from MCP to Ticket domain object.
        
        Args:
            raw_data: Raw ticket data from MCP response.
            
        Returns:
            Ticket domain object.
            
        Raises:
            ValidationError: If required fields are missing or invalid.
        """
        try:
            # Validate required fields
            required_fields = {"id", "title", "status"}
            missing_fields = required_fields - set(raw_data.keys())
            if missing_fields:
                raise ValidationError(
                    f"Missing required ticket fields: {missing_fields}",
                    {"missing_fields": list(missing_fields), "raw_data": raw_data}
                )
            
            # Parse dates safely
            created_date = TicketDataMapper._parse_date(raw_data.get("createDate"))
            updated_date = TicketDataMapper._parse_date(raw_data.get("lastUpdatedDate"))
            resolved_date = TicketDataMapper._parse_date(raw_data.get("lastResolvedDate"))
            
            # Map status and severity with validation
            status = TicketDataMapper._map_status(raw_data.get("status"))
            severity = TicketDataMapper._map_severity(raw_data.get("severity", "SEV_5"))
            
            # Extract metadata
            metadata = {
                "resolver_group": raw_data.get("extensions", {}).get("tt", {}).get("assignedGroup"),
                "impact": raw_data.get("extensions", {}).get("tt", {}).get("impact"),
                "urgency": raw_data.get("extensions", {}).get("tt", {}).get("urgency"),
                "category": raw_data.get("extensions", {}).get("tt", {}).get("category"),
                "subcategory": raw_data.get("extensions", {}).get("tt", {}).get("subcategory"),
                "source": raw_data.get("source"),
                "external_id": raw_data.get("externalId")
            }
            
            # Remove None values from metadata
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return Ticket(
                id=raw_data["id"],
                title=raw_data["title"],
                description=raw_data.get("description", ""),
                status=status,
                severity=severity,
                created_date=created_date,
                updated_date=updated_date,
                resolved_date=resolved_date,
                assignee=raw_data.get("assignee"),
                resolver_group=metadata.get("resolver_group"),
                tags=raw_data.get("tags", []),
                metadata=metadata
            )
            
        except (KeyError, ValueError, TypeError) as e:
            raise ValidationError(
                f"Failed to map ticket data: {e}",
                {"raw_data": raw_data, "error": str(e)}
            )
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object.
        
        Args:
            date_str: Date string in ISO format.
            
        Returns:
            Datetime object or None if date_str is None/empty.
        """
        if not date_str:
            return None
        
        try:
            # Handle various ISO date formats
            if date_str.endswith('Z'):
                return datetime.fromisoformat(date_str[:-1] + '+00:00')
            elif '+' in date_str or date_str.count('-') > 2:
                return datetime.fromisoformat(date_str)
            else:
                # Assume UTC if no timezone info
                return datetime.fromisoformat(date_str + '+00:00')
        except ValueError as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
    
    @staticmethod
    def _map_status(status_str: Optional[str]) -> TicketStatus:
        """Map status string to TicketStatus enum.
        
        Args:
            status_str: Status string from MCP.
            
        Returns:
            TicketStatus enum value.
        """
        if not status_str:
            return TicketStatus.OPEN
        
        # Normalize status string
        normalized = status_str.strip().upper().replace(" ", "_")
        
        # Map common status variations
        status_mapping = {
            "OPEN": TicketStatus.OPEN,
            "NEW": TicketStatus.OPEN,
            "ASSIGNED": TicketStatus.IN_PROGRESS,
            "IN_PROGRESS": TicketStatus.IN_PROGRESS,
            "WORK_IN_PROGRESS": TicketStatus.IN_PROGRESS,
            "RESEARCHING": TicketStatus.IN_PROGRESS,
            "PENDING": TicketStatus.IN_PROGRESS,
            "RESOLVED": TicketStatus.RESOLVED,
            "CLOSED": TicketStatus.CLOSED,
            "CANCELLED": TicketStatus.CLOSED,
            "CANCELED": TicketStatus.CLOSED
        }
        
        return status_mapping.get(normalized, TicketStatus.OPEN)
    
    @staticmethod
    def _map_severity(severity_str: Optional[str]) -> TicketSeverity:
        """Map severity string to TicketSeverity enum.
        
        Args:
            severity_str: Severity string from MCP.
            
        Returns:
            TicketSeverity enum value.
        """
        if not severity_str:
            return TicketSeverity.SEV_5
        
        # Normalize severity string
        normalized = severity_str.strip().upper()
        
        # Map severity variations
        severity_mapping = {
            "SEV_1": TicketSeverity.SEV_1,
            "SEV1": TicketSeverity.SEV_1,
            "SEVERITY_1": TicketSeverity.SEV_1,
            "CRITICAL": TicketSeverity.SEV_1,
            "SEV_2": TicketSeverity.SEV_2,
            "SEV2": TicketSeverity.SEV_2,
            "SEVERITY_2": TicketSeverity.SEV_2,
            "HIGH": TicketSeverity.SEV_2,
            "SEV_3": TicketSeverity.SEV_3,
            "SEV3": TicketSeverity.SEV_3,
            "SEVERITY_3": TicketSeverity.SEV_3,
            "MEDIUM": TicketSeverity.SEV_3,
            "SEV_4": TicketSeverity.SEV_4,
            "SEV4": TicketSeverity.SEV_4,
            "SEVERITY_4": TicketSeverity.SEV_4,
            "LOW": TicketSeverity.SEV_4,
            "SEV_5": TicketSeverity.SEV_5,
            "SEV5": TicketSeverity.SEV_5,
            "SEVERITY_5": TicketSeverity.SEV_5,
            "LOWEST": TicketSeverity.SEV_5
        }
        
        return severity_mapping.get(normalized, TicketSeverity.SEV_5)


class MCPTicketRepository(DataRetrievalInterface, TicketRepositoryInterface):
    """Repository for ticket data access via MCP with comprehensive error handling.
    
    This repository implements both DataRetrievalInterface and TicketRepositoryInterface
    to provide flexible ticket access patterns. It includes built-in resilience patterns,
    data validation, sanitization, and comprehensive error handling.
    """
    
    def __init__(self,
                 mcp_client: Optional[MCPClientInterface] = None,
                 authenticator: Optional[AuthenticationInterface] = None,
                 sanitizer: Optional[DataSanitizerInterface] = None,
                 validator: Optional[InputValidatorInterface] = None) -> None:
        """Initialize MCP ticket repository.
        
        Args:
            mcp_client: MCP client for server communication.
            authenticator: Authentication service.
            sanitizer: Data sanitizer for PII removal.
            validator: Input validator for security.
        """
        self._mcp_client = mcp_client or MCPClient()
        self._authenticator = authenticator
        self._sanitizer = sanitizer
        self._validator = validator
        self._data_mapper = TicketDataMapper()
        
        # Connection state
        self._connected = False
    
    def _ensure_connection(self) -> None:
        """Ensure MCP client is connected and authenticated."""
        if not self._connected:
            try:
                # Ensure authentication if authenticator is provided
                if self._authenticator:
                    self._authenticator.ensure_authenticated()
                
                # Connect to MCP server
                self._mcp_client.connect()
                self._connected = True
                logger.info("MCP ticket repository connected")
                
            except Exception as e:
                raise DataRetrievalError(
                    f"Failed to establish MCP connection: {e}",
                    {"service": "MCP", "operation": "connect"}
                )
    
    def validate_connection(self) -> bool:
        """Validate connection to MCP server.
        
        Returns:
            True if connection is valid and operational, False otherwise.
        """
        try:
            self._ensure_connection()
            
            # Perform health check
            health_info = self._mcp_client.health_check()
            return health_info.get("connected", False) and health_info.get("server_responsive", False)
            
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to MCP server and return diagnostic information.
        
        Returns:
            Dictionary containing connectivity status and diagnostic information.
        """
        try:
            self._ensure_connection()
            return self._mcp_client.health_check()
        except Exception as e:
            return {
                "connected": False,
                "server_responsive": False,
                "error_message": str(e)
            }
    
    def search_tickets(self, criteria: SearchCriteria) -> List[Ticket]:
        """Search for tickets based on criteria with Lucene query support.
        
        Args:
            criteria: Search criteria for filtering tickets.
            
        Returns:
            List of tickets matching the criteria.
            
        Raises:
            DataRetrievalError: If search operation fails.
            AuthenticationError: If authentication is required but not available.
        """
        try:
            # Validate search criteria
            if not self.validate_search_criteria(criteria):
                raise ValidationError("Invalid search criteria provided")
            
            # Ensure connection and authentication
            self._ensure_connection()
            
            # Format search request
            search_params = criteria.to_dict()
            
            # Sanitize search parameters if sanitizer is available
            if self._sanitizer:
                search_params = self._sanitizer.sanitize_search_criteria(criteria).to_dict()
            
            # Execute search via MCP
            logger.info(f"Searching tickets with criteria: {criteria}")
            raw_tickets = self._mcp_client.search_tickets(search_params)
            
            # Map raw data to domain objects
            tickets = []
            for raw_ticket in raw_tickets:
                try:
                    # Sanitize ticket data if sanitizer is available
                    if self._sanitizer:
                        raw_ticket = self._sanitizer.sanitize_ticket_data(raw_ticket)
                    
                    ticket = self._data_mapper.map_to_ticket(raw_ticket)
                    tickets.append(ticket)
                except ValidationError as e:
                    logger.warning(f"Skipping invalid ticket data: {e}")
                    continue
            
            logger.info(f"Successfully retrieved {len(tickets)} tickets")
            return tickets
            
        except AuthenticationError:
            raise
        except MCPError as e:
            raise DataRetrievalError(
                f"MCP search failed: {e}",
                {"service": "MCP", "operation": "search_tickets", "criteria": str(criteria)}
            )
        except Exception as e:
            raise DataRetrievalError(
                f"Ticket search failed: {e}",
                {"service": "MCP", "operation": "search_tickets"}
            )
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Retrieve a specific ticket by ID with full details.
        
        Args:
            ticket_id: Unique identifier for the ticket.
            
        Returns:
            Ticket object if found, None otherwise.
            
        Raises:
            DataRetrievalError: If retrieval operation fails.
            AuthenticationError: If authentication is required but not available.
        """
        try:
            # Validate ticket ID
            if self._validator and not self._validator.validate_ticket_id(ticket_id):
                raise ValidationError(f"Invalid ticket ID format: {ticket_id}")
            
            # Ensure connection and authentication
            self._ensure_connection()
            
            # Retrieve ticket via MCP
            logger.debug(f"Retrieving ticket: {ticket_id}")
            raw_ticket = self._mcp_client.get_ticket(ticket_id)
            
            if not raw_ticket:
                logger.debug(f"Ticket {ticket_id} not found")
                return None
            
            # Sanitize ticket data if sanitizer is available
            if self._sanitizer:
                raw_ticket = self._sanitizer.sanitize_ticket_data(raw_ticket)
            
            # Map to domain object
            ticket = self._data_mapper.map_to_ticket(raw_ticket)
            logger.debug(f"Successfully retrieved ticket: {ticket_id}")
            return ticket
            
        except AuthenticationError:
            raise
        except MCPError as e:
            raise DataRetrievalError(
                f"MCP ticket retrieval failed: {e}",
                {"service": "MCP", "operation": "get_ticket", "ticket_id": ticket_id}
            )
        except ValidationError:
            raise
        except Exception as e:
            raise DataRetrievalError(
                f"Ticket retrieval failed: {e}",
                {"service": "MCP", "operation": "get_ticket", "ticket_id": ticket_id}
            )
    
    def get_ticket_details(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve detailed ticket information including metadata.
        
        Args:
            ticket_id: Unique identifier for the ticket.
            
        Returns:
            Dictionary containing detailed ticket information, None if not found.
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return None
            
            # Convert ticket to detailed dictionary
            details = {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status.value,
                "severity": ticket.severity.value,
                "created_date": ticket.created_date.isoformat() if ticket.created_date else None,
                "updated_date": ticket.updated_date.isoformat() if ticket.updated_date else None,
                "resolved_date": ticket.resolved_date.isoformat() if ticket.resolved_date else None,
                "assignee": ticket.assignee,
                "resolver_group": ticket.resolver_group,
                "tags": ticket.tags,
                "metadata": ticket.metadata,
                "is_resolved": ticket.is_resolved(),
                "age_days": ticket.age().days if ticket.age() else None,
                "resolution_time_hours": (
                    ticket.resolution_time().total_seconds() / 3600 
                    if ticket.resolution_time() else None
                )
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to get ticket details for {ticket_id}: {e}")
            return None
    
    def count_tickets(self, criteria: SearchCriteria) -> int:
        """Count tickets matching criteria without retrieving full data.
        
        Args:
            criteria: Search criteria for filtering tickets.
            
        Returns:
            Number of tickets matching criteria.
        """
        try:
            # For MCP, we need to perform a search to get count
            # This could be optimized with a dedicated count endpoint
            tickets = self.search_tickets(criteria)
            return len(tickets)
            
        except Exception as e:
            logger.error(f"Failed to count tickets: {e}")
            return 0
    
    def search_tickets_paginated(self, criteria: SearchCriteria, 
                                page_size: int = 100, 
                                page_token: Optional[str] = None) -> Dict[str, Any]:
        """Search tickets with pagination support.
        
        Args:
            criteria: Search criteria for filtering tickets.
            page_size: Number of tickets per page.
            page_token: Token for retrieving specific page.
            
        Returns:
            Dictionary containing paginated results.
        """
        try:
            # Set pagination parameters in criteria
            paginated_criteria = SearchCriteria(
                status_filters=criteria.status_filters,
                assignee=criteria.assignee,
                start_date=criteria.start_date,
                end_date=criteria.end_date,
                search_text=criteria.search_text,
                lucene_query=criteria.lucene_query,
                max_results=page_size,
                offset=int(page_token) if page_token else 0
            )
            
            # Execute search
            tickets = self.search_tickets(paginated_criteria)
            
            # Calculate next page token
            next_page_token = None
            if len(tickets) == page_size:
                next_offset = (int(page_token) if page_token else 0) + page_size
                next_page_token = str(next_offset)
            
            return {
                "tickets": tickets,
                "next_page_token": next_page_token,
                "page_size": len(tickets),
                "total_count": None  # Would need separate count query
            }
            
        except Exception as e:
            raise DataRetrievalError(
                f"Paginated search failed: {e}",
                {"service": "MCP", "operation": "search_paginated"}
            )
    
    def validate_search_criteria(self, criteria: SearchCriteria) -> bool:
        """Validate search criteria before executing search.
        
        Args:
            criteria: Search criteria to validate.
            
        Returns:
            True if criteria is valid, False otherwise.
        """
        try:
            # Use validator if available
            if self._validator:
                return self._validator.validate_search_criteria(criteria)
            
            # Basic validation
            if criteria.max_results and criteria.max_results > 10000:
                logger.warning("Max results exceeds recommended limit")
                return False
            
            if criteria.start_date and criteria.end_date:
                if criteria.start_date > criteria.end_date:
                    logger.warning("Start date is after end date")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Search criteria validation failed: {e}")
            return False
    
    def get_supported_query_fields(self) -> List[str]:
        """Get list of supported query fields for search operations.
        
        Returns:
            List of field names that can be used in search queries.
        """
        return [
            "id",
            "title", 
            "description",
            "status",
            "severity",
            "assignee",
            "resolver_group",
            "created_date",
            "updated_date",
            "resolved_date",
            "tags"
        ]
    
    # TicketRepositoryInterface methods
    def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Find ticket by ID (alias for get_ticket_by_id)."""
        return self.get_ticket_by_id(ticket_id)
    
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets matching criteria (alias for search_tickets)."""
        return self.search_tickets(criteria)
    
    def count_by_status(self, status: str) -> int:
        """Count tickets by status."""
        try:
            criteria = SearchCriteria(status_filters=[status])
            return self.count_tickets(criteria)
        except Exception as e:
            logger.error(f"Failed to count tickets by status {status}: {e}")
            return 0
    
    def __enter__(self) -> 'MCPTicketRepository':
        """Context manager entry."""
        self._ensure_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._connected and self._mcp_client:
            try:
                self._mcp_client.disconnect()
                self._connected = False
            except Exception as e:
                logger.error(f"Error disconnecting MCP client: {e}")