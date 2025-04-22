# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
uno.core.di.test_helpers

Provides utilities for setting up and configuring the Uno Dependency Injection system in test environments.
Includes helpers for creating isolated ServiceProvider instances, configuring test services, and ensuring test isolation.

This module provides utilities for setting up and configuring the DI system
in test environments, with proper isolation and cleanup.
"""

import os
from uno.config.general import GeneralConfig
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider


import contextlib
import asyncio
from typing import Any, Callable, Iterator, AsyncIterator

class TestDI:
    """
    Helper class for managing DI in tests.

    Provides utilities for test isolation, temporary service overrides (sync & async),
    registering mocks/doubles in a test context, and pytest fixtures for DI setup.

    Best Practices:
    - Use `TestDI.create_test_provider()` or the `di_provider` fixture for isolated providers.
    - Use `TestDI.override_service` or `TestDI.async_override_service` for temporary service overrides.
    - Use `TestDI.register_mock` to inject mocks/doubles.
    - Always reset DI state between tests with `TestDI.reset_di_state()` or the fixture.
    """

    @staticmethod
    def create_test_provider() -> ServiceProvider:
        """
        Create a clean, isolated service provider for testing.

        Returns:
            ServiceProvider: A fresh service provider instance with a clean state, suitable for isolated testing.
        """
        provider = ServiceProvider()
        provider._initialized = False
        provider._lifecycle_queue.clear()
        provider._extensions.clear()
        provider._base_services = ServiceCollection()
        return provider

    @staticmethod
    @contextlib.contextmanager
    def override_service(provider: ServiceProvider, service_type: type, implementation_or_instance: Any) -> Iterator[None]:
        """
        Context manager to temporarily override a service registration or instance for a test (sync).
        Restores the original registration/instance after exiting the context.

        Args:
            provider: The ServiceProvider to modify
            service_type: The type or protocol to override
            implementation_or_instance: The new implementation or instance to use

        Usage:
            with TestDI.override_service(provider, MyService, my_mock):
                ... # test code
        """
        orig_reg = provider._base_services._registrations.get(service_type)
        orig_inst = provider._base_services._instances.get(service_type)
        try:
            if callable(implementation_or_instance):
                provider._base_services.add_singleton(service_type, implementation_or_instance)
            else:
                provider._base_services.add_instance(service_type, implementation_or_instance)
            yield
        finally:
            if orig_reg is not None:
                provider._base_services._registrations[service_type] = orig_reg
            else:
                provider._base_services._registrations.pop(service_type, None)
            if orig_inst is not None:
                provider._base_services._instances[service_type] = orig_inst
            else:
                provider._base_services._instances.pop(service_type, None)

    @staticmethod
    @contextlib.asynccontextmanager
    async def async_override_service(provider: ServiceProvider, service_type: type, implementation_or_instance: Any) -> AsyncIterator[None]:
        """
        Async context manager to temporarily override a service registration or instance for a test (async).
        Restores the original registration/instance after exiting the context.

        Usage:
            async with TestDI.async_override_service(provider, MyService, my_mock):
                ... # async test code
        """
        orig_reg = provider._base_services._registrations.get(service_type)
        orig_inst = provider._base_services._instances.get(service_type)
        try:
            if callable(implementation_or_instance):
                provider._base_services.add_singleton(service_type, implementation_or_instance)
            else:
                provider._base_services.add_instance(service_type, implementation_or_instance)
            yield
        finally:
            if orig_reg is not None:
                provider._base_services._registrations[service_type] = orig_reg
            else:
                provider._base_services._registrations.pop(service_type, None)
            if orig_inst is not None:
                provider._base_services._instances[service_type] = orig_inst
            else:
                provider._base_services._instances.pop(service_type, None)

    @staticmethod
    def register_mock(provider: ServiceProvider, service_type: type, mock_instance: Any) -> None:
        """
        Register a mock or test double as a singleton for the test.
        Args:
            provider: The ServiceProvider to modify
            service_type: The type or protocol to override
            mock_instance: The mock or test double to use
        """
        provider._base_services.add_instance(service_type, mock_instance)

    @staticmethod
    def reset_di_state() -> None:
        """
        Reset any global DI state (if present). Useful for test teardown.
        This is a no-op unless global provider state is used.
        """
        # If global provider state exists, reset it here
        from uno.core.di.provider import _service_provider
        try:
            _service_provider = None
        except Exception:
            pass

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
        # Always use a local or explicitly provided provider
        provider = provider if provider is not None else TestDI.create_test_provider()
        services = ServiceCollection()
        services.add_instance(GeneralConfig, GeneralConfig(SITE_NAME=site_name))
        provider.configure_services(services)
        return provider

    @staticmethod
    async def setup_test_services(
        provider: ServiceProvider | None = None,
        additional_services: ServiceCollection | None = None,
    ) -> ServiceProvider:
        """
        Set up test services and initialize the provider.

        Args:
            provider (ServiceProvider | None): Optional provider to use (creates a new one if None)
            additional_services (ServiceCollection | None): Optional additional services to register

        Returns:
            ServiceProvider: The initialized service provider
        """
        # Always use a local or explicitly provided provider
        provider = TestDI.initialize_test_provider(provider)
        if additional_services:
            provider.configure_services(additional_services)
        await provider.initialize()
        return provider
