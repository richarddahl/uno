"""
This module provides scope management for the logging system, aligning logger
lifetimes with dependency injection scopes.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from uno.injection.protocols import ContainerProtocol


class LoggerScope:
    """Manages logger scopes aligned with DI scopes."""

    def __init__(self, container: ContainerProtocol) -> None:
        """Initialize the logger scope manager.

        Args:
            container: The dependency injection container
        """
        self._container = container
        self._scopes: dict[str, dict[str, Any]] = {}
        self.entered: list[str] = []  # Track entered scopes
        self.exited: list[str] = []  # Track exited scopes

    def get_scope(self, scope_name: str) -> dict[str, Any]:
        """Get the scope data for a given scope name.

        Args:
            scope_name: The name of the scope

        Returns:
            The scope data
        """
        return self._scopes.get(scope_name, {})

    def set_scope(self, scope_name: str, scope: dict[str, Any]) -> None:
        """Set the scope data for a given scope name.

        Args:
            scope_name: The name of the scope
            scope: The scope data to set
        """
        self._scopes[scope_name] = scope

    def update_scope(self, scope_name: str, **kwargs: Any) -> None:
        """Update the scope data for a given scope name.

        Args:
            scope_name: The name of the scope
            **kwargs: The scope data to update
        """
        self._scopes.setdefault(scope_name, {}).update(kwargs)

    @asynccontextmanager
    async def scope(self, name: str, **kwargs: Any) -> AsyncGenerator[None, None]:
        """Create a scope that will be automatically cleaned up.

        This method is part of LoggerScopeProtocol from uno.logging.protocols.

        Args:
            name: The name of the scope
            **kwargs: Additional scope data to use (not part of the protocol)

        Yields:
            None
        """
        try:
            # Use name as scope_name to match implementation in protocols.py
            self.set_scope(name, kwargs)
            # Track that this scope was entered - use the name directly
            # The container should be passing in a name that includes the scope ID
            self.entered.append(name)
            yield
        finally:
            # Clean up the scope when exiting
            self._scopes.pop(name, None)
            # Track that this scope was exited
            self.exited.append(name)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with scope-aware context.

        Args:
            name: The name of the logger

        Returns:
            A logger instance
        """
        logger = logging.getLogger(name)

        # Apply scope context to the logger
        for scope_name, scope_data in self._scopes.items():
            for key, value in scope_data.items():
                logger = logger.bind(**{f"{scope_name}_{key}": value})

        return logger
