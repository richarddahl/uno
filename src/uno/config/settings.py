# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Configuration settings loading and caching.

This module provides functions for loading and caching configuration settings
from environment variables, .env files, and other sources.
"""

import asyncio
import inspect
import os
import tempfile
from functools import wraps
from typing import Any, TypeVar, cast

from uno.config.environment import Environment
from uno.config.env_cache import env_cache

T = TypeVar("T")
CONFIG_CACHE: dict[type, Any] = {}
_CONFIG_CACHE_LOCK = asyncio.Lock()


async def load_settings(
    settings_class: type[T],
    env: Environment | None = None,
    override_values: dict[str, Any] | None = None,
    config_path: str | None = None,
) -> T:
    """Load configuration settings for the specified class.

    Args:
        settings_class: The settings class to load
        env: Optional environment to use (default: current environment)
        override_values: Optional values to override settings
        config_path: Optional path to load configuration from

    Returns:
        The settings instance.
    """
    # Store original cwd and make sure we can restore it even if it's been deleted
    try:
        orig_cwd = os.getcwd()
    except (FileNotFoundError, PermissionError):
        # Use temp directory as fallback if CWD doesn't exist or is inaccessible
        orig_cwd = tempfile.gettempdir()

    env = env or Environment.get_current()

    # Handle config_path - safely change directory
    valid_config_path = False
    if config_path:
        try:
            os.chdir(config_path)
            valid_config_path = True
        except (FileNotFoundError, PermissionError):
            # If config_path doesn't exist, don't try to use it
            pass

    try:
        # Only try to load env files if a valid directory is available
        if valid_config_path or os.path.exists(os.getcwd()):
            # Load environment variables from .env files
            from uno.config.env_loader import load_env_files

            load_env_files(env=env, override=True)
            # Rebuild the model class to ensure it picks up new env vars
            settings_class.model_rebuild(force=True)
    except (FileNotFoundError, PermissionError):
        # Skip env file loading if directory is invalid
        pass

    # Create settings instance
    settings = settings_class()  # type: ignore

    # Apply environment-specific settings if method exists
    if hasattr(settings, "_load_env_settings"):
        await settings._load_env_settings(env)

    # Apply override values if provided
    if override_values:
        for key, value in override_values.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

    # Restore original working directory if possible
    try:
        os.chdir(orig_cwd)
    except (FileNotFoundError, PermissionError):
        # If original directory was deleted, move to a safe location
        os.chdir(tempfile.gettempdir())

    return settings


async def get_config(settings_class: type[T]) -> T:
    """Get configuration for a component (with global cache).

    This function provides a cached access to configuration settings,
    ensuring that each settings class is only instantiated once during
    the application lifecycle.

    Args:
        settings_class: The settings class to load

    Returns:
        The cached settings instance
    """
    global CONFIG_CACHE

    # Check cache first for fast path
    if settings_class in CONFIG_CACHE:
        return cast(T, CONFIG_CACHE[settings_class])

    # Acquire lock for thread safety
    async with _CONFIG_CACHE_LOCK:
        # Check again in case another thread loaded it while we were waiting
        if settings_class in CONFIG_CACHE:
            return cast(T, CONFIG_CACHE[settings_class])

        # Load settings
        settings = await load_settings(settings_class)
        CONFIG_CACHE[settings_class] = settings
        return settings


def clear_config_cache() -> None:
    """Clear the global configuration cache.

    This function is primarily used for testing and should not normally
    be needed in application code.
    """
    global CONFIG_CACHE
    CONFIG_CACHE.clear()
