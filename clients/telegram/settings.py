from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramBotSettings(BaseSettings):
    telegram_bot_token: SecretStr = Field(min_length=1)

    api_base_url: str = "http://127.0.0.1:8000"
    api_timeout_seconds: float = Field(default=10.0, gt=0)

    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> TelegramBotSettings:
    return TelegramBotSettings()