# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Core interfaces for the Uno DI system.

This module defines the core protocols used by the DI system. All dependencies
must be passed explicitly from the composition root.
"""

from __future__ import annotations

from typing import (
    Protocol, TypeVar, Any, List, Dict, runtime_checkable, Type
)
from datetime import datetime, UTC
from enum import Enum, auto
from dataclasses import dataclass, field
from uno.core.errors.result import Result, Success, Failure

# Type variables for generic protocols
T = TypeVar("T")
TService = TypeVar("TService")
TEvent = TypeVar("TEvent", contravariant=True)
TComposite = TypeVar("TComposite", covariant=True)
TAggregate = TypeVar("TAggregate", covariant=True)
TMock = TypeVar("TMock", covariant=True)
TNext = TypeVar("TNext", contravariant=True)

@runtime_checkable
class ServiceResolverProtocol(Protocol):
    """Protocol for service resolution.

    Example:
        ```python
        class MyResolver(ServiceResolverProtocol):
            def resolve(self, service_type: type[Any], _resolving: set[type[Any]] = None) -> Result[Any, ServiceRegistrationError]:
                return Success(service)
        ```
    """

    def resolve(self, service_type: type[Any], _resolving: set[type[Any]] | None = None) -> Result[Any, ServiceRegistrationError]:
        """
        Resolve a service instance.

        Args:
            service_type: The type of service to resolve
            _resolving: Set of currently resolving types (for circular dependency detection)

        Returns:
            Success with the resolved service or Failure with an error
        """
        ...

class ServiceState(Enum):
    """Service state enumeration."""
    INITIALIZED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()

@dataclass
class ServiceHealth:
    """Service health information."""
    is_healthy: bool = True
    last_check: datetime = datetime.now(UTC)
    error_count: int = 0
    recovery_attempts: int = 0
    state: ServiceState = ServiceState.INITIALIZED
    details: dict[str, Any] = field(default_factory=dict)

@runtime_checkable
class ServiceLifecycleProtocol(Protocol):
    """
    Protocol for services with lifecycle hooks.

    This protocol defines the lifecycle hooks that services can implement
    to participate in the DI container's lifecycle management.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def get_state(self) -> ServiceState:
        """Get the current state of the service."""
        ...

    def get_health(self) -> ServiceHealth:
        """Get the current health status of the service."""
        ...

    async def initialize(self) -> None:
        """
        Initialize the service.

        This method is called when the service is first created.
        It should perform any necessary setup or initialization.

        State transition: INITIALIZED -> RUNNING
        """
        ...

    async def start(self) -> None:
        """
        Start the service.

        This method is called when the service should start processing.
        It should perform any necessary startup operations.

        State transition: INITIALIZED -> RUNNING
        """
        ...

    async def pause(self) -> None:
        """
        Pause the service.

        This method is called when the service should temporarily stop processing.
        It should perform any necessary pause operations.

        State transition: RUNNING -> PAUSED
        """
        ...

    async def resume(self) -> None:
        """
        Resume the service.

        This method is called when the service should resume processing.
        It should perform any necessary resume operations.

        State transition: PAUSED -> RUNNING
        """
        ...

    async def stop(self) -> None:
        """
        Stop the service.

        This method is called when the service should stop processing.
        It should perform any necessary shutdown operations.

        State transition: RUNNING/PAUSED -> STOPPED
        """
        ...

    async def cleanup(self) -> None:
        """
        Clean up the service.

        This method is called when the service is being disposed of.
        It should perform any necessary cleanup operations.

        State transition: STOPPED -> INITIALIZED
        """
        ...

