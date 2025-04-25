"""
Event-driven architecture implementation for the Uno framework
"""

import asyncio
import datetime
import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import Enum, auto
from typing import Any, Generic, Protocol, TypeVar, cast

from pydantic import BaseModel, ConfigDict

# Import dependencies in correct order
from uno.core.domain._base_types import BaseDomainEvent
from uno.core.errors.result import Failure, Result, Success
from uno.core.logging.logger import LoggerService, LoggingConfig

# Type variables
T = TypeVar("T", bound="DomainEvent")
HandlerFnT = TypeVar("HandlerFnT")


class EventPriority(Enum):
    """Priority levels for event handling.
    
    This enum defines the priority levels for event handlers. Higher priority
    handlers will be executed before lower priority handlers.
    """

    HIGH = auto()    # Execute first
    NORMAL = auto()  # Execute in middle (default)
    LOW = auto()     # Execute last


class EventBusProtocol(Protocol):
    """Protocol for event bus implementations."""

    async def publish(self, event: "DomainEvent", metadata: dict[str, Any] | None = None) -> Result[list[Result[Any, Exception]], Exception]: ...
    async def publish_many(self, events: list["DomainEvent"], metadata: dict[str, Any] | None = None) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]: ...
    def subscribe(
        self,
        handler: Any,
        event_type: type["DomainEvent"] | None = None,
        topic_pattern: str | re.Pattern | None = None,
        priority: "EventPriority" = EventPriority.NORMAL,
    ) -> None: ...
    def unsubscribe(
        self,
        handler: Any,
        event_type: type["DomainEvent"] | None = None,
        topic_pattern: str | re.Pattern | None = None,
    ) -> None: ...


class EventPublisherProtocol(Protocol):
    """Protocol for event publisher implementations."""

    async def publish(self, event: "DomainEvent", metadata: dict[str, Any] | None = None) -> Result[list[Result[Any, Exception]], Exception]: ...
    async def publish_many(self, events: list["DomainEvent"], metadata: dict[str, Any] | None = None) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]: ...
    def add(self, event: "DomainEvent", metadata: dict[str, Any] | None = None) -> None: ...
    def add_many(self, events: list["DomainEvent"], metadata: dict[str, Any] | None = None) -> None: ...
    async def publish_pending(self, metadata: dict[str, Any] | None = None) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]: ...


class DomainEvent(BaseDomainEvent, BaseModel):
    """
    Base class for domain events.

    Domain events represent significant occurrences within the domain model.
    They are immutable records of something that happened.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    
    # Optional correlation and causation IDs for event tracing
    correlation_id: str | None = None
    causation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "DomainEvent":
        """Create event from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def with_metadata(
        self,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        topic: str | None = None,
    ) -> "DomainEvent":
        """
        Create a copy of the event with additional metadata.

        Args:
            correlation_id: Optional correlation ID for distributed tracing
            causation_id: Optional causation ID for event causality chains
            topic: Optional topic for routing

        Returns:
            A new event instance with the additional metadata
        """
        data = self.to_dict()

        if correlation_id:
            data["correlation_id"] = correlation_id

        if causation_id:
            data["causation_id"] = causation_id

        if topic:
            data["topic"] = topic

        return self.__class__(**data)


class EventHandler(Generic[T], ABC):
    """
    Abstract base class for event handlers.

    Event handlers process domain events by executing business logic
    in response to the events.
    """

    def __init__(self, event_type: type[T], name: str | None = None):
        """
        Initialize the event handler.

        Args:
            event_type: The type of event this handler can process
            name: Optional name for the handler, defaults to the class name
        """
        self.event_type = event_type
        self.name = name or self.__class__.__name__

    @abstractmethod
    async def handle(self, event: T) -> Any:
        """
        Handle an event.

        Args:
            event: The event to handle
            
        Returns:
            Handler result, may vary based on implementation
        """
        pass

    def can_handle(self, event: DomainEvent) -> bool:
        """
        Check if this handler can handle the given event.

        Args:
            event: The event to check

        Returns:
            True if this handler can handle the event, False otherwise
        """
        return isinstance(event, self.event_type)


