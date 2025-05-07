"""
Dependency injection integration for event handler middleware.

This module provides extension methods and helpers for registering middleware
components in the DI container, avoiding circular imports between the event system
and the DI system.

Note: All dependencies must be passed explicitly from the composition root.
"""

from typing import Any, TypeVar, Callable, cast

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.interfaces import MiddlewareRegistry
from uno.core.events.middleware import (
    CircuitBreakerOptions,
    MetricsOptions,
    RetryOptions,
)
from uno.core.events.middleware_factory import EventHandlerMiddlewareFactory
from uno.infrastructure.logging.factory import LoggerServiceFactory

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])


def register_middleware_services(services: ServiceCollection) -> ServiceCollection:
    """
    Register middleware services with the DI container.

    This registers the middleware factory and default options for all
    standard middleware components.

    Args:
        services: The service collection to register with

    Returns:
        The updated service collection

    Example:
        ```python
        # Register middleware services
        services = register_middleware_services(services)
        ```
    """
    # Register middleware factory
    services.add_singleton(
        EventHandlerMiddlewareFactory,
        implementation=EventHandlerMiddlewareFactory,
        logger_factory=LoggerServiceFactory(),
    )

    # Register default retry middleware options
    services.add_singleton(
        RetryOptions,
        implementation=RetryOptions,
        max_retries=3,
        base_delay_ms=100,
        backoff_factor=2.0,
    )

    # Register default circuit breaker middleware options
    services.add_singleton(
        CircuitBreakerOptions,
        implementation=CircuitBreakerOptions,
        failure_threshold=5,
        reset_timeout_seconds=30,
        half_open_success_threshold=1,
    )

    # Register default metrics middleware options
    services.add_singleton(
        MetricsOptions, implementation=MetricsOptions, report_interval_seconds=60
    )

    return services


def register_standard_middleware(
    services: ServiceCollection,
    registry: MiddlewareRegistry,
    event_types: list[str] | None = None,
) -> None:
    """
    Register standard middleware with the event system.

    This registers all standard middleware components (retry, circuit breaker,
    and metrics) either globally or for specific event types.

    Args:
        services: The service collection
        registry: The event handler registry
        event_types: Optional list of event types to register middleware for

    Example:
        ```python
        # Register standard middleware globally
        register_standard_middleware(services, registry)

        # Register standard middleware for specific events
        register_standard_middleware(
            services,
            registry,
            event_types=["user.created", "user.updated"]
        )
        ```
    """
    # Get the middleware factory
    factory = cast(
        "EventHandlerMiddlewareFactory",
        services.get_service(EventHandlerMiddlewareFactory),
    )

    # Create middleware
    retry_middleware = factory.create_retry_middleware()
    circuit_breaker_middleware = factory.create_circuit_breaker_middleware()
    metrics_middleware = factory.create_metrics_middleware()

    # Register middleware based on event_types
    if event_types:
        for event_type in event_types:
            registry.register_middleware_for_event_type(event_type, retry_middleware)
            registry.register_middleware_for_event_type(
                event_type, circuit_breaker_middleware
            )
            registry.register_middleware_for_event_type(event_type, metrics_middleware)
    else:
        # Register globally
        registry.register_middleware(retry_middleware)
        registry.register_middleware(circuit_breaker_middleware)
        registry.register_middleware(metrics_middleware)


def add_retry_middleware(
    services: ServiceCollection,
    registry: MiddlewareRegistry,
    options: RetryOptions | None = None,
    event_types: list[str] | None = None,
) -> None:
    """
    Add retry middleware to the event system.

    Args:
        services: The service collection
        registry: The event handler registry
        options: Optional custom retry options
        event_types: Optional list of event types to register middleware for

    Example:
        ```python
        # Add retry middleware with default options
        add_retry_middleware(services, registry)

        # Add retry middleware with custom options
        options = RetryOptions(max_retries=5, base_delay_ms=200)
        add_retry_middleware(services, registry, options)

        # Add retry middleware for specific events
        add_retry_middleware(
            services,
            registry,
            event_types=["user.created"]
        )
        ```
    """
    factory = cast(
        "EventHandlerMiddlewareFactory",
        services.get_service(EventHandlerMiddlewareFactory),
    )

    # Create retry middleware with custom options if provided
    middleware = factory.create_retry_middleware(options)

    # Register middleware based on event_types
    if event_types:
        for event_type in event_types:
            registry.register_middleware_for_event_type(event_type, middleware)
    else:
        # Register globally
        registry.register_middleware(middleware)


def add_circuit_breaker_middleware(
    services: ServiceCollection,
    registry: MiddlewareRegistry,
    options: CircuitBreakerOptions | None = None,
    event_types: list[str] | None = None,
) -> None:
    """
    Add circuit breaker middleware to the event system.

    Args:
        services: The service collection
        registry: The event handler registry
        options: Optional custom circuit breaker options
        event_types: Optional list of event types to register middleware for

    Example:
        ```python
        # Add circuit breaker middleware with default options
        add_circuit_breaker_middleware(services, registry)

        # Add circuit breaker middleware with custom options
        options = CircuitBreakerOptions(failure_threshold=3)
        add_circuit_breaker_middleware(services, registry, options)

        # Add circuit breaker middleware for specific events
        add_circuit_breaker_middleware(
            services,
            registry,
            event_types=["user.created"]
        )
        ```
    """
    factory = cast(
        "EventHandlerMiddlewareFactory",
        services.get_service(EventHandlerMiddlewareFactory),
    )

    # Create circuit breaker middleware with custom options if provided
    middleware = factory.create_circuit_breaker_middleware(options)

    # Register middleware based on event_types
    if event_types:
        for event_type in event_types:
            registry.register_middleware_for_event_type(event_type, middleware)
    else:
        # Register globally
        registry.register_middleware(middleware)


def add_metrics_middleware(
    services: ServiceCollection,
    registry: MiddlewareRegistry,
    options: MetricsOptions | None = None,
    event_types: list[str] | None = None,
) -> None:
    """
    Add metrics middleware to the event system.

    Args:
        services: The service collection
        registry: The event handler registry
        options: Optional custom metrics options
        event_types: Optional list of event types to register middleware for

    Example:
        ```python
        # Add metrics middleware with default options
        add_metrics_middleware(services, registry)

        # Add metrics middleware with custom options
        options = MetricsOptions(report_interval_seconds=30)
        add_metrics_middleware(services, registry, options)

        # Add metrics middleware for specific events
        add_metrics_middleware(
            services,
            registry,
            event_types=["user.created"]
        )
        ```
    """
    factory = cast(
        "EventHandlerMiddlewareFactory",
        services.get_service(EventHandlerMiddlewareFactory),
    )

    # Create metrics middleware with custom options if provided
    middleware = factory.create_metrics_middleware(options)

    # Register middleware based on event_types
    if event_types:
        for event_type in event_types:
            registry.register_middleware_for_event_type(event_type, middleware)
    else:
        # Register globally
        registry.register_middleware(middleware)
