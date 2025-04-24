# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, TypeVar, TYPE_CHECKING
from uno.infrastructure.database.config import ConnectionConfig

if TYPE_CHECKING:
    from uno.core.logging.logger import LoggerService

# Type for connection callback functions
T = TypeVar("T")
C = TypeVar("C")  # Connection type
E = TypeVar("E")  # Engine type
ConnectionCallback = Callable[[C], None]


class EngineFactory(Generic[E, C], ABC):
    """Base class for engine factories."""

    def __init__(
        self,
        logger_service: "LoggerService",
        config: ConnectionConfig | None = None,
    ):
        """Initialize the engine factory with DI-managed logger."""
        self.logger = logger_service.get_logger(__name__)
        self.connection_callbacks: dict[str, ConnectionCallback] = {}

    @abstractmethod
    def create_engine(self, config: ConnectionConfig) -> E:
        """Create an engine with the given configuration."""
        pass

    def register_callback(self, name: str, callback: ConnectionCallback) -> None:
        """Register a callback for new connections."""
        self.connection_callbacks[name] = callback

    def unregister_callback(self, name: str) -> None:
        """Unregister a connection callback."""
        if name in self.connection_callbacks:
            del self.connection_callbacks[name]

    def execute_callbacks(self, connection: C) -> None:
        """Execute all registered callbacks with the connection."""
        for name, callback in self.connection_callbacks.items():
            try:
                callback(connection)
            except Exception as e:
                self.logger.error(f"Error in connection callback '{name}': {e}")
