"""Configuration settings for MCP server."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    max_search_results: int = 10
    search_timeout: int = 30

    crawler_timeout: int = 60
    crawler_word_count_threshold: int = 1000
    crawler_exclude_external_links: bool = True
    crawler_remove_overlay_elements: bool = True

    max_arxiv_search_results: int = 10
    arxiv_search_timeout: int = 30

    allowed_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()