import pytest
import asyncio
from uno.logging.injection import LoggingRegistrationExtensions
from uno.logging.config import LoggingSettings
from uno.logging.protocols import LoggerFactoryProtocol
from tests.conftest_protocols import assert_implements_protocol


class FakeContainer:
    def __init__(self):
        self._singletons = {}

    async def register_singleton(self, typ, inst):
        # If inst is a callable (provider), call it with self and await if needed
        if callable(inst):
            result = inst(self)
            if hasattr(result, "__await__"):
                result = await result
            self._singletons[typ] = result
        else:
            self._singletons[typ] = inst

    def resolve(self, typ):
        return self._singletons[typ]


@pytest.mark.asyncio
async def test_register_logging():
    # Set up an event loop explicitly for Python 3.13
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    container = FakeContainer()
    settings = LoggingSettings(level="INFO")
    await LoggingRegistrationExtensions.register_logging(container, settings)
    # Find the registered logger factory
    factory = None
    for v in container._singletons.values():
        # Use protocol assertion instead of isinstance
        try:
            assert_implements_protocol(LoggerFactoryProtocol, v)
            factory = v
            break
        except AssertionError:
            continue
    assert factory is not None
