from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./market.db"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "market"
    api_keys: str = "dev-key"  # comma-separated
    max_page_size: int = 1000
    mongo_timeout_ms: int = 2000

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