@runtime_checkable
class ServiceEventHandlerProtocol(Protocol[TEvent]):
    """
    Protocol for service event handlers.

    This protocol defines the interface for handling service events.
    Event handlers are used to process events emitted by services.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    async def handle_event(self, event: TEvent) -> None:
        """
        Handle a service event.

        Args:
            event: The event to handle

        Example:
            ```python
            class MyEventHandler(ServiceEventHandlerProtocol[MyEvent]):
                async def handle_event(self, event: MyEvent) -> None:
                    # Handle the event
                    pass
            ```
        """
        ...

@runtime_checkable
class ServiceEventEmitterProtocol(Protocol[TEvent]):
    """
    Protocol for service event emitters.

    This protocol defines the interface for emitting service events.
    Event emitters are used to notify other services of state changes.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    async def emit_event(self, event: TEvent) -> None:
        """
        Emit a service event.

        Args:
            event: The event to emit

        Example:
            ```python
            class MyEventEmitter(ServiceEventEmitterProtocol[MyEvent]):
                async def emit_event(self, event: MyEvent) -> None:
                    # Emit the event
                    pass
            ```
        """
        ...

@runtime_checkable
class ServiceMockProtocol(Protocol[TMock]):
    """
    Protocol for service mocks.

    This protocol defines the interface for mocking services in tests.
    Mocks are used to simulate service behavior during testing.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def setup(self) -> None:
        """
        Set up the mock.

        This method is called before the mock is used.
        It should perform any necessary setup operations.

        Example:
            ```python
            class MyServiceMock(ServiceMockProtocol[MyService]):
                def setup(self) -> None:
                    # Set up the mock
                    pass
            ```
        """
        ...

    def verify(self) -> None:
        """
        Verify the mock.

        This method is called after the mock is used.
        It should verify that the mock was used as expected.

        Example:
            ```python
            class MyServiceMock(ServiceMockProtocol[MyService]):
                def verify(self) -> None:
                    # Verify the mock
                    pass
            ```
        """
        ...

    def reset(self) -> None:
        """
        Reset the mock.

        This method is called to reset the mock to its initial state.
        It should perform any necessary reset operations.

        Example:
            ```python
            class MyServiceMock(ServiceMockProtocol[MyService]):
                def reset(self) -> None:
                    # Reset the mock
                    pass
            ```
        """
        ...

    def get_mock(self) -> TMock:
        """
        Get the mock instance.

        Returns:
            The mock instance

        Example:
            ```python
            class MyServiceMock(ServiceMockProtocol[MyService]):
                def get_mock(self) -> MyService:
                    # Return the mock instance
                    return self._mock
            ```
        """
        ...

@runtime_checkable
class ServiceRecoveryProtocol(Protocol):
    """
    Protocol for service recovery.

    This protocol defines the interface for recovering services from errors.
    Recovery mechanisms are used to restore service functionality after failures.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    async def recover(self) -> bool:
        """
        Attempt to recover the service.

        Returns:
            True if recovery was successful, False otherwise

        Example:
            ```python
            class MyServiceRecovery(ServiceRecoveryProtocol):
                async def recover(self) -> bool:
                    # Attempt recovery
                    return success
            ```
        """
        ...

    def can_recover(self) -> bool:
        """
        Check if the service can be recovered.

        Returns:
            True if the service can be recovered, False otherwise

        Example:
            ```python
            class MyServiceRecovery(ServiceRecoveryProtocol):
                def can_recover(self) -> bool:
                    # Check if recovery is possible
                    return can_recover
            ```
        """
        ...

@runtime_checkable
class CompositeServiceProtocol(Protocol[TComposite]):
    """
    Protocol for composite services.

    This protocol defines the interface for composing multiple services into a single service.
    Composite services are used to combine functionality from multiple services.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def compose(self, services: list[Any]) -> TComposite:
        """
        Compose services into a composite service.

        Args:
            services: The services to compose

        Returns:
            The composite service

        Example:
            ```python
            class MyCompositeService(CompositeServiceProtocol[MyService]):
                def compose(self, services: list[Any]) -> MyService:
                    # Compose the services
                    return composite_service
            ```
        """
        ...

@runtime_checkable
class ServiceComposite(Protocol):
    """
    Protocol for service composition.

    This protocol defines the interface for composing services in the DI container.
    It provides methods for managing service composition and lifecycle.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def add_service(self, service: Any) -> None:
        """
        Add a service to the composition.

        Args:
            service: The service to add

        Example:
            ```python
            composite = ServiceComposite()
            composite.add_service(my_service)
            ```
        """
        ...

    def remove_service(self, service: Any) -> None:
        """
        Remove a service from the composition.

        Args:
            service: The service to remove

        Example:
            ```python
            composite = ServiceComposite()
            composite.remove_service(my_service)
            ```
        """
        ...

    def get_services(self) -> list[Any]:
        """
        Get all services in the composition.

        Returns:
            List of services in the composition

        Example:
            ```python
            composite = ServiceComposite()
            services = composite.get_services()
            ```
        """
        ...

    async def initialize(self) -> None:
        """
        Initialize all services in the composition.

        Example:
            ```python
            composite = ServiceComposite()
            await composite.initialize()
            ```
        """
        ...

    async def cleanup(self) -> None:
        """
        Clean up all services in the composition.

        Example:
            ```python
            composite = ServiceComposite()
            await composite.cleanup()
            ```
        """
        ...

