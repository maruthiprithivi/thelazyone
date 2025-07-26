"""
Context7 Integration - Provides library documentation lookup capabilities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

# Note: We'll use the actual Context7 MCP tools provided by the environment
# The actual implementation will use the mcp__context7__resolve_library_id and 
# mcp__context7__get_library_docs tools available in the environment

logger = logging.getLogger(__name__)

class Context7Integration:
    """Integration with Context7 for library documentation and technical resources"""
    
    def __init__(self):
        """Initialize Context7 integration"""
        self.session_cache = {}
        self.request_timeout = 30.0
        
    async def resolve_library_id(self, library_name: str) -> Optional[str]:
        """
        Resolve a library name to its Context7-compatible ID
        
        Args:
            library_name: Name or partial name of the library
            
        Returns:
            Context7-compatible library ID or None if not found
        """
        try:
            # In the actual implementation, this would use:
            # from mcp__context7__resolve_library_id import resolve_library_id
            # return resolve_library_id(library_name)
            
            # For now, we'll simulate the resolution
            logger.info(f"Resolving library ID for: {library_name}")
            
            # This is a placeholder - in real implementation, use the MCP tool
            common_libraries = {
                'react': '/facebook/react',
                'next.js': '/vercel/next.js',
                'express': '/expressjs/express',
                'django': '/django/django',
                'flask': '/pallets/flask',
                'fastapi': '/tiangolo/fastapi',
                'numpy': '/numpy/numpy',
                'pandas': '/pandas-dev/pandas',
                'scikit-learn': '/scikit-learn/scikit-learn',
                'tensorflow': '/tensorflow/tensorflow',
                'pytorch': '/pytorch/pytorch',
                'mongodb': '/mongodb/docs',
                'postgresql': '/postgresql/postgresql',
                'redis': '/redis/redis',
                'supabase': '/supabase/supabase',
                'prisma': '/prisma/prisma',
                'docker': '/docker/docs',
                'kubernetes': '/kubernetes/kubernetes'
            }
            
            library_name_lower = library_name.lower().strip()
            
            # Direct match
            if library_name_lower in common_libraries:
                return common_libraries[library_name_lower]
            
            # Partial match
            for key, value in common_libraries.items():
                if library_name_lower in key or key in library_name_lower:
                    return value
            
            # Return a generic format for unknown libraries
            return f"/{library_name_lower}/{library_name_lower}"
            
        except Exception as e:
            logger.error(f"Error resolving library ID for {library_name}: {e}")
            return None
    
    async def get_library_docs(self, 
                             library_id: str, 
                             topic: Optional[str] = None,
                             tokens: int = 10000) -> List[Dict[str, Any]]:
        """
        Get documentation for a specific library
        
        Args:
            library_id: Context7-compatible library ID
            topic: Specific topic to focus on (e.g., 'hooks', 'routing', 'authentication')
            tokens: Maximum number of tokens to retrieve
            
        Returns:
            List of documentation entries with content and metadata
        """
        try:
            logger.info(f"Fetching docs for library: {library_id}, topic: {topic}")
            
            # In the actual implementation, this would use:
            # from mcp__context7__get_library_docs import get_library_docs
            # return get_library_docs(library_id, topic=topic, tokens=tokens)
            
            # Simulate documentation fetch
            mock_docs = [
                {
                    'content': f"Documentation for {library_id} - {topic or 'general'}",
                    'score': 0.95,
                    'metadata': {
                        'library': library_id,
                        'topic': topic,
                        'section': 'overview',
                        'version': 'latest'
                    },
                    'url': f"https://docs.context7.com{library_id}/{topic or ''}"
                }
            ]
            
            return mock_docs
            
        except Exception as e:
            logger.error(f"Error fetching docs for {library_id}: {e}")
            return []
    
    async def search_documentation(self, 
                                 query: str, 
                                 max_results: int = 10,
                                 context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for technical documentation based on query
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            context: Optional context for refining search
            
        Returns:
            List of documentation results
        """
        try:
            logger.info(f"Searching documentation for: {query}")
            
            # Extract library names from query or context
            library_names = self._extract_library_names(query, context)
            
            results = []
            
            for library_name in library_names:
                library_id = await self.resolve_library_id(library_name)
                if library_id:
                    docs = await self.get_library_docs(
                        library_id,
                        topic=query,
                        tokens=2000  # Smaller chunks for multiple libraries
                    )
                    results.extend(docs)
            
            # If no specific libraries found, do general search
            if not results:
                general_results = await self._general_technical_search(query, max_results)
                results.extend(general_results)
            
            # Sort by relevance and limit results
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in documentation search: {e}")
            return []
    
    async def search_troubleshooting(self, 
                                   query: str, 
                                   context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for troubleshooting information and common issues
        
        Args:
            query: Problem description or error message
            context: Optional context including stack traces, versions, etc.
            
        Returns:
            List of troubleshooting results
        """
        try:
            logger.info(f"Searching troubleshooting for: {query}")
            
            # Enhance query with context
            enhanced_query = self._enhance_troubleshooting_query(query, context)
            
            # Search for error patterns, common issues, and solutions
            results = await self.search_documentation(
                enhanced_query,
                max_results=15,
                context=context
            )
            
            # Filter for troubleshooting-related content
            troubleshooting_results = [
                result for result in results
                if any(keyword in result.get('content', '').lower() 
                      for keyword in ['error', 'issue', 'problem', 'troubleshoot', 'fix', 'solution'])
            ]
            
            return troubleshooting_results
            
        except Exception as e:
            logger.error(f"Error in troubleshooting search: {e}")
            return []
    
    async def search_best_practices(self, 
                                  query: str, 
                                  context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for best practices and patterns
        
        Args:
            query: Topic or technology to find best practices for
            context: Optional context for specific use cases
            
        Returns:
            List of best practice results
        """
        try:
            logger.info(f"Searching best practices for: {query}")
            
            # Enhance query for best practices
            bp_query = f"{query} best practices patterns guidelines"
            
            results = await self.search_documentation(
                bp_query,
                max_results=12,
                context=context
            )
            
            # Filter for best practice content
            bp_results = [
                result for result in results
                if any(keyword in result.get('content', '').lower() 
                      for keyword in ['best practice', 'pattern', 'guideline', 'recommend', 'standard'])
            ]
            
            return bp_results
            
        except Exception as e:
            logger.error(f"Error in best practices search: {e}")
            return []
    
    async def general_search(self, 
                           query: str, 
                           max_results: int = 10) -> List[Dict[str, Any]]:
        """
        General technical search across all available libraries
        
        Args:
            query: General technical query
            max_results: Maximum number of results
            
        Returns:
            List of technical results
        """
        try:
            logger.info(f"General technical search for: {query}")
            
            # Common technical libraries to search
            common_libraries = [
                'react', 'next.js', 'express', 'django', 'flask',
                'fastapi', 'numpy', 'pandas', 'scikit-learn', 'tensorflow',
                'pytorch', 'mongodb', 'postgresql', 'redis', 'docker'
            ]
            
            results = []
            
            for library in common_libraries:
                library_id = await self.resolve_library_id(library)
                if library_id:
                    docs = await self.get_library_docs(
                        library_id,
                        topic=query,
                        tokens=1000  # Smaller chunks for broad search
                    )
                    results.extend(docs)
            
            # Sort by relevance and limit results
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in general search: {e}")
            return []
    
    def _extract_library_names(self, query: str, context: Optional[Dict[str, Any]]) -> List[str]:
        """Extract library names from query and context"""
        libraries = []
        
        # Common library patterns
        library_patterns = [
            'react', r'next\.js', 'express', 'django', 'flask', 'fastapi',
            'numpy', 'pandas', 'scikit-learn', 'tensorflow', 'pytorch',
            'mongodb', 'postgresql', 'redis', 'supabase', 'prisma',
            'docker', 'kubernetes', 'terraform', 'ansible'
        ]
        
        query_lower = query.lower()
        
        # Check query for library names
        for pattern in library_patterns:
            import re
            if re.search(pattern.replace('.', r'\.'), query_lower):
                libraries.append(pattern)
        
        # Check context for library names
        if context and 'libraries' in context:
            libraries.extend(context['libraries'])
        
        # Check context for technology stack
        if context and 'tech_stack' in context:
            tech_stack = context['tech_stack']
            if isinstance(tech_stack, dict):
                for category, libs in tech_stack.items():
                    if isinstance(libs, list):
                        libraries.extend(libs)
                    elif isinstance(libs, str):
                        libraries.append(libs)
        
        return list(set(libraries))  # Remove duplicates
    
    def _enhance_troubleshooting_query(self, 
                                     query: str, 
                                     context: Optional[Dict[str, Any]]) -> str:
        """Enhance query with troubleshooting context"""
        enhanced_parts = [query]
        
        if context:
            # Add error context
            if 'error_message' in context:
                enhanced_parts.append(context['error_message'])
            
            # Add stack trace context
            if 'stack_trace' in context:
                enhanced_parts.append(context['stack_trace'])
            
            # Add version context
            if 'versions' in context:
                versions = context['versions']
                if isinstance(versions, dict):
                    for lib, version in versions.items():
                        enhanced_parts.append(f"{lib} {version}")
        
        # Add troubleshooting keywords
        enhanced_query = ' '.join(enhanced_parts)
        enhanced_query += " error fix solution troubleshooting"
        
        return enhanced_query
    
    def _general_technical_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback general technical search"""
        # This would typically use a broader search across technical documentation
        # For now, return mock results
        return [
            {
                'content': f"General technical documentation for: {query}",
                'score': 0.7,
                'metadata': {
                    'source': 'general_technical',
                    'type': 'documentation',
                    'confidence': 'medium'
                },
                'url': f"https://devdocs.io/search?q={query}"
            }
        ]