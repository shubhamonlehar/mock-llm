from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    proxy_mode: Literal["record", "replay", "regular"] = Field(default="replay", alias="PROXY_MODE")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    sqlite_path: Path = Field(default=Path("data/fixtures.db"), alias="SQLITE_PATH")
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    provider: str = Field(default="groq", alias="PROVIDER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
