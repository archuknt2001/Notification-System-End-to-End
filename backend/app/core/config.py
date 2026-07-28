"""
Application configuration.

Reads environment variables via pydantic-settings.
All other modules import from here — never from os.environ directly.
Designed so JWT or other auth settings can be added here later without
touching any other module.
"""

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "AI-Native CRM Notification System"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./notifications.db"

    # CORS — accepts either a JSON array or a comma-separated string in .env
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        """
        Allows .env to contain either:
          ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
        or a proper JSON array:
          ALLOWED_ORIGINS=["http://localhost:5173"]
        """
        if isinstance(v, str):
            # Strip surrounding whitespace and split on commas
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


# Single shared instance — import this everywhere
settings = Settings()
