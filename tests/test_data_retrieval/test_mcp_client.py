"""Comprehensive tests for MCP client implementation.

This module contains unit tests for the MCPClient class,
including Node.js compatibility, subprocess communication, and error handling.
"""

import pytest
import subprocess
import json
import os
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, call, MagicMock

from ticket_analyzer.external.mcp_client import (
    MCPClient,
    MCPRequest,
    MCPResponse,
    MCPRequestFormatter,
    NodeCompatibilityError
)
from ticket_analyzer.models import (
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPAuthenticationError,
    MCPResponseError,
    SearchCriteria
)


class TestMCPRequest:
    """Test cases for MCPRequest class."""
    
    def test_request_creation(self) -> None:
        """Test MCPRequest creation and serialization."""
        request = MCPRequest(
            method="test_method",
            params={"key": "value"},
            id="test_id"
        )
        
        assert request.method == "test_method"
        assert request.params == {"key": "value"}
        assert request.id == "test_id"
    
    def test_request_to_dict(self) -> None:
        """Test MCPRequest serialization to dictionary."""
        request = MCPRequest(
            method="search_tickets",
            params={"status": "Open"},
            id="req_123"
        )
        
        result = request.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "method": "search_tickets",
            "params": {"status": "Open"},
            "id": "req_123"
        }
        
        assert result == expected
    
    def test_request_to_dict_without_id(self) -> None:
        """Test MCPRequest serialization without ID."""
        request = MCPRequest(
            method="test_method",
            params={"key": "value"}
        )
        
        result = request.to_dict()
        
        assert "id" not in result
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "test_method"
        assert result["params"] == {"key": "value"}


class TestMCPResponse:
    """Test cases for MCPResponse class."""
    
    def test_response_creation_success(self) -> None:
        """Test MCPResponse creation for successful response."""
        response = MCPResponse(
            result={"tickets": []},
            id="req_123"
        )
        
        assert response.result == {"tickets": []}
        assert response.error is None
        assert response.id == "req_123"
        assert response.is_success() is True
    
    def test_response_creation_error(self) -> None:
        """Test MCPResponse creation for error response."""
        response = MCPResponse(
            error={"code": -1, "message": "Test error"},
            id="req_123"
        )
        
        assert response.result is None
        assert response.error == {"code": -1, "message": "Test error"}
        assert response.is_success() is False
        assert response.get_error_message() == "Test error"
    
    def test_response_from_dict_success(self) -> None:
        """Test MCPResponse creation from dictionary (success)."""
        data = {
            "jsonrpc": "2.0",
            "result": {"tickets": [{"id": "T123"}]},
            "id": "req_123"
        }
        
        response = MCPResponse.from_dict(data)
        
        assert response.result == {"tickets": [{"id": "T123"}]}
        assert response.error is None
        assert response.id == "req_123"
        assert response.is_success() is True
    
    def test_response_from_dict_error(self) -> None:
        """Test MCPResponse creation from dictionary (error)."""
        data = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
            "id": "req_123"
        }
        
        response = MCPResponse.from_dict(data)
        
        assert response.result is None
        assert response.error == {"code": -32600, "message": "Invalid Request"}
        assert response.get_error_message() == "Invalid Request"
        assert response.is_success() is False
    
    def test_get_error_message_no_error(self) -> None:
        """Test get_error_message when no error exists."""
        response = MCPResponse(result={"success": True})
        
        assert response.get_error_message() == ""
    
    def test_get_error_message_no_message_field(self) -> None:
        """Test get_error_message when error has no message field."""
        response = MCPResponse(error={"code": -1})
        
        assert response.get_error_message() == "Unknown MCP error"


