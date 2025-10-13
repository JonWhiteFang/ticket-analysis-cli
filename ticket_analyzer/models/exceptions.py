"""Custom exception hierarchy for ticket analysis operations."""

from __future__ import annotations
from typing import Optional, Dict, Any


class TicketAnalysisError(Exception):
    """Base exception for all ticket analysis errors.
    
    This is the root exception class that all other custom exceptions
    inherit from. It provides a consistent interface for error handling
    throughout the application.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class AuthenticationError(TicketAnalysisError):
    """Raised when authentication operations fail.
    
    This includes failures in Midway authentication, session timeouts,
    and credential validation errors.
    """
    pass


class ConfigurationError(TicketAnalysisError):
    """Raised when configuration is invalid or missing.
    
    This includes malformed configuration files, missing required settings,
    and invalid configuration values.
    """
    pass


class DataRetrievalError(TicketAnalysisError):
    """Raised when data retrieval operations fail.
    
    This includes MCP connection failures, API errors, network timeouts,
    and data parsing errors.
    """
    pass


class AnalysisError(TicketAnalysisError):
    """Raised when analysis operations fail.
    
    This includes calculation errors, invalid data for analysis,
    and processing failures.
    """
    pass


class ValidationError(TicketAnalysisError):
    """Raised when data validation fails.
    
    This includes input validation errors, data format issues,
    and security validation failures.
    """
    pass


class MCPError(DataRetrievalError):
    """Raised when MCP operations fail."""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operations timeout."""
    pass


class MCPAuthenticationError(MCPError):
    """Raised when MCP authentication fails."""
    pass


class CircuitBreakerOpenError(DataRetrievalError):
    """Raised when circuit breaker is open."""
    pass


class DataProcessingError(AnalysisError):
    """Raised when data processing fails."""
    pass


class ReportGenerationError(TicketAnalysisError):
    """Raised when report generation fails."""
    pass


class SecurityError(TicketAnalysisError):
    """Raised when security violations are detected."""
    pass