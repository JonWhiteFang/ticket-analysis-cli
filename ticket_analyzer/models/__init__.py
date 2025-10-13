"""Models package for ticket analyzer.

This package contains all data models, enums, and exceptions used throughout
the application. Models are organized by functionality and follow Python 3.7
compatibility requirements.
"""

from __future__ import annotations

# Import all models for easy access
from .ticket import Ticket, TicketStatus, TicketSeverity
from .analysis import AnalysisResult, SearchCriteria
from .config import ReportConfig, AuthConfig
from .exceptions import (
    TicketAnalysisError,
    AuthenticationError,
    ConfigurationError,
    DataRetrievalError,
    AnalysisError,
    ValidationError,
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPAuthenticationError,
    CircuitBreakerOpenError,
    DataProcessingError,
    ReportGenerationError,
    SecurityError
)

__all__ = [
    # Core models
    "Ticket",
    "TicketStatus",
    "TicketSeverity",
    "AnalysisResult", 
    "SearchCriteria",
    "ReportConfig",
    "AuthConfig",
    
    # Exceptions
    "TicketAnalysisError",
    "AuthenticationError",
    "ConfigurationError",
    "DataRetrievalError", 
    "AnalysisError",
    "ValidationError",
    "MCPError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPAuthenticationError",
    "CircuitBreakerOpenError",
    "DataProcessingError",
    "ReportGenerationError",
    "SecurityError"
]