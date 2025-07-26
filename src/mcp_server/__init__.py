"""
Claude Code MCP Server - AI-powered development assistant

A comprehensive Model Context Protocol (MCP) server that provides
AI-powered code development capabilities with Claude Code integration.
"""

__version__ = "0.0.1"
__author__ = "Maruthi Prithivi"
__email__ = "maruthiprithivi@gmail.com"
__description__ = "AI-powered MCP server for automated code development"

from .server import MCPServer
from .config import ServerConfig

__all__ = ["MCPServer", "ServerConfig"]