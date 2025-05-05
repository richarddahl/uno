# SPDX-FileCopyrightT_coext: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT_co
# uno framework
"""
Scoped dependency injection container for Uno framework.

Public API:
- ServiceCollection: Main API for registering services
- ServiceScope: Enum for service lifetimes
- ServiceFactory: Protocol for service factories

Internal/advanced classes (ServiceRegistration, _ServiceResolver) are not part of the public API.
"""

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from uno.infrastructure.di.resolver import ServiceResolver
from uno.infrastructure.di.service_registration import ServiceRegistration
from uno.infrastructure.di.service_scope import ServiceScope

if TYPE_CHECKING:
    from uno.infrastructure.di.service_provider import ServiceProvider


class ServiceCollection[TService]:
    """
    A collection of service registrations that can be used to build a service provider.

    This class provides methods for registering services with different lifetimes
    (singleton, scoped, transient) and building a service provider that can resolve
    these services.
    """

    def __init__(self, resolver_class: type[ServiceResolver] | None = None) -> None:
        """
        Initialize a new ServiceCollection instance.

        Args:
            resolver_class: Optional custom resolver class to use
        """
        self._registrations: dict[type[TService], ServiceRegistration[TService]] = {}
        self._instances: dict[type[TService], Any] = {}
        self._validations: list[Callable[[], None]] = []
        self._resolver_class = resolver_class or ServiceResolver

    def register(
        self,
        service_type: type[TService],
        implementation: type[TService] | None = None,
        **params: Any,
    ) -> "ServiceCollection[TService]":
        """
        Register a service with the container.

        Args:
            service_type: The type of service to register
            implementation: The implementation type (defaults to service_type)
            params: Additional parameters for service creation

        Returns:
            The ServiceCollection instance for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SINGLETON, params
        )
        return self

    def register_singleton(
        self,
        service_type: type[TService],
        implementation: type[TService] | None = None,
        **params: Any,
    ) -> "ServiceCollection[TService]":
        """
        Register a singleton service with the container.

        Args:
            service_type: The type of service to register
            implementation: The implementation type (defaults to service_type)
            params: Additional parameters for service creation

        Returns:
            The ServiceCollection instance for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SINGLETON, params
        )
        return self

    def add_scoped(
        self,
        service_type: type[TService],
        implementation: type[TService] | None = None,
        **params: Any,
    ) -> "ServiceCollection[TService]":
        """
        Register a scoped service with the container.

        Args:
            service_type: The type of service to register
            implementation: The implementation type (defaults to service_type)
            params: Additional parameters for service creation

        Returns:
            The ServiceCollection instance for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SCOPED, params
        )
        return self

    def add_transient(
        self,
        service_type: type[TService],
        implementation: type[TService] | None = None,
        **params: Any,
    ) -> "ServiceCollection[TService]":
        """
        Register a transient service with the container.

        Args:
            service_type: The type of service to register
            implementation: The implementation type (defaults to service_type)
            params: Additional parameters for service creation

        Returns:
            The ServiceCollection instance for method chaining
        """
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.TRANSIENT, params
        )
        return self

    def add_instance(
        self,
        service_type: type[TService],
        instance: TService,
    ) -> "ServiceCollection[TService]":
        """
        Register an existing instance as a singleton service.

        Args:
            service_type: The type of service to register
            instance: The existing instance to register

        Returns:
            The ServiceCollection instance for method chaining
        """
        self._instances[service_type] = instance
        # Also add to registrations for discovery/validation
        self._registrations[service_type] = ServiceRegistration(
            type(instance), ServiceScope.SINGLETON, {}
        )
        return self

    def add_validation(
        self,
        validation_fn: Callable[[], None],
    ) -> "ServiceCollection[TService]":
        """
        Add a validation function to be run before building the service provider.

        Args:
            validation_fn: A function that performs validation checks

        Returns:
            The ServiceCollection instance for method chaining
        """
        self._validations.append(validation_fn)
        return self

    def validate(self) -> None:
        """
        Validate the service registrations.
        Raises:
            ValueError: If there are circular dependencies or missing implementations
        """
        # TODO: Implement validation logic
        pass

    def build_service_provider(self) -> "ServiceProvider[TService]":
        """
        Build a service provider from the registered services.

        Returns:
            A ServiceProvider instance that can resolve services
        """
        self.validate()
        from uno.infrastructure.di.service_provider import ServiceProvider

        return ServiceProvider(self)
