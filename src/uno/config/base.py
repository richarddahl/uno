"""
Base configuration classes and utilities for the Uno framework.

This module provides the foundation for environment-driven configuration
with support for env files, environment variables, and type validation.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, TypeVar, cast

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

    # Use PrivateAttr instead of trying to set a ClassVar
    _secure_fields_data: ClassVar[dict[str, SecureValueHandling]] = {}
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
        overrides = cls._get_environment_overrides(env)
        return dynamic_settings(**overrides)

    @classmethod
    def _get_environment_overrides(
        cls, env: Environment | None = None
    ) -> dict[str, Any]:
        """Get environment-specific overrides from env vars."""
        # Extract environment variables that match the prefix
        result: dict[str, Any] = {}
        prefix = cls.model_config.get("env_prefix", "")

        # Add special handling for test environment
        test_mode = (
            env == Environment.TESTING or os.environ.get("UNO_TEST_MODE") == "true"
        )

        # Create a mapping from various formats to field names
        field_aliases: dict[str, str] = {}

        # Generate class prefixes for environment variables
        class_name = cls.__name__
        if class_name.endswith("Settings"):
            class_name = class_name[:-8]  # Remove "Settings" suffix

        class_prefix = class_name.upper() + "__"
        alt_class_prefix = (
            "_".join([s.upper() for s in class_name]) + "__"
            if "_" not in class_name
            else ""
        )

        # First, build the field aliases map
        for field_name, field_info in cls.model_fields.items():
            # Add direct field name mappings
            field_aliases[field_name] = field_name
            field_aliases[field_name.upper()] = field_name
            field_aliases[field_name.lower()] = field_name

            # Add class-prefixed mappings
            field_aliases[f"{class_prefix}{field_name}"] = field_name
            field_aliases[f"{class_prefix}{field_name.upper()}"] = field_name

            if alt_class_prefix:
                field_aliases[f"{alt_class_prefix}{field_name}"] = field_name
                field_aliases[f"{alt_class_prefix}{field_name.upper()}"] = field_name

            # Add settings-prefixed mappings
            settings_prefix = cls.__name__.upper() + "__"
            field_aliases[f"{settings_prefix}{field_name}"] = field_name
            field_aliases[f"{settings_prefix}{field_name.upper()}"] = field_name

            # Add prefix mappings if specified
            if prefix:
                field_aliases[f"{prefix}{field_name}"] = field_name
                field_aliases[f"{prefix}{field_name.upper()}"] = field_name

            # Handle field aliases
            if hasattr(field_info, "alias") and field_info.alias:
                alias = field_info.alias
                field_aliases[alias] = field_name
                field_aliases[alias.upper()] = field_name
                field_aliases[alias.lower()] = field_name

                # Add prefixed versions of aliases
                field_aliases[f"{class_prefix}{alias}"] = field_name
                field_aliases[f"{settings_prefix}{alias}"] = field_name
                if alt_class_prefix:
                    field_aliases[f"{alt_class_prefix}{alias}"] = field_name

            # Handle alias priority
            elif hasattr(field_info, "alias_priority") and field_info.alias_priority:
                try:
                    for a in field_info.alias_priority:  # type: ignore
                        if a:
                            field_aliases[a] = field_name
                            field_aliases[a.upper()] = field_name
                            field_aliases[a.lower()] = field_name

                            field_aliases[f"{class_prefix}{a}"] = field_name
                            field_aliases[f"{settings_prefix}{a}"] = field_name
                            if alt_class_prefix:
                                field_aliases[f"{alt_class_prefix}{a}"] = field_name
                except TypeError:
                    if field_info.alias_priority:
                        alias = str(field_info.alias_priority)
                        field_aliases[alias] = field_name
                        field_aliases[alias.upper()] = field_name
                        field_aliases[alias.lower()] = field_name

                        field_aliases[f"{class_prefix}{alias}"] = field_name
                        field_aliases[f"{settings_prefix}{alias}"] = field_name
                        if alt_class_prefix:
                            field_aliases[f"{alt_class_prefix}{alias}"] = field_name

        # Process environment variables with enhanced matching
        # First process UNO_TEST_* variables which should have highest priority in tests
        if test_mode:
            test_overrides = {}
            for key, value in os.environ.items():
                if key.startswith("UNO_TEST_") and not key == "UNO_TEST_MODE":
                    # Remove the UNO_TEST_ prefix to get the actual field name
                    clean_key = key[9:]  # "UNO_TEST_" is 9 chars

                    # Direct match
                    if clean_key in field_aliases:
                        test_overrides[field_aliases[clean_key]] = value
                    elif clean_key.upper() in field_aliases:
                        test_overrides[field_aliases[clean_key.upper()]] = value
                    elif clean_key.lower() in field_aliases:
                        test_overrides[field_aliases[clean_key.lower()]] = value
                    else:
                        # Try with class prefixes
                        for possible_prefix in [
                            class_prefix,
                            alt_class_prefix,
                            settings_prefix,
                        ]:
                            if possible_prefix and clean_key.startswith(
                                possible_prefix
                            ):
                                field_key = clean_key[len(possible_prefix) :]
                                if field_key in field_aliases:
                                    test_overrides[field_aliases[field_key]] = value
                                    break
                                elif field_key.upper() in field_aliases:
                                    test_overrides[field_aliases[field_key.upper()]] = (
                                        value
                                    )
                                    break

            # Apply test overrides with highest priority
            result.update(test_overrides)

        # Create a reverse alias mapping for more efficient lookups
        reversed_aliases: dict[str, list[str]] = {}
        for alias, field in field_aliases.items():
            if field not in reversed_aliases:
                reversed_aliases[field] = []
            reversed_aliases[field].append(alias)

        # Process regular environment variables - improved matching algorithm
        for key, value in os.environ.items():
            # Skip test variables which we already processed
            if test_mode and key.startswith("UNO_TEST_"):
                continue

            # Direct field match
            if key in cls.model_fields:
                result[key] = value
                continue

            # First look for direct matches in aliases
            if key in field_aliases:
                result[field_aliases[key]] = value
                continue

            # Try standard environment variable formats
            normalized_key = key.lower().replace("-", "_")

            # Check for environ vars in format ENV_VAR or ENV_PREFIX_VAR
            for field_name in cls.model_fields:
                if key.upper() == field_name.upper():
                    result[field_name] = value
                    break

                # Check with common prefixes
                if key.upper() == f"{prefix.upper()}{field_name.upper()}":
                    result[field_name] = value
                    break

                # Check with class name prefix
                if (
                    key.upper() == f"{class_name.upper()}_{field_name.upper()}"
                    or key.upper() == f"{class_name.upper()}__{field_name.upper()}"
                ):
                    result[field_name] = value
                    break

                # Try to match with class and settings variants
                if key.upper().endswith(
                    f"__{field_name.upper()}"
                ) or key.upper().endswith(f"_{field_name.upper()}"):
                    result[field_name] = value
                    break

            # If we haven't found a match yet, try with prefixes
            if key not in result:
                clean_key = key
                for possible_prefix in [
                    prefix,
                    class_prefix,
                    alt_class_prefix,
                    settings_prefix,
                ]:
                    if possible_prefix and key.startswith(possible_prefix):
                        clean_key = key[len(possible_prefix) :]

                        if clean_key in field_aliases:
                            result[field_aliases[clean_key]] = value
                            break
                        elif clean_key.upper() in field_aliases:
                            result[field_aliases[clean_key.upper()]] = value
                            break
                        elif clean_key.lower() in field_aliases:
                            result[field_aliases[clean_key.lower()]] = value
                            break

        return result

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
                self._instance_secure_fields[field_name] = SecureValueHandling(handling_str)

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
                d[k] = "********"
            # Unwrap SecureValue for non-secure fields
            elif isinstance(v, SecureValue):
                d[k] = v.get_value()
            # Handle nested UnoSettings objects
            elif isinstance(v, UnoSettings):
                d[k] = v._mask_secure_fields()
            else:
                d[k] = v

        return d
