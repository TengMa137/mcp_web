# MCP Web Server

Dockerized MCP server that exposes web search, webpage crawling, and arXiv fetch-by-ID over SSE.

## Tools

- `search_web`: DuckDuckGo/DDGS web search with bounded result count.
- `crawl_url`: Crawl one known URL and return readable markdown/text.
- `crawl_urls`: Crawl a bounded list of known URLs.
- `fetch_arxiv`: Fetch arXiv metadata/abstract by exact arXiv ID.

Paper discovery is intentionally done through `search_web`, for example with `site:arxiv.org/abs diffusion language model`, then `fetch_arxiv` is called with the selected ID.

## Docker Service

Create local config:

```bash
cp -n env.example .env
```

Run the MCP server:

```bash
docker compose up --build -d mcp-server
```

The service is exposed only on the Compose network, not published to the host. An agent container on the same network should use:

```text
http://mcp-server:8000/sse
```

To integrate into a larger agent stack, copy the `mcp-server` service into that Compose file or attach both projects to a shared external network.

## Local Development

```bash
pip install -r requirements.txt
playwright install chromium
python server.py
```

## Configuration

Environment variables are defined in `env.example`:

- `MAX_SEARCH_RESULTS`, `SEARCH_TIMEOUT`
- `CRAWLER_TIMEOUT`, `CRAWLER_MAX_BATCH_URLS`, `CRAWLER_MAX_CONCURRENCY`
- `CRAWLER_WORD_COUNT_THRESHOLD`, `CRAWLER_EXCLUDE_EXTERNAL_LINKS`, `CRAWLER_REMOVE_OVERLAY_ELEMENTS`, `CRAWLER_ALLOW_PRIVATE_HOSTS`
- `ARXIV_FETCH_TIMEOUT`, `ARXIV_MIN_REQUEST_INTERVAL`

Keep `CRAWLER_ALLOW_PRIVATE_HOSTS=false` for production. The crawler blocks localhost, private IP literals, Docker host gateway names, and single-label internal service names by default.

## Response Models

Responses are JSON serialized Pydantic models from `models.py`:

- `WebSearchResponse`
- `CrawlResponse`
- `BatchCrawlResponse`
- `ArxivFetchResponse`

## Runtime Hardening

The Docker service runs as non-root UID/GID `10001`, with `read_only: true`, dropped Linux capabilities, `no-new-privileges`, bounded CPU/memory/PIDs, and tmpfs-backed writable paths for Chromium/cache needs.
