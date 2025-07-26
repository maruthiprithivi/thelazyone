"""
End-to-End Integration Tests for MCP Tools

Tests complete workflows for all MCP tools with real dependencies.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.mcp_server.server import MCPServer
from src.mcp_server.config import ServerConfig


class TestToolIntegration:
    """Integration tests for MCP tools."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    async def server(self, temp_dir):
        """Create and start test server with real components."""
        config = ServerConfig()
        config.debug = True
        config.state_settings.state_directory = str(temp_dir / "state")
        config.journal_settings.journal_path = str(temp_dir / "journal.md")
        config.spec_directory = str(temp_dir / "specs")
        
        # Mock LLM providers for testing
        from src.mcp_server.config import ModelConfig, LLMProvider
        config.llm_providers = [
            ModelConfig(
                provider=LLMProvider.OPENAI,
                api_key="test-key",
                model_name="gpt-4"
            )
        ]
        
        server = MCPServer(config)
        
        # Mock external dependencies
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_openai:
            mock_provider = AsyncMock()
            mock_provider.generate_code.return_value = "def test_function():\n    return 'Hello MCP'"
            mock_provider.analyze_code.return_value = "Code analysis complete"
            mock_openai.return_value = mock_provider
            
            await server.start()
            yield server
            await server.stop()
    
    @pytest.fixture
    def mcp_client(self, server):
        """Integration test client."""
        return IntegrationTestClient(server)
    
    @pytest.mark.asyncio
    async def test_code_generation_workflow(self, mcp_client):
        """Test complete code generation workflow."""
        result = await mcp_client.call_tool("generate_code", {
            "prompt": "Create a simple Python function that returns 'Hello MCP'",
            "language": "python"
        })
        
        assert "def test_function" in result.content[0]["text"]
        assert "Hello MCP" in result.content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_debug_code_workflow(self, mcp_client):
        """Test code debugging workflow."""
        result = await mcp_client.call_tool("debug_code", {
            "code": "def divide(a, b):\n    return a / b",
            "error": "ZeroDivisionError: division by zero",
            "language": "python"
        })
        
        assert "fix" in result.content[0]["text"].lower()
        assert "ZeroDivisionError" in result.content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_research_documentation_workflow(self, mcp_client):
        """Test research documentation workflow."""
        with patch('src.mcp_server.research.engine.ResearchEngine.research') as mock_research:
            mock_research.return_value = [
                {
                    "title": "Python async best practices",
                    "content": "Use asyncio for concurrent operations...",
                    "source": "example.com"
                }
            ]
            
            result = await mcp_client.call_tool("research_documentation", {
                "query": "Python async programming best practices",
                "query_type": "technical",
                "max_results": 5
            })
            
            assert "async" in result.content[0]["text"]
            assert "best practices" in result.content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_session_management_workflow(self, mcp_client):
        """Test session management lifecycle."""
        # Create session
        create_result = await mcp_client.call_tool("manage_session", {
            "action": "create",
            "context": {"test": "integration"}
        })
        
        session_id = create_result.content[0]["text"]
        assert "session" in session_id.lower()
        
        # List sessions
        list_result = await mcp_client.call_tool("manage_session", {
            "action": "list"
        })
        
        assert session_id in list_result.content[0]["text"]
        
        # Close session
        close_result = await mcp_client.call_tool("manage_session", {
            "action": "close",
            "session_id": session_id
        })
        
        assert "closed" in close_result.content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_spec_generation_workflow(self, mcp_client):
        """Test specification generation workflow."""
        # Create requirements spec
        req_result = await mcp_client.call_tool("create_requirements_spec", {
            "title": "Test API",
            "description": "A simple REST API for testing",
            "requirements": [
                {
                    "id": "REQ-001",
                    "description": "API must respond within 1 second",
                    "priority": "high"
                }
            ]
        })
        
        assert "Test API" in req_result.content[0]["text"]
        assert "REQ-001" in req_result.content[0]["text"]
        
        # Create design spec from requirements
        design_result = await mcp_client.call_tool("create_design_spec", {
            "title": "Test API Design",
            "requirements": ["REQ-001"],
            "technology_stack": ["FastAPI", "Python"]
        })
        
        assert "FastAPI" in design_result.content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_state_persistence_workflow(self, mcp_client, temp_dir):
        """Test state persistence and recovery."""
        # Create session with state
        session_result = await mcp_client.call_tool("manage_session", {
            "action": "create",
            "context": {"project": "persistence-test"}
        })
        
        session_id = session_result.content[0]["text"]
        
        # Verify state file exists
        state_files = list(Path(temp_dir / "state").glob("*.json"))
        assert len(state_files) > 0
        
        # Test recovery (simulate restart)
        recovery_result = await mcp_client.call_tool("manage_session", {
            "action": "recover",
            "session_id": session_id
        })
        
        assert "recovered" in recovery_result.content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_complete_developer_workflow(self, mcp_client):
        """Test complete developer workflow."""
        # 1. Create new project session
        session = await mcp_client.call_tool("manage_session", {
            "action": "create",
            "context": {"project": "todo-api", "type": "new-project"}
        })
        session_id = session.content[0]["text"]
        
        # 2. Generate requirements
        specs = await mcp_client.call_tool("create_requirements_spec", {
            "title": "Todo REST API",
            "description": "A RESTful API for managing todo items",
            "requirements": [
                {"id": "REQ-001", "description": "CRUD operations for todos", "priority": "high"},
                {"id": "REQ-002", "description": "Response time < 1s", "priority": "medium"}
            ]
        })
        
        # 3. Generate design
        design = await mcp_client.call_tool("create_design_spec", {
            "title": "Todo API Design",
            "requirements": ["REQ-001", "REQ-002"],
            "technology_stack": ["FastAPI", "PostgreSQL"]
        })
        
        # 4. Generate code
        code = await mcp_client.call_tool("generate_code", {
            "prompt": "Create FastAPI todo API with CRUD endpoints",
            "language": "python",
            "framework": "fastapi"
        })
        
        # 5. Test the code
        test_result = await mcp_client.call_tool("execute_tests", {
            "code": code.content[0]["text"],
            "test_framework": "pytest"
        })
        
        # 6. Debug if needed
        if "failed" in test_result.content[0]["text"].lower():
            debug = await mcp_client.call_tool("debug_code", {
                "code": code.content[0]["text"],
                "error": "test failures"
            })
            assert "fix" in debug.content[0]["text"].lower()
        
        # 7. Research documentation
        docs = await mcp_client.call_tool("research_documentation", {
            "query": "FastAPI deployment best practices",
            "query_type": "technical"
        })
        
        # 8. Cleanup
        cleanup = await mcp_client.call_tool("manage_session", {
            "action": "close",
            "session_id": session_id
        })
        
        assert "closed" in cleanup.content[0]["text"]


class IntegrationTestClient:
    """Integration test client for MCP server."""
    
    def __init__(self, server: MCPServer):
        self.server = server
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call MCP tool and return result."""
        request = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return await self.server.handle_request(request)