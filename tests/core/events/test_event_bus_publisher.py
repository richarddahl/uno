import asyncio
import logging
from typing import Any
from unittest.mock import MagicMock

from pydantic import Field

from uno.core.events.base_event import DomainEvent
from uno.core.events.bus import InMemoryEventBus
from uno.core.events.publisher import EventPublisher


class ExampleEvent(DomainEvent):
    aggregate_id: str
    value: int = Field(...)
    extra: str | None = None


def test_event_bus_logs_canonical():
    logger = MagicMock()
    bus = InMemoryEventBus(logger)
    event = ExampleEvent(aggregate_id="agg-1", value=42, extra=None)

    async def fake_handler(e: ExampleEvent) -> None:
        pass

    bus._subscribers[event.event_type] = [fake_handler]
    asyncio.run(bus.publish(event))
    canonical = bus._canonical_event_dict(event)
    logger.debug.assert_any_call(f"Publishing event (canonical): {canonical}")

    # Simulate error and check error logging
    async def error_handler(e: ExampleEvent) -> None:
        raise Exception("fail")

    bus._subscribers[event.event_type] = [error_handler]
    asyncio.run(bus.publish(event))
    # Robust: check for structured_log or error fallback
    if hasattr(logger, "structured_log"):
        assert logger.structured_log.called
    else:
        assert logger.error.called


def test_event_publisher_logs_canonical() -> None:
    logger = MagicMock()
    bus = InMemoryEventBus(logger)
    publisher: EventPublisher = EventPublisher(bus, logger=MagicMock())
    event = ExampleEvent(aggregate_id="agg-1", value=42, extra=None)
    publisher.logger.structured_log = MagicMock()
    bus._subscribers[event.event_type] = [lambda e: None]
    asyncio.run(publisher.publish(event))
    publisher.logger.structured_log.assert_any_call(
        "DEBUG",
        "Publishing event (canonical)",
        event=publisher._canonical_event_dict(event),
    )
