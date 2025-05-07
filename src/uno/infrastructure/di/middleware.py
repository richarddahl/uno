"""
Dependency injection extensions for event middleware.

This module provides extension methods for the Uno DI container
to easily register event middleware components.

Note: All dependencies must be passed explicitly from the composition root.
"""

from typing import Any, TypeVar, Callable

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.interfaces import MiddlewareRegistry
from uno.core.events.middleware import (
    CircuitBreakerOptions,
    MetricsOptions,
    RetryOptions,
)
from uno.core.events.middleware_di import (
    add_circuit_breaker_middleware,
    add_metrics_middleware,
    add_retry_middleware,
    register_middleware_services,
    register_standard_middleware,
)
from uno.core.events.middleware_factory import EventHandlerMiddlewareFactory

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])

def add_event_middleware(services: ServiceCollection) -> ServiceCollection:
    """
    Add event middleware services to the DI container.

    This registers the middleware factory and default options for all
    standard middleware components.

    Args:
        services: The service collection to register with

    Returns:
        The updated service collection

    Example:
        ```python
        # Add event middleware services
        services = add_event_middleware(services)
        ```
    """
    return register_middleware_services(services)


class MiddlewareBuilder:
    """
    Builder for configuring and registering middleware components.

    This class provides a fluent interface for configuring and registering
    middleware components with the event system.

    Note: All dependencies must be passed explicitly from the composition root.

    Example:
        ```python
        # Configure middleware using builder
        builder = MiddlewareBuilder(services, registry)
        builder.add_standard_middleware()  # Add all standard middleware
        builder.add_retry()  # Add retry middleware
        builder.add_circuit_breaker()  # Add circuit breaker middleware
        builder.add_metrics()  # Add metrics middleware
        ```
    """

    def __init__(self, services: ServiceCollection, registry: MiddlewareRegistry):
        """
        Initialize the middleware builder.

        Args:
            services: The service collection
            registry: The event handler registry

        Example:
            ```python
            # Create middleware builder
            builder = MiddlewareBuilder(services, registry)
            ```
        """
        self.services = services
        self.registry = registry

    def add_standard_middleware(
        self, event_types: list[str] | None = None
    ) -> "MiddlewareBuilder":
        """
        Add all standard middleware components.

        Args:
            event_types: Optional list of event types to register middleware for

        Returns:
            The builder instance for chaining

        Example:
            ```python
            # Add standard middleware for all events
            builder.add_standard_middleware()

            # Add standard middleware for specific events
            builder.add_standard_middleware(["user.created", "user.updated"])
            ```
        """
        register_standard_middleware(self.services, self.registry, event_types)
        return self

    def add_retry(
        self, options: RetryOptions | None = None, event_types: list[str] | None = None
    ) -> "MiddlewareBuilder":
        """
        Add retry middleware.

        Args:
            options: Optional custom retry options
            event_types: Optional list of event types to register middleware for

        Returns:
            The builder instance for chaining

        Example:
            ```python
            # Add retry middleware with default options
            builder.add_retry()

            # Add retry middleware with custom options
            options = RetryOptions(max_retries=5, base_delay_ms=200)
            builder.add_retry(options)

            # Add retry middleware for specific events
            builder.add_retry(event_types=["user.created"])
            ```
        """
        add_retry_middleware(self.services, self.registry, options, event_types)
        return self

    def add_circuit_breaker(
        self,
        options: CircuitBreakerOptions | None = None,
        event_types: list[str] | None = None,
    ) -> "MiddlewareBuilder":
        """
        Add circuit breaker middleware.

        Args:
            options: Optional custom circuit breaker options
            event_types: Optional list of event types to register middleware for

        Returns:
            The builder instance for chaining

        Example:
            ```python
            # Add circuit breaker middleware with default options
            builder.add_circuit_breaker()

            # Add circuit breaker middleware with custom options
            options = CircuitBreakerOptions(failure_threshold=3)
            builder.add_circuit_breaker(options)

            # Add circuit breaker middleware for specific events
            builder.add_circuit_breaker(event_types=["user.created"])
            ```
        """
        add_circuit_breaker_middleware(
            self.services, self.registry, options, event_types
        )
        return self

    def add_metrics(
        self,
        options: MetricsOptions | None = None,
        event_types: list[str] | None = None,
    ) -> "MiddlewareBuilder":
        """
        Add metrics middleware.

        Args:
            options: Optional custom metrics options
            event_types: Optional list of event types to register middleware for

        Returns:
            The builder instance for chaining

        Example:
            ```python
            # Add metrics middleware with default options
            builder.add_metrics()

            # Add metrics middleware with custom options
            options = MetricsOptions(report_interval_seconds=30)
            builder.add_metrics(options)

            # Add metrics middleware for specific events
            builder.add_metrics(event_types=["user.created"])
            ```
        """
        add_metrics_middleware(self.services, self.registry, options, event_types)
        return self


def configure_event_middleware(
    services: ServiceCollection,
    registry: MiddlewareRegistry,
    configuration_action: Callable[[MiddlewareBuilder], Any] | None = None,
) -> None:
    """
    Configure event middleware using a builder pattern.

    Args:
        services: The service collection
        registry: The event handler registry
        configuration_action: Optional action to configure middleware

    Example:
        ```python
        # Configure middleware with default settings
        configure_event_middleware(services, registry)

        # Configure middleware with custom settings
        def configure(builder):
            builder.add_retry()
            builder.add_circuit_breaker()
            builder.add_metrics()

        configure_event_middleware(services, registry, configure)
        ```
    """
    # Register middleware services if not already registered
    middleware_factory = services.try_get_service(EventHandlerMiddlewareFactory)
    if middleware_factory is None:
        register_middleware_services(services)

    # Create builder
    builder = MiddlewareBuilder(services, registry)

    # Apply configuration action if provided
    if configuration_action:
        configuration_action(builder)
