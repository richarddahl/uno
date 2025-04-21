"""
Command handling infrastructure for the Uno framework.

This module provides base classes for implementing the Command pattern,
which formalizes application use cases as explicit command objects.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Dict, Any, Type, Callable, List, Optional

T = TypeVar("T")  # Command result type
C = TypeVar("C")  # Command type


@dataclass
class Command:
    """Base class for all commands in the system."""

    pass


class CommandHandler(Generic[C, T], ABC):
    """Base class for command handlers."""

    @abstractmethod
    async def handle(self, command: C) -> T:
        """Handle the given command and return a result."""
        pass


class CommandBus:
    """Command bus for dispatching commands to their handlers."""

    _handlers: Dict[Type[Command], CommandHandler] = {}
    _middleware: List[Callable] = []

    @classmethod
    def register_handler(
        cls, command_type: Type[Command], handler: CommandHandler
    ) -> None:
        """Register a handler for a specific command type."""
        cls._handlers[command_type] = handler

    @classmethod
    def add_middleware(cls, middleware: Callable) -> None:
        """Add middleware to the command processing pipeline."""
        cls._middleware.append(middleware)

    @classmethod
    async def dispatch(cls, command: Command) -> Any:
        """Dispatch a command to its registered handler."""
        command_type = type(command)

        if command_type not in cls._handlers:
            raise ValueError(
                f"No handler registered for command type {command_type.__name__}"
            )

        handler = cls._handlers[command_type]

        # Apply middleware (if any)
        if cls._middleware:
            return await cls._execute_middleware_chain(command, handler)

        # No middleware, execute handler directly
        return await handler.handle(command)

    @classmethod
    async def _execute_middleware_chain(
        cls, command: Command, handler: CommandHandler
    ) -> Any:
        """Execute the middleware chain."""

        async def execute_handler(cmd):
            return await handler.handle(cmd)

        # Build the middleware chain
        chain = execute_handler
        for middleware in reversed(cls._middleware):
            next_chain = chain
            chain = lambda cmd, next_chain=next_chain: middleware(cmd, next_chain)

        # Execute the chain
        return await chain(command)
