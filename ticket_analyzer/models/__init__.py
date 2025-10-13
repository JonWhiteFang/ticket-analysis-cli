"""Models package for ticket analyzer.

This package contains all data models, configuration classes, and exceptions
used throughout the ticket analyzer application. All models are Python 3.7
compatible and use dataclasses with proper type hints.
"""

from __future__ import annotations

# Import ticket models
from .ticket import (
    Ticket,
    TicketStatus,
    TicketSeverity
)

# Import analysis models
from .analysis import (
    SearchCriteria,
    AnalysisResult,
    MetricDefinition,
    TrendPoint,
    TrendAnalysis
)

# Import configuration models
from .config import (
    ReportConfig,
    AuthConfig,
    MCPConfig,
    LoggingConfig,
    ApplicationConfig,
    OutputFormat,
    LogLevel
)

# Import exceptions
from .exceptions import (
    # Base exception
    TicketAnalysisError,
    
    # Core exceptions
    AuthenticationError,
    ConfigurationError,
    DataRetrievalError,
    AnalysisError,
    ValidationError,
    
    # MCP exceptions
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPAuthenticationError,
    MCPResponseError,
    
    # Resilience exceptions
    CircuitBreakerOpenError,
    
    # Processing exceptions
    DataProcessingError,
    ReportGenerationError,
    SecurityError,
    CLIError,
    FileOperationError,
    
    # Utility functions
    create_error_context,
    wrap_exception
)

# Export all public classes and functions
__all__ = [
    # Ticket models
    "Ticket",
    "TicketStatus", 
    "TicketSeverity",
    
    # Analysis models
    "SearchCriteria",
    "AnalysisResult",
    "MetricDefinition",
    "TrendPoint",
    "TrendAnalysis",
    
    # Configuration models
    "ReportConfig",
    "AuthConfig",
    "MCPConfig",
    "LoggingConfig",
    "ApplicationConfig",
    "OutputFormat",
    "LogLevel",
    
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
    "MCPResponseError",
    "CircuitBreakerOpenError",
    "DataProcessingError",
    "ReportGenerationError",
    "SecurityError",
    "CLIError",
    "FileOperationError",
    "create_error_context",
    "wrap_exception"
]