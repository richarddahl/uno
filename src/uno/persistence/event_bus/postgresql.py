"""PostgreSQL LISTEN/NOTIFY implementation for event subscriptions."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Set, TypeVar

import asyncpg

from uno.domain.events import DomainEvent
from uno.event_store.errors import EventStoreError

# Type variable for events
E = TypeVar('E', bound=DomainEvent)

# Type alias for event handler callbacks
EventHandler = Callable[[DomainEvent], None]


@dataclass
class Subscription:
    """Represents an active subscription to a PostgreSQL channel."""
    
    channel: str
    connection: asyncpg.Connection
    task: asyncio.Task[None]
    handlers: Set[EventHandler] = field(default_factory=set)
    
    async def close(self) -> None:
        """Close the subscription and cleanup resources."""
        if not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self.connection.remove_listener(
            self.channel,
            self._notification_handler
        )
    
    def _notification_handler(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str
    ) -> None:
        """Handle incoming notifications."""
        try:
            event_data = json.loads(payload)
            event = DomainEvent.model_validate(event_data)
            for handler in self.handlers:
                try:
                    handler(event)
                except Exception as e:
                    logging.error(
                        "Error in event handler for channel %s: %s",
                        channel, str(e),
                        exc_info=True
                    )
        except json.JSONDecodeError as e:
            logging.error(
                "Failed to decode notification payload on channel %s: %s",
                channel, str(e)
            )
        except Exception as e:
            logging.error(
                "Unexpected error processing notification on channel %s: %s",
                channel, str(e),
                exc_info=True
            )


class SubscriptionManager:
    """Manages PostgreSQL LISTEN/NOTIFY subscriptions.
    
    This class handles the lifecycle of subscriptions and ensures proper
    cleanup of resources.
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        """Initialize the subscription manager.
        
        Args:
            connection_pool: The connection pool to use for subscriptions.
        """
        self._pool = connection_pool
        self._subscriptions: Dict[str, Subscription] = {}
        self._lock = asyncio.Lock()
    
    async def subscribe(
        self,
        channel: str,
        handler: EventHandler
    ) -> None:
        """Subscribe to a channel with the given handler.
        
        Args:
            channel: The channel to subscribe to.
            handler: The callback to invoke when an event is received.
            
        Raises:
            EventStoreError: If the subscription fails.
        """
        async with self._lock:
            if channel not in self._subscriptions:
                try:
                    connection = await self._pool.acquire()
                    await connection.execute(f"LISTEN \"{channel}\"")
                    
                    # Create a task to listen for notifications
                    task = asyncio.create_task(self._listen_for_notifications(connection, channel))
                    
                    # Create and store the subscription
                    subscription = Subscription(channel, connection, task)
                    self._subscriptions[channel] = subscription
                    
                    # Add the notification handler
                    connection.add_listener(channel, subscription._notification_handler)
                    
                except Exception as e:
                    if 'connection' in locals():
                        await self._pool.release(connection)
                    raise EventStoreError(f"Failed to subscribe to channel {channel}: {str(e)}") from e
            
            # Add the handler to the subscription
            self._subscriptions[channel].handlers.add(handler)
    
    async def unsubscribe(self, channel: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from a channel.
        
        Args:
            channel: The channel to unsubscribe from.
            handler: The handler to remove.
        """
        async with self._lock:
            if channel in self._subscriptions:
                subscription = self._subscriptions[channel]
                subscription.handlers.discard(handler)
                
                # If no more handlers, clean up the subscription
                if not subscription.handlers:
                    await self._remove_subscription(channel)
    
    async def _remove_subscription(self, channel: str) -> None:
        """Remove and clean up a subscription."""
        subscription = self._subscriptions.pop(channel, None)
        if subscription:
            await subscription.close()
            await self._pool.release(subscription.connection)
    
    async def _listen_for_notifications(
        self,
        connection: asyncpg.Connection,
        channel: str
    ) -> None:
        """Continuously listen for notifications on a connection."""
        try:
            while True:
                await connection.wait_for_notify()
        except asyncio.CancelledError:
            # Cleanup on cancellation
            await connection.remove_all_listeners()
            raise
        except Exception as e:
            logging.error(
                "Error in notification listener for channel %s: %s",
                channel, str(e),
                exc_info=True
            )
            # Re-raise to trigger task completion
            raise
    
    async def close(self) -> None:
        """Close all subscriptions and release resources."""
        async with self._lock:
            for channel in list(self._subscriptions.keys()):
                await self._remove_subscription(channel)
    
    async def __aenter__(self) -> "SubscriptionManager":
        """Context manager entry."""
        return self
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Context manager exit.
        
        Args:
            exc_type: Exception type if an exception was raised, None otherwise.
            exc_val: Exception value if an exception was raised, None otherwise.
            exc_tb: Traceback if an exception was raised, None otherwise.
        """
        await self.close()
