"""
Integration tests for Uno event dispatch with DI-aware handler resolution and async lifecycle support.
"""

import sys
import os
import pytest
from typing import Any

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from uno.di.container import Container
from uno.di.errors import ServiceNotRegisteredError
from uno.events.bus import InMemoryEventBus
from uno.events.config import EventsConfig
from uno.events.errors import EventPublishError
from uno.logging import get_logger

# --- Fake Event and Handler ---


class FakeEvent:
    event_type: str = "FakeEvent"

    def __init__(self, payload: str) -> None:
        self.payload: str = payload
        self._metadata: dict[str, Any] = {}  # Initialize metadata storage


class FakeHandler:
    def __init__(self) -> None:
        self.called: bool = False
        self.entered: bool = False
        self.exited: bool = False
        self.payload: str | None = None

    async def __aenter__(self) -> "FakeHandler":
        self.entered = True
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> bool:
        self.exited = True
        return False

    async def handle(self, event: FakeEvent) -> None:
        self.called = True
        self.payload = event.payload


# --- Middleware for testing order and error handling ---
class RecordingMiddleware:
    def __init__(self, record: list[str]) -> None:
        self.record = record

    async def process(self, event: Any, next_middleware: Any) -> None:
        self.record.append("before")
        await next_middleware(event)
        self.record.append("after")


@pytest.mark.asyncio
async def test_di_event_handler_resolution_and_lifecycle() -> None:
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    # Register handler as a singleton instance
    handler_instance = FakeHandler()
    await container.register_singleton(FakeHandler, lambda: handler_instance)
    await bus.registry.register_handler("FakeEvent", FakeHandler)

    # Publish event and assert handler is resolved and context manager entered/exited
    assert handler_instance.entered is False
    assert handler_instance.exited is False
    assert handler_instance.called is False
    await bus.publish(FakeEvent("foo"))
    assert handler_instance.entered is True
    assert handler_instance.exited is True
    assert handler_instance.called is True
    assert handler_instance.payload == "foo"
    assert handler_instance.exited
    assert handler_instance.payload == "foo"


@pytest.mark.asyncio
async def test_event_middleware_chain_and_error_handling() -> None:
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[str] = []
    middleware = RecordingMiddleware(record)
    await bus.registry.register_middleware(middleware)

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            record.append("handler")

    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    await bus.publish(FakeEvent("bar"))
    assert record == ["before", "handler", "after"]


from uno.di.errors import ServiceNotRegisteredError


@pytest.mark.asyncio
async def test_event_handler_di_resolution_failure() -> None:
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container
    # Handler not registered in DI
    await bus.registry.register_handler("FakeEvent", FakeHandler)
    with pytest.raises(EventPublishError) as excinfo:
        await bus.publish(FakeEvent("fail"))
    # Ensure the cause is ServiceNotRegisteredError
    assert isinstance(excinfo.value.__cause__, ServiceNotRegisteredError)


@pytest.mark.asyncio
async def test_event_handler_missing() -> None:
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container
    # No handler registered
    # Should not raise, but nothing should happen
    await bus.publish(FakeEvent("none"))


@pytest.mark.asyncio
async def test_middleware_error_propagation() -> None:
    """
    If middleware raises an exception, the handler is not called and error is propagated.
    """
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[str] = []

    class ErrorMiddleware:
        async def process(self, event: Any, next_middleware: Any) -> None:
            record.append("before-error")
            raise RuntimeError("middleware boom")

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            record.append("handler-called")

    await bus.registry.register_middleware(ErrorMiddleware())
    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    with pytest.raises(EventPublishError) as excinfo:
        await bus.publish(FakeEvent("err"))
    assert "middleware boom" in str(excinfo.value)
    assert record == ["before-error"]  # handler not called


