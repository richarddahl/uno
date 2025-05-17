# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.postgresql
PostgreSQL event store implementation for Uno framework
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, TypeVar, Sequence, Callable
from uuid import UUID

import asyncpg

from uno.persistence.event_store.subscription import SubscriptionManager

from uno.domain.events import DomainEvent
from uno.event_store.errors import (
    EventStoreError,
    EventStoreConnectError,
    EventStoreAppendError,
    EventStoreGetEventsError,
    EventStoreReplayError,
    EventStoreVersionConflict,
)
from uno.event_store.base import EventStore
from uno.event_store.config import EventStoreSettings, default_settings
from uno.injection import ContainerProtocol
from uno.logging import LoggerProtocol, get_logger

# Type variable for events
E = TypeVar("E", bound=DomainEvent)

# Type aliases
JSONType = dict[str, Any]
EventData = tuple[
    UUID, str, int, str, str, str, str, datetime, JSONType
]  # Format of event data from DB


class PostgreSQLEventStore(EventStore[E]):
    """PostgreSQL-based event store implementation.

    This implementation uses PostgreSQL as the underlying storage for events.
    It supports both regular event storage and vector search capabilities.
    """

    def __init__(
        self,
        container: ContainerProtocol,
        settings: EventStoreSettings | None = None,
        logger: LoggerProtocol | None = None,
        **pool_kwargs: Any,
    ) -> None:
        """Initialize the PostgreSQL event store.

        Args:
            container: The dependency injection container.
            settings: Optional settings instance. Defaults will be used if not provided.
            logger: Optional logger instance. A default one will be created if not provided.
            **pool_kwargs: Additional keyword arguments for the connection pool.
        """
        self._settings = settings or default_settings
        self._logger = logger or get_logger("uno.persistence.event_store")
        self._container = container

        # Initialize connection parameters
        self._dsn = self._settings.postgres_dsn
        self._pool_min_size = self._settings.postgres_pool_min_size
        self._pool_max_size = self._settings.postgres_pool_max_size
        self._enable_vector_search = self._settings.postgres_enable_vector_search
        self._vector_dimensions = self._settings.postgres_vector_dimensions

        if not self._dsn:
            raise ValueError("PostgreSQL DSN is required")

        self._pool: asyncpg.Pool | None = None
        self._pool_kwargs = pool_kwargs
        self._vector_extension_available = False
        self._subscription_manager: SubscriptionManager | None = None

        # Initialize connection pool
        self._init_pool()

    @property
    def settings(self) -> EventStoreSettings:
        """Get the event store settings."""
        return self._settings

    @property
    def logger(self) -> LoggerProtocol:
        """Get the logger instance."""
        return self._logger

    def _init_pool(self) -> None:
        """Initialize the connection pool with proper configuration."""
        self._pool_kwargs.update(
            {
                "min_size": self._pool_min_size,
                "max_size": self._pool_max_size,
                "statement_cache_size": 0,  # Disable statement cache for now
                "server_settings": {
                    "application_name": "uno-event-store",
                    "search_path": "public",
                },
            }
        )

    async def connect(self) -> None:
        """Connect to the PostgreSQL database and create tables if they don't exist."""
        if self._pool is not None:
            return

        self.logger.info(
            "Connecting to PostgreSQL event store",
            extra={
                "dsn": self._obfuscate_dsn(self._dsn),
                "pool_min_size": self._pool_min_size,
                "pool_max_size": self._pool_max_size,
                "vector_search_enabled": self._enable_vector_search,
            },
        )

        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(dsn=self._dsn, **self._pool_kwargs)

            # Set up schema and extensions
            async with self._pool.acquire() as conn:
                if self._enable_vector_search:
                    await self._setup_vector_extension(conn)
                await self._create_tables(conn)
                await self._create_indexes(conn)

            # Initialize subscription manager
            self._subscription_manager = SubscriptionManager(self._pool)

            self.logger.info(
                "Successfully connected to PostgreSQL event store",
                extra={
                    "dsn": self._obfuscate_dsn(self._dsn),
                    "server_version": await self._get_server_version(),
                },
            )

        except Exception as exc:
            error_msg = f"Failed to connect to PostgreSQL: {exc}"
            self.logger.error(error_msg, exc_info=exc)
            raise EventStoreConnectError(error_msg) from exc

    async def _get_server_version(self) -> str:
        """Get the PostgreSQL server version."""
        if self._pool is None:
            return "not connected"

        try:
            async with self._pool.acquire() as conn:
                return await conn.fetchval("SELECT version()")
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("Failed to get server version", exc_info=exc)
            return "unknown"

    @staticmethod
    def _obfuscate_dsn(dsn: str) -> str:
        """Obfuscate sensitive information in DSN for logging."""
        if not dsn:
            return ""

        try:
            # Simple obfuscation - replace password with ****
            if "password=" in dsn:
                parts = dsn.split(" ")
                for i, part in enumerate(parts):
                    if part.startswith("password="):
                        parts[i] = "password=****"
                return " ".join(parts)
            return dsn
        except Exception as e:
            return f"[obfuscated]: {str(e)}"

    async def _setup_vector_extension(self, conn: asyncpg.Connection) -> None:
        """Set up the pgvector extension if not already enabled."""
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            self._vector_extension_available = True
            self.logger.info("pgvector extension is available")
        except Exception as exc:
            self.logger.warning(
                "Could not enable pgvector extension. Vector search will be disabled",
                exc_info=exc,
            )
            self._vector_extension_available = False

    async def _create_tables(self, conn: asyncpg.Connection) -> None:
        """Create event store tables if they don't exist."""
        try:
            # Create events table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id UUID PRIMARY KEY,
                    aggregate_id UUID NOT NULL,
                    version INTEGER NOT NULL,
                    event_type VARCHAR(255) NOT NULL,
                    data JSONB NOT NULL,
                    metadata JSONB NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    correlation_id UUID,
                    causation_id UUID,
                    embedding VECTOR(%s) NULL,
                    
                    CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, version)
                )
            """,
                self._vector_dimensions if self._enable_vector_search else 1,
            )

            # Create snapshots table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    aggregate_id UUID PRIMARY KEY,
                    version INTEGER NOT NULL,
                    data JSONB NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            """
            )

            # Create aggregates table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS aggregates (
                    id UUID PRIMARY KEY,
                    version INTEGER NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """
            )

            self.logger.debug("Event store tables created or verified")

        except Exception as exc:
            error_msg = "Failed to create event store tables"
            self.logger.error(error_msg, exc_info=exc)
            raise EventStoreError(error_msg) from exc

    async def _create_indexes(self, conn: asyncpg.Connection) -> None:
        """Create necessary indexes for better query performance."""
        try:
            # Basic indexes for common query patterns
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_aggregate_id ON events (aggregate_id);
                CREATE INDEX IF NOT EXISTS idx_events_aggregate_version ON events (aggregate_id, version);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type);
            """
            )

            # Add index for vector search if enabled
            if self._enable_vector_search and self._vector_extension_available:
                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_embedding ON events 
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                """
                )
            self._logger.debug("Created indexes for events table")
        except Exception as e:
            self._logger.error(
                "Failed to create indexes", exc_info=True, extra={"error": str(e)}
            )
            raise

    @asynccontextmanager
    async def _get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Get a connection from the pool.

        Yields:
            A database connection from the pool.

        Raises:
            EventStoreError: If the connection cannot be established.
        """
        if self._pool is None:
            await self.connect()

        if self._pool is None:
            raise EventStoreError("Failed to establish database connection")

        conn = await self._pool.acquire()
        try:
            async with conn.transaction():
                yield conn
        except Exception as exc:
            self._logger.error("Database operation failed", exc_info=exc)
            raise EventStoreError("Database operation failed") from exc
        finally:
            if self._pool:  # Check if pool still exists
                await self._pool.release(conn)

    async def close(self) -> None:
        """Close the event store and release resources."""
        if self._subscription_manager:
            await self._subscription_manager.close()
            self._subscription_manager = None

        if self._pool:
            await self._pool.close()
            self._pool = None

        self.logger.info("Closed PostgreSQL event store connection")

    async def disconnect(self) -> None:
        """Alias for close() for interface compatibility."""
        await self.close()

    async def subscribe(
        self,
        channel: str,
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Subscribe to a channel to receive event notifications.

        Args:
            channel: The channel to subscribe to.
            handler: Callback function to handle incoming events.

        Raises:
            EventStoreError: If the subscription fails.
        """
        if not self._subscription_manager:
            raise EventStoreError("Not connected to PostgreSQL")

        await self._subscription_manager.subscribe(channel, handler)
        self.logger.debug("Subscribed to channel: %s", channel)

    async def unsubscribe(
        self,
        channel: str,
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Unsubscribe a handler from a channel.

        Args:
            channel: The channel to unsubscribe from.
            handler: The handler to remove.
        """
        if not self._subscription_manager:
            return

        await self._subscription_manager.unsubscribe(channel, handler)
        self.logger.debug("Unsubscribed from channel: %s", channel)

    async def _notify_event(self, event: DomainEvent) -> None:
        """Notify subscribers about a new event.

        Args:
            event: The event to notify about.
        """
        if not self._pool:
            return

        try:
            # Notify on both the global and aggregate-specific channels
            global_channel = "events:all"
            aggregate_channel = f"events:aggregate:{event.aggregate_id}"

            async with self._pool.acquire() as conn:
                # Convert event to JSON string
                event_json = event.model_dump_json()

                # Notify on both channels
                await conn.execute(
                    "SELECT pg_notify($1, $2), pg_notify($3, $2)",
                    global_channel,
                    event_json,
                    aggregate_channel,
                )

        except Exception as e:
            self.logger.error(
                "Failed to send notification for event %s: %s",
                event.event_id,
                str(e),
                exc_info=True,
            )

    async def append(
        self,
        aggregate_id: str,
        events: list[E],
        expected_version: int | None = None,
    ) -> None:
        """Append events to the event store.

        Args:
            aggregate_id: The ID of the aggregate to append events to
            events: The sequence of events to append
            expected_version: The expected version of the aggregate.
                If provided, the operation will fail if the current version does not match.

        Raises:
            EventStoreAppendError: If appending the events fails
            EventStoreError: If there is an error appending the events
            EventStoreVersionConflict: If there is a version conflict
        """
        # Import here to avoid circular imports
        from uno.event_store.errors import (
            EventStoreAppendError,
            EventStoreError,
            EventStoreVersionConflict,
        )

        if not events:
            return

        try:
            async with self._get_connection() as connection:
                # Get current version
                row = await connection.fetchrow(
                    "SELECT MAX(version) FROM events WHERE aggregate_id = $1",
                    str(aggregate_id),  # Convert UUID to string for query
                )
                current_version = row[0] if row and row[0] is not None else 0

                # Check for version conflict
                if expected_version is not None and current_version != expected_version:
                    raise EventStoreVersionConflict(
                        f"Version conflict: expected {expected_version}, got {current_version}",
                        context={
                            "aggregate_id": aggregate_id,
                            "expected_version": expected_version,
                            "current_version": current_version,
                        },
                    )

                # Insert events
                async with connection.transaction() as tx:
                    for event in events:
                        event_data = event.model_dump()
                        await tx.execute(
                            """
                            INSERT INTO events (
                                event_id, aggregate_id, version, event_type, 
                                event_data, metadata, correlation_id, timestamp
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            """,
                            event.event_id,
                            aggregate_id,
                            current_version + 1,
                            event.__class__.__name__,
                            event_data,
                            {},
                            None,
                            datetime.now(timezone.utc),
                        )
                        current_version += 1

                        # Notify about the new event
                        await tx.execute(
                            "SELECT pg_notify($1, $2)",
                            f"events:aggregate:{aggregate_id}",
                            json.dumps(event_data),
                        )

                    # Update the aggregate version
                    await tx.execute(
                        """
                        INSERT INTO aggregates (id, version, updated_at)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) DO UPDATE 
                        SET version = EXCLUDED.version, updated_at = EXCLUDED.updated_at
                        """,
                        aggregate_id,
                        current_version
                        - 1,  # version was incremented after the last event
                        datetime.now(timezone.utc),
                    )

                    # Notify about the batch of events
                    for event in events:
                        await self._notify_event(event)

                    await tx.commit()

        except Exception as exc:
            if isinstance(exc, EventStoreVersionConflict):
                raise

            error_msg = (
                f"Failed to append events for aggregate {aggregate_id}: {str(exc)}"
            )
            self._logger.error(error_msg, exc_info=exc)
            raise EventStoreAppendError(
                error_msg,
                context={
                    "aggregate_id": str(aggregate_id),
                    "events_count": len(events),
                    "error": str(exc),
                },
            ) from exc

    async def _replay_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Replay events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate to replay events for.
            from_version: The starting version to replay from (inclusive).
            to_version: The ending version to replay to (inclusive).

        Yields:
            The replayed events in order.

        Raises:
            EventStoreError: If there is an error replaying events.
        """
        if self._pool is None:
            raise EventStoreError("Event store is not connected")

        query = """
            SELECT event_id, event_type, timestamp, version, metadata, event_data
            FROM events 
            WHERE aggregate_id = $1::uuid AND version >= $2
        """
        # Use Union[str, int] for params since we're mixing string and integer parameters
        params: list[str | int] = [str(aggregate_id), from_version]

        if to_version is not None:
            query += " AND version <= $3"
            params.append(to_version)

        query += " ORDER BY version ASC"

        try:
            async with self._get_connection() as connection:
                rows = await connection.fetch(query, *params)

                for row in rows:
                    try:
                        # Extract and validate required fields
                        event_id = UUID(str(row["event_id"]))
                        event_type = str(row["event_type"])
                        version = int(row["version"])
                        timestamp = row["timestamp"]

                        # Safely get metadata with default empty dict
                        metadata_raw = row.get("metadata")
                        if metadata_raw and isinstance(metadata_raw, dict):
                            metadata = dict(metadata_raw)
                        else:
                            metadata = {}

                        # Get event data
                        state_data = row["event_data"]

                        # Resolve event class
                        event_class = self._resolve_event_type(event_type)
                        if event_class is None:
                            self._logger.warning("Unknown event type: %s", event_type)
                            continue

                        # Create and yield the event
                        event = event_class(
                            event_id=event_id,
                            event_type=event_type,
                            occurred_on=timestamp,
                            version=version,
                            aggregate_version=version,  # Assuming aggregate_version should match version for now
                            metadata=metadata,
                            state=state_data,  # Changed from state_data to state to match DomainEvent
                        )
                        # Safe to yield since we've verified the type
                        yield event  # type: ignore[misc]  # E is a type var with DomainEvent bound

                    except (KeyError, ValueError, TypeError) as e:
                        self._logger.error(
                            "Failed to create event from row data: %s",
                            dict(row) if hasattr(row, "_asdict") else str(row),
                            exc_info=True,
                        )
                        raise EventStoreError(
                            f"Invalid event data for aggregate {aggregate_id}",
                            context={
                                "event_type": (
                                    event_type
                                    if "event_type" in locals()
                                    else "unknown"
                                ),
                                "error": str(e),
                            },
                        ) from e

        except Exception as exc:
            self._logger.exception(
                "Error replaying events for aggregate %s (from_version=%s, to_version=%s)",
                aggregate_id,
                from_version,
                to_version,
            )
            raise EventStoreError(
                f"Failed to replay events for aggregate {aggregate_id}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(exc),
                },
            ) from exc

    def _resolve_event_type(self, event_type: str) -> type[DomainEvent] | None:
        """Resolve an event type string to a DomainEvent class.

        Args:
            event_type: The event type string to resolve

        Returns:
            The DomainEvent class or None if not found
        """
        try:
            # Get the event class from the container using the appropriate method
            # The container might use resolve(), provide(), get_type(), or some other method
            # Adjust based on your container's actual interface
            event_class: Any = None
            try:
                # Try different potential methods on the container
                if hasattr(self._container, "resolve"):
                    event_class = self._container.resolve(event_type)
                elif hasattr(self._container, "get_type"):
                    event_class = self._container.get_type(event_type)
                elif hasattr(self._container, "provide"):
                    event_class = self._container.provide(event_type)
                elif hasattr(self._container, "get"):
                    # Unsafe from a type checking perspective, but might work at runtime
                    event_class = self._container.get(event_type)  # type: ignore
                else:
                    self._logger.error(
                        "Container doesn't have a method to resolve types: %s",
                        event_type,
                    )
                    return None
            except Exception as container_ex:
                self._logger.debug(
                    "Container couldn't resolve type %s: %s",
                    event_type,
                    str(container_ex),
                    exc_info=True,
                )
                return None

            # Check if it's a type and a DomainEvent subclass
            if not isinstance(event_class, type):
                return None

            # Skip if it's not a DomainEvent or is the base DomainEvent class
            if not issubclass(event_class, DomainEvent) or event_class is DomainEvent:
                return None

            # We've verified it's a concrete DomainEvent subclass
            # The cast is safe because we've verified the type at runtime
            return event_class

        except Exception as e:
            self._logger.debug(
                "Failed to resolve event type %s: %s", event_type, str(e), exc_info=True
            )
            return None

    def _create_event_from_row(self, row: Any) -> E | None:
        """Create a DomainEvent instance from a database row.

        Args:
            row: The database row containing event data

        Returns:
            A DomainEvent instance or None if the event type is unknown

        Raises:
            KeyError: If required fields are missing
        """
        try:
            event_data = json.loads(row["event_data"])
            event_type = row["event_type"]

            # Get the event class from the registry
            event_class = self._resolve_event_type(event_type)
            if not event_class:
                self._logger.warning(
                    "No event class registered for type: %s",
                    event_type,
                    extra={"event_type": event_type},
                )
                return None

            # Create and return the event instance
            event = event_class(
                event_id=row["event_id"],
                event_type=event_type,
                occurred_on=row["timestamp"],
                version=row["version"],
                aggregate_version=row["aggregate_version"],
                state=event_data.get("state"),
                metadata=row["metadata"] or {},
            )
            # Safe to cast since we've verified the type at runtime
            # The cast is safe because we've verified the type matches E_co
            return event  # type: ignore[return-value]

        except Exception as e:
            self._logger.error(
                "Failed to create event from row: %s",
                str(e),
                exc_info=True,
                extra={
                    "event_type": event_type if "event_type" in locals() else "unknown",
                    "row": dict(row) if hasattr(row, "_asdict") else str(row),
                },
            )
            return None

    async def search_events_by_vector(
        self,
        query_embedding: Sequence[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[E]:
        """Search for events using vector similarity.

        Args:
            query_embedding: The query vector to compare against
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            filter_conditions: Additional filter conditions as {field: value} pairs

        Returns:
            List of matching events ordered by similarity

        Raises:
            ValueError: If vector search is not enabled
            EventStoreError: If there is an error executing the search
        """
        if not self._vector_extension_available:
            raise ValueError(
                "Vector search is not enabled or pgvector extension is not available"
            )

        if self._pool is None:
            raise EventStoreError("Event store is not connected")

        try:
            # Build the base query
            query = """
                SELECT event_id, event_type, timestamp, version, metadata, event_data,
                       (1 - (embedding <=> $1::vector)) as similarity
                FROM events
                WHERE (1 - (embedding <=> $1::vector)) >= $2
            """

            params: list[Any] = [query_embedding, similarity_threshold]
            param_count = 2

            # Add filter conditions if provided
            if filter_conditions:
                for field, value in filter_conditions.items():
                    param_count += 1
                    query += f" AND {field} = ${param_count}"
                    params.append(value)

            # Add ordering and limit
            query += " ORDER BY similarity DESC"
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)

            # Execute the query
            results: list[E] = []
            async with self._get_connection() as conn:
                rows = await conn.fetch(query, *params)

                for row in rows:
                    try:
                        event = self._create_event_from_row(row)
                        if event is not None:
                            # Add similarity score to metadata
                            if not hasattr(event, "metadata"):
                                event.metadata = {}
                            event.metadata["_similarity"] = row["similarity"]
                            results.append(event)

                    except (KeyError, ValueError, TypeError) as e:
                        self._logger.error(
                            "Failed to create event from row data: %s",
                            dict(row) if hasattr(row, "_asdict") else str(row),
                            exc_info=True,
                        )
                        continue  # Skip invalid events but continue with the rest

            return results

        except Exception as exc:
            self._logger.exception(
                "Error searching events by vector similarity (limit=%s, threshold=%s)",
                limit,
                similarity_threshold,
            )
            raise EventStoreError(
                "Failed to search events by vector similarity",
                context={
                    "limit": limit,
                    "similarity_threshold": similarity_threshold,
                    "error": str(exc),
                },
            ) from exc

    # Performance Optimization Methods

    async def vacuum(self, full: bool = False, analyze: bool = True) -> None:
        """Run VACUUM on the events table to optimize storage.

        Args:
            full: If True, perform a full VACUUM (locks the table)
            analyze: If True, update statistics for the query planner
        """
        if self._pool is None:
            raise EventStoreError("Event store is not connected")

        try:
            async with self._pool.acquire() as conn:
                if full:
                    await conn.execute("VACUUM FULL events")
                if analyze:
                    await conn.execute("ANALYZE events")
        except Exception as e:
            self.logger.error("Error during VACUUM/ANALYZE", exc_info=True)
            raise EventStoreError(f"Failed to optimize table: {str(e)}")

    async def get_metrics(self) -> dict[str, Any]:
        """Get database and table metrics."""
        metrics = {
            "event_count": 0,
            "aggregate_count": 0,
            "table_size_mb": 0,
            "indexes_size_mb": 0,
            "vector_search_enabled": self._vector_extension_available,
        }

        if self._pool is None:
            raise EventStoreError("Event store is not connected")

        try:
            async with self._pool.acquire() as conn:
                # Get event count
                row = await conn.fetchrow("SELECT COUNT(*) FROM events")
                metrics["event_count"] = row[0] if row else 0

                # Get unique aggregate count
                row = await conn.fetchrow(
                    "SELECT COUNT(DISTINCT aggregate_id) FROM events"
                )
                metrics["aggregate_count"] = row[0] if row else 0

                # Get table size
                row = await conn.fetchrow(
                    """
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('events')),
                        pg_size_pretty(pg_indexes_size('events'))
                """
                )
                if row:
                    metrics["table_size"] = row[0]
                    metrics["indexes_size"] = row[1]

        except Exception as e:
            self.logger.error("Error collecting metrics", exc_info=True)

        return metrics
