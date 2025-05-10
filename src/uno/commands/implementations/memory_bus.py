# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Simple in-memory command bus implementation.

This module provides a simplified version of the command bus
that doesn't require explicit logger initialization for backward compatibility.
"""

from __future__ import annotations

from uno.commands.implementations.structural_bus import StructuralCommandBus
from uno.logging import LoggerProtocol, LoggingConfig


class InMemoryCommandBus(StructuralCommandBus):
    """
    Backward-compatible in-memory command bus implementation.

    This class provides a simplified interface that initializes its own logger
    if one is not provided, for backward compatibility with existing code.
    """

    def __init__(self, logger: LoggerProtocol | None = None) -> None:
        """
        Initialize the in-memory command bus with an optional logger.

        If no logger is provided, a default one will be created.

        Args:
            logger: Optional logger service
        """
        # Create a default logger if none is provided
        if logger is None:
            logger = LoggerProtocol(LoggingConfig())

        super().__init__(logger)
