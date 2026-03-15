"""Web search tool using DuckDuckGo."""

import asyncio
from typing import List
from ddgs import DDGS
import logging

from models import SearchResult, WebSearchResponse

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Tool for searching the web."""
    
    def __init__(self, max_results: int = 10, timeout: int = 30):
        self.max_results = max_results
        self.timeout = timeout
    
    async def search(self, query: str, max_results: int = None) -> WebSearchResponse:
        """Search the web and return structured results.
        
        Args:
            query: Search query
            max_results: Max results to return (overrides default)
            
        Returns:
            WebSearchResponse with structured results
        """
        max_results = max_results or self.max_results
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                query,
                max_results
            )
            
            search_results = [
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    snippet=r["snippet"],
                    position=i + 1
                )
                for i, r in enumerate(results)
            ]
            
            return WebSearchResponse(
                query=query,
                results=search_results,
                total_results=len(search_results)
            )
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise
    
    def _search_sync(self, query: str, max_results: int) -> List[dict]:
        """Synchronous search implementation."""
        with DDGS() as ddgs:
            results = []
            
            search_results = ddgs.text(
                query=query,
                max_results=max_results
            )
            
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                })
            
            logger.info(f"Found {len(results)} results for query: {query}")
            return results
