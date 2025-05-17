# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.vector
Vector store implementation for Uno framework
"""

from __future__ import annotations
from typing import TypeVar, Generic, AsyncIterator, Any, Optional, List
from uuid import UUID
from datetime import datetime
from contextlib import asynccontextmanager
import numpy as np
from sentence_transformers import SentenceTransformer
from chromadb import ChromaDB
from chromadb.config import Settings

from uno.domain.events import DomainEvent
from uno.event_store.errors import (
    EventStoreAppendError,
    EventStoreGetEventsError,
    EventStoreVersionConflict,
    EventStoreReplayError,
    EventStoreConnectError,
    EventStoreTransactionError,
    EventStoreSearchError,
)

E = TypeVar("E", bound=DomainEvent)


class ChromaDBEventStore(Generic[E]):
    """Vector store implementation of the event store."""

    def __init__(self, db_path: str) -> None:
        """Initialize the Vector event store.

        Args:
            db_path: Path to the ChromaDB database
        """
        self._db_path = db_path
        self._db: Optional[ChromaDB] = None
        self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    async def connect(self) -> None:
        """Connect to the vector database and create collections if they don't exist."""
        try:
            settings = Settings(
                chroma_db_impl="duckdb+parquet", persist_directory=self._db_path
            )
            self._db = ChromaDB(settings=settings)
            await self._create_collections()
        except Exception as e:
            raise EventStoreConnectError(
                f"Failed to connect to vector database: {str(e)}",
                context={
                    "db_path": self._db_path,
                    "error": str(e),
                },
            )

    async def _create_collections(self) -> None:
        """Create vector store collections if they don't exist."""
        if not await self._db.has_collection("events"):
            await self._db.create_collection(
                "events", metadata={"hnsw:space": "cosine"}, get_or_create=True
            )

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[ChromaDB]:
        """Context manager for database transactions."""
        if self._db is None:
            raise EventStoreTransactionError(
                "Event store not connected. Call connect() first.",
                context={
                    "db_path": self._db_path,
                    "status": "disconnected",
                },
            )

        try:
            yield self._db
        except Exception as e:
            raise EventStoreConnectError(
                f"Failed to connect to vector database: {str(e)}",
                context={
                    "db_path": self._db_path,
                    "error": str(e),
                },
            )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text content."""
        return self._embedding_model.encode(text).tolist()

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
            async with self._transaction() as db:
                # Get current version
                result = await db.get(
                    collection_name="events",
                    where={"aggregate_id": str(aggregate_id)},
                    include=["documents", "metadatas"],
                )
                current_version = (
                    max([m["aggregate_version"] for m in result["metadatas"]])
                    if result["metadatas"]
                    else 0
                )

                if expected_version is not None and expected_version != current_version:
                    raise EventStoreVersionConflict(
                        f"Version conflict for aggregate {aggregate_id}. Expected {expected_version}, got {current_version}",
                        context={
                            "aggregate_id": str(aggregate_id),
                            "expected_version": expected_version,
                            "current_version": current_version,
                        },
                    )

                # Prepare data for insertion
                ids = []
                embeddings = []
                metadatas = []
                documents = []

                for event in events:
                    if event.version != 1:
                        raise EventStoreVersionConflict(
                            f"Event version must be 1 for new events. Got {event.version}",
                            context={
                                "event_id": str(event.event_id),
                                "event_version": event.version,
                                "aggregate_id": str(aggregate_id),
                            },
                        )

                    event.aggregate_version = current_version + 1
                    current_version += 1

                    # Generate embeddings for searchable content
                    searchable_content = f"""{event.event_type}: {event.state}
                    Timestamp: {event.occurred_on.isoformat()}
                    Metadata: {event.metadata}"""
                    embedding = self._generate_embedding(searchable_content)

                    ids.append(str(event.event_id))
                    embeddings.append(embedding)
                    metadatas.append(
                        {
                            "aggregate_id": str(aggregate_id),
                            "event_type": event.event_type,
                            "occurred_on": event.occurred_on.isoformat(),
                            "version": event.version,
                            "aggregate_version": event.aggregate_version,
                            "state": event.state,
                            "metadata": event.metadata,
                            "created_at": datetime.now().isoformat(),
                        }
                    )
                    documents.append(searchable_content)

                # Add to vector store
                await db.add(
                    collection_name="events",
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )

        except Exception as e:
            raise EventStoreAppendError(
                f"Failed to append events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "events_count": len(events),
                    "error": str(e),
                },
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
            async with self._transaction() as db:
                where_clause = {"aggregate_id": str(aggregate_id)}
                if from_version is not None:
                    where_clause["aggregate_version"] = {"$gte": from_version}

                result = await db.get(
                    collection_name="events", where=where_clause, include=["metadatas"]
                )

                for metadata in result["metadatas"]:
                    event = DomainEvent(
                        event_id=UUID(metadata["id"]),
                        event_type=metadata["event_type"],
                        occurred_on=datetime.fromisoformat(metadata["occurred_on"]),
                        version=metadata["version"],
                        aggregate_version=metadata["aggregate_version"],
                        state=metadata["state"],
                        metadata=metadata["metadata"],
                    )
                    yield event

        except Exception as e:
            raise EventStoreGetEventsError(
                f"Failed to get events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "error": str(e),
                },
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
            async with self._transaction() as db:
                where_clause = {"aggregate_id": str(aggregate_id)}
                if from_version is not None:
                    where_clause["aggregate_version"] = {"$gte": from_version}
                if to_version is not None:
                    where_clause["aggregate_version"] = {"$lte": to_version}

                result = await db.get(
                    collection_name="events", where=where_clause, include=["metadatas"]
                )

                # Sort by aggregate_version
                metadatas = sorted(
                    result["metadatas"], key=lambda m: m["aggregate_version"]
                )

                for metadata in metadatas:
                    event = DomainEvent(
                        event_id=UUID(metadata["id"]),
                        event_type=metadata["event_type"],
                        occurred_on=datetime.fromisoformat(metadata["occurred_on"]),
                        version=metadata["version"],
                        aggregate_version=metadata["aggregate_version"],
                        state=metadata["state"],
                        metadata=metadata["metadata"],
                    )
                    yield event

        except Exception as e:
            raise EventStoreReplayError(
                f"Failed to replay events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(e),
                },
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
            async with self._transaction() as db:
                # Generate query embedding
                query_embedding = self._generate_embedding(query)

                # Perform semantic search
                result = await db.query(
                    collection_name="events",
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["metadatas"],
                )

                for metadata in result["metadatas"][0]:
                    event = DomainEvent(
                        event_id=UUID(metadata["id"]),
                        event_type=metadata["event_type"],
                        occurred_on=datetime.fromisoformat(metadata["occurred_on"]),
                        version=metadata["version"],
                        aggregate_version=metadata["aggregate_version"],
                        state=metadata["state"],
                        metadata=metadata["metadata"],
                    )
                    yield event

        except Exception as e:
            raise EventStoreSearchError(
                f"Failed to search events: {str(e)}",
                context={
                    "query": query,
                    "error": str(e),
                    "db_path": self._db_path,
                },
            )