@runtime_checkable
class AggregateServiceProtocol(Protocol[TAggregate]):
    """
    Protocol for aggregate services.

    This protocol defines the interface for aggregating multiple services into a single service.
    Aggregate services are used to combine functionality from multiple services.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def aggregate(self, services: list[Any]) -> TAggregate:
        """
        Aggregate services into an aggregate service.

        Args:
            services: The services to aggregate

        Returns:
            The aggregate service

        Example:
            ```python
            class MyAggregateService(AggregateServiceProtocol[MyService]):
                def aggregate(self, services: list[Any]) -> MyService:
                    # Aggregate the services
                    return aggregate_service
            ```
        """
        ...

@runtime_checkable
class ServiceAggregate(Protocol):
    """
    Protocol for service aggregation.

    This protocol defines the interface for aggregating services in the DI container.
    It provides methods for managing service aggregation and lifecycle.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def add_service(self, service: Any) -> None:
        """
        Add a service to the aggregation.

        Args:
            service: The service to add

        Example:
            ```python
            aggregate = ServiceAggregate()
            aggregate.add_service(my_service)
            ```
        """
        ...

    def remove_service(self, service: Any) -> None:
        """
        Remove a service from the aggregation.

        Args:
            service: The service to remove

        Example:
            ```python
            aggregate = ServiceAggregate()
            aggregate.remove_service(my_service)
            ```
        """
        ...

    def get_services(self) -> list[Any]:
        """
        Get all services in the aggregation.

        Returns:
            List of services in the aggregation

        Example:
            ```python
            aggregate = ServiceAggregate()
            services = aggregate.get_services()
            ```
        """
        ...

    async def initialize(self) -> None:
        """
        Initialize all services in the aggregation.

        Example:
            ```python
            aggregate = ServiceAggregate()
            await aggregate.initialize()
            ```
        """
        ...

    async def cleanup(self) -> None:
        """
        Clean up all services in the aggregation.

        Example:
            ```python
            aggregate = ServiceAggregate()
            await aggregate.cleanup()
            ```
        """
        ...

@runtime_checkable
class ServiceChainProtocol(Protocol):
    """
    Protocol for service chains.

    This protocol defines the interface for chaining multiple services together.
    Service chains are used to execute services in sequence.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def next(self, service: Any) -> None:
        """
        Add a service to the chain.

        Args:
            service: The service to add

        Example:
            ```python
            class MyServiceChain(ServiceChainProtocol):
                def next(self, service: Any) -> None:
                    # Add service to chain
                    pass
            ```
        """
        ...

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the service chain.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the chain execution

        Example:
            ```python
            class MyServiceChain(ServiceChainProtocol):
                async def execute(self, *args: Any, **kwargs: Any) -> Any:
                    # Execute chain
                    return result
            ```
        """
        ...

