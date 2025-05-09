"""
Configuration for the Uno logging system.

This module defines the configuration settings for the logging system,
using the Uno configuration system for environment-driven settings.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import Field

from uno.config import UnoSettings, get_env_value
from uno.logging.protocols import LogLevel


class LoggingSettings(UnoSettings):
    """Configuration settings for the logging system."""

    model_config = {"env_prefix": "UNO_LOGGING_"}

    # General settings
    level: LogLevel = Field(default=LogLevel.INFO, description="Default logging level")

    # Output format settings
    json_format: bool = Field(
        default=False, description="Whether to use JSON formatting for logs"
    )

    include_timestamp: bool = Field(
        default=True, description="Whether to include timestamps in logs"
    )

    include_level: bool = Field(
        default=True, description="Whether to include log level in logs"
    )

    # Console output settings
    console_enabled: bool = Field(
        default=True, description="Whether to output logs to console"
    )

    # File output settings
    file_enabled: bool = Field(
        default=False, description="Whether to output logs to file"
    )

    file_path: Optional[str] = Field(
        default=None, description="Path to log file (if file logging is enabled)"
    )

    # Performance settings
    async_logging: bool = Field(
        default=False, description="Whether to use asynchronous logging"
    )

    # Module-specific levels
    module_levels: Dict[str, LogLevel] = Field(
        default_factory=dict, description="Module-specific log levels"
    )

    @classmethod
    def load(cls) -> LoggingSettings:
        """Load logging settings from environment variables.

        Returns:
            LoggingSettings instance
        """
        settings = cls()

        # Parse module-specific levels from environment
        module_level_prefix = f"{cls.model_config['env_prefix']}MODULE_LEVEL_"
        for key, value in get_env_value_pairs().items():
            if key.startswith(module_level_prefix):
                module_name = key[len(module_level_prefix) :].lower()
                try:
                    level = LogLevel.from_string(value)
                    settings.module_levels[module_name] = level
                except ValueError:
                    # Just skip invalid levels
                    pass

        return settings


def get_env_value_pairs() -> Dict[str, str]:
    """Get all environment variables as key-value pairs.

    This is a helper function for parsing module-specific log levels.

    Returns:
        Dictionary of environment variables
    """
    import os

    return {key: value for key, value in os.environ.items() if value}
