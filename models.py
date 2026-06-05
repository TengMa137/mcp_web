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
    markdown: Optional[str] = None
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


class ArxivFetchResponse(BaseModel):
    """Response from arxiv_fetch tool."""
    arxiv_id: str
    paper: Optional[ArxivPaper] = None
    found: bool
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ApiLocation(BaseModel):
    """Resolved location returned by a public API."""
    name: str
    country: Optional[str] = None
    admin1: Optional[str] = None
    latitude: float
    longitude: float
    timezone: Optional[str] = None


class WeatherDailyForecast(BaseModel):
    """Daily weather forecast for one local date."""
    date: str
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None
    temperature_min_c: Optional[float] = None
    temperature_max_c: Optional[float] = None
    precipitation_sum_mm: Optional[float] = None
    precipitation_probability_max_percent: Optional[int] = None
    wind_speed_max_kmh: Optional[float] = None


class WeatherHourlyForecast(BaseModel):
    """Hourly weather forecast point."""
    time: str
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    precipitation_probability_percent: Optional[int] = None
    wind_speed_kmh: Optional[float] = None


class WeatherForecastResponse(BaseModel):
    """Response from weather_forecast tool."""
    query: str
    date: str
    location: Optional[ApiLocation] = None
    daily: Optional[WeatherDailyForecast] = None
    hourly: List[WeatherHourlyForecast] = Field(default_factory=list)
    source: str = "Open-Meteo"
    source_url: str = "https://open-meteo.com/"
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class WikiSummaryResponse(BaseModel):
    """Response from wiki_summary tool."""
    query: str
    language: str
    title: Optional[str] = None
    description: Optional[str] = None
    extract: Optional[str] = None
    page_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source: str = "Wikipedia"
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class NewsArticle(BaseModel):
    """Single news article result from a public news API."""
    title: str
    url: str
    domain: Optional[str] = None
    language: Optional[str] = None
    source_country: Optional[str] = None
    seen_at: Optional[str] = None
    image_url: Optional[str] = None


class NewsSearchResponse(BaseModel):
    """Response from news_search tool."""
    query: str
    timespan: str
    articles: List[NewsArticle]
    total_results: int
    source: str = "GDELT DOC 2.0"
    source_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
