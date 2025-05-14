"""
Base configuration classes and utilities for the Uno framework.

This module provides the foundation for environment-driven configuration
with support for env files, environment variables, and type validation.
"""

from __future__ import annotations

import os
import re
import json
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, cast, get_origin, get_args
from uno.types import T

from pydantic import model_serializer, model_validator, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

from uno.config.secure import SecureValue, SecureValueHandling
from uno.config.errors import ConfigError


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
                code="INVALID_ENVIRONMENT",
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




def get_env_var(name: str, case_sensitive: bool = True) -> str | None:
    """
    Get environment variable with optional case-insensitive support.

    Args:
        name: Environment variable name
        case_sensitive: Whether to do a case-sensitive lookup

    Returns:
        Value of environment variable or None if not found
    """
    if case_sensitive:
        return os.environ.get(name)

    # Case-insensitive lookup
    for env_name, value in os.environ.items():
        if env_name.lower() == name.lower():
            return value

    return None


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

    # Use PrivateAttr instead of trying to set a ClassVar
    _secure_values_initialized: bool = PrivateAttr(default=False)
    _instance_secure_fields: dict[str, SecureValueHandling] = PrivateAttr(
        default_factory=dict
    )

    def __init__(self, **data: Any) -> None:
        """Initialize settings instance."""
        # Initialize the private attributes first
        super().__init__(**data)
        # No need to set _secure_fields here as we use _instance_secure_fields

    @property
    def _secure_fields(self) -> dict[str, SecureValueHandling]:
        """Access the instance's secure fields.

        Returns:
            Dictionary of secure field names to handling strategies
        """
        return self._instance_secure_fields

    @classmethod
    async def from_env(cls: type[T], env: Environment | None = None) -> T:
        """Load settings from environment or specific env file (Pydantic v2 compatible)."""
        if env is None:
            env = Environment.get_current()

        # Determine the env file to use
        env_file = f".env.{env.value}"
        additional_env_files = []

        # Look for component-specific env files like .env.database or .env.app
        component_name = None
        if cls.__name__.lower().endswith("settings"):
            component_name = cls.__name__.lower().replace("settings", "")
            component_env_file = f".env.{component_name}"

            # Search paths to look for component files
            search_paths = [
                Path("."),  # Current directory
                Path.cwd(),  # Working directory
                Path.cwd().parent,  # Parent of working directory
                Path(__file__).parent.parent.parent.parent,  # Project root
            ]

            # Try to find the component-specific env file
            for search_path in search_paths:
                file_path = search_path / component_env_file
                if file_path.exists():
                    additional_env_files.append(str(file_path))
                    break  # Stop once we find one

        # Create settings config with all env files
        model_config_override = dict(getattr(cls, "model_config", {}))
        env_files = []

        # Base .env should always be first
        if Path(".env").exists():
            env_files.append(".env")

        # Add environment-specific file if it exists
        if Path(env_file).exists():
            env_files.append(env_file)

        # Add component-specific files - ensure they override previous files
        env_files.extend(additional_env_files)

        # Add local overrides for non-production environments ONLY
        if env != Environment.PRODUCTION:  # Only add if NOT in production
            local_env = ".env.local"
            if Path(local_env).exists():
                env_files.append(local_env)

            # Also handle component-specific local files
            if component_name:
                component_local_env = f".env.{component_name}.local"
                if Path(component_local_env).exists():
                    env_files.append(component_local_env)
        # For production, explicitly ensure no local files are included
        else:
            # Filter out any .local files that might have been added
            env_files = [f for f in env_files if not str(f).endswith(".local")]

        # Set the env_file in the config
        model_config_override["env_file"] = env_files

        # Dynamically create a subclass with the correct env_file in model_config
        dynamic_settings: type[T] = type(
            "DynamicEnvSettings",
            (cls,),
            {"model_config": SettingsConfigDict(**model_config_override)},
        )

        # Get environment overrides and create instance
        overrides = cls._get_environment_overrides()
        return dynamic_settings(**overrides)

    @classmethod
    def _get_environment_overrides(cls) -> dict[str, Any]:
        """
        Get environment variable overrides for settings.

        Scans environment variables once and resolves field values based on:
        1. Exact match with model field name
        2. Match with field alias, if defined
        3. Match with field name in uppercase with underscores

        Returns:
            Dictionary of field names and their values from environment
        """
        # Scan environment only once
        env_vars = os.environ

        # Create single mapping dictionary for field names to env variable candidates
        field_to_env_candidates: dict[str, list[str]] = {}

        # Get model fields and their potential environment variable names
        model_fields = cls.model_fields

        # Build mapping of field names to possible environment variable forms
        for field_name, field_info in model_fields.items():
            # Skip if field doesn't allow env var overrides
            if getattr(field_info, "exclude_from_env", False):
                continue

            # List of potential environment variable names for this field
            candidates = []

            # 1. Exact field name
            candidates.append(field_name)

            # 2. Field alias if available
            if hasattr(field_info, "alias") and field_info.alias:
                candidates.append(field_info.alias)

            # 3. Uppercase with underscores (common env var convention)
            env_style_name = re.sub(r"(?<!^)(?=[A-Z])", "_", field_name).upper()
            candidates.append(env_style_name)

            # 4. Add prefix if defined
            if hasattr(cls, "env_prefix") and cls.env_prefix:
                prefix = cls.env_prefix
                prefixed_candidates = [f"{prefix}{c}" for c in candidates]
                candidates.extend(prefixed_candidates)

            field_to_env_candidates[field_name] = candidates

        # Single pass through candidate mapping to find matches
        result: dict[str, Any] = {}
        for field_name, candidates in field_to_env_candidates.items():
            field_info = model_fields[field_name]

            # Check each candidate in priority order
            for env_var_name in candidates:
                if env_var_name in env_vars:
                    # Convert environment string to appropriate type
                    env_value = env_vars[env_var_name]
                    field_type = field_info.annotation

                    try:
                        # Convert string value to field's type
                        typed_value = cls._convert_env_value(env_value, field_type)
                        result[field_name] = typed_value
                        # Stop at first match (highest priority)
                        break
                    except ValueError:
                        # Log invalid type conversion
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(
                            f"Environment variable {env_var_name} value '{env_value}' "
                            f"could not be converted to type {field_type}"
                        )

        return result

    @classmethod
    def _convert_env_value(cls, value: str, target_type: type) -> Any:
        """
        Convert environment variable string value to the target type.

        Args:
            value: String value from environment
            target_type: Target type to convert to

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
        """
        # Handle basic types
        if target_type == str:
            return value
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == bool:
            return value.lower() in ("true", "1", "yes", "y", "on")
        # Handle list types - comma-separated values
        elif get_origin(target_type) == list:
            item_type = get_args(target_type)[0]
            items = [s.strip() for s in value.split(",")]
            return [cls._convert_env_value(item, item_type) for item in items]
        # Handle dict types from JSON string
        elif get_origin(target_type) == dict:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse JSON for dict type: {value}")
        # Handle other complex types with best effort
        else:
            try:
                return target_type(value)
            except Exception as e:
                raise ValueError(f"Failed to convert to {target_type}: {e}")

    @model_validator(mode="after")
    def _handle_secure_fields(self) -> UnoSettings:
        """Process secure fields and wrap them in SecureValue containers."""
        if self._secure_values_initialized:
            return self

        # Extract secure field information from the schema
        schema = self.model_json_schema()
        properties = schema.get("properties", {})


 
        # Find all secure fields
        for field_name, field_schema in properties.items():
            if field_schema.get("secure"):
                # Convert handling to string if it's not already
                handling_value = field_schema.get("handling", "mask")
                # Ensure handling is a string for the enum
                if isinstance(handling_value, dict):
                    # If it's a dict, try to get a string value from it
                    handling_value = handling_value.get("value", "mask")
                handling_str = str(handling_value)
                self._instance_secure_fields[field_name] = SecureValueHandling(
                    handling_str
                )

        # Process each secure field
        for field_name, handling in self._instance_secure_fields.items():
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
        d = {}
        for k, v in super().__dict__.items():
            # Skip internal pydantic attributes
            if k.startswith("_"):
                continue

            # Mask secure fields
            if k in self._instance_secure_fields:
                d[k] = "******"
            # Unwrap SecureValue for non-secure fields
            elif isinstance(v, SecureValue):
                d[k] = v.get_value()
            # Handle nested UnoSettings objects
            elif isinstance(v, UnoSettings):
                d[k] = v._mask_secure_fields()
            else:
                d[k] = v

        return d
