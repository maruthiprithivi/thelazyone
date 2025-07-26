"""
Research Engine - Coordinates research activities across different sources
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json

from .context7_integration import Context7Integration
from .web_searcher import WebSearcher

logger = logging.getLogger(__name__)

@dataclass
class ResearchQuery:
    """Represents a research query with metadata"""
    query: str
    query_type: str  # 'technical', 'general', 'troubleshooting', 'best_practices'
    context: Optional[Dict[str, Any]] = None
    max_results: int = 10
    priority: str = "medium"  # 'high', 'medium', 'low'
    timeout: float = 30.0

@dataclass
class ResearchResult:
    """Represents a research result"""
    source: str  # 'context7', 'web_search', 'cached'
    content: str
    relevance_score: float
    metadata: Dict[str, Any]
    timestamp: datetime
    url: Optional[str] = None

class CacheEntry:
    """Cache entry with TTL support"""
    def __init__(self, data: Any, ttl_minutes: int = 60):
        self.data = data
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

class RateLimiter:
    """Simple rate limiter for API calls"""
    def __init__(self, max_calls: int = 10, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []
    
    def can_make_request(self) -> bool:
        now = time.time()
        self.calls = [call_time for call_time in self.calls if now - call_time < self.window_seconds]
        return len(self.calls) < self.max_calls
    
    def record_request(self):
        self.calls.append(time.time())

class ResearchEngine:
    """Main research engine that coordinates between different research sources"""
    
    def __init__(self, 
                 cache_ttl_minutes: int = 60,
                 rate_limit_max_calls: int = 10,
                 rate_limit_window_seconds: int = 60):
        """
        Initialize the Research Engine
        
        Args:
            cache_ttl_minutes: Cache time-to-live in minutes
            rate_limit_max_calls: Maximum API calls per window
            rate_limit_window_seconds: Rate limit window in seconds
        """
        self.context7 = Context7Integration()
        self.web_searcher = WebSearcher()
        
        # Cache management
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl_minutes = cache_ttl_minutes
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_calls=rate_limit_max_calls,
            window_seconds=rate_limit_window_seconds
        )
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'rate_limit_hits': 0,
            'errors': 0
        }
    
    def _generate_cache_key(self, query: ResearchQuery) -> str:
        """Generate a cache key for a query"""
        key_data = {
            'query': query.query,
            'type': query.query_type,
            'max_results': query.max_results
        }
        if query.context:
            key_data['context'] = query.context
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[ResearchResult]]:
        """Get cached results if available and not expired"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                self.stats['cache_hits'] += 1
                return entry.data
            else:
                del self.cache[cache_key]
        
        self.stats['cache_misses'] += 1
        return None
    
    def _cache_results(self, cache_key: str, results: List[ResearchResult]):
        """Cache research results"""
        self.cache[cache_key] = CacheEntry(results, self.cache_ttl_minutes)
    
    async def _execute_context7_search(self, query: ResearchQuery) -> List[ResearchResult]:
        """Execute search using Context7 for technical documentation"""
        try:
            if not self.rate_limiter.can_make_request():
                self.stats['rate_limit_hits'] += 1
                logger.warning("Rate limit reached for Context7 API")
                return []
            
            self.rate_limiter.record_request()
            
            # Determine search strategy based on query type
            if query.query_type == 'technical':
                docs = await self.context7.search_documentation(
                    query.query,
                    max_results=query.max_results,
                    context=query.context
                )
            elif query.query_type == 'troubleshooting':
                docs = await self.context7.search_troubleshooting(
                    query.query,
                    context=query.context
                )
            elif query.query_type == 'best_practices':
                docs = await self.context7.search_best_practices(
                    query.query,
                    context=query.context
                )
            else:
                docs = await self.context7.general_search(
                    query.query,
                    max_results=query.max_results
                )
            
            return [
                ResearchResult(
                    source='context7',
                    content=doc.get('content', ''),
                    relevance_score=doc.get('score', 0.0),
                    metadata=doc.get('metadata', {}),
                    timestamp=datetime.now(),
                    url=doc.get('url')
                )
                for doc in docs
            ]
            
        except Exception as e:
            logger.error(f"Error in Context7 search: {e}")
            self.stats['errors'] += 1
            return []
    
    async def _execute_web_search(self, query: ResearchQuery) -> List[ResearchResult]:
        """Execute web search for general queries"""
        try:
            if not self.rate_limiter.can_make_request():
                self.stats['rate_limit_hits'] += 1
                logger.warning("Rate limit reached for web search")
                return []
            
            self.rate_limiter.record_request()
            
            search_results = await self.web_searcher.search(
                query.query,
                max_results=query.max_results,
                query_type=query.query_type
            )
            
            return [
                ResearchResult(
                    source='web_search',
                    content=result.get('snippet', ''),
                    relevance_score=result.get('score', 0.0),
                    metadata={
                        'title': result.get('title', ''),
                        'source_url': result.get('url', ''),
                        **result.get('metadata', {})
                    },
                    timestamp=datetime.now(),
                    url=result.get('url')
                )
                for result in search_results
            ]
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            self.stats['errors'] += 1
            return []
    
    async def research(self, query: ResearchQuery) -> List[ResearchResult]:
        """
        Main research method that coordinates between different sources
        
        Args:
            query: ResearchQuery object with search parameters
            
        Returns:
            List of ResearchResult objects sorted by relevance
        """
        self.stats['total_queries'] += 1
        logger.info(f"Starting research for query: {query.query} (type: {query.query_type})")
        
        # Check cache first
        cache_key = self._generate_cache_key(query)
        cached_results = self._get_from_cache(cache_key)
        if cached_results is not None:
            logger.info(f"Cache hit for query: {query.query}")
            return cached_results
        
        # Determine search strategy based on query type
        all_results = []
        
        # Technical queries should prioritize Context7
        if query.query_type in ['technical', 'troubleshooting', 'best_practices']:
            context7_results = await self._execute_context7_search(query)
            all_results.extend(context7_results)
            
            # If we need more results, supplement with web search
            if len(all_results) < query.max_results:
                remaining = query.max_results - len(all_results)
                web_query = ResearchQuery(
                    query=query.query,
                    query_type=query.query_type,
                    max_results=remaining,
                    context=query.context
                )
                web_results = await self._execute_web_search(web_query)
                all_results.extend(web_results)
        
        # General queries should prioritize web search
        elif query.query_type == 'general':
            web_results = await self._execute_web_search(query)
            all_results.extend(web_results)
            
            # If we need more results, supplement with Context7
            if len(all_results) < query.max_results:
                remaining = query.max_results - len(all_results)
                context7_query = ResearchQuery(
                    query=query.query,
                    query_type='technical',  # Try technical search for context
                    max_results=remaining,
                    context=query.context
                )
                context7_results = await self._execute_context7_search(context7_query)
                all_results.extend(context7_results)
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to max_results
        final_results = all_results[:query.max_results]
        
        # Cache results
        self._cache_results(cache_key, final_results)
        
        logger.info(f"Research completed. Found {len(final_results)} results")
        return final_results
    
    async def research_batch(self, queries: List[ResearchQuery]) -> Dict[str, List[ResearchResult]]:
        """
 Execute multiple research queries in parallel
        
        Args:
            queries: List of ResearchQuery objects
            
        Returns:
            Dictionary mapping query strings to their results
        """
        logger.info(f"Starting batch research for {len(queries)} queries")
        
        tasks = [self.research(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and map results
        final_results = {}
        for query, result in zip(queries, results):
            if isinstance(result, Exception):
                logger.error(f"Error processing query {query.query}: {result}")
                final_results[query.query] = []
            else:
                final_results[query.query] = result
        
        return final_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get research engine statistics"""
        return {
            **self.stats,
            'cache_size': len(self.cache),
            'rate_limiter_calls_in_window': len(self.rate_limiter.calls)
        }
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        logger.info("Research cache cleared")
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")