"""
Web Searcher - Provides web search capabilities for general queries
"""

import asyncio
import logging
import aiohttp
from typing import Dict, List, Optional, Any
import json
import urllib.parse
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class WebSearcher:
    """Web search capabilities for general queries and information gathering"""
    
    def __init__(self, 
                 timeout: float = 30.0,
                 max_retries: int = 3,
                 user_agent: str = "Mozilla/5.0 (compatible; ResearchBot/1.0)"):
        """
        Initialize Web Searcher
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            user_agent: User agent string for requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={'User-Agent': self.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure we have an active session"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            )
    
    async def search(self, 
                   query: str, 
                   max_results: int = 10,
                   query_type: str = "general",
                   search_engine: str = "duckduckgo") -> List[Dict[str, Any]]:
        """
        Perform web search
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            query_type: Type of search ('general', 'technical', 'troubleshooting', 'tutorial')
            search_engine: Search engine to use ('duckduckgo', 'bing', 'google')
            
        Returns:
            List of search results with title, snippet, URL, and metadata
        """
        try:
            await self._ensure_session()
            
            # Enhance query based on type
            enhanced_query = self._enhance_query(query, query_type)
            
            logger.info(f"Web search: {enhanced_query} (type: {query_type})")
            
            # For now, we'll simulate web search results
            # In a real implementation, this would use actual search APIs
            results = await self._simulate_web_search(enhanced_query, max_results)
            
            # Post-process results
            processed_results = self._process_results(results, query_type)
            
            return processed_results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
    
    async def _simulate_web_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Simulate web search results (placeholder implementation)
        In a real implementation, this would use actual search APIs
        """
        # This is a simulation - replace with actual API calls
        mock_results = []
        
        # Generate mock results based on query content
        search_terms = query.lower().split()
        
        for i in range(max_results):
            mock_result = {
                'title': f"Result {i+1} for: {query}",
                'snippet': self._generate_snippet(query, i),
                'url': f"https://example.com/search-result-{i+1}",
                'display_url': f"example.com/search-result-{i+1}",
                'score': 1.0 - (i * 0.1),  # Decreasing relevance
                'date': datetime.now().isoformat(),
                'source': 'web_search',
                'metadata': {
                    'position': i + 1,
                    'type': 'web_result'
                }
            }
            mock_results.append(mock_result)
        
        return mock_results
    
    def _generate_snippet(self, query: str, index: int) -> str:
        """Generate a relevant snippet for mock results"""
        snippets = [
            f"Learn how to {query} with this comprehensive guide...",
            f"This article covers {query} in detail with examples...",
            f"Find solutions for {query} including common issues...",
            f"Step-by-step tutorial for implementing {query}...",
            f"Best practices for {query} based on real-world experience...",
            f"Complete documentation for {query} with code examples...",
            f"Common {query} problems and their solutions...",
            f"Advanced techniques for {query} optimization...",
            f"Getting started with {query} - beginner's guide...",
            f"Expert tips and tricks for {query} mastery..."
        ]
        
        return snippets[index % len(snippets)]
    
    def _enhance_query(self, query: str, query_type: str) -> str:
        """Enhance search query based on type"""
        enhanced = query
        
        if query_type == "technical":
            enhanced += " documentation tutorial guide"
        elif query_type == "troubleshooting":
            enhanced += " error fix solution problem issue"
        elif query_type == "tutorial":
            enhanced += " tutorial how to guide step by step"
        elif query_type == "best_practices":
            enhanced += " best practices patterns standards recommendations"
        
        return enhanced
    
    def _process_results(self, results: List[Dict[str, Any]], query_type: str) -> List[Dict[str, Any]]:
        """Process and filter search results"""
        processed = []
        
        for result in results:
            # Clean and validate result
            processed_result = {
                'title': self._clean_text(result.get('title', '')),
                'snippet': self._clean_text(result.get('snippet', '')),
                'url': result.get('url', ''),
                'display_url': self._clean_display_url(result.get('display_url', result.get('url', ''))),
                'score': self._calculate_relevance_score(result, query_type),
                'date': result.get('date', datetime.now().isoformat()),
                'metadata': {
                    'source': 'web_search',
                    'type': self._classify_result_type(result),
                    'confidence': result.get('score', 0.8)
                }
            }
            
            processed.append(processed_result)
        
        # Sort by relevance score
        processed.sort(key=lambda x: x['score'], reverse=True)
        
        return processed
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Limit length
        if len(text) > 300:
            text = text[:297] + "..."
        
        return text
    
    def _clean_display_url(self, url: str) -> str:
        """Clean and format display URL"""
        if not url:
            return ""
        
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        
        # Remove www
        url = re.sub(r'^www\.', '', url)
        
        # Limit length
        if len(url) > 50:
            url = url[:47] + "..."
        
        return url
    
    def _calculate_relevance_score(self, result: Dict[str, Any], query_type: str) -> float:
        """Calculate relevance score for a result"""
        base_score = result.get('score', 0.5)
        
        # Boost scores based on content quality indicators
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        # Technical content boost
        if query_type == "technical":
            technical_keywords = ['documentation', 'guide', 'tutorial', 'api', 'reference']
            for keyword in technical_keywords:
                if keyword in title or keyword in snippet:
                    base_score += 0.1
        
        # Tutorial content boost
        elif query_type == "tutorial":
            tutorial_keywords = ['tutorial', 'how to', 'guide', 'step by step', 'learn']
            for keyword in tutorial_keywords:
                if keyword in title or keyword in snippet:
                    base_score += 0.1
        
        # Troubleshooting boost
        elif query_type == "troubleshooting":
            troubleshoot_keywords = ['fix', 'error', 'solution', 'problem', 'issue', 'debug']
            for keyword in troubleshoot_keywords:
                if keyword in title or keyword in snippet:
                    base_score += 0.1
        
        # Best practices boost
        elif query_type == "best_practices":
            bp_keywords = ['best practice', 'pattern', 'standard', 'recommend', 'guideline']
            for keyword in bp_keywords:
                if keyword in title or keyword in snippet:
                    base_score += 0.1
        
        return min(base_score, 1.0)  # Cap at 1.0
    
    def _classify_result_type(self, result: Dict[str, Any]) -> str:
        """Classify the type of search result"""
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        url = result.get('url', '').lower()
        
        # Check for documentation
        if any(keyword in url for keyword in ['docs', 'documentation', 'api']):
            return 'documentation'
        
        # Check for tutorials
        if any(keyword in title + snippet for keyword in ['tutorial', 'how to', 'guide']):
            return 'tutorial'
        
        # Check for forums/discussions
        if any(keyword in url for keyword in ['stackoverflow', 'github', 'reddit', 'forum']):
            return 'discussion'
        
        # Check for blogs/articles
        if any(keyword in url for keyword in ['blog', 'medium', 'dev.to']):
            return 'article'
        
        return 'general'
    
    async def search_stack_overflow(self, 
                                  query: str, 
                                  max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search Stack Overflow for programming questions
        
        Args:
            query: Programming question or error
            max_results: Maximum number of results
            
        Returns:
            List of Stack Overflow results
        """
        try:
            enhanced_query = f"site:stackoverflow.com {query}"
            results = await self.search(enhanced_query, max_results, "troubleshooting")
            
            # Mark results as Stack Overflow
            for result in results:
                result['metadata']['source'] = 'stackoverflow'
                result['metadata']['type'] = 'qa'
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Stack Overflow: {e}")
            return []
    
    async def search_github(self, 
                          query: str, 
                          max_results: int = 5,
                          search_type: str = "repositories") -> List[Dict[str, Any]]:
        """
        Search GitHub for repositories, issues, or discussions
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_type: Type of search ('repositories', 'issues', 'discussions')
            
        Returns:
            List of GitHub results
        """
        try:
            enhanced_query = f"site:github.com {query}"
            
            if search_type == "issues":
                enhanced_query += " is:issue"
            elif search_type == "discussions":
                enhanced_query += " discussions"
            
            results = await self.search(enhanced_query, max_results, "technical")
            
            # Mark results as GitHub
            for result in results:
                result['metadata']['source'] = 'github'
                result['metadata']['type'] = search_type
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
            return []
    
    async def search_documentation(self, 
                                 query: str, 
                                 max_results: int = 5,
                                 docs_sites: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search specific documentation sites
        
        Args:
            query: Search query
            max_results: Maximum number of results
            docs_sites: List of documentation sites to search
            
        Returns:
            List of documentation results
        """
        try:
            if not docs_sites:
                docs_sites = [
                    'developer.mozilla.org',
                    'docs.python.org',
                    'nodejs.org',
                    'react.dev',
                    'vuejs.org',
                    'angular.io'
                ]
            
            results = []
            
            for site in docs_sites:
                site_query = f"site:{site} {query}"
                site_results = await self.search(site_query, max_results, "technical")
                
                # Mark results with source
                for result in site_results:
                    result['metadata']['source'] = 'documentation'
                    result['metadata']['docs_site'] = site
                
                results.extend(site_results)
            
            # Sort by relevance
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching documentation: {e}")
            return []
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()