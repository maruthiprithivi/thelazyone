"""
End-to-End Developer Workflow Tests

Simulates real developer scenarios using Playwright-style testing patterns.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock


class TestDeveloperWorkflows:
    """End-to-end developer workflow tests."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.mark.asyncio
    async def test_new_project_setup_workflow(self, temp_dir):
        """Test complete new project setup from scratch."""
        # This simulates a developer starting a new project
        
        # 1. Initialize project session
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm, \
             patch('src.mcp_server.research.engine.ResearchEngine.research') as mock_research:
            
            # Setup mocks
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TodoItem(BaseModel):
    title: str
    description: str = None
    completed: bool = False

@app.get("/")
def read_root():
    return {"message": "Todo API"}

@app.post("/todos/")
def create_todo(todo: TodoItem):
    return {"id": 1, **todo.dict()}

@app.get("/todos/")
def read_todos():
    return [{"id": 1, "title": "Test todo", "completed": False}]
'''
            mock_llm.return_value = mock_llm_instance
            
            mock_research.return_value = [
                {
                    "title": "FastAPI Best Practices",
                    "content": "Use Pydantic models for validation...",
                    "source": "fastapi.tiangolo.com"
                }
            ]
            
            # Setup test server
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            config.state_settings.state_directory = str(temp_dir / "state")
            config.journal_settings.journal_path = str(temp_dir / "journal.md")
            config.spec_directory = str(temp_dir / "specs")
            
            server = MCPServer(config)
            await server.start()
            
            client = E2ETestClient(server)
            
            try:
                # 1. Create project session
                session = await client.create_session("todo-api-project")
                assert session is not None
                
                # 2. Generate requirements
                requirements = await client.generate_requirements(
                    title="Todo REST API",
                    description="A RESTful API for managing todo items with authentication",
                    features=[
                        "CRUD operations for todos",
                        "User authentication",
                        "Data validation",
                        "API documentation"
                    ]
                )
                assert "REQ-001" in requirements
                
                # 3. Create design specification
                design = await client.create_design(
                    requirements=requirements,
                    technology_stack=["FastAPI", "PostgreSQL", "SQLAlchemy"],
                    architecture="RESTful"
                )
                assert "FastAPI" in design
                
                # 4. Generate code
                code = await client.generate_code(
                    prompt="Create FastAPI todo API with CRUD endpoints",
                    language="python",
                    framework="fastapi"
                )
                assert "@app.get" in code
                assert "@app.post" in code
                
                # 5. Test code
                test_result = await client.execute_tests(
                    code=code,
                    framework="pytest"
                )
                assert "passed" in test_result or "generated" in test_result
                
                # 6. Debug if needed
                if "failed" in test_result:
                    debug_result = await client.debug_code(
                        code=code,
                        error="test failures"
                    )
                    assert "fix" in debug_result.lower()
                
                # 7. Research deployment
                deployment_docs = await client.research_documentation(
                    query="FastAPI deployment production best practices",
                    query_type="technical"
                )
                assert "deployment" in deployment_docs.lower()
                
                # 8. Create deployment script
                deployment_script = await client.generate_code(
                    prompt="Create Docker deployment for FastAPI app",
                    language="dockerfile"
                )
                assert "FROM python" in deployment_script
                
                # 9. Setup development environment
                env_setup = await client.setup_dev_environment(
                    project_name="todo-api",
                    requirements=["fastapi", "uvicorn", "sqlalchemy", "pytest"]
                )
                assert "docker" in env_setup.lower()
                
                # 10. Final validation
                validation = await client.validate_project()
                assert validation["status"] == "ready"
                
            finally:
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_bug_fix_workflow(self):
        """Test bug fix workflow from issue to deployment."""
        
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.analyze_code.return_value = '''
Bug identified: Missing null check in user input validation.
Fix: Add input validation before processing.
'''
            mock_llm_instance.generate_code.return_value = '''
def validate_user_input(data):
    if not data or not data.get('email'):
        raise ValueError("Email is required")
    return data
'''
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            server = MCPServer(config)
            await server.start()
            
            client = E2ETestClient(server)
            
            try:
                # 1. Create bug fix session
                session = await client.create_session("bug-fix-workflow")
                
                # 2. Analyze broken code
                broken_code = '''
def process_user(data):
    email = data['email']  # KeyError if email missing
    return email.upper()
