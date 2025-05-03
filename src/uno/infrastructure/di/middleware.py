"""
Dependency injection extensions for event middleware.

This module provides extension methods for the Uno DI container
to easily register event middleware components.
"""

from typing import Any, Protocol

from uno.infrastructure.di.container import ServiceCollection
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


class MiddlewareRegistry(Protocol):
    """Protocol for middleware registration."""

    def register_middleware(self, middleware: Any) -> None:
        """Register middleware globally."""
        ...

    def register_middleware_for_event_type(
        self, event_type: str, middleware: Any
    ) -> None:
        """Register middleware for a specific event type."""
        ...


def add_event_middleware(services: ServiceCollection) -> ServiceCollection:
    """
    Add event middleware services to the DI container.

    This registers the middleware factory and default options for all
    standard middleware components.

    Args:
        services: The service collection to register with

    Returns:
        The updated service collection
    """
    return register_middleware_services(services)


class MiddlewareBuilder:
    """Builder for configuring and registering middleware components."""

    def __init__(self, services: ServiceCollection, registry: MiddlewareRegistry):
        """
        Initialize the middleware builder.

        Args:
            services: The service collection
            registry: The event handler registry
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
        """
        add_metrics_middleware(self.services, self.registry, options, event_types)
        return self


def configure_event_middleware(
    services: ServiceCollection,
    registry: MiddlewareRegistry,
    configuration_action: callable[[MiddlewareBuilder], Any] | None = None,
) -> None:
    """
    Configure event middleware using a builder pattern.

    Args:
        services: The service collection
        registry: The event handler registry
        configuration_action: Optional action to configure middleware
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
