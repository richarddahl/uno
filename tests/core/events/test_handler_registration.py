
import pytest

from uno.core.events.events import (
    DomainEvent,
    EventBus,
    EventPriority,
    register_event_handler,
    subscribe,
)
from uno.core.logging.logger import LoggerService, LoggingConfig


class FakeEvent(DomainEvent):
    event_type: str = "test"
    payload: dict[str, str] = {}


@pytest.mark.asyncio
async def test_decorator_registration_with_priority_and_topic():
    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    bus = EventBus(logger)
    results: list[str] = []

    @subscribe(
        event_type=FakeEvent,
        topic_pattern="foo",
        priority=EventPriority.HIGH,
        event_bus=bus,
    )
    async def handler_high(event: FakeEvent):
        results.append("high")

    @subscribe(
        event_type=FakeEvent,
        topic_pattern="foo",
        priority=EventPriority.LOW,
        event_bus=bus,
    )
    async def handler_low(event: FakeEvent):
        results.append("low")

    event = FakeEvent(aggregate_id="a", event_type="test", topic="foo", payload={})
    await bus.publish(event)
    # Should invoke handlers in priority order
    assert results == ["high", "low"]


@pytest.mark.asyncio
async def test_config_registration_and_filtering():
    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    bus = EventBus(logger)
    results: list[str] = []

    async def handler_topic(event: FakeEvent):
        results.append(f"topic:{event.topic}")

    async def handler_type(event: FakeEvent):
        results.append(f"type:{event.event_type}")

    register_event_handler(
        handler_topic, event_type=FakeEvent, topic_pattern="bar", event_bus=bus
    )
    register_event_handler(handler_type, event_type=FakeEvent, event_bus=bus)

    event1 = FakeEvent(aggregate_id="b", event_type="test", topic="bar", payload={})
    event2 = FakeEvent(aggregate_id="b", event_type="test", topic="baz", payload={})
    await bus.publish(event1)
    await bus.publish(event2)
    # handler_topic only fires for topic 'bar', handler_type for any topic
    assert results == ["topic:bar", "type:test", "type:test"]


@pytest.mark.asyncio
async def test_di_registration_with_multiple_buses():
    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    bus1 = EventBus(logger)
    bus2 = EventBus(logger)
    results1: list[str] = []
    results2: list[str] = []

    async def handler1(event: FakeEvent):
        results1.append("bus1")

    async def handler2(event: FakeEvent):
        results2.append("bus2")

    register_event_handler(handler1, event_type=FakeEvent, event_bus=bus1)
    register_event_handler(handler2, event_type=FakeEvent, event_bus=bus2)

    event = FakeEvent(aggregate_id="c", event_type="test", topic="multi", payload={})
    await bus1.publish(event)
    await bus2.publish(event)
    assert results1 == ["bus1"]
    assert results2 == ["bus2"]
