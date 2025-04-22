# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Modern service provider for Uno framework.

This module implements a service provider pattern that uses the scoped container
to provide enhanced dependency injection functionality, including proper scoping,
automatic dependency resolution, and improved lifecycle management.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, TypeVar, overload

from uno.core.di.container import (
    ServiceCollection,
    create_async_scope,
    create_scope,
    get_container,
    get_service,
    initialize_container,
)
from uno.core.di.interfaces import (
    ConfigProtocol,
    DatabaseProviderProtocol,
    DBManagerProtocol,
    DTOManagerProtocol,
    EventBusProtocol,
    SQLEmitterFactoryProtocol,
    SQLExecutionProtocol,
)
from uno.core.errors.base import FrameworkError
from uno.core.errors.definitions import DependencyResolutionError
from uno.core.errors.result import Failure, Success

T = TypeVar("T")
EntityT = TypeVar("EntityT")
QueryT = TypeVar("QueryT")
ResultT = TypeVar("ResultT")


class ServiceLifecycle:
    """Interface for services with custom initialization and disposal."""

    async def initialize(self) -> None:
        """Initialize the service asynchronously."""
        pass

    async def dispose(self) -> None:
        """Dispose the service asynchronously."""
        pass


class ServiceProvider:
    """
    Modern service provider for the Uno framework.

    This class provides a centralized registry for all services in the application,
    with support for scoped services, lifecycle management, and automatic dependency resolution.
    """

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize the service provider.

        Args:
            logger: Optional logger for diagnostic information
        """
        from uno.core.logging.logger import get_logger

        self._logger = logger or get_logger("uno.services")
        self._initialized = False
        self._base_services = ServiceCollection()
        self._extensions: dict[str, ServiceCollection] = {}
        self._lifecycle_queue: list[type[ServiceLifecycle]] = []
        self._initializing = False

    def is_initialized(self) -> bool:
        """Return True if the service provider has been initialized."""
        return self._initialized

    def configure_services(
        self, services: ServiceCollection
    ) -> Success[None] | Failure[FrameworkError]:
        """
        Configure the base services.

        Args:
            services: The service collection to use

        Returns:
            Success(None) if base services set, or Failure(FrameworkError) if already initialized.
        """
        if self._initialized:
            return Failure(
                FrameworkError(
                    "Services have already been initialized and cannot be reconfigured",
                    "SERVICES_ALREADY_INITIALIZED",
                )
            )
        self._base_services = services

    def register_extension(self, name: str, services: ServiceCollection) -> None:
        """
        Register a service extension.

        Args:
            name: The name of the extension
            services: The service collection containing extension services

        Returns:
            Success(None) if extension registered, or Failure(FrameworkError) if already initialized.
        """
        if self._initialized:
            return Failure(
                FrameworkError(
                    "Services have already been initialized and cannot be extended",
                    "SERVICES_ALREADY_INITIALIZED",
                )
            )
        self._extensions[name] = services

    def register_lifecycle_service(self, service_type: type[ServiceLifecycle]) -> None:
        """
        Register a service that requires lifecycle management.

        Args:
            service_type: The service type to register
        """
        self._lifecycle_queue.append(service_type)

    async def initialize(self) -> None:
        """
        Initialize the service provider.

        This method initializes the container and all registered services.
        It should be called during application startup.
        """
        if self._initialized:
            return

        if self._initializing:
            # Prevent circular initialization
            self._logger.warning("Service initialization is already in progress")
            return

        self._initializing = True
        try:
            # Initialize container with base services
            initialize_container(self._base_services, self._logger)

            # Initialize each extension
            for name, services in self._extensions.items():
                container = get_container()
                for (
                    service_type,
                    registration,
                ) in services._registrations.items():  # Access private attribute
                    container.register(
                        service_type,
                        registration.implementation,
                        registration.scope,
                        registration.params,
                    )
                for (
                    service_type,
                    instance,
                ) in services._instances.items():  # Access private attribute
                    container.register_instance(service_type, instance)

                self._logger.info(f"Initialized extension: {name}")

            # Initialize lifecycle services
            if self._lifecycle_queue:
                self._logger.info(
                    f"Initializing {len(self._lifecycle_queue)} lifecycle services"
                )

                async with create_async_scope("lifecycle_initialization") as scope:
                    # Initialize each service
                    for service_type in self._lifecycle_queue:
                        try:
                            service = scope.resolve(service_type)
                            await service.initialize()
                            self._logger.debug(
                                f"Initialized lifecycle service: {service_type.__name__}"
                            )
                        except Exception as e:
                            self._logger.error(
                                f"Error initializing service {service_type.__name__}: {str(e)}"
                            )
                            raise

            self._initialized = True
            self._logger.info("Service provider initialized successfully")

        finally:
            self._initializing = False

    async def shutdown(self) -> None:
        """
        Shut down the service provider.

        This method disposes all registered services in the reverse order they were initialized.
        It should be called during application shutdown.
        """
        if not self._initialized:
            return

        self._logger.info("Shutting down service provider")

        # Shut down lifecycle services in reverse order
        if self._lifecycle_queue:
            # Make a reversed copy to avoid modifying the original
            reversed_queue = self._lifecycle_queue.copy()
            reversed_queue.reverse()

            self._logger.info(f"Disposing {len(reversed_queue)} lifecycle services")

            for service_type in reversed_queue:
                try:
                    # Get the service if it exists
                    service = get_service(service_type)
                    await service.dispose()
                    self._logger.debug(
                        f"Disposed lifecycle service: {service_type.__name__}"
                    )
                except Exception as e:
                    self._logger.error(
                        f"Error disposing service {service_type.__name__}: {str(e)}"
                    )

        self._initialized = False
        self._logger.info("Service provider shut down")

    def get_service(self, service_type: type[T]) -> T:
        """
        Get a service by its type.

        Args:
            service_type: The type of service to retrieve

        Returns:
            An instance of the requested service

        Raises:
            FrameworkError: If the service provider is not initialized
        """
        if not self._initialized:
            self._logger.error("Service provider not initialized")
            return Failure(
                FrameworkError(
                    "Service provider must be initialized before retrieving services",
                    "SERVICES_NOT_INITIALIZED",
                )
            )

        return get_service(service_type)

    @overload
    def get_service_in_scope(self, service_type: type[T]) -> T: ...

    @overload
    def get_service_in_scope(self, service_type: type[T], scope_id: str) -> T: ...

    def get_service_in_scope(
        self, service_type: type[T], scope_id: str | None = None
    ) -> T:
        """
        Get a service in a new scope.

        This method creates a new scope and resolves the service within it.
        The scope is closed after the service is resolved, so any scoped
        dependencies will be disposed.

        Args:
            service_type: The type of service to retrieve
            scope_id: Optional scope identifier

        Returns:
            An instance of the requested service

        Raises:
            FrameworkError: If the service provider is not initialized
        """
        if not self._initialized:
            self._logger.error("Service provider not initialized")
            return Failure(
                FrameworkError(
                    "Service provider must be initialized before retrieving services",
                    "SERVICES_NOT_INITIALIZED",
                )
            )

        with create_scope(scope_id) as scope:
            return scope.resolve(service_type)

    async def get_service_async_scope(
        self, service_type: type[T], scope_id: str | None = None
    ) -> T:
        """
        Get a service in a new async scope.

        This method creates a new async scope and resolves the service within it.
        The scope is closed after the service is resolved, so any scoped
        dependencies will be disposed.

        Args:
            service_type: The type of service to retrieve
            scope_id: Optional scope identifier

        Returns:
            An instance of the requested service

        Raises:
            FrameworkError: If the service provider is not initialized
        """
        if not self._initialized:
            self._logger.error("Service provider not initialized")
            return Failure(
                FrameworkError(
                    "Service provider must be initialized before retrieving services",
                    "SERVICES_NOT_INITIALIZED",
                )
            )

        async with create_async_scope(scope_id) as scope:
            return scope.resolve(service_type)

    @asynccontextmanager
    async def create_scope(self, scope_id: str | None = None):
        """
        Create a service scope.

        This async context manager creates a new scope for resolving scoped services,
        ensuring they are properly disposed when the scope ends.

        Args:
            scope_id: Optional scope identifier

        Yields:
            The service resolver with the active scope

        Raises:
            FrameworkError: If the service provider is not initialized
        """
        if not self._initialized:
            self._logger.error("Service provider not initialized")
            raise FrameworkError(
                "Service provider must be initialized before creating a scope",
                "SERVICES_NOT_INITIALIZED",
            )

        async with create_async_scope(scope_id) as scope:
            yield scope

    # Convenience methods for common services

    def get_config(self) -> ConfigProtocol:
        """
        Get the configuration service.

        Returns:
            The configuration service
        """
        return self.get_service(ConfigProtocol)

    def get_db_provider(self) -> DatabaseProviderProtocol:
        """
        Get the database provider service.

        Returns:
            The database provider service
        """
        return self.get_service(DatabaseProviderProtocol)

    def get_db_manager(self) -> DBManagerProtocol:
        """
        Get the database manager service.

        Returns:
            The database manager service
        """
        return self.get_service(DBManagerProtocol)

    def get_dto_manager(self) -> DTOManagerProtocol:
        """
        Get the DTO manager service.

        Returns:
            The DTO manager service
        """
        return self.get_service(DTOManagerProtocol)

    def get_sql_emitter_factory(self) -> SQLEmitterFactoryProtocol:
        """
        Get the SQL emitter factory service.

        Returns:
            The SQL emitter factory service
        """
        return self.get_service(SQLEmitterFactoryProtocol)

    def get_sql_execution_service(self) -> SQLExecutionProtocol:
        """
        Get the SQL execution service.

        Returns:
            The SQL execution service
        """
        return self.get_service(SQLExecutionProtocol)

    def get_event_bus(self) -> EventBusProtocol:
        """
        Get the event bus service.

        Returns:
            The event bus service
        """
        return self.get_service(EventBusProtocol)

    def get_vector_config(self):
        """
        Get the vector configuration service.

        Returns:
            The vector configuration service
        """
        # Import here to avoid circular imports
        from uno.core.di.vector_interfaces import VectorConfigServiceProtocol

        return self.get_service(VectorConfigServiceProtocol)

    def get_vector_update_service(self):
        """
        Get the vector update service.

        Returns:
            The vector update service
        """
        # Import here to avoid circular imports
        from uno.core.di.vector_interfaces import VectorUpdateServiceProtocol

        return self.get_service(VectorUpdateServiceProtocol)

    def get_batch_vector_update_service(self):
        """
        Get the batch vector update service.

        Returns:
            The batch vector update service
        """
        # Import here to avoid circular imports
        from uno.core.di.vector_interfaces import BatchVectorUpdateServiceProtocol

        return self.get_service(BatchVectorUpdateServiceProtocol)

    def get_vector_search_service(self, entity_type, table_name, repository=None):
        """
        Get a vector search service for a specific entity type.

        Args:
            entity_type: The entity type to search
            table_name: The database table name
            repository: Optional repository to use

        Returns:
            Vector search service
        """
        # Import here to avoid circular imports
        from uno.core.di.vector_interfaces import VectorSearchServiceFactoryProtocol

        factory = self.get_service(VectorSearchServiceFactoryProtocol)
        return factory.create_search_service(entity_type, table_name, repository)

    def get_rag_service(self, vector_search):
        """
        Get a RAG service using a vector search service.

        Args:
            vector_search: The vector search service to use

        Returns:
            RAG service
        """
        # Import here to avoid circular imports
        from uno.core.di.vector_interfaces import RAGServiceFactoryProtocol

        factory = self.get_service(RAGServiceFactoryProtocol)
        return factory.create_rag_service(vector_search)


import threading

# Thread-safe global singleton pattern for ServiceProvider
_service_provider: ServiceProvider | None = None
_service_provider_lock = threading.Lock()

def get_service_provider() -> ServiceProvider:
    """
    Get the global service provider instance (thread-safe singleton).

    Returns:
        The service provider instance
    """
    global _service_provider
    if _service_provider is None:
        with _service_provider_lock:
            if _service_provider is None:
                _service_provider = ServiceProvider()
    return _service_provider

# Generic thread-safe singleton pattern for any class (for future use)
def get_singleton(cls, *args, **kwargs):
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


def register_singleton(service_type: type[T], instance: T) -> None:
    """
    Register a singleton instance in the container.

    This is useful for registering resources and services that should be
    available globally across the application.

    Args:
        service_type: The type to register
        instance: The instance to register

    Raises:
        DependencyResolutionError: If the dependency injection is not set up
    """
    try:
        container = get_container()
        container.register_instance(service_type, instance)
    except Exception as e:
        return Failure(
            DependencyResolutionError(
                f"Failed to register singleton for {service_type.__name__}: {str(e)}",
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

    # Register configuration service
    from uno.settings import uno_settings

    class UnoConfig(ConfigProtocol):
        """Configuration provider implementation."""

        def __init__(self, settings=None):
            self._settings = settings or uno_settings

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

    # Register logger
    from uno.core.logging.logger import get_logger

    services.add_singleton(logging.Logger, lambda: get_logger("uno"))

    # Register database provider
    from uno.database.config import ConnectionConfig
    from uno.database.provider import DatabaseProvider

    # Create connection config from settings
    connection_config = ConnectionConfig(
        db_role=uno_settings.DB_NAME + "_login",
        db_name=uno_settings.DB_NAME,
        db_host=uno_settings.DB_HOST,
        db_port=uno_settings.DB_PORT,
        db_user_pw=uno_settings.DB_USER_PW,
        db_driver=uno_settings.DB_ASYNC_DRIVER,
        db_schema=uno_settings.DB_SCHEMA,
    )

    # Create and register database provider
    db_provider = DatabaseProvider(connection_config, logger=get_logger("uno.database"))
    services.add_instance(DatabaseProvider, db_provider)
    services.add_instance(DatabaseProviderProtocol, db_provider)

    # Register database manager
    from uno.database.db_manager import DBManager

    services.add_singleton(
        DBManagerProtocol,
        DBManager,
        connection_provider=db_provider.sync_connection,
        logger=get_logger("uno.database"),
    )

    # Register SQL emitter factory
    from uno.sql.services import SQLEmitterFactoryService

    services.add_singleton(
        SQLEmitterFactoryProtocol,
        SQLEmitterFactoryService,
        config=UnoConfig(),
        logger=get_logger("uno.sql"),
    )

    # Register SQL execution service
    from uno.sql.services import SQLExecutionService

    services.add_singleton(
        SQLExecutionProtocol, SQLExecutionService, logger=get_logger("uno.sql")
    )

    # Register schema manager
    from uno.schema.services import DTOManagerService

    services.add_singleton(
        DTOManagerProtocol,
        DTOManagerService,
        logger=get_logger("uno.schema"),
    )

    # Register event bus
    from uno.domain.events import EventBus, EventPublisher

    event_bus = EventBus(logger=get_logger("uno.events"))
    services.add_instance(EventBus, event_bus)
    services.add_instance(EventBusProtocol, event_bus)
    services.add_instance(
        EventPublisher,
        EventPublisher(event_bus, logger=get_logger("uno.events")),
    )

    # Register domain registry
    from uno.domain.factory import DomainRegistry

    services.add_singleton(
        DomainRegistry, DomainRegistry, logger=get_logger("uno.domain")
    )

    # Configure the service provider
    provider.configure_services(services)

    # Initialize vector search components if available
    try:
        # Register vector search components
        from uno.core.di.vector_provider import configure_vector_services

        await configure_vector_services()
    except (ImportError, AttributeError) as e:
        get_logger("uno.services").debug(f"Vector search provider not available: {e}")
        pass

    # Register queries provider
    try:
        from uno.queries.domain_provider import get_queries_provider

        provider.register_extension("queries", get_queries_provider())
    except (ImportError, AttributeError) as e:
        get_logger("uno.services").debug(f"Queries provider not available: {e}")
        pass

    # Register reports provider
    try:
        from uno.reports.domain_provider import get_reports_provider

        provider.register_extension("reports", get_reports_provider())
    except (ImportError, AttributeError) as e:
        get_logger("uno.services").debug(f"Reports provider not available: {e}")
        pass