# Type aliases for event handler functions
SyncEventHandler = Callable[[T], None]
AsyncEventHandler = Callable[[T], Awaitable[None]]
EventHandlerFn = SyncEventHandler[T] | AsyncEventHandler[T]


class EventSubscription(Generic[T]):
    """
    Event subscription holding a handler function or object.

    This class tracks a subscription for a specific event type or topic,
    along with its handler function or object.
    """

    def __init__(
        self,
        handler: EventHandler[T] | EventHandlerFn[T],
        event_type: type[T] | None = None,
        topic_pattern: str | re.Pattern | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        is_async: bool | None = None,
    ):
        """
        Initialize the event subscription.

        Args:
            handler: The event handler function or object
            event_type: The type of event this subscription is for
            topic_pattern: Optional topic pattern for topic-based routing
            priority: The priority of this subscription
            is_async: Whether the handler is asynchronous (auto-detected if None)
        """
        self.handler = handler
        self.event_type = event_type
        self.priority = priority

        # Compile topic pattern if provided as string
        if isinstance(topic_pattern, str):
            self.topic_pattern = re.compile(topic_pattern)
        else:
            self.topic_pattern = topic_pattern

        # Auto-detect if handler is async
        if is_async is None:
            self.is_async = asyncio.iscoroutinefunction(
                handler.handle if isinstance(handler, EventHandler) else handler
            )
        else:
            self.is_async = is_async

    def matches_event(self, event: DomainEvent) -> bool:
        """
        Check if this subscription matches the given event.

        Args:
            event: The event to check

        Returns:
            True if this subscription matches the event, False otherwise
        """
        # Check event type if specified
        if self.event_type and not isinstance(event, self.event_type):
            return False

        # Check topic pattern if specified
        # If the event has no topic but we have a pattern, it doesn't match
        if not event.topic and self.topic_pattern:
            return False

        # If we have a pattern and the event has a topic, check the pattern
        return not (
            self.topic_pattern
            and not self.topic_pattern.match(event.topic)
        )

    async def invoke(self, event: DomainEvent) -> Result[Any, Exception]:
        """
        Invoke the handler for the given event.

        Args:
            event: The event to handle
            
        Returns:
            Result with the handler's return value on success, or Exception on failure
        """
        try:
            # Cast event to the expected type
            typed_event = cast("T", event)

            if isinstance(self.handler, EventHandler):
                # Handler object
                result = await self.handler.handle(typed_event)
                return Success(result)
            elif self.is_async:
                # Async handler function
                result = await self.handler(typed_event)
                return Success(result)
            else:
                # Sync handler function - run in executor
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, self.handler, typed_event)
                return Success(result)
        except Exception as e:
            return Failure(e)


