from typing import Any, Callable, TypeVar, cast
from uno.core.events.base_event import DomainEvent
from uno.core.events.interfaces import EventBusProtocol
from uno.core.events.priority import EventPriority
from uno.core.logging.logger import LoggerService

HandlerFnT = TypeVar("HandlerFnT")


def subscribe(
    event_type: type[DomainEvent] | None = None,
    topic_pattern: str | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    *,
    event_bus: EventBusProtocol | None = None,
    logger: LoggerService,
) -> Callable[[HandlerFnT], HandlerFnT]:
    """
    Decorator to register an event handler with the event bus.
    Args:
        event_type: Type of event to subscribe to
        topic_pattern: Optional topic pattern
        priority: Handler priority (default NORMAL)
        event_bus: The EventBus instance (defaults to global bus)
        logger: Logger for registration actions
    Returns:
        Decorated handler
    """
    def decorator(handler: HandlerFnT) -> HandlerFnT:
        bus = event_bus or get_event_bus()
        bus.subscribe(
            handler=cast("Any", handler),
            event_type=event_type,
            topic_pattern=topic_pattern,
            priority=priority,
        )
        logger.structured_log(
            "info",
            "Subscribed handler",
            handler=str(handler),
            event_type=str(event_type),
            topic_pattern=topic_pattern,
            priority=str(priority)
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
    logger: LoggerService,
) -> None:
    """
    Register an event handler function or object with the event bus (DI/config-friendly).
    Args:
        handler: The handler function or object
        event_type: The type of event to subscribe to
        topic_pattern: Optional topic pattern for topic-based routing
        priority: Handler priority
        event_bus: The EventBus instance to register with (defaults to global bus)
        logger: Logger for registration actions
    """
    bus = event_bus or get_event_bus()
    bus.subscribe(
        handler=cast("Any", handler),
        event_type=event_type,
        topic_pattern=topic_pattern,
        priority=priority,
    )
    logger.structured_log(
        "info",
        "Registered handler",
        handler=str(handler),
        event_type=str(event_type),
        topic_pattern=topic_pattern,
        priority=str(priority)
    )

# Import get_event_bus from factory to avoid circular import at module top-level
from uno.core.events.factory import get_event_bus
