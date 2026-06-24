from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_version: str = "0.1.0"
    request_timeout_seconds: float = Field(default=5.0, ge=1.0, le=20.0)
    open_beauty_facts_base_url: str = "https://world.openbeautyfacts.org"
    open_beauty_facts_user_agent: str = (
        "CosmeticsShelfAPI/0.1.0 contact@example.com"
    )
    official_search_enabled: bool = False
    official_search_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

