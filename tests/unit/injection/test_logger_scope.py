import pytest
import asyncio
from contextlib import asynccontextmanager
from uno.injection.container import Container
from uno.logging.protocols import LoggerScopeProtocol


class FakeLoggerScope:
    def __init__(self):
        self.entered = []
        self.exited = []
        self.names = []

    @asynccontextmanager
    async def scope(self, name: str):
        self.entered.append(name)
        self.names.append(name)
        try:
            yield self
        finally:
            self.exited.append(name)


@pytest.mark.asyncio
async def test_logger_scope_enter_exit():
    container = Container()
    fake_logger_scope = FakeLoggerScope()
    # Register the fake logger scope as a singleton
    await container.register_singleton(LoggerScopeProtocol, lambda: fake_logger_scope)

    async with container.create_scope() as scope:
        # Logger scope should be entered
        assert fake_logger_scope.entered == [f"di_scope_{id(scope)}"]
        assert fake_logger_scope.exited == []
    # Logger scope should be exited after context
    assert fake_logger_scope.exited == [f"di_scope_{id(scope)}"]


@pytest.mark.asyncio
async def test_logger_scope_missing():
    container = Container()
    # Should not raise if LoggerScopeProtocol is not registered
    async with container.create_scope() as scope:
        assert scope is not None


@pytest.mark.asyncio
async def test_logger_scope_exception_handling():
    """Test that logger scope exceptions can be propagated when configured."""
    container = Container()

    class MockLoggerScope:
        """Mock logger scope that raises on exit."""

        async def scope(self, name: str):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Raise exception during exit
            raise RuntimeError("Test logger scope exit error")

    # Register our mock logger scope that will raise an exception on exit
    await container.register_singleton("LoggerScope", MockLoggerScope())

    # Should propagate the exception from logger scope.__aexit__
    with pytest.raises(RuntimeError, match="Test logger scope exit error"):
        async with container.create_scope(propagate_logger_scope_errors=True):
            pass  # Just create and exit the scope

    # Without propagation, the exception should be caught and logged
    async with container.create_scope(propagate_logger_scope_errors=False):
        pass  # Should not raise an exception

    # Clean up
    await container.dispose()
