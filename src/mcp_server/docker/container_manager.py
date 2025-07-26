"""
Container Manager Module

Manages Docker container lifecycle including creation, execution, monitoring, and cleanup.
Provides comprehensive container management with security and resource constraints.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import aiodocker
from aiodocker.containers import DockerContainer
from aiodocker.exceptions import DockerError
import time

from ..config import DockerConfig


class ContainerManager:
    """
    Manages Docker container lifecycle and operations.
    
    Handles container creation, execution, monitoring, and cleanup with comprehensive
    error handling, security constraints, and resource management.
    """
    
    def __init__(self, docker_client: aiodocker.Docker, config: DockerConfig):
        """
        Initialize container manager.
        
        Args:
            docker_client: AioDocker client instance
            config: Docker configuration settings
        """
        self.docker_client = docker_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._containers: Dict[str, DockerContainer] = {}
        self._initialized = False
        
        self.logger.info("ContainerManager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize container manager and verify Docker capabilities.
        
        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Verify Docker API version
            try:
                version_info = await self.docker_client.system.version()
                api_version = version_info.get('ApiVersion', 'unknown')
                self.logger.info(f"Docker API version: {api_version}")
            except AttributeError:
                # Handle different aiodocker API versions
                try:
                    version_info = await self.docker_client.version()
                    api_version = version_info.get('ApiVersion', 'unknown')
                    self.logger.info(f"Docker API version: {api_version}")
                except Exception as e:
                    self.logger.warning(f"Could not determine Docker API version: {e}")
                    api_version = "unknown"
            
            # Load existing containers
            await self._load_existing_containers()
            
            self._initialized = True
            self.logger.info("ContainerManager fully initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ContainerManager: {e}")
            raise RuntimeError(f"Container manager initialization failed: {e}")
    
    async def _load_existing_containers(self) -> None:
        """
        Load existing managed containers.
        """
        try:
            containers = await self.docker_client.containers.list()
            for container in containers:
                container_info = await container.show()
                name = container_info.get('Name', '').lstrip('/')
                
                # Track containers managed by this system
                if name.startswith('mcp-'):
                    self._containers[name] = container
                    self.logger.debug(f"Loaded existing container: {name}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to load existing containers: {e}")
    
    async def create_container(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create and start a new container.
        
        Args:
            name: Container name
            config: Container configuration dictionary
            
        Returns:
            Dictionary containing container information
            
        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If container creation fails
        """
        self.logger.info(f"Creating container: {name}")
        
        try:
            # Validate container name
            if not name or not name.replace('-', '').replace('_', '').isalnum():
                raise ValueError("Invalid container name")
            
            # Check if container already exists
            if name in self._containers:
                raise ValueError(f"Container {name} already exists")
            
            # Prepare container configuration
            container_config = self._prepare_container_config(name, config)
            
            # Create container
            container = await self.docker_client.containers.create(
                config=container_config,
                name=name
            )
            
            # Start container
            await container.start()
            
            # Store container reference
            self._containers[name] = container
            
            # Wait for container to be ready
            await self._wait_for_container_ready(container)
            
            # Get container information
            container_info = await self._get_container_info(container)
            
            self.logger.info(f"Container created successfully: {name}")
            return container_info
            
        except DockerError as e:
            self.logger.error(f"Docker error creating container {name}: {e}")
            raise RuntimeError(f"Failed to create container: {e}")
        except Exception as e:
            self.logger.error(f"Error creating container {name}: {e}")
            raise
    
    def _prepare_container_config(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare container configuration with security and resource constraints.
        
        Args:
            name: Container name
            config: User configuration
            
        Returns:
            Docker container configuration
        """
        # Base configuration
        container_config = {
            'Image': config.get('image', self.config.base_image),
            'WorkingDir': config.get('working_dir', '/app'),
            'Env': [],
            'ExposedPorts': {},
            'HostConfig': {
                'Memory': self._parse_memory_limit(self.config.memory_limit),
                'CpuQuota': self._parse_cpu_limit(self.config.cpu_limit),
                'NetworkMode': self.config.network_mode,
                'SecurityOpt': self.config.security_opts,
                'ReadonlyRootfs': False,
                'Privileged': False,
                'RestartPolicy': {'Name': 'no'},
                'AutoRemove': False,
                'Binds': [],
                'PortBindings': {},
                'Dns': ['8.8.8.8', '8.8.4.4']
            }
        }
        
        # Add environment variables
        env_vars = config.get('environment', {})
        for key, value in env_vars.items():
            container_config['Env'].append(f"{key}={value}")
        
        # Add port mappings
        ports = config.get('ports', {})
        for container_port, host_port in ports.items():
            container_config['ExposedPorts'][f"{container_port}/tcp"] = {}
            container_config['HostConfig']['PortBindings'][f"{container_port}/tcp"] = [
                {'HostPort': str(host_port)}
            ]
        
        # Add volume mounts
        volumes = config.get('volumes', {})
        for host_path, container_path in volumes.items():
            bind_config = f"{host_path}:{container_path}"
            if container_path.startswith('/app'):
                bind_config += ":rw"
            else:
                bind_config += ":ro"
            container_config['HostConfig']['Binds'].append(bind_config)
        
        # Add command
        if 'command' in config:
            container_config['Cmd'] = config['command']
        
        # Add entrypoint
        if 'entrypoint' in config:
            container_config['Entrypoint'] = config['entrypoint']
        
        return container_config
    
    def _parse_memory_limit(self, memory_str: str) -> int:
        """
        Parse memory limit string to bytes.
        
        Args:
            memory_str: Memory limit string (e.g., "512m", "1g")
            
        Returns:
            Memory limit in bytes
        """
        memory_str = memory_str.lower()
        
        if memory_str.endswith('k'):
            return int(memory_str[:-1]) * 1024
        elif memory_str.endswith('m'):
            return int(memory_str[:-1]) * 1024 * 1024
        elif memory_str.endswith('g'):
            return int(memory_str[:-1]) * 1024 * 1024 * 1024
        else:
            return int(memory_str)
    
    def _parse_cpu_limit(self, cpu_str: str) -> int:
        """
        Parse CPU limit string to quota value.
        
        Args:
            cpu_str: CPU limit string (e.g., "1.0", "0.5")
            
        Returns:
            CPU quota value for Docker
        """
        cpu_value = float(cpu_str)
        # Docker uses 100000 as the base for CPU quota
        return int(cpu_value * 100000)
    
    async def _wait_for_container_ready(
        self,
        container: DockerContainer,
        timeout: int = 60
    ) -> None:
        """
        Wait for container to be ready.
        
        Args:
            container: Docker container
            timeout: Maximum wait time in seconds
            
        Raises:
            RuntimeError: If container fails to start
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container_info = await container.show()
                state = container_info.get('State', {})
                
                if state.get('Running'):
                    # Check if container is actually ready
                    if state.get('Health', {}).get('Status') == 'healthy':
                        return
                    
                    # For containers without health check, wait a bit more
                    await asyncio.sleep(2)
                    return
                    
                elif state.get('Error'):
                    raise RuntimeError(f"Container failed to start: {state['Error']}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                raise RuntimeError(f"Error checking container status: {e}")
        
        raise RuntimeError(f"Container failed to start within {timeout} seconds")
    
    async def _get_container_info(self, container: DockerContainer) -> Dict[str, Any]:
        """
        Get detailed container information.
        
        Args:
            container: Docker container
            
        Returns:
            Dictionary containing container information
        """
        try:
            container_info = await container.show()
            
            return {
                'id': container_info['Id'][:12],
                'name': container_info['Name'].lstrip('/'),
                'status': container_info['State']['Status'],
                'running': container_info['State']['Running'],
                'image': container_info['Config']['Image'],
                'created': container_info['Created'],
                'ports': self._extract_ports(container_info),
                'mounts': self._extract_mounts(container_info),
                'environment': container_info['Config'].get('Env', [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get container info: {e}")
            return {}
    
    def _extract_ports(self, container_info: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract port mappings from container info.
        
        Args:
            container_info: Container information
            
        Returns:
            Dictionary of port mappings
        """
        ports = {}
        
        # Network settings
        network_settings = container_info.get('NetworkSettings', {})
        port_bindings = network_settings.get('Ports', {})
        
        for container_port, host_configs in port_bindings.items():
            if host_configs:
                ports[container_port] = [
                    {
                        'host_ip': config.get('HostIp', ''),
                        'host_port': config.get('HostPort', '')
                    }
                    for config in host_configs
                ]
        
        return ports
    
    def _extract_mounts(self, container_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract mount information from container info.
        
        Args:
            container_info: Container information
            
        Returns:
            List of mount information
        """
        mounts = []
        
        # Mounts
        container_mounts = container_info.get('Mounts', [])
        for mount in container_mounts:
            mounts.append({
                'source': mount.get('Source', ''),
                'destination': mount.get('Destination', ''),
                'mode': mount.get('Mode', ''),
                'type': mount.get('Type', 'bind')
            })
        
        return mounts
    
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
        self.logger.info(f"Executing command in container {container_id}: {command}")
        
        try:
            # Get container
            container = await self._get_container(container_id)
            if not container:
                raise ValueError(f"Container {container_id} not found")
            
            # Execute command
            exec_config = {
                'Cmd': ['/bin/sh', '-c', command],
                'AttachStdout': True,
                'AttachStderr': True,
                'Tty': False
            }
            
            exec_instance = await container.exec(exec_config)
            
            # Start execution
            output = await exec_instance.start(detach=False)
            
            # Get exit code
            result = await exec_instance.inspect()
            exit_code = result.get('ExitCode', -1)
            
            # Parse output
            stdout = output.decode('utf-8') if isinstance(output, bytes) else str(output)
            
            return {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': '',  # Combined with stdout in this implementation
                'command': command,
                'container_id': container_id
            }
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
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
        container = await self._get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not found")
        
        return await self._get_container_info(container)
    
    async def list_containers(self) -> List[Dict[str, Any]]:
        """
        List all managed containers.
        
        Returns:
            List of container information dictionaries
        """
        containers = []
        
        try:
            all_containers = await self.docker_client.containers.list(all=True)
            
            for container in all_containers:
                try:
                    container_info = await self._get_container_info(container)
                    containers.append(container_info)
                except Exception as e:
                    self.logger.warning(f"Failed to get info for container: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to list containers: {e}")
        
        return containers
    
    async def stop_container(self, container_id: str, timeout: int = 30) -> None:
        """
        Stop a running container.
        
        Args:
            container_id: ID or name of the container
            timeout: Graceful shutdown timeout in seconds
        """
        self.logger.info(f"Stopping container: {container_id}")
        
        try:
            container = await self._get_container(container_id)
            if container:
                await container.stop(timeout=timeout)
                
                # Remove from tracking
                name = container_id
                if name in self._containers:
                    del self._containers[name]
                
                self.logger.info(f"Container stopped: {container_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to stop container {container_id}: {e}")
            raise
    
    async def remove_container(self, container_id: str, force: bool = False) -> None:
        """
        Remove a container.
        
        Args:
            container_id: ID or name of the container
            force: Force removal even if running
        """
        self.logger.info(f"Removing container: {container_id}")
        
        try:
            container = await self._get_container(container_id)
            if container:
                await container.remove(force=force)
                
                # Remove from tracking
                name = container_id
                if name in self._containers:
                    del self._containers[name]
                
                self.logger.info(f"Container removed: {container_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to remove container {container_id}: {e}")
            raise
    
    async def _get_container(self, container_id: str) -> Optional[DockerContainer]:
        """
        Get container by ID or name.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Docker container or None if not found
        """
        try:
            # Try direct reference
            if container_id in self._containers:
                return self._containers[container_id]
            
            # Try to get by ID
            return await self.docker_client.containers.get(container_id)
            
        except DockerError:
            return None
        except Exception as e:
            self.logger.error(f"Error getting container {container_id}: {e}")
            return None
    
    async def get_container_logs(
        self,
        container_id: str,
        tail: int = 100,
        follow: bool = False
    ) -> str:
        """
        Get container logs.
        
        Args:
            container_id: Container ID or name
            tail: Number of lines to return from the end
            follow: Whether to follow the log output
            
        Returns:
            Container logs as string
        """
        try:
            container = await self._get_container(container_id)
            if not container:
                raise ValueError(f"Container {container_id} not found")
            
            logs = await container.log(stdout=True, stderr=True, tail=tail, follow=follow)
            
            if isinstance(logs, bytes):
                return logs.decode('utf-8')
            elif isinstance(logs, list):
                return '\n'.join(logs)
            else:
                return str(logs)
                
        except Exception as e:
            self.logger.error(f"Failed to get logs for container {container_id}: {e}")
            return ""
    
    async def cleanup(self) -> None:
        """
        Cleanup container manager resources.
        """
        self.logger.info("Cleaning up ContainerManager...")
        
        try:
            # Stop all managed containers
            for name, container in list(self._containers.items()):
                try:
                    await self.stop_container(name)
                except Exception as e:
                    self.logger.warning(f"Failed to stop container {name}: {e}")
            
            self._containers.clear()
            
        except Exception as e:
            self.logger.error(f"Error during container manager cleanup: {e}")
        
        finally:
            self._initialized = False
            self.logger.info("ContainerManager cleanup completed")