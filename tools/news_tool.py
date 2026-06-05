"""News search tool using the free GDELT DOC 2.0 API."""

import logging
from typing import Optional

import httpx

from models import NewsArticle, NewsSearchResponse

logger = logging.getLogger(__name__)


class NewsTool:
    """Tool for searching recent global news coverage."""

    doc_api_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(
        self,
        timeout: int = 20,
        max_results: int = 25,
        default_timespan: str = "1d",
        user_agent: str = "mcp-web-server/0.1",
    ):
        self.timeout = timeout
        self.max_results = max(1, min(max_results, 250))
        self.default_timespan = self._normalize_timespan(default_timespan)
        self.headers = {"User-Agent": user_agent}

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        timespan: Optional[str] = None,
    ) -> NewsSearchResponse:
        query = query.strip()
        if not query:
            return self._error(
                query,
                timespan or self.default_timespan,
                "query must not be empty",
            )

        record_count = max_results or self.max_results
        record_count = max(1, min(record_count, self.max_results))
        normalized_timespan = self._normalize_timespan(timespan or self.default_timespan)

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "sort": "datedesc",
            "maxrecords": record_count,
            "timespan": normalized_timespan,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            ) as client:
                response = await client.get(self.doc_api_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            return self._error(
                query,
                normalized_timespan,
                f"GDELT request failed with HTTP {exc.response.status_code}",
            )
        except httpx.HTTPError as exc:
            return self._error(
                query,
                normalized_timespan,
                f"GDELT request failed: {exc.__class__.__name__}",
            )

        articles = [
            self._parse_article(article)
            for article in payload.get("articles", [])
            if article.get("title") and article.get("url")
        ]

        return NewsSearchResponse(
            query=query,
            timespan=normalized_timespan,
            articles=articles,
            total_results=len(articles),
        )

    def _parse_article(self, article: dict) -> NewsArticle:
        return NewsArticle(
            title=article.get("title", "").strip(),
            url=article.get("url", "").strip(),
            domain=article.get("domain"),
            language=article.get("language"),
            source_country=article.get("sourcecountry"),
            seen_at=article.get("seendate"),
            image_url=article.get("socialimage"),
        )

    def _normalize_timespan(self, value: str) -> str:
        value = value.strip().lower()
        if not value:
            return "1d"

        units = [
            ("minutes", "min", 31 * 3 * 24 * 60),
            ("minute", "min", 31 * 3 * 24 * 60),
            ("min", "min", 31 * 3 * 24 * 60),
            ("hours", "h", 31 * 3 * 24),
            ("hour", "h", 31 * 3 * 24),
            ("h", "h", 31 * 3 * 24),
            ("days", "d", 31 * 3),
            ("day", "d", 31 * 3),
            ("d", "d", 31 * 3),
            ("weeks", "week", 13),
            ("week", "week", 13),
            ("w", "week", 13),
            ("months", "month", 3),
            ("month", "month", 3),
        ]
        for suffix, unit, maximum in units:
            if not value.endswith(suffix):
                continue
            amount_text = value[: -len(suffix)].strip()
            if amount_text.isdigit():
                amount = max(1, min(int(amount_text), maximum))
                if unit == "min":
                    amount = max(15, amount)
                return f"{amount}{unit}"

        if value.isdigit():
            return f"{max(15, min(int(value), 31 * 3 * 24 * 60))}min"

        logger.warning("Invalid GDELT timespan '%s', using 1d", value)
        return "1d"

    def _error(self, query: str, timespan: str, error: str) -> NewsSearchResponse:
        return NewsSearchResponse(
            query=query,
            timespan=timespan,
            articles=[],
            total_results=0,
            success=False,
            error=error,
        )
