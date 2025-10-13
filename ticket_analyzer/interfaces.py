"""Abstract interfaces for all application modules.

This module defines the abstract base classes and protocols that establish
the contracts between different layers of the application. All concrete
implementations must implement these interfaces to ensure consistency
and testability throughout the system.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
from datetime import datetime

from .models import (
    Ticket, 
    SearchCriteria, 
    AnalysisResult, 
    ReportConfig,
    AuthConfig
)


# Authentication Interfaces
class AuthenticationInterface(ABC):
    """Abstract interface for authentication operations."""
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Perform authentication with external systems.
        
        Returns:
            True if authentication successful, False otherwise.
            
        Raises:
            AuthenticationError: If authentication fails.
        """
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated.
        
        Returns:
            True if authenticated, False otherwise.
        """
        pass
    
    @abstractmethod
    def ensure_authenticated(self) -> None:
        """Ensure user is authenticated, authenticate if needed.
        
        Raises:
            AuthenticationError: If authentication fails.
        """
        pass
    
    @abstractmethod
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information.
        
        Returns:
            Dictionary containing session details.
        """
        pass


class AuthenticationSessionInterface(ABC):
    """Abstract interface for authentication session management."""
    
    @abstractmethod
    def start_session(self) -> None:
        """Start a new authentication session.
        
        Raises:
            AuthenticationError: If session cannot be started.
        """
        pass
    
    @abstractmethod
    def end_session(self) -> None:
        """End the current authentication session."""
        pass
    
    @abstractmethod
    def is_session_valid(self) -> bool:
        """Check if the current session is valid.
        
        Returns:
            True if session is valid and not expired, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_session_duration(self) -> Optional[datetime]:
        """Get the duration of the current session.
        
        Returns:
            Session duration as datetime, None if no active session.
        """
        pass
    
    @abstractmethod
    def refresh_session(self) -> bool:
        """Refresh the current session to extend its validity.
        
        Returns:
            True if session was successfully refreshed, False otherwise.
            
        Raises:
            AuthenticationError: If session refresh fails.
        """
        pass
    
    @abstractmethod
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get metadata about the current session.
        
        Returns:
            Dictionary containing session metadata (start time, last activity, etc.).
        """
        pass


# Data Retrieval Interfaces
class DataRetrievalInterface(ABC):
    """Abstract interface for ticket data retrieval operations.
    
    This interface defines the contract for retrieving ticket data from external
    sources such as MCP services. Implementations should handle authentication,
    connection management, error handling, and data validation.
    """
    
    @abstractmethod
    def search_tickets(self, criteria: SearchCriteria) -> List[Ticket]:
        """Search for tickets based on criteria with Lucene query support.
        
        Args:
            criteria: Search criteria for filtering tickets including Lucene queries.
            
        Returns:
            List of tickets matching the criteria.
            
        Raises:
            DataRetrievalError: If search operation fails.
            AuthenticationError: If authentication is required but not available.
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def count_tickets(self, criteria: SearchCriteria) -> int:
        """Count tickets matching criteria without retrieving full data.
        
        Args:
            criteria: Search criteria for filtering tickets.
            
        Returns:
            Number of tickets matching criteria.
            
        Raises:
            DataRetrievalError: If count operation fails.
            AuthenticationError: If authentication is required but not available.
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate connection to data source.
        
        Returns:
            True if connection is valid and operational, False otherwise.
            
        Raises:
            DataRetrievalError: If connection validation fails.
        """
        pass
    
    @abstractmethod
    def get_ticket_details(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve detailed ticket information including metadata.
        
        Args:
            ticket_id: Unique identifier for the ticket.
            
        Returns:
            Dictionary containing detailed ticket information, None if not found.
            
        Raises:
            DataRetrievalError: If retrieval operation fails.
            AuthenticationError: If authentication is required but not available.
        """
        pass
    
    @abstractmethod
    def search_tickets_paginated(self, criteria: SearchCriteria, 
                                page_size: int = 100, 
                                page_token: Optional[str] = None) -> Dict[str, Any]:
        """Search tickets with pagination support.
        
        Args:
            criteria: Search criteria for filtering tickets.
            page_size: Number of tickets per page (default: 100).
            page_token: Token for retrieving specific page (None for first page).
            
        Returns:
            Dictionary containing:
                - 'tickets': List of tickets for current page
                - 'next_page_token': Token for next page (None if last page)
                - 'total_count': Total number of matching tickets
                - 'page_size': Actual page size returned
            
        Raises:
            DataRetrievalError: If search operation fails.
            AuthenticationError: If authentication is required but not available.
        """
        pass
    
    @abstractmethod
    def validate_search_criteria(self, criteria: SearchCriteria) -> bool:
        """Validate search criteria before executing search.
        
        Args:
            criteria: Search criteria to validate.
            
        Returns:
            True if criteria is valid, False otherwise.
            
        Raises:
            ValidationError: If criteria contains invalid parameters.
        """
        pass
    
    @abstractmethod
    def get_supported_query_fields(self) -> List[str]:
        """Get list of supported query fields for search operations.
        
        Returns:
            List of field names that can be used in search queries.
        """
        pass
    
    @abstractmethod
    def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to data source and return status information.
        
        Returns:
            Dictionary containing connectivity status and diagnostic information:
                - 'connected': Boolean indicating connection status
                - 'response_time_ms': Response time in milliseconds
                - 'server_info': Server information if available
                - 'error_message': Error message if connection failed
        """
        pass


class TicketRepositoryInterface(ABC):
    """Abstract interface for ticket repository operations."""
    
    @abstractmethod
    def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Find ticket by ID."""
        pass
    
    @abstractmethod
    def find_by_criteria(self, criteria: SearchCriteria) -> List[Ticket]:
        """Find tickets matching criteria."""
        pass
    
    @abstractmethod
    def count_by_status(self, status: str) -> int:
        """Count tickets by status."""
        pass