class EventBus(EventBusProtocol):
    """
    Event bus for publishing and subscribing to domain events.

    The event bus enables loosely coupled communication between different
    parts of the application using an event-driven architecture.
    Implements EventBusProtocol.
    """

    def __init__(self, logger: LoggerService):
        """
        Initialize the event bus.

        Args:
            logger: DI-injected LoggerService instance
        """
        self.logger = logger
        self._subscriptions: list[EventSubscription] = []
        self._publish_time: dict[str, float] = {}  # Event type -> last publish time

    def subscribe(
        self,
        handler: EventHandler[T] | EventHandlerFn[T],
        event_type: type[T] | None = None,
        topic_pattern: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """
        Subscribe to events of a specific type or topic.

        Args:
            handler: Event handler function or object
            event_type: The type of event to subscribe to
            topic_pattern: Optional topic pattern for topic-based routing
            priority: Handler priority
        """
        # If handler is an EventHandler, use its event_type if not provided
        if isinstance(handler, EventHandler) and event_type is None:
            event_type = handler.event_type

        # Create subscription
        subscription = EventSubscription(
            handler=handler,
            event_type=event_type,
            topic_pattern=topic_pattern,
            priority=priority,
        )

        # Add subscription to list, sorted by priority
        self._subscriptions.append(subscription)
        self._subscriptions.sort(key=lambda s: s.priority.value)

        self.logger.debug(
            f"Subscribed handler to events: "
            f"event_type={event_type.__name__ if event_type else 'Any'}, "
            f"topic_pattern={topic_pattern or 'Any'}, "
            f"priority={priority.name}"
        )

    def unsubscribe(
        self,
        handler: EventHandler[T] | EventHandlerFn[T],
        event_type: type[T] | None = None,
        topic_pattern: str | None = None,
    ) -> None:
        """
        Unsubscribe from events of a specific type or topic.

        Args:
            handler: Event handler function or object
            event_type: The type of event to unsubscribe from
            topic_pattern: Optional topic pattern for topic-based routing
        """
        before = len(self._subscriptions)
        self._subscriptions = [
            s
            for s in self._subscriptions
            if not (
                s.handler == handler
                and (event_type is None or s.event_type == event_type)
                and (
                    topic_pattern is None
                    or (
                        s.topic_pattern.pattern == topic_pattern
                        if hasattr(s.topic_pattern, "pattern")
                        else s.topic_pattern == topic_pattern
                    )
                )
            )
        ]
        after = len(self._subscriptions)
        self.logger.debug(
            f"Unsubscribed handler from events: "
            f"event_type={event_type.__name__ if event_type else 'Any'}, "
            f"topic_pattern={topic_pattern or 'Any'}, "
            f"removed={before - after}"
        )

    async def publish(self, event: DomainEvent, metadata: dict[str, Any] | None = None) -> Result[list[Result[Any, Exception]], Exception]:
        """
        Publish an event to all matching subscribers.

        Args:
            event: The event to publish
            metadata: Optional metadata to associate with the event

        Returns:
            Result containing a list of Results from each handler, or an Exception if the overall process failed
        """
        event_type_name = event.__class__.__name__
        topic = event.topic or ""

        self.logger.debug(f"Publishing event: {event_type_name} (topic={topic})")
        self._publish_time[event_type_name] = time.time()

        # Get matching subscriptions
        matching_subscriptions = [
            s for s in self._subscriptions if s.matches_event(event)
        ]

        if not matching_subscriptions:
            self.logger.debug(f"No handlers registered for event: {event_type_name}")
            return Success([])

        # Invoke handlers and collect results
        results: list[Result[Any, Exception]] = []
        
        for subscription in matching_subscriptions:
            try:
                result = await subscription.invoke(event)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e!s}")
                results.append(Failure(e))
                
        return Success(results)

    async def publish_many(self, events: list[DomainEvent], metadata: dict[str, Any] | None = None) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]:
        """
        Publish multiple events.

        Args:
            events: The events to publish
            metadata: Optional metadata to associate with all events

        Returns:
            Result containing results from publishing each event, or an Exception if the overall process failed
        """
        # Create shared metadata if needed
        event_metadata = metadata or {}
        
        # Track results for each event published
        results: list[Result[list[Result[Any, Exception]], Exception]] = []
        
        try:
            for event in events:
                # Include event-specific metadata from the event itself if available
                combined_metadata = {**event_metadata}
                
                # Publish the event with combined metadata
                event_result = await self.publish(event, combined_metadata)
                
                # Store the result
                if event_result.is_success():
                    results.append(event_result)
                else:
                    # If publishing failed, propagate the failure but continue with other events
                    self.logger.warning(
                        f"Failed to publish event {event.__class__.__name__}: {event_result.error}"
                    )
                    results.append(Failure(event_result.error))
                    
            return Success(results)
        except Exception as e:
            self.logger.error(f"Error in publish_many: {e}")
            return Failure(e)


