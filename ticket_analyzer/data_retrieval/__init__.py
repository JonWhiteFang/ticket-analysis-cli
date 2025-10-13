"""Data retrieval package.

This package contains components for retrieving ticket data from external
sources, including MCP-based repositories, data validation, and caching.
"""

from __future__ import annotations

# Import repository implementations
from .mcp_ticket_repository import (
    MCPTicketRepository,
    TicketDataMapper
)

# Import validation components
from .validation import (
    InputValidator,
    DataValidator,
    SearchCriteriaValidator
)

__all__ = [
    # Repository implementations
    "MCPTicketRepository",
    "TicketDataMapper",
    
    # Validation components
    "InputValidator",
    "DataValidator", 
    "SearchCriteriaValidator"
]