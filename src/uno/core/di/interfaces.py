# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Protocol definitions for dependency injection.

This module defines Protocol classes that provide interfaces for
various components in the  framework, enabling dependency injection
and improved testability.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractContextManager
from typing import (
    Any,
    Protocol,
    TypeVar,
    runtime_checkable,
    Generic,
)

import asyncpg
import psycopg
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")
ModelT = TypeVar("ModelT")
SQLEmitterT = TypeVar("SQLEmitterT")
EntityT = TypeVar("EntityT")
EventT = TypeVar("EventT")
VectorT = TypeVar("VectorT")
QueryT = TypeVar("QueryT")
ResultT = TypeVar("ResultT")


@runtime_checkable
class ConfigProtocol(Protocol):
    """Protocol for configuration providers."""

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        ...

    def all(self) -> dict[str, Any]:
        """Get all configuration values."""
        ...


@runtime_checkable
class RepositoryProtocol(Protocol, Generic[ModelT]):
    """Protocol for data repositories (async)."""

    async def get(self, id: str) -> ModelT | None:
        """Get an entity by ID."""
        ...
    async def list(
        self,
        filters: dict[str, Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        """List entities with optional filters, ordering, and pagination."""
        ...
    async def create(self, data: dict[str, Any]) -> ModelT:
        """Create a new entity."""
        ...
    async def update(self, id: str, data: dict[str, Any]) -> ModelT | None:
        """Update an entity by ID."""
        ...
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        ...
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching optional filters."""
        ...


class DatabaseProviderProtocol(Protocol):
    """Protocol for database providers (mixed async/sync)."""

    def async_session(self) -> AsyncIterator[AsyncSession]:
        ...
    def sync_session(self) -> AbstractContextManager[Any]:
        ...
    def async_connection(self) -> AsyncIterator[asyncpg.Connection]:
        ...
    def sync_connection(self) -> AbstractContextManager[psycopg.Connection]:
        ...
    async def health_check(self) -> bool:
        ...
    async def close(self) -> None:
        ...


class DBManagerProtocol(Protocol):
    """Protocol for database managers (sync)."""

    def execute_ddl(self, ddl: str) -> None:
        ...
    def execute_script(self, script: str) -> None:
        ...
    def execute_from_emitter(self, emitter: Any) -> None:
        ...
    def execute_from_emitters(self, emitters: list[Any]) -> None:
        ...
    def create_schema(self, schema_name: str) -> None:
        ...
    def drop_schema(self, schema_name: str, cascade: bool = False) -> None:
        ...
    def create_extension(self, extension_name: str, schema: str | None = None) -> None:
        ...
    def table_exists(self, table_name: str, schema: str | None = None) -> bool:
        ...
    def function_exists(self, function_name: str, schema: str | None = None) -> bool:
        ...

    def type_exists(self, type_name: str, schema: str | None = None) -> bool:
        """Check if type exists."""
        ...

    def trigger_exists(
        self, trigger_name: str, table_name: str, schema: str | None = None
    ) -> bool:
        """Check if trigger exists."""
        ...

    def policy_exists(
        self, policy_name: str, table_name: str, schema: str | None = None
    ) -> bool:
        """Check if policy exists."""
        ...


class ServiceProtocol(Protocol, Generic[T]):
    """Protocol for service classes."""

    async def execute(self, *args, **kwargs) -> T:
        """Execute the service operation."""
        ...


class SQLEmitterFactoryProtocol(Protocol):
    """Protocol for SQL emitter factory services."""

    def register_emitter(self, name: str, emitter_class: type[Any]) -> None:
        """Register an SQL emitter class with the factory."""
        ...

    def get_emitter(self, name: str, **kwargs) -> Any:
        """Create a new instance of a registered SQL emitter."""
        ...

    def create_emitter_instance(self, emitter_class: type[Any], **kwargs) -> Any:
        """Create a new emitter instance from a class."""
        ...

    def register_core_emitters(self) -> None:
        """Register all core SQL emitters with the factory."""
        ...


class SQLExecutionProtocol(Protocol):
    """Protocol for SQL execution services."""

    def execute_ddl(self, ddl: str) -> None:
        """Execute a DDL statement."""
        ...

    def execute_script(self, script: str) -> None:
        """Execute a SQL script."""
        ...

    def execute_emitter(self, emitter: Any, dry_run: bool = False) -> list[Any]:
        """Execute an SQL emitter."""
        ...


class DTOManagerProtocol(Protocol):
    """Protocol for schema manager services."""

    def add_schema_config(self, name: str, config: Any) -> None:
        """Add a schema configuration."""
        ...

    def create_schema(self, schema_name: str, model: type[Any]) -> Any:
        """Create a schema for a model."""
        ...

    def create_all_schemas(self, model: type[Any]) -> dict[str, Any]:
        """Create all schemas for a model."""
        ...

    def get_schema(self, schema_name: str) -> Any | None:
        """Get a schema by name."""
        ...

    def register_standard_configs(self) -> None:
        """Register standard schema configurations."""
        ...

    def create_standard_schemas(self, model: type[Any]) -> dict[str, Any]:
        """Create standard schemas for a model."""
        ...


class DomainRepositoryProtocol(Protocol, Generic[EntityT]):
    """Protocol for domain repositories."""

    async def get(self, id: str) -> EntityT | None:
        """Get an entity by ID."""
        ...

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EntityT]:
        """list entities with filtering, ordering, and pagination."""
        ...

    async def add(self, entity: EntityT) -> EntityT:
        """Add a new entity."""
        ...

    async def update(self, entity: EntityT) -> EntityT:
        """Update an existing entity."""
        ...

    async def remove(self, entity: EntityT) -> None:
        """Remove an entity."""
        ...

    async def remove_by_id(self, id: str) -> bool:
        """Remove an entity by ID."""
        ...

    async def exists(self, id: str) -> bool:
        """Check if an entity exists."""
        ...

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching filters."""
        ...


@runtime_checkable
class DomainServiceProtocol(Protocol, Generic[EntityT]):
    """Protocol for domain services."""

    async def get_by_id(self, id: str) -> EntityT | None:
        """Get an entity by ID."""
        ...

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EntityT]:
        """list entities with filtering, ordering, and pagination."""
        ...

    async def save(self, entity: EntityT) -> EntityT | None:
        """Save an entity (create or update)."""
        ...

    async def delete(self, entity: EntityT) -> bool:
        """Delete an entity."""
        ...

    async def delete_by_id(self, id: str) -> bool:
        """Delete an entity by ID."""
        ...


class EventBusProtocol(Protocol):
    """Protocol for event buses (async publish, sync subscribe)."""

    async def publish(self, event: Any) -> None:
        ...
    async def publish_all(self, events: list[Any]) -> None:
        ...
    def subscribe(self, event_type: type[Any], handler: Any) -> None:
        ...
    def subscribe_all(self, handler: Any) -> None:
        ...
    def unsubscribe(self, event_type: type[Any], handler: Any) -> None:
        ...
    def unsubscribe_all(self, handler: Any) -> None:
        ...
