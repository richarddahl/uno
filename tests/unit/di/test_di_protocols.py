# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework


import contextlib
import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import Any, Awaitable, Literal, TypeVar

import pytest

from uno.di.protocols import (
    ContainerProtocol,
    ScopeProtocol,
    AsyncServiceFactoryProtocol,
    ServiceFactoryProtocol,
)

T = TypeVar("T")


class ImplementsContainerProtocol:
    """Test implementation of ContainerProtocol for structural typing tests."""

    def __init__(self) -> None:
        self._disposed = False
        self._registrations = {}

    async def register_singleton(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        replace: bool = False,
    ) -> None:
        """Register a singleton service."""
        pass

    async def register_scoped(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        replace: bool = False,
    ) -> None:
        """Register a scoped service."""
        pass

    async def register_transient(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        replace: bool = False,
    ) -> None:
        """Register a transient service."""
        pass

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service by interface."""
        raise NotImplementedError()

    async def resolve_optional(self, interface: type[T]) -> T | None:
        """Resolve a service or return None if not found."""
        return None

    async def get_registration_keys(self) -> list[str]:
        """Get all registered service keys."""
        return []

    async def get_scopes(self) -> list[ScopeProtocol]:
        """Get all managed scopes."""
        return []

    async def get_singleton_scope(self) -> ScopeProtocol:
        """Get the singleton scope."""
        raise NotImplementedError()

    async def get_scope_chain(self) -> list[ScopeProtocol]:
        """Get the scope chain from current to root."""
        return []

    @contextlib.asynccontextmanager
    async def create_scope(self) -> AsyncGenerator[ScopeProtocol, None]:
        """Create a new scope."""
        scope = FakeScopeProtocol()
        try:
            yield scope
        finally:
            await scope.dispose()

    async def wait_for_pending_tasks(self) -> None:
        """Wait for pending tasks to complete."""
        pass

    async def dispose(self) -> None:
        """Dispose the container."""
        self._disposed = True

    async def dispose_services(self, services: list[Any]) -> None:
        """Dispose a list of services."""
        pass

    async def has_registration(self, interface: type[T]) -> bool:
        """Check if a service is registered."""
        return interface in self._registrations

    async def create_service(self, interface: type[Any], implementation: Any) -> Any:
        """Create a service instance."""
        if isinstance(implementation, type):
            return implementation()
        elif callable(implementation):
            return implementation(self)
        return implementation

    async def register_type_name(self, name: str, implementation: type[T]) -> None:
        """Register a service with a type name."""
        pass


class FakeScopeProtocol:
    """A fake implementation of ScopeProtocol for testing."""

    def __init__(self) -> None:
        self._disposed = False
        self._parent = None
        self._services = {}

    @property
    def parent(self) -> ScopeProtocol | None:
        """Get the parent scope."""
        return self._parent

    @property
    def id(self) -> str:
        """Get the scope ID."""
        return f"test-scope-{id(self)}"

    @property
    def is_disposed(self) -> bool:
        """Check if the scope is disposed."""
        return self._disposed

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service by interface."""
        raise NotImplementedError()

    async def create_scope(self) -> ScopeProtocol:
        """Create a child scope."""
        child = FakeScopeProtocol()
        child._parent = self
        return child

    async def dispose(self) -> None:
        """Dispose the scope."""
        self._disposed = True

    async def __getitem__(self, key: type[T]) -> T:
        """Get a service by type."""
        if key in self._services:
            return self._services[key]
        raise KeyError(f"Service not found: {key}")

    async def __setitem__(self, key: type[T], value: T) -> None:
        """Set a service by type."""
        self._services[key] = value

    async def get_service_keys(self) -> list[str]:
        """Get service keys in this scope."""
        return [str(k) for k in self._services.keys()]

    async def has_registration(self, interface: type[T]) -> bool:
        """Check if a service is registered in this scope."""
        return interface in self._services


@pytest.mark.asyncio
async def test_container_protocol_structural():
    """Verify that ContainerProtocol works with structural typing."""
    # Create a concrete implementation
    impl = ImplementsContainerProtocol()

    # This should pass if the implementation matches the protocol
    assert isinstance(
        impl, ContainerProtocol
    ), "Implementation doesn't satisfy ContainerProtocol"


@pytest.mark.asyncio
async def test_scope_protocol_structural():
    """Verify that ScopeProtocol works with structural typing."""
    # Create a concrete implementation
    impl = FakeScopeProtocol()

    # This should pass if the implementation matches the protocol
    assert isinstance(
        impl, ScopeProtocol
    ), "Implementation doesn't satisfy ScopeProtocol"
