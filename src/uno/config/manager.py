# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Configuration manager implementation for the Uno framework.

This module provides a concrete implementation of the ConfigManagerProtocol,
adding caching, environment handling, and additional utility methods.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar, cast

from uno.config.base import Config
from uno.config.environment import Environment
from uno.config.protocols import ConfigManagerProtocol, ConfigProtocol
from uno.config.settings import get_config, load_settings


T = TypeVar("T", bound=Config)


class ConfigManager:
    """
    Configuration manager for loading and caching configuration objects.

    Implements the ConfigManagerProtocol interface.
    """

    def __init__(self, default_env: Environment | None = None) -> None:
        """
        Initialize the configuration manager.

        Args:
            default_env: Default environment to use when not specified
        """
        self.default_env = default_env or Environment.get_current()
        self._config_cache: dict[type[ConfigProtocol], ConfigProtocol] = {}

    async def load_settings(
        self,
        settings_class: type[T],
        env: Environment | None = None,
        config_path: str | None = None,
        override_values: dict[str, object] | None = None,
    ) -> T:
        """
        Load settings with explicit control over sources and priorities.

        Args:
            settings_class: The settings class to instantiate
            env: The environment to load settings for
            config_path: Optional path to configuration files
            override_values: Optional override values

        Returns:
            Configured settings instance
        """
        return await load_settings(
            settings_class,
            env=env or self.default_env,
            config_path=config_path,
            override_values=override_values,
        )

    async def get_config(self, settings_class: type[T]) -> T:
        """
        Get configuration for a component with caching.

        Args:
            settings_class: The settings class to retrieve

        Returns:
            Configured settings instance (cached if previously loaded)
        """
        # Check cache first
        if settings_class in self._config_cache:
            return cast(T, self._config_cache[settings_class])

        # Load settings and store in cache
        settings = await self.load_settings(settings_class)
        self._config_cache[settings_class] = settings
        return settings

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._config_cache.clear()

    async def reload_config(self, settings_class: type[T]) -> T:
        """
        Force reload a configuration object.

        Args:
            settings_class: The settings class to reload

        Returns:
            Freshly loaded configuration object
        """
        # Remove from cache if present
        if settings_class in self._config_cache:
            del self._config_cache[settings_class]

        # Load settings and return
        return await self.get_config(settings_class)
