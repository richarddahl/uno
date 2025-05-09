"""
Base configuration classes and utilities for the Uno framework.

This module provides the foundation for environment-driven configuration
with support for env files, environment variables, and type validation.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import model_serializer, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from uno.config.secure import SecureValue, SecureValueHandling
from uno.errors import ErrorCategory, UnoError


class ConfigError(UnoError):
    """Base class for configuration-related errors."""

    def __init__(
        self, message: str, error_code: str | None = None, **context: Any
    ) -> None:
        """Initialize a configuration error.

        Args:
            message: Human-readable error message
            error_code: Error code without prefix
            **context: Additional context information
        """
        super().__init__(
            message=message,
            error_code=f"CONFIG_{error_code}" if error_code else "CONFIG_ERROR",
            category=ErrorCategory.CONFIG,
            **context,
        )


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
                f"Invalid environment: {value}",
                error_code="INVALID_ENVIRONMENT",
                provided_value=value,
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


T = TypeVar("T", bound="UnoSettings")


class UnoSettings(BaseSettings):
    """Base settings class for all Uno configuration.

    This class extends Pydantic's BaseSettings with Uno-specific functionality.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        validate_default=True,
    )

    # Keep track of secure fields
    _secure_fields: ClassVar[dict[str, SecureValueHandling]] = {}

    # Track if we've initialized secure values for this instance
    _secure_values_initialized: bool = False

    @classmethod
    def from_env(cls: type[T], env: Environment | None = None) -> T:
        """Load settings from environment or specific env file (Pydantic v2 compatible).

        Args:
            env: Optional environment to load settings for

        Returns:
            Settings instance
        """
        if env is None:
            env = Environment.get_current()

        # Determine the env file to use
        env_file = f".env.{env.value}"
        if Path(env_file).exists():
            # Dynamically create a subclass with the correct env_file in model_config
            dynamic_env_settings: type[T] = type(
                "DynamicEnvSettings",
                (cls,),
                {
                    "model_config": SettingsConfigDict(
                        **{**getattr(cls, "model_config", {}), "env_file": env_file}
                    )
                },
            )

            return dynamic_env_settings(**cls._get_environment_overrides())

        # Fallback to default .env file (already in model_config)
        return cls(**cls._get_environment_overrides())

    @classmethod
    def _get_environment_overrides(cls) -> dict[str, Any]:
        """Get environment-specific overrides from env vars.

        Returns:
            Dictionary of environment variable overrides
        """
        # Extract environment variables that match the prefix
        result: dict[str, Any] = {}
        prefix = cls.model_config.get("env_prefix", "")

        for key, value in os.environ.items():
            if prefix and not key.startswith(prefix):
                continue

            # Strip prefix if present
            clean_key = key[len(prefix) :] if key.startswith(prefix) else key
            result[clean_key] = value

        return result

    @model_validator(mode="after")
    def _handle_secure_fields(self) -> UnoSettings:
        """Process secure fields and wrap them in SecureValue containers.

        This method is called after the model is validated and initialized,
        and it processes any fields marked as secure to ensure proper handling.

        Returns:
            The processed settings object
        """
        if self._secure_values_initialized:
            return self

        # Extract secure field information from the schema
        schema = self.model_json_schema()
        properties = schema.get("properties", {})

        # Find all secure fields
        secure_fields: dict[str, SecureValueHandling] = {}
        for field_name, field_schema in properties.items():
            if field_schema.get("secure"):
                handling = field_schema.get("handling", "mask")
                secure_fields[field_name] = SecureValueHandling(handling)

        # Update class-level tracking of secure fields
        self._secure_fields.update(secure_fields)

        # Process each secure field
        for field_name, handling in secure_fields.items():
            value = getattr(self, field_name, None)

            # Skip if already a SecureValue
            if isinstance(value, SecureValue):
                continue

            # Skip if None
            if value is None:
                continue

            # Wrap in SecureValue
            secure_value = SecureValue(value, handling=handling)
            setattr(self, field_name, secure_value)

        self._secure_values_initialized = True
        return self

    @model_serializer(mode="plain")
    def _mask_secure_fields(self) -> dict[str, Any]:
        """Mask secure fields and optionally unwrap SecureValue for non-masked fields."""
        d = super().__dict__.copy()
        for k in self._secure_fields:
            if k in d:
                d[k] = "********"
        for k, v in d.items():
            if k not in self._secure_fields and isinstance(v, SecureValue):
                d[k] = v.get_value()
        return d
