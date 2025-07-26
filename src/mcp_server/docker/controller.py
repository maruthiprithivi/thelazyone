"""
Docker Controller Module

Core controller for managing Docker operations, container lifecycle, and resource management.
Provides high-level orchestration for development environment isolation.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiodocker
from aiodocker.exceptions import DockerError

from ..config import DockerConfig
from .container_manager import ContainerManager
from .environment_setup import EnvironmentSetup


class DockerController:
    """
    Main Docker controller for orchestrating containerized development environments.
    
    Provides unified management of Docker resources, container lifecycle,
    and environment setup with comprehensive error handling and security.
    """
    
    def __init__(self, config: DockerConfig):
        """
        Initialize Docker controller with configuration.
        
        Args:
            config: Docker configuration settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.docker_client: Optional[aiodocker.Docker] = None
        self.container_manager: Optional[ContainerManager] = None
        self.environment_setup: Optional[EnvironmentSetup] = None
        self._initialized = False
        
        self.logger.info("DockerController initialized")
    
    async def initialize(self) -> None:
        """
        Initialize Docker client and subcomponents.
        
        Raises:
            ConnectionError: If Docker daemon is not accessible
            RuntimeError: If initialization fails
        """
        if self._initialized:
            return
            
        try:
            self.logger.info("Initializing Docker client...")
            self.docker_client = aiodocker.Docker()
            
            # Verify Docker daemon connectivity
            await self._verify_docker_connection()
            
            # Initialize subcomponents
            self.container_manager = ContainerManager(
                docker_client=self.docker_client,
                config=self.config
            )
            
            self.environment_setup = EnvironmentSetup(
                docker_client=self.docker_client,
                config=self.config
            )
            
            await self.container_manager.initialize()
            await self.environment_setup.initialize()
            
            self._initialized = True
            self.logger.info("DockerController fully initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DockerController: {e}")
            await self.cleanup()
            raise RuntimeError(f"Docker initialization failed: {e}")
    
    async def _verify_docker_connection(self) -> None:
        """
        Verify connectivity to Docker daemon.
        
        Raises:
            ConnectionError: If Docker daemon is not accessible
        """
        try:
            info = await self.docker_client.system.info()
            self.logger.info(f"Connected to Docker daemon: {info.get('Name', 'unknown')}")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Docker daemon: {e}")
    
    async def create_development_environment(
        self,
        project_name: str,
        project_path: Path,
        requirements: Optional[List[str]] = None,
        environment_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete development environment for a project.
        
        Args:
            project_name: Name of the project
            project_path: Path to the project directory
            requirements: List of Python package requirements
            environment_vars: Environment variables for the container
            
        Returns:
            Dictionary containing container information and access details
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If environment creation fails
        """
        if not self._initialized:
            await self.initialize()
        
        self.logger.info(f"Creating development environment for {project_name}")
        
        try:
            # Setup environment configuration
            env_config = await self.environment_setup.create_environment_config(
                project_name=project_name,
                project_path=project_path,
                requirements=requirements,
                environment_vars=environment_vars
            )
            
            # Create and start container
            container_info = await self.container_manager.create_container(
                name=f"mcp-{project_name}",
                config=env_config
            )
            
            self.logger.info(f"Development environment created: {container_info}")
            return container_info
            
        except Exception as e:
            self.logger.error(f"Failed to create development environment: {e}")
            raise RuntimeError(f"Environment creation failed: {e}")
    
    async def execute_command(
        self,
        container_id: str,
        command: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a command in a container.
        
        Args:
            container_id: ID or name of the container
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            ValueError: If container doesn't exist
            RuntimeError: If command execution fails
        """
        if not self._initialized:
            await self.initialize()
        
        self.logger.info(f"Executing command in container {container_id}: {command}")
        
        try:
            result = await self.container_manager.execute_command(
                container_id=container_id,
                command=command,
                timeout=timeout or self.config.timeout
            )
            
            self.logger.debug(f"Command executed successfully: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute command: {e}")
            raise RuntimeError(f"Command execution failed: {e}")
    
    async def get_container_status(self, container_id: str) -> Dict[str, Any]:
        """
        Get status information for a container.
        
        Args:
            container_id: ID or name of the container
            
        Returns:
            Dictionary containing container status information
            
        Raises:
            ValueError: If container doesn't exist
        """
        if not self._initialized:
            await self.initialize()
        
        return await self.container_manager.get_container_status(container_id)
    
    async def list_containers(self, project_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all managed containers.
        
        Args:
            project_filter: Optional project name filter
            
        Returns:
            List of container information dictionaries
        """
        if not self._initialized:
            await self.initialize()
        
        containers = await self.container_manager.list_containers()
        
        if project_filter:
            containers = [
                c for c in containers
                if c.get('project_name') == project_filter
            ]
        
        return containers
    
    async def stop_container(self, container_id: str, timeout: int = 30) -> None:
        """
        Stop a running container.
        
        Args:
            container_id: ID or name of the container
            timeout: Graceful shutdown timeout in seconds
        """
        if not self._initialized:
            await self.initialize()
        
        self.logger.info(f"Stopping container: {container_id}")
        await self.container_manager.stop_container(container_id, timeout)
    
    async def remove_container(self, container_id: str, force: bool = False) -> None:
        """
        Remove a container.
        
        Args:
            container_id: ID or name of the container
            force: Force removal even if running
        """
        if not self._initialized:
            await self.initialize()
        
        self.logger.info(f"Removing container: {container_id}")
        await self.container_manager.remove_container(container_id, force)
    
    async def cleanup_project(self, project_name: str) -> None:
        """
        Clean up all resources for a project.
        
        Args:
            project_name: Name of the project to clean up
        """
        if not self._initialized:
            return
        
        self.logger.info(f"Cleaning up project: {project_name}")
        
        try:
            containers = await self.list_containers(project_filter=project_name)
            
            for container in containers:
                container_id = container['id']
                try:
                    await self.stop_container(container_id)
                    await self.remove_container(container_id)
                    self.logger.info(f"Cleaned up container: {container_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up container {container_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error during project cleanup: {e}")
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get overall Docker resource usage.
        
        Returns:
            Dictionary containing resource usage statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            info = await self.docker_client.system.info()
            containers = await self.docker_client.containers.list()
            
            usage = {
                'containers_total': len(containers),
                'containers_running': len([c for c in containers if c['State'] == 'running']),
                'memory_total': info.get('MemTotal', 0),
                'memory_used': info.get('MemTotal', 0) - info.get('MemAvailable', 0),
                'cpu_count': info.get('NCPU', 0),
                'images': len(info.get('Images', [])),
                'docker_version': info.get('ServerVersion', 'unknown')
            }
            
            return usage
            
        except Exception as e:
            self.logger.error(f"Failed to get resource usage: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of Docker subsystem.
        
        Returns:
            Dictionary containing health status information
        """
        health = {
            'status': 'healthy',
            'components': {},
            'errors': []
        }
        
        try:
            if not self._initialized:
                await self.initialize()
            
            # Check Docker daemon
            await self.docker_client.system.info()
            health['components']['docker_daemon'] = 'healthy'
            
            # Check container manager
            if self.container_manager:
                health['components']['container_manager'] = 'healthy'
            
            # Check environment setup
            if self.environment_setup:
                health['components']['environment_setup'] = 'healthy'
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(str(e))
            health['components']['docker_daemon'] = 'unhealthy'
        
        return health
    
    async def cleanup(self) -> None:
        """
        Cleanup all Docker resources and close connections.
        """
        self.logger.info("Cleaning up DockerController...")
        
        try:
            if self.container_manager:
                await self.container_manager.cleanup()
            
            if self.environment_setup:
                await self.environment_setup.cleanup()
            
            if self.docker_client:
                await self.docker_client.close()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        
        finally:
            self.docker_client = None
            self.container_manager = None
            self.environment_setup = None
            self._initialized = False
            self.logger.info("DockerController cleanup completed")