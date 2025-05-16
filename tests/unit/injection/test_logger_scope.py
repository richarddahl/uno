import pytest
import asyncio
import inspect
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
    # Fix: use the correct factory signature with container argument
    await container.register_singleton(LoggerScopeProtocol, lambda c: fake_logger_scope)

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
    # Create a completely isolated container for this test
    container = Container()

    # Use a unique class name to avoid any potential shared state issues
    class UniqueTestMockLoggerScope:
        """Mock logger scope that raises on exit."""

        @asynccontextmanager
        async def scope(self, name: str):
            print(f"UniqueTestMockLoggerScope.scope entered with name: {name}")
            try:
                yield self
            finally:
                print(f"UniqueTestMockLoggerScope.scope exiting with name: {name}")
                # Deliberately raise an exception on exit
                raise RuntimeError("Test logger scope exit error")

    # Create our mock
    mock_scope = UniqueTestMockLoggerScope()

    # The key issue is here - we need to use the same registration pattern
    # as the test_logger_scope_enter_exit test
    await container.register_singleton(LoggerScopeProtocol, lambda c: mock_scope)

    # Verify the registration and resolve it to ensure it's what we expect
    print(f"After direct registration: {await container.get_registration_keys()}")
    resolved = await container.resolve(LoggerScopeProtocol)
    print(f"Resolved directly: {resolved}")

    # Now do the identity check
    assert (
        resolved is mock_scope
    ), "Expected the exact same instance that was registered"

    # Should propagate the exception from logger scope's __aexit__
    error_raised = False
    try:
        print("Creating scope with propagate_logger_scope_errors=True")
        async with container.create_scope(propagate_logger_scope_errors=True):
            print("Inside scope context manager")
            # Ensure the async context is fully processed
            await asyncio.sleep(0.1)
            print("After sleep in scope")
    except RuntimeError as e:
        error_raised = True
        print(f"Caught expected RuntimeError: {e}")
        assert "Test logger scope exit error" in str(e)

    assert error_raised, "Expected RuntimeError was not raised"

    # Without propagation, the exception should be caught and logged
    print("Creating scope with propagate_logger_scope_errors=False")
    async with container.create_scope(propagate_logger_scope_errors=False):
        await asyncio.sleep(0.1)
        print("No exception with propagate_logger_scope_errors=False")

    await container.dispose()
