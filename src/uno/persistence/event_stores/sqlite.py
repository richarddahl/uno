# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.sqlite
SQLite event store implementation for Uno framework
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections.abc import AsyncIterator, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, Generic
from uuid import UUID

import aiosqlite
from aiosqlite import Connection, Cursor
from pydantic import BaseModel, Field
from ulid import ULID

from uno.domain.events import DomainEvent
from uno.event_store.base import EventStore, EventStoreError
from uno.event_store.config import EventStoreSettings
from uno.event_store.errors import (
    EventStoreAppendError,
    EventStoreError,
    EventStoreGetEventsError,
    EventStoreConnectionError,
    EventStoreTransactionError,
    EventStoreConnectError,
    EventStoreVersionConflict,
)
from uno.logging import get_logger

logger = get_logger(__name__)

E = TypeVar('E', bound=DomainEvent)


class _ConnectionManager:
    """Manages SQLite database connections.
    
    This class handles connection pooling and ensures proper cleanup.
    """
    
    def __init__(self, db_path: str, **kwargs: Any) -> None:
        self._db_path = db_path
        self._connection_config: Dict[str, Any] = {
            'isolation_level': kwargs.get('isolation_level'),
            'check_same_thread': kwargs.get('check_same_thread', False),
            'timeout': kwargs.get('timeout', 5.0),
            'detect_types': 0,
            'cached_statements': 128,
        }
        self._connection: Optional[Connection] = None
        self._lock = asyncio.Lock()
        self._connected = False

    async def _ensure_connection(self) -> None:
        """Ensure we have a connection to the database."""
        if self._connection is not None:
            return

        conn = None
        try:
            conn = await aiosqlite.connect(
                database=self._db_path,
                **{k: v for k, v in self._connection_config.items() 
                   if k in ('timeout', 'detect_types', 'cached_statements', 'isolation_level')}
            )
            
            if conn is None:
                raise RuntimeError("Failed to create database connection")
                
            conn.row_factory = aiosqlite.Row
            
            # Configure connection for better concurrency
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            
            if self._connection_config['isolation_level']:
                isolation_level = str(self._connection_config['isolation_level']).upper()
                if isolation_level in ('DEFERRED', 'IMMEDIATE', 'EXCLUSIVE'):
                    await conn.execute(
                        f"PRAGMA read_uncommitted = {'1' if isolation_level == 'IMMEDIATE' else '0'}"
                    )
            
            self._connection = conn
            self._connected = True
            
        except Exception as e:
            self._connected = False
            if conn is not None:
                await conn.close()
            raise

    async def get_connection(self) -> Connection:
        """Get a connection from the pool with proper settings."""
        async with self._lock:
            if not self._connected or self._connection is None:
                await self._ensure_connection()
            if self._connection is None:
                raise RuntimeError("Failed to get database connection")
            return self._connection  # type: ignore[return-value]
    
    async def close_connection(self, conn: Optional[Connection]) -> None:
        """Close a connection.
        
        Args:
            conn: The connection to close.
        """
        if conn is not None:
            try:
                await conn.close()
            except Exception as e:
                logger.error("Error closing database connection", exc_info=True)
                raise
    
    async def close(self) -> None:
        """Close the connection pool and all connections."""
        async with self._lock:
            if self._connection is not None:
                try:
                    await self._connection.close()
                except Exception as e:
                    logger.error("Error closing database connection", exc_info=True)
                    raise
                finally:
                    self._connection = None
                    self._connected = False