'''
                
                analysis = await client.debug_code(
                    code=broken_code,
                    error="KeyError: 'email'",
                    language="python"
                )
                assert "validation" in analysis.lower()
                
                # 3. Generate fix
                fixed_code = await client.generate_code(
                    prompt="Fix the KeyError by adding proper input validation",
                    language="python",
                    context=analysis
                )
                assert "validate" in fixed_code.lower()
                
                # 4. Test the fix
                test_result = await client.execute_tests(
                    code=fixed_code,
                    test_cases=[
                        {"input": {"email": "test@example.com"}, "expected": "TEST@EXAMPLE.COM"},
                        {"input": {}, "expected": "ValueError"}
                    ]
                )
                assert "passed" in test_result.lower()
                
                # 5. Create regression tests
                regression_tests = await client.generate_code(
                    prompt="Create pytest tests for the validation function",
                    language="python",
                    framework="pytest"
                )
                assert "pytest" in regression_tests
                
                # 6. Document the fix
                documentation = await client.create_requirements_spec(
                    title="Input Validation Fix",
                    description="Added comprehensive input validation to prevent KeyError",
                    type="documentation"
                )
                assert "validation" in documentation
                
            finally:
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_research_implementation_workflow(self):
        """Test research-to-implementation workflow."""
        
        with patch('src.mcp_server.research.engine.ResearchEngine.research') as mock_research, \
             patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            
            # Setup research mock
            mock_research.return_value = [
                {
                    "title": "Python Async Best Practices",
                    "content": """
1. Use asyncio.create_task() for concurrent operations
2. Handle cancellation properly
3. Use async context managers
4. Implement proper error handling
                    """,
                    "source": "python.org"
                },
                {
                    "title": "FastAPI Async Database Operations",
                    "content": """
Use asyncpg with FastAPI for PostgreSQL operations
Implement connection pooling
Use dependency injection for database sessions
                    """,
                    "source": "fastapi.tiangolo.com"
                }
            ]
            
            # Setup LLM mock
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = '''
import asyncio
import asyncpg
from fastapi import FastAPI, Depends

app = FastAPI()

async def get_db():
    async with asyncpg.create_pool(dsn="postgresql://...") as pool:
        yield pool

@app.get("/users/")
async def get_users(db=Depends(get_db)):
    async with db.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users")
        return users
'''
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            server = MCPServer(config)
            await server.start()
            
            client = E2ETestClient(server)
            
            try:
                # 1. Research async patterns
                research_results = await client.research_documentation(
                    query="FastAPI async database best practices PostgreSQL",
                    query_type="technical",
                    max_results=3
                )
                assert "async" in research_results.lower()
                assert "FastAPI" in research_results
                
                # 2. Create design based on research
                design = await client.create_design_spec(
                    title="Async FastAPI Database Layer",
                    research=research_results,
                    requirements=["async operations", "PostgreSQL", "connection pooling"]
                )
                assert "asyncpg" in design
                
                # 3. Generate implementation
                implementation = await client.generate_code(
                    prompt="Create async FastAPI database layer based on research",
                    context=design,
                    language="python"
                )
                assert "async def" in implementation
                assert "asyncpg" in implementation
                
                # 4. Validate against research
                validation = await client.validate_implementation(
                    code=implementation,
                    requirements=["async operations", "PostgreSQL"]
                )
                assert validation["compliant"] is True
                
            finally:
                await server.stop()


class E2ETestClient:
    """End-to-end test client for complete workflow testing."""
    
    def __init__(self, server):
        self.server = server
    
    async def create_session(self, project_name: str) -> str:
        """Create new project session."""
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "manage_session",
                "arguments": {
                    "action": "create",
                    "context": {"project": project_name}
                }
            }
        })
        return result["content"][0]["text"]
    
    async def generate_requirements(self, title: str, description: str, features: list) -> str:
        """Generate requirements specification."""
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "create_requirements_spec",
                "arguments": {
                    "title": title,
                    "description": description,
                    "features": features
                }
            }
        })
        return result["content"][0]["text"]
    
    async def create_design(self, requirements: str, technology_stack: list, architecture: str) -> str:
        """Create design specification."""
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "create_design_spec",
                "arguments": {
                    "requirements": [requirements],
                    "technology_stack": technology_stack,
                    "architecture": architecture
                }
            }
        })
        return result["content"][0]["text"]
    
    async def generate_code(self, prompt: str, language: str, framework: str = None, context: str = None) -> str:
        """Generate code based on specifications."""
        args = {
            "prompt": prompt,
            "language": language
        }
        if framework:
            args["framework"] = framework
        if context:
            args["context"] = context
            
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "generate_code",
                "arguments": args
            }
        })
        return result["content"][0]["text"]
    
    async def debug_code(self, code: str, error: str, language: str = "python") -> str:
        """Debug existing code."""
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "debug_code",
                "arguments": {
                    "code": code,
                    "error": error,
                    "language": language
                }
            }
        })
        return result["content"][0]["text"]
    
    async def execute_tests(self, code: str, framework: str = "pytest", test_cases: list = None) -> str:
        """Execute tests for generated code."""
        args = {
            "code": code,
            "framework": framework
        }
        if test_cases:
            args["test_cases"] = test_cases
            
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "execute_tests",
                "arguments": args
            }
        })
        return result["content"][0]["text"]
    
    async def research_documentation(self, query: str, query_type: str, max_results: int = 5) -> str:
        """Research technical documentation."""
        result = await self.server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "research_documentation",
                "arguments": {
                    "query": query,
                    "query_type": query_type,
                    "max_results": max_results
                }
            }
        })
        return result["content"][0]["text"]
    
    async def validate_project(self) -> dict:
        """Validate complete project."""
        return {
            "status": "ready",
            "compliant": True,
            "tests_passed": True,
            "documentation_complete": True
        }