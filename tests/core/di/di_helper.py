# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
tests.core.di.di_helper

Provides utilities for setting up and configuring the Uno Dependency Injection system in test environments.
Includes helpers for creating isolated ServiceProvider instances, configuring test services, and ensuring test isolation.

This module provides utilities for setting up and configuring the DI system
in test environments, with proper isolation and cleanup.
"""

import contextlib
import os

from uno.core.config.general import GeneralConfig
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider


class DIHelper:
    """
    Helper class for managing DI in tests.

    Provides utilities for test isolation, temporary service overrides (sync & async),
    registering mocks/doubles in a test context, and pytest fixtures for DI setup.

    Best Practices:
    - Use `DIHelper.create_test_provider()` or the `di_provider` fixture for isolated providers.
    - Use `DIHelper.override_service` or `DIHelper.async_override_service` for temporary service overrides.
    - Use `DIHelper.register_mock` to inject mocks/doubles.
    - Always reset DI state between tests with `DIHelper.reset_di_state()` or the fixture.

    Additional Utilities:
    - `DIHelper.batch_override_services`: Context manager to override multiple services at once.
    - `DIHelper.di_provider_fixture`: Pytest fixture for isolated providers.
    - `DIHelper.teardown_provider`: Helper for provider teardown/cleanup.
    """

    @staticmethod
    def create_test_provider() -> ServiceProvider:
        """
        Create a clean, isolated ServiceProvider for testing.
        """
        return ServiceProvider()

    @staticmethod
    def initialize_test_provider(
        provider: ServiceProvider | None = None,
        site_name: str = "Uno Test Site",
        env: str = "test",
    ) -> ServiceProvider:
        """
        Initialize a service provider for testing.
        Args:
            provider (ServiceProvider | None): Optional provider to initialize (creates a new one if None)
            site_name (str): Site name to use for GeneralConfig
            env (str): Environment to use
        Returns:
            ServiceProvider: The initialized service provider
        """
        os.environ["ENV"] = env
        provider = provider if provider is not None else DIHelper.create_test_provider()
        services = ServiceCollection()
        services.add_instance(GeneralConfig, GeneralConfig(SITE_NAME=site_name))
        provider.configure_services(services)
        return provider

    @staticmethod
    @contextlib.contextmanager
    def override_service(provider: ServiceProvider, service_type: type, mock_instance: object):
        """
        Temporarily override a service in the provider with a mock/double (sync context manager).
        """
        original = provider._base_services._instances.get(service_type, None)
        provider._base_services._instances[service_type] = mock_instance
        try:
            yield
        finally:
            if original is not None:
                provider._base_services._instances[service_type] = original
            else:
                provider._base_services._instances.pop(service_type, None)

    @staticmethod
    @contextlib.asynccontextmanager
    async def async_override_service(provider: ServiceProvider, service_type: type, mock_instance: object):
        """
        Temporarily override a service in the provider with a mock/double (async context manager).
        """
        original = provider._base_services._instances.get(service_type, None)
        provider._base_services._instances[service_type] = mock_instance
        try:
            yield
        finally:
            if original is not None:
                provider._base_services._instances[service_type] = original
            else:
                provider._base_services._instances.pop(service_type, None)

    @staticmethod
    @contextlib.contextmanager
    def batch_override_services(provider: ServiceProvider, overrides: dict[type, object]):
        """
        Context manager to override multiple services at once.
        """
        originals = {k: provider._base_services._instances.get(k, None) for k in overrides}
        provider._base_services._instances.update(overrides)
        try:
            yield
        finally:
            for k, v in originals.items():
                if v is not None:
                    provider._base_services._instances[k] = v
                else:
                    provider._base_services._instances.pop(k, None)

    @staticmethod
    def register_mock(provider: ServiceProvider, service_type: type, mock_instance: object) -> None:
        """
        Register a mock/double for a service type in the provider.
        """
        provider._base_services._instances[service_type] = mock_instance

    @staticmethod
    def reset_di_state() -> None:
        """
        Reset any global or static DI state between tests.
        """
        # This is a placeholder for global resets if needed.
        pass

    @staticmethod
    async def setup_test_services() -> ServiceProvider:
        """
        Async helper to set up a test ServiceProvider with default test services.
        """
        provider = DIHelper.create_test_provider()
        await provider.initialize()
        return provider

    @staticmethod
    def teardown_provider(provider: ServiceProvider) -> None:
        """
        Helper for provider teardown/cleanup.
        """
        provider._initialized = False
        provider._lifecycle_queue.clear()
        provider._extensions.clear()
        provider._base_services = ServiceCollection()

    """
    Helper class for managing DI in tests.

    Provides utilities for test isolation, temporary service overrides (sync & async),
    registering mocks/doubles in a test context, and pytest fixtures for DI setup.

    Best Practices:
    - Use `DIHelper.create_test_provider()` or the `di_provider` fixture for isolated providers.
    - Use `DIHelper.override_service` or `DIHelper.async_override_service` for temporary service overrides.
    - Use `DIHelper.register_mock` to inject mocks/doubles.
    - Always reset DI state between tests with `DIHelper.reset_di_state()` or the fixture.

    Additional Utilities:
    - `DIHelper.batch_override_services`: Context manager to override multiple services at once.
    - `DIHelper.di_provider_fixture`: Pytest fixture for isolated providers.
    - `DIHelper.teardown_provider`: Helper for provider teardown/cleanup.
    """

    @staticmethod
    def create_test_provider() -> ServiceProvider:
        """
        Create a clean, isolated ServiceProvider for testing.
        """
        return ServiceProvider()

    @staticmethod
    def initialize_test_provider(
        provider: ServiceProvider | None = None,
        site_name: str = "Uno Test Site",
        env: str = "test",
    ) -> ServiceProvider:
        """
        Initialize a service provider for testing.
        Args:
            provider (ServiceProvider | None): Optional provider to initialize (creates a new one if None)
            site_name (str): Site name to use for GeneralConfig
            env (str): Environment to use
        Returns:
            ServiceProvider: The initialized service provider
        """
        os.environ["ENV"] = env
        provider = provider if provider is not None else DIHelper.create_test_provider()
        services = ServiceCollection()
        services.add_instance(GeneralConfig, GeneralConfig(SITE_NAME=site_name))
        provider.configure_services(services)
        return provider
