"""Base classes for event store implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, AsyncIterator, Generic, Optional, Type, TypeVar, final

from uno.logging.protocols import LoggerProtocol

from pydantic import BaseModel

from uno.domain.events import DomainEvent
from uno.event_store.config import EventStoreSettings, default_settings
from uno.event_store.errors import EventStoreError

# Type variable for events
E = TypeVar("E", bound=DomainEvent)

# Type alias for logger
LoggerLike = LoggerProtocol


class EventStore(Generic[E], ABC):
    """Abstract base class for event store implementations.

    This class provides common functionality and integration with Uno's core systems,
    including logging, configuration, and error handling.
    """

    def __init__(
        self,
        *,
        settings: EventStoreSettings | None = None,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """Initialize the event store with optional dependencies.

        Args:
            settings: Optional settings instance. If not provided, defaults will be used.
            logger: Optional logger instance. If not provided, a default logger will be created.
        """
        self._settings = settings or default_settings
        self._logger = logger or logging.getLogger("uno.event_store")

    @property
    def settings(self) -> EventStoreSettings:
        """Get the event store settings."""
        return self._settings

    @property
    def logger(self) -> LoggerProtocol:
        """Get the event store logger."""
        return self._logger

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the event store.

        This method should be implemented by subclasses to establish connections
        to their respective storage backends.
        """
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the event store.

        This method should be implemented by subclasses to clean up resources.
        """
        raise NotImplementedError

    async def __aenter__(self) -> EventStore[E]:
        """Async context manager entry.

        Returns:
            The event store instance.
        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type if an exception was raised, None otherwise.
            exc_val: Exception value if an exception was raised, None otherwise.
            exc_tb: Traceback if an exception was raised, None otherwise.
        """
        await self.disconnect()

    @abstractmethod
    async def append(
        self,
        aggregate_id: str,
        events: list[E],
        expected_version: int | None = None,
    ) -> None:
        """Append events to the event store.

        Args:
            aggregate_id: The aggregate ID.
            events: The events to append.
            expected_version: The expected version of the aggregate.

        Raises:
            EventStoreAppendError: If the append operation fails.
            EventStoreVersionConflictError: If there's a version conflict.

        Example:
            ```python
            async with event_store as store:
                await store.append("aggregate-1", [event1, event2])
            ```
        """
        if not events:
            self._logger.debug("No events to append for aggregate %s", aggregate_id)
            return

        self._logger.debug(
            "Appending %d events for aggregate %s (expected version: %s)",
            len(events),
            aggregate_id,
            expected_version or "latest",
        )
        raise NotImplementedError

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None,
    ) -> AsyncIterator[E]:
        """Get events for an aggregate.

        Args:
            aggregate_id: The aggregate ID.
            from_version: The version to start from (inclusive).
            to_version: The version to end at (inclusive). If None, gets all events.

        Yields:
            The events in order of version.

        Raises:
            EventStoreGetEventsError: If the operation fails.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_events_of_type(
        self, event_type: type[E], limit: int = 100, offset: int = 0
    ) -> list[E]:
        """Get events of a specific type.

        Args:
            event_type: The event type class.
            limit: Maximum number of events to return.
            offset: Number of events to skip.

        Returns:
            A list of events of the specified type.

        """
        raise NotImplementedError

    @abstractmethod
    async def get_events_by_aggregate_type(
        self, aggregate_type: str, limit: int = 100, offset: int = 0
    ) -> list[E]:
        """Get events for a specific aggregate type.

        Args:
            aggregate_type: The aggregate type.
            limit: Maximum number of events to return.
            offset: Number of events to skip.

        Returns:
            A list of events for the specified aggregate type.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_last_event(self, aggregate_id: str) -> Optional[E]:
        """Get the last event for an aggregate.

        Args:
            aggregate_id: The aggregate ID.

        Returns:
            The last event or None if no events exist.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_aggregate_version(self, aggregate_id: str) -> int:
        """Get the current version of an aggregate.

        Args:
            aggregate_id: The aggregate ID.

        Returns:
            The current version of the aggregate.
        """
        raise NotImplementedError

    @abstractmethod
    async def optimize(self) -> None:
        """Optimize the event store for better performance."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the event store and release resources."""
        await self.disconnect()
