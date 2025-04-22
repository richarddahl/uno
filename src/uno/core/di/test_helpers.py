# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Test helpers for dependency injection.

This module provides utilities for setting up and configuring the DI system
in test environments, with proper isolation and cleanup.
"""

import os
from typing import Any, Optional

from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider, get_service_provider
from uno.config.general import GeneralConfig


class TestDI:
    """Helper class for managing DI in tests."""

    @staticmethod
    def create_test_provider() -> ServiceProvider:
        """
        Create a clean service provider for testing.

        This method returns a new service provider with a clean state,
        suitable for isolated testing.

        Returns:
            A fresh service provider instance
        """
        # Temporarily override the singleton
        global _service_provider
        old_provider = _service_provider
        _service_provider = None

        # Create a new provider
        provider = get_service_provider()
        provider._initialized = False
        provider._lifecycle_queue.clear()
        provider._extensions.clear()
        provider._base_services = ServiceCollection()

        # Restore the global provider when tests are done
        _service_provider = old_provider

        return provider

    @staticmethod
    def initialize_test_provider(
        provider: Optional[ServiceProvider] = None,
        site_name: str = "Uno Test Site",
        env: str = "test",
    ) -> ServiceProvider:
        """
        Initialize a service provider for testing.

        This method sets up a properly configured service provider with
        test-appropriate configuration values.

        Args:
            provider: Optional provider to initialize (creates a new one if None)
            site_name: Site name to use for GeneralConfig
            env: Environment to use

        Returns:
            The initialized service provider
        """
        # Set the environment
        os.environ["ENV"] = env

        # Get or create the provider
        provider = provider or TestDI.create_test_provider()

        # Create a basic service collection with required configs
        services = ServiceCollection()

        # Add a test GeneralConfig
        services.add_instance(GeneralConfig, GeneralConfig(SITE_NAME=site_name))

        # Configure the provider
        provider.configure_services(services)
        return provider

    @staticmethod
    async def setup_test_services(
        provider: Optional[ServiceProvider] = None,
        additional_services: Optional[ServiceCollection] = None,
    ) -> ServiceProvider:
        """
        Set up test services and initialize the provider.

        This is a convenience method that combines creation, configuration,
        and initialization of a test service provider.

        Args:
            provider: Optional provider to use (creates a new one if None)
            additional_services: Optional additional services to register

        Returns:
            The initialized service provider
        """
        # Initialize the provider
        provider = TestDI.initialize_test_provider(provider)

        # Add additional services if provided
        if additional_services:
            provider.configure_services(additional_services)

        # Initialize the provider
        await provider.initialize()

        return provider
