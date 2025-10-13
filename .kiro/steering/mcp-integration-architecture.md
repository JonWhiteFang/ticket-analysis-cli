# MCP Integration Architecture

## Builder MCP Integration Patterns

### MCP Client Architecture
```python
from __future__ import annotations
import subprocess
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class MCPRequest:
    """MCP request structure."""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

@dataclass
class MCPResponse:
    """MCP response structure."""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPClient:
    """Client for communicating with MCP services."""
    
    def __init__(self, server_command: List[str]) -> None:
        self._server_command = server_command
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
    
    def connect(self) -> None:
        """Establish connection to MCP server."""
        try:
            self._process = subprocess.Popen(
                self._server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            # Initialize handshake
            self._send_initialize_request()
        except Exception as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
    
    def disconnect(self) -> None:
        """Close connection to MCP server."""
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
```

### Node.js Subprocess Communication
```python
import json
import subprocess
from typing import Dict, Any, List

class NodeMCPBridge:
    """Bridge for communicating with Node.js MCP servers."""
    
    def __init__(self, node_script_path: str) -> None:
        self._script_path = node_script_path
        self._process: Optional[subprocess.Popen] = None
    
    def start_server(self) -> None:
        """Start Node.js MCP server process."""
        try:
            self._process = subprocess.Popen(
                ["node", self._script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._get_node_env()
            )
        except FileNotFoundError:
            raise MCPError("Node.js not found. Please install Node.js 16+")
    
    def _get_node_env(self) -> Dict[str, str]:
        """Get environment variables for Node.js process."""
        import os
        env = os.environ.copy()
        env.update({
            "NODE_ENV": "production",
            "MCP_LOG_LEVEL": "error"
        })
        return env
    
    def send_request(self, request: MCPRequest) -> MCPResponse:
        """Send request to Node.js MCP server."""
        if not self._process:
            raise MCPError("MCP server not started")
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": request.method,
            "params": request.params,
            "id": request.id or self._generate_id()
        })
        
        try:
            self._process.stdin.write(request_json + "\n")
            self._process.stdin.flush()
            
            response_line = self._process.stdout.readline()
            if not response_line:
                raise MCPError("No response from MCP server")
            
            response_data = json.loads(response_line.strip())
            return MCPResponse(
                result=response_data.get("result"),
                error=response_data.get("error"),
                id=response_data.get("id")
            )
        except json.JSONDecodeError as e:
            raise MCPError(f"Invalid JSON response: {e}")
```

### Error Handling and Retry Logic
```python
import time
from typing import Callable, TypeVar, Any
from functools import wraps

T = TypeVar('T')

class MCPRetryPolicy:
    """Retry policy for MCP operations."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 10.0, backoff_factor: float = 2.0) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except (MCPConnectionError, MCPTimeoutError) as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    time.sleep(delay)
                    continue
                break
            except MCPError:
                # Don't retry on non-recoverable errors
                raise
        
        raise last_exception

def with_retry(policy: MCPRetryPolicy):
    """Decorator for adding retry logic to MCP operations."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return policy.execute(func, *args, **kwargs)
        return wrapper
    return decorator

# Usage
retry_policy = MCPRetryPolicy(max_attempts=3, base_delay=1.0)

class ResilientMCPClient(MCPClient):
    """MCP client with built-in retry logic."""
    
    @with_retry(retry_policy)
    def search_tickets(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search tickets with retry logic."""
        request = MCPRequest(method="search_tickets", params=query)
        response = self.send_request(request)
        
        if response.error:
            raise MCPError(f"Search failed: {response.error}")
        
        return response.result.get("tickets", [])
```