@runtime_checkable
class ServiceHealthCheckProtocol(Protocol):
    """
    Protocol for service health checks.

    This protocol defines the interface for checking service health.
    Health checks are used to monitor service health and detect issues.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def check_health(self) -> ServiceHealth:
        """
        Check the health of the service.

        Returns:
            The health status of the service

        Example:
            ```python
            class MyHealthCheck(ServiceHealthCheckProtocol):
                def check_health(self) -> ServiceHealth:
                    # Check service health
                    return health_status
            ```
        """
        ...

@runtime_checkable
class ServiceConstraintValidatorProtocol(Protocol):
    """
    Protocol for service constraint validators.

    This protocol defines the interface for validating service constraints.
    Constraint validators are used to ensure services meet their requirements.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def validate_constraints(self, service: Any) -> None:
        """
        Validate service constraints.

        Args:
            service: The service to validate

        Raises:
            ServiceConstraintError: If validation fails

        Example:
            ```python
            class MyConstraintValidator(ServiceConstraintValidatorProtocol):
                def validate_constraints(self, service: Any) -> None:
                    # Validate service constraints
                    pass
            ```
        """
        ...

@runtime_checkable
class ServiceInterceptorProtocol(Protocol[TNext]):
    """
    Protocol for service interceptors.

    This protocol defines the interface for intercepting service method calls.
    Interceptors are used to add cross-cutting concerns to services.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    async def intercept(self, next: TNext, *args: Any, **kwargs: Any) -> Any:
        """
        Intercept a service method call.

        Args:
            next: The next interceptor or service method
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the intercepted call

        Example:
            ```python
            class MyInterceptor(ServiceInterceptorProtocol[Callable]):
                async def intercept(self, next: Callable, *args: Any, **kwargs: Any) -> Any:
                    # Intercept the call
                    return await next(*args, **kwargs)
            ```
        """
        ...

@runtime_checkable
class ServiceMiddlewareProtocol(Protocol[TNext]):
    """
    Protocol for service middleware.

    This protocol defines the interface for service middleware.
    Middleware is used to add cross-cutting concerns to services.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    async def __call__(self, next: TNext, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the middleware.

        Args:
            next: The next middleware or service method
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the middleware chain

        Example:
            ```python
            class MyMiddleware(ServiceMiddlewareProtocol[Callable]):
                async def __call__(self, next: Callable, *args: Any, **kwargs: Any) -> Any:
                    # Execute middleware
                    return await next(*args, **kwargs)
            ```
        """
        ...

@runtime_checkable
class ServiceContractProtocol(Protocol):
    """
    Protocol for service contracts.

    This protocol defines the interface for service contracts.
    Contracts are used to define service behavior and requirements.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def validate_input(self, *args: Any, **kwargs: Any) -> None:
        """
        Validate service method input.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Raises:
            ServiceValidationError: If validation fails

        Example:
            ```python
            class MyContract(ServiceContractProtocol):
                def validate_input(self, *args: Any, **kwargs: Any) -> None:
                    # Validate input
                    pass
            ```
        """
        ...

    def validate_output(self, result: Any) -> None:
        """
        Validate service method output.

        Args:
            result: The method result

        Raises:
            ServiceValidationError: If validation fails

        Example:
            ```python
            class MyContract(ServiceContractProtocol):
                def validate_output(self, result: Any) -> None:
                    # Validate output
                    pass
            ```
        """
        ...

class MiddlewareRegistry(Protocol):
    """
    Protocol for middleware registration in the event system.

    This protocol defines the interface for registering middleware components
    either globally or for specific event types.

    Note: All dependencies must be passed explicitly from the composition root.

    Example:
        ```python
        # Register middleware globally
        registry.register_middleware(retry_middleware)

        # Register middleware for specific event type
        registry.register_middleware_for_event_type("user.created", retry_middleware)
        ```
    """

    def register_middleware(self, middleware: Any) -> None:
        """
        Register middleware globally.

        Args:
            middleware: The middleware component to register

        Example:
            ```python
            # Register retry middleware globally
            registry.register_middleware(retry_middleware)
            ```
        """
        ...

    def register_middleware_for_event_type(
        self, event_type: str, middleware: Any
    ) -> None:
        """
        Register middleware for a specific event type.

        Args:
            event_type: The event type to register middleware for
            middleware: The middleware component to register

        Example:
            ```python
            # Register retry middleware for user.created events
            registry.register_middleware_for_event_type("user.created", retry_middleware)
            ```
        """
        ...
