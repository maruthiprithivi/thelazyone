"""
Claude Code MCP Server - AI-powered development assistant

A comprehensive Model Context Protocol (MCP) server that provides
AI-powered code development capabilities with Claude Code integration.
"""

__version__ = "1.0.0"
__author__ = "Maruthi Prithivi"
__email__ = "maruthi@example.com"
__description__ = "AI-powered MCP server for automated code development"

from .server import MCPServer
from .config import ServerConfig

__all__ = ["MCPServer", "ServerConfig"]