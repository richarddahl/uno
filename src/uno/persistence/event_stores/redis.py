# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""Redis event store implementation for Uno framework.

This module provides a Redis-based implementation of the event store that supports
both standalone Redis and Redis Cluster modes. It integrates with Uno's core systems
for dependency injection, configuration, and logging.

Example:
    ```python
    from uno.injection import Container
    from uno.event_store.redis import RedisEventStore
    from uno.event_store.config import EventStoreSettings

    # Create a container and configure Redis settings
    container = Container()
    settings = EventStoreSettings(
        redis_url="redis://localhost:6379",
        redis_cluster_mode=False
    )

    # Create the event store
    event_store = RedisEventStore(container, settings=settings)
    await event_store.connect()
    ```
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, TypeVar, cast
from uuid import UUID

from redis.asyncio import Redis, RedisCluster
from redis.exceptions import RedisError

from uno.domain.events import DomainEvent
from uno.event_store.base import EventStore
from uno.event_store.config import EventStoreSettings, default_settings
from uno.event_store.errors import (
    EventStoreAppendError,
    EventStoreConnectError,
    EventStoreError,
    EventStoreGetEventsError,
    EventStoreReplayError,
    EventStoreVersionConflict,
)
from uno.injection import ContainerProtocol
from uno.logging import get_logger, LoggerProtocol

# Type variable for events
E = TypeVar("E", bound=DomainEvent)

