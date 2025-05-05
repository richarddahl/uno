from __future__ import annotations
from enum import Enum, auto
from types import TracebackType
from typing import Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from uno.infrastructure.di.service_collection import ServiceCollection
    from uno.infrastructure.di.service_registration import ServiceRegistration

TService = TypeVar("TService")


class ServiceScope(Enum):
    """
    Service lifetime scopes for dependency injection.

    Defines the lifetime of a service instance, including singleton (application),
    scoped, and transient.
    """

    SINGLETON = auto()  # One instance per container
    SCOPED = auto()  # One instance per scope (e.g., request)
    TRANSIENT = auto()  # New instance each time


class Scope(Generic[TService]):
    """
    A DI scope that provides scoped service resolution.

    Services resolved within a scope are scoped to that scope and are disposed
    when the scope is exited.
    """

    def __init__(
        self, collection: ServiceCollection[TService], scope_id: str | None = None
    ) -> None:
        """
        Initialize a new DI scope.

        Args:
            collection: The service collection to use for resolution
            scope_id: Optional identifier for the scope
        """
        self._collection = collection
        self._scope_id = scope_id
        self._instances: dict[type[TService], TService] = {}

    async def __aenter__(self) -> "Scope[TService]":
        """
        Enter the scope.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exit the scope and dispose scoped services.
        """
        for instance in self._instances.values():
            if hasattr(instance, "dispose"):
                dispose = getattr(instance, "dispose")
                if callable(dispose):
                    await dispose()

    def resolve(self, service_type: type[TService]) -> TService:
        """
        Resolve a service within the scope.

        Args:
            service_type: The type of service to resolve

        Returns:
            The resolved service instance

        Raises:
            KeyError: If the service is not registered
        """
        if service_type in self._instances:
            return self._instances[service_type]

        registration = self._collection._registrations.get(service_type)
        if registration is None:
            raise KeyError(f"Service {service_type.__name__} not registered")

        if registration.scope == ServiceScope.SINGLETON:
            if service_type in self._collection._instances:
                return self._collection._instances[service_type]
            instance = self._create_instance(service_type, registration)
            self._collection._instances[service_type] = instance
            return instance

        if registration.scope == ServiceScope.SCOPED:
            instance = self._create_instance(service_type, registration)
            self._instances[service_type] = instance
            return instance

        # TRANSIENT
        return self._create_instance(service_type, registration)

    def _create_instance(
        self, service_type: type[TService], registration: ServiceRegistration
    ) -> TService:
        """
        Create a new instance of the service.

        Args:
            service_type: The type of service to create
            registration: The service registration

        Returns:
            The created service instance
        """
        if registration.implementation is None:
            return service_type(**registration.params)

        if registration.implementation != service_type:
            return registration.implementation(**registration.params)

        return service_type(**registration.params)
