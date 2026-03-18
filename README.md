# MCP Server - Modular Design with Structured Responses

This is a **clean, modular implementation** with:
-   Separate tools (not bundled together)
-   Structured responses (Pydantic models)
-   Type safety and validation
-   Works across Docker containers (SSE transport)
-   Uses official MCP SDK
-   Easy to extend
-   Not over-engineered

## Key Features

  **Separate Tools**: Each tool is independent and focused
- `search_web` - Web search with DuckDuckGo
- `crawl_url` - Single URL crawling
- `crawl_urls` - Batch URL crawling

  **Structured Responses**: All responses use Pydantic models
- Type-safe and validated
- Easy to parse and use
- JSON serializable

  **Modular Code**: Clean separation of concerns
- `models.py` - Pydantic response models
- `tools/search_tool.py` - Web search implementation
- `tools/crawler_tool.py` - Crawler implementation
- `server.py` - MCP server with SSE transport

  **No Over-Engineering**: Simple, straightforward design

## Project Structure

```
mcp/
├── models.py              # Pydantic models for responses
├── config/                # Pydantic settings
├── tools/
│   ├── search_tool.py     # WebSearchTool
│   ├── crawler_tool.py    # CrawlerTool
│   └── arxiv_tool.py      # arXivTool
├── server.py              # MCP server (SSE transport)
├── client.py              # Test client
├── requirements.txt       # Dependencies
├── Dockerfile             # Container setup
└── docker-compose.yml     # Multi-container setup
```

## Response Models

### WebSearchResponse
```python
{
  "query": "Python async",
  "results": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "...",
      "position": 1
    }
  ],
  "total_results": 5,
  "timestamp": "2024-..."
}
```

### CrawlResponse
```python
{
  "url": "https://example.com",
  "content": {
    "url": "https://example.com",
    "success": true,
    "title": "Example Domain",
    "markdown": "# Example Domain\n\n...",
    "text": "Example Domain...",
    "html": "<html>...",
    "links": ["https://..."],
    "error": null
  },
  "timestamp": "2024-..."
}
```

### BatchCrawlResponse
```python
{
  "urls": ["https://...", "https://..."],
  "results": [
    {
      "url": "https://...",
      "success": true,
      "title": "...",
      "markdown": "...",
      ...
    }
  ],
  "successful": 2,
  "failed": 0,
  "timestamp": "2024-..."
}
```

## Quick Start

First set up the environment variables, modify .env as needed:
```bash
cp env.example .env
```
### Option 1: Docker (Recommended)

```bash
# Start server
docker-compose up -d mcp-server

# Server available at http://localhost:8000/sse
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run server
python server.py

# In another terminal, test client
python client.py
# or
python client.py --interactive
```

## Usage Examples

### 1. Search Web

**Request:**
```python
await session.call_tool("search_web", {
    "query": "Python async programming",
    "max_results": 5
})
```

**Response:**
```json
{
  "query": "Python async programming",
  "results": [
    {
      "title": "Asyncio — Python Documentation",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "snippet": "asyncio is a library to write concurrent code...",
      "position": 1
    },
    ...
  ],
  "total_results": 5,
  "timestamp": "2024-02-15T09:15:00.000000"
}
```

### 2. Crawl Single URL

**Request:**
```python
await session.call_tool("crawl_url", {
    "url": "https://example.com"
})
```

**Response:**
```json
{
  "url": "https://example.com",
  "content": {
    "url": "https://example.com",
    "success": true,
    "title": "Example Domain",
    "markdown": "# Example Domain\n\nThis domain is for use...",
    "text": "Example Domain This domain is for use...",
    "html": "<!doctype html><html>...",
    "links": [
      "https://www.iana.org/domains/example"
    ],
    "error": null
  },
  "timestamp": "2024-02-15T09:15:00.000000"
}
```

### 3. Batch Crawl URLs

**Request:**
```python
await session.call_tool("crawl_urls", {
    "urls": [
        "https://example.com",
        "https://www.python.org"
    ]
})
```

