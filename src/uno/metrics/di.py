from __future__ import annotations

import asyncio
from typing import Any

from ..core.di import Container
from .collector import AsyncMetricReporter
from .registry import MetricRegistry


class MetricsRegistrationExtensions:
    """Extension methods for registering metrics components in the DI container."""

    @staticmethod
    def register_metrics(container: Container) -> None:
        """Register metrics components in the DI container.

        Args:
            container: DI container to register components in
        """
        # Register metric registry as singleton
        container.register_singleton(MetricRegistry)

        # Register async metric reporter
        container.register_singleton(
            AsyncMetricReporter,
            lambda: AsyncMetricReporter(interval=1.0),
        )

    @staticmethod
    def register_metric_backend(
        container: Container,
        backend: Any,  # Replace with actual backend type
    ) -> None:
        """Register a metric backend in the DI container.

        Args:
            container: DI container to register backend in
            backend: Metric backend instance
        """
        # Get the async reporter
        reporter = container.resolve(AsyncMetricReporter)
        
        # Add the backend to the reporter
        asyncio.create_task(reporter.add_backend(backend))

    @staticmethod
    def register_metric(
        container: Container,
        name: str,
        metric_type: type[Any],  # Replace with actual metric type
        **kwargs: Any,
    ) -> Any:  # Replace with actual metric type
        """Register a metric in the DI container.

        Args:
            container: DI container to register metric in
            name: Name of the metric
            metric_type: Type of the metric to create
            **kwargs: Additional arguments for metric creation

        Returns:
            The created metric instance
        """
        # Get the metric registry
        registry = container.resolve(MetricRegistry)
        
        # Create the metric
        metric = metric_type(name=name, **kwargs)
        
        # Register the metric
        registry.register(name, metric)
        
        return metric