class EventStore(ABC):
    """
    Abstract base class for event stores.

    Event stores persist domain events for reliable processing and
    event sourcing.
    """

    @abstractmethod
    async def append(self, event: DomainEvent) -> Result[None, Exception]:
        """
        Append an event to the event store.

        Args:
            event: The event to append
        
        Returns:
            Result with None on success, or an error on failure
        """
        pass

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: str | None = None,
        aggregate_type: str | None = None,
        since_version: int | None = None,
        since_timestamp: datetime.datetime | None = None,
        limit: int | None = None,
    ) -> Result[list[DomainEvent], Exception]:
        """
        Get events from the event store.

        Args:
            aggregate_id: Optional aggregate ID to filter by
            aggregate_type: Optional aggregate type to filter by
            since_version: Optional minimum version to filter by
            since_timestamp: Optional minimum timestamp to filter by
            limit: Optional maximum number of events to return

        Returns:
            Result with list of events matching the criteria, or an error on failure
        """
        pass


class InMemoryEventStore(EventStore):
    """
    In-memory implementation of the event store.

    This implementation stores events in memory, which is useful for
    testing and simple applications.
    """

    def __init__(self, logger: LoggerService):
        """
        Initialize the in-memory event store.

        Args:
            logger: DI-injected LoggerService instance
        """
        self.logger = logger
        self._events: list[DomainEvent] = []

    async def append(self, event: DomainEvent) -> Result[None, Exception]:
        """
        Append an event to the event store.

        Args:
            event: The event to append
            
        Returns:
            Result with None on success, or an error on failure
        """
        try:
            self._events.append(event)
            self.logger.debug(f"Event appended to store: {event.__class__.__name__}")
            return Success(None)
        except Exception as e:
            self.logger.error(f"Failed to append event to store: {e!s}")
            return Failure(e)

    async def get_events(
        self,
        aggregate_id: str | None = None,
        aggregate_type: str | None = None,
        since_version: int | None = None,
        since_timestamp: datetime.datetime | None = None,
        limit: int | None = None,
    ) -> Result[list[DomainEvent], Exception]:
        """
        Get events from the event store.

        Args:
            aggregate_id: Optional aggregate ID to filter by
            aggregate_type: Optional aggregate type to filter by
            since_version: Optional minimum version to filter by
            since_timestamp: Optional minimum timestamp to filter by
            limit: Optional maximum number of events to return

        Returns:
            Result with list of events matching the criteria, or an error on failure
        """
        try:
            # Start with all events
            filtered_events = self._events.copy()

            # Apply filters
            if aggregate_id:
                filtered_events = [
                    e for e in filtered_events if e.aggregate_id == aggregate_id
                ]

            if aggregate_type:
                filtered_events = [
                    e for e in filtered_events if e.aggregate_type == aggregate_type
                ]

            if since_version:
                filtered_events = [e for e in filtered_events if e.version >= since_version]

            if since_timestamp:
                filtered_events = [
                    e for e in filtered_events if e.timestamp >= since_timestamp
                ]

            # Sort by timestamp
            filtered_events.sort(key=lambda e: e.timestamp)

            # Apply limit
            if limit:
                filtered_events = filtered_events[:limit]

            self.logger.debug(f"Retrieved {len(filtered_events)} events from store")
            return Success(filtered_events)
        except Exception as e:
            self.logger.error(f"Failed to retrieve events from store: {e!s}")
            return Failure(e)


