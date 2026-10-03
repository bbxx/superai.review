from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret application configuration.

    Provider credentials are deliberately not modeled here. Real provider adapters
    will obtain secrets from their dedicated secret layer.
    """

    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./superai.db"
    log_level: str = "INFO"
    document_storage_root: Path = Path("./data/documents")
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    document_extraction_timeout_seconds: float = Field(default=45.0, gt=0)
    pdf_text_min_chars_per_page: int = Field(default=24, ge=1)
    evidence_chunk_chars: int = Field(default=4000, ge=256)
    context_max_source_chars: int = Field(default=40000, ge=1000)
    retrieval_max_items: int = Field(default=12, ge=1)
    retrieval_max_chars: int = Field(default=16000, ge=256)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SUPERAI_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
