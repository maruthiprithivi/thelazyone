"""
Journal and Documentation Module

Maintains comprehensive activity logs and documentation for all MCP server operations.
Provides structured logging and cross-referencing capabilities.
"""

from .manager import JournalManager
from .models import JournalEntry

__all__ = ["JournalManager", "JournalEntry"]