class TestMCPClient:
    """Test cases for MCPClient class."""
    
    @pytest.fixture
    def mock_subprocess_success(self) -> Mock:
        """Mock successful subprocess execution."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.wait.return_value = 0
        mock_process.terminate.return_value = None
        mock_process.kill.return_value = None
        return mock_process
    
    @pytest.fixture
    def client(self) -> MCPClient:
        """Provide MCPClient instance for testing."""
        return MCPClient(timeout=10)
    
    def test_initialization_default_command(self) -> None:
        """Test MCPClient initialization with default server command."""
        client = MCPClient()
        
        assert client._server_command == ["npx", "@amazon-builder/mcp-server"]
        assert client._timeout == 30  # Default timeout
        assert client._connected is False
    
    def test_initialization_custom_command(self) -> None:
        """Test MCPClient initialization with custom server command."""
        custom_command = ["node", "custom-mcp-server.js"]
        client = MCPClient(server_command=custom_command, timeout=60)
        
        assert client._server_command == custom_command
        assert client._timeout == 60
        assert client._connected is False
    
    @patch('subprocess.run')
    def test_validate_node_version_success(self, mock_run: Mock, client: MCPClient) -> None:
        """Test successful Node.js version validation."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "v18.17.0\n"
        mock_run.return_value = mock_result
        
        result = client.validate_node_version()
        
        assert result is True
        mock_run.assert_called_once_with(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=client._get_secure_env()
        )
    
    @patch('subprocess.run')
    def test_validate_node_version_old_version(self, mock_run: Mock, client: MCPClient) -> None:
        """Test Node.js version validation with old version."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "v14.21.3\n"  # Too old
        mock_run.return_value = mock_result
        
        with pytest.raises(NodeCompatibilityError) as exc_info:
            client.validate_node_version()
        
        assert "Node.js 14 is not supported" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_validate_node_version_not_found(self, mock_run: Mock, client: MCPClient) -> None:
        """Test Node.js version validation when Node.js not found."""
        mock_run.side_effect = FileNotFoundError("node not found")
        
        with pytest.raises(NodeCompatibilityError) as exc_info:
            client.validate_node_version()
        
        assert "Node.js not found in PATH" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_validate_node_version_timeout(self, mock_run: Mock, client: MCPClient) -> None:
        """Test Node.js version validation timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("node", 10)
        
        with pytest.raises(NodeCompatibilityError) as exc_info:
            client.validate_node_version()
        
        assert "Node.js version check timed out" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_validate_node_version_invalid_format(self, mock_run: Mock, client: MCPClient) -> None:
        """Test Node.js version validation with invalid version format."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid-version-format\n"
        mock_run.return_value = mock_result
        
        with pytest.raises(NodeCompatibilityError) as exc_info:
            client.validate_node_version()
        
        assert "Invalid Node.js version format" in str(exc_info.value)    def t
est_get_secure_env(self, client: MCPClient) -> None:
        """Test secure environment variable generation."""
        test_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/test",
            "USER": "testuser",
            "LANG": "en_US.UTF-8",
            "KRB5_CONFIG": "/etc/krb5.conf",
            "KRB5CCNAME": "/tmp/krb5cc_test",
            "SENSITIVE_VAR": "should_not_be_included",
            "PASSWORD": "secret123"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            secure_env = client._get_secure_env()
        
        # Check expected variables are included
        assert secure_env["PATH"] == "/usr/bin:/bin"
        assert secure_env["HOME"] == "/home/test"
        assert secure_env["USER"] == "testuser"
        assert secure_env["LANG"] == "en_US.UTF-8"
        assert secure_env["NODE_ENV"] == "production"
        assert secure_env["KRB5_CONFIG"] == "/etc/krb5.conf"
        assert secure_env["KRB5CCNAME"] == "/tmp/krb5cc_test"
        
        # Check sensitive variables are not included
        assert "SENSITIVE_VAR" not in secure_env
        assert "PASSWORD" not in secure_env
    
    @patch('subprocess.Popen')
    @patch.object(MCPClient, 'validate_node_version')
    def test_connect_success(self, mock_validate: Mock, mock_popen: Mock,
                           client: MCPClient, mock_subprocess_success: Mock) -> None:
        """Test successful MCP client connection."""
        mock_validate.return_value = True
        mock_popen.return_value = mock_subprocess_success
        
        # Mock successful initialization response
        init_response = {
            "jsonrpc": "2.0",
            "result": {"capabilities": {}},
            "id": "req_1"
        }
        mock_subprocess_success.stdout.readline.return_value = json.dumps(init_response) + "\n"
        
        client.connect()
        
        assert client._connected is True
        assert client._process == mock_subprocess_success
        mock_validate.assert_called_once()
        mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    @patch.object(MCPClient, 'validate_node_version')
    def test_connect_node_validation_failure(self, mock_validate: Mock, mock_popen: Mock,
                                           client: MCPClient) -> None:
        """Test connection failure due to Node.js validation."""
        mock_validate.side_effect = NodeCompatibilityError("Node.js too old")
        
        with pytest.raises(MCPConnectionError) as exc_info:
            client.connect()
        
        assert "MCP connection failed" in str(exc_info.value)
        assert client._connected is False
        mock_popen.assert_not_called()
    
    @patch('subprocess.Popen')
    @patch.object(MCPClient, 'validate_node_version')
    def test_connect_subprocess_failure(self, mock_validate: Mock, mock_popen: Mock,
                                      client: MCPClient) -> None:
        """Test connection failure due to subprocess error."""
        mock_validate.return_value = True
        mock_popen.side_effect = subprocess.SubprocessError("Failed to start process")
        
        with pytest.raises(MCPConnectionError) as exc_info:
            client.connect()
        
        assert "Failed to start MCP server" in str(exc_info.value)
        assert client._connected is False
    
    def test_disconnect_when_not_connected(self, client: MCPClient) -> None:
        """Test disconnect when client is not connected."""
        # Should not raise exception
        client.disconnect()
        
        assert client._connected is False
        assert client._process is None
    
    @patch.object(MCPClient, '_cleanup_process')
    def test_disconnect_when_connected(self, mock_cleanup: Mock, client: MCPClient,
                                     mock_subprocess_success: Mock) -> None:
        """Test disconnect when client is connected."""
        client._connected = True
        client._process = mock_subprocess_success
        
        # Mock successful shutdown response
        shutdown_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": "req_shutdown"
        }
        mock_subprocess_success.stdout.readline.return_value = json.dumps(shutdown_response) + "\n"
        
        client.disconnect()
        
        assert client._connected is False
        mock_cleanup.assert_called_once()
    
    def test_cleanup_process_graceful_termination(self, client: MCPClient,
                                                mock_subprocess_success: Mock) -> None:
        """Test graceful process cleanup."""
        client._process = mock_subprocess_success
        mock_subprocess_success.wait.return_value = 0  # Graceful termination
        
        client._cleanup_process()
        
        mock_subprocess_success.terminate.assert_called_once()
        mock_subprocess_success.wait.assert_called_once_with(timeout=5)
        mock_subprocess_success.kill.assert_not_called()
        assert client._process is None
    
    def test_cleanup_process_force_kill(self, client: MCPClient,
                                      mock_subprocess_success: Mock) -> None:
        """Test process cleanup with force kill."""
        client._process = mock_subprocess_success
        mock_subprocess_success.wait.side_effect = [
            subprocess.TimeoutExpired("mcp-server", 5),  # First wait times out
            0  # Second wait after kill succeeds
        ]
        
        client._cleanup_process()
        
        mock_subprocess_success.terminate.assert_called_once()
        mock_subprocess_success.kill.assert_called_once()
        assert mock_subprocess_success.wait.call_count == 2
        assert client._process is None
    
    def test_is_connected_when_not_connected(self, client: MCPClient) -> None:
        """Test is_connected when client is not connected."""
        assert client.is_connected() is False
    
    def test_is_connected_when_connected(self, client: MCPClient,
                                       mock_subprocess_success: Mock) -> None:
        """Test is_connected when client is connected."""
        client._connected = True
        client._process = mock_subprocess_success
        
        assert client.is_connected() is True
    
    def test_is_connected_process_terminated(self, client: MCPClient,
                                           mock_subprocess_success: Mock) -> None:
        """Test is_connected when process has terminated."""
        client._connected = True
        client._process = mock_subprocess_success
        mock_subprocess_success.poll.return_value = 1  # Process terminated
        
        result = client.is_connected()
        
        assert result is False
        assert client._connected is False
    
    def test_generate_request_id(self, client: MCPClient) -> None:
        """Test request ID generation."""
        id1 = client._generate_request_id()
        id2 = client._generate_request_id()
        
        assert id1 != id2
        assert id1.startswith("req_")
        assert id2.startswith("req_")
        assert "_" in id1
        assert "_" in id2
    
    @patch('select.select')
    def test_read_response_with_timeout_success(self, mock_select: Mock, client: MCPClient,
                                              mock_subprocess_success: Mock) -> None:
        """Test successful response reading with timeout."""
        client._process = mock_subprocess_success
        mock_select.return_value = ([mock_subprocess_success.stdout], [], [])
        mock_subprocess_success.stdout.readline.return_value = "test response\n"
        
        response = client._read_response_with_timeout()
        
        assert response == "test response\n"
        mock_select.assert_called_once_with([mock_subprocess_success.stdout], [], [], 10)
    
    @patch('select.select')
    def test_read_response_with_timeout_timeout(self, mock_select: Mock, client: MCPClient,
                                              mock_subprocess_success: Mock) -> None:
        """Test response reading timeout."""
        client._process = mock_subprocess_success
        mock_select.return_value = ([], [], [])  # No ready streams
        
        with pytest.raises(MCPTimeoutError) as exc_info:
            client._read_response_with_timeout()
        
        assert "MCP request timed out after 10 seconds" in str(exc_info.value)
    
    def test_send_raw_request_not_connected(self, client: MCPClient) -> None:
        """Test sending request when not connected."""
        request = MCPRequest(method="test", params={})
        
        with pytest.raises(MCPConnectionError) as exc_info:
            client._send_raw_request(request)
        
        assert "MCP client not connected" in str(exc_info.value)
    
    @patch.object(MCPClient, '_read_response_with_timeout')
    def test_send_raw_request_success(self, mock_read: Mock, client: MCPClient,
                                    mock_subprocess_success: Mock) -> None:
        """Test successful raw request sending."""
        client._process = mock_subprocess_success
        
        response_data = {
            "jsonrpc": "2.0",
            "result": {"success": True},
            "id": "req_1"
        }
        mock_read.return_value = json.dumps(response_data) + "\n"
        
        request = MCPRequest(method="test", params={"key": "value"})
        response = client._send_raw_request(request)
        
        assert response.is_success() is True
        assert response.result == {"success": True}
        
        # Verify request was written to stdin
        expected_request = json.dumps(request.to_dict()) + "\n"
        mock_subprocess_success.stdin.write.assert_called_once_with(expected_request)
        mock_subprocess_success.stdin.flush.assert_called_once()
    
    @patch.object(MCPClient, '_read_response_with_timeout')
    def test_send_raw_request_json_decode_error(self, mock_read: Mock, client: MCPClient,
                                              mock_subprocess_success: Mock) -> None:
        """Test raw request with JSON decode error."""
        client._process = mock_subprocess_success
        mock_read.return_value = "invalid json response"
        
        request = MCPRequest(method="test", params={})
        
        with pytest.raises(MCPError) as exc_info:
            client._send_raw_request(request)
        
        assert "Invalid JSON response from MCP server" in str(exc_info.value)
    
    @patch.object(MCPClient, '_read_response_with_timeout')
    def test_send_raw_request_no_response(self, mock_read: Mock, client: MCPClient,
                                        mock_subprocess_success: Mock) -> None:
        """Test raw request with no response."""
        client._process = mock_subprocess_success
        mock_read.return_value = ""
        
        request = MCPRequest(method="test", params={})
        
        with pytest.raises(MCPError) as exc_info:
            client._send_raw_request(request)
        
        assert "No response received from MCP server" in str(exc_info.value)
    
    @patch.object(MCPClient, 'is_connected')
    @patch.object(MCPClient, '_send_raw_request')
    def test_send_request_success(self, mock_send_raw: Mock, mock_is_connected: Mock,
                                client: MCPClient) -> None:
        """Test successful generic request sending."""
        mock_is_connected.return_value = True
        mock_response = MCPResponse(result={"tickets": []}, id="req_1")
        mock_send_raw.return_value = mock_response
        
        result = client.send_request("search_tickets", {"status": "Open"})
        
        assert result == {"tickets": []}
        mock_send_raw.assert_called_once()
    
    @patch.object(MCPClient, 'is_connected')
    def test_send_request_not_connected(self, mock_is_connected: Mock, client: MCPClient) -> None:
        """Test sending request when not connected."""
        mock_is_connected.return_value = False
        
        with pytest.raises(MCPConnectionError) as exc_info:
            client.send_request("test", {})
        
        assert "MCP client not connected" in str(exc_info.value)
    
    @patch.object(MCPClient, 'is_connected')
    @patch.object(MCPClient, '_send_raw_request')
    def test_send_request_authentication_error(self, mock_send_raw: Mock, mock_is_connected: Mock,
                                             client: MCPClient) -> None:
        """Test request with authentication error."""
        mock_is_connected.return_value = True
        mock_response = MCPResponse(
            error={"code": -32001, "message": "Authentication failed"},
            id="req_1"
        )
        mock_send_raw.return_value = mock_response
        
        with pytest.raises(MCPAuthenticationError) as exc_info:
            client.send_request("test", {})
        
        assert "MCP authentication failed" in str(exc_info.value)
    
    @patch.object(MCPClient, 'is_connected')
    @patch.object(MCPClient, '_send_raw_request')
    def test_send_request_generic_error(self, mock_send_raw: Mock, mock_is_connected: Mock,
                                      client: MCPClient) -> None:
        """Test request with generic error."""
        mock_is_connected.return_value = True
        mock_response = MCPResponse(
            error={"code": -32000, "message": "Internal error"},
            id="req_1"
        )
        mock_send_raw.return_value = mock_response
        
        with pytest.raises(MCPError) as exc_info:
            client.send_request("test", {})
        
        assert "MCP request failed: Internal error" in str(exc_info.value)    @
patch.object(MCPClient, 'send_request')
    def test_search_tickets_success(self, mock_send_request: Mock, client: MCPClient) -> None:
        """Test successful ticket search."""
        mock_send_request.return_value = {
            "tickets": [
                {"id": "T123456", "title": "Test ticket 1"},
                {"id": "T123457", "title": "Test ticket 2"}
            ]
        }
        
        query = {"status": ["Open"], "assignee": "testuser"}
        tickets = client.search_tickets(query)
        
        assert len(tickets) == 2
        assert tickets[0]["id"] == "T123456"
        assert tickets[1]["id"] == "T123457"
        
        mock_send_request.assert_called_once_with(
            "mcp_builder_mcp_TicketingReadActions",
            {
                "action": "search-tickets",
                "input": query
            }
        )
    
    @patch.object(MCPClient, 'send_request')
    def test_search_tickets_empty_result(self, mock_send_request: Mock, client: MCPClient) -> None:
        """Test ticket search with empty result."""
        mock_send_request.return_value = {}  # No tickets field
        
        query = {"status": ["Nonexistent"]}
        tickets = client.search_tickets(query)
        
        assert tickets == []
    
    @patch.object(MCPClient, 'send_request')
    def test_search_tickets_mcp_error(self, mock_send_request: Mock, client: MCPClient) -> None:
        """Test ticket search with MCP error."""
        mock_send_request.side_effect = MCPError("Search failed")
        
        query = {"status": ["Open"]}
        
        with pytest.raises(MCPError):
            client.search_tickets(query)
    
    @patch.object(MCPClient, 'send_request')
    def test_get_ticket_success(self, mock_send_request: Mock, client: MCPClient) -> None:
        """Test successful ticket retrieval."""
        mock_send_request.return_value = {
            "ticket": {"id": "T123456", "title": "Test ticket"}
        }
        
        ticket = client.get_ticket("T123456")
        
        assert ticket is not None
        assert ticket["id"] == "T123456"
        assert ticket["title"] == "Test ticket"
        
        mock_send_request.assert_called_once_with(
            "mcp_builder_mcp_TicketingReadActions",
            {
                "action": "get-ticket",
                "input": {"ticketId": "T123456"}
            }
        )
    
    @patch.object(MCPClient, 'send_request')
    def test_get_ticket_not_found(self, mock_send_request: Mock, client: MCPClient) -> None:
        """Test ticket retrieval when ticket not found."""
        mock_send_request.return_value = {}  # No ticket field
        
        ticket = client.get_ticket("NONEXISTENT")
        
        assert ticket is None
    
    @patch.object(MCPClient, 'send_request')
    def test_get_ticket_mcp_error(self, mock_send_request: Mock, client: MCPClient) -> None:
        """Test ticket retrieval with MCP error."""
        mock_send_request.side_effect = MCPError("Retrieval failed")
        
        with pytest.raises(MCPError):
            client.get_ticket("T123456")
    
    @patch.object(MCPClient, 'is_connected')
    @patch.object(MCPClient, 'send_request')
    def test_get_server_info_success(self, mock_send_request: Mock, mock_is_connected: Mock,
                                   client: MCPClient) -> None:
        """Test successful server info retrieval."""
        mock_is_connected.return_value = True
        mock_send_request.return_value = {
            "name": "MCP Server",
            "version": "1.0.0",
            "capabilities": ["search", "retrieve"]
        }
        
        info = client.get_server_info()
        
        assert info["name"] == "MCP Server"
        assert info["version"] == "1.0.0"
        assert "capabilities" in info
    
    @patch.object(MCPClient, 'is_connected')
    def test_get_server_info_not_connected(self, mock_is_connected: Mock, client: MCPClient) -> None:
        """Test server info retrieval when not connected."""
        mock_is_connected.return_value = False
        
        with pytest.raises(MCPConnectionError) as exc_info:
            client.get_server_info()
        
        assert "MCP client not connected" in str(exc_info.value)
    
    @patch.object(MCPClient, 'validate_node_version')
    @patch.object(MCPClient, 'is_connected')
    @patch.object(MCPClient, 'send_request')
    @patch('subprocess.run')
    def test_health_check_success(self, mock_run: Mock, mock_send_request: Mock,
                                mock_is_connected: Mock, mock_validate: Mock,
                                client: MCPClient) -> None:
        """Test successful health check."""
        # Mock Node.js version check
        mock_validate.return_value = True
        mock_result = Mock()
        mock_result.stdout = "v18.17.0\n"
        mock_run.return_value = mock_result
        
        # Mock connection status
        mock_is_connected.return_value = True
        
        # Mock ping response
        mock_send_request.return_value = {"pong": True}
        
        health_info = client.health_check()
        
        assert health_info["connected"] is True
        assert health_info["node_version"] == "v18.17.0"
        assert health_info["server_responsive"] is True
        assert "response_time_ms" in health_info
        assert health_info["error_message"] is None
    
    @patch.object(MCPClient, 'validate_node_version')
    def test_health_check_node_validation_failure(self, mock_validate: Mock,
                                                client: MCPClient) -> None:
        """Test health check with Node.js validation failure."""
        mock_validate.side_effect = NodeCompatibilityError("Node.js too old")
        
        health_info = client.health_check()
        
        assert health_info["connected"] is False
        assert health_info["node_version"] is None
        assert health_info["server_responsive"] is False
        assert "Node.js too old" in health_info["error_message"]
    
    @patch.object(MCPClient, 'connect')
    @patch.object(MCPClient, 'disconnect')
    def test_context_manager_success(self, mock_disconnect: Mock, mock_connect: Mock,
                                   client: MCPClient) -> None:
        """Test client as context manager with success."""
        with client as c:
            assert c == client
        
        mock_connect.assert_called_once()
        mock_disconnect.assert_called_once()
    
    @patch.object(MCPClient, 'connect')
    @patch.object(MCPClient, 'disconnect')
    def test_context_manager_with_exception(self, mock_disconnect: Mock, mock_connect: Mock,
                                          client: MCPClient) -> None:
        """Test client as context manager with exception."""
        try:
            with client as c:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        mock_connect.assert_called_once()
        mock_disconnect.assert_called_once()


class TestMCPRequestFormatter:
    """Test cases for MCPRequestFormatter class."""
    
    @pytest.fixture
    def formatter(self) -> MCPRequestFormatter:
        """Provide MCPRequestFormatter instance for testing."""
        return MCPRequestFormatter()
    
    def test_format_search_request_basic(self, formatter: MCPRequestFormatter) -> None:
        """Test basic search request formatting."""
        criteria = SearchCriteria(
            status_filters=["Open", "Resolved"],
            assignee="testuser",
            max_results=100
        )
        
        request_params = formatter.format_search_request(criteria)
        
        assert request_params["status"] == ["Open", "Resolved"]
        assert request_params["assignee"] == "testuser"
        assert request_params["rows"] == 100
    
    def test_format_search_request_with_dates(self, formatter: MCPRequestFormatter) -> None:
        """Test search request formatting with date range."""
        from datetime import datetime
        
        criteria = SearchCriteria(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            max_results=50
        )
        
        request_params = formatter.format_search_request(criteria)
        
        expected_date_filter = "[2024-01-01T00:00:00Z TO 2024-01-31T00:00:00Z]"
        assert request_params["createDate"] == expected_date_filter
        assert request_params["rows"] == 50
    
    def test_format_search_request_with_text_search(self, formatter: MCPRequestFormatter) -> None:
        """Test search request formatting with text search."""
        criteria = SearchCriteria(
            search_text="authentication error",
            lucene_query="status:Open AND assignee:testuser"
        )
        
        request_params = formatter.format_search_request(criteria)
        
        assert request_params["fullText"] == "authentication error"
        assert request_params["query"] == "status:Open AND assignee:testuser"
    
    def test_format_search_request_with_pagination(self, formatter: MCPRequestFormatter) -> None:
        """Test search request formatting with pagination."""
        criteria = SearchCriteria(
            max_results=25,
            offset=50
        )
        
        request_params = formatter.format_search_request(criteria)
        
        assert request_params["rows"] == 25
        assert request_params["start"] == 50
    
    def test_format_ticket_request(self, formatter: MCPRequestFormatter) -> None:
        """Test ticket request formatting."""
        request_params = formatter.format_ticket_request("T123456")
        
        assert request_params == {"ticketId": "T123456"}
    
    def test_parse_response_ticket_list(self, formatter: MCPRequestFormatter) -> None:
        """Test parsing response with ticket list."""
        response = {
            "tickets": [
                {"id": "T123456", "title": "Ticket 1"},
                {"id": "T123457", "title": "Ticket 2"}
            ]
        }
        
        parsed = formatter.parse_response(response)
        
        assert len(parsed) == 2
        assert parsed[0]["id"] == "T123456"
        assert parsed[1]["id"] == "T123457"
    
    def test_parse_response_single_ticket(self, formatter: MCPRequestFormatter) -> None:
        """Test parsing response with single ticket."""
        response = {
            "ticket": {"id": "T123456", "title": "Single ticket"}
        }
        
        parsed = formatter.parse_response(response)
        
        assert len(parsed) == 1
        assert parsed[0]["id"] == "T123456"
    
    def test_parse_response_results_field(self, formatter: MCPRequestFormatter) -> None:
        """Test parsing response with results field."""
        response = {
            "results": [
                {"id": "T123456", "title": "Result 1"}
            ]
        }
        
        parsed = formatter.parse_response(response)
        
        assert len(parsed) == 1
        assert parsed[0]["id"] == "T123456"
    
    def test_parse_response_empty(self, formatter: MCPRequestFormatter) -> None:
        """Test parsing empty response."""
        response = {"status": "success"}  # No tickets, ticket, or results
        
        parsed = formatter.parse_response(response)
        
        assert parsed == []


class TestMCPClientIntegration:
    """Integration tests for MCPClient with multiple components."""
    
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_full_connection_and_search_flow(self, mock_run: Mock, mock_popen: Mock) -> None:
        """Test complete connection and search flow."""
        # Mock Node.js version check
        mock_version_result = Mock()
        mock_version_result.returncode = 0
        mock_version_result.stdout = "v18.17.0\n"
        mock_run.return_value = mock_version_result
        
        # Mock MCP server process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process
        
        # Mock responses
        init_response = {
            "jsonrpc": "2.0",
            "result": {"capabilities": {}},
            "id": "req_1"
        }
        
        search_response = {
            "jsonrpc": "2.0",
            "result": {
                "tickets": [
                    {"id": "T123456", "title": "Integration test ticket"}
                ]
            },
            "id": "req_2"
        }
        
        mock_process.stdout.readline.side_effect = [
            json.dumps(init_response) + "\n",
            json.dumps(search_response) + "\n"
        ]
        
        # Test the flow
        client = MCPClient(timeout=5)
        
        with client:
            tickets = client.search_tickets({"status": ["Open"]})
        
        assert len(tickets) == 1
        assert tickets[0]["id"] == "T123456"
        
        # Verify calls
        assert mock_process.stdin.write.call_count == 2  # Init + search
        mock_process.terminate.assert_called_once()
    
    def test_error_propagation_and_recovery(self) -> None:
        """Test error propagation and recovery mechanisms."""
        client = MCPClient()
        
        # Test that connection errors are properly wrapped
        with pytest.raises(NodeCompatibilityError):
            # This should fail because Node.js validation will fail in test environment
            client.validate_node_version()
        
        # Test that client remains in consistent state after errors
        assert client._connected is False
        assert client._process is None
    
    @patch.object(MCPClient, 'validate_node_version')
    def test_initialization_with_node_validation_failure(self, mock_validate: Mock) -> None:
        """Test client initialization with Node.js validation failure."""
        mock_validate.side_effect = NodeCompatibilityError("Node.js not found")
        
        # Should raise error during initialization if validation is called
        with pytest.raises(NodeCompatibilityError):
            client = MCPClient()
            client.validate_node_version()  # Explicit call for testing