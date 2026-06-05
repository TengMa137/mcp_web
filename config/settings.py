"""Configuration settings for MCP server."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    api_user_agent: str = "mcp-web-server/0.1"

    max_search_results: int = 10
    search_timeout: int = 30

    crawler_timeout: int = 60
    crawler_max_batch_urls: int = 10
    crawler_max_concurrency: int = 4
    crawler_word_count_threshold: int = 1000
    crawler_exclude_external_links: bool = True
    crawler_remove_overlay_elements: bool = True
    crawler_allow_private_hosts: bool = False

    arxiv_fetch_timeout: int = 30
    arxiv_min_request_interval: float = 3.0

    weather_timeout: int = 20
    weather_max_forecast_days: int = 16

    wiki_timeout: int = 20
    wiki_default_language: str = "en"

    news_timeout: int = 20
    news_max_results: int = 25
    news_default_timespan: str = "1d"

    allowed_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
