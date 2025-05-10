"""
Factory for creating event handler middleware with proper logging integration.

This module provides factories for creating middleware instances with
standardized logging configuration using the LoggerProtocolFactory pattern.
"""

from typing import Any

from uno.events.middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)
from uno.logging.factory import LoggerProtocolFactory


class EventHandlerMiddlewareFactory:
    """Factory for creating event handler middleware with consistent logging."""

    def __init__(self, logger_factory: LoggerProtocolFactory):
        """
        Initialize the middleware factory.

        Args:
            logger_factory: Factory for creating logger services
        """
        self.logger_factory = logger_factory

    def create_retry_middleware(
        self,
        options: RetryOptions | None = None,
        component_name: str = "events.middleware.retry",
    ) -> RetryMiddleware:
        """
        Create a RetryMiddleware instance (strict DI: inject LoggerProtocol).

        Args:
            options: Optional retry options
            component_name: Component name for the logger
        Returns:
            Configured RetryMiddleware instance
        """
        return RetryMiddleware(
            logger=self.logger_factory.create(component_name), options=options
        )

    def create_circuit_breaker_middleware(
        self,
        event_types: list[str] | None = None,
        options: CircuitBreakerState | None = None,
        component_name: str = "events.middleware.circuit_breaker",
    ) -> CircuitBreakerMiddleware:
        """
        Create a CircuitBreakerMiddleware instance (strict DI: inject LoggerProtocol).

        Args:
            event_types: Optional list of event types to apply circuit breaking to
            options: Optional circuit breaker options
            component_name: Component name for the logger
        Returns:
            Configured CircuitBreakerMiddleware instance
        """
        return CircuitBreakerMiddleware(
            logger=self.logger_factory.create(component_name),
            event_types=event_types,
            options=options,
        )

    def create_metrics_middleware(
        self,
        report_interval_seconds: float = 60.0,
        component_name: str = "events.middleware.metrics",
    ) -> MetricsMiddleware:
        """
        Create a MetricsMiddleware instance (strict DI: inject LoggerProtocol).

        Args:
            report_interval_seconds: Interval in seconds to report metrics
            component_name: Component name for the logger
        Returns:
            Configured MetricsMiddleware instance
        """
        return MetricsMiddleware(
            logger=self.logger_factory.create(component_name),
            report_interval_seconds=report_interval_seconds,
        )

    def create_default_middleware_stack(
        self,
        retry_options: RetryOptions | None = None,
        circuit_breaker_options: CircuitBreakerState | None = None,
        metrics_interval_seconds: float = 60.0,
    ) -> list[MetricsMiddleware | CircuitBreakerMiddleware | RetryMiddleware]:
        """
        Create a default stack of middleware in the recommended order.

        The recommended order is:
        1. Metrics (outermost - measures everything)
        2. Circuit Breaker (prevents cascading failures)
        3. Retry (retries failed operations)

        Args:
            retry_options: Optional retry options
            circuit_breaker_options: Optional circuit breaker options
            metrics_interval_seconds: Interval for metrics reporting

        Returns:
            List of middleware instances in the recommended order
        """
        return [
            self.create_metrics_middleware(
                report_interval_seconds=metrics_interval_seconds
            ),
            self.create_circuit_breaker_middleware(options=circuit_breaker_options),
            self.create_retry_middleware(options=retry_options),
        ]


def create_middleware_factory(
    logger_factory: LoggerProtocolFactory,
) -> EventHandlerMiddlewareFactory:
    """
    Create a middleware factory with the given logger factory.

    Args:
        logger_factory: Factory for creating logger services

    Returns:
        Configured EventHandlerMiddlewareFactory instance
    """
    return EventHandlerMiddlewareFactory(logger_factory=logger_factory)


def register_middleware(
    registry: Any,
    middleware_factory: EventHandlerMiddlewareFactory,
    retry_options: RetryOptions | None = None,
    circuit_breaker_options: CircuitBreakerState | None = None,
    metrics_interval_seconds: float = 60.0,
) -> None:
    """
    Register middleware with a registry.

    Args:
        registry: Registry to register middleware with
        middleware_factory: Factory for creating middleware
        retry_options: Optional retry options
        circuit_breaker_options: Optional circuit breaker options
        metrics_interval_seconds: Interval for metrics reporting

    Raises:
        Exception: If middleware registration fails
    """
    try:
        middleware_stack = middleware_factory.create_default_middleware_stack(
            retry_options=retry_options,
            circuit_breaker_options=circuit_breaker_options,
            metrics_interval_seconds=metrics_interval_seconds,
        )

        for middleware in middleware_stack:
            registry.register_middleware(middleware)

    except Exception as e:
        raise e
