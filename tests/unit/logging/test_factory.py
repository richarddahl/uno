import pytest
from uno.logging.factory import LoggerFactory, register_logger_factory
from uno.logging.protocols import LoggerFactoryProtocol
from uno.logging.config import LoggingSettings


class FakeContainer:
    def __init__(self):
        self._singletons = {}

    def register_singleton(self, typ, inst):
        self._singletons[typ] = inst

    def resolve(self, typ):
        return self._singletons[typ]


@pytest.mark.asyncio
async def test_register_logger_factory():
    container = FakeContainer()
    settings = LoggingSettings(level="INFO")
    register_logger_factory(container, settings)
    factory = container.resolve(LoggerFactoryProtocol)
    assert isinstance(factory, LoggerFactory)
    assert factory.settings.level == "INFO"


@pytest.mark.asyncio
async def test_logger_factory_create_logger():
    container = FakeContainer()
    settings = LoggingSettings(level="DEBUG")
    register_logger_factory(container, settings)
    factory = container.resolve(LoggerFactoryProtocol)
    logger = await factory.create_logger("uno.test")
    assert logger is not None
    assert hasattr(logger, "_logger")


@pytest.mark.asyncio
async def test_logger_factory_scoped_logger():
    container = FakeContainer()
    settings = LoggingSettings(level="INFO")
    register_logger_factory(container, settings)
    factory = container.resolve(LoggerFactoryProtocol)
    # Use the scoped_logger async context manager
    async with factory.scoped_logger("uno.scoped") as logger:
        assert logger is not None
        assert hasattr(logger, "_logger")
    # No exceptions means cleanup contract is honored (even if no-op)
