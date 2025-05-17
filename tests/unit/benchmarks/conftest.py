"""Pytest configuration and fixtures for benchmark tests."""

from __future__ import annotations

from typing import Any, Callable, TypeVar
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from uno.event_store.config import EventStoreSettings
from uno.injection import ContainerProtocol
from uno.logging.protocols import LoggerProtocol

T = TypeVar('T')


class MockContainer(ContainerProtocol):
    """Mock container for dependency injection in tests."""
    
    def get(self, type_: type[T]) -> T:
        """Get a dependency by type."""
        return MagicMock(spec=type_)
    
    def get_named(self, type_: type[T], name: str) -> T:
        """Get a named dependency by type and name."""
        return MagicMock(spec=type_)
        
    def create_scope(self, name: str = "") -> 'MockContainer':
        """Create a new scope."""
        return self
        
    def create_service(self, type_: type[T], *args: Any, **kwargs: Any) -> T:
        """Create a service."""
        return type_(*args, **kwargs)
        
    def register(self, type_: type[T], factory: Callable[..., T], *, name: str = "") -> None:
        """Register a factory for a type."""
        pass
        
    def register_instance(self, instance: T, type_: type[T] | None = None, *, name: str = "") -> None:
        """Register an instance for a type."""
        pass
        
    def dispose(self) -> None:
        """Dispose of the container and all its resources."""
        pass
        
    async def dispose_async(self) -> None:
        """Asynchronously dispose of the container and all its resources."""
        pass
        
    def is_registered(self, type_: type[object], name: str = "") -> bool:
        """Check if a type is registered."""
        return True
        
    def get_required(self, type_: type[T], name: str = "") -> T:
        """Get a required dependency by type and optional name."""
        return MagicMock(spec=type_)
        
    async def wait_for_pending_tasks(self, timeout: float | None = None) -> None:
        """Wait for pending tasks to complete."""
        pass


class MockLogger(LoggerProtocol):
    """Mock logger for testing."""
    
    def debug(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log a debug message."""
        pass
    
    def info(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log an info message."""
        pass
    
    def warning(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log a warning message."""
        pass
    
    def error(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log an error message."""
        pass
    
    def critical(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log a critical message."""
        pass
    
    def exception(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log an exception with traceback."""
        pass
        
    def log(self, level: int, msg: str, *args: object, **kwargs: object) -> None:
        """Log a message with the specified level."""
        pass
        
    def is_enabled_for(self, level: int) -> bool:
        """Check if logging is enabled for the specified level."""
        return True
        
    def add_handler(self, handler: Any) -> None:
        """Add a handler to the logger."""
        pass
        
    def remove_handler(self, handler: Any) -> None:
        """Remove a handler from the logger."""
        pass
        
    def set_level(self, level: int) -> None:
        """Set the logging level."""
        pass


@pytest.fixture
def mock_container() -> MockContainer:
    """Create a mock container for dependency injection."""
    return MockContainer()


@pytest.fixture
def mock_settings() -> EventStoreSettings:
    """Create test settings for the event store."""
    return EventStoreSettings(
        postgres_dsn="postgresql://postgres:postgres@localhost:5432/test",
        redis_url="redis://localhost:6379/0"
    )


@pytest.fixture
def mock_logger() -> MockLogger:
    """Create a mock logger."""
    return MockLogger()
