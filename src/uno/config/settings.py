# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Settings and configuration loading for Uno framework.
"""
from __future__ import annotations

import asyncio
import os
from typing import TypeVar
from uno.config.base import Environment, UnoSettings

T = TypeVar("T", bound=UnoSettings)

async def load_settings(
    settings_class: type[T],
    env: Environment | None = None,
    config_path: str | None = None,
    override_values: dict[str, object] | None = None,
) -> T:
    """
    Load settings with explicit control over sources and priorities.
    """
    if env is None:
        env = Environment.get_current()

    orig_cwd = os.getcwd()
    if config_path:
        os.chdir(config_path)
    try:
        settings = await settings_class.from_env(env)
        if override_values:
            for key, value in override_values.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
        return settings
    finally:
        if config_path:
            os.chdir(orig_cwd)

# Simple DI-friendly cache for get_config (per Uno integration principles)
_config_cache: dict[type[UnoSettings], UnoSettings] = {}
import asyncio
_config_cache_lock: asyncio.Lock = asyncio.Lock()

async def get_config(settings_class: type[T]) -> T:
    """Get configuration for a component (with global cache)."""
    async with _config_cache_lock:
        if settings_class in _config_cache:
            return _config_cache[settings_class]  # type: ignore
        settings = await load_settings(settings_class)
        _config_cache[settings_class] = settings
        return settings

class SettingsConfigDict(dict):
    """Type alias for settings config dict (for compatibility)."""
    pass
