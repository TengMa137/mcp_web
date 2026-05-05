"""Web crawler tool using Crawl4AI."""

import asyncio
import ipaddress
from typing import List
import logging
from urllib.parse import urlparse

from models import CrawledContent, CrawlResponse, BatchCrawlResponse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

logger = logging.getLogger(__name__)


class CrawlerTool:
    """Tool for crawling web pages."""
    
    def __init__(
        self, 
        timeout: int = 60,
        max_batch_urls: int = 10,
        max_concurrency: int = 4,
        word_count_threshold: int = 1000,
        exclude_external_links: bool = True,
        remove_overlay_elements: bool = True,
        allow_private_hosts: bool = False,
    ):
        self.timeout = timeout
        self.max_batch_urls = max_batch_urls
        self.allow_private_hosts = allow_private_hosts
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self.config = CrawlerRunConfig(
                word_count_threshold=word_count_threshold,
                excluded_tags=["nav", "header", "footer", "aside", "script", "style"],
                exclude_external_links=exclude_external_links,
                remove_overlay_elements=remove_overlay_elements,
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(
                        threshold=0.45,
                        threshold_type="dynamic",  # adapts per page, better than fixed
                        min_word_threshold=5,
                    ),
                    options={"ignore_links": True, "ignore_images": True},
                ),
            )
    
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
        if len(urls) > self.max_batch_urls:
            raise ValueError(f"Too many URLs: max {self.max_batch_urls}")

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
            self._validate_url(url)
            config = self.config

            async with self._semaphore:
                async with AsyncWebCrawler(verbose=False) as crawler:
                    result = await asyncio.wait_for(
                        crawler.arun(url=url, config=config),
                        timeout=self.timeout,
                    )

            if not result.success:
                return CrawledContent(
                    url=url,
                    success=False,
                    error=result.error_message or "Unknown error"
                )

            md = result.markdown
            markdown = ""
            if md:
                # fit_markdown is populated because we passed a PruningContentFilter
                markdown = md.fit_markdown or md.raw_markdown or ""

            return CrawledContent(
                url=url,
                success=True,
                title=result.metadata.get("title", "") if result.metadata else "",
                markdown=markdown,
                text=markdown,
                links=self._normalize_links(getattr(result, "links", None)),
            )

        except asyncio.TimeoutError:
            return CrawledContent(url=url, success=False, error="Request timeout")
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawledContent(url=url, success=False, error=str(e))

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")
        if not parsed.hostname:
            raise ValueError("URL must include a hostname")
        if self.allow_private_hosts:
            return

        host = parsed.hostname.strip().lower()
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None

        if ip:
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise ValueError("Private and localhost URLs are disabled")
            return

        blocked_hosts = {"localhost", "host.docker.internal", "gateway.docker.internal"}
        if host in blocked_hosts or host.endswith(".localhost") or "." not in host:
            raise ValueError("Private and localhost URLs are disabled")

    def _normalize_links(self, links) -> dict:
        if not isinstance(links, dict):
            return {"internal": [], "external": []}

        normalized = {}
        for key, value in links.items():
            normalized[key] = value if isinstance(value, list) else []

        normalized.setdefault("internal", [])
        normalized.setdefault("external", [])
        return normalized
