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

def test_event_bus_logs_canonical(caplog: Any) -> None:
    bus = InMemoryEventBus()
    event = ExampleEvent(aggregate_id="agg-1", value=42, extra=None)
    async def fake_handler(e: ExampleEvent) -> None:
        pass
    bus._subscribers[event.event_type] = [fake_handler]
    with caplog.at_level(logging.DEBUG, logger="uno.events.bus"):
        asyncio.run(bus.publish(event))
    canonical = bus._canonical_event_dict(event)
    assert any(
        record.name == "uno.events.bus"
        and record.levelname == "DEBUG"
        and "Publishing event (canonical):" in record.getMessage()
        and str(canonical) in record.getMessage()
        for record in caplog.records
    ), "Canonical event dict not found in logs"

def test_event_publisher_logs_canonical() -> None:
    bus = InMemoryEventBus()
    publisher: EventPublisher = EventPublisher(bus, logger=MagicMock())
    event = ExampleEvent(aggregate_id="agg-1", value=42, extra=None)
    publisher.logger.structured_log = MagicMock()
    bus._subscribers[event.event_type] = [lambda e: None]
    asyncio.run(publisher.publish(event))
    publisher.logger.structured_log.assert_any_call(
        "DEBUG", "Publishing event (canonical)", event=publisher._canonical_event_dict(event)
    )
