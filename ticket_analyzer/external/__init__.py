"""External integrations package.

This package contains integrations with external services and systems,
including MCP (Model Context Protocol) clients, authentication services,
and resilience patterns for external service communication.
"""

from __future__ import annotations

# Import MCP client components
from .mcp_client import (
    MCPClient,
    MCPRequest,
    MCPResponse,
    NodeCompatibilityError
)

# Import resilience components  
from .resilience import (
    CircuitBreaker,
    RetryPolicy,
    ExponentialBackoff,
    ResilienceManager
)

__all__ = [
    # MCP components
    "MCPClient",
    "MCPRequest", 
    "MCPResponse",
    "NodeCompatibilityError",
    
    # Resilience components
    "CircuitBreaker",
    "RetryPolicy", 
    "ExponentialBackoff",
    "ResilienceManager"
]