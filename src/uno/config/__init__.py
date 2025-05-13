# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/config/__init__.py

"""
Public API for the Uno configuration system.

This module exports the core components needed to define and load configuration
settings in the Uno framework.
"""

from __future__ import annotations

import asyncio
from typing import TypeVar

import os
from uno.config.base import Environment, UnoSettings
from uno.config.errors import (
    ConfigEnvironmentError,
    ConfigError,
    ConfigFileNotFoundError,
    ConfigMissingKeyError,
    ConfigParseError,
    ConfigValidationError,
    SecureValueError,
)
from uno.config.env_loader import get_env_value, load_env_files
from uno.config.secure import (
    SecureField,
    SecureValue,
    SecureValueHandling,
    requires_secure_access,
)

T = TypeVar("T", bound=UnoSettings)


async def load_settings(
    settings_class: type[T],
    env: Environment | None = None,
    config_path: str | None = None,
    override_values: dict[str, object] | None = None
) -> T:
    """
    Load settings with explicit control over sources and priorities.

    Args:
        settings_class: Settings class to load
        env: Optional environment to target (defaults to current)
        config_path: Optional explicit config directory
        override_values: Optional dictionary of override values (applied last, useful for tests)

    Returns:
        Initialized settings instance

    Loading order:
        1. Default values from the settings class
        2. .env files (base, environment-specific, component, local) from config_path or cwd
        3. Environment variables
        4. Explicit override_values (highest priority)
    """
    if env is None:
        env = Environment.get_current()

    # Use config_path if provided (set cwd temporarily)
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
_config_cache_lock = asyncio.Lock()


async def get_config(settings_class: type[T]) -> T:
    """Get configuration for a component.

    This is a convenience wrapper around load_settings with global config caching.

    Args:
        settings_class: Settings class to load

    Returns:
        Initialized settings instance
    """
    # Thread-safe cache access
    async with _config_cache_lock:
        if settings_class in _config_cache:
            return _config_cache[settings_class]  # type: ignore

        # Load settings and cache them
        config = await load_settings(settings_class)
        _config_cache[settings_class] = config
        return config


async def setup_secure_config(master_key: str | bytes | None = None) -> None:
    """Set up secure configuration with encryption capabilities.

    This function initializes the encryption system for secure config values.

    Args:
        master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)
    """
    await SecureValue.setup_encryption(master_key)


__all__ = [
    "ConfigError",
    "ConfigEnvironmentError",
    "ConfigFileNotFoundError",
    "ConfigMissingKeyError",
    "ConfigParseError",
    "ConfigValidationError",
    "Environment",
    # Secure configuration
    "SecureField",
    "SecureValue",
    "SecureValueError",
    "SecureValueHandling",
    # Base classes
    "UnoSettings",
    "get_config",
    "get_env_value",
    "load_env_files",
    # Loading functions
    "load_settings",
    "requires_secure_access",
    "setup_secure_config",
]
