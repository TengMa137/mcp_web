"""MCP Client demonstrating structured tool responses."""
import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

from models import (
    WebSearchResponse,
    CrawlResponse,
    BatchCrawlResponse,
    ArxivSearchResponse,
    ArxivFetchResponse,
)

import os

server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")

async def demo_search():
    """Demo search tool with structured response."""    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to MCP server\n")
            
            # Search web
            print("=" * 60)
            print("DEMO: search_web")
            print("=" * 60)
            
            result = await session.call_tool("search_web", {
                "query": "Python async programming",
                "max_results": 5
            })
            
            # Parse structured response
            response_json = json.loads(result.content[0].text)
            search_response = WebSearchResponse(**response_json)
            
            print(f"\nQuery: {search_response.query}")
            print(f"Total Results: {search_response.total_results}")
            print(f"Timestamp: {search_response.timestamp}\n")
            
            for result in search_response.results:
                print(f"{result.position}. {result.title}")
                print(f"   URL: {result.url}")
                print(f"   Snippet: {result.snippet[:100]}...")
                print()


async def demo_crawl():
    """Demo crawl tool with structured response."""    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n" + "=" * 60)
            print("DEMO: crawl_url")
            print("=" * 60)
            
            result = await session.call_tool("crawl_url", {
                "url": "https://example.com"
            })
            
            # Parse structured response
            response_json = json.loads(result.content[0].text)
            crawl_response = CrawlResponse(**response_json)
            
            print(f"\nURL: {crawl_response.url}")
            print(f"Success: {crawl_response.content.success}")
            
            if crawl_response.content.success:
                print(f"Title: {crawl_response.content.title}")
                print(f"Links found: {len(crawl_response.content.links)}")
                print(f"\nMarkdown preview:")
                print(crawl_response.content.markdown[:500])
                print("\n...")
            else:
                print(f"Error: {crawl_response.content.error}")


async def demo_batch_crawl():
    """Demo batch crawl with structured response."""    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n" + "=" * 60)
            print("DEMO: crawl_urls (batch)")
            print("=" * 60)
            
            result = await session.call_tool("crawl_urls", {
                "urls": [
                    "https://example.com",
                    "https://www.python.org"
                ]
            })
            
            # Parse structured response
            response_json = json.loads(result.content[0].text)
            batch_response = BatchCrawlResponse(**response_json)
            
            print(f"\nTotal URLs: {len(batch_response.urls)}")
            print(f"Successful: {batch_response.successful}")
            print(f"Failed: {batch_response.failed}")
            print(f"Timestamp: {batch_response.timestamp}\n")
            
            for content in batch_response.results:
                print(f"URL: {content.url}")
                print(f"Success: {content.success}")
                if content.success:
                    print(f"Title: {content.title}")
                    print(f"Text length: {len(content.text or '')} chars")
                else:
                    print(f"Error: {content.error}")
                print()


async def demo_arxiv_search():
    """Demo arXiv search tool with structured response."""    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n" + "=" * 60)
            print("DEMO: search_arxiv")
            print("=" * 60)
            
            result = await session.call_tool("search_arxiv", {
                "query": "transformer",
                "category": "cs.LG",
                "max_results": 5
            })
            
            response_json = json.loads(result.content[0].text)
            arxiv_response = ArxivSearchResponse(**response_json)
            
            print(f"\nQuery: {arxiv_response.query}")
            print(f"Category: {arxiv_response.category}")
            print(f"Total Results: {arxiv_response.total_results}")
            print(f"Timestamp: {arxiv_response.timestamp}\n")
            
            for idx, paper in enumerate(arxiv_response.results, 1):
                print(f"{idx}. {paper.title}")
                print(f"   arXiv ID: {paper.arxiv_id}")
                print(f"   Authors: {', '.join(a.name for a in paper.authors)}")
                print(f"   Published: {paper.published.date()}")
                print(f"   Category: {paper.primary_category}")
                print(f"   PDF: {paper.pdf_url}")
                print(f"   Abstract preview: {paper.summary[:200]}...")
                print()


async def demo_arxiv_fetch():
    """Demo arXiv fetch tool."""
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n" + "=" * 60)
            print("DEMO: fetch_arxiv")
            print("=" * 60)

            arxiv_id = "2301.00001"  # example ID

            result = await session.call_tool("fetch_arxiv", {
                "arxiv_id": arxiv_id
            })

            response_json = json.loads(result.content[0].text)
            fetch_response = ArxivFetchResponse(**response_json)

            if fetch_response.found:
                paper = fetch_response.paper
                print(f"\nTitle: {paper.title}")
                print(f"Authors: {', '.join(a.name for a in paper.authors)}")
                print(f"Published: {paper.published}")
                print(f"Categories: {', '.join(paper.categories)}")
                print(f"\nFull Abstract:\n{paper.summary}")
            else:
                print(f"\n❌ Paper {arxiv_id} not found")


