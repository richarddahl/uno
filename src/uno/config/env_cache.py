# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Environment variable caching for the Uno configuration system.

This module provides an efficient caching layer for environment variable
lookups and env file content to improve performance.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from functools import lru_cache
from typing import Any, ClassVar


class EnvFileCacheEntry:
    """Cache entry for env file content."""

    def __init__(self, content: dict[str, str], mtime: float) -> None:
        self.content = content
        self.mtime = mtime

    def is_valid(self) -> bool:
        """Check if the cache entry is still valid by comparing file mtime."""
        # If the file no longer exists, cache is invalid
        try:
            # Find the file path by reverse lookup (not ideal, but works for this cache)
            for path, entry in env_cache._env_file_cache.items():
                if entry is self:
                    return path.exists() and path.stat().st_mtime == self.mtime
        except Exception:
            return False
        return False


class EnvCache:
    """
    Cache manager for environment variables and env file content.

    This singleton class provides cached access to environment variables
    and env file content with automatic invalidation.
    """

    _instance: ClassVar[EnvCache | None] = None
    _cache_ttl: int = 60  # Cache TTL in seconds

    def __new__(cls) -> EnvCache:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self) -> None:
        """Initialize the cache structures."""
        self._env_vars_cache: dict[str, str] = {}
        self._env_file_cache: dict[str, tuple[float, dict[str, str]]] = {}
        self._env_last_refresh = 0.0
        self._field_mapping_cache: dict[type, dict[str, list[str]]] = {}

    def get_env_var(self, name: str, case_sensitive: bool = True) -> str | None:
        """
        Get environment variable with caching.

        Args:
            name: Environment variable name
            case_sensitive: Whether to do a case-sensitive lookup

        Returns:
            Value of environment variable or None if not found
        """
        # Check if cache is stale
        current_time = time.time()
        if current_time - self._env_last_refresh > self._cache_ttl:
            self._env_vars_cache = {}
            self._env_last_refresh = current_time

        # Use cache for case-sensitive lookups
        if case_sensitive:
            # Check cache first
            if name in self._env_vars_cache:
                return self._env_vars_cache[name]

            # Cache miss - get from environment
            value = os.environ.get(name)
            if value is not None:
                self._env_vars_cache[name] = value
            return value

        # For case-insensitive lookups, we don't cache as they're less common
        for env_name, value in os.environ.items():
            if env_name.lower() == name.lower():
                return value

        return None

    def get_env_file_content(self, file_path: Path) -> dict[str, str]:
        """Get environment variables from a file, using cache if available.

        Args:
            file_path: Path to the .env file

        Returns:
            Dictionary of environment variables
        """
        # Check if file exists in cache and if it's up to date
        if file_path in self._env_file_cache:
            cached_entry = self._env_file_cache[file_path]
            if cached_entry.is_valid():
                return cached_entry.content

        # Load file content directly instead of calling back to env_loader
        content = self._load_env_file_content(file_path)

        # Cache the content with current modification time
        self._env_file_cache[file_path] = EnvFileCacheEntry(
            content=content, mtime=file_path.stat().st_mtime
        )

        return content

    def _load_env_file_content(self, file_path: Path) -> dict[str, str]:
        """Load environment variables from a file directly.

        Args:
            file_path: Path to the .env file

        Returns:
            Dictionary of environment variables
        """
        if not file_path.exists():
            return {}

        result: dict[str, str] = {}

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                key, value = self._parse_env_line(line)
                if key:
                    result[key] = value

        return result

    def _parse_env_line(self, line: str) -> tuple[str, str]:
        """Parse a line from an .env file.

        Args:
            line: A line from an .env file

        Returns:
            Tuple of (key, value)
        """
        if "=" not in line:
            return ("", "")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Remove quotes if present
        if value and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]

        return key, value

    def cache_field_mapping(self, cls: type, mapping: dict[str, list[str]]) -> None:
        """
        Cache field-to-env-var mapping for a class.

        Args:
            cls: The class to cache mapping for
            mapping: Field name to env var names mapping
        """
        self._field_mapping_cache[cls] = mapping

    def get_field_mapping(self, cls: type) -> dict[str, list[str]] | None:
        """
        Get cached field-to-env-var mapping for a class.

        Args:
            cls: The class to get mapping for

        Returns:
            Cached mapping or None if not found
        """
        return self._field_mapping_cache.get(cls)

    def clear(self) -> None:
        """Clear all caches."""
        self._env_vars_cache.clear()
        self._env_file_cache.clear()
        self._field_mapping_cache.clear()
        self._env_last_refresh = 0.0


# Singleton instance for global use
env_cache = EnvCache()


@lru_cache(maxsize=128)
def get_cached_env_var(name: str, case_sensitive: bool = True) -> str | None:
    """
    Get environment variable with function-level caching.

    This is an alternative to the singleton cache that uses Python's lru_cache.

    Args:
        name: Environment variable name
        case_sensitive: Whether to do a case-sensitive lookup

    Returns:
        Value of environment variable or None if not found
    """
    if case_sensitive:
        return os.environ.get(name)

    for env_name, value in os.environ.items():
        if env_name.lower() == name.lower():
            return value

    return None
