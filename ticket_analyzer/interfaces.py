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


# Data Retrieval Interfaces
class DataRetrievalInterface(ABC):
    """Abstract interface for ticket data retrieval operations."""
    
    @abstractmethod
    def search_tickets(self, criteria: SearchCriteria) -> List[Ticket]:
        """Search for tickets based on criteria.
        
        Args:
            criteria: Search criteria for filtering tickets.
            
        Returns:
            List of tickets matching the criteria.
            
        Raises:
            DataRetrievalError: If search operation fails.
        """
        pass
    
    @abstractmethod
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Retrieve a specific ticket by ID.
        
        Args:
            ticket_id: Unique identifier for the ticket.
            
        Returns:
            Ticket object if found, None otherwise.
            
        Raises:
            DataRetrievalError: If retrieval operation fails.
        """
        pass
    
    @abstractmethod
    def count_tickets(self, criteria: SearchCriteria) -> int:
        """Count tickets matching criteria without retrieving them.
        
        Args:
            criteria: Search criteria for filtering tickets.
            
        Returns:
            Number of tickets matching criteria.
            
        Raises:
            DataRetrievalError: If count operation fails.
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


class ConfigurationHandlerInterface(ABC):
    """Abstract interface for configuration source handlers."""
    
    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Check if handler can process the configuration source."""
        pass
    
    @abstractmethod
    def load_from_source(self, source: str) -> Dict[str, Any]:
        """Load configuration from specific source."""
        pass


# External Service Interfaces
class MCPClientInterface(ABC):
    """Abstract interface for MCP client operations."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to MCP server.
        
        Raises:
            MCPConnectionError: If connection fails.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to MCP server."""
        pass
    
    @abstractmethod
    def search_tickets(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search tickets via MCP.
        
        Args:
            query: Search query parameters.
            
        Returns:
            List of raw ticket data.
            
        Raises:
            MCPError: If search operation fails.
        """
        pass
    
    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket by ID via MCP.
        
        Args:
            ticket_id: Ticket identifier.
            
        Returns:
            Raw ticket data if found, None otherwise.
            
        Raises:
            MCPError: If retrieval operation fails.
        """
        pass


# Security and Validation Interfaces
class DataSanitizerInterface(ABC):
    """Abstract interface for data sanitization operations."""
    
    @abstractmethod
    def sanitize_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ticket data to remove sensitive information.
        
        Args:
            ticket_data: Raw ticket data to sanitize.
            
        Returns:
            Sanitized ticket data.
        """
        pass
    
    @abstractmethod
    def sanitize_log_message(self, message: str) -> str:
        """Sanitize log message to remove sensitive information.
        
        Args:
            message: Log message to sanitize.
            
        Returns:
            Sanitized log message.
        """
        pass


class InputValidatorInterface(ABC):
    """Abstract interface for input validation operations."""
    
    @abstractmethod
    def validate_input(self, value: str, input_type: str) -> bool:
        """Validate input value against type constraints.
        
        Args:
            value: Input value to validate.
            input_type: Type of input for validation rules.
            
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
            Sanitized input value.
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