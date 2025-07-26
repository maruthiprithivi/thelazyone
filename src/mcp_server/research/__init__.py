"""
Research and Documentation Module

Provides research capabilities for documentation lookup, best practices,
and troubleshooting through integration with external services.
"""

from .engine import ResearchEngine
from .context7_integration import Context7Integration
from .web_searcher import WebSearcher

__all__ = ["ResearchEngine", "Context7Integration", "WebSearcher"]