"""
Service resolution implementation for uno DI system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast

from uno.di.errors import ScopeError, ServiceNotRegisteredError, DICircularDependencyError, DIScopeDisposedError

if TYPE_CHECKING:
    from types import TracebackType

    from uno.di.protocols import ContainerProtocol

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
    def singleton(cls, container: ContainerProtocol) -> _Scope:
        """Create a singleton (root) scope with no parent."""
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

    def _check_not_disposed(self, operation: str) -> None:
        """Check if the scope is disposed and raise an error if it is."""
        if self._disposed:
            raise DIScopeDisposedError(operation=operation, scope_id=str(id(self)))

    async def _dispose_services(self) -> None:
        """Safely dispose all services in this scope."""
        await self.container.dispose_services(list(self._services.values()))

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service from this scope or parent scopes."""
        self._check_not_disposed("operation on scope")
        try:
            # First check in this scope for non-singleton services
            if interface in self._services:
                return cast("T", self._services[interface])

            # Try container registrations for non-singleton services
            if interface in self.container._registrations:
                registration = self.container._registrations[interface]

                match registration.lifetime:
                    case "scoped":
                        if not self._scopes and self.parent is None:
                            raise ScopeError(
                                f"Cannot resolve scoped service {interface.__name__} outside of a scope"
                            )
                        instance = await self.container._create_service(
                            interface, registration.implementation
                        )
                        self._services[interface] = instance
                        return cast("T", instance)
                    case "transient":
                        # For transient services, always create a new instance
                        # Never cache or reuse transient instances
                        return await self.container._create_service(
                            interface, registration.implementation
                        )

            # If not found and we have a parent, try the parent
            if self.parent is not None:
                return await self.parent.resolve(interface)

            # If all else fails
            raise ServiceNotRegisteredError(interface)
        except DICircularDependencyError:
            raise  # propagate directly

    def create_scope(self) -> _Scope:
        """Create a nested scope."""
        self._check_not_disposed("operation on scope")
        scope = type(self)(self.container, parent=self)
        self._scopes.append(scope)
        return scope

    async def __getitem__(self, interface: type[T]) -> T:
        """Get a service instance from this scope or its parent asynchronously."""
        self._check_not_disposed("operation on scope")

        # Check if this is a singleton service
        if (
            interface in self.container._registrations
            and self.container._registrations[interface].lifetime == "singleton"
            and interface in self.container._singleton_scope._services
        ):
            # For singletons, always get from the singleton scope
            return cast("T", self.container._singleton_scope._services[interface])

        # For non-singleton services or if singleton not found
        if interface in self._services:
            return cast("T", self._services[interface])

        # If not found and we have a parent, try the parent
        if self.parent is not None:
            return await self.parent.__getitem__(interface)

        raise ServiceNotRegisteredError(interface)

    async def __setitem__(self, interface: type[T], service: T) -> None:
        """Set a service instance in this scope asynchronously."""
        self._check_not_disposed("operation on scope")
        self._services[interface] = service



    async def get_service_keys(self) -> list[str]:
        """Get the service keys available in this scope asynchronously.

        Returns:
            A list of service type names available in this scope.
        """
        self._check_not_disposed("operation on scope")
        return [t.__name__ for t in self._services]
