# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol defining a logger interface"""

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message"""
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an informational message"""
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message"""
        ...

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message"""
        ...

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message"""
        ...


@runtime_checkable
class LoggerFactoryProtocol(Protocol):
    """Protocol for a factory that creates loggers"""

    def create_logger(self, component_name: str) -> LoggerProtocol:
        """Create a logger for a specific component"""
        ...
