"""
Service scope implementation for Uno DI.

This module provides the ServiceScope enum and Scope class, which define the
lifetime scopes for services in the DI container. The Scope class manages
service instances for a specific scope.

Note: All dependencies must be passed explicitly from the composition root.
"""

from __future__ import annotations

from typing import Type, Any, Generic, TypeVar, Callable, Dict
from enum import Enum, auto

TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])

class ServiceScope(Enum):
    """
    Service lifetime scopes.

    SINGLETON: One instance for the entire application
    SCOPED: One instance per scope
    TRANSIENT: New instance for each resolution

    Example:
        ```python
        # Register a singleton service
        collection.add_singleton(IMyService, MyService)

        # Register a scoped service
        collection.add_scoped(IMyService, MyService)

        # Register a transient service
        collection.add_transient(IMyService, MyService)
        ```
    """

    SINGLETON = auto()
    SCOPED = auto()
    TRANSIENT = auto()



    def __str__(self) -> str:
        """Get a string representation of the scope."""
        return self.name

class Scope(Generic[TService]):
    """
    A scope for service resolution.

    This class manages service instances for a specific scope. It provides
    methods for getting, setting, and clearing instances.

    Note: All dependencies must be passed explicitly from the composition root.

    Example:
        ```python
        # Create a scope
        with provider.create_scope() as scope:
            # Get a service from the scope
            service = scope.get_service(IMyService)

            # Set a service in the scope
            scope.set_service(IMyService, MyService())

            # Clear the scope
            scope.clear()
        ```
    """

    def __init__(
        self,
        provider: Any,
        collection: Any,
        scope_id: str | None = None,
    ) -> None:
        """
        Initialize a new Scope instance.

        Args:
            provider: The service provider
            collection: The service collection
            scope_id: Optional scope identifier
        """
        self._provider = provider
        self._collection = collection
        self._scope_id = scope_id
        self._instances: dict[type[Any], Any] = {}
        self._named_instances: dict[str, Any] = {}

    def __enter__(self) -> "Scope[TService]":
        """Enter the scope context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the scope context."""
        self.dispose()

    async def __aenter__(self) -> "Scope[TService]":
        """Enter the async scope context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async scope context."""
        await self.dispose_async()

    def get_or_create(
        self,
        service_type: type[TService],
        factory: Callable[[], TService],
        name: str | None = None,
    ) -> TService:
        """
        Get an existing instance or create a new one.

        Args:
            service_type: The type of service to get or create
            factory: Factory function to create a new instance
            name: Optional name for named service registration

        Returns:
            The service instance

        Example:
            ```python
            # Get or create a service
            service = scope.get_or_create(IMyService, lambda: MyService())
            ```
        """
        if name:
            if name not in self._named_instances:
                self._named_instances[name] = factory()
            return self._named_instances[name]

        if service_type not in self._instances:
            self._instances[service_type] = factory()
        return self._instances[service_type]

    def get_service(self, service_type: type[TService], name: str | None = None) -> TService | None:
        """
        Get a service instance from the scope.

        Args:
            service_type: The type of service to get
            name: Optional name for named service registration

        Returns:
            The service instance, or None if not found

        Example:
            ```python
            # Get a service
            service = scope.get_service(IMyService)
            ```
        """
        if name:
            return self._named_instances.get(name)
        return self._instances.get(service_type)

    def set_service(self, service_type: type[TService], instance: TService, name: str | None = None) -> None:
        """
        Set a service instance in the scope.

        Args:
            service_type: The type of service to set
            instance: The service instance
            name: Optional name for named service registration

        Example:
            ```python
            # Set a service
            scope.set_service(IMyService, MyService())
            ```
        """
        if name:
            self._named_instances[name] = instance
        else:
            self._instances[service_type] = instance

    async def clear_async(self) -> None:
        """
        Asynchronously clear all service instances from the scope.

        Example:
            ```python
            # Clear the scope
            await scope.clear_async()
            ```
        """
        for instance in self._instances.values():
            if hasattr(instance, 'dispose_async'):
                await instance.dispose_async()
        for instance in self._named_instances.values():
            if hasattr(instance, 'dispose_async'):
                await instance.dispose_async()
        self._instances.clear()
        self._named_instances.clear()

    def clear(self) -> None:
        """
        Clear all service instances from the scope.

        Example:
            ```python
            # Clear the scope
            scope.clear()
            ```
        """
        for instance in self._instances.values():
            if hasattr(instance, 'dispose'):
                instance.dispose()
        for instance in self._named_instances.values():
            if hasattr(instance, 'dispose'):
                instance.dispose()
        self._instances.clear()
        self._named_instances.clear()

    async def dispose_async(self) -> None:
        """
        Asynchronously dispose of the scope and its services.

        Example:
            ```python
            # Dispose of the scope
            await scope.dispose_async()
            ```
        """
        await self.clear_async()

    def dispose(self) -> None:
        """
        Dispose of the scope and its services.

        Example:
            ```python
            # Dispose of the scope
            scope.dispose()
            ```
        """
        self.clear()
