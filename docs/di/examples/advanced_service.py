"""
Advanced service example for the Uno DI system.

This example demonstrates:
1. Service lifecycle management
2. Service events
3. Service versioning
4. Service composition
5. Service constraints
6. Service health monitoring
"""

from typing import Protocol, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uno.di.decorators import (
    service,
    singleton,
    ServiceLifecycle,
    ServiceEventType,
    ServiceEvent,
    ServiceEventHandler,
    ServiceEventEmitter,
    ServiceVersion,
    ServiceComposite,
    ServiceConstraint,
    ServiceConstraintValidator,
    ServiceHealth,
)
from uno.di.service_scope import ServiceScope
from uno.di.service_collection import ServiceCollection
from uno.di.service_provider import ServiceProvider
from uno.di.errors import ServiceConfigurationError


# Define interfaces
class IDatabaseService(Protocol):
    """Interface for database services."""

    async def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a query."""
        ...


class ICacheService(Protocol):
    """Interface for cache services."""

    async def get(self, key: str) -> Any:
        """Get a value from cache."""
        ...

    async def set(self, key: str, value: Any) -> None:
        """Set a value in cache."""
        ...


# Define service options
@dataclass
class DatabaseOptions:
    """Options for database service."""

    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 5
    timeout: int = 30

    def validate(self) -> None:
        """Validate database options."""
        if not self.host:
            raise ServiceConfigurationError("Database host is required")
        if self.port < 1 or self.port > 65535:
            raise ServiceConfigurationError("Invalid port number")
        if not self.database:
            raise ServiceConfigurationError("Database name is required")


# Define service constraints
class DatabaseConstraintValidator(ServiceConstraintValidator):
    """Validator for database service constraints."""

    def validate(self, service: Any) -> None:
        """Validate database service constraints."""
        if not hasattr(service, "query"):
            raise ServiceConfigurationError(
                "Database service must implement query method"
            )
        if not hasattr(service, "connection_pool"):
            raise ServiceConfigurationError(
                "Database service must have connection pool"
            )


# Implement services
@service(
    interface=IDatabaseService,
    scope=ServiceScope.SINGLETON,
    options_type=DatabaseOptions,
    version="1.0.0",
    constraints=[ServiceConstraint.REQUIRES_CONNECTION_POOL],
    constraint_validators=[DatabaseConstraintValidator()],
)
class DatabaseService(ServiceLifecycle, ServiceEventEmitter):
    """Database service implementation."""

    def __init__(self, options: DatabaseOptions):
        self.options = options
        self.connection_pool = []
        self._version = ServiceVersion("1.0.0")
        self._health = ServiceHealth(is_healthy=True)

    async def initialize(self) -> None:
        """Initialize the database service."""
        self.connection_pool = [
            f"Connection {i}" for i in range(self.options.pool_size)
        ]
        self.emit_event(
            ServiceEvent(
                type=ServiceEventType.INITIALIZED,
                data={"pool_size": len(self.connection_pool)},
            )
        )

    async def start(self) -> None:
        """Start the database service."""
        self.emit_event(
            ServiceEvent(
                type=ServiceEventType.STARTED,
                data={"timestamp": datetime.now().isoformat()},
            )
        )

    async def stop(self) -> None:
        """Stop the database service."""
        self.connection_pool.clear()
        self.emit_event(
            ServiceEvent(
                type=ServiceEventType.STOPPED,
                data={"timestamp": datetime.now().isoformat()},
            )
        )

    async def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a query."""
        self.emit_event(
            ServiceEvent(type=ServiceEventType.QUERY_EXECUTED, data={"sql": sql})
        )
        return [{"result": "dummy"}]

    def check_health(self) -> ServiceHealth:
        """Check service health."""
        self._health.is_healthy = len(self.connection_pool) > 0
        self._health.last_check = datetime.now()
        return self._health


@service(interface=ICacheService, scope=ServiceScope.SINGLETON, version="1.0.0")
class CacheService(ServiceLifecycle):
    """Cache service implementation."""

    def __init__(self):
        self.cache: dict[str, Any] = {}
        self._version = ServiceVersion("1.0.0")

    async def initialize(self) -> None:
        """Initialize the cache service."""
        self.cache.clear()

    async def get(self, key: str) -> Any:
        """Get a value from cache."""
        return self.cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        """Set a value in cache."""
        self.cache[key] = value


# Implement composite service
@service(
    interface=IDatabaseService, scope=ServiceScope.SINGLETON, composite=DatabaseService
)
class CachedDatabaseService(ServiceComposite):
    """Composite database service with caching."""

    def __init__(self, database: IDatabaseService, cache: ICacheService):
        self.database = database
        self.cache = cache

    async def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a query with caching."""
        # Try to get from cache first
        cache_key = f"query:{sql}"
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # If not in cache, execute query
        result = await self.database.query(sql)
        await self.cache.set(cache_key, result)
        return result


# Implement event handler
class DatabaseEventHandler(ServiceEventHandler):
    """Handler for database service events."""

    async def handle_event(self, event: ServiceEvent) -> None:
        """Handle a service event."""
        print(f"Database event: {event.type}")
        print(f"Event data: {event.data}")


def main() -> None:
    """Run the example."""
    # Create service collection
    services = ServiceCollection()

    # Register services
    services.add_singleton(IDatabaseService, CachedDatabaseService)
    services.add_singleton(ICacheService, CacheService)

    # Configure services
    services.configure[DatabaseOptions](
        lambda options: {
            "host": "localhost",
            "port": 5432,
            "database": "mydb",
            "username": "user",
            "password": "pass",
            "pool_size": 5,
            "timeout": 30,
        }
    )

    # Create service provider
    provider = ServiceProvider(services)

    # Register event handler
    database_service = provider.get_service(IDatabaseService)
    database_service.add_event_handler(DatabaseEventHandler())

    # Initialize services
    import asyncio

    asyncio.run(provider.initialize_services())

    # Use services
    async def run_queries():
        # Execute some queries
        result1 = await database_service.query("SELECT * FROM users")
        print(f"Query 1 result: {result1}")

        # This should use cache
        result2 = await database_service.query("SELECT * FROM users")
        print(f"Query 2 result: {result2}")

        # Check service health
        health = database_service.check_health()
        print(f"Service health: {health}")

    asyncio.run(run_queries())


if __name__ == "__main__":
    main()
