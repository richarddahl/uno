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

T = TypeVar("T", bound=UnoSettings)


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


def get_config(settings_class: type[T]) -> T:
    """Get configuration for a component.

    This is a convenience wrapper around load_settings with global config caching.

    Args:
        settings_class: Settings class to load

    Returns:
        Initialized settings instance
    """
    # In a future implementation, this would include caching
    return load_settings(settings_class)


__all__ = [
    "ConfigError",
    "Environment",
    # Base classes
    "UnoSettings",
    "get_config",
    "get_env_value",
    "load_env_files",
    # Loading functions
    "load_settings",
]
