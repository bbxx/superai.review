from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret application configuration.

    Provider credentials are deliberately not modeled here. Real provider adapters
    will obtain secrets from their dedicated secret layer.
    """

    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./superai.db"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SUPERAI_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
