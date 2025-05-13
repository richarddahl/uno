"""
Configuration for the Uno logging system.

This module defines the configuration settings for the logging system,
using the Uno configuration system for environment-driven settings.
"""

from __future__ import annotations

from typing import Optional
from uno.logging.protocols import LogLevel


# Simplified LoggingSettings class
class LoggingSettings:
    """Simplified configuration settings for the logging system."""

    def __init__(
        self,
        level: str = LogLevel.INFO,
        json_format: bool = False,
        include_timestamp: bool = True,
        include_level: bool = True,
        console_enabled: bool = True,
        file_enabled: bool = False,
        file_path: Optional[str] = None,
    ):
        self.level = level
        self.json_format = json_format
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.console_enabled = console_enabled
        self.file_enabled = file_enabled
        self.file_path = file_path

    @classmethod
    def load(cls) -> LoggingSettings:
        """Load logging settings from environment variables or defaults."""
        import os

        return cls(
            level=os.getenv("UNO_LOGGING_LEVEL", "INFO"),
            json_format=os.getenv("UNO_LOGGING_JSON_FORMAT", "false").lower() == "true",
            include_timestamp=os.getenv("UNO_LOGGING_INCLUDE_TIMESTAMP", "true").lower()
            == "true",
            include_level=os.getenv("UNO_LOGGING_INCLUDE_LEVEL", "true").lower()
            == "true",
            console_enabled=os.getenv("UNO_LOGGING_CONSOLE_ENABLED", "true").lower()
            == "true",
            file_enabled=os.getenv("UNO_LOGGING_FILE_ENABLED", "false").lower()
            == "true",
            file_path=os.getenv("UNO_LOGGING_FILE_PATH"),
        )
