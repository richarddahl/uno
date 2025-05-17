# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Environment definitions for the Uno configuration system.
"""

from __future__ import annotations

import os
from enum import Enum
from uno.config.errors import ConfigError, CONFIG_ENVIRONMENT_ERROR


class Environment(str, Enum):
    """Supported environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, value: str | None) -> Environment:
        """Convert a string to an Environment enum value.

        Args:
            value: String representation of environment

        Returns:
            Environment enum value

        Raises:
            ConfigError: If the string doesn't match a valid environment
        """
        if value is None:
            return cls.DEVELOPMENT

        normalized = value.lower().strip()

        if normalized in ("dev", "development"):
            return cls.DEVELOPMENT
        elif normalized in ("test", "testing"):
            return cls.TESTING
        elif normalized in ("prod", "production"):
            return cls.PRODUCTION
        else:
            raise ConfigError(
                message=f"Invalid environment: {value}",
                code=CONFIG_ENVIRONMENT_ERROR,
                context={"provided_value": value},
            )

    @classmethod
    def get_current(cls) -> Environment:
        """Get the current environment based on env vars.

        This checks UNO_ENV or fallbacks to ENVIRONMENT or ENV

        Returns:
            Current environment enum value
        """
        env_var = (
            os.environ.get("UNO_ENV")
            or os.environ.get("ENVIRONMENT")
            or os.environ.get("ENV")
        )
        return cls.from_string(env_var)
