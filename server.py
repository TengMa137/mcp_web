import logging
from typing import Annotated, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP

from tools import ArxivTool, CrawlerTool, NewsTool, WeatherTool, WebSearchTool, WikiTool

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP(
    "mcp-web-server",
    host=settings.host,
    port=settings.port,
)

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request):
    return JSONResponse({"status": "ok"})

# Initialize tools
logger.info("Initializing tools...")
search_tool = WebSearchTool(max_results=settings.max_search_results, timeout=settings.search_timeout)
crawler_tool = CrawlerTool(
    timeout=settings.crawler_timeout,
    max_batch_urls=settings.crawler_max_batch_urls,
    max_concurrency=settings.crawler_max_concurrency,
    word_count_threshold=settings.crawler_word_count_threshold,
    exclude_external_links=settings.crawler_exclude_external_links,
    remove_overlay_elements=settings.crawler_remove_overlay_elements,
    allow_private_hosts=settings.crawler_allow_private_hosts,
)
arxiv_tool = ArxivTool(
    timeout=settings.arxiv_fetch_timeout,
    min_request_interval=settings.arxiv_min_request_interval,
)
weather_tool = WeatherTool(
    timeout=settings.weather_timeout,
    max_forecast_days=settings.weather_max_forecast_days,
    user_agent=settings.api_user_agent,
)
wiki_tool = WikiTool(
    timeout=settings.wiki_timeout,
    default_language=settings.wiki_default_language,
    user_agent=settings.api_user_agent,
)
news_tool = NewsTool(
    timeout=settings.news_timeout,
    max_results=settings.news_max_results,
    default_timespan=settings.news_default_timespan,
    user_agent=settings.api_user_agent,
)
logger.info("Tools initialized.")


@mcp.tool(
    description="""
Search the public internet for relevant pages.

Use this tool to DISCOVER sources when you do not yet know URLs.

Typical workflow:
1. Call search_web to find relevant pages
2. Call crawl_url or crawl_urls to retrieve full content

Avoid calling search_web repeatedly with small query variations.
If you already have relevant URLs, call crawl_url instead.
"""
)
async def search_web(
    query: Annotated[str, "Search query describing the information needed"],
    max_results: Annotated[Optional[int], "Maximum number of results to return"] = None,
) -> str:
    result = await search_tool.search(
        query=query,
        max_results=_bounded_max_results(max_results, settings.max_search_results),
    )
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Get a weather forecast from the free Open-Meteo API.

Use this before generic web search for weather questions such as current conditions,
today, tomorrow, or an exact near-future date.

Pass an exact ISO date as YYYY-MM-DD when the user asks a relative date.
If date is omitted, the tool uses today's date in the resolved location timezone.
"""
)
async def weather_forecast(
    location: Annotated[str, "Location name, optionally with country or region"],
    date: Annotated[Optional[str], "Forecast date as YYYY-MM-DD"] = None,
) -> str:
    result = await weather_tool.forecast(location=location, forecast_date=date)
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Get a concise encyclopedic overview from Wikipedia's free public APIs.

Use this before generic web search for definitions, entity background, and stable
overview questions. Do not use it for breaking news, prices, schedules, or facts
that need current source verification.
"""
)
async def wiki_summary(
    query: Annotated[str, "Topic, concept, person, place, organization, or title"],
    language: Annotated[Optional[str], "Wikipedia language code, defaults to server config"] = None,
) -> str:
    result = await wiki_tool.summary(query=query, language=language)
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Search recent global news articles through the free GDELT DOC 2.0 API.

Use this before generic web search for news, politics, and current-event discovery.
It returns article titles, URLs, domains, countries, languages, and seen dates.
If those previews answer the question, do not crawl the articles.
"""
)
async def news_search(
    query: Annotated[str, "News query; GDELT supports quoted phrases and OR operators"],
    max_results: Annotated[Optional[int], "Maximum number of articles to return"] = None,
    timespan: Annotated[
        Optional[str],
        "Recent window such as 24h, 1day, 1week, or 1month",
    ] = None,
) -> str:
    result = await news_tool.search(
        query=query,
        max_results=_bounded_max_results(max_results, settings.news_max_results),
        timespan=timespan,
    )
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Download and extract readable content from a single webpage.

Use this when:
• you already know the exact URL
• you want the full page content

Do NOT use this tool to discover new sources.
Use search_web first if you need URLs.
"""
)
async def crawl_url(
    url: Annotated[str, "The full URL of the webpage to download"]
) -> str:
    result = await crawler_tool.crawl_url(url=url)
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Download and extract content from multiple webpages.

Use this when you have several URLs from search_web and want to retrieve them efficiently.
"""
)
async def crawl_urls(
    urls: Annotated[list[str], "List of URLs to download"]
) -> str:
    result = await crawler_tool.crawl_urls(urls=urls)
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Retrieve the full metadata and abstract of a specific arXiv paper by ID.

Use normal web search scoped to arxiv.org/abs to discover paper IDs, then call this tool.
"""
)
async def fetch_arxiv(
    arxiv_id: Annotated[str, "The arXiv paper ID to fetch, e.g. 2605.06548"]
) -> str:
    result = await arxiv_tool.fetch(arxiv_id=arxiv_id)
    return result.model_dump_json(indent=2)


def _bounded_max_results(value: Optional[int], default: int) -> int:
    if value is None:
        return default
    if value < 1:
        raise ValueError("max_results must be at least 1")
    return min(value, default)


if __name__ == "__main__":
    logger.info(f"Starting MCP server on {settings.host}:{settings.port}")
    mcp.run(transport="sse")
