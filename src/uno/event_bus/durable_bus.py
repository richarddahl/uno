"""Durable event bus implementation with subscription management and retry policies."""

from __future__ import annotations

import asyncio
import importlib
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, cast

from pydantic import BaseModel

from uno.domain.protocols import DomainEventProtocol
from uno.event_bus.base import EventBus
from uno.event_bus.dead_letter import DeadLetterQueue, DeadLetterReason
from uno.event_bus.durable import (
    DurableSubscription,
    DurableSubscriptionManager,
    RetryPolicy,
    SubscriptionState as DurableSubscriptionState,
)
from uno.event_bus.metrics_integration import EventBusMetrics, MetricsMiddleware
from uno.event_bus.persistence import (
    InMemorySubscriptionStore,
    StoredSubscription,
    SubscriptionPersistence,
    SubscriptionState as PersistedSubscriptionState,
)
from uno.event_bus.protocols import EventHandlerProtocol, EventMiddlewareProtocol
from uno.logging import LoggerProtocol

# Re-export SubscriptionState for backward compatibility
SubscriptionState = DurableSubscriptionState

__all__ = [
    "DurableEventBus",
    "SubscriptionState",
    "DeadLetterQueue",
    "DeadLetterReason",
    "RetryPolicy",
    "SubscriptionState",
    "EventBusMetrics",
    "MetricsCollector",
    "MetricsMiddleware",
]

E = TypeVar("E", bound=DomainEventProtocol)


