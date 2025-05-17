# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py
"""
Logger implementation for the Uno framework.

This module provides the default logger implementation based on Python's
standard logging module, enhanced with structured logging capabilities.
"""

from __future__ import annotations

import logging
from enum import Enum


# Define standard logging levels
class LogLevel(str, Enum):
    """Standard logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def to_stdlib_level(self) -> int:
        """Convert to standard library logging level.

        Returns:
            Standard library logging level integer
        """
        return int(getattr(logging, self.value))

    @classmethod
    def from_string(cls, value: str) -> LogLevel:
        """Convert a string to a LogLevel.

        Args:
            value: String representation of level

        Returns:
            LogLevel enum value

        Raises:
            ValueError: If the string doesn't match a valid level
        """
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Invalid log level: {value}")
