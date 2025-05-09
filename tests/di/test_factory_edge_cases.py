"""
Test edge cases for factory functions in the DI container.
"""

from typing import Any, Protocol, runtime_checkable

import pytest

from uno.di.container import Container
from uno.di.errors import ServiceCreationError, TypeMismatchError


@runtime_checkable
class ILogger(Protocol):
    def log(self, message: str) -> None: ...


class ConsoleLogger:
    def log(self, message: str) -> None:
        pass  # Mock implementation


@pytest.mark.asyncio
async def test_factory_returns_wrong_type() -> None:
    """Test that a factory function returning the wrong type raises TypeMismatchError."""
    container = Container()

    def bad_factory(container: Container) -> Any:
        return 42  # Integer instead of ILogger

    with pytest.raises(ServiceCreationError) as excinfo:
        await container.register_singleton(ILogger, bad_factory)
    # Verify that the TypeMismatchError is the cause
    assert isinstance(excinfo.value.__cause__, TypeMismatchError)
    assert "Expected ILogger, got int" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_factory_raises_exception() -> None:
    """Test that an async factory function raising an exception is properly handled."""
    container = Container()

    async def failing_factory(container: Container) -> ILogger:
        raise ValueError("Factory failed")

    with pytest.raises(ServiceCreationError) as excinfo:
        await container.register_singleton(ILogger, failing_factory)
    # Check that the original error is preserved as the cause
    assert isinstance(excinfo.value.__cause__, ValueError)
    assert "Factory failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_factory_with_dependencies() -> None:
    """Test that a factory function with dependencies is properly resolved."""
    container = Container()

    class Config:
        def __init__(self, log_level: str) -> None:
            self.log_level = log_level

    class ConfiguredLogger:
        def __init__(self, config: Config) -> None:
            self.config = config

        def log(self, message: str) -> None:
            pass

    # Use a simple lambda for Config since it doesn't have async dependencies
    await container.register_singleton(Config, lambda container: Config("INFO"))

    # Use an async factory for the logger since it needs to await container.resolve
    async def logger_factory(container: Container) -> ILogger:
        config = await container.resolve(Config)
        return ConfiguredLogger(config)

    await container.register_singleton(ILogger, logger_factory)

    logger = await container.resolve(ILogger)
    assert isinstance(logger, ConfiguredLogger)
    assert logger.config.log_level == "INFO"
