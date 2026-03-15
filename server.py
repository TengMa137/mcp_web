import os
import logging
from datetime import datetime
from typing import Annotated

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP

from tools import WebSearchTool, CrawlerTool, ArxivTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Use Docker-safe port
PORT = int(os.environ.get("PORT", 8000))

# Initialize FastMCP
mcp = FastMCP(
    "mcp-web-server",
    host="0.0.0.0",
    port=PORT,
)

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request):
    return JSONResponse({"status": "ok"})

# Initialize tools
logger.info("Initializing tools...")
search_tool = WebSearchTool(max_results=10, timeout=30)
crawler_tool = CrawlerTool(timeout=60)
arxiv_tool = ArxivTool(max_results=10)
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
    max_results: Annotated[int, "Maximum number of results to return"] = 10,
) -> str:
    result = await search_tool.search(query=query, max_results=max_results)
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
Search the arXiv academic paper database.

Use this tool when:
• the topic involves scientific or technical research
• academic papers may provide authoritative information

Returns metadata including title, authors, abstract, and arXiv ID.
"""
)
async def search_arxiv(
    query: Annotated[str, "Search query for academic papers"],
    category: Annotated[str, "Optional arXiv category filter"] = None,
    start_date: Annotated[str, "Earliest publication date (ISO format)"] = None,
    end_date: Annotated[str, "Latest publication date (ISO format)"] = None,
    max_results: Annotated[int, "Maximum number of papers"] = 10,
) -> str:
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    result = await arxiv_tool.search(
        query=query,
        category=category,
        start_date=start_dt,
        end_date=end_dt,
    )
    return result.model_dump_json(indent=2)


@mcp.tool(
    description="""
Retrieve the full metadata and abstract of a specific arXiv paper.

Use this after search_arxiv when you want detailed information about a paper.
"""
)
async def fetch_arxiv(
    arxiv_id: Annotated[str, "The arXiv paper ID returned by search_arxiv"]
) -> str:
    result = await arxiv_tool.fetch(arxiv_id=arxiv_id)
    return result.model_dump_json(indent=2)


if __name__ == "__main__":
    logger.info(f"Starting MCP server on 0.0.0.0:{PORT}")
    mcp.run(transport="sse")
