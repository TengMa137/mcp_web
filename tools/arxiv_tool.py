import httpx
import feedparser
from datetime import datetime
from typing import Optional, List

from models import (
    ArxivAuthor,
    ArxivPaper,
    ArxivSearchResponse,
    ArxivFetchResponse,
)

ARXIV_API_URL = "https://export.arxiv.org/api/query"


class ArxivTool:
    def __init__(self, max_results: int = 10, timeout: int = 30):
        self.max_results = max_results
        self.timeout = timeout

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        start: int = 0,
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
            "max_results": self.max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        papers = [self._parse_entry(entry) for entry in feed.entries]

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

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        if not feed.entries:
            return ArxivFetchResponse(
                arxiv_id=arxiv_id,
                paper=None,
                found=False,
            )

        paper = self._parse_entry(feed.entries[0])

        return ArxivFetchResponse(
            arxiv_id=arxiv_id,
            paper=paper,
            found=True,
        )

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

        authors = [ArxivAuthor(name=a.name) for a in entry.authors]

        pdf_url = None
        for link in entry.links:
            if link.type == "application/pdf":
                pdf_url = link.href
                break

        categories: List[str] = []
        if hasattr(entry, "tags"):
            categories = [tag["term"] for tag in entry.tags]

        return ArxivPaper(
            arxiv_id=entry.id.split("/abs/")[-1],
            title=entry.title.strip(),
            summary=entry.summary.strip(),
            authors=authors,
            pdf_url=pdf_url,
            primary_category=categories[0] if categories else None,
            categories=categories,
            published=datetime.fromisoformat(entry.published.replace("Z", "+00:00")),
            updated=datetime.fromisoformat(entry.updated.replace("Z", "+00:00")),
        )
