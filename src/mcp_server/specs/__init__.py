"""
Spec-Driven Development Module

Handles requirements, design, and task specification management.
Provides tools for structured development workflows and feedback integration.
"""

from .manager import SpecManager
from .generators import RequirementsGenerator, DesignGenerator, TaskGenerator
from .models import SpecDocument

__all__ = ["SpecManager", "RequirementsGenerator", "DesignGenerator", "TaskGenerator", "SpecDocument"]