@pytest.mark.asyncio
async def test_multiple_middleware_order() -> None:
    """
    Multiple middleware are executed in the correct order.
    """
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[str] = []

    class MW1:
        async def process(self, event: Any, next_middleware: Any) -> None:
            record.append("mw1-before")
            await next_middleware(event)
            record.append("mw1-after")

    class MW2:
        async def process(self, event: Any, next_middleware: Any) -> None:
            record.append("mw2-before")
            await next_middleware(event)
            record.append("mw2-after")

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            record.append("handler")

    await bus.registry.register_middleware(MW1())
    await bus.registry.register_middleware(MW2())
    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    await bus.publish(FakeEvent("order"))
    assert record == ["mw1-before", "mw2-before", "handler", "mw2-after", "mw1-after"]


@pytest.mark.asyncio
async def test_middleware_short_circuit() -> None:
    """
    Middleware that does not call next_middleware prevents handler execution.
    """
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[str] = []

    class ShortCircuitMiddleware:
        async def process(self, event: Any, next_middleware: Any) -> None:
            record.append("short-circuit")
            # Do not call next_middleware

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            record.append("handler")

    await bus.registry.register_middleware(ShortCircuitMiddleware())
    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    await bus.publish(FakeEvent("skip"))
    assert record == ["short-circuit"]  # handler not called


@pytest.mark.asyncio
async def test_async_handler_error_handling() -> None:
    """
    Test that if a handler raises an exception, it's properly wrapped and logged,
    and that middleware "after" logic is still executed.
    """
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[str] = []

    class ErrorMiddleware:
        async def process(self, event: Any, next_middleware: Any) -> None:
            record.append("before")
            try:
                await next_middleware(event)
            finally:
                record.append("after")

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            record.append("handler")
            raise ValueError("handler boom")

    await bus.registry.register_middleware(ErrorMiddleware())
    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    with pytest.raises(EventPublishError) as excinfo:
        await bus.publish(FakeEvent("error"))
    assert "handler boom" in str(excinfo.value)
    assert record == ["before", "handler", "after"]  # middleware "after" still called


@pytest.mark.asyncio
async def test_middleware_event_modification() -> None:
    """
    Test that middleware can modify the event before it reaches the handler.
    """
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[str] = []

    class ModifyMiddleware:
        async def process(self, event: Any, next_middleware: Any) -> None:
            event.payload = f"modified-{event.payload}"
            await next_middleware(event)

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            record.append(event.payload)

    await bus.registry.register_middleware(ModifyMiddleware())
    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    await bus.publish(FakeEvent("original"))
    assert record == ["modified-original"]


@pytest.mark.asyncio
async def test_metadata_propagation() -> None:
    """
    Test that metadata is properly passed through middleware and to the handler,
    and that it can be modified by middleware.
    """
    container: Container = Container()
    logger = get_logger("test")
    config = EventsConfig(batch_size=10, retry_attempts=3)
    bus = InMemoryEventBus(logger=logger, config=config)
    bus.registry.container = container

    record: list[dict[str, Any]] = []

    class ModifyMetadataMiddleware:
        async def process(self, event: Any, next_middleware: Any) -> None:
            metadata = getattr(event, "_metadata", {})
            metadata["middleware_key"] = "middleware_value"
            await next_middleware(event)

    class Handler:
        async def handle(self, event: FakeEvent) -> None:
            metadata = getattr(event, "_metadata", {})
            record.append(metadata)

    await bus.registry.register_middleware(ModifyMetadataMiddleware())
    await bus.registry.register_handler("FakeEvent", Handler)
    await container.register_singleton(Handler, Handler)

    # Test with initial metadata
    metadata = {"initial_key": "initial_value"}
    event = FakeEvent("test")
    event._metadata = metadata  # Set metadata directly
    await bus.publish(event)
    assert record == [
        {"initial_key": "initial_value", "middleware_key": "middleware_value"}
    ]

    # Test with no initial metadata
    record.clear()
    event = FakeEvent("test")
    await bus.publish(event)
    assert record == [{"middleware_key": "middleware_value"}]
