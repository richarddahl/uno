"""
Service provider implementation for Uno DI.

This module provides the ServiceProvider class, which is responsible for resolving
services from the container. It maintains service instances according to their
lifetimes (singleton, scoped, transient) and handles dependency resolution.
"""

from __future__ import annotations

from typing import Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from uno.infrastructure.di.service_collection import ServiceCollection

from uno.infrastructure.di.resolver import ServiceResolver
from uno.infrastructure.di.service_scope import Scope, ServiceScope

TService = TypeVar("TService")


class ServiceProvider(Generic[TService]):
    """
    A service provider that resolves services from the container.

    This class maintains service instances according to their lifetimes
    (singleton, scoped, transient) and handles dependency resolution.
    """

    def __init__(self, collection: "ServiceCollection[TService]") -> None:
        """
        Initialize a new ServiceProvider instance.

        Args:
            collection: The service collection to build from
        """
        self._collection = collection
        self._resolver = ServiceResolver(
            registrations=collection._registrations,
            instances=collection._instances,
            auto_register=False,
        )

    def get_service(self, service_type: type[TService]) -> TService | None:
        """
        Get a service instance from the provider.

        Args:
            service_type: The type of service to resolve

        Returns:
            The resolved service instance, or None if not found
        """
        try:
            return self._resolver.resolve(service_type)
        except KeyError:
            return None

    def get_required_service(self, service_type: type[TService]) -> TService:
        """
        Get a required service instance from the provider.

        Args:
            service_type: The type of service to resolve

        Returns:
            The resolved service instance

        Raises:
            KeyError: If the service is not registered
        """
        return self._resolver.resolve(service_type)

    def configure_services(self, services: "ServiceCollection[TService]") -> None:
        """
        Configure additional services in the provider.

        Args:
            services: A ServiceCollection containing additional services to register
        """
        self._collection._registrations.update(services._registrations)
        self._collection._instances.update(services._instances)
        self._resolver = ServiceResolver(
            registrations=self._collection._registrations,
            instances=self._collection._instances,
            auto_register=False,
        )

    def create_scope(self, scope_id: str | None = None) -> "Scope[TService]":
        """
        Create a new async DI scope. Use as:
        async with provider.create_scope() as scope:
            ...
        Returns a Scope object that can resolve services within the scope.
        """
        return ServiceScope(self._collection, scope_id)

    def create_scope(self) -> "ServiceProvider[TService]":
        """
        Create a new service provider with a new scope.

        Returns:
            A new ServiceProvider instance with a new scope
        """
        scope = ServiceCollection[TService]()
        scope._registrations = self._collection._registrations.copy()
        scope._instances = self._collection._instances.copy()
        return ServiceProvider(scope)
