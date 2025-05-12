"""
Command, CommandHandler, and CommandBus abstractions for Uno's DDD/event sourcing system.
Modernized and integrated for DI, error handling, and extensibility.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Generic, TypeVar
from uno.events.errors import UnoError, CommandDispatchError


C = TypeVar("C", bound="Command")
T = TypeVar("T")


class Command(ABC):
    """
    Base class for commands (write-side intent in CQRS/DDD).
    """

    command_type: ClassVar[str] = "command"


class CommandHandler(Generic[C, T], ABC):
    """
    Base class for command handlers.
    """

    @abstractmethod
    async def handle(self, command: C) -> T:
        """Handle the given command and return a result."""
        pass


class CommandBus:
    """
    Command bus for dispatching commands to their handlers.
    Supports middleware and DI integration.
    """

    _handlers: dict[type[Command], CommandHandler] = {}
    _middleware: list[Callable] = []

    @classmethod
    def register_handler(
        cls, command_type: type[Command], handler: CommandHandler
    ) -> None:
        """Register a handler for a specific command type."""
        cls._handlers[command_type] = handler

    @classmethod
    def add_middleware(cls, middleware: Callable) -> None:
        """Add middleware to the command processing pipeline."""
        cls._middleware.append(middleware)

    @classmethod
    async def dispatch(cls, command: Command) -> Any:
        """
        Dispatch a command to its registered handler.
        Raises:
        - All public methods raise CommandDispatchError on error for error propagation.
        Returns:
            The result of the command handler.
        """
        command_type = type(command)
        if command_type not in cls._handlers:
            raise CommandDispatchError(
                command_type=command_type.__name__,
                reason="No handler registered for command type",
                command=command,
            )
        handler = cls._handlers[command_type]
        # Apply middleware (if any)
        result = handler.handle
        for mw in reversed(cls._middleware):
            result = mw(result)
        try:
            return await result(command)
        except Exception as e:
            raise CommandDispatchError(
                command_type=command_type.__name__,
                reason=str(e),
                command=command,
            ) from e
