"""
Async context manager for DI scopes in Uno.

This module provides the Scope class, which manages the lifecycle of scoped services
using Python contextvars for per-coroutine/task isolation.

Note: All dependencies must be passed explicitly from the composition root.
"""

import asyncio
import contextvars
from typing import TYPE_CHECKING, Any, TypeVar, Callable, Dict, Type
from types import TracebackType

if TYPE_CHECKING:
    from .provider import ServiceProvider

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])

# Context variable to track the current active scope per coroutine/task
_current_scope = contextvars.ContextVar("uno_di_current_scope", default=None)


class ScopeContext:
    """
    Sync or async context manager representing a DI scope.
    Tracks scoped service instances and disposes them on exit.
    Use `with` for sync-only scopes, `async with` for scopes with async services.

    Note: All dependencies must be passed explicitly from the composition root.

    Example:
        ```python
        # Sync scope
        with provider.create_scope() as scope:
            service = scope.get_service(IMyService)

        # Async scope
        async with provider.create_scope() as scope:
            service = scope.get_service(IMyService)
        ```
    """

    def __init__(self, provider: "ServiceProvider", scope_id: str | None = None):
        """
        Initialize a new scope context.

        Args:
            provider: The service provider
            scope_id: Optional scope identifier

        Example:
            ```python
            # Create a scope context
            scope = ScopeContext(provider, "my-scope")
            ```
        """
        self._provider = provider
        self._scope_id = scope_id
        self._instances: dict[type[Any], Any] = {}
        self._disposed = False
        self._token = None

    def __enter__(self) -> "ScopeContext[TService]":
        """
        Enter the scope context.

        Returns:
            The scope context instance

        Example:
            ```python
            with provider.create_scope() as scope:
                # Use scope
                pass
            ```
        """
        self._token = _current_scope.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the scope context.

        This will dispose of all scoped services in reverse order.

        Example:
            ```python
            with provider.create_scope() as scope:
                # Use scope
                pass  # Services are disposed here
            ```
        """
        try:
            for instance in reversed(list(self._instances.values())):
                dispose = getattr(instance, "dispose", None)
                if dispose and not asyncio.iscoroutinefunction(dispose):
                    dispose()
        finally:
            _current_scope.reset(self._token)
            self._disposed = True

    async def __aenter__(self) -> "ScopeContext[TService]":
        """
        Enter the scope context asynchronously.

        Returns:
            The scope context instance

        Example:
            ```python
            async with provider.create_scope() as scope:
                # Use scope
                pass
            ```
        """
        self._token = _current_scope.set(self)
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: TracebackType) -> None:
        """
        Exit the scope context asynchronously.

        This will dispose of all scoped services in reverse order.

        Example:
            ```python
            async with provider.create_scope() as scope:
                # Use scope
                pass  # Services are disposed here
            ```
        """
        try:
            for instance in reversed(list(self._instances.values())):
                dispose = getattr(instance, "dispose", None)
                if dispose:
                    if asyncio.iscoroutinefunction(dispose):
                        await dispose()
                    else:
                        dispose()
        finally:
            _current_scope.reset(self._token)
            self._disposed = True

    def get_service(self, service_type: type[TService]) -> TService:
        """
        Get a service from the scope (singleton, transient, or scoped).

        Args:
            service_type: The type of service to get

        Returns:
            The service instance

        Example:
            ```python
            # Get a service
            service = scope.get_service(IMyService)
            ```
        """
        return self._provider.get_service(service_type)

    def set_instance(self, service_type: type[Any], instance: Any) -> None:
        """
        Set a service instance in the scope.

        Args:
            service_type: The type of service
            instance: The service instance

        Example:
            ```python
            # Set a service instance
            scope.set_instance(IMyService, MyService())
            ```
        """
        self._instances[service_type] = instance

    def get_instance(self, service_type: type[Any]) -> Any | None:
        """
        Get a service instance from the scope.

        Args:
            service_type: The type of service to get

        Returns:
            The service instance, or None if not found

        Example:
            ```python
            # Get a service instance
            instance = scope.get_instance(IMyService)
            ```
        """
        return self._instances.get(service_type)

    @property
    def id(self) -> str | None:
        """
        Get the scope identifier.

        Returns:
            The scope identifier, or None if not set

        Example:
            ```python
            # Get scope ID
            scope_id = scope.id
            ```
        """
        return self._scope_id

    @staticmethod
    def get_current_scope() -> type["ScopeContext"] | None:
        """
        Get the current active scope.

        Returns:
            The current scope, or None if no scope is active

        Example:
            ```python
            # Get current scope
            current_scope = ScopeContext.get_current_scope()
            ```
        """
        return _current_scope.get()