class EventPublisher(EventPublisherProtocol):
    """
    Helper class for publishing events.

    Provides a convenient interface for collecting, persisting, and publishing
    events to an event bus. Implements EventPublisherProtocol.
    """

    def __init__(
        self,
        event_bus: EventBusProtocol,
        event_store: EventStore | None = None,
        logger: LoggerService | None = None,
    ):
        """
        Initialize the event publisher.

        Args:
            event_bus: The event bus to publish events to
            event_store: Optional event store for event persistence
            logger: DI-injected LoggerService instance
        """
        self.event_bus = event_bus
        self.event_store = event_store
        self.logger = logger  # Must be a LoggerService instance
        self._pending_events: list[DomainEvent] = []

    def add(self, event: DomainEvent) -> None:
        """
        Add an event to be published later.

        Args:
            event: The event to add
        """
        self._pending_events.append(event)

    def add_many(self, events: list[DomainEvent]) -> None:
        """
        Add multiple events to be published later.

        Args:
            events: The events to add
        """
        self._pending_events.extend(events)

    async def publish_pending(self, metadata: dict[str, Any] | None = None) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]:
        """
        Publish all pending events.

        This method publishes all events that have been added with add()
        or add_many() and clears the list of pending events.
        
        Args:
            metadata: Optional metadata to associate with all events
            
        Returns:
            Result containing the results of publishing each event
        """
        events = self._pending_events.copy()
        self._pending_events.clear()

        if not events:
            self.logger.debug("No pending events to publish.")
            return Success([])

        # Track results for persistence and publishing
        persist_results = []
        
        # Persist events if event store is available
        if self.event_store:
            for event in events:
                persist_result = await self.event_store.append(event)
                persist_results.append(persist_result)
                
                if persist_result.is_success():
                    self.logger.info(
                        f"Persisted event {event.event_type} with ID {event.event_id}."
                    )
                else:
                    self.logger.error(
                        f"Failed to persist event {event.event_type} with ID {event.event_id}: "
                        f"{persist_result.error}"
                    )

        # Publish events to the event bus and return the results
        result = await self.event_bus.publish_many(events, metadata)
        self.logger.info(f"Published {len(events)} pending events to event bus.")
        
        return result

    async def publish(self, event: DomainEvent, metadata: dict[str, Any] | None = None) -> Result[list[Result[Any, Exception]], Exception]:
        """
        Publish an event immediately.

        Args:
            event: The event to publish
            metadata: Optional metadata to associate with the event
            
        Returns:
            Result containing the results of publishing the event
        """
        # Track results
        results = []
        
        # Persist event if event store is available
        if self.event_store:
            persist_result = await self.event_store.append(event)
            results.append(persist_result)
            
            if persist_result.is_success():
                self.logger.info(f"Persisted event {event.event_type} with ID {event.event_id}.")
            else:
                self.logger.error(
                    f"Failed to persist event {event.event_type} with ID {event.event_id}: "
                    f"{persist_result.error}"
                )
                # We continue publishing even if persistence fails

        # Publish event to the event bus
        publish_result = await self.event_bus.publish(event, metadata)
        
        if publish_result.is_success():
            self.logger.info(f"Published event {event.event_type} with ID {event.event_id} to event bus.")
        else:
            self.logger.error(
                f"Failed to publish event {event.event_type} with ID {event.event_id}: "
                f"{publish_result.error}"
            )
            
        return publish_result

    async def publish_many(self, events: list[DomainEvent], metadata: dict[str, Any] | None = None) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]:
        """
        Publish multiple events immediately.

        Args:
            events: The events to publish
            metadata: Optional metadata to associate with all events
            
        Returns:
            Result containing the results of publishing the events
        """
        # Track results for persistence operations
        persist_results = []
        
        # Persist events if event store is available
        if self.event_store:
            for event in events:
                persist_result = await self.event_store.append(event)
                persist_results.append(persist_result)
                
                if persist_result.is_success():
                    self.logger.info(f"Persisted event {event.event_type} with ID {event.event_id}.")
                else:
                    self.logger.error(
                        f"Failed to persist event {event.event_type} with ID {event.event_id}: "
                        f"{persist_result.error}"
                    )
                    # We continue with other events even if one fails

        # Publish events to the event bus
        publish_result = await self.event_bus.publish_many(events, metadata)
        
        if publish_result.is_success():
            self.logger.info(f"Published {len(events)} events to event bus.")
        else:
            self.logger.error(f"Failed to publish events: {publish_result.error}")
            
        return publish_result


# Factory functions for event system components
# These implement the Service Locator pattern for use when DI is not available
# In production code, proper DI container should be used instead

# Initialize lazily loaded singletons
_event_system_components = {
    "logger": None,
    "event_bus": None,
    "event_store": None,
    "publisher": None,
}


def get_logger_service() -> LoggerService:
    """Get the default LoggerService instance for event system components.
    
    Returns:
        A shared LoggerService instance
    """
    if _event_system_components["logger"] is None:
        # Create a default logger if not provided through DI
        _event_system_components["logger"] = LoggerService(LoggingConfig())
    
    return _event_system_components["logger"]


