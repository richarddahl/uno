"""PostgreSQL repository implementation."""

from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar, cast
from uuid import UUID

import asyncpg
from pydantic import BaseModel

from uno.domain.aggregate import AggregateRoot
from uno.domain.repository import BaseRepository
from uno.logging import LoggerProtocol, get_logger
from uno.uow.errors import ConcurrencyError, SerializationError

A = TypeVar("A", bound=AggregateRoot[Any])


class PostgresRepository(BaseRepository[A, UUID], Generic[A]):
    """PostgreSQL implementation of the repository pattern.

    This repository uses PostgreSQL as the underlying storage and supports:
    - JSONB for flexible schema
    - Optimistic concurrency control
    - Connection pooling
    - Automatic schema validation
    """

    def __init__(
        self,
        aggregate_type: Type[A],
        pool: asyncpg.Pool,
        table_name: str | None = None,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """Initialize the PostgreSQL repository.

        Args:
            aggregate_type: The aggregate class this repository manages
            pool: AsyncPG connection pool
            table_name: Optional custom table name (defaults to aggregate type name)
            logger: Logger instance (optional)
        """
        super().__init__(logger=logger)
        self._aggregate_type = aggregate_type
        self._pool = pool
        self._table_name = table_name or aggregate_type.__name__.lower()
        self._ensure_table_initialized = False

    async def _ensure_table(self) -> None:
        """Ensure the table exists and has the correct schema."""
        if self._ensure_table_initialized:
            return

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    id UUID PRIMARY KEY,
                    version BIGINT NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT {self._table_name}_version_check 
                        CHECK (version >= 0)
                )
                """
            )
            
            # Create index on ID if it doesn't exist
            await conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS 
                    idx_{self._table_name}_id 
                ON {self._table_name} (id)
                """
            )
            
            # Create update trigger for updated_at
            await conn.execute(
                f"""
                CREATE OR REPLACE FUNCTION update_{self._table_name}_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
            
            await conn.execute(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger 
                        WHERE tgname = 'update_{self._table_name}_updated_at_trigger'
                    ) THEN
                        CREATE TRIGGER update_{self._table_name}_updated_at_trigger
                        BEFORE UPDATE ON {self._table_name}
                        FOR EACH ROW EXECUTE FUNCTION update_{self._table_name}_updated_at();
                    END IF;
                END $$;
                """
            )
            
        self._ensure_table_initialized = True

    async def get(self, id: UUID) -> A | None:
        """Get an aggregate by ID.
        
        Args:
            id: The ID of the aggregate to retrieve
            
        Returns:
            The aggregate if found, None otherwise
            
        Raises:
            SerializationError: If there's an error deserializing the aggregate
            RuntimeError: If there's an error accessing the database
        """
        await self._ensure_table()
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT data, version 
                FROM {self._table_name} 
                WHERE id = $1
                """,
                id,
            )
            
            if not row:
                return None
                
            try:
                # Create aggregate instance from JSON data
                data = dict(row["data"])
                aggregate = self._aggregate_type.model_validate(data)
                
                # Set the version
                if hasattr(aggregate, "_version"):
                    setattr(aggregate, "_version", row["version"])
                    
                return aggregate
                
            except Exception as e:
                self._logger.error(
                    "Error deserializing aggregate %s: %s", id, e, exc_info=True
                )
                raise SerializationError(f"Failed to deserialize aggregate {id}") from e

    async def add(self, entity: A) -> None:
        """Add a new aggregate.
        
        Args:
            entity: The aggregate to add
            
        Raises:
            ConcurrencyError: If an aggregate with the same ID already exists
            SerializationError: If there's an error serializing the aggregate
            RuntimeError: If there's an error accessing the database
        """
        await self._ensure_table()
        
        try:
            # Convert aggregate to dict for storage
            data = entity.model_dump()
            version = getattr(entity, "_version", 0)
            
            async with self._pool.acquire() as conn:
                await conn.execute(
                    f"""
                    INSERT INTO {self._table_name} (id, version, data)
                    VALUES ($1, $2, $3)
                    """,
                    entity.id,
                    version,
                    data,
                )
                
        except asyncpg.UniqueViolationError as e:
            raise ConcurrencyError(
                f"Aggregate {entity.id} already exists"
            ) from e
        except Exception as e:
            self._logger.error(
                "Error adding aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise RuntimeError(f"Failed to add aggregate {entity.id}") from e

    async def update(self, entity: A) -> None:
        """Update an existing aggregate.
        
        Args:
            entity: The aggregate to update
            
        Raises:
            ConcurrencyError: If the aggregate doesn't exist or version mismatch
            SerializationError: If there's an error serializing the aggregate
            RuntimeError: If there's an error accessing the database
        """
        await self._ensure_table()
        
        try:
            # Convert aggregate to dict for storage
            data = entity.model_dump()
            current_version = getattr(entity, "_version", 0)
            new_version = current_version + 1
            
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {self._table_name}
                    SET data = $1, version = $2
                    WHERE id = $3 AND version = $4
                    RETURNING id
                    """,
                    data,
                    new_version,
                    entity.id,
                    current_version,
                )
                
                if result == "UPDATE 0":
                    # Check if aggregate exists
                    exists = await conn.fetchval(
                        f"SELECT 1 FROM {self._table_name} WHERE id = $1",
                        entity.id,
                    )
                    
                    if not exists:
                        raise ConcurrencyError(f"Aggregate {entity.id} does not exist")
                    else:
                        raise ConcurrencyError(
                            f"Concurrent modification of aggregate {entity.id} detected"
                        )
                        
                # Update the version on the entity
                if hasattr(entity, "_version"):
                    setattr(entity, "_version", new_version)
                    
        except Exception as e:
            self._logger.error(
                "Error updating aggregate %s: %s", entity.id, e, exc_info=True
            )
            if not isinstance(e, ConcurrencyError):
                raise RuntimeError(f"Failed to update aggregate {entity.id}") from e
            raise

    async def remove(self, entity: A) -> None:
        """Remove an aggregate from the repository.
        
        Args:
            entity: The aggregate to remove
            
        Raises:
            RuntimeError: If there's an error accessing the database
        """
        await self._ensure_table()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    DELETE FROM {self._table_name}
                    WHERE id = $1
                    RETURNING id
                    """,
                    entity.id,
                )
                
                if result == "DELETE 0":
                    self._logger.warning(
                        "Attempted to delete non-existent aggregate %s", entity.id
                    )
                    
        except Exception as e:
            self._logger.error(
                "Error deleting aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise RuntimeError(f"Failed to delete aggregate {entity.id}") from e
