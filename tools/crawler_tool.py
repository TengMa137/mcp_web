"""Web crawler tool using Crawl4AI."""

import asyncio
from typing import List
import logging
from crawl4ai import AsyncWebCrawler

from models import CrawledContent, CrawlResponse, BatchCrawlResponse

logger = logging.getLogger(__name__)


class CrawlerTool:
    """Tool for crawling web pages."""
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
    
    async def crawl_url(self, url: str) -> CrawlResponse:
        """Crawl a single URL and return structured content.
        
        Args:
            url: URL to crawl
            
        Returns:
            CrawlResponse with structured content
        """
        content = await self._fetch_url(url)
        
        return CrawlResponse(
            url=url,
            content=content
        )
    
    async def crawl_urls(self, urls: List[str]) -> BatchCrawlResponse:
        """Crawl multiple URLs concurrently.
        
        Args:
            urls: List of URLs to crawl
            
        Returns:
            BatchCrawlResponse with all results
        """
        tasks = [self._fetch_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    CrawledContent(
                        url=urls[i],
                        success=False,
                        error=str(result)
                    )
                )
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - successful
        
        return BatchCrawlResponse(
            urls=urls,
            results=processed_results,
            successful=successful,
            failed=failed
        )
    
    async def _fetch_url(self, url: str) -> CrawledContent:
        """Fetch and extract content from a URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            CrawledContent with structured data
        """
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    timeout=self.timeout
                )
                
                if not result.success:
                    return CrawledContent(
                        url=url,
                        success=False,
                        error=result.error_message or "Unknown error"
                    )
                
                return CrawledContent(
                    url=url,
                    success=True,
                    title=result.metadata.get("title", "") if result.metadata else "",
                    markdown=result.markdown or "",
                    text=result.extracted_content or "",
                    html=result.html or "",
                    links=result.links
                )
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout crawling {url}")
            return CrawledContent(
                url=url,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawledContent(
                url=url,
                success=False,
                error=str(e)
            )