class SQLiteEventStore(EventStore[E]):
    """SQLite implementation of the EventStore interface.
    
    This implementation uses SQLite as the underlying storage for events.
    It provides ACID compliance and supports concurrent access.
    """
    
    def __init__(
        self,
        db_path: str | Path,
        settings: Optional[EventStoreSettings] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the SQLite event store.
        
        Args:
            db_path: Path to the SQLite database file.
            settings: Optional settings for the event store.
            **kwargs: Additional keyword arguments passed to the connection.
        """
        super().__init__(settings=settings)
        self._db_path = str(db_path)
        self._connection_config = kwargs
        self._connection_manager: Optional[_ConnectionManager] = None
        self._connected = False
        self._lock = asyncio.Lock()
        self._closed = False

    @property
    def is_connected(self) -> bool:
        """Check if the store is connected to the database."""
        return self._connected and not self._closed

    async def connect(self) -> None:
        """Connect to the SQLite database and create tables if they don't exist."""
        if self._connected:
            return

        try:
            # Create tables first
            await self._create_tables()

            # Get a connection and configure it
            conn = await self._get_connection()
            try:
                # Enable WAL mode for better concurrency
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA busy_timeout=5000")
                self._connected = True
                logger.info(
                    "Connected to SQLite database",
                    extra={"db_path": self._db_path},
                )
            finally:
                # Always ensure the connection is returned to the pool
                await conn.close()

        except Exception as e:
            await self._close_connection()
            logger.error(
                "Failed to connect to SQLite database",
                exc_info=True,
                extra={"db_path": self._db_path, "error": str(e)},
            )
            raise EventStoreConnectError(
                f"Failed to connect to SQLite database: {str(e)}",
                context={
                    "db_path": self._db_path,
                    "error": str(e),
                    "status": "disconnected",
                },
            ) from e

    async def _get_connection(self) -> Connection:
        """Get a database connection."""
        if self._connection_manager is None:
            self._connection_manager = _ConnectionManager(
                self._db_path, **self._connection_config
            )
        return await self._connection_manager.get_connection()

    async def _release_connection(self, conn: Optional[Connection]) -> None:
        """Release a database connection."""
        if self._connection_manager and conn is not None:
            await self._connection_manager.close_connection(conn)

    async def _get_cursor(self) -> Cursor:
        """Get a cursor from the current thread's connection.

        Returns:
            Cursor: A database cursor for executing queries.

        Raises:
            EventStoreConnectionError: If unable to get a connection.
        """
        conn = await self._get_connection()
        return await conn.cursor()

    async def _release_cursor(self, cursor: Cursor) -> None:
        """Release a cursor.

        Args:
            cursor: The cursor to release.
        """
        if cursor is not None:
            await cursor.close()

    async def _close_connection(self) -> None:
        """Close the connection asynchronously."""
        if self._connection_manager:
            await self._connection_manager.close()

    async def _close_all_connections(self) -> None:
        """Close all connections."""
        if self._connection_manager:
            await self._connection_manager.close()
        self._connected = False

    async def _create_tables(self) -> None:
        """Create the necessary tables if they don't exist."""
        conn = await self._get_connection()
        cursor = await conn.cursor()
        try:
            # Create events table
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    aggregate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_on TIMESTAMP NOT NULL,
                    version INTEGER NOT NULL,
                    aggregate_version INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(aggregate_id, aggregate_version)
                )"""
            )

            # Create indexes
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_aggregate 
                ON events (aggregate_id)
                """
            )

            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_aggregate_version 
                ON events (aggregate_id, aggregate_version)
                """
            )

            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON events (event_type)
                """
            )

            # Commit the transaction
            await conn.commit()
        except Exception as e:
            try:
                await conn.rollback()
            except Exception as rollback_error:
                logger.warning("Error during rollback: {error}", error=str(rollback_error))
            raise
        finally:
            await cursor.close()
            await self._release_connection(conn)

    async def optimize(self) -> None:
        """Optimize the database by running VACUUM and ANALYZE.

        Note: For simplicity, we'll just run ANALYZE since VACUUM requires
        exclusive access and can be problematic in a connection pool.
        """
        conn: Optional[Connection] = None
        try:
            conn = await self._get_connection()
            logger.info("Optimizing SQLite database")
            
            # Run ANALYZE in a transaction
            try:
                await conn.execute("ANALYZE")
                await conn.commit()
                logger.info("SQLite database optimization complete")
            except Exception as e:
                logger.warning(f"ANALYZE failed: {e}")
                try:
                    await conn.rollback()
                except Exception:
                    pass
                # Continue even if ANALYZE fails
                
        except Exception as e:
            logger.error("Failed to optimize SQLite database", exc_info=True)
            raise EventStoreError(
                f"Failed to optimize database: {str(e)}",
                context={"error": str(e)},
            ) from e
        finally:
            if conn:
                try:
                    await self._release_connection(conn)
                except Exception:
                    pass

    async def close(self) -> None:
        """Close all database connections and clean up resources."""
        await self._close_all_connections()
        logger.info("Closed all SQLite connections")

    async def __aenter__(self) -> SQLiteEventStore[E]:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def append(
        self,
        aggregate_id: str,
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
        if not events:
            return  # No-op for empty event list

        try:
            async with self._transaction() as cursor:
                # Get current version in a single query
                await cursor.execute(
                    """
                    SELECT COALESCE(MAX(aggregate_version), 0)
                    FROM events
                    WHERE aggregate_id = ?
                    """,
                    (str(aggregate_id),),
                )
                result = await cursor.fetchone()
                current_version = result[0] if result and result[0] is not None else 0

                # Check version conflict
                if expected_version is not None and expected_version != current_version:
                    raise EventStoreVersionConflict(
                        f"Version conflict for aggregate {aggregate_id}. "
                        f"Expected {expected_version}, got {current_version}",
                        context={
                            "aggregate_id": str(aggregate_id),
                            "expected_version": expected_version,
                            "current_version": current_version,
                        },
                    )

                # Prepare batch insert
                event_values = []
                now = datetime.now(timezone.utc).isoformat()

                for event in events:
                    event_dict = event.model_dump()
                    if event_dict['version'] != 1:
                        raise EventStoreVersionConflict(
                            f"Event version must be 1 for new events. Got {event_dict['version']}",
                            context={
                                "event_id": str(event_dict['event_id']),
                                "event_version": event_dict['version'],
                                "aggregate_id": str(aggregate_id),
                            },
                        )

                    current_version += 1
                    event.aggregate_version = current_version

                    # Get event attributes
                    event_dict = event.model_dump()
                    
                    # Get event_type from the property if it exists, otherwise from dict
                    event_type = ''
                    if hasattr(event, 'event_type'):
                        event_type_value = event.event_type
                        if isinstance(event_type_value, str):
                            event_type = event_type_value
                        elif hasattr(event_type_value, '__str__'):
                            event_type = str(event_type_value)
                    
                    if not event_type:  # Fallback to dict if not set
                        event_type = str(event_dict.get('event_type', ''))
                    
                    # Handle occurred_on separately to ensure it's a datetime
                    occurred_on = event.occurred_on
                    if isinstance(occurred_on, str):
                        occurred_on = datetime.fromisoformat(occurred_on)
                    
                    event_values.append((
                        str(event_dict['event_id']),
                        str(aggregate_id),
                        event_type,
                        occurred_on.isoformat(),
                        event_dict['version'],
                        event_dict['aggregate_version'],
                        json.dumps(event_dict['state']),
                        json.dumps(event_dict.get('metadata', {})),
                        now,
                    ))

                # Batch insert all events
                await cursor.executemany(
                    """
                    INSERT INTO events (
                        event_id, aggregate_id, event_type, occurred_on,
                        version, aggregate_version, state, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    event_values,
                )

                logger.debug(
                    "Appended events to aggregate",
                    extra={
                        "aggregate_id": str(aggregate_id),
                        "event_count": len(events),
                        "new_version": current_version,
                    },
                )

        except EventStoreVersionConflict:
            raise  # Re-raise version conflicts
            
        except Exception as e:
            logger.error(
                "Failed to append events",
                exc_info=True,
                extra={
                    "aggregate_id": str(aggregate_id),
                    "event_count": len(events),
                    "error": str(e),
                },
            )
            raise EventStoreAppendError(
                f"Failed to append events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "events_count": len(events),
                    "error": str(e),
                },
            ) from e

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None,
    ) -> AsyncIterator[E]:
        """Get events for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID.
            from_version: The version to start from (inclusive).
            to_version: The version to end at (inclusive). If None, gets all events.
            
        Yields:
            The events in order of version.
            
        Raises:
            EventStoreError: If the operation fails.
        """
        query = """
            SELECT * FROM events 
            WHERE aggregate_id = ? AND aggregate_version >= ?
        """
        params: List[Union[str, int]] = [str(aggregate_id), from_version]
        
        if to_version is not None:
            query += " AND aggregate_version <= ?"
            params.append(to_version)
            
        query += " ORDER BY aggregate_version ASC"
        
        conn: Optional[Connection] = None
        try:
            conn = await self._get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params)
            
            while True:
                row = await cursor.fetchone()
                if not row:
                    break
                    
                # Deserialize the event data
                event_data = dict(row)
                event_type = event_data.get('event_type')
                event_data_str = event_data.get('data', '{}')
                
                try:
                    event_dict = json.loads(event_data_str)
                    # Create the appropriate event type
                    # This assumes event types are registered in a registry
                    event_class = self._get_event_class(event_type)
                    if event_class is None:
                        raise ValueError(f"Unknown event type: {event_type}")
                        
                    event = event_class(**event_dict)
                    yield event  # type: ignore
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(
                        "Failed to deserialize event data",
                        exc_info=True,
                        extra={
                            "event_data": event_data_str,
                            "event_type": event_type,
                            "error": str(e)
                        },
                    )
                    continue
                
        except Exception as e:
            logger.error(
                "Failed to get events",
                exc_info=True,
                extra={"aggregate_id": aggregate_id, "error": str(e)},
            )
            raise EventStoreGetEventsError(
                f"Failed to get events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(e),
                }
            ) from e

    async def replay_events(
        self,
        aggregate_id: UUID,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
    ) -> AsyncIterator[E]:
        """Replay events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            from_version: Optional starting version
            to_version: Optional ending version

        Yields:
            Events in order from oldest to newest

        Raises:
            EventStoreError: If replay fails
        """
        query = "SELECT * FROM events WHERE aggregate_id = ?"
        params: List[Union[str, int]] = [str(aggregate_id)]

        if from_version is not None:
            query += " AND aggregate_version >= ?"
            params.append(from_version)
            
        if to_version is not None:
            query += " AND aggregate_version <= ?"
            params.append(to_version)
            
        query += " ORDER BY aggregate_version ASC"
        
        conn: Optional[Connection] = None
        try:
            conn = await self._get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params)
            
            while True:
                row = await cursor.fetchone()
                if not row:
                    break
                    
                # Deserialize the event data
                event_data = dict(row)
                event_type = event_data.get('event_type')
                event_data_str = event_data.get('data', '{}')
                
                try:
                    event_dict = json.loads(event_data_str)
                    # Create the appropriate event type
                    event_class = self._get_event_class(event_type)
                    if event_class is None:
                        raise ValueError(f"Unknown event type: {event_type}")
                        
                    event = event_class(**event_dict)
                    yield event  # type: ignore
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(
                        "Failed to deserialize event data during replay",
                        exc_info=True,
                        extra={
                            "event_data": event_data_str,
                            "event_type": event_type,
                            "error": str(e)
                        },
                    )
                    continue
                    
        except Exception as e:
            logger.error(
                "Failed to replay events",
                exc_info=True,
                extra={"aggregate_id": str(aggregate_id), "error": str(e)},
            )
            raise EventStoreError(
                f"Failed to replay events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(e),
                },
            ) from e
        finally:
            if conn is not None:
                await self._release_connection(conn)
