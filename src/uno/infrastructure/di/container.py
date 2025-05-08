"""
DI container implementation for uno.

This module implements the DI container that provides service registration and resolution.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, TYPE_CHECKING, Generic, Literal, TypeVar

if TYPE_CHECKING:
    from types import TracebackType

from uno.infrastructure.di.errors import (
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotRegisteredError,
    TypeMismatchError,
)

if TYPE_CHECKING:
    from types import TracebackType

T = TypeVar("T")


class ServiceRegistration(Generic[T]):
    """Represents a service registration in the container."""

    def __init__(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
        lifetime: Literal["singleton", "scoped", "transient"],
    ) -> None:
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime


ServiceFactory = Callable[["DIContainer"], T]
AsyncServiceFactory = Callable[["DIContainer"], Awaitable[T]]
Lifetime = Literal["singleton", "scoped", "transient"]


class _Scope(Generic[T]):
    """
    Internal scope implementation for service lifetime management.
    """

    def __init__(self, container: DIContainer, parent: _Scope[T] | None = None) -> None:
        self.container = container
        self.parent = parent
        self._services: dict[type[T], T] = {}
        self._scopes: list[_Scope] = []
        self._disposed = False

    @classmethod
    def singleton(cls, container: DIContainer) -> _Scope:
        """Create a singleton (root) scope with no parent."""
        return cls(container=container, parent=None)

    async def __aenter__(self) -> _Scope:
        self._check_not_disposed()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.dispose()

    async def dispose(self) -> None:
        """Dispose of all services in this scope and its children."""
        if self._disposed:
            return  # Already disposed, nothing to do

        # Dispose of all services in this scope using helper
        for service in self._services.values():
            await self.container._dispose_service(service)

        # Dispose of all child scopes
        for scope in list(self._scopes):
            await scope.dispose()

        self._disposed = True

        # Clear all services
        self._services.clear()
        self._scopes.clear()

    def _check_not_disposed(self) -> None:
        if self._disposed:
            raise ScopeError("Scope is disposed")

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service from this scope or parent scopes."""
        self._check_not_disposed()

        # First check in this scope
        if interface in self._services:
            return self._services[interface]

        # Try container registrations
        if interface in self.container._registrations:
            registration = self.container._registrations[interface]

            match registration.lifetime:
                case "singleton":
                    # Delegate singleton resolution to the container's singleton scope
                    return await self.container._singleton_scope.resolve(interface)
                case "scoped":
                    instance = await self.container._create_service(
                        interface, registration.implementation
                    )
                    self._services[interface] = instance
                    return instance
                case "transient":
                    return await self.container._create_service(
                        interface, registration.implementation
                    )

        # If not found and we have a parent, try the parent
        if self.parent is not None:
            return await self.parent.resolve(interface)

        # If all else fails
        raise ServiceNotRegisteredError(interface)

        # If all else fails
        raise ServiceNotRegisteredError(interface)

    def create_scope(self) -> _Scope:
        """Create a nested scope."""
        self._check_not_disposed()
        scope = type(self)(self.container, parent=self)
        self._scopes.append(scope)
        return scope

    def __getitem__(self, interface: type[T]) -> T:
        """Get a service instance from this scope or its parent."""
        self._check_not_disposed()
        if interface in self._services:
            return self._services[interface]
        if self.parent is not None:
            return self.parent[interface]
        raise ServiceNotRegisteredError(interface)

    def __setitem__(self, interface: type[T], service: T) -> None:
        """Set a service instance in this scope."""
        self._check_not_disposed()
        self._services[interface] = service


