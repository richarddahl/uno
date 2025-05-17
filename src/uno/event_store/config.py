"""Configuration for the Event Store."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict
from uno.config import Config


class EventStoreSettings(Config):
    """Configuration settings for the Event Store.

    Settings can be configured via environment variables with the `UNO_EVENT_STORE_` prefix.
    """

    # SQLite settings
    sqlite_path: str = ":memory:"

    # PostgreSQL settings
    postgres_dsn: str | None = None
    postgres_enable_vector_search: bool = False
    postgres_vector_dimensions: int = 1536
    postgres_pool_min_size: int = 1
    postgres_pool_max_size: int = 10
    postgres_vector_index_type: str = "ivfflat"  # or "hnsw"
    postgres_vector_index_lists: int = 100  # For IVFFlat
    postgres_vector_index_m: int = 16  # For HNSW (number of bi-directional links)
    postgres_vector_index_ef_construction: int = 64  # For HNSW

    # Redis settings
    redis_url: str | None = None
    redis_cluster_mode: bool = False
    redis_cluster_nodes: list[str] | None = None  # List of node URLs in cluster mode
    redis_ssl: bool = False
    redis_ssl_ca_certs: str | None = None
    redis_connection_kwargs: dict[str, Any] = Field(
        default_factory=dict
    )  # Additional connection args

    # General settings
    max_retry_attempts: int = 3
    retry_delay: float = 0.1

    # Validation
    @field_validator("sqlite_path")
    @classmethod
    def validate_sqlite_path(cls, v: str) -> str:
        """Ensure SQLite path is valid."""
        if v != ":memory:":
            try:
                path = Path(v).resolve()
                path.parent.mkdir(parents=True, exist_ok=True)
                return str(path)
            except (OSError, TypeError) as e:
                raise ValueError(f"Invalid SQLite path: {v}") from e
        return v

    @model_validator(mode="after")
    def validate_postgres_settings(self) -> "EventStoreSettings":
        """Validate PostgreSQL-related settings."""
        if self.postgres_dsn and not self.postgres_dsn.startswith("postgresql://"):
            if (
                "://" not in self.postgres_dsn
            ):  # If no scheme provided, add postgresql://
                self.postgres_dsn = f"postgresql://{self.postgres_dsn}"
            else:
                raise ValueError("PostgreSQL DSN must use the postgresql:// scheme")

        if self.postgres_vector_dimensions <= 0:
            raise ValueError("Vector dimensions must be a positive integer")

        if self.postgres_pool_min_size < 0 or self.postgres_pool_max_size < 1:
            raise ValueError("Pool sizes must be positive integers")

        if self.postgres_pool_min_size > self.postgres_pool_max_size:
            raise ValueError(
                "Minimum pool size cannot be greater than maximum pool size"
            )

        return self

    model_config = SettingsConfigDict(
        env_prefix="UNO_EVENT_STORE_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


# Default settings instance
default_settings = EventStoreSettings(
    sqlite_path=":memory:",
    postgres_dsn=None,
    redis_url=None,
    max_retry_attempts=3,
    retry_delay=0.1,
)
