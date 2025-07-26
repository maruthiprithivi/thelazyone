"""
Pytest configuration and fixtures for MCP server testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from src.mcp_server.config import ServerConfig
from src.mcp_server.server import MCPServer


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration."""
    config = ServerConfig()
    config.state_settings.state_directory = str(temp_dir / "state")
    config.journal_settings.journal_path = str(temp_dir / "journal.md")
    config.spec_directory = str(temp_dir / "specs")
    config.debug = True
    
    # Add mock LLM providers for testing
    from src.mcp_server.config import ModelConfig, LLMProvider
    config.llm_providers = [
        ModelConfig(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            model_name="gpt-4"
        )
    ]
    return config


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "choices": [{
            "message": {
                "content": "# Test Response\n\nThis is a test response from the LLM."
            }
        }]
    }


@pytest.fixture
def sample_mcp_request():
    """Sample MCP request for testing."""
    return {
        "method": "tools/call",
        "params": {
            "name": "generate_code",
            "arguments": {
                "prompt": "Create a simple Python function",
                "language": "python"
            }
        }
    }


@pytest.fixture
def sample_mcp_list_request():
    """Sample MCP list tools request."""
    return {
        "method": "tools/list",
        "params": {}
    }


@pytest.fixture
def sample_mcp_initialize_request():
    """Sample MCP initialize request."""
    return {
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }


@pytest.fixture
async def test_server(test_config):
    """Create test server instance."""
    server = MCPServer(test_config)
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def test_docker_config():
    """Test Docker configuration."""
    return {
        "base_image": "python:3.11-slim",
        "memory_limit": "256m",
        "cpu_limit": "0.5",
        "timeout": 60
    }


@pytest.fixture
def test_research_query():
    """Test research query."""
    return {
        "query": "Python async programming best practices",
        "query_type": "technical",
        "max_results": 5
    }


@pytest.fixture
def test_spec_data():
    """Test specification data."""
    return {
        "title": "Test API",
        "description": "A test API for validation",
        "requirements": [
            {
                "id": "REQ-001",
                "description": "The API must respond within 1 second",
                "priority": "high"
            }
        ]
    }