class DurableEventBus(EventBus[E]):
    """Event bus implementation with durable subscriptions and retry policies.

    This implementation extends the base EventBus with support for durable
    subscriptions, retry policies, and subscription management.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        dead_letter_queue: Optional[DeadLetterQueue[E]] = None,
        subscription_store: Optional[SubscriptionPersistence[E]] = None,
        metrics: Optional[EventBusMetrics] = None,
    ) -> None:
        """Initialize the durable event bus.

        Args:
            logger: Logger instance for logging events and errors
            dead_letter_queue: Optional dead letter queue for unprocessable events
            subscription_store: Optional store for persisting subscriptions
            metrics: Optional metrics collector for monitoring
        """
        super().__init__(logger)
        
        # Initialize dead letter queue if not provided
        self._dead_letter_queue = dead_letter_queue or DeadLetterQueue[E](logger)
        
        # Initialize subscription persistence
        self._subscription_store = subscription_store or SubscriptionPersistence[E](
            InMemorySubscriptionStore[E](), logger
        )
        
        # Initialize metrics
        self._metrics = metrics or EventBusMetrics(logger)
        
        # Initialize middleware list from parent class
        self._middleware: list[EventMiddlewareProtocol[E]] = []
            
        # Register metrics middleware if metrics is available
        if hasattr(self, '_metrics'):
            middleware = MetricsMiddleware[E](self._metrics)
            self._middleware.append(middleware)
            
    def add_middleware(self, middleware: EventMiddlewareProtocol[E]) -> None:
        """Add middleware to the event bus.
        
        Args:
            middleware: The middleware to add to the event bus
        """
        self._middleware.append(middleware)
        
        # Initialize subscription manager
        self._subscription_manager = DurableSubscriptionManager[E](logger)
        
        # Load persisted subscriptions
        self._subscription_loader_task = asyncio.create_task(self._load_persisted_subscriptions())
        
        # Register a default handler that forwards events to all matching subscriptions
        self._default_handler: Optional[EventHandlerProtocol] = None
        self._register_default_handler()

    def _register_default_handler(self) -> None:
        """Register the default event handler for durable subscriptions."""
        bus = self  # Capture self for use in the closure
        
        class DefaultHandler:
            def __init__(self, bus: DurableEventBus[E]) -> None:
                self._bus = bus
                
            async def handle(self, event: DomainEventProtocol) -> None:
                # Forward the event to all matching subscriptions
                for subscription in bus._subscription_manager.get_subscriptions_for_event(event):
                    try:
                        await subscription.handler(event)
                        # Record success in metrics if metrics is available
                        if hasattr(bus, '_metrics'):
                            bus._metrics.record_event_processed(event, 0, success=True)
                    except Exception as e:
                        if hasattr(bus, '_logger'):
                            bus._logger.error(
                                f"Error in subscription {subscription.id} for event {event.__class__.__name__}",
                                exc_info=True,
                            )
                        # Record failure in metrics if metrics is available
                        if hasattr(bus, '_metrics'):
                            bus._metrics.record_event_processed(event, 0, success=False)
                        # Re-raise to allow for retry logic
                        raise
        
        # Create and set the default handler
        self._default_handler = DefaultHandler(self)

    async def create_durable_subscription(
        self,
        event_type: Type[E],
        handler: Callable[[E], Awaitable[Any]],
        subscription_id: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
        persist: bool = True,
        **metadata: Any,
    ) -> DurableSubscription[E]:
        """Create a new durable subscription.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to process events
            subscription_id: Optional custom subscription ID
            retry_policy: Optional custom retry policy
            persist: Whether to persist this subscription
            **metadata: Additional metadata to store with the subscription

        Returns:
            The created subscription

        Raises:
            ValueError: If a subscription with the same ID already exists
        """
        # Create the subscription
        subscription = await self._subscription_manager.subscribe(
            event_type=event_type,
            handler=handler,
            subscription_id=subscription_id,
            retry_policy=retry_policy,
        )
        
        # Persist if requested
        if persist:
            await self._persist_subscription(subscription, **metadata)
            
        return subscription
        
    async def _persist_subscription(
        self, subscription: DurableSubscription[E], **metadata: Any
    ) -> None:
        """Persist a subscription to the store.
        
        Args:
            subscription: The subscription to persist
            **metadata: Additional metadata to store with the subscription
        """
        # Get the handler's module and name for reloading
        handler_module = subscription.handler.__class__.__module__
        handler_name = subscription.handler.__class__.__name__
        
        # Create a stored subscription
        stored_sub = StoredSubscription[E](
            subscription_id=subscription.subscription_id,
            event_type=subscription.event_type.__name__,
            handler_module=handler_module,
            handler_name=handler_name,
            state=PersistedSubscriptionState(subscription.state.value),
            config={
                "retry_policy": {
                    "max_attempts": subscription.retry_policy.max_attempts,
                    "initial_delay_ms": subscription.retry_policy.initial_delay_ms,
                    "max_delay_ms": subscription.retry_policy.max_delay_ms,
                    "backoff_factor": subscription.retry_policy.backoff_factor,
                    "policy_type": subscription.retry_policy.policy_type.value,
                }
            },
            metadata=metadata,
        )
        
        # Save to the store
        await self._subscription_store.save_subscription(stored_sub)

    async def remove_durable_subscription(
        self, subscription_id: str, delete_persisted: bool = True
    ) -> bool:
        """Remove a durable subscription.

        Args:
            subscription_id: ID of the subscription to remove
            delete_persisted: Whether to also delete the persisted subscription

        Returns:
            True if the subscription was removed, False if not found
        """
        # Remove from the manager
        result = await self._subscription_manager.unsubscribe(subscription_id)
        
        # Remove from persistence if requested and found
        if result and delete_persisted:
            await self._subscription_store.delete_subscription(subscription_id)
            
        return result

    async def get_durable_subscription(
        self, subscription_id: str
    ) -> Optional[DurableSubscription[E]]:
        """Get a durable subscription by ID.

        Args:
            subscription_id: ID of the subscription to retrieve

        Returns:
            The subscription if found, None otherwise
        """
        return await self._subscription_manager.get_subscription(subscription_id)

    async def _process_event(self, event: E) -> None:
        """Process an event through middleware and handlers.

        This overrides the base implementation to include durable subscriptions.

        Args:
            event: The event to process
        """
        try:
            # First process through middleware
            async def process_middleware(
                middleware: EventMiddlewareProtocol[E], e: E
            ) -> None:
                await middleware.process(
                    e, lambda x: asyncio.create_task(process_middleware(middleware, x))
                )

            # Process through middleware chain
            for middleware in self._middleware:
                await process_middleware(middleware, event)

            # Then forward to all matching handlers and subscriptions
            event_type = type(event).__name__
            handlers = self._handlers.get(event_type, [])

            # Process with regular handlers
            if handlers:
                await asyncio.gather(
                    *(handler(event) for handler in handlers),
                    return_exceptions=True,
                )

            # Process with durable subscriptions if no specific handlers
            elif self._default_handler:
                await self._default_handler.handle(event)
                
        except Exception as e:
            # Record the error in metrics
            if hasattr(self, '_metrics'):
                self._metrics.record_dead_letter(
                    event,
                    reason="unhandled_exception",
                    error=e,
                )
            # Re-raise to allow other error handling to proceed
            raise
                    
                # Recreate the subscription
                await self.create_durable_subscription(
                    event_type=self._get_event_type(stored_sub.event_type),
                    handler=handler,
                    subscription_id=stored_sub.subscription_id,
                    retry_policy=retry_policy,
                    persist=False,  # Already persisted
                    **stored_sub.metadata,
                )
                
                self._logger.info(
                    "Restored subscription",
                    subscription_id=stored_sub.subscription_id,
                    event_type=stored_sub.event_type,
                )
                    
                except Exception as e:
                    self._logger.error(
                        "Failed to restore subscription",
                        subscription_id=stored_sub.subscription_id,
                        error=str(e),
                        exc_info=True,
                    )
                    
        except Exception as e:
            self._logger.error(
                "Error loading persisted subscriptions",
                error=str(e),
                exc_info=True,
            )
            
    def _get_event_type(self, type_name: str) -> Type[E]:
        """Get an event type by name.
        
        Args:
            type_name: The name of the event type to get
            
        Returns:
            The event type class
            
        Raises:
            ValueError: If the event type cannot be found
        """
        # This is a simplified implementation - in a real app,
        # you'd want to maintain a registry of event types
        for cls in DomainEventProtocol.__subclasses__():
            if cls.__name__ == type_name:
                return cast(Type[E], cls)
                
        raise ValueError(f"Unknown event type: {type_name}")
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get the current metrics.
        
        Returns:
            A dictionary of metric data
        """
        if hasattr(self, '_metrics'):
            return self._metrics.get_metrics()
        return {}
        
    @property
    def dead_letter_queue(self) -> DeadLetterQueue[E]:
        """Get the dead letter queue.
        
        Returns:
            The dead letter queue instance
        """
        return self._dead_letter_queue
        
    async def close(self) -> None:
        """Clean up resources used by the event bus."""
        # Cancel the subscription loader task if it exists and is running
        if hasattr(self, '_subscription_loader_task') and not self._subscription_loader_task.done():
            self._subscription_loader_task.cancel()
            try:
                await self._subscription_loader_task
            except asyncio.CancelledError:
                pass
                
        # Close the dead letter queue if it exists and has a close method
        if hasattr(self, '_dead_letter_queue') and hasattr(self._dead_letter_queue, 'close'):
            await self._dead_letter_queue.close()
            
        # Cancel any pending tasks
        if hasattr(self, '_pending_tasks'):
            for task in self._pending_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
        # Call parent class close if it exists and is a coroutine function
        parent_close = getattr(super(), 'close', None)
        if parent_close and asyncio.iscoroutinefunction(parent_close):
            await parent_close()
