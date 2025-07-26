"""
Main MCP Server Implementation

Core server class implementing the Model Context Protocol specification
for comprehensive coding assistance capabilities.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import traceback

from .config import ServerConfig, load_config
from .llm.router import LLMRouter
from .docker.controller import DockerController
from .research.engine import ResearchEngine
from .state.manager import StateManager
from .journal.manager import JournalManager
from .specs.manager import SpecManager


class MCPServer:
    """
    Main MCP Server class implementing the Model Context Protocol.
    
    Provides comprehensive coding assistance including code generation,
    debugging, testing, research, and spec-driven development workflows.
    """
    
    def __init__(self, config: Optional[ServerConfig] = None):
        """Initialize the MCP server with configuration."""
        self.config = config or load_config()
        self.logger = self._setup_logging()
        self._tools_registry: Dict[str, Any] = {}
        self._active_sessions: Dict[str, Any] = {}
        
        # Initialize core components
        self.llm_router = None
        self.docker_controller = None
        self.spec_manager = None
        self.research_engine = None
        self.journal_manager = None
        self.state_manager = None
        
        # MCP protocol support
        self.server_info = {
            "name": "mcp-server",
            "version": "1.0.0",
            "capabilities": {
                "tools": {},
                "prompts": {},
                "resources": {}
            }
        }
        
        self.logger.info("MCP Server initialized with configuration")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up structured logging for the server."""
        logger = logging.getLogger("mcp_server")
        logger.setLevel(getattr(logging, self.config.journal_settings.log_level))
        
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    async def start(self):
        """Start the MCP server and initialize all components."""
        self.logger.info("Starting MCP Server...")
        
        try:
            # Validate configuration
            self.config.validate()
            
            # Initialize components (placeholders for now)
            await self._initialize_components()
            
            # Register tools
            await self._register_tools()
            
            self.logger.info("MCP Server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP Server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server and cleanup resources."""
        self.logger.info("Stopping MCP Server...")
        
        try:
            # Cleanup components
            await self._cleanup_components()
            
            self.logger.info("MCP Server stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during server shutdown: {e}")
            raise
    
    async def _initialize_components(self):
        """Initialize all server components."""
        self.logger.info("Initializing server components...")
        
        try:
            # Initialize LLM Router
            self.llm_router = LLMRouter(
                self.config.llm_providers,
                default_provider=self.config.default_llm_provider.value if hasattr(self.config.default_llm_provider, 'value') else str(self.config.default_llm_provider)
            )
            await self.llm_router.initialize()
            
            # Initialize Docker Controller
            self.docker_controller = DockerController(self.config.docker_settings)
            await self.docker_controller.initialize()
            
            # Initialize Spec Manager
            self.spec_manager = SpecManager(self.config.spec_directory)
            
            # Initialize Research Engine
            self.research_engine = ResearchEngine(
                cache_ttl_minutes=self.config.research_settings.cache_ttl_minutes,
                rate_limit_max_calls=self.config.research_settings.rate_limit_max_calls,
                rate_limit_window_seconds=self.config.research_settings.rate_limit_window_seconds
            )
            
            # Initialize Journal Manager
            self.journal_manager = JournalManager(self.config.journal_settings)
            
            # Initialize State Manager
            self.state_manager = StateManager(
                state_dir=Path(self.config.state_settings.state_directory),
                auto_checkpoint_interval=self.config.state_settings.auto_checkpoint_interval,
                max_checkpoints_per_session=self.config.state_settings.max_checkpoints_per_session,
                cleanup_interval=self.config.state_settings.cleanup_interval
            )
            
            # Start state manager
            self.state_manager.start()
            
            self.logger.info("All server components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            await self._cleanup_components()
            raise
    
    async def _cleanup_components(self):
        """Cleanup all server components."""
        self.logger.info("Cleaning up server components...")
        
        try:
            if self.docker_controller:
                await self.docker_controller.cleanup()
            
            if self.state_manager:
                self.state_manager.stop()
            
            if self.llm_router:
                await self.llm_router.cleanup()
            
            if self.research_engine:
                self.research_engine.cleanup_expired_cache()
            
            self.logger.info("All server components cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during component cleanup: {e}")
    
    async def _register_tools(self):
        """Register all available MCP tools."""
        self.logger.info("Registering MCP tools...")
        
        # Register tools with MCP-compliant schemas
        tools = [
            {
                "name": "generate_code",
                "description": "Generate code based on requirements and context",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "string",
                            "description": "Detailed requirements for the code to generate"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language for the generated code",
                            "default": "python"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context or existing code"
                        },
                        "style_guide": {
                            "type": "string",
                            "description": "Coding style or conventions to follow"
                        }
                    },
                    "required": ["requirements"]
                }
            },
            {
                "name": "debug_code",
                "description": "Debug and fix issues in code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to debug"
                        },
                        "error_message": {
                            "type": "string",
                            "description": "Error message or description of the issue"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "default": "python"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about the issue"
                        }
                    },
                    "required": ["code", "error_message"]
                }
            },
            {
                "name": "execute_tests",
                "description": "Run tests in a controlled environment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project directory"
                        },
                        "test_command": {
                            "type": "string",
                            "description": "Specific test command to run",
                            "default": "pytest"
                        },
                        "environment": {
                            "type": "string",
                            "description": "Docker environment configuration"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds",
                            "default": 300
                        }
                    },
                    "required": ["project_path"]
                }
            },
            {
                "name": "research_documentation",
                "description": "Research technical documentation and best practices",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Research query or topic"
                        },
                        "query_type": {
                            "type": "string",
                            "enum": ["technical", "general", "troubleshooting", "best_practices"],
                            "description": "Type of research query",
                            "default": "technical"
                        },
                        "max_results": {
                            "type": "number",
                            "description": "Maximum number of results",
                            "default": 5
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context for the research"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_requirements_spec",
                "description": "Create a requirements specification document",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the requirements document"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of what needs to be built"
                        },
                        "project_context": {
                            "type": "object",
                            "description": "Additional context about the project"
                        },
                        "constraints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Technical or business constraints"
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Acceptance criteria for the requirements"
                        }
                    },
                    "required": ["title", "description"]
                }
            },
            {
                "name": "create_design_spec",
                "description": "Create a technical design specification",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the design document"
                        },
                        "requirements_id": {
                            "type": "string",
                            "description": "ID of requirements this design addresses"
                        },
                        "design_type": {
                            "type": "string",
                            "enum": ["technical", "system", "database", "api"],
                            "description": "Type of design document",
                            "default": "technical"
                        },
                        "components": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific components to design"
                        },
                        "architecture_style": {
                            "type": "string",
                            "description": "Architecture style to follow"
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "manage_session",
                "description": "Manage development sessions and state",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "update", "close", "checkpoint", "recover"],
                            "description": "Session management action"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session identifier"
                        },
                        "context": {
                            "type": "object",
                            "description": "Session context data"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Session metadata"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "setup_dev_environment",
                "description": "Set up a development environment with Docker",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project directory"
                        },
                        "requirements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Python package requirements"
                        },
                        "environment_vars": {
                            "type": "object",
                            "description": "Environment variables for the container"
                        }
                    },
                    "required": ["project_name", "project_path"]
                }
            },
            {
                "name": "execute_command",
                "description": "Execute commands in development environment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID or name"
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Command timeout in seconds",
                            "default": 300
                        }
                    },
                    "required": ["container_id", "command"]
                }
            }
        ]
        
        # Register tools
        for tool in tools:
            self._tools_registry[tool["name"]] = tool
        
        self.logger.info(f"Registered {len(tools)} MCP tools")
        
        # Update server capabilities
        self.server_info["capabilities"]["tools"] = {
            "listChanged": True
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP requests.
        
        Args:
            request: MCP request dictionary
            
        Returns:
            MCP response dictionary
        """
        self.logger.debug(f"Handling MCP request: {request.get('method', 'unknown')}")
        
        request_id = str(uuid.uuid4())
        session_id = request.get("session_id", "default")
        
        try:
            method = request.get("method")
            params = request.get("params", {})
            
            # Log request
            if self.journal_manager:
                self.journal_manager.log_operation(
                    operation="mcp_request",
                    session_id=session_id,
                    parameters={"method": method, "params": params},
                    metadata={"request_id": request_id}
                )
            
            # Handle different MCP methods
            if method == "initialize":
                return await self._handle_initialize(params)
            elif method == "tools/list":
                return await self._handle_list_tools()
            elif method == "tools/call":
                return await self._handle_tool_call(params, session_id)
            elif method == "ping":
                return {"pong": True}
            elif method == "capabilities":
                return await self._handle_capabilities()
            else:
                return {
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            if self.journal_manager:
                self.journal_manager.log_error(
                    error=e,
                    operation="mcp_request_error",
                    session_id=session_id,
                    context={"method": method, "request_id": request_id}
                )
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request for MCP protocol."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.server_info["capabilities"],
            "serverInfo": self.server_info
        }
    
    async def _handle_capabilities(self) -> Dict[str, Any]:
        """Handle capabilities request."""
        return {
            "capabilities": self.server_info["capabilities"]
        }
    
    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "tools": list(self._tools_registry.values())
        }
    
    async def _handle_tool_call(self, params: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        self.logger.info(f"Tool call: {tool_name}")
        start_time = asyncio.get_event_loop().time()
        
        if tool_name not in self._tools_registry:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        try:
            # Log tool call
            if self.journal_manager:
                self.journal_manager.log_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=None,
                    session_id=session_id,
                    success=True
                )
            
            # Execute tool
            result = await self._execute_tool(tool_name, arguments, session_id)
            
            # Calculate duration
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Log result
            if self.journal_manager:
                self.journal_manager.log_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    session_id=session_id,
                    duration_ms=duration_ms,
                    success=True
                )
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ],
                "isError": False
            }
            
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Log error
            if self.journal_manager:
                self.journal_manager.log_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    result={"error": str(e)},
                    session_id=session_id,
                    duration_ms=duration_ms,
                    success=False
                )
                self.journal_manager.log_error(
                    error=e,
                    operation="tool_execution",
                    session_id=session_id,
                    tool_name=tool_name,
                    context=arguments
                )
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing tool {tool_name}: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute a specific tool with given arguments."""
        
        if tool_name == "generate_code":
            return await self._generate_code(arguments, session_id)
        elif tool_name == "debug_code":
            return await self._debug_code(arguments, session_id)
        elif tool_name == "execute_tests":
            return await self._execute_tests(arguments, session_id)
        elif tool_name == "research_documentation":
            return await self._research_documentation(arguments, session_id)
        elif tool_name == "create_requirements_spec":
            return await self._create_requirements_spec(arguments, session_id)
        elif tool_name == "create_design_spec":
            return await self._create_design_spec(arguments, session_id)
        elif tool_name == "manage_session":
            return await self._manage_session(arguments, session_id)
        elif tool_name == "setup_dev_environment":
            return await self._setup_dev_environment(arguments, session_id)
        elif tool_name == "execute_command":
            return await self._execute_command(arguments, session_id)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _generate_code(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Generate code using LLM."""
        from .llm.models import LLMRequest, Message, MessageRole
        
        requirements = arguments["requirements"]
        language = arguments.get("language", "python")
        context = arguments.get("context", "")
        style_guide = arguments.get("style_guide", "")
        
        prompt = f"""
        Generate {language} code based on the following requirements:
        
        Requirements: {requirements}
        
        Context: {context}
        
        Style Guide: {style_guide}
        
        Please provide:
        1. Complete, working code
        2. Comments explaining the implementation
        3. Usage examples if applicable
        4. Error handling
        5. Unit tests if appropriate
        """
        
        request = LLMRequest(
            messages=[
                Message(role=MessageRole.USER, content=prompt)
            ],
            model="gpt-4"
        )
        
        response = await self.llm_router.generate(request, conversation_id=session_id)
        
        return {
            "generated_code": response.content,
            "language": language,
            "timestamp": str(asyncio.get_event_loop().time())
        }
    
    async def _debug_code(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Debug and fix code issues."""
        from .llm.models import LLMRequest, Message, MessageRole
        
        code = arguments["code"]
        error_message = arguments["error_message"]
        language = arguments.get("language", "python")
        context = arguments.get("context", "")
        
        prompt = f"""
        Debug and fix the following {language} code:
        
        Error: {error_message}
        
        Code to debug:
        ```{language}
        {code}
        ```
        
        Context: {context}
        
        Please provide:
        1. Analysis of the issue
        2. Fixed code
        3. Explanation of the fix
        4. Prevention suggestions
        """
        
        request = LLMRequest(
            messages=[
                Message(role=MessageRole.USER, content=prompt)
            ],
            model="gpt-4"
        )
        
        response = await self.llm_router.generate(request, conversation_id=session_id)
        
        return {
            "analysis": response.content,
            "original_code": code,
            "language": language,
            "error": error_message
        }
    
    async def _execute_tests(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute tests in development environment."""
        project_path = arguments["project_path"]
        test_command = arguments.get("test_command", "pytest")
        timeout = arguments.get("timeout", 300)
        
        # Create or get container for this project
        project_name = Path(project_path).name
        container_info = await self.docker_controller.create_development_environment(
            project_name=project_name,
            project_path=Path(project_path)
        )
        
        # Execute test command
        result = await self.docker_controller.execute_command(
            container_id=container_info["id"],
            command=test_command,
            timeout=timeout
        )
        
        return {
            "container_id": container_info["id"],
            "test_command": test_command,
            "result": result,
            "success": result.get("exit_code") == 0
        }
    
    async def _research_documentation(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Research technical documentation."""
        from .research.engine import ResearchQuery
        
        query = ResearchQuery(
            query=arguments["query"],
            query_type=arguments.get("query_type", "technical"),
            max_results=arguments.get("max_results", 5),
            context={"additional_context": arguments.get("context", "")}
        )
        
        results = await self.research_engine.research(query)
        
        return {
            "query": arguments["query"],
            "query_type": arguments.get("query_type", "technical"),
            "results": [
                {
                    "source": result.source,
                    "content": result.content,
                    "relevance_score": result.relevance_score,
                    "url": result.url,
                    "metadata": result.metadata
                }
                for result in results
            ]
        }
    
    async def _create_requirements_spec(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Create requirements specification."""
        spec = self.spec_manager.create_requirements_spec(
            title=arguments["title"],
            description=arguments["description"],
            project_context=arguments.get("project_context"),
            constraints=arguments.get("constraints"),
            acceptance_criteria=arguments.get("acceptance_criteria")
        )
        
        return {
            "spec_id": spec.id,
            "title": spec.title,
            "type": spec.type,
            "created_at": spec.created_at.isoformat(),
            "requirements": spec.content
        }
    
    async def _create_design_spec(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Create design specification."""
        spec = self.spec_manager.create_design_spec(
            title=arguments["title"],
            requirements_id=arguments.get("requirements_id"),
            design_type=arguments.get("design_type", "technical"),
            components=arguments.get("components"),
            architecture_style=arguments.get("architecture_style")
        )
        
        return {
            "spec_id": spec.id,
            "title": spec.title,
            "type": spec.type,
            "created_at": spec.created_at.isoformat(),
            "design": spec.content
        }
    
    async def _manage_session(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Manage development sessions."""
        action = arguments["action"]
        
        if action == "create":
            new_session_id = self.state_manager.create_session(
                context=arguments.get("context", {}),
                metadata=arguments.get("metadata", {})
            )
            return {"session_id": new_session_id, "action": "created"}
        
        elif action == "update":
            target_session_id = arguments.get("session_id", session_id)
            success = self.state_manager.update_session(
                session_id=target_session_id,
                context=arguments.get("context"),
                metadata=arguments.get("metadata")
            )
            return {"success": success, "action": "updated"}
        
        elif action == "close":
            target_session_id = arguments.get("session_id", session_id)
            success = self.state_manager.close_session(
                session_id=target_session_id,
                status=arguments.get("status", "completed")
            )
            return {"success": success, "action": "closed"}
        
        elif action == "checkpoint":
            target_session_id = arguments.get("session_id", session_id)
            checkpoint_id = self.state_manager.create_checkpoint(
                session_id=target_session_id,
                reason="manual",
                metadata=arguments.get("metadata", {})
            )
            return {"checkpoint_id": checkpoint_id, "action": "checkpoint_created"}
        
        elif action == "recover":
            target_session_id = arguments.get("session_id", session_id)
            success = self.state_manager.recover_session(
                session_id=target_session_id,
                checkpoint_id=arguments.get("checkpoint_id")
            )
            return {"success": success, "action": "recovered"}
        
        else:
            raise ValueError(f"Unknown session action: {action}")
    
    async def _setup_dev_environment(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Setup development environment with Docker."""
        project_name = arguments["project_name"]
        project_path = Path(arguments["project_path"])
        requirements = arguments.get("requirements", [])
        environment_vars = arguments.get("environment_vars", {})
        
        container_info = await self.docker_controller.create_development_environment(
            project_name=project_name,
            project_path=project_path,
            requirements=requirements,
            environment_vars=environment_vars
        )
        
        return {
            "project_name": project_name,
            "container_id": container_info["id"],
            "container_name": container_info["name"],
            "status": container_info["status"],
            "access_info": container_info.get("access_info", {})
        }
    
    async def _execute_command(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute command in development environment."""
        container_id = arguments["container_id"]
        command = arguments["command"]
        timeout = arguments.get("timeout", 300)
        
        result = await self.docker_controller.execute_command(
            container_id=container_id,
            command=command,
            timeout=timeout
        )
        
        return {
            "container_id": container_id,
            "command": command,
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "duration": result["duration"]
        }


async def main():
    """Main entry point for the MCP server."""
    config = load_config()
    server = MCPServer(config)
    
    try:
        await server.start()
        
        # Keep server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())