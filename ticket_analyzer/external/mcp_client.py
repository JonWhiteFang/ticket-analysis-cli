"""MCP (Model Context Protocol) client implementation.

This module provides a secure MCP client for communicating with Amazon's
internal Builder MCP services. It includes Node.js compatibility checking,
subprocess communication, connection management, and comprehensive error handling.
"""

from __future__ import annotations
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from ..interfaces import MCPClientInterface, MCPRequestInterface
from ..models import (
    MCPError,
    MCPConnectionError, 
    MCPTimeoutError,
    MCPAuthenticationError,
    MCPResponseError,
    SearchCriteria
)

logger = logging.getLogger(__name__)


class NodeCompatibilityError(Exception):
    """Raised when Node.js version is incompatible."""
    pass


@dataclass
class MCPRequest:
    """MCP request data structure."""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary format."""
        request_data = {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params
        }
        if self.id:
            request_data["id"] = self.id
        return request_data


@dataclass 
class MCPResponse:
    """MCP response data structure."""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResponse':
        """Create response from dictionary."""
        return cls(
            result=data.get("result"),
            error=data.get("error"),
            id=data.get("id")
        )
    
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.error is None
    
    def get_error_message(self) -> str:
        """Get error message from response."""
        if self.error:
            return self.error.get("message", "Unknown MCP error")
        return ""


class MCPClient(MCPClientInterface):
    """MCP client with Node.js 16+ compatibility and secure subprocess communication.
    
    This client handles communication with MCP servers through Node.js subprocess
    execution. It includes comprehensive error handling, connection management,
    and security measures for subprocess execution.
    """
    
    def __init__(self, 
                 server_command: Optional[List[str]] = None,
                 timeout: int = 30,
                 node_path: str = "node") -> None:
        """Initialize MCP client.
        
        Args:
            server_command: Command to start MCP server (defaults to Builder MCP).
            timeout: Request timeout in seconds.
            node_path: Path to Node.js executable.
        """
        self._server_command = server_command or self._get_default_server_command()
        self._timeout = timeout
        self._node_path = node_path
        self._process: Optional[subprocess.Popen] = None
        self._connected = False
        self._request_id_counter = 0
        
        # Validate Node.js compatibility on initialization
        if not self.validate_node_version():
            raise NodeCompatibilityError("Node.js 16+ is required for MCP client")
    
    def _get_default_server_command(self) -> List[str]:
        """Get default Builder MCP server command."""
        return ["npx", "@amazon-builder/mcp-server"]
    
    def validate_node_version(self) -> bool:
        """Validate Node.js version compatibility (16+).
        
        Returns:
            True if Node.js version is compatible, False otherwise.
            
        Raises:
            NodeCompatibilityError: If Node.js is not available or incompatible.
        """
        try:
            result = subprocess.run(
                [self._node_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._get_secure_env()
            )
            
            if result.returncode != 0:
                raise NodeCompatibilityError("Node.js not found or not executable")
            
            version_str = result.stdout.strip()
            if not version_str.startswith('v'):
                raise NodeCompatibilityError(f"Invalid Node.js version format: {version_str}")
            
            # Extract major version number
            version_parts = version_str[1:].split('.')
            major_version = int(version_parts[0])
            
            if major_version < 16:
                raise NodeCompatibilityError(
                    f"Node.js {major_version} is not supported. Minimum version is 16."
                )
            
            logger.info(f"Node.js version {version_str} is compatible")
            return True
            
        except subprocess.TimeoutExpired:
            raise NodeCompatibilityError("Node.js version check timed out")
        except (subprocess.SubprocessError, ValueError, IndexError) as e:
            raise NodeCompatibilityError(f"Failed to check Node.js version: {e}")
        except FileNotFoundError:
            raise NodeCompatibilityError("Node.js not found in PATH")
    
    def _get_secure_env(self) -> Dict[str, str]:
        """Get secure environment variables for subprocess execution."""
        # Start with minimal environment
        secure_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "C"),
            "NODE_ENV": "production"
        }
        
        # Add necessary authentication variables
        auth_vars = ["KRB5_CONFIG", "KRB5CCNAME", "MIDWAY_CONFIG"]
        for var in auth_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]
        
        return secure_env
    
    def connect(self) -> None:
        """Establish connection to MCP server with Node.js compatibility check.
        
        Raises:
            MCPConnectionError: If connection fails.
            NodeCompatibilityError: If Node.js version is incompatible.
        """
        if self._connected:
            logger.debug("MCP client already connected")
            return
        
        try:
            # Validate Node.js version before connecting
            self.validate_node_version()
            
            # Start MCP server process
            logger.info(f"Starting MCP server: {' '.join(self._server_command)}")
            self._process = subprocess.Popen(
                self._server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                env=self._get_secure_env()
            )
            
            # Send initialization request
            self._send_initialize_request()
            self._connected = True
            logger.info("MCP client connected successfully")
            
        except subprocess.SubprocessError as e:
            raise MCPConnectionError(f"Failed to start MCP server: {e}")
        except Exception as e:
            self._cleanup_process()
            raise MCPConnectionError(f"MCP connection failed: {e}")
    
    def disconnect(self) -> None:
        """Close connection to MCP server and cleanup resources."""
        if not self._connected:
            return
        
        try:
            # Send shutdown notification if process is still running
            if self._process and self._process.poll() is None:
                shutdown_request = MCPRequest(method="shutdown", params={})
                self._send_raw_request(shutdown_request)
        except Exception as e:
            logger.warning(f"Error during MCP shutdown: {e}")
        finally:
            self._cleanup_process()
            self._connected = False
            logger.info("MCP client disconnected")
    
    def _cleanup_process(self) -> None:
        """Clean up MCP server process."""
        if self._process:
            try:
                # Terminate process gracefully
                self._process.terminate()
                
                # Wait for process to terminate with timeout
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning("MCP server did not terminate gracefully, forcing kill")
                    self._process.kill()
                    self._process.wait()
                    
            except Exception as e:
                logger.error(f"Error cleaning up MCP process: {e}")
            finally:
                self._process = None
    
    def is_connected(self) -> bool:
        """Check if client is currently connected to MCP server.
        
        Returns:
            True if connected, False otherwise.
        """
        if not self._connected or not self._process:
            return False
        
        # Check if process is still running
        if self._process.poll() is not None:
            logger.warning("MCP server process has terminated")
            self._connected = False
            return False
        
        return True
    
    def _send_initialize_request(self) -> None:
        """Send MCP initialization request."""
        init_request = MCPRequest(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "ticket-analyzer",
                    "version": "1.0.0"
                }
            }
        )
        
        response = self._send_raw_request(init_request)
        if not response.is_success():
            raise MCPConnectionError(f"MCP initialization failed: {response.get_error_message()}")
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_id_counter += 1
        return f"req_{self._request_id_counter}_{int(time.time())}"
    
    def _send_raw_request(self, request: MCPRequest) -> MCPResponse:
        """Send raw MCP request and get response.
        
        Args:
            request: MCP request to send.
            
        Returns:
            MCP response.
            
        Raises:
            MCPError: If request fails.
            MCPTimeoutError: If request times out.
        """
        if not self._process:
            raise MCPConnectionError("MCP client not connected")
        
        # Set request ID if not provided
        if not request.id:
            request.id = self._generate_request_id()
        
        try:
            # Send request
            request_json = json.dumps(request.to_dict())
            logger.debug(f"Sending MCP request: {request.method}")
            
            self._process.stdin.write(request_json + "\n")
            self._process.stdin.flush()
            
            # Read response with timeout
            response_line = self._read_response_with_timeout()
            
            if not response_line:
                raise MCPError("No response received from MCP server")
            
            # Parse response
            response_data = json.loads(response_line.strip())
            response = MCPResponse.from_dict(response_data)
            
            logger.debug(f"Received MCP response for {request.method}")
            return response
            
        except json.JSONDecodeError as e:
            raise MCPError(f"Invalid JSON response from MCP server: {e}")
        except BrokenPipeError:
            raise MCPConnectionError("MCP server connection broken")
        except Exception as e:
            raise MCPError(f"MCP request failed: {e}")
    
    def _read_response_with_timeout(self) -> Optional[str]:
        """Read response from MCP server with timeout."""
        import select
        
        if not self._process or not self._process.stdout:
            return None
        
        # Use select for timeout on Unix systems
        if hasattr(select, 'select'):
            ready, _, _ = select.select([self._process.stdout], [], [], self._timeout)
            if ready:
                return self._process.stdout.readline()
            else:
                raise MCPTimeoutError(f"MCP request timed out after {self._timeout} seconds")
        else:
            # Fallback for Windows - simple readline with process timeout
            try:
                return self._process.stdout.readline()
            except Exception:
                raise MCPTimeoutError(f"MCP request timed out after {self._timeout} seconds")
    
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
        if not self.is_connected():
            raise MCPConnectionError("MCP client not connected")
        
        request = MCPRequest(method=method, params=params)
        response = self._send_raw_request(request)
        
        if not response.is_success():
            error_msg = response.get_error_message()
            if "authentication" in error_msg.lower():
                raise MCPAuthenticationError(f"MCP authentication failed: {error_msg}")
            else:
                raise MCPError(f"MCP request failed: {error_msg}")
        
        return response.result or {}
    
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
        try:
            # Use TicketingReadActions for ticket search
            response = self.send_request(
                method="mcp_builder_mcp_TicketingReadActions",
                params={
                    "action": "search-tickets",
                    "input": query
                }
            )
            
            # Extract tickets from response
            tickets = response.get("tickets", [])
            logger.info(f"Retrieved {len(tickets)} tickets from MCP search")
            return tickets
            
        except MCPAuthenticationError:
            raise
        except MCPError as e:
            logger.error(f"MCP ticket search failed: {e}")
            raise
        except Exception as e:
            raise MCPError(f"Unexpected error in ticket search: {e}")
    
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
        try:
            # Use TicketingReadActions for ticket retrieval
            response = self.send_request(
                method="mcp_builder_mcp_TicketingReadActions", 
                params={
                    "action": "get-ticket",
                    "input": {
                        "ticketId": ticket_id
                    }
                }
            )
            
            # Extract ticket data from response
            ticket_data = response.get("ticket")
            if ticket_data:
                logger.debug(f"Retrieved ticket {ticket_id} from MCP")
                return ticket_data
            else:
                logger.debug(f"Ticket {ticket_id} not found")
                return None
                
        except MCPAuthenticationError:
            raise
        except MCPError as e:
            logger.error(f"MCP ticket retrieval failed for {ticket_id}: {e}")
            raise
        except Exception as e:
            raise MCPError(f"Unexpected error retrieving ticket {ticket_id}: {e}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get information about connected MCP server.
        
        Returns:
            Dictionary containing server information and capabilities.
            
        Raises:
            MCPError: If server info retrieval fails.
        """
        if not self.is_connected():
            raise MCPConnectionError("MCP client not connected")
        
        try:
            # Send server info request
            response = self.send_request("server/info", {})
            return response
        except Exception as e:
            raise MCPError(f"Failed to get server info: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on MCP connection.
        
        Returns:
            Dictionary containing health status and diagnostic information.
        """
        health_info = {
            "connected": False,
            "node_version": None,
            "server_responsive": False,
            "error_message": None
        }
        
        try:
            # Check Node.js version
            if self.validate_node_version():
                result = subprocess.run(
                    [self._node_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                health_info["node_version"] = result.stdout.strip()
            
            # Check connection status
            health_info["connected"] = self.is_connected()
            
            # Test server responsiveness
            if health_info["connected"]:
                start_time = time.time()
                self.send_request("ping", {})
                response_time = (time.time() - start_time) * 1000
                health_info["server_responsive"] = True
                health_info["response_time_ms"] = response_time
            
        except Exception as e:
            health_info["error_message"] = str(e)
        
        return health_info
    
    def __enter__(self) -> 'MCPClient':
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()


class MCPRequestFormatter(MCPRequestInterface):
    """Formatter for MCP requests to standardize request format."""
    
    def format_search_request(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Format search criteria into MCP request format.
        
        Args:
            criteria: Search criteria to format.
            
        Returns:
            Dictionary formatted for MCP request.
        """
        request_params = {}
        
        # Add status filters
        if criteria.status_filters:
            request_params["status"] = criteria.status_filters
        
        # Add assignee filter
        if criteria.assignee:
            request_params["assignee"] = criteria.assignee
        
        # Add date range filters
        if criteria.start_date:
            request_params["createDate"] = f"[{criteria.start_date.isoformat()}Z TO *]"
        
        if criteria.end_date:
            request_params["createDate"] = f"[* TO {criteria.end_date.isoformat()}Z]"
        
        if criteria.start_date and criteria.end_date:
            request_params["createDate"] = (
                f"[{criteria.start_date.isoformat()}Z TO {criteria.end_date.isoformat()}Z]"
            )
        
        # Add full text search
        if criteria.search_text:
            request_params["fullText"] = criteria.search_text
        
        # Add Lucene query if provided
        if criteria.lucene_query:
            request_params["query"] = criteria.lucene_query
        
        # Add pagination
        request_params["rows"] = criteria.max_results or 100
        if criteria.offset:
            request_params["start"] = criteria.offset
        
        return request_params
    
    def format_ticket_request(self, ticket_id: str) -> Dict[str, Any]:
        """Format ticket ID request into MCP request format.
        
        Args:
            ticket_id: Ticket ID to format.
            
        Returns:
            Dictionary formatted for MCP request.
        """
        return {"ticketId": ticket_id}
    
    def parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse MCP response into standardized format.
        
        Args:
            response: Raw MCP response.
            
        Returns:
            List of parsed ticket data.
            
        Raises:
            MCPResponseError: If response format is invalid.
        """
        if "tickets" in response:
            return response["tickets"]
        elif "ticket" in response:
            return [response["ticket"]]
        elif "results" in response:
            return response["results"]
        else:
            # Return empty list if no tickets found
            return []