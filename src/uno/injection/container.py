# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
DI container implementation for uno.

This module implements the DI container that provides service registration and resolution.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import contextvars
from collections.abc import AsyncGenerator, Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    TypeVar,
    cast,
)

from uno.injection.disposal import _DisposalManager
from uno.injection.errors import (
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotFoundError,
    TypeMismatchError,
    CircularDependencyError,
    ContainerDisposedError,
)
from uno.injection.config import ServiceLifetime

# Import ContainerProtocol only for the cast, not for inheritance
from uno.injection.protocols import ContainerProtocol

if TYPE_CHECKING:
    from uno.injection.protocols import (
        AsyncServiceFactoryProtocol,
        ServiceFactoryProtocol,
        ScopeProtocol,
    )
    from uno.logging.protocols import LoggerProtocol, LoggerScopeProtocol
from uno.injection.registration import ServiceRegistration
from uno.injection.resolution import _Scope

T = TypeVar("T")

# Context variable for dependency chain tracking (per-task/async context)
_DI_DEPENDENCY_CHAIN: contextvars.ContextVar[list[str]] = contextvars.ContextVar(
    "_DI_DEPENDENCY_CHAIN", default=[]
)


class Container:
    """Dependency Injection container for managing service lifetimes.

    This container supports three service lifetimes:
    - Singleton: One instance per container
    - Scoped: One instance per scope
    - Transient: New instance per resolution

    Attributes:
        _singleton_scope: _Scope
            The singleton scope that contains all singleton services.
        _current_scope: _Scope | None
            The current active scope, if any.
        _registrations: dict[type, ServiceRegistration]
            Dictionary mapping service interfaces to their registrations.
        _scopes: list[_Scope]
            List of active scopes created by this container.
    """

    def __init__(self) -> None:
        """Initialize a new DI container.

        Creates the singleton scope and initializes internal structures.
        """
        self._singleton_scope: _Scope = _Scope.singleton(self)
        self._current_scope: _Scope | None = None
        self._registrations: dict[type, ServiceRegistration[Any]] = {}
        self._scopes: list[_Scope] = [self._singleton_scope]
        # Use cast to tell the type checker that self satisfies ContainerProtocol
        self._disposal_manager = _DisposalManager(cast(ContainerProtocol, self))
        self._disposed: bool = False
        self._logger: logging.Logger | None = None

    async def dispose_services(self, services: list[Any]) -> None:
        """Dispose multiple services asynchronously.

        Args:
            services: List of services to dispose
        """
        for service in services:
            await self._dispose_service(service)

    async def _resolve_logger(self) -> logging.Logger:
        """Resolve a logger from the container or create a default one.

        Returns:
            A logger instance
        """
        try:
            logger = await self.resolve_optional(logging.Logger)
            if logger is not None:
                return logger
        except ImportError:
            pass

        logging.debug("Falling back to logging.getLogger")
        return logging.getLogger(__name__)

    async def _get_logger(self) -> logging.Logger:
        """Get or lazily create a logger.

        Returns:
            A logger instance
        """
        if self._logger is None:
            self._logger = await self._resolve_logger()
        return self._logger

    async def resolve_optional(self, interface: type[T]) -> T | None:
        """Resolve a service instance or return None if not registered.

        Similar to resolve(), but returns None instead of raising an error when
        the service is not registered.

        Args:
            interface: type[T]
                The interface type of the service to resolve.

        Returns:
            T | None: The service instance, or None if not registered.

        Raises:
            ScopeError: If the container has been disposed or trying to resolve a scoped service outside of a scope.
            TypeMismatchError: If the implementation does not implement the interface.
        """
        await self._check_not_disposed("resolve_optional")

        # Check if service is registered before attempting to resolve
        if interface not in self._registrations:
            return None  # Return None instead of raising an error for optional services

        # If registered, use the standard resolve method
        return await self.resolve(interface)

    @classmethod
    async def create(
        cls, configurator: Callable[[Container], Awaitable[None]] = None
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
        if configurator is None:

            async def configurator(_):  # type: ignore
                pass

        try:
            await configurator(container)
        except Exception as e:
            # If an error occurs during configuration, ensure any coroutines are closed
            import inspect

            if inspect.iscoroutine(container):
                container.close()
            raise e
        return container

    async def _check_not_disposed(self, operation: str) -> None:
        """Check if the container is disposed and raise an error if it is.

        Args:
            operation: The operation being attempted

        Raises:
            ContainerDisposedError: If the container is disposed
        """
        if self._disposed:
            # Use the standard constructor instead of async_init
            from uno.injection.errors import ContainerDisposedError

            # Create the error using the new constructor pattern
            error = ContainerDisposedError(
                message=f"Container has been disposed and cannot perform: {operation}",
                operation=operation,
                # Add any other context information you need
            )

            # If you need to capture container state, consider using a separate utility
            # For example:
            # await capture_container_state(error, self)

            raise error

    async def get_registration_keys(self) -> list[str]:
        """Get all registered service keys asynchronously.

        Returns:
            A list of service keys (type names) that are registered in this container.
        """
        await self._check_not_disposed("register")
        return [t.__name__ for t in self._registrations]

    async def get_scopes(self) -> list[_Scope]:
        """Get all scopes managed by this container.

        Returns:
            A list of all scopes managed by this container.
        """
        await self._check_not_disposed("get_scopes")
        return self._scopes

    async def get_singleton_scope(self) -> _Scope:
        """Get the singleton scope for this container.

        Returns:
            The singleton scope for this container.
        """
        await self._check_not_disposed("get_singleton_scope")
        return self._singleton_scope

    async def get_scope_chain(self) -> list[_Scope]:
        """Get the chain of scopes from current to root asynchronously.

        Returns:
            A list of scopes from the current scope to the root scope.
        """
        await self._check_not_disposed("get_scope_chain")
        if self._current_scope is None:
            return [self._singleton_scope]

        chain = []
        scope: _Scope | None = self._current_scope
        while scope is not None:
            chain.append(scope)
            scope = scope.parent

        return chain

    async def _dispose_service(self, service: Any) -> None:
        """Safely dispose a service using the disposal manager (internal use)."""
        await self._disposal_manager.dispose_service(service)

    @contextlib.asynccontextmanager
    async def create_scope(
        self, propagate_logger_scope_errors: bool = False
    ) -> AsyncGenerator[_Scope, None]:
        """Create a new scope for scoped services, and align logger scope with DI scope.

        This method returns an async context manager that yields a scope.
        The scope will be automatically disposed when the context exits.
        If LoggerScope is registered, a logger scope is also entered/exited.

        Args:
            propagate_logger_scope_errors: If True, exceptions from logger scope's __aexit__
                will be propagated rather than caught and logged (useful for testing)

        Example:
            ```python
            async with container.create_scope() as scope:
                service = await scope.resolve(IService)
            # Scope is automatically disposed here
            ```
        """
        await self._check_not_disposed("create_scope")

        # Create a new scope
        scope = await self._singleton_scope.create_scope()
        self._scopes.append(scope)
        self._current_scope = scope

        # Set up logger scope if available
        logger_scope_cm = None

        try:
            # Try to get the LoggerScopeProtocol
            try:
                # Import LoggerScopeProtocol only when needed to avoid circular imports
                from uno.logging.protocols import (
                    LoggerScopeProtocol as LoggerScopeProtocolCls,
                )

                logger_scope = await self.resolve_optional(LoggerScopeProtocolCls)
            except (ImportError, NameError):
                # Try a string-based lookup if the protocol isn't available
                logger_scope = await self.resolve_optional("LoggerScopeProtocol")

            # Set up logger scope context manager if available
            if logger_scope is not None and hasattr(logger_scope, "scope"):
                # Get the context manager from the scope method
                scope_result = logger_scope.scope(f"di_scope_{id(scope)}")

                # Use asyncio.iscoroutine for more reliable coroutine detection
                if asyncio.iscoroutine(scope_result):
                    scope_result = await scope_result

                logger_scope_cm = scope_result
                # Then enter the context
                await logger_scope_cm.__aenter__()
        except Exception as e:
            # Log but continue if logger scope resolution fails
            logger = await self._get_logger()
            logger.debug(f"Failed to set up logger scope: {e}")

        try:
            # Yield the scope for use
            yield scope
        finally:
            # Clean up logger scope if it was created
            if logger_scope_cm is not None:
                try:
                    # Always call __aexit__ directly and handle exceptions based on parameter
                    await logger_scope_cm.__aexit__(None, None, None)
                except Exception as e:
                    if propagate_logger_scope_errors:
                        # Re-raise the exception if we're supposed to propagate errors
                        raise
                    else:
                        # In normal operation, catch and log exceptions
                        logger = await self._get_logger()
                        logger.debug(f"Error exiting logger scope: {e}")

            # Clean up the scope
            if scope in self._scopes:
                self._scopes.remove(scope)

            # Reset current scope
            if self._current_scope is scope:
                self._current_scope = scope.parent

            # Dispose the scope
            await scope.dispose()

    async def wait_for_pending_tasks(self) -> None:
        """Wait for all pending registration tasks to complete.

        This method should be called before disposing the container to ensure
        all asynchronous registration tasks have completed.

        Raises:
            Exception: If any of the pending tasks raised an exception.
        """
        # Skip the disposed check for this method, as it needs to work during disposal
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
        if self._disposed:
            return  # Already disposed

        # Mark as disposed first to prevent new registrations during disposal
        self._disposed = True

        # Wait for any pending tasks
        await self.wait_for_pending_tasks()

        # Use the disposal manager to properly dispose all services
        await self._disposal_manager.dispose_container()

    async def register_singleton(
        self,
        interface: type[Any],
        implementation: Any,
        replace: bool = False,
    ) -> None:
        import asyncio

        # Remove previous instance if replace=True
        if replace and interface in self._singleton_scope._services:
            del self._singleton_scope._services[interface]

        # If implementation is a class, instantiate it with no arguments
        if isinstance(implementation, type):
            instance = implementation()
        # If implementation is a callable (but not a class), call it with self and await if needed
        elif callable(implementation):
            if asyncio.iscoroutinefunction(implementation):
                instance = await implementation(self)
            else:
                result = implementation(self)
                if asyncio.iscoroutine(result):
                    instance = await result
                else:
                    instance = result
        else:
            instance = implementation
        # Store the instance directly in the singleton scope
        await self._register(interface, instance, ServiceLifetime.SINGLETON, replace)

    async def register_scoped(
        self,
        interface: type[Any],
        implementation: Any,
        replace: bool = False,
    ) -> None:
        await self._register(interface, implementation, ServiceLifetime.SCOPED, replace)

    async def register_transient(
        self,
        interface: type[Any],
        implementation: Any,
        replace: bool = False,
    ) -> None:
        await self._register(
            interface, implementation, ServiceLifetime.TRANSIENT, replace
        )

    async def _register(
        self,
        interface: type[Any],
        implementation: Any,
        lifetime: ServiceLifetime,
        replace: bool = False,
    ) -> None:
        await self._check_not_disposed("get_registration_keys")
        if interface in self._registrations and replace:
            for scope in self._scopes:
                if interface in scope._services:
                    del scope._services[interface]
        elif interface in self._registrations and not replace:
            raise DuplicateRegistrationError(interface)
        registration = ServiceRegistration(interface, implementation, lifetime)
        self._registrations[interface] = registration
        # For singleton, store the instance in the singleton scope
        if lifetime == ServiceLifetime.SINGLETON:
            self._singleton_scope._services[interface] = implementation

    async def create_service(self, interface: type[Any], implementation: Any) -> Any:
        import asyncio

        if isinstance(implementation, type):
            try:
                return implementation()
            except Exception as exc:
                # Special handling for circular dependency errors - propagate directly
                if isinstance(exc, CircularDependencyError):
                    raise exc
                # Use async_init instead of direct instantiation
                raise await ServiceCreationError.async_init(
                    service_type=interface,
                    original_error=exc,
                    container=cast(ContainerProtocol, self),
                )
        elif callable(implementation):
            try:
                result = implementation(self)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as exc:
                # Special handling for circular dependency errors - propagate directly
                if isinstance(exc, CircularDependencyError):
                    raise exc
                # Use async_init instead of direct instantiation
                raise await ServiceCreationError.async_init(
                    service_type=interface,
                    original_error=exc,
                    container=cast(ContainerProtocol, self),
                )
        else:
            return implementation

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service instance asynchronously.

        Args:
            interface: The interface type of the service to resolve

        Returns:
            An instance of the requested service

        Raises:
            ScopeError: If trying to resolve a scoped service outside of a scope
            ServiceNotFoundError: If the service is not registered
            CircularDependencyError: If a circular dependency is detected
        """
        await self._check_not_disposed("resolve")

        # Check if service is registered
        if interface not in self._registrations:
            raise await ServiceNotFoundError.async_init(
                service_type=interface, container=cast(ContainerProtocol, self)
            )

        # Get the type name for dependency tracking
        service_type_name = getattr(interface, "__name__", str(interface))

        # Track dependency chain to detect circular dependencies
        dependency_chain = _DI_DEPENDENCY_CHAIN.get()

        # Check for circular dependencies
        if service_type_name in dependency_chain:
            # Create a new chain that includes the current service to show the complete cycle
            circular_chain = dependency_chain + [service_type_name]
            raise await CircularDependencyError.async_init(
                container=cast(ContainerProtocol, self),
                dependency_chain=circular_chain,
            )

        # Set a new context with the current service added to the chain
        token = _DI_DEPENDENCY_CHAIN.set(dependency_chain + [service_type_name])

        try:
            registration = self._registrations[interface]

            # Singleton: always return the instance from the singleton scope
            if registration.lifetime == ServiceLifetime.SINGLETON:
                return self._singleton_scope._services[interface]

            # Check for scoped service outside of scope
            if registration.lifetime == ServiceLifetime.SCOPED and (
                len(self._scopes) <= 1 or self._current_scope is None
            ):
                # Only singleton scope exists or no current scope
                raise ScopeError.outside_scope(interface)

            policy = registration.lifetime_policy
            scope = self._scopes[-1] if self._scopes else self._singleton_scope
            key = interface

            async def factory() -> Any:
                return await self.create_service(interface, registration.implementation)

            if hasattr(policy, "get_instance"):
                instance = await policy.get_instance(scope, factory, key)
            else:
                # If the policy doesn't have get_instance, use the factory directly
                instance = await factory()
            return cast(T, instance)
        finally:
            # Restore the previous dependency chain
            _DI_DEPENDENCY_CHAIN.reset(token)

    async def replace(
        self,
        interface: type[Any],
        implementation: Any,
        lifetime: ServiceLifetime,
    ) -> AsyncGenerator[None, None]:  # Add proper return type
        await self._check_not_disposed("get_registration_keys")
        original_registration = self._registrations.get(interface)
        original_instance = None
        if original_registration is not None:
            if (
                original_registration.lifetime == ServiceLifetime.SINGLETON
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
            await self._register(interface, implementation, lifetime, replace=True)
            yield
        finally:
            await self._restore_original(
                interface, original_registration, original_instance, lifetime
            )

    async def _restore_original(
        self,
        interface: type[Any],
        original_registration: Any,
        original_instance: Any,
        lifetime: ServiceLifetime,
    ) -> None:
        if original_instance is not None:
            if lifetime == ServiceLifetime.SINGLETON:
                self._singleton_scope._services[interface] = original_instance
            else:
                self._scopes[-1]._services[interface] = original_instance
        if original_registration is None:
            if interface in self._registrations:
                del self._registrations[interface]
        else:
            self._registrations[interface] = original_registration
            if original_instance is not None:
                if original_registration.lifetime == ServiceLifetime.SINGLETON:
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
