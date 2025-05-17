# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Public API for the Uno logging system.

This module exports the public API for logging in the Uno framework, providing
structured logging capabilities and context management.
"""

from __future__ import annotations

from uno.logging.config import LoggingSettings
from uno.logging.errors import (
    ErrorLogger,
    ErrorSeverity,
    LoggingError,
    get_error_logger,
)
from uno.logging.error_logger import EnhancedErrorLogger, get_enhanced_error_logger
from uno.logging.logger import UnoLogger, get_logger
from uno.logging.level import LogLevel
from uno.logging.protocols import LoggerProtocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerFactoryProtocol

__all__ = [
    # Core interfaces
    "LoggerProtocol",
    "LoggerFactoryProtocol",
    "LogLevel",
    # Implementation
    "UnoLogger",
    "ErrorLogger",
    "EnhancedErrorLogger",
    "ErrorSeverity",
    "LoggingError",
    # Settings
    "LoggingSettings",
    # Factory functions
    "get_logger",
    "get_error_logger",
    "get_enhanced_error_logger",
]
