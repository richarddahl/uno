"""
DI container implementation for uno.

This module implements the DI container that provides service registration and resolution.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from uno.di.disposal import _DisposalManager
from uno.di.errors import (
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotRegisteredError,
    TypeMismatchError,
)
from uno.di.registration import ServiceRegistration
from uno.di.resolution import _Scope
from uno.di.shared_types import ContainerProtocol

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from uno.di.types import (
        AsyncServiceFactoryProtocol,
        ServiceFactoryProtocol,
    )

T = TypeVar("T")


class Container(ContainerProtocol):
    """Dependency Injection container for managing service lifetimes.

    This container supports three service lifetimes:
    - Singleton: One instance per container
    - Scoped: One instance per scope
    - Transient: New instance per resolution

    Attributes:
        _singleton_scope: ScopeProtocol[Any]
            The singleton scope that contains all singleton services.
        _current_scope: Optional[ScopeProtocol[Any]]
            The current active scope, if any.
        _registrations: dict[type[Any], ServiceRegistration[Any]]
            Dictionary mapping service interfaces to their registrations.
        _scopes: list[ScopeProtocol[Any]]
            List of active scopes created by this container.
    """

    def __init__(self) -> None:
        """Initialize a new DI container.

        Creates the singleton scope and initializes internal structures.
        """
        self._singleton_scope: _Scope = _Scope.singleton(self)
        self._current_scope: _Scope | None = None
        self._registrations: dict[type[Any], ServiceRegistration[Any]] = {}
        self._scopes: list[_Scope] = [self._singleton_scope]
        self._disposal_manager = _DisposalManager(self)
        self._disposed: bool = False
        self._logger = logging.getLogger(__name__)

    @classmethod
    async def create(
        cls, configurator: Callable[[Container], Awaitable[None]]
    ) -> Container:
        """Create and configure a new container.

        This factory method streamlines the container creation and configuration process,
        allowing all service registrations to be defined in a single callback function.

        Args:
            configurator: An async function that receives the new container and
                         registers all required services.

        Returns:
            A fully configured Container instance ready for use.

        Example:
            ```python
            container = await Container.create(
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
        container = cls()
        await configurator(container)
        return container

    def _check_not_disposed(self) -> None:
        """Check if the container is disposed and raise an error if it is."""
        if self._disposed:
            raise ScopeError("Container has been disposed")

    @contextlib.asynccontextmanager
    async def create_scope(self) -> AsyncGenerator[_Scope]:
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
        scope = self._singleton_scope.create_scope()
        self._scopes.append(scope)
        try:
            yield scope
        finally:
            # Only dispose and remove if this is a root scope (parent is None or singleton_scope)
            if scope.parent is None or scope.parent is self._singleton_scope:
                await scope.dispose()
                if scope in self._scopes:
                    self._scopes.remove(scope)

    async def wait_for_pending_tasks(self) -> None:
        """Wait for all pending registration tasks to complete.

        This method should be called before disposing the container to ensure
        all asynchronous registration tasks have completed.

        Raises:
            Exception: If any of the pending tasks raised an exception.
        """
        await self._disposal_manager.wait_for_pending_tasks()

    async def dispose(self) -> None:
        """Dispose the container and all its services.

        This method:
        1. Waits for any pending registration tasks
        2. Disposes all scopes
        3. Disposes singleton services

        After disposal, the container cannot be used and will raise ScopeError
        when attempting to register or resolve services.
        """
        self._check_not_disposed()
        await self._disposal_manager.dispose_container()
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
        await self._register(interface, implementation, "singleton", replace)

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
        await self._register(interface, implementation, "scoped", replace)

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
        await self._register(interface, implementation, "transient", replace)

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

        # If replacing an existing registration, ensure we clean up properly first
        if interface in self._registrations and replace:
            # Remove the service from all scopes (including singleton scope)
            for scope in self._scopes:
                if interface in scope._services:
                    del scope._services[interface]
        elif interface in self._registrations and not replace:
            raise DuplicateRegistrationError(interface)

        registration = ServiceRegistration(interface, implementation, lifetime)  # type: ignore
        self._registrations[interface] = registration

        # Create singleton instance immediately
        if lifetime == "singleton":
            instance = await self._create_service(interface, implementation)
            self._singleton_scope._services[interface] = instance

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

        # Check if service is registered before attempting to resolve
        if interface not in self._registrations:
            raise ServiceNotRegisteredError(interface)

        # If trying to resolve a scoped service outside of a scope, provide a clear error
        registration = self._registrations[interface]
        if (
            registration.lifetime == "scoped" and len(self._scopes) <= 1
        ):  # Only singleton scope
            raise ScopeError.outside_scope(interface)

        # Delegate to the singleton scope's resolve method for actual resolution
        return await self._singleton_scope.resolve(interface)

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
            if isinstance(implementation, type):
                # Type is a class, instantiate it directly
                instance = implementation()
            elif asyncio.iscoroutinefunction(implementation):
                # Handle async factory function
                try:
                    # Try to call with container argument first (per AsyncServiceFactory definition)
                    instance = await implementation(self)
                except TypeError:
                    # Fall back to calling without arguments
                    instance = await implementation()
            else:
                # Handle sync factory function
                try:
                    # Try to call with container argument first (per ServiceFactory definition)
                    instance = implementation(self)
                except TypeError:
                    # Fall back to calling without arguments
                    instance = implementation()

            if not isinstance(instance, interface):
                raise TypeMismatchError(interface, type(instance))

            return instance

        except Exception as e:
            raise ServiceCreationError(interface, e) from e

    async def _dispose_service(self, service: Any) -> None:
        """Dispose a service if it has a dispose method.

        Args:
            service: Any
                The service instance to dispose.
        """
        await self._disposal_manager.dispose_service(service)

    @contextlib.asynccontextmanager
    async def replace(
        self,
        interface: type[Any],
        implementation: type[Any] | ServiceFactory[Any] | AsyncServiceFactory[Any],
        lifetime: Literal["singleton", "scoped", "transient"],
    ) -> AsyncGenerator[None]:
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

        # Save original registration and instance
        original_registration = self._registrations.get(interface)
        original_instance = None

        # Backup original instance if it exists
        if original_registration is not None:
            if (
                original_registration.lifetime == "singleton"
                and interface in self._singleton_scope._services
            ):
                original_instance = self._singleton_scope._services[interface]
                del self._singleton_scope._services[interface]
            elif self._scopes and interface in self._scopes[-1]._services:
                original_instance = self._scopes[-1]._services[interface]
                del self._scopes[-1]._services[interface]
            if interface in self._registrations:
                del self._registrations[interface]

        try:
            # Register the replacement
            await self._register(interface, implementation, lifetime, replace=True)
            yield
        finally:
            # Clean up the replacement
            await self._cleanup_replacement(interface)

            # Restore original registration and instance
            await self._restore_original(
                interface, original_registration, original_instance, lifetime
            )

    async def _cleanup_replacement(self, interface: type[Any]) -> None:
        """Clean up a replacement registration by removing it from all scopes."""
        # Remove the replacement registration from all scopes
        if interface in self._singleton_scope._services:
            del self._singleton_scope._services[interface]
        if self._scopes and interface in self._scopes[-1]._services:
            del self._scopes[-1]._services[interface]
        if interface in self._registrations:
            del self._registrations[interface]

    async def _restore_original(
        self,
        interface: type[Any],
        original_registration: Any,
        original_instance: Any,
        lifetime: Literal["singleton", "scoped", "transient"],
    ) -> None:
        """Restore the original registration and instance after replacement."""
        # Restore original service instance if it existed
        if original_instance is not None:
            if lifetime == "singleton":
                self._singleton_scope._services[interface] = original_instance
            else:
                self._scopes[-1]._services[interface] = original_instance

        # Restore the original registration
        if original_registration is None:
            if interface in self._registrations:
                del self._registrations[interface]
        else:
            self._registrations[interface] = original_registration

            # Restore the original instance if it exists
            if original_instance is not None:
                if original_registration.lifetime == "singleton":
                    self._singleton_scope._services[interface] = original_instance
                elif self._scopes:
                    self._scopes[-1]._services[interface] = original_instance

    @contextlib.asynccontextmanager
    async def use(self) -> AsyncGenerator[Container]:
        """Context manager for using the container.

        Example:
            ```python
            async with Container.use() as container:
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