**Response:**
```json
{
  "urls": [
    "https://example.com",
    "https://www.python.org"
  ],
  "results": [
    {
      "url": "https://example.com",
      "success": true,
      "title": "Example Domain",
      ...
    },
    {
      "url": "https://www.python.org",
      "success": true,
      "title": "Welcome to Python.org",
      ...
    }
  ],
  "successful": 2,
  "failed": 0,
  "timestamp": "2024-02-15T09:15:00.000000"
}
```

## Using from Your Code

### Parse Structured Responses

```python
from mcp import ClientSession
from mcp.client.sse import sse_client
import json
from models import WebSearchResponse, CrawlResponse

async def search_and_process():
    server_url = "http://localhost:8000/sse"
    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Search
            result = await session.call_tool("search_web", {
                "query": "Python tutorials"
            })
            
            # Parse structured response
            data = json.loads(result.content[0].text)
            search_response = WebSearchResponse(**data)
            
            # Access structured data
            for result in search_response.results:
                print(f"{result.position}. {result.title}")
                print(f"   URL: {result.url}")
            
            # Crawl top result
            if search_response.results:
                top_url = search_response.results[0].url
                
                crawl_result = await session.call_tool("crawl_url", {
                    "url": top_url
                })
                
                # Parse crawl response
                crawl_data = json.loads(crawl_result.content[0].text)
                crawl_response = CrawlResponse(**crawl_data)
                
                if crawl_response.content.success:
                    print(f"\nContent from {top_url}:")
                    print(crawl_response.content.markdown[:500])
```

## Tool Details

### search_web

**Parameters:**
- `query` (string, required): Search query
- `max_results` (integer, optional): Max results (default: 10, max: 20)

**Returns:** `WebSearchResponse`
- Structured list of search results
- Each result has title, URL, snippet, position
- Includes query and timestamp

### crawl_url

**Parameters:**
- `url` (string, required): URL to crawl

**Returns:** `CrawlResponse`
- Structured content from URL
- Includes title, markdown, text, HTML, links
- Success/error status

### crawl_urls

**Parameters:**
- `urls` (array, required): List of URLs (1-10 items)

**Returns:** `BatchCrawlResponse`
- Structured content for each URL
- Success/failure counts
- Individual results for each URL

## Why This Design?

###   Modularity
- Each tool is independent
- Easy to add new tools
- Easy to test individually

###   Structured Data
- Pydantic models ensure type safety
- Easy to validate and parse
- Self-documenting with types

###   Clear Separation
- Models define data structures
- Tools implement business logic
- Server orchestrates tools

###   Not Over-Engineered
- Simple file structure
- No complex abstractions
- Easy to understand and modify

## Extending

### Add a New Tool

1. **Create model in `models.py`:**
```python
class MyToolResponse(BaseModel):
    result: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

2. **Create tool in `tools/my_tool.py`:**
```python
class MyTool:
    async def execute(self, param: str) -> MyToolResponse:
        result = await do_something(param)
        return MyToolResponse(result=result)
```

3. **Register in `server.py`:**
```python
my_tool = MyTool()

@server.list_tools()
async def handle_list_tools():
    return [
        types.Tool(name="my_tool", ...),
        # ... other tools
    ]

@server.call_tool()
async def handle_call_tool(name, arguments):
    if name == "my_tool":
        result = await my_tool.execute(arguments["param"])
        return [types.TextContent(
            type="text",
            text=result.model_dump_json(indent=2)
        )]
```

Done! Your new tool is ready.

## Docker Commands

```bash
# Start server
docker-compose up -d mcp-server

# View logs
docker-compose logs -f mcp-server

# Run client interactively
docker-compose run --rm mcp-client python client.py --interactive

# Stop all
docker-compose down
```

## Development Tips

1. **Test tools independently:**
```python
from tools import WebSearchTool

tool = WebSearchTool()
result = await tool.search("test query")
print(result.model_dump_json(indent=2))
```

2. **Validate models:**
```python
from models import WebSearchResponse

# This will raise validation error if invalid
response = WebSearchResponse(**data)
```

3. **Add logging:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Processing {len(urls)} URLs")
```
