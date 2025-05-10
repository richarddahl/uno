import pytest

from uno.di.container import Container
from uno.events.config import EventsConfig
from uno.events.di import (
    EventHandlerRegistry,
    EventPublisher,
    LoggingMiddleware,
    TimingMiddleware,
    register_event_services,
)
from uno.events.protocols import EventBusProtocol
from uno.persistence.event_sourcing.protocols import EventStoreProtocol


@pytest.mark.asyncio
async def test_event_services_are_registered_and_resolvable() -> None:
    container = Container()
    await register_event_services(container)

    # Core event services
    assert await container.resolve(EventsConfig)
    assert await container.resolve(EventBusProtocol)
    assert await container.resolve(EventStoreProtocol)
    assert await container.resolve(EventHandlerRegistry)
    assert await container.resolve(LoggingMiddleware)
    assert await container.resolve(TimingMiddleware)
    assert await container.resolve(EventPublisher)

    # Check types
    assert isinstance(
        await container.resolve(EventHandlerRegistry), EventHandlerRegistry
    )
    assert isinstance(await container.resolve(LoggingMiddleware), LoggingMiddleware)
    assert isinstance(await container.resolve(TimingMiddleware), TimingMiddleware)
    assert isinstance(await container.resolve(EventPublisher), EventPublisher)
