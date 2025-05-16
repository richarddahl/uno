# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Service resolution implementation for uno DI system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast, Any

from uno.injection.errors import (
    ScopeError,
    ServiceNotFoundError,
    CircularDependencyError,
    ScopeDisposedError,
)

if TYPE_CHECKING:
    from types import TracebackType

    from uno.injection.protocols import ContainerProtocol

T = TypeVar("T")


class _Scope:
    """Internal scope implementation for service lifetime management."""

    def __init__(
        self, container: ContainerProtocol, parent: _Scope | None = None
    ) -> None:
        self.container = container
        self.parent = parent
        self._services: dict[type, object] = {}
        self._scopes: list[_Scope] = []
        self._disposed = False

    @classmethod
    def singleton(cls, container: Any) -> _Scope:
        """Create a singleton (root) scope with no parent.

        Args:
            container: The container that owns this scope

        Returns:
            A new singleton scope
        """
        return cls(container)

    async def __aenter__(self) -> _Scope:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.dispose()

    async def dispose(self) -> None:
        """Dispose of all services in this scope and its children (idempotent)."""
        if self._disposed:
            return
        for scope in reversed(self._scopes):
            await scope.dispose()
        await self._dispose_services()
        self._disposed = True

    async def _check_not_disposed(self, operation: str) -> None:
        """Check if the scope is disposed and raise an error if it is."""
        if self._disposed:
            raise await ScopeDisposedError.async_init(
                f"Scope is disposed, cannot perform {operation}",
                operation=operation,
                scope_id=str(id(self)),
            )

    async def _dispose_services(self) -> None:
        """Safely dispose all services in this scope."""
        await self.container.dispose_services(list(self._services.values()))

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service from this scope or parent scopes."""
        await self._check_not_disposed("operation on scope")
        try:
            # First check in this scope for non-singleton services
            if interface in self._services:
                # Cast needed because _services is typed as dict[type, object]
                return cast(T, self._services[interface])

            # Simply try to resolve from the container directly
            # This delegates the resolution logic to the container
            # which knows how to handle different lifetimes
            try:
                # Try to resolve from the container
                instance = await self.container.resolve(interface)

                # If it's a scoped service, cache it in this scope
                # We can cache all non-transient services for performance
                # The container should handle lifetime rules
                if interface not in self._services:
                    # Only store in the scope if not already present
                    # and if the container allows it to be stored
                    self._services[interface] = instance

                # Cast needed because instance might come from different sources
                return cast(T, instance)  # type: ignore
            except ServiceNotFoundError:
                # Container couldn't resolve it, so we'll check parent or fail
                pass

            # Check if we have a parent scope
            if self.parent is not None:
                # Simply try to resolve from parent and catch any ServiceNotFoundError
                try:
                    return await self.parent.resolve(interface)
                except ServiceNotFoundError:
                    # If parent can't resolve it, we'll fall through to our own
                    # ServiceNotFoundError below
                    pass

            # If all else fails
            raise ServiceNotFoundError(interface)
        except CircularDependencyError:
            raise  # propagate directly

    async def create_scope(self) -> _Scope:
        """Create a nested scope."""
        await self._check_not_disposed("operation on scope")
        scope = type(self)(self.container, parent=self)
        self._scopes.append(scope)
        return scope

    async def __getitem__(self, interface: type[T]) -> T:
        """Get a service instance from this scope or its parent asynchronously."""
        await self._check_not_disposed("operation on scope")

        # For services already resolved in this scope
        if interface in self._services:
            return cast(T, self._services[interface])

        # Try to resolve from container
        try:
            # Use the container's resolve method directly
            # This should handle different lifetimes appropriately
            instance = await self.container.resolve(interface)
            return cast(T, instance)  # type: ignore
        except ServiceNotFoundError:
            # If the container can't resolve it, try the parent
            if self.parent is not None:
                return await self.parent.__getitem__(interface)
            # If there's no parent, re-raise the error
            raise

    async def __setitem__(self, interface: type[T], service: T) -> None:
        """Set a service instance in this scope asynchronously."""
        await self._check_not_disposed("operation on scope")
        self._services[interface] = service

    async def get_service_keys(self) -> list[str]:
        """Get the service keys available in this scope asynchronously.

        Returns:
            A list of service type names available in this scope.
        """
        await self._check_not_disposed("operation on scope")
        return [t.__name__ for t in self._services]

    async def has_registration(self, interface: type[T]) -> bool:
        """Asynchronously check if a service is registered in this scope or its container.

        Args:
            interface: The service type to check

        Returns:
            True if the service is registered, False otherwise
        """
        return interface in self._services or await self.container.has_registration(
            interface
        )