### Authentication Flow Integration
```python
import subprocess
from typing import Optional

class MidwayAuthenticator:
    """Handle Midway authentication for MCP operations."""
    
    def __init__(self) -> None:
        self._authenticated = False
        self._auth_token: Optional[str] = None
    
    def ensure_authenticated(self) -> None:
        """Ensure user is authenticated with Midway."""
        if not self._is_authenticated():
            self._perform_authentication()
    
    def _is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        try:
            result = subprocess.run(
                ["mwinit", "-s"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _perform_authentication(self) -> None:
        """Perform Midway authentication."""
        try:
            result = subprocess.run(
                ["mwinit", "-o"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise AuthenticationError(
                    f"Authentication failed: {result.stderr}"
                )
            
            self._authenticated = True
        except subprocess.TimeoutExpired:
            raise AuthenticationError("Authentication timeout")
        except FileNotFoundError:
            raise AuthenticationError("mwinit command not found")

class AuthenticatedMCPClient(MCPClient):
    """MCP client with automatic authentication."""
    
    def __init__(self, server_command: List[str]) -> None:
        super().__init__(server_command)
        self._authenticator = MidwayAuthenticator()
    
    def connect(self) -> None:
        """Connect with authentication check."""
        self._authenticator.ensure_authenticated()
        super().connect()
    
    def send_request(self, request: MCPRequest) -> MCPResponse:
        """Send request with authentication retry."""
        try:
            return super().send_request(request)
        except MCPAuthenticationError:
            # Re-authenticate and retry once
            self._authenticator._perform_authentication()
            return super().send_request(request)
```

### Data Serialization and Validation
```python
from typing import Any, Dict, List
from dataclasses import dataclass, asdict
import json

@dataclass
class TicketSearchCriteria:
    """Criteria for ticket search operations."""
    status: Optional[List[str]] = None
    assignee: Optional[str] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    max_results: int = 100
    
    def to_mcp_params(self) -> Dict[str, Any]:
        """Convert to MCP request parameters."""
        params = {}
        
        if self.status:
            params["status"] = self.status
        if self.assignee:
            params["assignee"] = self.assignee
        if self.created_after:
            params["created_after"] = self.created_after
        if self.created_before:
            params["created_before"] = self.created_before
        
        params["max_results"] = self.max_results
        return params
    
    def validate(self) -> None:
        """Validate search criteria."""
        if self.max_results <= 0:
            raise ValueError("max_results must be positive")
        
        if self.max_results > 1000:
            raise ValueError("max_results cannot exceed 1000")

class MCPDataValidator:
    """Validator for MCP request/response data."""
    
    @staticmethod
    def validate_ticket_data(data: Dict[str, Any]) -> bool:
        """Validate ticket data structure."""
        required_fields = {"id", "title", "status"}
        return all(field in data for field in required_fields)
    
    @staticmethod
    def sanitize_response_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize response data for security."""
        sanitized = []
        for item in data:
            # Remove sensitive fields
            clean_item = {
                k: v for k, v in item.items()
                if k not in {"internal_notes", "private_data"}
            }
            sanitized.append(clean_item)
        return sanitized
```

### Connection Pooling and Resource Management
```python
from contextlib import contextmanager
from typing import Generator, Dict, Any
import threading

class MCPConnectionPool:
    """Connection pool for MCP clients."""
    
    def __init__(self, max_connections: int = 5) -> None:
        self._max_connections = max_connections
        self._connections: List[MCPClient] = []
        self._available: List[MCPClient] = []
        self._lock = threading.Lock()
    
    @contextmanager
    def get_connection(self) -> Generator[MCPClient, None, None]:
        """Get connection from pool with context management."""
        client = self._acquire_connection()
        try:
            yield client
        finally:
            self._release_connection(client)
    
    def _acquire_connection(self) -> MCPClient:
        """Acquire connection from pool."""
        with self._lock:
            if self._available:
                return self._available.pop()
            
            if len(self._connections) < self._max_connections:
                client = MCPClient(["node", "mcp-server.js"])
                client.connect()
                self._connections.append(client)
                return client
            
            # Wait for available connection
            raise MCPError("No available connections")
    
    def _release_connection(self, client: MCPClient) -> None:
        """Release connection back to pool."""
        with self._lock:
            self._available.append(client)

# Usage
connection_pool = MCPConnectionPool(max_connections=3)

def search_tickets_with_pool(criteria: TicketSearchCriteria) -> List[Dict[str, Any]]:
    """Search tickets using connection pool."""
    with connection_pool.get_connection() as client:
        request = MCPRequest(
            method="search_tickets",
            params=criteria.to_mcp_params()
        )
        response = client.send_request(request)
        return response.result.get("tickets", [])
```