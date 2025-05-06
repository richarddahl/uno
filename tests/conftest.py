# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Performance/benchmark tests are only run if explicitly selected.
Add '-m performance' or '-m benchmark' to your pytest command to include them:
    hatch run test:testV -m performance
    hatch run test:testV -m benchmark
Otherwise, these tests will be skipped by default.

To mark a test as performance/benchmark, use @pytest.mark.performance or @pytest.mark.benchmark_only.
"""

import os
import sys
from pathlib import Path

# Ensure the src directory is on sys.path so local uno package is imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

import pytest
import asyncio
from uno.infrastructure.di.provider import configure_base_services

@pytest.fixture(scope="function", autouse=True)
async def uno_di_setup():
    services = ServiceCollection()
    provider = services.build_service_provider()
    await configure_base_services(provider)


from uno.infrastructure.config.general import GeneralConfig
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.di.service_collection import ServiceCollection

from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from typing import Any
import asyncio

class FakeLoggerService(LoggerService):
    def __init__(self, *args, **kwargs):
        super().__init__(LoggingConfig())
        self.structured_logs: list[dict[str, Any]] = []
        self.info_logs: list[str] = []
        self.warning_logs: list[str] = []
        self.error_logs: list[str] = []

    def structured_log(self, level: str, msg: str, *args: Any, **kwargs: Any) -> None:
        self.structured_logs.append({"level": level, "msg": msg, "args": args, "kwargs": kwargs})

    async def astructured_log(self, level: str, msg: str, *args: Any, **kwargs: Any) -> None:
        await asyncio.sleep(0)
        self.structured_log(level, msg, *args, **kwargs)

    def info(self, msg: str) -> None:
        self.info_logs.append(msg)
    async def ainfo(self, msg: str) -> None:
        await asyncio.sleep(0)
        self.info(msg)
    def warning(self, msg: str) -> None:
        self.warning_logs.append(msg)
    async def awarning(self, msg: str) -> None:
        await asyncio.sleep(0)
        self.warning(msg)
    def error(self, msg: str) -> None:
        self.error_logs.append(msg)
    async def aerror(self, msg: str) -> None:
        await asyncio.sleep(0)
        self.error(msg)


# Monkeypatch globally for DI tests
import uno.infrastructure.logging.logger as logger_module
logger_module.LoggerService = FakeLoggerService


from uno.core.services.hash_service_protocol import HashServiceProtocol
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from typing import Any


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance/benchmark (skip unless -m performance or -m benchmark)",
    )
    config.addinivalue_line(
        "markers",
        "benchmark_only: mark test as DI performance/benchmark (skip unless -m performance or -m benchmark)",
    )


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    m_option = config.getoption("-m")
    # Only run performance/benchmark tests if '-m performance' or '-m benchmark' is specified
    if not m_option or ("performance" not in m_option and "benchmark" not in m_option):
        skip_perf = pytest.mark.skip(
            reason="Skipped unless -m performance or -m benchmark is specified."
        )
        for item in items:
            if "performance" in item.keywords or "benchmark_only" in item.keywords:
                item.add_marker(skip_perf)


class FakeHashService(HashServiceProtocol):
    def compute_hash(self, payload: str) -> str:
        return "test-hash-123"


@pytest.fixture(scope="function", autouse=True)
async def initialize_di() -> None:
    """
    Initialize the dependency injection system for tests.

    This fixture ensures that all tests have access to a properly
    configured DI system with test-appropriate configuration values.
    It also forcibly resets the global DI provider to avoid recursion issues.
    """
    import uno.infrastructure.di.provider as di_provider_mod
    # Make sure we're in test environment
    os.environ["ENV"] = "test"

    # Forcibly reset the global provider before each test
    if hasattr(di_provider_mod, "_service_provider"):
        di_provider_mod._service_provider = None

    # Create a test config with required values
    config = GeneralConfig(SITE_NAME="Uno Test Site")

    # Create service collection
    services = ServiceCollection()
    services.add_instance(GeneralConfig, config)
    services.add_instance(HashServiceProtocol, FakeHashService())

    # Register database services with test configuration
    register_database_services(services, {
        "backend": "memory",
        "dsn": "sqlite+aiosqlite:///:memory:",
        "pool_size": 5
    })

    # Get the global provider and configure it
    # Create a new provider with test configuration
    provider = ServiceProvider(services)
    await provider.initialize()
    return provider


@pytest.fixture(scope="function")
async def test_services() -> ServiceCollection:
    """
    Create a fresh service collection for each test.
    """
    services = ServiceCollection()
    services.add_instance(GeneralConfig, GeneralConfig())
    services.add_instance(HashServiceProtocol, FakeHashService())
    return services


@pytest.fixture
def service_collection() -> ServiceCollection:
    """Provide a clean service collection for tests."""
    return ServiceCollection()


@pytest.fixture
def service_provider() -> ServiceProvider:
    """
    Provide a clean service provider for tests.

    This provider is not initialized yet. Use initialize_provider
    if you need an initialized provider.
    """
    services = ServiceCollection()
    services.add_instance(LoggingConfig, LoggingConfig())
    services.add_singleton(LoggerService, implementation=FakeLoggerService)
    provider = ServiceProvider(services)
    return provider


@pytest.fixture
def config_instance() -> GeneralConfig:
    """Provide a test config instance."""
    return GeneralConfig(SITE_NAME="Uno Test Site")
