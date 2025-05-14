# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Public API for the Uno logging system.

This module exports the public API for logging in the Uno framework, providing
structured logging capabilities and context management.
"""

from uno.logging.config import LoggingSettings
from uno.logging.errors import ErrorLogger, ErrorSeverity, get_error_logger
from uno.logging.logger import UnoLogger, get_logger
from uno.logging.protocols import LogLevel, LoggerProtocol, LoggerFactoryProtocol

__all__ = [
    # Core interfaces
    "LoggerProtocol",
    "LoggerFactoryProtocol",
    "LogLevel",
    # Implementation
    "UnoLogger",
    "ErrorLogger",
    "ErrorSeverity",
    # Settings
    "LoggingSettings",
    # Factory functions
    "get_logger",
    "get_error_logger",
]
