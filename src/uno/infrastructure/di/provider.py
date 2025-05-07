# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Modern service provider for Uno framework.

This module implements a service provider pattern that uses the scoped container
to provide enhanced dependency injection functionality, including proper scoping,
automatic dependency resolution, and improved lifecycle management.

Note: All dependencies must be passed explicitly from the composition root.
"""

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable, Type, Callable
import threading

if TYPE_CHECKING:
    from uno.core.events.bus import EventBusProtocol

from uno.core.errors.base import FrameworkError
from uno.infrastructure.di.errors import DependencyResolutionError
from uno.core.errors.result import Failure, Result, Success
from uno.infrastructure.di.interfaces import ServiceProtocol


from uno.infrastructure.di import ServiceCollection, ServiceProvider, ServiceLifecycle

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])
TEntity = TypeVar("TEntity", bound=Any)
TQuery = TypeVar("TQuery", bound=Any)
TResult = TypeVar("TResult", bound=Any)


async def register_singleton(
    service_type: type[TService], instance: TService, provider: ServiceProvider
) -> Result[None, FrameworkError]:
    """
    Register a singleton instance in the container.

    This is useful for registering resources and services that should be
    available globally across the application.

    Args:
        service_type: The type to register
        instance: The instance to register
        provider: The service provider instance

    Returns:
        Success(None) if registered successfully, or Failure with error details

    Example:
        ```python
        # Register a singleton service
        result = await register_singleton(IMyService, MyService(), provider)
        if result.is_success:
            print("Service registered successfully")
        ```
    """
    try:
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


async def shutdown_services(provider: ServiceProvider) -> None:
    """
    Shut down all services.

    This function should be called during application shutdown to ensure
    that all services are properly disposed.

    Args:
        provider: The service provider instance

    Example:
        ```python
        # Shut down services
        await shutdown_services(provider)
        ```
    """
    provider.shutdown()


async def configure_base_services(provider: ServiceProvider) -> None:
    """
    Configure the base services for the application.

    This function configures the base services for the application,
    including the configuration service, database provider, and more.

    Args:
        provider: The service provider instance

    Example:
        ```python
        # Configure base services
        await configure_base_services(provider)
        ```
    """
    if provider._initialized:
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

    from uno.infrastructure.config import GeneralConfig

    # Register configuration service
    config = GeneralConfig()
    services.add_instance(ConfigProtocol, config)

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
    services.add_singleton(LoggerService, LoggerService(logging_config))

    # Register hash service
    from uno.core.services.hash_service_protocol import HashServiceProtocol
    from uno.core.services.default_hash_service import DefaultHashService
    services.add_singleton(HashServiceProtocol, DefaultHashService)

    # Register database provider
    from uno.infrastructure.di.providers.database import register_database_services

    from uno.infrastructure.config.database import DatabaseConfig
    
    register_database_services(services, config=DatabaseConfig(
        DB_USER=database_config.DB_USER,
        DB_USER_PW=database_config.DB_USER_PW,
        DB_HOST=database_config.DB_HOST,
        DB_PORT=database_config.DB_PORT,
        DB_SCHEMA=database_config.DB_SCHEMA,
        DB_NAME=database_config.DB_NAME,
        DB_SYNC_DRIVER=database_config.DB_SYNC_DRIVER,
        DB_ASYNC_DRIVER=database_config.DB_ASYNC_DRIVER
    ))

    # Register SQL emitter factory
    from uno.infrastructure.sql.services import SQLEmitterFactoryService

    # Build the provider and get LoggerService instance
    provider = ServiceProvider(services)
    logger = provider.get_service(LoggerService)

    services.add_singleton(
        SQLEmitterFactoryProtocol,
        SQLEmitterFactoryService,
    )

    # Register SQL execution service
    from uno.infrastructure.sql.services.sql_execution_service import SQLExecutionService
    from uno.infrastructure.di.providers.database import get_db_manager
    
    db_manager = get_db_manager(provider)
    services.add_singleton(SQLExecutionServiceProtocol, SQLExecutionService, db_manager=db_manager, logger=logger)

    # Register schema manager
    from uno.schema.services import DTOManagerService

    services.add_singleton(DTOManagerProtocol, DTOManagerService, logger=logger)

    # Register event bus
    from uno.core.events.handlers import EventBus

    event_bus = EventBus(logger=logger)
    services.add_instance(EventBus, event_bus)
    services.add_instance(EventBusProtocol, event_bus)

    # Register domain registry
    from uno.domain.factory import DomainRegistry

    services.add_singleton(DomainRegistry, DomainRegistry, logger=logger)

    # Get provider and configure services
    provider.configure_services(services)

    # Initialize vector search components if available
    try:
        from uno.infrastructure.di.vector_provider import configure_vector_services

        await configure_vector_services()
    except (ImportError, AttributeError) as e:
        logger_service.debug(f"Vector search provider not available: {e}")

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
