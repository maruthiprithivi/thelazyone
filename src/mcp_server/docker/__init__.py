"""
Docker Container Management Module

Manages isolated development environments for code execution and testing.
Handles container lifecycle, environment setup, and resource management.
"""

from .controller import DockerController
from .container_manager import ContainerManager
from .environment_setup import EnvironmentSetup

__all__ = ["DockerController", "ContainerManager", "EnvironmentSetup"]