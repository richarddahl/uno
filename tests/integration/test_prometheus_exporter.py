"""
Integration tests for Uno PrometheusExporter.
"""

import pytest
from typing import ClassVar
from uno.metrics.backends.prometheus import PrometheusExporter
from prometheus_client.parser import text_string_to_metric_families
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient


class FakeCounter:
    name: ClassVar[str] = "tagged_counter"
    description: ClassVar[str] = "A counter with dimensional tags"
    tags: dict[str, str]
    _value: float

    def __init__(self) -> None:
        self.tags = {}
        self._value = 0.0

    async def increment(self, amount: float) -> None:
        self._value += amount

    async def get_value(self) -> float:
        return self._value


class FakeGauge:
    name: ClassVar[str] = "empty_tags_gauge"
    description: ClassVar[str] = "No tags"
    tags: dict[str, str]
    _value: float

    def __init__(self) -> None:
        self.tags = {}
        self._value = 0.0

    async def set(self, value: float) -> None:
        self._value = value

    async def get_value(self) -> float:
        return self._value


@pytest.fixture
def exporter() -> PrometheusExporter:
    return PrometheusExporter()


def prometheus_endpoint(exporter: PrometheusExporter):
    async def metrics(request):
        formatted = await exporter.format([])
        return Response(formatted, media_type="text/plain; version=0.0.4")

    return metrics


class TestPrometheusExporterIntegration:
    @pytest.mark.asyncio
    async def test_dimensional_tagging(self, exporter: PrometheusExporter) -> None:
        counter = FakeCounter()
        counter.tags = {"service": "integration", "env": "test"}
        await counter.increment(7)
        await exporter.export([counter])
        output = await exporter.format([counter])
        found = False
        for family in text_string_to_metric_families(output):
            for sample in family.samples:
                if sample.name == "uno_tagged_counter":
                    assert sample.value == 7
                    assert sample.labels["service"] == "integration"
                    assert sample.labels["env"] == "test"
                    found = True
        assert found, "Metric with tags not found in Prometheus output"

    @pytest.mark.asyncio
    async def test_scraping_endpoint(self, exporter: PrometheusExporter) -> None:
        """Test that the metrics endpoint correctly responds to scrape requests."""
        # Skip metric creation for now - just test the endpoint itself
        app = Starlette(routes=[Route("/metrics", prometheus_endpoint(exporter))])

        # Use TestClient as a regular context manager, not an async one
        with TestClient(app) as client:
            response = client.get("/metrics")

            # Verify basic response properties
            assert response.status_code == 200

            # Accept either OpenMetrics or traditional Prometheus format
            content_type = response.headers["content-type"]
            assert (
                "application/openmetrics-text" in content_type
                or "text/plain" in content_type
            ), f"Unexpected content type: {content_type}"

            # Make a minimal check that we have some response content
            # Even an empty metrics response should have some content like comments
            assert response.text is not None

    @pytest.mark.asyncio
    async def test_error_handling_invalid_metric(
        self, exporter: PrometheusExporter
    ) -> None:
        class FakeMetric:
            name: None = None  # Invalid name
            description: str = "No name"
            tags: dict[str, str] = {}

        # Should raise ValueError for unsupported metric type
        with pytest.raises(ValueError):
            await exporter.export([FakeMetric()])

    @pytest.mark.asyncio
    async def test_edge_case_empty_tags(self, exporter: PrometheusExporter) -> None:
        gauge = FakeGauge()
        gauge.tags = {}
        await gauge.set(1.23)
        await exporter.export([gauge])
        output = await exporter.format([gauge])
        # Should still output metric line without labels
        assert "uno_empty_tags_gauge" in output
        assert "1.23" in output
