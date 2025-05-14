import pytest
from uno.logging.di import LoggingRegistrationExtensions
from uno.logging.config import LoggingSettings

class FakeContainer:
    def __init__(self):
        self._singletons = {}
    def register_singleton(self, typ, inst):
        self._singletons[typ] = inst
    def resolve(self, typ):
        return self._singletons[typ]

def test_register_logging():
    container = FakeContainer()
    settings = LoggingSettings(level="INFO")
    LoggingRegistrationExtensions.register_logging(container, settings)
    # Should register logger factory
    assert any(["LoggerFactory" in str(type(v)) for v in container._singletons.values()])
