# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Modern service provider for Uno framework.

This module implements a service provider pattern that uses the scoped container
to provide enhanced dependency injection functionality, including proper scoping,
automatic dependency resolution, and improved lifecycle management.
"""

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from uno.core.events.bus import EventBusProtocol

from uno.core.errors.base import FrameworkError
from uno.core.errors.definitions import DependencyResolutionError
from uno.core.errors.result import Failure, Result, Success
from uno.core.interfaces import (
    ConfigProtocol,
    DTOManagerProtocol,
    SQLEmitterFactoryProtocol,
    SQLExecutionProtocol,
)
from uno.infrastructure.di import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider

T = TypeVar("T")
EntityT = TypeVar("EntityT")
QueryT = TypeVar("QueryT")
ResultT = TypeVar("ResultT")


@runtime_checkable
class ServiceLifecycle(Protocol):
    """Interface for services with custom initialization and disposal."""

    async def initialize(self) -> None:
        """Initialize the service asynchronously."""
        ...

    async def dispose(self) -> None:
        """Dispose the service asynchronously."""
        ...


# Global service provider state
_service_provider: ServiceProvider | None = None
_service_provider_lock = threading.Lock()


def get_singleton(cls, *args, **kwargs):
    """
    Generic thread-safe singleton factory for any class.
    Usage: instance = get_singleton(MyClass, ...)
    """
    if not hasattr(cls, "_instance"):
        with threading.Lock():
            if not hasattr(cls, "_instance"):
                cls._instance = cls(*args, **kwargs)
    return cls._instance


def register_singleton(
    service_type: type[T], instance: T
) -> Result[None, FrameworkError]:
    """
    Register a singleton instance in the container.

    This is useful for registering resources and services that should be
    available globally across the application.

    Args:
        service_type: The type to register
        instance: The instance to register

    Returns:
        Success(None) if registered successfully, or Failure with error details
    """
    try:
        provider = get_service_provider()
        services = ServiceCollection()
        services.add_instance(service_type, instance)
        provider.configure_services(services)
        return Success(None)
    except Exception as e:
        return Failure(
            DependencyResolutionError(
                f"Failed to register singleton for {service_type.__name__}: {e!s}",
                "DEPENDENCY_REGISTRATION_ERROR",
            )
        )


async def initialize_services() -> None:
    """
    Initialize all services.

    This function should be called during application startup to ensure
    that all services are properly initialized and ready to use.
    """
    # Configure the base service collection
    await configure_base_services()

    # Initialize the service provider
    provider = get_service_provider()
    await provider.initialize()


async def shutdown_services() -> None:
    """
    Shut down all services.

    This function should be called during application shutdown to ensure
    that all services are properly disposed.
    """
    provider = get_service_provider()
    await provider.shutdown()


async def configure_base_services() -> None:
    """
    Configure the base services for the application.

    This function configures the base services for the application,
    including the configuration service, database provider, and more.
    """
    provider = get_service_provider()
    if provider.is_initialized():
        return

    # Create service collection
    services = ServiceCollection()

    # Register configuration service using DI (no direct uno_settings import)
    from uno.infrastructure.config import (
        general_config,
        application_config,
        database_config,
        security_config,
        api_config,
        vector_search_config,
    )

    class UnoConfig(ConfigProtocol):
        """Configuration provider implementation."""

        def __init__(self, settings=None):
            # Always resolve from DI unless explicitly injected
            provider = get_service_provider()
            self._settings = settings or provider.get_service(type(general_config))

        def get_value(self, key: str, default: Any = None) -> Any:
            """Get a configuration value by key."""
            return getattr(self._settings, key, default)

        def all(self) -> dict[str, Any]:
            """Get all configuration values."""
            return {
                k: v
                for k, v in self._settings.__dict__.items()
                if not k.startswith("_")
            }

    services.add_singleton(ConfigProtocol, UnoConfig)

    # Register all config objects as singletons in DI
    from uno.infrastructure.config.api import APIConfig
    from uno.infrastructure.config.application import ApplicationConfig
    from uno.infrastructure.config.database import DatabaseConfig
    from uno.infrastructure.config.general import GeneralConfig
    from uno.infrastructure.config.security import SecurityConfig
    from uno.infrastructure.config.vector_search import VectorSearchConfig

    services.add_singleton(GeneralConfig, general_config)
    services.add_singleton(ApplicationConfig, application_config)
    services.add_singleton(DatabaseConfig, database_config)
    services.add_singleton(SecurityConfig, security_config)
    services.add_singleton(APIConfig, api_config)
    services.add_singleton(VectorSearchConfig, vector_search_config)

    # Register LoggerService as a singleton
    from uno.infrastructure.logging.logger import LoggerService

    from uno.infrastructure.logging.logger import LoggingConfig

    logging_config = LoggingConfig()
    services.add_singleton(
        LoggerService, implementation=LoggerService, config=logging_config
    )

    # Register database provider
    from uno.infrastructure.config.database import DatabaseConfig
    from uno.infrastructure.di.providers.database import register_database_services

    # Register database engine and session providers
    register_database_services(services)

    # Register SQL emitter factory
    from uno.infrastructure.sql.services import SQLEmitterFactoryService

    # Retrieve the DI-injected LoggerService instance
    # Build the resolver and get LoggerService instance
    resolver = services.build()
    logger_service = resolver.get(LoggerService)

    services.add_singleton(
        SQLEmitterFactoryProtocol,
        SQLEmitterFactoryService,
        config=UnoConfig(),
        # Use DI-injected LoggerService; downstream must call get_logger("uno.infrastructure.sql") if needed
        logger=logger_service,
    )

    # Register SQL execution service

    services.add_singleton(
        SQLExecutionProtocol,
        logger=logger_service,  # Use DI-injected LoggerService; downstream must call get_logger("uno.infrastructure.sql") if needed
    )

    # Register schema manager
    from uno.schema.services import DTOManagerService

    services.add_singleton(
        DTOManagerProtocol,
        DTOManagerService,
        # Use DI-injected LoggerService; downstream must call get_logger("uno.schema") if needed
        logger=logger_service,
    )

    # Register event bus
    from uno.core.events.handlers import EventHandler

    # Import the concrete EventBus implementation only when needed
    # to avoid circular imports
    from uno.core.events.handlers import EventBus

    # Use DI-injected LoggerService; downstream must call get_logger("uno.events") if needed
    event_bus = EventBus(logger=logger_service)
    services.add_instance(EventBus, event_bus)
    services.add_instance(EventBusProtocol, event_bus)

    # Register domain registry
    from uno.domain.factory import DomainRegistry

    services.add_singleton(
        DomainRegistry,
        DomainRegistry,  # Use DI-injected LoggerService; downstream must call get_logger("uno.domain") if needed
        logger=logger_service,
    )

    # Configure the service provider
    provider.configure_services(services)

    # Initialize vector search components if available
    try:
        # Register vector search components
        from uno.infrastructure.di.vector_provider import configure_vector_services

        await configure_vector_services()
    except (ImportError, AttributeError) as e:
        logger_service.debug(f"Vector search provider not available: {e}")
        pass

    # Register queries provider
    try:
        from uno.queries.domain_provider import get_queries_provider

        provider.register_extension("queries", get_queries_provider())
    except (ImportError, AttributeError) as e:
        logger_service.debug(f"Queries provider not available: {e}")
        pass

    # Register reports provider
    try:
        from uno.reports.domain_provider import get_reports_provider

        provider.register_extension("reports", get_reports_provider())
    except (ImportError, AttributeError) as e:
        logger_service.debug(f"Reports provider not available: {e}")
        pass


def get_service_provider() -> ServiceProvider:
    """
    Get the global service provider instance (thread-safe singleton).

    If no provider exists, creates one with a default LoggerService using a minimal LoggingConfig.
    This fallback avoids DI bootstrapping issues ("chicken-and-egg" problem).

    Returns:
        The service provider instance
    """
    global _service_provider
    if _service_provider is None:
        with _service_provider_lock:
            if _service_provider is None:
                from uno.infrastructure.logging.logger import (
                    LoggerService,
                    LoggingConfig,
                )

                logger = LoggerService(LoggingConfig())
                _service_provider = ServiceProvider(logger=logger)
    return _service_provider


def reset_global_service_provider() -> None:
    """
    Reset the global DI service provider and all related global DI state.
    Intended for test isolation and advanced scenarios.
    """
    global _service_provider
    _service_provider = None
    # If there are other globals (locks, caches), reset them here as well.


# Generic thread-safe singleton pattern for any class (for future use)
# Global service provider state
_service_provider: ServiceProvider | None = None
_service_provider_lock = threading.Lock()


def get_service_provider() -> ServiceProvider:
    """
    Get the global service provider instance (thread-safe singleton).

    If no provider exists, creates one with a default LoggerService using a minimal LoggingConfig.
    This fallback avoids DI bootstrapping issues ("chicken-and-egg" problem).

    Returns:
        The service provider instance
    """
    global _service_provider
    if _service_provider is None:
        with _service_provider_lock:
            if _service_provider is None:
                from uno.infrastructure.logging.logger import (
                    LoggerService,
                    LoggingConfig,
                )

                logger = LoggerService(LoggingConfig())
                _service_provider = ServiceProvider(logger=logger)
    return _service_provider


def reset_global_service_provider() -> None:
    """
    Reset the global DI service provider and all related global DI state.
    Intended for test isolation and advanced scenarios.
    """
    global _service_provider
    _service_provider = None
    # If there are other globals (locks, caches), reset them here as well.


def get_singleton(cls, *args, **kwargs) -> T:
    """
    Generic thread-safe singleton factory for any class.
    Usage: instance = get_singleton(MyClass, ...)
    """
    if not hasattr(cls, "_singleton_instance"):
        cls._singleton_lock = threading.Lock()
        cls._singleton_instance = None
    if cls._singleton_instance is None:
        with cls._singleton_lock:
            if cls._singleton_instance is None:
                cls._singleton_instance = cls(*args, **kwargs)
    return cls._singleton_instance


def register_singleton(
    service_type: type[T], instance: T
) -> Result[None, FrameworkError]:
    """
    Register a singleton instance in the container.

    This is useful for registering resources and services that should be
    available globally across the application.

    Args:
        service_type: The type to register
        instance: The instance to register

    Returns:
        Success(None) if registered successfully, or Failure with error details
    """
    try:
        provider = get_service_provider()
        services = ServiceCollection()
        services.add_instance(service_type, instance)
        provider.configure_services(services)
        return Success(None)
    except Exception as e:
        return Failure(
            DependencyResolutionError(
                f"Failed to register singleton for {service_type.__name__}: {e!s}",
                "DEPENDENCY_REGISTRATION_ERROR",
            )
        )
