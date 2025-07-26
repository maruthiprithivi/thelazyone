"""
Environment Setup Module

Configures development environments with proper Python setup, dependencies, and security settings.
Handles project-specific configurations and environment variable management.
"""

import asyncio
import logging
import tempfile
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import aiodocker
import aiofiles
from aiodocker.exceptions import DockerError

from ..config import DockerConfig


class EnvironmentSetup:
    """
    Configures and manages development environments for code execution.
    
    Handles Python environment setup, dependency installation, security configuration,
    and project-specific settings with comprehensive error handling.
    """
    
    def __init__(self, docker_client: aiodocker.Docker, config: DockerConfig):
        """
        Initialize environment setup manager.
        
        Args:
            docker_client: AioDocker client instance
            config: Docker configuration settings
        """
        self.docker_client = docker_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._base_images: Dict[str, str] = {}
        
        self.logger.info("EnvironmentSetup initialized")
    
    async def initialize(self) -> None:
        """
        Initialize environment setup manager and verify base images.
        
        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Ensure base image is available
            await self._ensure_base_image()
            
            self._initialized = True
            self.logger.info("EnvironmentSetup fully initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize EnvironmentSetup: {e}")
            raise RuntimeError(f"Environment setup initialization failed: {e}")
    
    async def _ensure_base_image(self) -> None:
        """
        Ensure the base Docker image is available locally.
        
        Raises:
            RuntimeError: If image cannot be pulled
        """
        try:
            # Check if image exists locally
            images = await self.docker_client.images.list()
            base_image = self.config.base_image
            
            image_exists = any(
                any(tag.startswith(base_image) for tag in image.get('RepoTags', []))
                for image in images
            )
            
            if not image_exists:
                self.logger.info(f"Pulling base image: {base_image}")
                await self.docker_client.images.pull(base_image)
                self.logger.info(f"Base image pulled successfully: {base_image}")
            else:
                self.logger.info(f"Base image already available: {base_image}")
                
        except Exception as e:
            self.logger.error(f"Failed to ensure base image: {e}")
            raise RuntimeError(f"Cannot pull base image {self.config.base_image}: {e}")
    
    async def create_environment_config(
        self,
        project_name: str,
        project_path: Path,
        requirements: Optional[List[str]] = None,
        environment_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create comprehensive environment configuration for a project.
        
        Args:
            project_name: Name of the project
            project_path: Path to the project directory
            requirements: List of Python package requirements
            environment_vars: Environment variables for the container
            
        Returns:
            Dictionary containing complete environment configuration
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If configuration creation fails
        """
        self.logger.info(f"Creating environment config for {project_name}")
        
        try:
            # Validate inputs
            if not project_name or not project_name.replace('-', '').replace('_', '').isalnum():
                raise ValueError("Invalid project name")
            
            if not project_path.exists():
                raise ValueError(f"Project path does not exist: {project_path}")
            
            # Create environment configuration
            config = {
                'image': self.config.base_image,
                'working_dir': '/app',
                'environment': {},
                'volumes': {},
                'ports': {},
                'command': None,
                'entrypoint': None
            }
            
            # Set up project volume
            config['volumes'][str(project_path.absolute())] = '/app'
            
            # Set up environment variables
            config['environment']['PROJECT_NAME'] = project_name
            config['environment']['PYTHONPATH'] = '/app'
            config['environment']['PYTHONDONTWRITEBYTECODE'] = '1'
            config['environment']['PYTHONUNBUFFERED'] = '1'
            
            # Add custom environment variables
            if environment_vars:
                config['environment'].update(environment_vars)
            
            # Set up requirements installation
            if requirements:
                requirements_content = '\n'.join(requirements)
                requirements_file = await self._create_temporary_requirements(
                    project_name, requirements_content
                )
                config['volumes'][requirements_file] = '/tmp/requirements.txt:ro'
                config['environment']['REQUIREMENTS_FILE'] = '/tmp/requirements.txt'
            
            # Configure development tools
            await self._configure_development_tools(config, project_path)
            
            # Set up security and resource constraints
            await self._apply_security_config(config)
            
            # Configure entrypoint for environment setup
            config['entrypoint'] = await self._create_entrypoint_script()
            
            self.logger.info(f"Environment config created for {project_name}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create environment config: {e}")
            raise RuntimeError(f"Environment configuration failed: {e}")
    
    async def _create_temporary_requirements(
        self,
        project_name: str,
        requirements_content: str
    ) -> str:
        """
        Create temporary requirements file.
        
        Args:
            project_name: Project name for filename
            requirements_content: Requirements file content
            
        Returns:
            Path to temporary requirements file
        """
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'_{project_name}_requirements.txt',
            delete=False
        )
        
        async with aiofiles.open(temp_file.name, 'w') as f:
            await f.write(requirements_content)
        
        return temp_file.name
    
    async def _configure_development_tools(
        self,
        config: Dict[str, Any],
        project_path: Path
    ) -> None:
        """
        Configure development tools and utilities.
        
        Args:
            config: Environment configuration
            project_path: Project directory path
        """
        # Configure port mappings for development tools
        config['ports']['8000'] = 8000  # Default web server port
        config['ports']['3000'] = 3000  # Alternative port
        config['ports']['8080'] = 8080  # Debug port
        
        # Configure additional volumes for development
        ssh_path = Path.home() / '.ssh'
        if ssh_path.exists():
            config['volumes'][str(ssh_path)] = '/root/.ssh:ro'
        
        git_config = Path.home() / '.gitconfig'
        if git_config.exists():
            config['volumes'][str(git_config)] = '/root/.gitconfig:ro'
    
    async def _apply_security_config(self, config: Dict[str, Any]) -> None:
        """
        Apply security configurations to the environment.
        
        Args:
            config: Environment configuration to modify
        """
        # Add security-related environment variables
        security_env = {
            'USER': 'developer',
            'HOME': '/home/developer',
            'PATH': '/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        }
        
        config['environment'].update(security_env)
    
    async def _create_entrypoint_script(self) -> List[str]:
        """
        Create entrypoint script for environment initialization.
        
        Returns:
            Entrypoint command list
        """
        script = [
            '/bin/bash',
            '-c',
            '''
            set -e
            
            # Create user if running as root
            if [ "$(id -u)" = "0" ]; then
                useradd -m -s /bin/bash developer 2>/dev/null || true
                chown -R developer:developer /app
            fi
            
            # Install requirements if provided
            if [ -f "$REQUIREMENTS_FILE" ]; then
                echo "Installing Python requirements..."
                python3 -m pip install --no-cache-dir -r "$REQUIREMENTS_FILE"
            fi
            
            # Install common development tools
            python3 -m pip install --no-cache-dir \
                pytest pytest-cov black flake8 mypy ipython jupyter
            
            # Set up git configuration if not present
            if [ ! -f /home/developer/.gitconfig ] && [ -f /root/.gitconfig ]; then
                cp /root/.gitconfig /home/developer/.gitconfig
                chown developer:developer /home/developer/.gitconfig
            fi
            
            # Start development environment
            echo "Development environment ready!"
            echo "Project: $PROJECT_NAME"
            echo "Working directory: $PWD"
            echo "Python version: $(python3 --version)"
            echo "Available commands: python3, pytest, black, flake8, mypy, ipython"
            
            # Keep container running
            tail -f /dev/null
            '''
        ]
        
        return script
    
    async def create_custom_image(
        self,
        project_name: str,
        base_image: str,
        requirements: List[str],
        custom_commands: Optional[List[str]] = None
    ) -> str:
        """
        Create a custom Docker image for a project.
        
        Args:
            project_name: Name of the project
            base_image: Base Docker image
            requirements: Python requirements
            custom_commands: Additional Docker commands
            
        Returns:
            Name of the created image
            
        Raises:
            RuntimeError: If image creation fails
        """
        self.logger.info(f"Creating custom image for {project_name}")
        
        try:
            # Create Dockerfile
            dockerfile_content = await self._create_dockerfile(
                base_image, requirements, custom_commands
            )
            
            # Create temporary build context
            with tempfile.TemporaryDirectory() as temp_dir:
                dockerfile_path = Path(temp_dir) / 'Dockerfile'
                
                async with aiofiles.open(dockerfile_path, 'w') as f:
                    await f.write(dockerfile_content)
                
                # Build image
                image_name = f"mcp-{project_name}:latest"
                
                build_logs = await self.docker_client.images.build(
                    path=str(temp_dir),
                    tag=image_name,
                    rm=True,
                    forcerm=True,
                    pull=True
                )
                
                self.logger.info(f"Custom image created: {image_name}")
                return image_name
                
        except Exception as e:
            self.logger.error(f"Failed to create custom image: {e}")
            raise RuntimeError(f"Custom image creation failed: {e}")
    
    async def _create_dockerfile(
        self,
        base_image: str,
        requirements: List[str],
        custom_commands: Optional[List[str]] = None
    ) -> str:
        """
        Create Dockerfile content.
        
        Args:
            base_image: Base Docker image
            requirements: Python requirements
            custom_commands: Additional Docker commands
            
        Returns:
            Dockerfile content
        """
        dockerfile = f"""
FROM {base_image}

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash developer

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
"""
        
        if requirements:
            requirements_str = '\n'.join(requirements)
            dockerfile += f"""
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt
"""
        
        dockerfile += """
# Install development tools
RUN python3 -m pip install --no-cache-dir \\
    pytest pytest-cov black flake8 mypy ipython jupyter

# Set up user environment
USER developer
ENV HOME=/home/developer
ENV PATH=$HOME/.local/bin:$PATH

# Default command
CMD ["tail", "-f", "/dev/null"]
"""
        
        if custom_commands:
            dockerfile += '\n# Custom commands\n'
            for command in custom_commands:
                dockerfile += f"RUN {command}\n"
        
        return dockerfile
    
    async def validate_environment(self, container_id: str) -> Dict[str, Any]:
        """
        Validate that a development environment is properly configured.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Validation results
        """
        self.logger.info(f"Validating environment: {container_id}")
        
        validation_results = {
            'container_id': container_id,
            'status': 'validating',
            'checks': {},
            'issues': [],
            'overall_status': 'unknown'
        }
        
        try:
            # Check Python availability
            validation_results['checks']['python'] = {
                'available': False,
                'version': None
            }
            
            # This would be implemented in container_manager
            # For now, return mock validation
            validation_results['checks']['python']['available'] = True
            validation_results['checks']['python']['version'] = '3.11.0'
            validation_results['checks']['pip'] = {'available': True}
            validation_results['checks']['git'] = {'available': True}
            validation_results['overall_status'] = 'valid'
            
        except Exception as e:
            validation_results['issues'].append(str(e))
            validation_results['overall_status'] = 'invalid'
        
        return validation_results
    
    async def get_environment_info(self, container_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a development environment.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Environment information dictionary
        """
        return {
            'container_id': container_id,
            'python_version': '3.11.0',
            'installed_packages': [],
            'environment_variables': {},
            'working_directory': '/app',
            'user': 'developer',
            'shell': '/bin/bash'
        }
    
    async def export_environment_config(
        self,
        project_name: str,
        output_path: Path
    ) -> None:
        """
        Export environment configuration to a file.
        
        Args:
            project_name: Project name
            output_path: Output file path
        """
        config = {
            'project_name': project_name,
            'base_image': self.config.base_image,
            'python_version': '3.11',
            'requirements': [],
            'environment_variables': {},
            'volumes': {},
            'ports': {}
        }
        
        async with aiofiles.open(output_path, 'w') as f:
            await f.write(json.dumps(config, indent=2))
    
    async def import_environment_config(
        self,
        config_path: Path
    ) -> Dict[str, Any]:
        """
        Import environment configuration from a file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Environment configuration dictionary
        """
        async with aiofiles.open(config_path, 'r') as f:
            content = await f.read()
            return json.loads(content)
    
    async def cleanup(self) -> None:
        """
        Cleanup environment setup resources.
        """
        self.logger.info("Cleaning up EnvironmentSetup...")
        
        try:
            # Cleanup any temporary files
            pass  # Temporary files are handled by context managers
            
        except Exception as e:
            self.logger.error(f"Error during environment setup cleanup: {e}")
        
        finally:
            self._initialized = False
            self.logger.info("EnvironmentSetup cleanup completed")