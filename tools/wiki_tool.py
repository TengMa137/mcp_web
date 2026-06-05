"""Wikipedia summary tool using free public APIs."""

import logging
import re
from typing import Optional
from urllib.parse import quote

import httpx

from models import WikiSummaryResponse

logger = logging.getLogger(__name__)


class WikiTool:
    """Tool for short encyclopedic summaries from Wikipedia."""

    def __init__(
        self,
        timeout: int = 20,
        default_language: str = "en",
        user_agent: str = "mcp-web-server/0.1",
    ):
        self.timeout = timeout
        self.default_language = self._normalize_language(default_language)
        self.headers = {"User-Agent": user_agent}

    async def summary(
        self,
        query: str,
        language: Optional[str] = None,
    ) -> WikiSummaryResponse:
        query = query.strip()
        if not query:
            return self._error(
                query,
                language or self.default_language,
                "query must not be empty",
            )

        lang = self._normalize_language(language or self.default_language)

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            ) as client:
                title = await self._search_title(client, query, lang)
                if title is None:
                    return self._error(query, lang, "no Wikipedia page found")

                response = await client.get(self._summary_url(title, lang))
                if response.status_code == 404:
                    return self._error(query, lang, "Wikipedia summary not found")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            return self._error(
                query,
                lang,
                f"Wikipedia request failed with HTTP {exc.response.status_code}",
            )
        except httpx.HTTPError as exc:
            return self._error(
                query,
                lang,
                f"Wikipedia request failed: {exc.__class__.__name__}",
            )

        thumbnail = payload.get("thumbnail") or {}
        content_urls = payload.get("content_urls") or {}
        desktop_urls = content_urls.get("desktop") or {}

        return WikiSummaryResponse(
            query=query,
            language=lang,
            title=payload.get("title") or title,
            description=payload.get("description"),
            extract=payload.get("extract"),
            page_url=desktop_urls.get("page") or payload.get("canonicalurl"),
            thumbnail_url=thumbnail.get("source"),
        )

    async def _search_title(
        self,
        client: httpx.AsyncClient,
        query: str,
        language: str,
    ) -> Optional[str]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 1,
            "format": "json",
            "utf8": 1,
        }
        response = await client.get(self._api_url(language), params=params)
        response.raise_for_status()

        results = response.json().get("query", {}).get("search", [])
        if not results:
            return None
        return results[0].get("title")

    def _api_url(self, language: str) -> str:
        return f"https://{language}.wikipedia.org/w/api.php"

    def _summary_url(self, title: str, language: str) -> str:
        title_path = quote(title, safe="")
        return f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{title_path}"

    def _normalize_language(self, language: str) -> str:
        language = language.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,11}", language):
            logger.warning("Invalid Wikipedia language code '%s', using en", language)
            return "en"
        return language

    def _error(self, query: str, language: str, error: str) -> WikiSummaryResponse:
        return WikiSummaryResponse(
            query=query,
            language=language,
            success=False,
            error=error,
        )
