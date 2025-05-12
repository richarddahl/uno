# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Event processor implementation.

This module provides the event processor that coordinates the invocation of event
handlers with proper async patterns and cancellation support.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, TYPE_CHECKING

from uno.events.retry import retry_async, RetryError
from uno.events.errors import EventProcessingError
from uno.events.protocols import (
    EventHandlerProtocol,
    EventRegistryProtocol,
)

if TYPE_CHECKING:
    from uno.events.protocols import EventProcessorProtocol


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from uno.domain.protocols import DomainEventProtocol
    from uno.logging.protocols import LoggerProtocol


class EventProcessor:
    """
    Event processor implementation.

    Coordinates the invocation of event handlers with proper async patterns
    and cancellation support.
    """

    def __init__(
        self,
        registry: EventRegistryProtocol,
        logger: LoggerProtocol,
    ) -> None:
        """
        Initialize the event processor.

        Args:
            registry: The registry containing event handlers
            logger: Logger for structured logging
        """
        self.registry = registry
        self.logger = logger

    async def process(
        self,
        event: DomainEventProtocol,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Process an event with all registered handlers.

        Args:
            event: The domain event to process
            context: Optional context information for event processing

        Raises:
            EventProcessingError: If processing the event fails
        """
        try:
            handlers = await self.registry.get_handlers_for_event(event)

            if not handlers:
                await self.logger.debug(
                    "No handlers found for event",
                    event_type=getattr(event, "event_type", type(event).__name__),
                    event_id=getattr(event, "event_id", None),
                )
                return

            await self.logger.debug(
                "Processing event with handlers",
                event_type=getattr(event, "event_type", type(event).__name__),
                event_id=getattr(event, "event_id", None),
                handler_count=len(handlers),
            )

            # Use retry_async for each handler
            async def run_with_retry(handler: EventHandlerProtocol) -> None:
                try:
                    await retry_async(
                        handler.handle,
                        event,
                        context,
                        max_attempts=getattr(self, "retry_attempts", 3),
                        delay=0.1,
                        backoff=2.0,
                        exceptions=(Exception,),
                    )
                except RetryError as e:
                    await self.logger.error(
                        "Handler failed after retries",
                        handler=handler.__class__.__name__,
                        event_type=getattr(event, "event_type", type(event).__name__),
                        event_id=getattr(event, "event_id", None),
                        error=str(e),
                    )
                    raise EventProcessingError(event=event, reason=str(e)) from e

            await asyncio.gather(*(run_with_retry(handler) for handler in handlers))
        except Exception as e:
            await self.logger.error(
                "Error processing event",
                event_type=getattr(event, "event_type", type(event).__name__),
                event_id=getattr(event, "event_id", None),
                error=str(e),
                exc_info=e,
            )
            raise EventProcessingError(
                event=event,
                reason=str(e),
            ) from e

    async def process_with_cancellation(
        self,
        event: DomainEventProtocol,
        context: dict[str, Any] | None = None,
        cancellation_token: Any = None,
    ) -> None:
        """
        Process an event with all registered handlers, with cancellation support.

        Args:
            event: The domain event to process
            context: Optional context information for event processing
            cancellation_token: Token that can be used to cancel processing

        Raises:
            asyncio.CancelledError: If event processing is cancelled
            EventProcessingError: If processing the event fails
        """
        if cancellation_token is None:
            # If no cancellation token provided, create a simple task
            # that can be cancelled via asyncio standard mechanisms
            await self.process(event, context)
            return

        try:
            handlers = await self.registry.get_handlers_for_event(event)

            if not handlers:
                await self.logger.debug(
                    "No handlers found for event",
                    event_type=getattr(event, "event_type", type(event).__name__),
                    event_id=getattr(event, "event_id", None),
                )
                return

            await self.logger.debug(
                "Processing event with handlers and cancellation support",
                event_type=getattr(event, "event_type", type(event).__name__),
                event_id=getattr(event, "event_id", None),
                handler_count=len(handlers),
            )

            async def run_with_retry(handler: EventHandlerProtocol) -> None:
                try:
                    await retry_async(
                        handler.handle,
                        event,
                        context,
                        max_attempts=getattr(self, "retry_attempts", 3),
                        delay=0.1,
                        backoff=2.0,
                        exceptions=(Exception,),
                    )
                except RetryError as e:
                    await self.logger.error(
                        "Handler failed after retries (cancellation)",
                        handler=handler.__class__.__name__,
                        event_type=getattr(event, "event_type", type(event).__name__),
                        event_id=getattr(event, "event_id", None),
                        error=str(e),
                    )
                    raise EventProcessingError(event=event, reason=str(e)) from e

            tasks = [
                asyncio.create_task(run_with_retry(handler)) for handler in handlers
            ]

            async with self._cancellation_context(tasks, cancellation_token):
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.ALL_COMPLETED
                )

                # If there are still pending tasks, cancel them
                for task in pending:
                    task.cancel()

                # Wait for all tasks to complete or be cancelled
                if pending:
                    await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)

        except asyncio.CancelledError:
            await self.logger.info(
                "Event processing cancelled",
                event_type=getattr(event, "event_type", type(event).__name__),
                event_id=getattr(event, "event_id", None),
            )
            raise
        except Exception as e:
            await self.logger.error(
                "Error processing event",
                event_type=getattr(event, "event_type", type(event).__name__),
                event_id=getattr(event, "event_id", None),
                error=str(e),
                exc_info=e,
            )
            raise EventProcessingError(
                event=event,
                reason=str(e),
            ) from e

    @contextlib.asynccontextmanager
    async def _cancellation_context(
        self, tasks: list[asyncio.Task], cancellation_token: Any
    ) -> AsyncGenerator:
        """
        Context manager for cancellation handling.

        This context manager sets up a monitor task that will cancel all handler tasks
        if the cancellation token is triggered.

        Args:
            tasks: The tasks to cancel if the token is triggered
            cancellation_token: Token that can be used to cancel processing

        Yields:
            None
        """
        # Setup monitoring in a task
        monitor_task = None

        # Define a monitoring coroutine that watches for cancellation
        async def monitor_cancellation():
            try:
                # Different types of cancellation tokens might have different interfaces
                if hasattr(cancellation_token, "wait"):
                    await cancellation_token.wait()
                elif hasattr(cancellation_token, "cancelled"):
                    await cancellation_token.cancelled()
                elif isinstance(cancellation_token, asyncio.Event):
                    await cancellation_token.wait()
                else:
                    # If the token doesn't have a standard interface, wait forever
                    # The context manager will clean up when exiting
                    while True:
                        await asyncio.sleep(0.1)

                # If we get here, the token was triggered, so cancel all tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
            except asyncio.CancelledError:
                # The monitor task itself was cancelled, which is fine
                pass

        # Start the monitor task
        monitor_task = asyncio.create_task(monitor_cancellation())

        try:
            # Yield control back to the caller
            yield
        finally:
            # Always clean up the monitor task
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await monitor_task
