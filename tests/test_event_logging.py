import pytest
from uno.infrastructure.logging.logger import LoggerService
from uno.core.events.handlers import EventHandler, EventHandlerRegistry
from uno.core.events.context import EventHandlerContext

from uno.core.events.base_event import DomainEvent

# Minimal fake DomainEvent for Pydantic model resolution
define_fake_event = True


class FakeDomainEvent(DomainEvent):
    pass


# Rebuild EventHandlerContext model to resolve forward refs (Pydantic v2)
EventHandlerContext.model_rebuild()


from tests.conftest import FakeLoggerService


@pytest.fixture
def fake_logger() -> FakeLoggerService:
    return FakeLoggerService()


def test_handler_logs_with_di_logger(fake_logger: FakeLoggerService) -> None:
    class MyHandler(EventHandler):
        logger: FakeLoggerService

        def __init__(self) -> None:
            self.logger = fake_logger

        async def handle(self, context: EventHandlerContext) -> None:
            self.logger.structured_log("INFO", "handler test log", name="MyHandler")
            return None

    handler = MyHandler()
    import asyncio

    fake_event = FakeDomainEvent()
    asyncio.run(handler.handle(EventHandlerContext(event=fake_event)))
    assert fake_logger.logged[0][1] == "handler test log"
    assert fake_logger.logged[0][2]["name"] == "MyHandler"


def test_registry_requires_logger(fake_logger: FakeLoggerService) -> None:
    registry = EventHandlerRegistry(fake_logger)
    assert hasattr(registry, "logger")
    assert registry.logger is fake_logger
