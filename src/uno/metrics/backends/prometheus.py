"""
Prometheus backend for metrics reporting.
"""

from __future__ import annotations

from typing import Any, Callable

from prometheus_client import REGISTRY, CollectorRegistry, generate_latest
from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge as PrometheusGauge
from prometheus_client import Histogram as PrometheusHistogram
from prometheus_client import Summary as PrometheusSummary
from starlette.requests import Request
from starlette.responses import Response

from uno.metrics.protocols import MetricProtocol


class PrometheusExporter:
    """Exporter for Prometheus metrics."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize the Prometheus exporter.

        Args:
            registry: Optional custom Prometheus registry to use
        """
        self._metrics = {}
        self._registry = registry or REGISTRY

    async def export(self, metrics: list[MetricProtocol]) -> str:
        """Export metrics in Prometheus format.

        Args:
            metrics: List of metrics to export

        Returns:
            Prometheus formatted metrics

        Raises:
            ValueError: If an invalid metric is provided
        """
        for metric in metrics:
            await self._register_metric(metric)

        return await self.format(metrics)

    async def _register_metric(self, metric: MetricProtocol) -> None:
        """Register a metric with Prometheus.

        Args:
            metric: The metric to register

        Raises:
            ValueError: If the metric is invalid or unsupported
        """
        # Validate metric before proceeding
        self._validate_metric(metric)

        metric_name = f"uno_{metric.name}"

        if metric_name in self._metrics:
            # Metric already registered
            return

        metric_value = await metric.get_value()

        # Get tags for label handling
        labels = {}
        if hasattr(metric, "tags") and metric.tags:
            labels = metric.tags

        # Determine metric type based on the value and name
        if (
            isinstance(metric_value, dict)
            and "min" in metric_value
            and "max" in metric_value
        ):
            # Timer or histogram
            if hasattr(metric, "record") or "timer" in metric.name.lower():
                # Create a summary for timer metrics
                summary = PrometheusSummary(
                    metric_name,
                    getattr(metric, "description", ""),
                    labelnames=list(labels.keys()) if labels else [],
                )
                self._metrics[metric_name] = summary

                # Record values using observe with proper label handling
                count = metric_value.get("count", 0)
                if count > 0:
                    # If we have a mean value, observe it once for each count
                    mean = metric_value.get("mean", 0)

                    # Use labels if we have them
                    if labels:
                        labeled_summary = summary.labels(**labels)
                        for _ in range(count):
                            labeled_summary.observe(mean)
                    else:
                        for _ in range(count):
                            summary.observe(mean)
            else:
                # Create a histogram for histogram metrics
                buckets = getattr(
                    metric,
                    "buckets",
                    [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                )
                histogram = PrometheusHistogram(
                    metric_name,
                    getattr(metric, "description", ""),
                    labelnames=list(labels.keys()) if labels else [],
                    buckets=buckets,
                )
                self._metrics[metric_name] = histogram

                # Record observations with proper label handling
                count = metric_value.get("count", 0)
                if count > 0:
                    mean = metric_value.get("mean", 0)

                    # Use labels if we have them
                    if labels:
                        labeled_histogram = histogram.labels(**labels)
                        for _ in range(count):
                            labeled_histogram.observe(mean)
                    else:
                        for _ in range(count):
                            histogram.observe(mean)
        elif hasattr(metric, "inc") and hasattr(metric, "dec"):
            # Counter
            counter = PrometheusCounter(
                metric_name,
                getattr(metric, "description", ""),
                labelnames=list(labels.keys()) if labels else [],
            )
            self._metrics[metric_name] = counter

            # Set initial value with proper label handling
            if labels:
                counter.labels(**labels).inc(float(metric_value))
            else:
                counter.inc(float(metric_value))
        else:
            # Gauge (default)
            gauge = PrometheusGauge(
                metric_name,
                getattr(metric, "description", ""),
                labelnames=list(labels.keys()) if labels else [],
            )
            self._metrics[metric_name] = gauge

            # Set initial value with proper label handling
            if labels:
                gauge.labels(**labels).set(float(metric_value))
            else:
                gauge.set(float(metric_value))

    def _validate_metric(self, metric: Any) -> None:
        """Validate that a metric meets the requirements.

        Args:
            metric: The metric to validate

        Raises:
            ValueError: If the metric is invalid
        """
        # Check for required attributes and methods
        if not hasattr(metric, "name") or metric.name is None:
            raise ValueError(f"Invalid metric: missing or None name attribute")

        if not hasattr(metric, "get_value"):
            raise ValueError(f"Invalid metric: missing get_value method")

        # Check that get_value is callable
        if not callable(getattr(metric, "get_value", None)):
            raise ValueError(f"Invalid metric: get_value is not a method")

        # Additional validation can be added as needed

    async def format(self, metrics: list[MetricProtocol]) -> str:
        """Format metrics in Prometheus format.

        Args:
            metrics: List of metrics to format

        Returns:
            Prometheus formatted metrics
        """
        formatted_lines = []

        for metric in metrics:
            metric_name = f"uno_{metric.name}"
            # Create tags string
            tags_str = ""
            if hasattr(metric, "tags") and metric.tags:
                tags_list = [f'{k}="{v}"' for k, v in metric.tags.items()]
                tags_str = "{" + ",".join(tags_list) + "}"

            # Get metric value and format appropriately
            value = await metric.get_value()

            if isinstance(value, dict):
                # Handle complex metrics (histograms and timers)
                if "count" in value:
                    formatted_lines.append(
                        f"# HELP {metric_name} {getattr(metric, 'description', '')}"
                    )
                    formatted_lines.append(f"# TYPE {metric_name} histogram")
                    formatted_lines.append(
                        f"{metric_name}_count{tags_str} {value['count']}"
                    )
                    if "sum" in value:
                        formatted_lines.append(
                            f"{metric_name}_sum{tags_str} {value['sum']}"
                        )
                    else:
                        # If sum not provided, estimate from mean * count
                        mean = value.get("mean", 0)
                        count = value.get("count", 0)
                        sum_value = mean * count
                        formatted_lines.append(
                            f"{metric_name}_sum{tags_str} {sum_value}"
                        )

                    # Add bucket information if available
                    for k, v in value.items():
                        if k.startswith("le_"):
                            bucket = k[3:]  # Remove 'le_' prefix
                            formatted_lines.append(
                                f'{metric_name}_bucket{tags_str}{{le="{bucket}"}} {v}'
                            )
            else:
                # Handle simple metrics (counters and gauges)
                formatted_lines.append(
                    f"# HELP {metric_name} {getattr(metric, 'description', '')}"
                )
                if hasattr(metric, "inc") and hasattr(metric, "dec"):
                    formatted_lines.append(f"# TYPE {metric_name} counter")
                else:
                    formatted_lines.append(f"# TYPE {metric_name} gauge")
                formatted_lines.append(f"{metric_name}{tags_str} {value}")

        return "\n".join(formatted_lines)

    async def get_latest(self) -> str:
        """Get the latest metrics in Prometheus format.

        Returns:
            The latest metrics in Prometheus format
        """
        # Always include all metrics registered via this exporter
        custom_metrics_output = await self.format(list(self._metrics.values()))

        # Also include metrics from the Prometheus registry (if any)
        prometheus_output = generate_latest(self._registry).decode("utf-8")
        if prometheus_output.strip():
            if custom_metrics_output.strip():
                return custom_metrics_output + "\n" + prometheus_output
            return prometheus_output

        # If no registry metrics, return our custom metrics (may be empty)
        return custom_metrics_output or "# No metrics available\n"

    async def generate_latest(self) -> str:
        """Generate the latest metrics in Prometheus format.

        Returns:
            String containing all metrics in Prometheus format
        """
        # Format all registered metrics
        metrics_list = list(self._metrics.values())

        # If no metrics are in our registry yet, just return empty string
        if not metrics_list:
            return ""

        # Use the format method to generate the output
        return await self.format(metrics_list)


def prometheus_endpoint(exporter: PrometheusExporter) -> Callable[[Request], Response]:
    """Create a Starlette endpoint that exposes Prometheus metrics.

    Args:
        exporter: The Prometheus exporter to expose

    Returns:
        An async handler function for Starlette routes
    """

    async def endpoint(request: Request) -> Response:
        """Handle HTTP requests for Prometheus metrics.

        Args:
            request: The incoming HTTP request

        Returns:
            HTTP response with Prometheus metrics in text format
        """
        # Get metrics from the exporter
        content = await exporter.get_latest()

        return Response(
            content=content,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return endpoint
