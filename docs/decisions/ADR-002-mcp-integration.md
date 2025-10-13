# ADR-002: Adopt MCP for Data Access

## Status
Accepted

## Context

The Ticket Analysis CLI needs reliable access to Amazon's internal ticketing systems. We evaluated several approaches for data access:

1. **Direct Database Access**: Connect directly to ticket system databases
2. **REST API Integration**: Use existing REST APIs for ticket data
3. **MCP Integration**: Use Model Context Protocol (Builder MCP) for data access
4. **File-based Import**: Process exported ticket data files

Key requirements:
- Secure authentication with Amazon internal systems
- Consistent data format and structure
- Rate limiting and resilience patterns
- Compliance with internal security policies
- Maintainability and platform support

## Decision

We will use Model Context Protocol (MCP) with Builder MCP integration for ticket data access.

Specifically:
- **Primary Integration**: `mcp_builder_mcp_TicketingReadActions` for ticket search and retrieval
- **Secondary Integration**: `mcp_builder_mcp_TaskeiGetTask` and `mcp_builder_mcp_TaskeiListTasks` for task data
- **Authentication**: Leverage MCP's built-in Midway authentication
- **Resilience**: Implement circuit breaker and retry patterns around MCP calls

## Consequences

### Positive
- **Standardized Protocol**: MCP provides consistent interface across Amazon services
- **Built-in Authentication**: Automatic Midway integration without custom auth handling
- **Platform Maintained**: MCP infrastructure is maintained by platform teams
- **Security Compliance**: Meets Amazon's internal security requirements
- **Rate Limiting**: Built-in rate limiting and throttling protection
- **Consistent Data Format**: Standardized response formats across different ticket systems

### Negative
- **External Dependency**: Relies on MCP infrastructure availability
- **Learning Curve**: Team needs to understand MCP concepts and patterns
- **Limited Control**: Cannot optimize queries beyond MCP capabilities
- **Potential Latency**: Additional network hop through MCP layer
- **Version Dependencies**: Must maintain compatibility with MCP protocol versions

## Implementation Notes

### MCP Client Architecture

```python
class MCPClient:
    """Client for communicating with MCP services."""
    
    def __init__(self, server_command: List[str]):
        self._server_command = server_command
        self._process: Optional[subprocess.Popen] = None
    
    def search_tickets(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search tickets via MCP TicketingReadActions."""
        request = MCPRequest(
            method="mcp_builder_mcp_TicketingReadActions",
            params={
                "action": "search-tickets",
                "input": query
            }
        )
        return self._send_request(request)
```

### Resilience Patterns

**Circuit Breaker**: Prevent cascading failures when MCP is unavailable
```python
class CircuitBreaker:
    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerOpenError("MCP service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

**Retry Logic**: Handle transient failures with exponential backoff
```python
class MCPRetryPolicy:
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except (MCPConnectionError, MCPTimeoutError) as e:
                if attempt < self.max_attempts - 1:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    time.sleep(delay)
                    continue
                raise
```

### Error Handling Strategy

- **Connection Errors**: Retry with exponential backoff
- **Authentication Errors**: Trigger re-authentication flow
- **Rate Limiting**: Respect rate limits and back off appropriately
- **Data Errors**: Log and continue processing with available data
- **Service Unavailable**: Fail fast with circuit breaker

### Configuration

```python
# MCP configuration
MCP_CONFIG = {
    "server_command": ["node", "mcp-server.js"],
    "timeout_seconds": 30,
    "max_retries": 3,
    "circuit_breaker": {
        "failure_threshold": 5,
        "timeout_minutes": 1
    }
}
```

### Testing Strategy

**Unit Tests**: Mock MCP client for isolated testing
```python
@pytest.fixture
def mock_mcp_client():
    with patch('ticket_analyzer.external.mcp_client.MCPClient') as mock:
        yield mock.return_value
```

**Integration Tests**: Test against MCP test environment
```python
def test_mcp_integration_search():
    client = MCPClient(test_server_command)
    results = client.search_tickets({"status": ["Open"]})
    assert len(results) >= 0
```

**Contract Tests**: Verify MCP response format compatibility
```python
def test_mcp_response_format():
    response = client.search_tickets(test_query)
    assert all(required_field in ticket for ticket in response 
              for required_field in ["id", "title", "status"])
```

### Migration Considerations

If MCP becomes unavailable or deprecated:
1. **Abstraction Layer**: Repository pattern allows switching implementations
2. **Fallback Options**: Could implement direct API or database access
3. **Data Compatibility**: Maintain consistent internal data models
4. **Configuration**: Support multiple data source configurations

### Performance Considerations

- **Connection Pooling**: Reuse MCP connections when possible
- **Batch Requests**: Group multiple ticket requests when supported
- **Caching**: Cache frequently accessed data with appropriate TTL
- **Pagination**: Handle large result sets efficiently

## Date
2024-01-16

## Participants
- Development Team
- Platform Architecture Team
- Security Team
- MCP Platform Team