class RedisEventStore(EventStore[E]):
    """Redis implementation of the event store with cluster support.
    
    This implementation supports both standalone Redis and Redis Cluster modes.
    It uses Uno's dependency injection, configuration, and logging systems.
    
    Args:
        container: The dependency injection container
        settings: Event store settings. If not provided, defaults will be used.
        logger: Logger instance. If not provided, a default one will be created.
    """

    def __init__(
        self,
        container: ContainerProtocol,
        settings: EventStoreSettings | None = None,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """Initialize the Redis event store.
        
        The store will not connect to Redis until `connect()` is called.
        """
        # Initialize with default settings if none provided
        settings = settings or default_settings
        
        # Configure logger with module name if not provided
        if logger is None:
            logger = get_logger("uno.event_store.redis")
            
        # Initialize base class
        super().__init__(settings=settings, logger=logger)
        
        # Store DI container
        self._container = container
        
        # Initialize Redis client
        self._redis: Redis[bytes] | RedisCluster[bytes] | None = None
        
        # Configure connection parameters
        self._is_cluster = settings.redis_cluster_mode
        self._nodes = settings.redis_cluster_nodes or [settings.redis_url or "redis://localhost:6379"]
        self._connection_kwargs: dict[str, Any] = settings.redis_connection_kwargs or {}
        
        # Configure SSL if needed
        if settings.redis_ssl:
            ssl_context = {
                "ssl": True,
                "ssl_cert_reqs": "required",
            }
            if settings.redis_ssl_ca_certs:
                ssl_context["ssl_ca_certs"] = settings.redis_ssl_ca_certs
            self._connection_kwargs.update(ssl_context)
            
        self._logger.debug(
            "Initialized RedisEventStore with %s mode", 
            "cluster" if self._is_cluster else "standalone"
        )

    async def connect(self) -> None:
        """Connect to the Redis database or cluster.
        
        This method establishes a connection to either a standalone Redis instance
        or a Redis Cluster, depending on the configuration. It handles connection
        errors and logs the connection attempt.
        
        Raises:
            EventStoreConnectError: If the connection to Redis fails
            
        Example:
            ```python
            event_store = RedisEventStore(container, settings)
            try:
                await event_store.connect()
                # Store is now ready to use
            except EventStoreConnectError as e:
                # Handle connection error
                logger.error("Failed to connect to Redis: %s", e)
            ```
        """
        if self._redis is not None:
            self._logger.debug("Redis connection already established")
            return
            
        self._logger.info("Connecting to Redis %s...", "cluster" if self._is_cluster else "standalone")
        
        try:
            if self._is_cluster:
                # Connect to Redis Cluster
                self._logger.debug("Initializing Redis Cluster with nodes: %s", self._nodes)
                
                # Parse node information
                startup_nodes = []
                for url in self._nodes:
                    if not url:
                        continue
                    try:
                        # Extract host and port from URL
                        url_parts = url.split("://")
                        if len(url_parts) != 2:
                            self._logger.warning("Invalid Redis URL format: %s", url)
                            continue
                            
                        host_port = url_parts[1].split(":")
                        host = host_port[0]
                        port = int(host_port[1]) if len(host_port) > 1 else 6379
                        startup_nodes.append({"host": host, "port": port})
                    except (ValueError, IndexError) as e:
                        self._logger.warning("Invalid Redis node URL '%s': %s", url, str(e))
                        continue
                
                if not startup_nodes:
                    raise EventStoreConnectError("No valid Redis cluster nodes provided")
                
                self._logger.debug("Connecting to Redis Cluster with nodes: %s", startup_nodes)
                self._redis = RedisCluster(
                    startup_nodes=startup_nodes,
                    **self._connection_kwargs
                )
                
                # Test the connection
                await self._redis.ping()
                self._logger.info("Successfully connected to Redis Cluster")
                
            else:
                # Connect to standalone Redis
                if not self._nodes or not self._nodes[0]:
                    raise EventStoreConnectError("No Redis URL provided")
                    
                redis_url = self._nodes[0]
                self._logger.debug("Connecting to standalone Redis at %s", redis_url)
                
                self._redis = Redis.from_url(
                    redis_url,
                    **self._connection_kwargs
                )
                
                # Test the connection
                await self._redis.ping()
                self._logger.info("Successfully connected to Redis at %s", redis_url)
                
        except RedisError as e:
            error_msg = f"Failed to connect to Redis: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            await self.disconnect()
            raise EventStoreConnectError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error connecting to Redis: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            await self.disconnect()
            raise EventStoreConnectError(error_msg) from e
            
    async def disconnect(self) -> None:
        """Disconnect from the Redis database or cluster.
        
        This method closes the connection to Redis and cleans up resources.
        It is safe to call this method multiple times or when not connected.
        """
        if self._redis is None:
            self._logger.debug("Redis connection already closed")
            return
            
        try:
            self._logger.debug("Closing Redis connection...")
            await self._redis.close()
            self._logger.info("Successfully disconnected from Redis")
        except Exception as e:
            self._logger.error("Error disconnecting from Redis: %s", str(e), exc_info=True)
            raise EventStoreError("Failed to disconnect from Redis") from e
        finally:
            self._redis = None

    def _get_event_type(self, type_name: str) -> type[E] | None:
        """Resolve an event type from its fully qualified name using the DI container.

        This method handles the resolution of event types from their string representations,
        performing validation to ensure the resolved type is a valid DomainEvent subclass.

        Args:
            type_name: The fully qualified name of the event type (e.g., 'myapp.events.MyEvent').

        Returns:
            The resolved event type class if found and valid, None otherwise.

        Raises:
            EventStoreError: If there's an error during type resolution or validation.

        Example:
            ```python
            # Resolve an event type
            event_type = self._get_event_type("myapp.events.UserCreated")
            if event_type:
                # Use the event type for deserialization
                event = event_type.model_validate_json(event_data)
            ```
        """
        from typing import cast, Type
        from uno.domain.events import DomainEvent  # Local import to avoid circular imports
        
        if not type_name or not isinstance(type_name, str):
            self._logger.warning(
                "Invalid type name provided",
                extra={"type_name": type_name, "type_of": type(type_name).__name__}
            )
            return None

        try:
            # Resolve the type from the container
            resolved = self._container.resolve(type_name)
            
            # Verify the resolved type is a class
            if not isinstance(resolved, type):
                self._logger.warning(
                    "Resolved type is not a class",
                    extra={
                        "type_name": type_name,
                        "resolved_type": type(resolved).__name__
                    }
                )
                return None
                
            # Verify it's a DomainEvent subclass
            if not issubclass(resolved, DomainEvent):
                self._logger.warning(
                    "Resolved type is not a DomainEvent",
                    extra={
                        "type_name": type_name,
                        "resolved_type": resolved.__name__,
                        "bases": [base.__name__ for base in resolved.__bases__]
                    }
                )
                return None
                
            self._logger.debug(
                "Successfully resolved event type",
                extra={"type_name": type_name, "resolved_type": resolved.__name__}
            )
            
            # Cast the resolved type to the expected type variable
            return cast(Type[E], resolved)
            
        except Exception as e:
            self._logger.error(
                "Failed to resolve event type",
                extra={"type_name": type_name, "error": str(e)},
                exc_info=True
            )
            return None

    async def _get_stream_version(self, stream_id: str) -> int:
        """Retrieve the current version of a stream from Redis.
        
        This method safely retrieves the version counter for a given stream.
        If the stream doesn't exist or has no version set, it returns 0.
        
        Args:
            stream_id: The unique identifier of the stream.
            
        Returns:
            The current version of the stream as an integer. Returns 0 if the stream 
            doesn't exist or has no version set.
            
        Raises:
            EventStoreError: If there's an error accessing Redis or if the version
                          is not a valid integer.
            
        Example:
            ```python
            # Get the current version of a stream
            try:
                version = await event_store._get_stream_version("order-123")
                print(f"Current stream version: {version}")
            except EventStoreError as e:
                print(f"Failed to get stream version: {e}")
            ```
        """
        if not stream_id or not isinstance(stream_id, str):
            raise EventStoreError(
                "Stream ID must be a non-empty string",
                extra={"stream_id": stream_id, "type": type(stream_id).__name__}
            )
            
        if self._redis is None:
            raise EventStoreError(
                "Redis client is not initialized. Call connect() first.",
                extra={"stream_id": stream_id}
            )
            
        stream_key = f"stream:{stream_id}"
        self._logger.debug(
            "Retrieving version for stream",
            extra={"stream_id": stream_id, "stream_key": stream_key}
        )
            
        try:
            # Get the version from the stream's hash
            version = await self._redis.hget(stream_key, "version")
            
            # Handle case where stream or version doesn't exist
            if version is None:
                self._logger.debug(
                    "No version found for stream, defaulting to 0",
                    extra={"stream_id": stream_id, "stream_key": stream_key}
                )
                return 0
                
            # Ensure the version is a valid integer
            try:
                version_int = int(version)
                self._logger.debug(
                    "Successfully retrieved stream version",
                    extra={"stream_id": stream_id, "version": version_int}
                )
                return version_int
                
            except (ValueError, TypeError) as e:
                error_msg = f"Invalid version format in Redis: {version!r}"
                self._logger.error(
                    error_msg,
                    extra={
                        "stream_id": stream_id,
                        "stream_key": stream_key,
                        "version_value": version,
                        "version_type": type(version).__name__
                    },
                    exc_info=True
                )
                raise EventStoreError(
                    f"Failed to parse version for stream {stream_id}: {error_msg}",
                    extra={"stream_id": stream_id, "version_value": version}
                ) from e
                
        except RedisError as e:
            error_msg = f"Redis error while getting version for stream {stream_id}"
            self._logger.error(
                error_msg,
                extra={"stream_id": stream_id, "stream_key": stream_key},
                exc_info=True
            )
            raise EventStoreError(
                f"{error_msg}: {str(e)}",
                extra={"stream_id": stream_id, "error": str(e)}
            ) from e
        
    async def _initialize_keys(self) -> None:
        """Initialize Redis keys and indexes required for the event store.
        
        This method ensures all necessary Redis data structures are properly set up,
        including stream metadata, counters, and search indexes. It's automatically
        called during the connect() process.
        
        The initialization is idempotent and safe to call multiple times. If Redis
        modules like RediSearch are not available, it will log a warning but continue
        with reduced functionality.
        
        Raises:
            EventStoreError: If there's a critical error during initialization.
            
        Example:
            ```python
            # Called automatically during connect()
            await event_store._initialize_keys()
            
            # Can be called manually if needed
            try:
                await event_store._initialize_keys()
            except EventStoreError as e:
                logger.error("Failed to initialize Redis keys: %s", str(e))
            ```
        """
        if self._redis is None:
            raise EventStoreError(
                "Redis client is not initialized. Call connect() first.",
                extra={"method": "_initialize_keys"}
            )
            
        self._logger.info("Initializing Redis keys and indexes...")
        
        # Define the initialization script with proper error handling
        init_script = """
        -- Initialize streams set if it doesn't exist
        local streams_key = 'events:streams'
        local streams_exists = redis.call('EXISTS', streams_key)
        
        if streams_exists == 0 then
            -- Initialize streams sorted set with default stream
            redis.call('ZADD', streams_key, 0, 'default')
            
            -- Initialize global event counter
            redis.call('SET', 'events:counter', 0)
            
            -- Initialize last event ID
            redis.call('SET', 'events:last_id', '0-0')
            
            -- Initialize default stream metadata
            redis.call('HSET', 'stream:default', 'version', 0, 'created_at', ARGV[1])
            
            return {
                initialized = true,
                message = "Initialized Redis keys"
            }
        else
            return {
                initialized = false,
                message = "Redis keys already exist"
            }
        end
        """
        
        # Define the search index creation script (optional)
        search_index_script = """
        -- Only proceed if RediSearch is available
        local success, error = pcall(function()
            -- Check if index already exists
            local index_name = 'idx:events'
            local indexes = redis.call('FT._LIST')
            
            for _, idx in ipairs(indexes) do
                if idx == index_name then
                    return {exists = true}
                end
            end
            
            -- Create the index if it doesn't exist
            return redis.call('FT.CREATE', index_name, 'ON', 'HASH', 
                'PREFIX', '1', 'event:', 'SCHEMA',
                'stream_id', 'TAG', 'SORTABLE',
                'event_type', 'TAG', 'SORTABLE',
                'aggregate_id', 'TAG', 'SORTABLE',
                'version', 'NUMERIC', 'SORTABLE',
                'timestamp', 'NUMERIC', 'SORTABLE',
                'data', 'TEXT'
            )
        end)
        
        if not success then
            return {
                error = "Failed to create search index: " .. tostring(error),
                warning = true
            }
        end
        
        return {success = true}
        """
        
        try:
            # Execute the keys initialization script
            current_time = str(int(datetime.now().timestamp()))
            init_result = await self._redis.eval(
                init_script,
                0,  # No keys
                current_time  # ARGV[1]
            )
            
            # Log initialization result
            if isinstance(init_result, dict):
                if init_result.get('initialized', False):
                    self._logger.info(
                        "Successfully initialized Redis keys",
                        extra={"details": init_result}
                    )
                else:
                    self._logger.debug(
                        "Redis keys already initialized",
                        extra={"details": init_result}
                    )
            
            # Try to set up search index (non-critical)
            try:
                search_result = await self._redis.eval(search_index_script, 0)
                if isinstance(search_result, dict):
                    if search_result.get('error'):
                        self._logger.warning(
                            "Search index initialization warning",
                            extra={"warning": search_result.get('error')}
                        )
                    elif search_result.get('exists'):
                        self._logger.debug("Search index already exists")
                    else:
                        self._logger.info("Successfully created search index")
            except Exception as search_error:
                self._logger.warning(
                    "Failed to initialize search index (RediSearch may not be available)",
                    extra={"error": str(search_error)},
                    exc_info=True
                )
            
        except RedisError as e:
            error_msg = "Failed to initialize Redis keys"
            self._logger.error(
                error_msg,
                extra={"error": str(e)},
                exc_info=True
            )
            raise EventStoreError(
                f"{error_msg}: {str(e)}",
                extra={"error_type": type(e).__name__}
            ) from e
            
        except Exception as e:
            error_msg = "Unexpected error during Redis initialization"
            self._logger.critical(
                error_msg,
                extra={"error": str(e)},
                exc_info=True
            )
            raise EventStoreError(
                f"{error_msg}: {str(e)}",
                extra={"error_type": type(e).__name__}
            ) from e

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[Any]:
        """Context manager for managing Redis transactions with robust error handling.
        
        This context manager provides a safe way to execute multiple Redis commands
        atomically. It automatically handles transaction lifecycle including:
        - Starting a transaction
        - Executing queued commands
        - Committing on success
        - Rolling back on error
        - Proper resource cleanup
        
        The transaction will be automatically committed when the context block
        exits successfully. If an exception occurs, the transaction will be rolled back.
        
        Yields:
            RedisPipeline: A Redis pipeline object for queuing commands.
            
        Raises:
            EventStoreError: If the Redis client is not initialized or if any error
                          occurs during the transaction.
            
        Example:
            ```python
            try:
                async with event_store._transaction() as pipe:
                    # Queue multiple commands
                    await pipe.incr('event:counter')
                    await pipe.hset(
                        'event:metadata', 
                        mapping={
                            'last_updated': str(datetime.utcnow()),
                            'version': '1.0.0'
                        }
                    )
                    # Transaction will be committed automatically if no exceptions occur
            except EventStoreError as e:
                logger.error("Transaction failed: %s", str(e))
                # Transaction was automatically rolled back
            ```
            
        Note:
            - All commands queued in the pipeline will be executed atomically
            - The transaction is automatically rolled back if any error occurs
            - The pipeline is automatically reset after commit/rollback
        """
        if self._redis is None:
            raise EventStoreError(
                "Redis client is not initialized. Call connect() first.",
                extra={"method": "_transaction"}
            )
            
        transaction_id = str(uuid.uuid4())[:8]  # Short ID for logging
        start_time = time.monotonic()
        
        self._logger.debug(
            "Starting Redis transaction",
            extra={"transaction_id": transaction_id}
        )
        
        # Start a new pipeline/transaction
        async with self._redis.pipeline(transaction=True) as pipe:
            try:
                # Track the number of commands in the transaction
                command_count = 0
                
                # Create a wrapper to track commands
                original_execute = pipe.execute_command
                
                def execute_wrapper(*args, **kwargs):
                    nonlocal command_count
                    command_count += 1
                    self._logger.debug(
                        "Queuing Redis command",
                        extra={
                            "transaction_id": transaction_id,
                            "command": args[0] if args else "unknown",
                            "command_count": command_count
                        }
                    )
                    return original_execute(*args, **kwargs)
                
                # Apply the wrapper
                pipe.execute_command = execute_wrapper  # type: ignore[method-assign]
                
                # Yield the pipeline to the caller
                yield pipe
                
                # Execute the transaction
                self._logger.debug(
                    "Executing Redis transaction",
                    extra={
                        "transaction_id": transaction_id,
                        "command_count": command_count
                    }
                )
                
                # Execute the pipeline (commit the transaction)
                await pipe.execute()
                
                duration_ms = int((time.monotonic() - start_time) * 1000)
                self._logger.info(
                    "Successfully committed Redis transaction",
                    extra={
                        "transaction_id": transaction_id,
                        "duration_ms": duration_ms,
                        "command_count": command_count
                    }
                )
                
            except RedisError as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                error_msg = f"Redis transaction failed after {duration_ms}ms"
                self._logger.error(
                    error_msg,
                    extra={
                        "transaction_id": transaction_id,
                        "duration_ms": duration_ms,
                        "command_count": command_count,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                # The pipeline will automatically handle rollback on error
                raise EventStoreError(
                    f"{error_msg}: {str(e)}",
                    extra={
                        "transaction_id": transaction_id,
                        "error_type": type(e).__name__
                    }
                ) from e
                raise EventStoreError(error_msg) from e
                
            except Exception as e:
                error_msg = f"Unexpected error in Redis transaction: {str(e)}"
                self._logger.error(error_msg, exc_info=True)
                try:
                    await pipe.reset()
                except RedisError as reset_error:
                    self._logger.error(
                        "Failed to reset Redis pipeline: %s", 
                        str(reset_error),
                        exc_info=True
                    )
                raise EventStoreError(error_msg) from e

    async def append(
        self,
        stream_id: str,
        events: list[E],
        expected_version: int | None = None,
    ) -> None:
        """Append events to a stream.

        Args:
            stream_id: The stream identifier.
            events: List of domain events to append.
            expected_version: Expected version for optimistic concurrency.

        Raises:
            EventStoreAppendError: If appending events fails.
            EventStoreVersionConflict: If version conflict occurs.
        """
        if not events:
            return
            
        if self._redis is None:
            raise EventStoreError("Redis client not connected")

        try:
            # Check version if expected_version is provided
            if expected_version is not None:
                current_version = await self._get_stream_version(stream_id)
                if current_version != expected_version:
                    raise EventStoreVersionConflict(
                        f"Version conflict for stream {stream_id}. "
                        f"Expected: {expected_version}, Actual: {current_version}",
                        stream_id=stream_id,
                        expected_version=expected_version,
                        actual_version=current_version,
                    )

            # Prepare events data
            events_data: List[Tuple[str, Dict[str, Any]]] = []
            for event in events:
                event_data = {
                    'event_id': str(event.event_id),
                    'event_type': event.__class__.__name__,
                    'data': event.model_dump_json(),
                    'metadata': json.dumps(getattr(event, 'metadata', {})),
                    'timestamp': str(int(datetime.now().timestamp() * 1000)),
                    'version': str(getattr(event, 'version', 0)),
                    'stream_id': stream_id,
                }
                events_data.append(('*', event_data))

            # Add events to stream using pipeline
            async with self._transaction() as pipe:
                for stream_id, event_data in events_data:
                    await pipe.xadd(
                        f"events:{stream_id}",
                        event_data,
                        maxlen=10000,
                        approximate=True,
                    )
                
                # Update stream version
                await pipe.hincrby(f"stream:{stream_id}", "version", len(events))
                
        except EventStoreVersionConflict:
            raise
        except Exception as e:
            self.logger.error("Failed to append events: %s", str(e), exc_info=True)
            raise EventStoreAppendError(
                f"Failed to append events to stream {stream_id}: {str(e)}",
                stream_id=stream_id,
                events=events,
            ) from e

    async def get_events(
        self,
        stream_id: str,
        from_version: int = 0,
        limit: int | None = None,
        timeout: float | None = None,
    ) -> list[E]:
        """Retrieve events from a stream with optional blocking behavior.
        
        This method provides a robust way to retrieve events from a stream with support for:
        - Version-based pagination
        - Optional blocking behavior with timeout
        - Automatic event deserialization and validation
        - Comprehensive error handling and logging
        
        Args:
            stream_id: The unique identifier of the stream to read from.
            from_version: The minimum version number to include in results (inclusive).
                         Defaults to 0 (start of stream).
            limit: Maximum number of events to return. If None, returns all available events.
            timeout: Maximum time in seconds to wait for new events if the end of stream is reached.
                   If None (default), returns immediately. If set, blocks until events are available
                   or the timeout is reached.
                   
        Returns:
            A list of deserialized domain events, ordered by version number.
            
        Raises:
            EventStoreError: If there's an error accessing Redis or deserializing events.
            ValueError: If any input parameters are invalid.
            
        Example:
            ```python
            # Get all events from a stream
            events = await event_store.get_events("order-123")
            
            # Get up to 10 events starting from version 5
            events = await event_store.get_events("order-123", from_version=5, limit=10)
            
            # Wait up to 5 seconds for new events
            events = await event_store.get_events(
                "order-123",
                from_version=10,
                timeout=5.0
            )
            ```
            
        Note:
            - Events are always returned in version order (ascending)
            - If the stream doesn't exist, an empty list is returned
            - Invalid events are logged and skipped
        """
        # Input validation
        if not stream_id or not isinstance(stream_id, str):
            raise ValueError(
                f"stream_id must be a non-empty string, got {stream_id!r}",
                extra={"stream_id": stream_id, "type": type(stream_id).__name__}
            )
            
        if from_version < 0:
            raise ValueError(
                f"from_version must be >= 0, got {from_version}",
                extra={"stream_id": stream_id, "from_version": from_version}
            )
            
        if limit is not None and limit <= 0:
            raise ValueError(
                f"limit must be > 0 or None, got {limit}",
                extra={"stream_id": stream_id, "limit": limit}
            )
            
        if timeout is not None and timeout <= 0:
            raise ValueError(
                f"timeout must be > 0 or None, got {timeout}",
                extra={"stream_id": stream_id, "timeout": timeout}
            )
            
        if self._redis is None:
            raise EventStoreError(
                "Redis client is not initialized. Call connect() first.",
                extra={"stream_id": stream_id, "method": "get_events"}
            )
            
        # Log the operation
        request_id = str(uuid.uuid4())[:8]
        self._logger.debug(
            "Retrieving events from stream",
            extra={
                "request_id": request_id,
                "stream_id": stream_id,
                "from_version": from_version,
                "limit": limit,
                "timeout": timeout
            }
        )
        
        stream_key = f"stream:{stream_id}:events"
        events: list[E] = []
        
        try:
            start_time = time.monotonic()
            
            # Implement blocking behavior if timeout is specified
            if timeout is not None:
                self._logger.debug(
                    "Starting blocking read from stream",
                    extra={
                        "request_id": request_id,
                        "stream_key": stream_key,
                        "timeout": timeout
                    }
                )
                
                # Calculate end time for timeout
                end_time = start_time + timeout
                current_version = await self._get_stream_version(stream_id)
                
                # Wait for new events if needed
                while current_version <= from_version and time.monotonic() < end_time:
                    time_left = end_time - time.monotonic()
                    if time_left <= 0:
                        break
                        
                    # Wait for the next event with a short timeout
                    try:
                        # Use BZPOPMIN to wait for new events with a small timeout
                        result = await self._redis.bzpopmin(
                            stream_key,
                            timeout=min(1.0, time_left)  # Check at least once per second
                        )
                        
                        if result is not None:
                            # New event arrived, update current version
                            current_version = await self._get_stream_version(stream_id)
                            
                    except RedisError as e:
                        self._logger.warning(
                            "Error during blocking read",
                            extra={"request_id": request_id, "error": str(e)},
                            exc_info=True
                        )
                        continue
            
            # Get the range of events
            self._logger.debug(
                "Retrieving event range from stream",
                extra={
                    "request_id": request_id,
                    "stream_key": stream_key,
                    "from_version": from_version,
                    "limit": limit
                }
            )
            
            # Calculate end index for the range query
            end = from_version + limit - 1 if limit is not None else -1
            
            # Get events from the sorted set
            events_data = await self._redis.zrange(
                stream_key,
                min=from_version,
                max=end if end != -1 else "+inf",
                withscores=True
            )
            
            # Process and deserialize events
            for event_data, score in events_data:
                try:
                    event_dict = json.loads(event_data)
                    event_type_name = event_dict.get("event_type")
                    
                    if not event_type_name:
                        self._logger.warning(
                            "Event missing type information",
                            extra={
                                "request_id": request_id,
                                "stream_id": stream_id,
                                "event_data": event_data[:100] + "..." if len(event_data) > 100 else event_data
                            }
                        )
                        continue
                    
                    # Get the event type class
                    event_type = self._get_event_type(event_type_name)
                    if event_type is None:
                        self._logger.warning(
                            "Unknown event type",
                            extra={
                                "request_id": request_id,
                                "stream_id": stream_id,
                                "event_type": event_type_name,
                                "version": score
                            }
                        )
                        continue
                    
                    # Deserialize and validate the event
                    try:
                        event = event_type.model_validate(event_dict)
                        events.append(event)
                        
                        self._logger.debug(
                            "Successfully deserialized event",
                            extra={
                                "request_id": request_id,
                                "event_type": event_type_name,
                                "version": score,
                                "aggregate_id": getattr(event, "aggregate_id", None)
                            }
                        )
                        
                    except ValidationError as e:
                        self._logger.error(
                            "Event validation failed",
                            extra={
                                "request_id": request_id,
                                "stream_id": stream_id,
                                "event_type": event_type_name,
                                "version": score,
                                "error": str(e),
                                "event_data": event_dict
                            },
                            exc_info=True
                        )
                        
                except json.JSONDecodeError as e:
                    self._logger.error(
                        "Failed to decode event JSON",
                        extra={
                            "request_id": request_id,
                            "stream_id": stream_id,
                            "error": str(e),
                            "event_data": event_data[:200] + "..." if len(event_data) > 200 else event_data
                        },
                        exc_info=True
                    )
                    continue
                    
                except Exception as e:
                    self._logger.error(
                        "Unexpected error processing event",
                        extra={
                            "request_id": request_id,
                            "stream_id": stream_id,
                            "error": str(e),
                            "event_data": event_data[:200] + "..." if len(event_data) > 200 else event_data
                        },
                        exc_info=True
                    )
                    continue
                
            # Log completion
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._logger.info(
                "Successfully retrieved events from stream",
                extra={
                    "request_id": request_id,
                    "stream_id": stream_id,
                    "event_count": len(events),
                    "duration_ms": duration_ms,
                    "from_version": from_version,
                    "to_version": events[-1].version if events else None
                }
            )
            
            return events
            
        except RedisError as e:
            error_msg = f"Redis error while getting events from stream {stream_id}"
            self._logger.error(
                error_msg,
                extra={
                    "request_id": request_id,
                    "stream_id": stream_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise EventStoreError(
                f"{error_msg}: {str(e)}",
                extra={
                    "stream_id": stream_id,
                    "error_type": type(e).__name__
                }
            ) from e
            
        except Exception as e:
            error_msg = f"Unexpected error while getting events from stream {stream_id}"
            self._logger.critical(
                error_msg,
                extra={
                    "request_id": request_id,
                    "stream_id": stream_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise EventStoreError(
                f"{error_msg}: {str(e)}",
                extra={
                    "stream_id": stream_id,
                    "error_type": type(e).__name__
                }
            ) from e

    async def replay_events(
        self,
        stream_id: str,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Replay events from a stream.

        Args:
            stream_id: The stream identifier.
            from_version: Starting version (inclusive).
            to_version: Ending version (inclusive). If None, gets all events from from_version.

        Yields:
            Domain events from the stream.

        Raises:
            EventStoreReplayError: If replay fails.
        """
        try:
            # Get events from stream
            events = await self._redis.xrange(
                f"events:{stream_id}",
                min=f"{from_version}-0",
                max=f"{to_version or '+'}-+" if to_version is not None else "+",
            )

            for event_id, event_data in events:
                try:
                    # Get event type from the event data
                    event_type_name = event_data.get(b'event_type', b'').decode()
                    if not event_type_name:
                        self.logger.warning(
                            "Skipping event %s: missing event_type",
                            event_id.decode()
                        )
                        continue

                    # Get the event class
                    event_type = self._get_event_type(event_type_name)
                    if event_type is None:
                        self.logger.warning(
                            "Skipping event with unknown type: %s",
                            event_type_name,
                        )
                        continue

                    # Parse event data
                    event_data_str = event_data.get(b'data', b'{}').decode()
                    event = event_type.model_validate_json(event_data_str)
                    
                    # Set additional metadata if available
                    if b'metadata' in event_data:
                        metadata = json.loads(event_data[b'metadata'].decode())
                        for key, value in metadata.items():
                            if hasattr(event, key):
                                setattr(event, key, value)
                    
                    yield event
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to deserialize event %s: %s",
                        event_id.decode(),
                        str(e),
                        exc_info=True,
                    )

        except Exception as e:
            self.logger.error(
                "Failed to replay events from stream %s: %s",
                stream_id,
                str(e),
                exc_info=True,
            )
            raise EventStoreReplayError(
                f"Failed to replay events from stream {stream_id}: {str(e)}",
                stream_id=stream_id,
                from_version=from_version,
                to_version=to_version,
            ) from e
