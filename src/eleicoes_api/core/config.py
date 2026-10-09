from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Eleições API"
    app_version: str = "0.1.0"
    app_description: str = "API para consulta de dados eleitorais do TSE."
    environment: str = "development"

    default_election_year: int = 2026

    tse_http_timeout: float = Field(default=15.0, gt=0)
    tse_cache_ttl: float = Field(default=15.0, ge=0)
    tse_cache_max_entries: int = Field(default=512, ge=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()