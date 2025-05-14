# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/config/__init__.py

"""
Public API for the Uno configuration system.
"""

from uno.config.base import Environment
from uno.config.settings import (
    UnoSettings,
    load_settings,
    get_config,
    SettingsConfigDict,
)
from uno.config.secure import (
    SecureValue,
    SecureField,
    SecureValueHandling,
    requires_secure_access,
    setup_secure_config,
)
from uno.config.errors import (
    ConfigError,
    ConfigEnvironmentError,
    ConfigFileNotFoundError,
    ConfigMissingKeyError,
    ConfigParseError,
    ConfigValidationError,
    SecureValueError,
)

# Create a cache for configuration objects
_config_cache = {}

__all__ = [
    "Environment",
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