async def interactive_mode():
    """Interactive mode for testing."""    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to MCP server\n")
            
            while True:
                print("\n" + "=" * 60)
                print("Commands:")
                print("  1. Search web")
                print("  2. Crawl single URL")
                print("  3. Crawl multiple URLs")
                print("  4. Search arXiv")
                print("  5. Fetch arXiv paper")

                print("  q. Quit")
                print("=" * 60)
                
                choice = input("\nChoice: ").strip()
                
                if choice == "q":
                    break
                
                elif choice == "1":
                    query = input("Search query: ")
                    max_results = input("Max results (default 5): ").strip() or "5"
                    
                    result = await session.call_tool("search_web", {
                        "query": query,
                        "max_results": int(max_results)
                    })
                    
                    response_json = json.loads(result.content[0].text)
                    search_response = WebSearchResponse(**response_json)
                    
                    print(f"\nFound {search_response.total_results} results:\n")
                    for r in search_response.results:
                        print(f"{r.position}. {r.title}")
                        print(f"   {r.url}")
                        print()
                
                elif choice == "2":
                    url = input("URL to crawl: ")
                    
                    result = await session.call_tool("crawl_url", {
                        "url": url
                    })
                    
                    response_json = json.loads(result.content[0].text)
                    crawl_response = CrawlResponse(**response_json)
                    
                    if crawl_response.content.success:
                        print(f"\n✅ Success!")
                        print(f"Title: {crawl_response.content.title}")
                        print(f"Text length: {len(crawl_response.content.text or '')} chars")
                        print(f"Links internal: {len(crawl_response.content.links['internal'])} Links external: {len(crawl_response.content.links['external'])}")
                        
                        show_content = input("\nShow content? (y/n): ").strip().lower()
                        if show_content == "y":
                            print("\nMarkdown:")
                            print(crawl_response.content.markdown[:1000])
                            print("\n...")
                    else:
                        print(f"\n❌ Failed: {crawl_response.content.error}")
                
                elif choice == "3":
                    urls_input = input("URLs (comma-separated): ")
                    urls = [u.strip() for u in urls_input.split(",")]
                    
                    result = await session.call_tool("crawl_urls", {
                        "urls": urls
                    })
                    
                    response_json = json.loads(result.content[0].text)
                    batch_response = BatchCrawlResponse(**response_json)
                    
                    print(f"\n✅ Successful: {batch_response.successful}")
                    print(f"❌ Failed: {batch_response.failed}\n")
                    
                    for content in batch_response.results:
                        status = "✅" if content.success else "❌"
                        print(f"{status} {content.url}")
                        if content.success:
                            print(f"   Title: {content.title}")
                        else:
                            print(f"   Error: {content.error}")
                
                elif choice == "4":
                    query = input("Search query: ")
                    category = input("Category (e.g., cs.LG, optional): ").strip() or None
                    max_results = input("Max results (default 5): ").strip() or "5"

                    payload = {
                        "query": query,
                        "max_results": int(max_results)
                    }

                    if category:
                        payload["category"] = category

                    result = await session.call_tool("search_arxiv", payload)
                    # print(result)
                    if result.isError:
                        print(result.content[0].text)
                        raise RuntimeError("Tool execution failed")

                    response_json = json.loads(result.content[0].text)
                    arxiv_response = ArxivSearchResponse(**response_json)

                    print(f"\nFound {arxiv_response.total_results} papers:\n")
                    for paper in arxiv_response.results:
                        print(f"{paper.arxiv_id} - {paper.title}")
                        print(f"   {paper.primary_category}")
                        print()

                elif choice == "5":
                    arxiv_id = input("arXiv ID: ").strip()

                    result = await session.call_tool("fetch_arxiv", {
                        "arxiv_id": arxiv_id
                    })

                    response_json = json.loads(result.content[0].text)
                    fetch_response = ArxivFetchResponse(**response_json)

                    if fetch_response.found:
                        paper = fetch_response.paper
                        print(f"\nTitle: {paper.title}")
                        print(f"Authors: {', '.join(a.name for a in paper.authors)}")
                        print(f"\nAbstract:\n{paper.summary}")
                    else:
                        print("❌ Paper not found")



async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_mode()
    else:
        # Run all demos
        await demo_search()
        await demo_crawl()
        await demo_batch_crawl()
        await demo_arxiv_search()
        await demo_arxiv_fetch


if __name__ == "__main__":
    asyncio.run(main())
