# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Scoped dependency injection container for Uno framework.

This module implements a hierarchical dependency injection container that supports
different scopes for services, such as singleton (application), scoped, and transient.
"""

import inspect
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from enum import Enum, auto
from typing import Any, Generic, TypeVar

from uno.core.errors.base import ErrorCode, FrameworkError

T = TypeVar("T")
ProviderT = TypeVar("ProviderT")


class ServiceScope(Enum):
    """Service lifetime scopes for dependency injection."""

    SINGLETON = auto()  # One instance per container
    SCOPED = auto()  # One instance per scope (e.g., request)
    TRANSIENT = auto()  # New instance each time


class ServiceRegistration(Generic[T]):
    """
    Service registration information.

    Holds the configuration for how a service should be resolved, including
    its implementation type or factory, scope, and initialization parameters.
    """

    def __init__(
        self,
        implementation: type[T] | Callable[..., T],
        scope: ServiceScope = ServiceScope.SINGLETON,
        params: dict[str, Any] | None = None,
    ):
        """
        Initialize service registration.

        Args:
            implementation: type or factory function for the service
            scope: Service lifetime scope
            params: Optional parameters to pass to the constructor/factory
        """
        self.implementation = implementation
        self.scope = scope
        self.params = params or {}


class _ServiceResolver:
    """
    Internal: Service resolver for dependency injection.

    This class is responsible for low-level service registration, resolution, and scoping.
    Not intended for direct use by application code. All application/service code should use ServiceProvider.
    """

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize the service resolver.

        Args:
            logger: Optional logger for diagnostic information
        """
        from uno.core.logging.logger import get_logger

        self._logger = logger or get_logger("uno.di")
        self._registrations: dict[type, ServiceRegistration] = {}
        self._singletons: dict[type, Any] = {}

    def register(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[..., T],
        scope: ServiceScope = ServiceScope.SINGLETON,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Register a service with the container.

        Args:
            service_type: The type or protocol to register
            implementation: The implementation type or factory function
            scope: The service lifetime scope
            params: Optional parameters to pass to the constructor/factory
        """
        registration = ServiceRegistration(implementation, scope, params)
        self._registrations[service_type] = registration
        self._logger.debug(
            f"Registered {service_type.__name__} with scope {scope.name}"
        )

        # Clear singleton cache for this type if it exists
        if service_type in self._singletons:
            del self._singletons[service_type]
            self._logger.debug(f"Cleared singleton cache for {service_type.__name__}")


    def register_instance(self, service_type: type[T], instance: T) -> None:
        """
        Register an existing instance as a singleton.

        Args:
            service_type: The type or protocol to register
            instance: The instance to register
        """
        self._singletons[service_type] = instance
        self._logger.debug(f"Registered instance of {service_type.__name__}")

    def resolve(self, service_type: type[T], scope=None) -> T:
        """
        Resolve a service by its type.

        Args:
            service_type: The type of service to resolve
            scope: The current Scope object if resolving a scoped service

        Returns:
            The resolved service instance

        Raises:
            FrameworkError: If the service is not registered
        """
        if service_type not in self._registrations:
            raise FrameworkError(
                f"Service {service_type.__name__} is not registered",
                error_code=ErrorCode.DEPENDENCY_ERROR
            )

        registration = self._registrations[service_type]
        lifetime = registration.scope

        if lifetime == ServiceScope.SINGLETON:
            if service_type not in self._singletons:
                self._singletons[service_type] = self._create_instance(registration)
            return self._singletons[service_type]
        elif lifetime == ServiceScope.TRANSIENT:
            return self._create_instance(registration)
        elif lifetime == ServiceScope.SCOPED:
            # Use contextvar-based scope management
            from .scope import Scope

            active_scope = scope or Scope.get_current_scope()
            if active_scope is None:
                raise FrameworkError(
                    f"Cannot resolve scoped service {service_type.__name__} outside of an active scope.",
                    error_code=ErrorCode.DEPENDENCY_ERROR
                )
            instance = active_scope.get_instance(service_type)
            if instance is None:
                instance = self._create_instance(registration)
                active_scope.set_instance(service_type, instance)
            return instance
        else:
            raise FrameworkError(
                f"Unknown service scope: {lifetime}",
                error_code=ErrorCode.DEPENDENCY_ERROR
            )

    # Internal use: for Scope and ServiceProvider to resolve with explicit scope
    def resolve_in_scope(self, service_type: type[T], scope) -> T:
        return self.resolve(service_type, scope=scope)

    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """
        Create a service instance from a registration.

        Args:
            registration: The service registration

        Returns:
            The created service instance
        """
        impl = registration.implementation
        params = registration.params.copy()

        # If it's a callable but not a class, just call it with params
        if callable(impl) and not inspect.isclass(impl):
            return impl(**params)

        # Otherwise it's a class, so we need to inspect its constructor
        sig = inspect.signature(impl.__init__)  # type: ignore

        # Get constructor params, excluding self
        for param_name, param in list(sig.parameters.items())[1:]:
            # Skip if we already have this param
            if param_name in params:
                continue

            # Skip if it has a default value
            if param.default is not param.empty:
                continue

            # Skip *args and **kwargs
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue

            # Try to resolve this parameter as a dependency
            param_type = param.annotation
            if param_type is not param.empty and param_type is not Any:
                try:
                    params[param_name] = self.resolve(param_type)
                except (KeyError, ValueError):
                    pass  # If we can't resolve it, leave it for the constructor to handle

        # Create the instance
        return impl(**params)  # type: ignore

    @contextmanager
    def create_scope(
        self, scope_id: str | None = None
    ) -> Generator["ServiceResolver", None, None]:
        """
        Create a service scope.

        This context manager creates a new scope for resolving scoped services,
        ensuring they are properly disposed when the scope ends.

        Args:
            scope_id: Optional scope identifier, defaults to a generated ID

        Yields:
            The service resolver with the active scope
        """
        scope_id = scope_id or f"scope_{id(object())}"
        self._logger.debug(f"Created scope {scope_id}")
        yield self

class ServiceCollection:
    """
    Collection for configuring service registrations.

    This class provides a fluent interface for registering services,
    making it easier to configure the dependency injection container.

    Note: ServiceCollection builds an internal _ServiceResolver. Do not use _ServiceResolver directly.
    """

    def __init__(self):
        """Initialize the service collection."""
        self._registrations: dict[type, ServiceRegistration] = {}
        self._instances: dict[type, Any] = {}

    def add_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[..., T] | None = None,
        **params: Any,
    ) -> "ServiceCollection":
        """
        Register a singleton service.

        Args:
            service_type: The type or protocol to register
            implementation: The implementation type or factory function, defaults to service_type
            **params: Parameters to pass to the constructor/factory

        Returns:
            The service collection for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SINGLETON, params
        )
        return self

    def add_instance(self, service_type: type[T], instance: T) -> "ServiceCollection":
        """
        Register an existing instance as a singleton.

        Args:
            service_type: The type or protocol to register
            instance: The instance to register

        Returns:
            The service collection for method chaining
        """
        self._instances[service_type] = instance
        return self

    def add_scoped(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[..., T] | None = None,
        **params: Any,
    ) -> "ServiceCollection":
        """
        Register a scoped service.

        Args:
            service_type: The type or protocol to register
            implementation: The implementation type or factory function, defaults to service_type
            **params: Parameters to pass to the constructor/factory

        Returns:
            The service collection for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SCOPED, params
        )
        return self

    def add_transient(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[..., T] | None = None,
        **params: Any,
    ) -> "ServiceCollection":
        """
        Register a transient service.

        Args:
            service_type: The type or protocol to register
            implementation: The implementation type or factory function, defaults to service_type
            **params: Parameters to pass to the constructor/factory

        Returns:
            The service collection for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.TRANSIENT, params
        )
        return self

    def build(self, logger: logging.Logger | None = None, resolver_class=None):
        """
        Build a service resolver from the collection.

        Args:
            logger: Optional logger for diagnostic information
            resolver_class: Internal use only. The resolver class to instantiate (default: _ServiceResolver)

        Returns:
            A configured internal service resolver
        """
        if resolver_class is None:
            resolver_class = _ServiceResolver
        resolver = resolver_class(logger)

        # Register all services
        for service_type, registration in self._registrations.items():
            resolver.register(
                service_type,
                registration.implementation,
                registration.scope,
                registration.params,
            )

        # Register all instances
        for service_type, instance in self._instances.items():
            resolver.register_instance(service_type, instance)

        return resolver
