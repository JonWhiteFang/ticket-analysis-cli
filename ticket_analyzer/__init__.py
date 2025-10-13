"""Ticket Analysis CLI Application.

A secure, Python 3.7-compatible CLI tool for analyzing ticket data from Amazon's 
internal systems using MCP (Model Context Protocol) integration.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Amazon Development Team"
__email__ = "dev-team@amazon.com"

# Core exports
from .models.ticket import Ticket, TicketStatus, TicketSeverity
from .models.analysis import AnalysisResult, SearchCriteria
from .models.config import ReportConfig, AuthConfig
from .models.exceptions import (
    TicketAnalysisError,
    AuthenticationError,
    ConfigurationError,
    DataRetrievalError,
    AnalysisError
)

__all__ = [
    "Ticket",
    "TicketStatus", 
    "TicketSeverity",
    "AnalysisResult",
    "SearchCriteria",
    "ReportConfig",
    "AuthConfig",
    "TicketAnalysisError",
    "AuthenticationError",
    "ConfigurationError", 
    "DataRetrievalError",
    "AnalysisError"
]