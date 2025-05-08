"""
Command, CommandHandler, and CommandBus abstractions for Uno's DDD/event sourcing system.
Modernized and integrated for DI, error handling, and extensibility.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Generic, TypeVar
from uno.errors.result import Result, Failure

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
    async def dispatch(cls, command: Command) -> Result[Any, Exception]:
        """Dispatch a command to its registered handler, returning Failure if no handler is registered."""
        command_type = type(command)
        if command_type not in cls._handlers:
            return Failure(
                ValueError(
                    f"No handler registered for command type {command_type.__name__}"
                )
            )
        handler = cls._handlers[command_type]
        # Apply middleware (if any)
        result = handler.handle
        for mw in reversed(cls._middleware):
            result = mw(result)
        try:
            return await result(command)
        except Exception as e:
            return Failure(e)
