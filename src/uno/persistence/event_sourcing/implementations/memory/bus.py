# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event bus implementation.

This module provides a fully-featured in-memory implementation of the event bus for testing
and simple applications. It supports metrics, DI-aware handler resolution, and flexible
event serialization.
"""

from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING

from uno.events.base import DomainEvent
from uno.events.errors import EventHandlerError, EventPublishError
from uno.events.metrics import EventMetrics

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uno.events.config import EventsConfig
    from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus:
    """
    Full-featured in-memory event bus for Uno event sourcing.

    Features:
    - DI-aware handler resolution via EventHandlerRegistry
    - Metrics collection and reporting
    - Flexible event serialization supporting Pydantic and traditional models
    - Structured logging and error handling

    Args:
        logger: Logger instance for structured logging
        config: Events configuration settings
        metrics_factory: Optional metrics factory for collecting event metrics

    Type Parameters:
        E: DomainEvent (or subclass)
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        config: EventsConfig,
        metrics_factory: Any | None = None,
    ) -> None:
        """
        Initialize the in-memory event bus.

        Args:
            logger: Logger instance for structured logging
            config: Events configuration settings
            metrics_factory: Optional metrics factory for collecting event metrics
        """
        self.logger = logger
        self.config = config
        self.metrics = (
            EventMetrics(metrics_factory, logger) if metrics_factory else None
        )

        # Import here to avoid circular imports
        from uno.events.registry import EventHandlerRegistry

        # Registry is required for handler resolution
        self.registry = EventHandlerRegistry(logger, getattr(config, "container", None))

    def _canonical_event_dict(self, event: E) -> dict[str, Any]:
        """
        Canonical event serialization for logging, storage, and transport.

        Args:
            event: The domain event to serialize
        Returns:
            Canonical dict representation of the event
        """
        if hasattr(event, "model_dump"):
            return dict(
                event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
            )
        elif hasattr(event, "to_dict"):
            return event.to_dict()
        return dict(event.__dict__)

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> None:
        """
        Publish a domain event to all registered handlers (via DI-aware registry).

        Args:
            event: The domain event to publish
            metadata: Optional metadata to include with the event

        Raises:
            EventPublishError: If there's an error publishing the event
        """
        # Record metrics before publishing
        if self.metrics:
            await self.metrics.record_event_published(event)
            await self.metrics.increment_active_events(event)

        event_type = getattr(event, "event_type", type(event).__name__)
        try:
            await self.logger.info(
                "Publishing event",
                event_type=event_type,
                event_id=getattr(event, "event_id", None),
                event=self._canonical_event_dict(event),
                metadata=metadata or {},
            )

            # Resolve handlers via DI-aware registry (async)
            handlers = await self.registry.resolve_handlers_for_event(event_type)
            if not handlers:
                await self.logger.debug(
                    "No handlers registered for event",
                    event_type=event_type,
                    event_id=getattr(event, "event_id", None),
                )
                # Update metrics after successful no-handler publishing
                if self.metrics:
                    await self.metrics.decrement_active_events(event)
                    await self.metrics.record_event_processed(event)
                return

            from uno.events.handlers import MiddlewareChainBuilder

            for handler in handlers:
                try:
                    chain = MiddlewareChainBuilder(handler, self.logger).build_chain(
                        self.registry._middleware
                    )
                    await chain(event)
                except Exception as exc:
                    await self.logger.error(
                        "Handler failed for event",
                        event_id=getattr(event, "event_id", None),
                        event_type=event_type,
                        handler=type(handler).__name__,
                        error=str(exc),
                        message=str(exc),
                        metadata=metadata,
                        exc_info=True,
                    )
                    # Update metrics for failed events
                    if self.metrics:
                        await self.metrics.record_event_failed(event)
                    raise

            # Update metrics after successful publishing
            if self.metrics:
                await self.metrics.decrement_active_events(event)
                await self.metrics.record_event_processed(event)

        except Exception as exc:
            # Update metrics for failed events
            if self.metrics:
                await self.metrics.record_event_failed(event)

            # Ensure all context values are serializable (stringify exception for logging)
            await self.logger.error(
                "Failed to publish event",
                event_type=event_type,
                error=str(exc),
                message=str(exc),
                exc_info=exc,
            )
            # Ensure the reason includes the original exception message
            raise EventPublishError(event_type=event_type, reason=str(exc)) from exc

    async def publish_many(self, events: list[E]) -> None:
        """
        Publish multiple domain events.

        Args:
            events: List of events to publish

        Raises:
            EventPublishError: If there's an error publishing any event
        """
        for event in events:
            await self.publish(event)


__all__ = ["InMemoryEventBus"]
