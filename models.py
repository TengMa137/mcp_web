"""Pydantic models for structured tool responses."""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Optional
from datetime import datetime


class SearchResult(BaseModel):
    """Single search result from web search."""
    title: str
    url: str
    snippet: str
    position: int = Field(..., description="Position in search results (1-indexed)")


class WebSearchResponse(BaseModel):
    """Response from web_search tool."""
    query: str
    results: List[SearchResult]
    total_results: int
    timestamp: datetime = Field(default_factory=datetime.now)


class CrawledContent(BaseModel):
    """Content extracted from a single URL."""
    url: str
    success: bool
    title: Optional[str] = None
    text: Optional[str] = None
    links: Dict[str, List[Dict]] = Field(default_factory=dict)
    error: Optional[str] = None


class CrawlResponse(BaseModel):
    """Response from crawl_url tool."""
    url: str
    content: CrawledContent
    timestamp: datetime = Field(default_factory=datetime.now)


class BatchCrawlResponse(BaseModel):
    """Response from batch crawl operation."""
    urls: List[str]
    results: List[CrawledContent]
    successful: int
    failed: int
    timestamp: datetime = Field(default_factory=datetime.now)


class ArxivAuthor(BaseModel):
    """Author of an arXiv paper."""
    name: str


class ArxivPaper(BaseModel):
    """Single arXiv paper result."""
    arxiv_id: str
    title: str
    summary: str
    authors: List[ArxivAuthor]
    pdf_url: Optional[HttpUrl] = None
    primary_category: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    published: datetime
    updated: datetime


class ArxivSearchResponse(BaseModel):
    """Response from arxiv_search tool."""
    query: str
    category: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    results: List[ArxivPaper]
    total_results: int
    timestamp: datetime = Field(default_factory=datetime.now)


class ArxivFetchResponse(BaseModel):
    """Response from arxiv_fetch tool."""
    arxiv_id: str
    paper: Optional[ArxivPaper] = None
    found: bool
    timestamp: datetime = Field(default_factory=datetime.now)
