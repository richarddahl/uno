# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import os
import sys
from pathlib import Path

# Ensure the src directory is on sys.path so local uno package is imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from uno.core.config import services
from uno.core.config.general import GeneralConfig
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider, get_service_provider


@pytest.fixture(scope="session", autouse=True)
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

    # Get the global provider and configure it
    provider = get_service_provider()
    provider._initialized = False  # Reset if it was previously initialized
    provider.configure_services(test_services)
    provider.configure_services(services)

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