# Analysis Interfaces
class AnalysisInterface(ABC):
    """Abstract interface for ticket analysis operations."""
    
    @abstractmethod
    def analyze_tickets(self, tickets: List[Ticket]) -> AnalysisResult:
        """Perform comprehensive analysis on ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Analysis results containing metrics and insights.
            
        Raises:
            AnalysisError: If analysis operation fails.
        """
        pass
    
    @abstractmethod
    def calculate_metrics(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate key performance metrics from ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing calculated metrics.
            
        Raises:
            AnalysisError: If metric calculation fails.
        """
        pass
    
    @abstractmethod
    def generate_trends(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Generate trend analysis from ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing trend data.
            
        Raises:
            AnalysisError: If trend generation fails.
        """
        pass


class MetricsCalculatorInterface(ABC):
    """Abstract interface for metrics calculation strategies."""
    
    @abstractmethod
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate specific metrics from ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing calculated metrics.
        """
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides.
        
        Returns:
            List of metric names.
        """
        pass


# Reporting Interfaces
class ReportingInterface(ABC):
    """Abstract interface for report generation operations."""
    
    @abstractmethod
    def generate_report(self, analysis: AnalysisResult, config: ReportConfig) -> str:
        """Generate report from analysis results.
        
        Args:
            analysis: Analysis results to include in report.
            config: Configuration for report generation.
            
        Returns:
            Generated report content or file path.
            
        Raises:
            ReportGenerationError: If report generation fails.
        """
        pass
    
    @abstractmethod
    def supports_format(self, format_type: str) -> bool:
        """Check if reporter supports the specified format.
        
        Args:
            format_type: Format type to check (e.g., 'json', 'html').
            
        Returns:
            True if format is supported, False otherwise.
        """
        pass


class FormatterInterface(ABC):
    """Abstract interface for data formatting operations."""
    
    @abstractmethod
    def format_data(self, data: Dict[str, Any]) -> str:
        """Format data for display or output.
        
        Args:
            data: Data to format.
            
        Returns:
            Formatted string representation.
        """
        pass


# Configuration Interfaces
class ConfigurationInterface(ABC):
    """Abstract interface for configuration management."""
    
    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from various sources.
        
        Returns:
            Dictionary containing configuration settings.
            
        Raises:
            ConfigurationError: If configuration loading fails.
        """
        pass
    
    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration setting.
        
        Args:
            key: Configuration key to retrieve.
            default: Default value if key not found.
            
        Returns:
            Configuration value or default.
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration settings.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            True if configuration is valid, False otherwise.
            
        Raises:
            ConfigurationError: If validation fails.
        """
        pass
    
    @abstractmethod
    def set_setting(self, key: str, value: Any) -> None:
        """Set a configuration setting.
        
        Args:
            key: Configuration key to set.
            value: Value to set for the key.
            
        Raises:
            ConfigurationError: If setting cannot be updated.
        """
        pass
    
    @abstractmethod
    def has_setting(self, key: str) -> bool:
        """Check if a configuration setting exists.
        
        Args:
            key: Configuration key to check.
            
        Returns:
            True if setting exists, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings.
        
        Returns:
            Dictionary containing all configuration settings.
        """
        pass


class ConfigurationHandlerInterface(ABC):
    """Abstract interface for configuration source handlers in Chain of Responsibility pattern."""
    
    @abstractmethod
    def set_next(self, handler: 'ConfigurationHandlerInterface') -> 'ConfigurationHandlerInterface':
        """Set the next handler in the chain.
        
        Args:
            handler: Next handler in the chain.
            
        Returns:
            The handler that was set as next.
        """
        pass
    
    @abstractmethod
    def handle(self, key: str) -> Optional[Any]:
        """Handle configuration request for a specific key.
        
        Args:
            key: Configuration key to retrieve.
            
        Returns:
            Configuration value if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def load_all(self) -> Dict[str, Any]:
        """Load all configuration from this handler's source.
        
        Returns:
            Dictionary containing all configuration from this source.
        """
        pass
    
    @abstractmethod
    def can_handle_source(self, source_type: str) -> bool:
        """Check if handler can process the configuration source type.
        
        Args:
            source_type: Type of configuration source (e.g., 'file', 'env', 'cli').
            
        Returns:
            True if handler can process this source type.
        """
        pass


class ConfigurationValidatorInterface(ABC):
    """Abstract interface for configuration validation."""
    
    @abstractmethod
    def validate_setting(self, key: str, value: Any) -> bool:
        """Validate a single configuration setting.
        
        Args:
            key: Configuration key.
            value: Value to validate.
            
        Returns:
            True if setting is valid, False otherwise.
            
        Raises:
            ConfigurationError: If validation fails with details.
        """
        pass
    
    @abstractmethod
    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """Validate entire configuration against schema.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            True if configuration is valid, False otherwise.
            
        Raises:
            ConfigurationError: If validation fails with details.
        """
        pass
    
    @abstractmethod
    def get_validation_errors(self, config: Dict[str, Any]) -> List[str]:
        """Get list of validation errors for configuration.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            List of validation error messages.
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the configuration schema.
        
        Returns:
            Dictionary representing the configuration schema.
        """
        pass


class ConfigurationSourceInterface(ABC):
    """Abstract interface for configuration sources (files, environment, etc.)."""
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if configuration source exists.
        
        Returns:
            True if source exists and is accessible.
        """
        pass
    
    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """Read configuration from source.
        
        Returns:
            Dictionary containing configuration data.
            
        Raises:
            ConfigurationError: If reading fails.
        """
        pass
    
    @abstractmethod
    def write(self, config: Dict[str, Any]) -> None:
        """Write configuration to source.
        
        Args:
            config: Configuration data to write.
            
        Raises:
            ConfigurationError: If writing fails.
        """
        pass
    
    @abstractmethod
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about the configuration source.
        
        Returns:
            Dictionary containing source metadata.
        """
        pass


# External Service Interfaces
class MCPClientInterface(ABC):
    """Abstract interface for MCP (Model Context Protocol) client operations.
    
    This interface defines the contract for communicating with MCP servers,
    including connection management, request handling, and error recovery.
    Implementations must support Node.js 16+ compatibility and handle
    subprocess communication securely.
    """
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to MCP server with Node.js compatibility check.
        
        Raises:
            MCPConnectionError: If connection fails.
            NodeCompatibilityError: If Node.js version is incompatible.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to MCP server and cleanup resources."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if client is currently connected to MCP server.
        
        Returns:
            True if connected, False otherwise.
        """
        pass
    
    @abstractmethod
    def search_tickets(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search tickets via MCP with TicketingReadActions integration.
        
        Args:
            query: Search query parameters including Lucene syntax support.
            
        Returns:
            List of raw ticket data from MCP response.
            
        Raises:
            MCPError: If search operation fails.
            AuthenticationError: If MCP authentication fails.
        """
        pass
    
    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket by ID via MCP with detailed information.
        
        Args:
            ticket_id: Ticket identifier.
            
        Returns:
            Raw ticket data if found, None otherwise.
            
        Raises:
            MCPError: If retrieval operation fails.
            AuthenticationError: If MCP authentication fails.
        """
        pass
    
    @abstractmethod
    def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send generic MCP request with error handling and retry logic.
        
        Args:
            method: MCP method name to call.
            params: Parameters for the MCP method.
            
        Returns:
            Response data from MCP server.
            
        Raises:
            MCPError: If request fails.
            MCPTimeoutError: If request times out.
        """
        pass
    
    @abstractmethod
    def validate_node_version(self) -> bool:
        """Validate Node.js version compatibility (16+).
        
        Returns:
            True if Node.js version is compatible, False otherwise.
            
        Raises:
            NodeCompatibilityError: If Node.js is not available or incompatible.
        """
        pass
    
    @abstractmethod
    def get_server_info(self) -> Dict[str, Any]:
        """Get information about connected MCP server.
        
        Returns:
            Dictionary containing server information and capabilities.
            
        Raises:
            MCPError: If server info retrieval fails.
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on MCP connection.
        
        Returns:
            Dictionary containing health status and diagnostic information.
        """
        pass


class MCPRequestInterface(ABC):
    """Abstract interface for MCP request handling and formatting."""
    
    @abstractmethod
    def format_search_request(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Format search criteria into MCP request format.
        
        Args:
            criteria: Search criteria to format.
            
        Returns:
            Dictionary formatted for MCP request.
        """
        pass
    
    @abstractmethod
    def format_ticket_request(self, ticket_id: str) -> Dict[str, Any]:
        """Format ticket ID request into MCP request format.
        
        Args:
            ticket_id: Ticket ID to format.
            
        Returns:
            Dictionary formatted for MCP request.
        """
        pass
    
    @abstractmethod
    def parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse MCP response into standardized format.
        
        Args:
            response: Raw MCP response.
            
        Returns:
            List of parsed ticket data.
            
        Raises:
            MCPResponseError: If response format is invalid.
        """
        pass


class ResilienceInterface(ABC):
    """Abstract interface for resilience patterns (Circuit Breaker, Retry, etc.)."""
    
    @abstractmethod
    def execute_with_resilience(self, operation: callable, *args, **kwargs) -> Any:
        """Execute operation with resilience patterns applied.
        
        Args:
            operation: Function to execute with resilience.
            *args: Positional arguments for the operation.
            **kwargs: Keyword arguments for the operation.
            
        Returns:
            Result of the operation.
            
        Raises:
            ResilienceError: If operation fails after all retry attempts.
        """
        pass
    
    @abstractmethod
    def get_circuit_state(self) -> str:
        """Get current circuit breaker state.
        
        Returns:
            Circuit state: 'CLOSED', 'OPEN', or 'HALF_OPEN'.
        """
        pass
    
    @abstractmethod
    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        pass


# Security and Validation Interfaces
class DataSanitizerInterface(ABC):
    """Abstract interface for data sanitization operations.
    
    This interface defines methods for sanitizing sensitive data in tickets,
    logs, and other outputs to prevent information leakage and ensure
    compliance with security requirements.
    """
    
    @abstractmethod
    def sanitize_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ticket data to remove sensitive information.
        
        Args:
            ticket_data: Raw ticket data to sanitize.
            
        Returns:
            Sanitized ticket data with PII and sensitive information removed.
        """
        pass
    
    @abstractmethod
    def sanitize_log_message(self, message: str) -> str:
        """Sanitize log message to remove sensitive information.
        
        Args:
            message: Log message to sanitize.
            
        Returns:
            Sanitized log message safe for logging.
        """
        pass
    
    @abstractmethod
    def detect_sensitive_data(self, text: str) -> List[str]:
        """Detect types of sensitive data present in text.
        
        Args:
            text: Text to analyze for sensitive data.
            
        Returns:
            List of detected sensitive data types (e.g., 'email', 'ssn', 'phone').
        """
        pass
    
    @abstractmethod
    def sanitize_search_criteria(self, criteria: SearchCriteria) -> SearchCriteria:
        """Sanitize search criteria to remove sensitive information.
        
        Args:
            criteria: Search criteria to sanitize.
            
        Returns:
            Sanitized search criteria safe for logging and processing.
        """
        pass


class InputValidatorInterface(ABC):
    """Abstract interface for comprehensive input validation operations.
    
    This interface defines methods for validating and sanitizing user inputs
    to prevent injection attacks, ensure data integrity, and maintain
    system security.
    """
    
    @abstractmethod
    def validate_input(self, value: str, input_type: str) -> bool:
        """Validate input value against type-specific constraints.
        
        Args:
            value: Input value to validate.
            input_type: Type of input for validation rules (e.g., 'ticket_id', 'username').
            
        Returns:
            True if input is valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def sanitize_input(self, value: str, input_type: str) -> str:
        """Sanitize input value for safe processing.
        
        Args:
            value: Input value to sanitize.
            input_type: Type of input for sanitization rules.
            
        Returns:
            Sanitized input value safe for processing.
        """
        pass
    
    @abstractmethod
    def validate_search_criteria(self, criteria: SearchCriteria) -> bool:
        """Validate search criteria for security and correctness.
        
        Args:
            criteria: Search criteria to validate.
            
        Returns:
            True if criteria is valid and safe, False otherwise.
            
        Raises:
            ValidationError: If criteria contains invalid or dangerous content.
        """
        pass
    
    @abstractmethod
    def validate_ticket_id(self, ticket_id: str) -> bool:
        """Validate ticket ID format and security.
        
        Args:
            ticket_id: Ticket ID to validate.
            
        Returns:
            True if ticket ID is valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def validate_date_range(self, start_date: str, end_date: str) -> bool:
        """Validate date range for search operations.
        
        Args:
            start_date: Start date in ISO format.
            end_date: End date in ISO format.
            
        Returns:
            True if date range is valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def detect_injection_attempt(self, value: str) -> bool:
        """Detect potential injection attacks in input.
        
        Args:
            value: Input value to check for injection patterns.
            
        Returns:
            True if injection attempt detected, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_validation_errors(self, value: str, input_type: str) -> List[str]:
        """Get detailed validation errors for input value.
        
        Args:
            value: Input value to validate.
            input_type: Type of input for validation rules.
            
        Returns:
            List of validation error messages.
        """
        pass


class DataValidationInterface(ABC):
    """Abstract interface for data validation operations on retrieved data."""
    
    @abstractmethod
    def validate_ticket_data(self, ticket_data: Dict[str, Any]) -> bool:
        """Validate ticket data structure and content.
        
        Args:
            ticket_data: Ticket data to validate.
            
        Returns:
            True if ticket data is valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate MCP response format and structure.
        
        Args:
            response: MCP response to validate.
            
        Returns:
            True if response format is valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def clean_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize ticket data for processing.
        
        Args:
            ticket_data: Raw ticket data to clean.
            
        Returns:
            Cleaned and normalized ticket data.
        """
        pass


# CLI Interfaces
class CLICommandInterface(ABC):
    """Abstract interface for CLI command implementations."""
    
    @abstractmethod
    def execute(self, **kwargs: Any) -> int:
        """Execute the CLI command.
        
        Args:
            **kwargs: Command arguments and options.
            
        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        pass
    
    @abstractmethod
    def get_help_text(self) -> str:
        """Get help text for the command.
        
        Returns:
            Help text string.
        """
        pass


# Protocols for type checking
class Authenticatable(Protocol):
    """Protocol for objects that can be authenticated."""
    
    def authenticate(self) -> bool:
        """Perform authentication."""
        ...
    
    def is_authenticated(self) -> bool:
        """Check authentication status."""
        ...


class Analyzable(Protocol):
    """Protocol for objects that can be analyzed."""
    
    def analyze(self, data: List[Ticket]) -> AnalysisResult:
        """Perform analysis on data."""
        ...


class Reportable(Protocol):
    """Protocol for objects that can generate reports."""
    
    def generate_report(self, data: AnalysisResult) -> str:
        """Generate report from data."""
        ...