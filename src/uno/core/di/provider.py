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
import threading
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from uno.core.events.events import EventBusProtocol, EventBus

from uno.core.di.container import ServiceCollection, ServiceScope, ServiceResolver
from uno.core.di.interfaces import (
    ConfigProtocol,
    DatabaseProviderProtocol,
    DBManagerProtocol,
    DTOManagerProtocol,
    SQLEmitterFactoryProtocol,
    SQLExecutionProtocol,
)
from uno.core.errors.base import FrameworkError
from uno.core.errors.definitions import DependencyResolutionError
from uno.core.errors.result import Failure, Result, Success

# Import EventBusProtocol only from type checking to avoid circular imports
if TYPE_CHECKING:
    from uno.core.events.events import EventBus

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


class ServiceProvider:
    """
    Modern service provider for the Uno framework.

    This class provides a centralized registry for all services in the application,
    with support for scoped services, lifecycle management, and automatic dependency resolution.

    Performance Tuning:
    - Use `prewarm_singletons()` after configuring services and before starting your app to eagerly instantiate all singleton services.
    - This can help catch errors early and improve startup performance for critical services.

    API Clarity:
    - Most users should interact with ServiceProvider and ServiceCollection only.
    - Internal helpers (e.g., ServiceResolver, ServiceRegistration) are for advanced/extensibility use only.
    """

    def __init__(
        self,
        services: ServiceCollection | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize the service provider.

        Args:
            services: Optional ServiceCollection to use as the base service registry
            logger: Optional logger for diagnostic information
        """
        self._logger = logger or logging.getLogger("uno.services")
        self._initialized = False
        self._base_services = services or ServiceCollection()
        self._extensions: dict[str, ServiceCollection] = {}
        self._lifecycle_queue: list[type[ServiceLifecycle]] = []
        self._initializing = False

    def _auto_register_lifecycle_services(self) -> None:
        """
        Automatically detect and register all ServiceLifecycle subclasses for lifecycle management.
        Enforces singleton scope for all lifecycle services and raises errors if misconfigured.
        """
        from uno.core.di.container import ServiceScope
        from uno.core.di.provider import ServiceLifecycle

        # Collect all registered services from base and extensions
        all_collections = [self._base_services, *list(self._extensions.values())]
        seen_types = set()
        for services in all_collections:
            # Access _registrations dict from ServiceCollection
            for service_type, registration in getattr(
                services, "_registrations", {}
            ).items():
                if (
                    isinstance(service_type, type)
                    and issubclass(service_type, ServiceLifecycle)
                    and service_type is not ServiceLifecycle
                ):
                    # Enforce singleton scope
                    if registration.scope != ServiceScope.SINGLETON:
                        raise TypeError(
                            f"Lifecycle service {service_type.__name__} must be registered as singleton, "
                            f"but has scope {registration.scope}."
                        )
                    # Auto-queue for lifecycle management if not already queued
                    if service_type not in self._lifecycle_queue:
                        self._lifecycle_queue.append(service_type)
                    seen_types.add(service_type)
        # Remove any stale entries from lifecycle queue
        self._lifecycle_queue = [t for t in self._lifecycle_queue if t in seen_types]

    def prewarm_singletons(self) -> None:
        """
        Eagerly instantiate all singleton services and cache them.
        Useful for performance-sensitive applications or to catch errors early.

        Call this after configuring all services and before application startup.
        """
        if hasattr(self, "_resolver") and self._resolver:
            self._resolver.prewarm_singletons()

    def is_initialized(self) -> bool:
        """
        Return True if the service provider has been initialized.
        """
        return self._initialized

    def configure_services(
        self, services: ServiceCollection
    ) -> Result[None, FrameworkError]:
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
        return Success(None)

    def register_extension(
        self, name: str, services: ServiceCollection
    ) -> Result[None, FrameworkError]:
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
        if name in self._extensions:
            return Failure(
                FrameworkError(
                    f"Extension '{name}' is already registered.",
                    "EXTENSION_ALREADY_REGISTERED",
                )
            )
        self._extensions[name] = services
        return Success(None)

    def register_lifecycle_service(self, service_type: type[ServiceLifecycle]) -> None:
        """
        Register a service that requires lifecycle management.
        Only singleton services can be registered as lifecycle services.

        Args:
            service_type: The service type to register

        Raises:
            NotImplementedError: If the service is not registered as a singleton
        """
        # Check if service is registered and is a singleton
        # Only allow singleton lifecycle services
        registration = (
            self._resolver._registrations.get(service_type)
            if hasattr(self, "_resolver")
            else None
        )
        if (
            registration is not None
            and getattr(registration, "scope", None) != ServiceScope.SINGLETON
        ):
            raise NotImplementedError(
                f"Lifecycle services must be registered as singletons. {service_type.__name__} is registered as {getattr(registration, 'scope', 'unknown')}."
            )
        self._lifecycle_queue.append(service_type)

    async def _integrate_extensions(self) -> None:
        """
        Integrate extensions into the main resolver.
        Called only by initialize().
        Async for future compatibility.
        """
        for name, services in self._extensions.items():
            self._logger.info(f"Initializing extension: {name}")
            # For each service in the extension, register it in the main resolver
            extension_resolver = services.build(resolver_class=ServiceResolver)
            for (
                service_type,
                registration,
            ) in extension_resolver._registrations.items():
                self._resolver.register(
                    service_type,
                    registration.implementation,
                    getattr(registration, "scope", None),
                    getattr(registration, "params", {}),
                )
            # Also copy over any instances
            if hasattr(extension_resolver, "_singletons"):
                for (
                    service_type,
                    instance,
                ) in extension_resolver._singletons.items():
                    self._resolver.register_instance(service_type, instance)
            self._logger.info(f"Initialized extension: {name}")

    async def _initialize_lifecycle_services(self) -> None:
        """
        Initialize lifecycle services.
        Called only by initialize().
        Async to support async service initialization.
        """
        if self._lifecycle_queue:
            self._logger.info(
                f"Initializing {len(self._lifecycle_queue)} lifecycle services"
            )

        for service_type in self._lifecycle_queue:
            registration = self._base_services._registrations.get(service_type)
            if registration is None:
                self._logger.warning(
                    f"Lifecycle service {service_type} is not registered; skipping."
                )
                continue

            if getattr(registration, "scope", None) != ServiceScope.SINGLETON:
                raise NotImplementedError(
                    f"Lifecycle service {service_type} must be registered as a singleton."
                )

            # Guarantee: Always resolve the actual singleton instance (Success.value)
            result = self._resolver.resolve(service_type)
            service = result.value if hasattr(result, "value") else result

            if hasattr(service, "initialize") and callable(service.initialize):
                await service.initialize()

            self._logger.debug(
                f"Initialized lifecycle service: {service_type.__name__}"
            )

    async def _dispose_lifecycle_services(self) -> None:
        """
        Dispose lifecycle services.
        Called only by shutdown().
        Async to support async service disposal.
        """
        if self._lifecycle_queue:
            # Make a reversed copy to avoid modifying the original
            reversed_queue = self._lifecycle_queue.copy()
            reversed_queue.reverse()

            self._logger.info(f"Disposing {len(reversed_queue)} lifecycle services")

            for service_type in reversed_queue:
                try:
                    # Get the service if it exists
                    result = self._resolver.resolve(service_type)
                    service = result.value if hasattr(result, "value") else result

                    await service.dispose()
                    self._logger.debug(
                        f"Disposed lifecycle service: {service_type.__name__}"
                    )
                except Exception as e:
                    self._logger.error(
                        f"Error disposing service {service_type.__name__}: {e!s}"
                    )

    async def initialize(self) -> None:
        """
        Initialize the service provider.

        This method initializes the container and all registered services.
        It should be called during application startup.

        Runs all configuration validation hooks registered in the base ServiceCollection before building the resolver.
        Raises if any validation fails.
        """
        if self._initialized:
            raise FrameworkError(
                "ServiceProvider has already been initialized.",
                "SERVICE_PROVIDER_ALREADY_INITIALIZED",
            )

        if self._initializing:
            # Prevent circular initialization
            self._logger.warning("Service initialization is already in progress")
            return

        self._initializing = True
        try:
            # Run configuration validation hooks before building resolver
            for validation_fn in getattr(self._base_services, "validation_hooks", []):
                try:
                    validation_fn(self._base_services)
                except Exception as e:
                    self._logger.error(
                        f"Service configuration validation failed: {e!s}"
                    )
                    raise

            # Modern DI: Build the resolver from the base services
            self._resolver = self._base_services.build(resolver_class=ServiceResolver)

            # Prewarm all singleton instances before initializing lifecycle services
            self._resolver.prewarm_singletons()

            await self._integrate_extensions()
            await self._initialize_lifecycle_services()

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

        await self._dispose_lifecycle_services()

        self._initialized = False
        self._logger.info("Service provider shut down")

    async def create_scope(self, scope_id: str | None = None):
        """
        Create a new async DI scope. Use as:
            async with provider.create_scope() as scope:
                ...
        Returns a Scope object that can resolve services within the scope.
        """
        from .scope import Scope

        return Scope(self, scope_id)

    def try_get_service(self, service_type: type[T]) -> Result[T, FrameworkError]:
        """
        Monad-based service resolution. Returns Success(instance) or Failure(error) instead of raising or setting .error attributes.
        Prefer this method for all new code and tests. Legacy code may use get_service.
        """
        if not self._initialized:
            return Failure(
                FrameworkError(
                    "Service provider is not initialized",
                    "SERVICE_PROVIDER_NOT_INITIALIZED",
                )
            )
        from .scope import Scope

        scope = Scope.get_current_scope()
        result = self._resolver.resolve(service_type, scope=scope)
        return result

    def get_service(self, service_type: type[T]) -> T:
        """
        Get a service by its type. Supports singleton, transient, and scoped lifetimes.

        If a scope is active and the service is SCOPED, resolves in the current scope.
        Otherwise, uses the default resolver.

        Args:
            service_type: The type of service to retrieve

        Returns:
            An instance of the requested service
        """
        if not self._initialized:
            from uno.core.errors.result import Failure

            return Failure(
                FrameworkError(
                    "Service provider is not initialized",
                    "SERVICE_PROVIDER_NOT_INITIALIZED",
                )
            )
        from .scope import Scope

        scope = Scope.get_current_scope()
        result = self._resolver.resolve(service_type, scope=scope)
        return result

    # All scope-related APIs and legacy logic have been removed.
    # ServiceProvider only exposes high-level APIs and delegates to ServiceResolver for resolution.

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

    def get_event_bus(self) -> "EventBusProtocol":
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


"""
uno.core.di.provider

Provides the ServiceProvider class and related helpers for dependency injection in Uno.
Manages service lifecycles, scopes, and global provider access for application and test contexts.
"""


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

    # Register GeneralConfig
    from uno.core.config.general import GeneralConfig

    services.add_singleton(GeneralConfig, GeneralConfig)

    # Register LoggerService as a singleton
    from uno.core.logging.logger import LoggerService

    services.add_singleton(LoggerService, implementation=LoggerService)

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
    db_provider = DatabaseProvider(
        connection_config, logger=logging.getLogger("uno.database")
    )
    services.add_instance(DatabaseProvider, db_provider)
    services.add_instance(DatabaseProviderProtocol, db_provider)

    # Register database manager
    from uno.database.db_manager import DBManager

    services.add_singleton(
        DBManagerProtocol,
        DBManager,
        connection_provider=db_provider.sync_connection,
        logger=logging.getLogger("uno.database"),
    )

    # Register SQL emitter factory
    from uno.sql.services import SQLEmitterFactoryService

    services.add_singleton(
        SQLEmitterFactoryProtocol,
        SQLEmitterFactoryService,
        config=UnoConfig(),
        logger=logging.getLogger("uno.sql"),
    )

    # Register SQL execution service
    from uno.sql.services import SQLExecutionService

    services.add_singleton(
        SQLExecutionProtocol, SQLExecutionService, logger=logging.getLogger("uno.sql")
    )

    # Register schema manager
    from uno.schema.services import DTOManagerService

    services.add_singleton(
        DTOManagerProtocol,
        DTOManagerService,
        logger=logging.getLogger("uno.schema"),
    )

    # Register event bus
    from uno.core.events.handlers import EventHandler

    # Import the concrete EventBus implementation only when needed
    # to avoid circular imports
    from uno.core.events.handlers import EventBus

    event_bus = EventBus(logger=logging.getLogger("uno.events"))
    services.add_instance(EventBus, event_bus)
    services.add_instance(EventBusProtocol, event_bus)

    # Register domain registry
    from uno.domain.factory import DomainRegistry

    services.add_singleton(
        DomainRegistry, DomainRegistry, logger=logging.getLogger("uno.domain")
    )

    # Configure the service provider
    provider.configure_services(services)

    # Initialize vector search components if available
    try:
        # Register vector search components
        from uno.core.di.vector_provider import configure_vector_services

        await configure_vector_services()
    except (ImportError, AttributeError) as e:
        logging.getLogger("uno.services").debug(
            f"Vector search provider not available: {e}"
        )
        pass

    # Register queries provider
    try:
        from uno.queries.domain_provider import get_queries_provider

        provider.register_extension("queries", get_queries_provider())
    except (ImportError, AttributeError) as e:
        logging.getLogger("uno.services").debug(f"Queries provider not available: {e}")
        pass

    # Register reports provider
    try:
        from uno.reports.domain_provider import get_reports_provider

        provider.register_extension("reports", get_reports_provider())
    except (ImportError, AttributeError) as e:
        logging.getLogger("uno.services").debug(f"Reports provider not available: {e}")
        pass