class DIContainer:
    """Dependency Injection container for managing service lifetimes.

    This container supports three service lifetimes:
    - Singleton: One instance per container
    - Scoped: One instance per scope
    - Transient: New instance per resolution

    Attributes:
        _singleton_scope: _Scope[Any]
            The singleton scope that contains all singleton services.
        _current_scope: Optional[_Scope[Any]]
            The current active scope, if any.
        _registrations: dict[type[Any], ServiceRegistration[Any]]
            Dictionary mapping service interfaces to their registrations.
        _scopes: list[_Scope[Any]]
            List of active scopes created by this container.
    """

    @staticmethod
    async def create(
        configurator: Callable[[DIContainer], Awaitable[None]],
    ) -> DIContainer:
        """Create and configure a new container.

        This factory method streamlines the container creation and configuration process,
        allowing all service registrations to be defined in a single callback function.

        Args:
            configurator: An async function that receives the new container and
                         registers all required services.

        Returns:
            A fully configured DIContainer instance ready for use.

        Example:
            ```python
            container = await DIContainer.create(
                async def configure(c):
                    # Register application services
                    await c.register_singleton(ILogger, ConsoleLogger)
                    await c.register_scoped(IDatabase, PostgresDatabase)
                    await c.register_transient(IEmailSender, SmtpEmailSender)

                    # Configure complex services
                    db = await c.resolve(IDatabase)
                    await db.initialize(connection_string="...")
            )
            ```
        """
        container = DIContainer()
        await configurator(container)

        # Optionally wait for any pending tasks to complete
        await container.wait_for_pending_tasks()

        return container

    def __init__(self) -> None:
        """Initialize a new DI container.

        Creates the singleton scope and initializes internal structures.
        """
        self._singleton_scope: _Scope[Any] = _Scope.singleton(self)
        self._current_scope: _Scope[Any] | None = None
        self._registrations: dict[type[Any], ServiceRegistration[Any]] = {}
        self._pending_tasks: set[asyncio.Task[None]] = set()
        self._disposed: bool = False
        self._scopes: list[_Scope[Any]] = [self._singleton_scope]
        self._logger = logging.getLogger(__name__)

    def _check_not_disposed(self) -> None:
        """Check if the container is disposed and raise an error if it is."""
        if self._disposed:
            raise ScopeError("Container is disposed")

    @contextlib.asynccontextmanager
    async def create_scope(self) -> AsyncGenerator[_Scope, None]:
        """Create a new scope for scoped services.

        This method returns an async context manager that yields a scope.
        The scope will be automatically disposed when the context exits.

        Example:
            ```python
            async with container.create_scope() as scope:
                service = await scope.resolve(IService)
            # Scope is automatically disposed here
            ```
        """
        self._check_not_disposed()

        # Create scope with parent if there's a current scope
        parent = self._current_scope if self._current_scope else self._singleton_scope
        scope = _Scope(self, parent=parent)
        self._scopes.append(scope)
        prev_scope = self._current_scope
        self._current_scope = scope

        try:
            yield scope
        finally:
            await scope.dispose()
            self._scopes.remove(scope)
            self._current_scope = prev_scope

    async def wait_for_pending_tasks(self) -> None:
        """Wait for all pending registration tasks to complete.

        This method should be called before disposing the container to ensure
        all asynchronous registration tasks have completed.

        Raises:
            Exception: If any of the pending tasks raised an exception.
        """
        if not self._pending_tasks:
            return

        # Make a copy to avoid modification during iteration
        tasks = self._pending_tasks.copy()
        done, pending = await asyncio.wait(tasks)

        # Clean up completed tasks
        for task in done:
            self._pending_tasks.discard(task)
            # Propagate any exceptions
            if task.exception():
                raise task.exception()

        # If there are still pending tasks, wait for them
        if pending:
            await asyncio.wait(pending)
            for task in pending:
                self._pending_tasks.discard(task)
                if task.exception():
                    raise task.exception()

    async def dispose(self) -> None:
        """Dispose the container and all its services.

        This method:
        1. Waits for any pending registration tasks
        2. Disposes all scopes
        3. Disposes singleton services

        After disposal, the container cannot be used and will raise ScopeError
        when attempting to register or resolve services.
        """
        if self._disposed:
            return

        # Wait for any pending tasks
        await self.wait_for_pending_tasks()

        # Dispose all scopes
        for scope in list(self._scopes):
            await scope.dispose()
        self._scopes.clear()
        self._current_scope = None

        # Dispose singleton services
        await self._singleton_scope.dispose()

        self._disposed = True

    async def register_singleton(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
        replace: bool = False,
    ) -> None:
        """Register a service with singleton lifetime.

        Args:
            interface: type[T]
                The interface type that will be used to resolve the service.
            implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T]
                Either a class that implements the interface, a synchronous factory function,
                or an asynchronous factory function that returns an instance of the implementation.
            replace: bool
                If True, replace any existing registration for this interface.
                Default: False

        Raises:
            ScopeError: If the container has been disposed.
            DuplicateRegistrationError: If a service is already registered for this interface and replace=False.
            TypeMismatchError: If the implementation does not implement the interface.
        """
        await self._register(interface, implementation, "singleton", replace=replace)

    async def register_scoped(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
        replace: bool = False,
    ) -> None:
        """Register a service with scoped lifetime.

        Args:
            interface: type[T]
                The interface type that will be used to resolve the service.
            implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T]
                Either a class that implements the interface, a synchronous factory function,
                or an asynchronous factory function that returns an instance of the implementation.
            replace: bool
                If True, replace any existing registration for this interface.
                Default: False

        Raises:
            ScopeError: If the container has been disposed.
            DuplicateRegistrationError: If a service is already registered for this interface and replace=False.
            TypeMismatchError: If the implementation does not implement the interface.
        """
        await self._register(interface, implementation, "scoped", replace=replace)

    async def register_transient(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
        replace: bool = False,
    ) -> None:
        """Register a service with transient lifetime.

        Args:
            interface: type[T]
                The interface type that will be used to resolve the service.
            implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T]
                Either a class that implements the interface, a synchronous factory function,
                or an asynchronous factory function that returns an instance of the implementation.
            replace: bool
                If True, replace any existing registration for this interface.
                Default: False

        Raises:
            ScopeError: If the container has been disposed.
            DuplicateRegistrationError: If a service is already registered for this interface and replace=False.
            TypeMismatchError: If the implementation does not implement the interface.
        """
        await self._register(interface, implementation, "transient", replace=replace)

    async def _register(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
        lifetime: Literal["singleton", "scoped", "transient"],
        replace: bool = False,
    ) -> None:
        """Internal method to register a service with the specified lifetime.

        Args:
            interface: type[T]
                The interface type that will be used to resolve the service.
            implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T]
                Either a class that implements the interface, a synchronous factory function,
                or an asynchronous factory function that returns an instance of the implementation.
            lifetime: Literal["singleton", "scoped", "transient"]
                The lifetime of the service:
                - "singleton": One instance per container
                - "scoped": One instance per scope
                - "transient": New instance per resolution
            replace: bool
                If True, replace any existing registration for this interface.
                Default: False

        Raises:
            ScopeError: If the container has been disposed.
            DuplicateRegistrationError: If a service is already registered for this interface and replace=False.
            TypeMismatchError: If the implementation does not implement the interface.
        """
        self._check_not_disposed()

        # Check if service is already registered
        if interface in self._registrations and not replace:
            raise DuplicateRegistrationError(interface)

        # Validate that the implementation implements the interface if it's a class
        if isinstance(implementation, type):
            # For runtime_checkable Protocols, we'll try to check at registration time
            # but also fall back to checking at instantiation time if needed
            try:
                # Try to detect Protocol structural compatibility without instantiation
                if hasattr(interface, "__annotations__"):
                    for method_name, _ in interface.__annotations__.items():
                        if not hasattr(implementation, method_name):
                            raise TypeMismatchError(interface, implementation)
            except Exception as e:
                # If we can't determine compatibility statically, we'll validate at instantiation
                self._logger.debug(
                    f"Could not validate {implementation} statically, will check at instantiation: {e}"
                )

        # Register the service
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
        )

        # Create singleton instances immediately
        if lifetime == "singleton":
            instance = await self._create_service(interface, implementation)
            self._singleton_scope[interface] = instance

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service.

        Args:
            interface: type[T]
                The interface type of the service to resolve.

        Returns:
            T: The service instance.

        Raises:
            ScopeError: If the container has been disposed or trying to resolve a scoped service outside of a scope.
            ServiceNotRegisteredError: If the service is not registered.
            TypeMismatchError: If the implementation does not implement the interface.
        """
        self._check_not_disposed()

        if interface not in self._registrations:
            raise ServiceNotRegisteredError(interface)

        registration = self._registrations[interface]

        match registration.lifetime:
            case "singleton":
                # Singleton services are stored in the singleton scope
                if interface not in self._singleton_scope._services:
                    instance = await self._create_service(
                        interface, registration.implementation
                    )
                    self._singleton_scope[interface] = instance
                return self._singleton_scope[interface]
            case "scoped":
                if not self._scopes:
                    raise ScopeError.outside_scope(interface)

                # Create the service if it doesn't exist in this scope
                return await self._scopes[-1].resolve(interface)
            case "transient":
                return await self._create_service(
                    interface, registration.implementation
                )

    async def _create_service(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
    ) -> T:
        """Create a service instance from the implementation.

        Args:
            interface: type[T]
                The interface type that will be used to resolve the service.
            implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T]
                Either a class that implements the interface, a synchronous factory function,
                or an asynchronous factory function that returns an instance of the implementation.

        Returns:
            T: The created service instance.

        Raises:
            TypeMismatchError: If the implementation does not implement the interface.
            ServiceCreationError: If the service cannot be created.
        """
        try:
            if inspect.isclass(implementation):
                # If it's a class, create an instance
                instance = implementation()
            elif inspect.iscoroutinefunction(implementation):
                # If it's an async factory function, check parameters
                signature = inspect.signature(implementation)
                if len(signature.parameters) > 0:
                    # If it takes parameters, pass the container
                    instance = await implementation(self)
                else:
                    # Otherwise, call it with no parameters
                    instance = await implementation()
            else:
                # If it's a sync factory function, check parameters
                signature = inspect.signature(implementation)
                if len(signature.parameters) > 0:
                    # If it takes parameters, pass the container
                    instance = implementation(self)
                else:
                    # Otherwise, call it with no parameters
                    instance = implementation()

            # Validate that the instance implements the interface
            if not isinstance(instance, interface):
                raise TypeMismatchError(interface, type(instance))

            return instance
        except Exception as e:
            raise ServiceCreationError(interface) from e

    async def _dispose_service(self, service: Any) -> None:
        """Safely dispose a service if it supports disposal."""
        try:
            if hasattr(service, "__aexit__"):
                await service.__aexit__(None, None, None)
            elif hasattr(service, "__exit__"):
                service.__exit__(None, None, None)
            elif hasattr(service, "dispose"):
                if inspect.iscoroutinefunction(service.dispose):
                    await service.dispose()
                else:
                    service.dispose()
        except Exception as e:
            self._logger.warning(
                f"Error disposing service {service}: {e}", exc_info=True
            )

    @contextlib.asynccontextmanager
    async def replace(
        self,
        interface: type[T],
        implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T],
        lifetime: Literal["singleton", "scoped", "transient"],
    ) -> AsyncGenerator[None, None]:
        """Temporarily replace a service registration for testing.

        This method creates a context manager that temporarily overrides a service
        registration. The original registration is restored when the context exits.

        Args:
            interface: type[T]
                The interface type of the service to replace.
            implementation: type[T] | ServiceFactory[T] | AsyncServiceFactory[T]
                The new implementation to use during the test.
            lifetime: Literal["singleton", "scoped", "transient"]
                The lifetime of the replacement service.

        Yields:
            None: The context manager yields when the replacement is active.

        Example:
            ```python
            # Replace a real service with a mock during a test
            async with container.replace(EmailService, MockEmailService):
                # Inside this block, EmailService will resolve to MockEmailService
                service = await container.resolve(EmailService)
                assert isinstance(service, MockEmailService)

            # Outside the block, the original EmailService is restored
            service = await container.resolve(EmailService)
            assert isinstance(service, RealEmailService)
            ```
        """
        self._check_not_disposed()

        # Store the original registration and instance if it exists
        original_registration = self._registrations.get(interface)
        original_instance = None

        if original_registration is not None:
            # Get the original instance from the appropriate scope
            if (
                original_registration.lifetime == "singleton"
                and interface in self._singleton_scope._services
            ):
                original_instance = self._singleton_scope._services[interface]
                # Remove from singleton scope to allow new registration
                del self._singleton_scope._services[interface]
            elif self._scopes and interface in self._scopes[-1]._services:
                original_instance = self._scopes[-1]._services[interface]
                # Optionally remove from current scope
                del self._scopes[-1]._services[interface]

            # Remove original registration
            del self._registrations[interface]

        try:
            # Register the replacement
            await self._register(interface, implementation, lifetime)
            yield
        finally:
            # Clean up any instances created during the replacement
            if lifetime == "singleton" and interface in self._singleton_scope._services:
                await self._dispose_service(self._singleton_scope._services[interface])
                del self._singleton_scope._services[interface]

            # Restore the original registration
            if original_registration is None:
                if interface in self._registrations:
                    del self._registrations[interface]
            else:
                self._registrations[interface] = original_registration

                # Restore the original instance if it exists
                if original_instance is not None:
                    if original_registration.lifetime == "singleton":
                        self._singleton_scope[interface] = original_instance
                    elif self._scopes:
                        self._scopes[-1]._services[interface] = original_instance

    @contextlib.asynccontextmanager
    async def use(self) -> AsyncGenerator[DIContainer, None]:
        """Context manager for using the container.

        Example:
            ```python
            async with DIContainer.use() as container:
                # Register services
                await container.register_singleton(ILogger, ConsoleLogger)

                # Resolve and use services
                logger = await container.resolve(ILogger)
                logger.log("Container created")

            # Container is automatically disposed here
            ```
        """
        try:
            yield self
        finally:
            await self.dispose()
