# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Simple middleware implementations for event handlers.

This module provides basic middleware implementations for logging and timing
event handling operations.
"""

import time
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uno.events.base_event import DomainEvent
    from uno.logging.protocols import LoggerProtocol


class NextMiddlewareCallable(Protocol):
    """Protocol for the next middleware in the chain."""

    async def __call__(self, event: "DomainEvent") -> None: ...


class LoggingMiddleware:
    """
    Middleware for logging event handling.

    Provides structured logging for event handling operations, including
    success and failure states.
    """

    def __init__(self, logger: "LoggerProtocol"):
        """
        Initialize the middleware.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger

    async def process(
        self,
        event: "DomainEvent",
        next_middleware: NextMiddlewareCallable,
    ) -> None:
        """
        Log event handling and pass to next middleware.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            Exception: If an error occurs during processing
        """
        self.logger.debug(
            "Processing event",
            event_type=event.event_type,
            event_id=getattr(event, "event_id", None),
            aggregate_id=getattr(event, "aggregate_id", None),
        )

        try:
            await next_middleware(event)

            self.logger.debug(
                "Event handled successfully",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
            )
        except Exception as e:
            self.logger.error(
                "Error handling event",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
                error=str(e),
                exc_info=e,
            )
            raise


class TimingMiddleware:
    """
    Middleware for timing event handling.

    Measures and logs the time taken to handle events.
    """

    def __init__(self, logger: "LoggerProtocol"):
        """
        Initialize the middleware.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger

    async def process(
        self,
        event: "DomainEvent",
        next_middleware: NextMiddlewareCallable,
    ) -> None:
        """
        Time event handling and pass to next middleware.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            Exception: If an error occurs during processing
        """
        start_time = time.time()

        try:
            await next_middleware(event)

            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            self.logger.debug(
                "Event handled",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
                elapsed_ms=f"{elapsed_ms:.2f}",
            )
        except Exception as e:
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            self.logger.error(
                "Error handling event",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
                elapsed_ms=f"{elapsed_ms:.2f}",
                error=str(e),
            )
            raise
