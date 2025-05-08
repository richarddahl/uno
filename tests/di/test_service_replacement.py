from typing import Protocol

import pytest
from typing_extensions import runtime_checkable

from uno.infrastructure.di.container import DIContainer
from uno.infrastructure.di.errors import ServiceNotRegisteredError

# Define test protocols and implementations


@runtime_checkable
class ILogger(Protocol):
    def log(self, message: str) -> None: ...


class ConsoleLogger:
    def log(self, message: str) -> None:
        pass  # Mock implementation


class MockLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def log(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_replace_service() -> None:
    container = DIContainer()
    await container.register_singleton(ILogger, ConsoleLogger)

    # Define a mock logger for testing

    # Replace the logger temporarily
    original = await container.resolve(ILogger)
    async with container.replace(ILogger, MockLogger, "singleton"):
        replacement = await container.resolve(ILogger)
        assert isinstance(replacement, MockLogger)

        # Test the replacement
        replacement.log("test")
        assert replacement.messages == ["test"]

    # Verify the original service is restored
    restored = await container.resolve(ILogger)
    assert restored is original
    assert isinstance(restored, ConsoleLogger)


@pytest.mark.asyncio
async def test_replace_non_existent_service() -> None:
    container = DIContainer()

    # Try to replace a service that doesn't exist
    async with container.replace(ILogger, ConsoleLogger, "singleton"):
        logger = await container.resolve(ILogger)
        assert isinstance(logger, ConsoleLogger)

    # Verify the service is removed after the context
    with pytest.raises(ServiceNotRegisteredError):
        await container.resolve(ILogger)
