import asyncio
import httpx
import feedparser
import time
from datetime import datetime
from typing import Optional, List

from models import (
    ArxivAuthor,
    ArxivPaper,
    ArxivSearchResponse,
    ArxivFetchResponse,
)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_USER_AGENT = "mcp-web-server/0.1"


class ArxivTool:
    def __init__(
        self,
        max_results: int = 10,
        timeout: int = 30,
        min_request_interval: float = 3.0,
    ):
        self.max_results = max_results
        self.timeout = timeout
        self.min_request_interval = max(0.0, min_request_interval)
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        start: int = 0,
        max_results: Optional[int] = None,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> ArxivSearchResponse:

        search_query = self._build_query(
            query=query,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results or self.max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        try:
            response = await self._get(params)
        except httpx.HTTPStatusError as exc:
            return ArxivSearchResponse(
                query=query,
                category=category,
                start_date=start_date,
                end_date=end_date,
                results=[],
                total_results=0,
                success=False,
                error=self._http_error_message(exc),
            )
        except httpx.HTTPError as exc:
            return ArxivSearchResponse(
                query=query,
                category=category,
                start_date=start_date,
                end_date=end_date,
                results=[],
                total_results=0,
                success=False,
                error=self._request_error_message(exc),
            )

        try:
            feed = feedparser.parse(response.text)
            papers = [self._parse_entry(entry) for entry in feed.entries]
        except Exception as exc:
            return ArxivSearchResponse(
                query=query,
                category=category,
                start_date=start_date,
                end_date=end_date,
                results=[],
                total_results=0,
                success=False,
                error=f"Failed to parse arXiv response: {exc}",
            )

        return ArxivSearchResponse(
            query=query,
            category=category,
            start_date=start_date,
            end_date=end_date,
            results=papers,
            total_results=len(papers),
        )

    async def fetch(self, arxiv_id: str) -> ArxivFetchResponse:

        params = {"id_list": arxiv_id}

        try:
            response = await self._get(params)
        except httpx.HTTPStatusError as exc:
            return ArxivFetchResponse(
                arxiv_id=arxiv_id,
                paper=None,
                found=False,
                success=False,
                error=self._http_error_message(exc),
            )
        except httpx.HTTPError as exc:
            return ArxivFetchResponse(
                arxiv_id=arxiv_id,
                paper=None,
                found=False,
                success=False,
                error=self._request_error_message(exc),
            )

        try:
            feed = feedparser.parse(response.text)
        except Exception as exc:
            return ArxivFetchResponse(
                arxiv_id=arxiv_id,
                paper=None,
                found=False,
                success=False,
                error=f"Failed to parse arXiv response: {exc}",
            )

        if not feed.entries:
            return ArxivFetchResponse(
                arxiv_id=arxiv_id,
                paper=None,
                found=False,
            )

        try:
            paper = self._parse_entry(feed.entries[0])
        except Exception as exc:
            return ArxivFetchResponse(
                arxiv_id=arxiv_id,
                paper=None,
                found=False,
                success=False,
                error=f"Failed to parse arXiv paper: {exc}",
            )

        return ArxivFetchResponse(
            arxiv_id=arxiv_id,
            paper=paper,
            found=True,
        )

    async def _get(self, params: dict) -> httpx.Response:
        headers = {"User-Agent": ARXIV_USER_AGENT}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            for attempt in range(3):
                await self._wait_for_rate_limit()
                response = await client.get(ARXIV_API_URL, params=params)

                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response

                if attempt == 2:
                    response.raise_for_status()

                await asyncio.sleep(self._retry_delay(response, attempt))

        raise RuntimeError("unreachable")

    async def _wait_for_rate_limit(self) -> None:
        async with self._request_lock:
            elapsed = time.monotonic() - self._last_request_at
            wait_for = self.min_request_interval - elapsed
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_request_at = time.monotonic()

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                pass
        return min(self.min_request_interval * (attempt + 1), 10.0)

    def _http_error_message(self, exc: httpx.HTTPStatusError) -> str:
        status = exc.response.status_code
        if status == 429:
            return "arXiv rate limit reached; wait a bit and try again"
        return f"arXiv request failed with HTTP {status}"

    def _request_error_message(self, exc: httpx.HTTPError) -> str:
        detail = str(exc).strip()
        if detail:
            return f"arXiv request failed: {detail}"
        return f"arXiv request failed: {exc.__class__.__name__}"

    def _build_query(
        self,
        query: str,
        category: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> str:

        query_parts = [f'all:"{query}"']

        if category:
            query_parts.append(f"cat:{category}")

        if start_date or end_date:
            start_str = (
                start_date.strftime("%Y%m%d%H%M")
                if start_date
                else "000000000000"
            )
            end_str = (
                end_date.strftime("%Y%m%d%H%M")
                if end_date
                else datetime.now().strftime("%Y%m%d%H%M")
            )

            query_parts.append(f"submittedDate:[{start_str} TO {end_str}]")

        return " AND ".join(query_parts)


    def _parse_entry(self, entry) -> ArxivPaper:

        authors = [ArxivAuthor(name=a.name) for a in getattr(entry, "authors", [])]

        pdf_url = None
        for link in getattr(entry, "links", []):
            if getattr(link, "type", None) == "application/pdf":
                pdf_url = getattr(link, "href", None)
                break

        categories: List[str] = []
        if hasattr(entry, "tags"):
            categories = [tag["term"] for tag in entry.tags]

        return ArxivPaper(
            arxiv_id=getattr(entry, "id", "").split("/abs/")[-1],
            title=getattr(entry, "title", "").strip(),
            summary=getattr(entry, "summary", "").strip(),
            authors=authors,
            pdf_url=pdf_url,
            primary_category=categories[0] if categories else None,
            categories=categories,
            published=self._parse_datetime(getattr(entry, "published", None)),
            updated=self._parse_datetime(getattr(entry, "updated", None)),
        )

    def _parse_datetime(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.fromtimestamp(0)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
