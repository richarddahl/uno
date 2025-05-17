"""Configuration for the cache system."""

from datetime import timedelta
from typing import Optional, Union

from pydantic import Field, field_validator
from uno.config import BaseSettings


class CacheSettings(BaseSettings):
    """Settings for the cache system."""
    
    # Backend configuration
    CACHE_BACKEND: str = Field(
        default="memory",
        description="Cache backend to use (memory or redis)",
        env="CACHE_BACKEND",
    )
    
    # Common settings
    CACHE_KEY_PREFIX: str = Field(
        default="uno:cache:",
        description="Prefix for all cache keys",
        env="CACHE_KEY_PREFIX",
    )
    CACHE_DEFAULT_TTL: Optional[int] = Field(
        default=3600,  # 1 hour
        description="Default time-to-live for cached items in seconds",
        env="CACHE_DEFAULT_TTL",
    )
    
    # In-memory backend settings
    CACHE_MAX_SIZE: int = Field(
        default=1000,
        description="Maximum number of items to store in memory",
        env="CACHE_MAX_SIZE",
    )
    
    # Redis backend settings
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (required for Redis backend)",
        env="REDIS_URL",
    )
    
    @property
    def default_ttl_timedelta(self) -> Optional[timedelta]:
        """Get the default TTL as a timedelta."""
        if self.CACHE_DEFAULT_TTL is None:
            return None
        return timedelta(seconds=self.CACHE_DEFAULT_TTL)
    
    @field_validator('CACHE_BACKEND')
    def validate_backend(cls, v: str) -> str:
        """Validate the cache backend."""
        if v.lower() not in ('memory', 'redis'):
            raise ValueError("CACHE_BACKEND must be either 'memory' or 'redis'")
        return v.lower()
    
    @field_validator('CACHE_MAX_SIZE')
    def validate_max_size(cls, v: int) -> int:
        """Validate the maximum cache size."""
        if v < 1:
            raise ValueError("CACHE_MAX_SIZE must be at least 1")
        return v
    
    @field_validator('CACHE_DEFAULT_TTL')
    def validate_ttl(cls, v: Optional[int]) -> Optional[int]:
        """Validate the TTL value."""
        if v is not None and v < 0:
            raise ValueError("CACHE_DEFAULT_TTL must be a positive integer or None")
        return v


# Export settings instance
settings = CacheSettings()
