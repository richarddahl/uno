# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py
"""
Configuration for the Uno logging system.

This module defines the configuration settings for the logging system,
using the Uno configuration system for environment-driven settings.
"""

from __future__ import annotations

from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from uno.logging.level import LogLevel


class LoggingSettings(BaseSettings):
    """
    Configuration settings for the Uno logging system.
    Loads from environment variables using Pydantic v2's env support.
    """

    model_config = SettingsConfigDict(
        env_prefix="UNO_LOGGING_",
        extra="ignore",
        case_sensitive=False,
        frozen=False,
    )

    level: str = Field(default=LogLevel.INFO, description="Log level")
    json_format: bool = Field(default=False, description="Enable JSON log format")
    include_timestamp: bool = Field(
        default=True, description="Include timestamp in logs"
    )
    include_level: bool = Field(default=True, description="Include log level in logs")
    console_enabled: bool = Field(default=True, description="Enable console logging")
    file_enabled: bool = Field(default=False, description="Enable file logging")
    file_path: str | None = Field(default=None, description="Path to log file")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: Any) -> str:
        """Validate that the level is a valid log level."""
        if not isinstance(v, str):
            raise ValueError(f"Log level must be a string, got {type(v).__name__}")
        try:
            return LogLevel.from_string(v).value
        except ValueError:
            raise ValueError(f"Invalid log level: {v}")

    @classmethod
    def load(cls) -> LoggingSettings:
        """
        Load logging settings from environment variables or defaults using Pydantic v2.
        Returns:
            LoggingSettings: Loaded and validated settings instance.
        """
        return cls()