def set_logger_service(logger: LoggerService) -> None:
    """Set a custom LoggerService for all event system components.
    
    Args:
        logger: The LoggerService instance to use
    """
    _event_system_components["logger"] = logger
    
    # Reset other components to ensure they use the new logger
    _event_system_components["event_bus"] = None
    _event_system_components["event_store"] = None
    _event_system_components["publisher"] = None


def get_event_bus() -> EventBus:
    """Get the default event bus.
    
    Returns:
        The default EventBus instance, creating it if necessary
    """
    if _event_system_components["event_bus"] is None:
        # Create a default event bus if not provided through DI
        _event_system_components["event_bus"] = EventBus(get_logger_service())
    
    return _event_system_components["event_bus"]


def set_event_bus(event_bus: EventBus) -> None:
    """Set a custom EventBus as the default.
    
    Args:
        event_bus: The EventBus instance to use
    """
    _event_system_components["event_bus"] = event_bus
    
    # Reset publisher to ensure it uses the new event bus
    _event_system_components["publisher"] = None


def get_event_store() -> EventStore:
    """Get the default event store.
    
    Returns:
        The default EventStore instance, creating it if necessary
    """
    if _event_system_components["event_store"] is None:
        # Create a default in-memory event store if not provided through DI
        _event_system_components["event_store"] = InMemoryEventStore(get_logger_service())
    
    return _event_system_components["event_store"]


def set_event_store(event_store: EventStore) -> None:
    """Set a custom EventStore as the default.
    
    Args:
        event_store: The EventStore instance to use
    """
    _event_system_components["event_store"] = event_store
    
    # Reset publisher to ensure it uses the new event store
    _event_system_components["publisher"] = None


def get_event_publisher() -> EventPublisher:
    """Get the default event publisher.
    
    Returns:
        The default EventPublisher instance, creating it if necessary
    """
    if _event_system_components["publisher"] is None:
        # Create a default publisher if not provided through DI
        _event_system_components["publisher"] = EventPublisher(
            get_event_bus(),
            get_event_store(),
            get_logger_service()
        )
    
    return _event_system_components["publisher"]


def set_event_publisher(publisher: EventPublisher) -> None:
    """Set a custom EventPublisher as the default.
    
    Args:
        publisher: The EventPublisher instance to use
    """
    _event_system_components["publisher"] = publisher


def subscribe(
    event_type: type[DomainEvent] | None = None,
    topic_pattern: str | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    *,
    event_bus: EventBusProtocol | None = None,
) -> Callable[[HandlerFnT], HandlerFnT]:
    """
    Decorator for subscribing functions or methods to events (DI-friendly).

    Registers a function or method as an event handler for a specific event type or topic.
    Supports handler priorities and topic pattern matching. Optionally allows DI of the event bus.

    Args:
        event_type: The type of event to subscribe to
        topic_pattern: Optional topic pattern for topic-based routing
        priority: Handler priority
        event_bus: The EventBus instance to register with (defaults to global bus)

    Returns:
        The decorated function or method
    """

    def decorator(handler: HandlerFnT) -> HandlerFnT:
        bus = event_bus or get_event_bus()
        bus.subscribe(
            handler=cast("Any", handler),
            event_type=event_type,
            topic_pattern=topic_pattern,
            priority=priority,
        )
        return handler

    return decorator


def register_event_handler(
    handler: HandlerFnT,
    event_type: type[DomainEvent] | None = None,
    topic_pattern: str | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    *,
    event_bus: EventBusProtocol | None = None,
) -> None:
    """
    Register an event handler function or object with the event bus (DI/config-friendly).

    Args:
        handler: The handler function or object
        event_type: The type of event to subscribe to
        topic_pattern: Optional topic pattern for topic-based routing
        priority: Handler priority
        event_bus: The EventBus instance to register with (defaults to global bus)
    """
    bus = event_bus or get_event_bus()
    bus.subscribe(
        handler=cast("Any", handler),
        event_type=event_type,
        topic_pattern=topic_pattern,
        priority=priority,
    )
