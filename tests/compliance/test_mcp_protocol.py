"""
MCP Protocol Compliance Tests

Tests MCP 2024-11-05 specification compliance for the Claude Code MCP Server.
Based on IBM certification framework standards.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from pathlib import Path

from src.mcp_server.server import MCPServer
from src.mcp_server.config import ServerConfig


class TestMCPProtocolCompliance:
    """Test suite for MCP protocol compliance."""
    
    @pytest.fixture
    async def server(self):
        """Create and start test server."""
        config = ServerConfig()
        config.debug = True
        config.llm_providers = []  # Mock providers for testing
        server = MCPServer(config)
        await server.start()
        yield server
        await server.stop()
    
    @pytest.fixture
    def mcp_client(self, server):
        """Mock MCP client for testing."""
        return MCPTestClient(server)
    
    async def test_initialize_handshake(self, mcp_client):
        """Test MCP initialize handshake."""
        request = {
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await mcp_client.send_request(request)
        
        assert response.get("protocolVersion") == "2024-11-05"
        assert "capabilities" in response
        assert "tools" in response["capabilities"]
        assert response["serverInfo"]["name"] == "claude-code-mcp-server"
    
    async def test_tool_discovery(self, mcp_client):
        """Test tool discovery endpoint."""
        request = {
            "method": "tools/list",
            "params": {}
        }
        
        response = await mcp_client.send_request(request)
        
        tools = response.get("tools", [])
        assert len(tools) >= 9  # All implemented tools
        
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "generate_code",
            "debug_code",
            "execute_tests",
            "research_documentation",
            "create_requirements_spec",
            "create_design_spec",
            "manage_session",
            "setup_dev_environment",
            "execute_command"
        ]
        
        for tool in expected_tools:
            assert tool in tool_names, f"Missing tool: {tool}"
    
    async def test_tool_call_schema(self, mcp_client):
        """Test tool call request/response schema."""
        request = {
            "method": "tools/call",
            "params": {
                "name": "generate_code",
                "arguments": {
                    "prompt": "Create a simple function",
                    "language": "python"
                }
            }
        }
        
        response = await mcp_client.send_request(request)
        
        assert "content" in response
        assert isinstance(response["content"], list)
        assert len(response["content"]) > 0
        assert "type" in response["content"][0]
        assert "text" in response["content"][0]
    
    async def test_error_handling(self, mcp_client):
        """Test error handling compliance."""
        # Test invalid method
        request = {
            "method": "invalid_method",
            "params": {}
        }
        
        response = await mcp_client.send_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found
        assert "message" in response["error"]
        
        # Test invalid tool
        request = {
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }
        
        response = await mcp_client.send_request(request)
        
        assert "content" in response  # Should return content, not error
    
    async def test_capability_advertisement(self, mcp_client):
        """Test capability advertisement."""
        request = {
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        }
        
        response = await mcp_client.send_request(request)
        
        assert "capabilities" in response
        capabilities = response["capabilities"]
        
        # Check required capabilities
        assert "tools" in capabilities
        assert capabilities["tools"] is not None
        
        # Check server info
        assert "serverInfo" in response
        server_info = response["serverInfo"]
        assert server_info["name"] == "claude-code-mcp-server"
        assert "version" in server_info
    
    async def test_notification_support(self, mcp_client):
        """Test notification handling."""
        # Test that notifications don't require responses
        request = {
            "method": "notifications/initialized",
            "params": {}
        }
        
        response = await mcp_client.send_request(request)
        
        # Notifications should not return responses
        assert response is None or response == {}


class MCPTestClient:
    """Mock MCP client for testing protocol compliance."""
    
    def __init__(self, server: MCPServer):
        self.server = server
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to MCP server."""
        return await self.server.handle_request(request)