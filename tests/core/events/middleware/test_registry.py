from typing import Any

import pytest

from uno.core.events.base_event import DomainEvent
from uno.core.events.interfaces import EventBusProtocol
from uno.core.events.priority import EventPriority
from uno.core.events.registry import register_event_handler, subscribe
from uno.core.logging.logger import LoggerService, LoggingConfig

class FakeLoggerService(LoggerService):
    def __init__(self) -> None:
        super().__init__(LoggingConfig())
        self.logs: list[dict[str, Any]] = []
    def structured_log(self, level: str, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logs.append({
            'level': level,
            'msg': msg,
            'args': args,
            'kwargs': kwargs
        })

class FakeEvent(DomainEvent):
    pass

class FakeEventBus(EventBusProtocol):
    def __init__(self) -> None:
        self.subscriptions: list[dict[str, Any]] = []
    def subscribe(
        self,
        handler: Any,
        event_type: Any = None,
        topic_pattern: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        self.subscriptions.append({
            'handler': handler,
            'event_type': event_type,
            'topic_pattern': topic_pattern,
            'priority': priority
        })
    async def publish(self, event: Any, metadata: dict[str, Any] | None = None) -> Any:
        pass
    async def publish_many(self, events: list[Any]) -> Any:
        pass

@pytest.fixture
def fake_logger() -> FakeLoggerService:
    return FakeLoggerService()

@pytest.fixture
def fake_event_bus() -> FakeEventBus:
    return FakeEventBus()

def test_register_event_handler_logs_and_registers(
    fake_logger: FakeLoggerService, fake_event_bus: FakeEventBus
) -> None:
    def handler(event: Any) -> None:
        pass
    register_event_handler(
        handler=handler,
        event_type=FakeEvent,
        topic_pattern='topic.*',
        priority=EventPriority.HIGH,
        event_bus=fake_event_bus,
        logger=fake_logger,
    )
    assert len(fake_event_bus.subscriptions) == 1
    sub = fake_event_bus.subscriptions[0]
    assert sub['handler'] == handler
    assert sub['event_type'] == FakeEvent
    assert sub['topic_pattern'] == 'topic.*'
    assert sub['priority'] == EventPriority.HIGH
    assert any('Registered handler' in log['msg'] for log in fake_logger.logs)

def test_subscribe_decorator_logs_and_registers(
    fake_logger: FakeLoggerService, fake_event_bus: FakeEventBus
) -> None:
    calls: dict[str, bool] = {}
    @subscribe(event_type=FakeEvent, topic_pattern='foo', priority=EventPriority.LOW, event_bus=fake_event_bus, logger=fake_logger)
    def handler(event: Any) -> None:
        calls['called'] = True
    # Simulate event dispatch
    handler(FakeEvent())
    assert len(fake_event_bus.subscriptions) == 1
    sub = fake_event_bus.subscriptions[0]
    assert sub['handler'] == handler
    assert sub['event_type'] == FakeEvent
    assert sub['topic_pattern'] == 'foo'
    assert sub['priority'] == EventPriority.LOW
    assert any('Subscribed handler' in log['msg'] for log in fake_logger.logs)

def test_register_event_handler_requires_logger(fake_event_bus: FakeEventBus) -> None:
    def handler(event: Any) -> None:
        pass
    with pytest.raises(TypeError):
        register_event_handler(
            handler=handler,
            event_type=FakeEvent,
            event_bus=fake_event_bus,
            # logger omitted intentionally
        )

def test_subscribe_decorator_requires_logger(fake_event_bus: FakeEventBus) -> None:
    with pytest.raises(TypeError):
        @subscribe(event_type=FakeEvent, event_bus=fake_event_bus)  # logger omitted
        def handler(event: Any) -> None:
            pass
