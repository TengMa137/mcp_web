"""Web crawler tool using Crawl4AI."""

import asyncio
from typing import List
import logging

from models import CrawledContent, CrawlResponse, BatchCrawlResponse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

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
        try:
            config = CrawlerRunConfig(
                word_count_threshold=1000,
                excluded_tags=["nav", "header", "footer", "aside", "script", "style"],
                exclude_external_links=True,
                remove_overlay_elements=True,
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(
                        threshold=0.45,
                        threshold_type="dynamic",  # adapts per page, better than fixed
                        min_word_threshold=5,
                    ),
                    options={"ignore_links": True, "ignore_images": True},
                ),
            )

            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url, config=config)

            if not result.success:
                return CrawledContent(
                    url=url,
                    success=False,
                    error=result.error_message or "Unknown error"
                )

            md = result.markdown
            text = ""
            if md:
                # fit_markdown is populated because we passed a PruningContentFilter
                text = md.fit_markdown or md.raw_markdown or ""

            return CrawledContent(
                url=url,
                success=True,
                title=result.metadata.get("title", "") if result.metadata else "",
                text=text,
            )

        except asyncio.TimeoutError:
            return CrawledContent(url=url, success=False, error="Request timeout")
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawledContent(url=url, success=False, error=str(e))
        