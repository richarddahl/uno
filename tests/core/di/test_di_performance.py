"""
Performance benchmarks for Uno Dependency Injection (DI) system.
Uses pytest-benchmark if available, otherwise falls back to time.perf_counter.

Benchmarks:
- Singleton service resolution
- Scoped service resolution
- Transient service resolution
- LoggerService DI initialization
- Override/mocking overhead

**Performance/benchmark tests are only run if explicitly selected.**
Add '-m benchmark' to your pytest command to include them:
    hatch run test:testV -m benchmark
Otherwise, these tests will be skipped by default.
"""

import pytest
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider
from uno.core.logging.logger import LoggerService, LoggingConfig
from tests.core.di.di_helper import DIHelper
import time

from pytest_benchmark.fixture import BenchmarkFixture
from typing import Any, Awaitable


class DummySingleton:
    def __init__(self) -> None:
        pass


class DummyScoped:
    def __init__(self) -> None:
        pass


class DummyTransient:
    def __init__(self) -> None:
        pass


@pytest.mark.benchmark(group="di_singleton")
@pytest.mark.benchmark_only
@pytest.mark.asyncio
async def test_singleton_resolution_benchmark(benchmark: BenchmarkFixture) -> None:
    services = ServiceCollection()
    services.add_singleton(DummySingleton)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    await provider.initialize()

    async def resolve() -> Any:
        return provider.get_service(DummySingleton)

    result = await benchmark(resolve)
    assert result.is_success
    assert isinstance(result.value, DummySingleton)


@pytest.mark.benchmark(group="di_scoped")
@pytest.mark.benchmark_only
@pytest.mark.asyncio
async def test_scoped_resolution_benchmark(benchmark: BenchmarkFixture) -> None:
    services = ServiceCollection()
    services.add_scoped(DummyScoped)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    await provider.initialize()

    async def resolve() -> Any:
        async with await provider.create_scope() as scope:
            return scope.get_service(DummyScoped)

    result = await benchmark(resolve)
    assert result.is_success
    assert isinstance(result.value, DummyScoped)


@pytest.mark.benchmark(group="di_transient")
@pytest.mark.benchmark_only
@pytest.mark.asyncio
async def test_transient_resolution_benchmark(benchmark: BenchmarkFixture) -> None:
    services = ServiceCollection()
    services.add_transient(DummyTransient)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    await provider.initialize()

    async def resolve() -> Any:
        return provider.get_service(DummyTransient)

    result = await benchmark(resolve)
    assert result.is_success
    assert isinstance(result.value, DummyTransient)


@pytest.mark.benchmark(group="di_logger_init")
@pytest.mark.benchmark_only
@pytest.mark.asyncio
async def test_logger_service_initialization_benchmark(
    benchmark: BenchmarkFixture,
) -> None:
    async def create_logger() -> LoggerService:
        logger = LoggerService(LoggingConfig())
        await logger.initialize()
        return logger

    logger = await benchmark(create_logger)
    assert isinstance(logger, LoggerService)


@pytest.mark.benchmark(group="di_override")
@pytest.mark.benchmark_only
@pytest.mark.asyncio
async def test_di_override_benchmark(benchmark: BenchmarkFixture) -> None:
    provider = DIHelper.create_test_provider()

    class Dummy:
        pass

    dummy1 = Dummy()
    dummy2 = Dummy()
    DIHelper.register_mock(provider, Dummy, dummy1)

    async def override() -> None:
        with DIHelper.override_service(provider, Dummy, dummy2):
            assert Dummy in provider._base_services._instances
            assert provider._base_services._instances[Dummy] is dummy2
        assert Dummy in provider._base_services._instances
        assert provider._base_services._instances[Dummy] is dummy1

    await benchmark(override)


# Fallback: If pytest-benchmark not installed, provide a warning and skip tests
pytestmark = pytest.mark.tryfirst


def pytest_configure(config: Any) -> None:
    try:
        import pytest_benchmark
    except ImportError:
        pytest.skip("pytest-benchmark is required for DI performance benchmarks.")

    # Register custom marker for performance/benchmark tests
    config.addinivalue_line(
        "markers", "benchmark_only: mark test as DI performance/benchmark (skip unless -m benchmark)"
    )

def pytest_collection_modifyitems(config, items):
    # If '-m benchmark' is not in command line, skip all tests marked benchmark_only
    if not config.getoption("-m") or "benchmark" not in config.getoption("-m"):
        skip_benchmark = pytest.mark.skip(reason="Skipped unless -m benchmark is specified.")
        for item in items:
            if "benchmark_only" in item.keywords:
                item.add_marker(skip_benchmark)
