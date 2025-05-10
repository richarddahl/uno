# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/config/__init__.py

"""
Public API for the Uno configuration system.

This module exports the core components needed to define and load configuration
settings in the Uno framework.
"""

from __future__ import annotations

from typing import TypeVar

from uno.config.base import ConfigError, Environment, UnoSettings
from uno.config.env_loader import get_env_value, load_env_files
from uno.config.secure import (
    SecureField,
    SecureValue,
    SecureValueError,
    SecureValueHandling,
    requires_secure_access,
)

T = TypeVar("T", bound=UnoSettings)


import asyncio
from typing import Awaitable, Callable


def load_settings(settings_class: type[T], env: Environment | None = None) -> T:
    """Load settings from environment variables and .env files.

    This function loads configuration settings for the specified class,
    leveraging environment variables, .env files, and default values.

    Args:
        settings_class: Settings class to load
        env: Optional environment to target (defaults to current)

    Returns:
        Initialized settings instance
    """
    if env is None:
        env = Environment.get_current()

    return settings_class.from_env(env)


async def load_settings_async(settings_class: type[T], env: Environment | None = None) -> T:
    """
    Async version of load_settings. Prepares for async config sources (e.g. remote secrets).
    """
    # For now, this is just a sync call wrapped for async compatibility.
    # Replace with true async logic if/when needed.
    return load_settings(settings_class, env)


# Simple DI-friendly cache for get_config (per Uno integration principles)
_config_cache: dict[type[UnoSettings], UnoSettings] = {}

def get_config(settings_class: type[T]) -> T:
    """Get configuration for a component.

    This is a convenience wrapper around load_settings with global config caching.

    Args:
        settings_class: Settings class to load

    Returns:
        Initialized settings instance
    """
    # DI-friendly cache: instance-based, not global singleton
    if settings_class in _config_cache:
        return _config_cache[settings_class]  # type: ignore
    config = load_settings(settings_class)
    _config_cache[settings_class] = config
    return config


def setup_secure_config(master_key: str | bytes | None = None) -> None:
    """Set up secure configuration with encryption capabilities.

    This function initializes the encryption system for secure config values.

    Args:
        master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)
    """
    SecureValue.setup_encryption(master_key)


__all__ = [
    "ConfigError",
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
