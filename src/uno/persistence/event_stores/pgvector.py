# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.pgvector
PostgreSQL event store with pgvector integration for Uno framework
"""

from __future__ import annotations
from typing import TypeVar, Generic, AsyncIterator, cast
from uuid import UUID
from contextlib import asynccontextmanager
import asyncpg
import numpy as np
from sentence_transformers import SentenceTransformer

from uno.domain.events import DomainEvent
from uno.event_store.errors import (
    EventStoreAppendError,
    EventStoreGetEventsError,
    EventStoreVersionConflict,
    EventStoreReplayError,
    EventStoreError,
    EventStoreConnectError,
    EventStoreTransactionError,
    EventStoreSearchError,
)

E = TypeVar('E', bound=DomainEvent)

class PGVectorEventStore(Generic[E]):
    """PostgreSQL with pgvector implementation of the event store."""

    def __init__(self, dsn: str) -> None:
        """Initialize the PGVector event store.

        Args:
            dsn: PostgreSQL connection string
        """
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None
        self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    async def connect(self) -> None:
        """Connect to the PostgreSQL database and create tables if they don't exist."""
        try:
            self._pool = await asyncpg.create_pool(self._dsn)
            async with self._pool.acquire() as conn:
                await self._create_tables(conn)
        except Exception as e:
            raise EventStoreConnectError(
                f"Failed to connect to PostgreSQL database: {str(e)}",
                context={
                    "dsn": self._dsn,
                    "error": str(e),
                }
            )

    async def _create_tables(self, conn: asyncpg.Connection) -> None:
        """Create event store tables with pgvector support."""
        await conn.execute("""
            -- Create extension if not exists
            CREATE EXTENSION IF NOT EXISTS vector;

            -- Create events table with vector column
            CREATE TABLE IF NOT EXISTS events (
                event_id UUID PRIMARY KEY,
                aggregate_id UUID NOT NULL,
                event_type TEXT NOT NULL,
                occurred_on TIMESTAMP WITH TIME ZONE NOT NULL,
                version INTEGER NOT NULL CHECK (version > 0),
                aggregate_version INTEGER NOT NULL CHECK (aggregate_version > 0),
                state JSONB NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}',
                embedding VECTOR(384),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, aggregate_version)
            );

            -- Create index for vector similarity search
            CREATE INDEX IF NOT EXISTS idx_embedding ON events USING ivfflat (embedding vector_cosine_ops);

            -- Create indexes for efficient queries
            CREATE INDEX IF NOT EXISTS idx_aggregate_id ON events (aggregate_id);
            CREATE INDEX IF NOT EXISTS idx_aggregate_version ON events (aggregate_id, aggregate_version);
        """)

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """Context manager for database transactions."""
        if self._pool is None:
            raise EventStoreTransactionError(
                "Event store not connected. Call connect() first.",
                context={
                    "dsn": self._dsn,
                    "status": "disconnected",
                }
            )
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    yield conn
        except Exception as e:
            raise EventStoreTransactionError(
                f"Transaction failed: {str(e)}",
                context={
                    "dsn": self._dsn,
                    "error": str(e),
                }
            ) from e

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text content."""
        embedding = self._embedding_model.encode(text)
        # tolist() returns List[float], but we need to be explicit about the type
        return [float(x) for x in embedding.tolist()]

    async def append(
        self,
        aggregate_id: UUID,
        events: list[E],
        expected_version: int | None = None,
    ) -> None:
        """Append events to an aggregate's stream.

        Args:
            aggregate_id: The ID of the aggregate
            events: List of events to append
            expected_version: Expected current version of the aggregate

        Raises:
            EventStoreVersionConflict: If version conflict occurs
            EventStoreAppendError: If append fails
        """
        try:
            async with self._transaction() as conn:
                # Get current version
                row = await conn.fetchrow(
                    "SELECT MAX(aggregate_version) FROM events WHERE aggregate_id = $1",
                    aggregate_id
                )
                current_version = row[0] or 0

                if expected_version is not None and expected_version != current_version:
                    raise EventStoreVersionConflict(
                        f"Version conflict for aggregate {aggregate_id}. Expected {expected_version}, got {current_version}",
                        context={
                            "aggregate_id": str(aggregate_id),
                            "expected_version": expected_version,
                            "current_version": current_version,
                        }
                    )

                # Insert events
                for event in events:
                    if event.version != 1:
                        raise EventStoreVersionConflict(
                            f"Event version must be 1 for new events. Got {event.version}",
                            context={
                                "event_id": str(event.event_id),
                                "event_version": event.version,
                                "aggregate_id": str(aggregate_id),
                            }
                        )

                    event.aggregate_version = current_version + 1
                    current_version += 1

                    # Generate embedding for searchable content
                    searchable_content = f"""{event.event_type}: {event.state}
                    Timestamp: {event.occurred_on.isoformat()}
                    Metadata: {event.metadata}"""
                    embedding = self._generate_embedding(searchable_content)

                    await conn.execute(
                        """
                        INSERT INTO events (
                            event_id, aggregate_id, event_type, occurred_on,
                            version, aggregate_version, state, metadata, embedding
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        event.event_id,
                        aggregate_id,
                        event.event_type,
                        event.occurred_on,
                        event.version,
                        event.aggregate_version,
                        event.state,
                        event.metadata,
                        embedding,
                    )

        except Exception as e:
            raise EventStoreAppendError(
                f"Failed to append events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "events_count": len(events),
                    "error": str(e),
                }
            )

    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Get events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            from_version: Optional starting version

        Yields:
            Events in order from oldest to newest

        Raises:
            EventStoreGetEventsError: If event retrieval fails
        """
        try:
            query = "SELECT * FROM events WHERE aggregate_id = $1"
            params: list[UUID | int] = [aggregate_id]

            if from_version is not None:
                query += " AND aggregate_version >= $2"
                params.append(from_version)

            query += " ORDER BY aggregate_version ASC"
            if self._pool is None:
                raise EventStoreError(
                    "Event store not connected. Call connect() first.",
                    context={"method": "get_events"}
                )
            async with self._pool.acquire() as conn:
                async for row in conn.cursor(query, *params):
                    event = DomainEvent(
                        event_id=row[0],
                        event_type=row[2],
                        occurred_on=row[3],
                        version=row[4],
                        aggregate_version=row[5],
                        state=row[6],
                        metadata=row[7],
                    )
                    yield cast(E, event)

        except Exception as e:
            raise EventStoreGetEventsError(
                f"Failed to get events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "error": str(e),
                }
            )

    async def replay_events(
        self,
        aggregate_id: UUID,
        from_version: int | None = None,
        to_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Replay events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            from_version: Optional starting version
            to_version: Optional ending version

        Yields:
            Events in order from oldest to newest

        Raises:
            EventStoreReplayError: If replay fails
        """
        try:
            query = "SELECT * FROM events WHERE aggregate_id = $1"
            params: list[UUID | int] = [aggregate_id]

            if from_version is not None:
                query += " AND aggregate_version >= $2"
                params.append(from_version)

            if to_version is not None:
                query += " AND aggregate_version <= $3"
                params.append(to_version)

            query += " ORDER BY aggregate_version ASC"

            if self._pool is None:
                raise EventStoreConnectError(
                    "Event store not connected. Call connect() first.",
                    context={
                        "dsn": self._dsn,
                        "status": "disconnected",
                    }
                )

            async with self._pool.acquire() as conn:
                async for row in conn.cursor(query, *params):
                    event = DomainEvent(
                        event_id=row[0],
                        event_type=row[2],
                        occurred_on=row[3],
                        version=row[4],
                        aggregate_version=row[5],
                        state=row[6],
                        metadata=row[7],
                    )
                    yield cast(E, event)

        except Exception as e:
            raise EventStoreReplayError(
                f"Failed to replay events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(e),
                }
            )

    async def search_events(
        self,
        query: str,
        limit: int = 10,
    ) -> AsyncIterator[E]:
        """Search for events using semantic search.

        Args:
            query: Search query
            limit: Maximum number of results

        Yields:
            Events ordered by relevance
        """
        try:
            if self._pool is None:
                raise EventStoreConnectError(
                    "Event store not connected. Call connect() first.",
                    context={
                        "dsn": self._dsn,
                        "status": "disconnected",
                    }
                )
            async with self._pool.acquire() as conn:
                # Generate query embedding
                query_embedding = self._generate_embedding(query)

                # Perform semantic search
                query = """
                    SELECT *, 1 - (embedding <=> $1) as similarity
                    FROM events
                    ORDER BY embedding <=> $1
                    LIMIT $2
                """

                async for row in conn.cursor(query, query_embedding, limit):
                    event = DomainEvent(
                        event_id=row[0],
                        event_type=row[2],
                        occurred_on=row[3],
                        version=row[4],
                        aggregate_version=row[5],
                        state=row[6],
                        metadata=row[7],
                    )
                    yield cast(E, event)

        except Exception as e:
            raise EventStoreSearchError(
                f"Failed to search events: {str(e)}",
                context={
                    "query": query,
                    "limit": limit,
                    "error": str(e),
                }
            )
