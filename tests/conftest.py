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

from uno.infrastructure.config.general import GeneralConfig
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.provider import ServiceProvider, get_service_provider
from uno.core.services.hash_service_protocol import HashServiceProtocol
from typing import Any


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance/benchmark (skip unless -m performance or -m benchmark)",
    )
    config.addinivalue_line(
        "markers",
        "benchmark_only: mark test as DI performance/benchmark (skip unless -m performance or -m benchmark)",
    )


def pytest_collection_modifyitems(config, items):
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
    def hash_event(self, event: Any) -> str:
        return "fakehash"


@pytest.fixture(scope="function", autouse=True)
def initialize_di():
    """
    Initialize the dependency injection system for tests.

    This fixture ensures that all tests have access to a properly
    configured DI system with test-appropriate configuration values.
    """
    # Make sure we're in test environment
    os.environ["ENV"] = "test"

    # Create a test config with required values
    config = GeneralConfig(SITE_NAME="Uno Test Site")

    # Create service collection
    test_services = ServiceCollection()
    test_services.add_instance(GeneralConfig, config)
    test_services.add_singleton(
        HashServiceProtocol, FakeHashService
    )  # Register fake hash service

    # Get the global provider and configure it
    provider = get_service_provider()
    provider._initialized = False  # Reset if it was previously initialized
    provider.configure_services(test_services)

    # Not calling initialize() here since it's async and pytest fixture can't be async
    # Tests that need initialized services should use initialize_provider fixture

    return provider


@pytest.fixture
def service_collection():
    """Provide a clean service collection for tests."""
    return ServiceCollection()


@pytest.fixture
def service_provider():
    """
    Provide a clean service provider for tests.

    This provider is not initialized yet. Use initialize_provider
    if you need an initialized provider.
    """
    provider = ServiceProvider()
    return provider


@pytest.fixture
def config_instance():
    """Provide a test config instance."""
    return GeneralConfig(SITE_NAME="Uno Test Site")
