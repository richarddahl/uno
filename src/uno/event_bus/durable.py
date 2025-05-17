"""Durable subscription and retry policies for the event bus."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    TypeVar,
    cast,
)

from pydantic import BaseModel, Field

from uno.domain.protocols import DomainEventProtocol
from uno.logging import LoggerProtocol
from uno.event_bus.protocols import EventHandlerProtocol

E = TypeVar("E", bound=DomainEventProtocol)


class RetryPolicyType(str, Enum):
    """Types of retry policies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


class SubscriptionState(str, Enum):
    """State of a durable subscription."""

    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


class RetryPolicy(BaseModel):
    """Configuration for retrying failed event processing.

    Attributes:
        max_attempts: Maximum number of retry attempts (0 for no retry)
        initial_delay_ms: Initial delay between retries in milliseconds
        max_delay_ms: Maximum delay between retries in milliseconds
        backoff_factor: Multiplier for delay between retries
        policy_type: Type of backoff policy to use
    """

    max_attempts: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_factor: float = 2.0
    policy_type: RetryPolicyType = RetryPolicyType.EXPONENTIAL

    def get_delay_ms(self, attempt: int) -> int:
        """Calculate delay for a specific retry attempt.

        Args:
            attempt: Current attempt number (1-based)

        Returns:
            Delay in milliseconds
        """
        if attempt <= 0:
            return 0

        if self.policy_type == RetryPolicyType.FIXED:
            delay = self.initial_delay_ms
        elif self.policy_type == RetryPolicyType.EXPONENTIAL:
            delay = int(self.initial_delay_ms * (self.backoff_factor ** (attempt - 1)))
        elif self.policy_type == RetryPolicyType.FIBONACCI:
            a, b = 0, self.initial_delay_ms
            for _ in range(attempt):
                a, b = b, a + b
            delay = min(a, self.max_delay_ms)
        else:
            delay = self.initial_delay_ms

        return min(delay, self.max_delay_ms)


@dataclass
class DurableSubscription(Generic[E]):
    """Represents a durable subscription to an event stream.

    Attributes:
        subscription_id: Unique identifier for the subscription
        event_type: Type of event being subscribed to
        handler: Callback function to process events
        retry_policy: Policy for retrying failed events
        state: Current state of the subscription
        last_error: Last error that occurred, if any
        error_count: Number of consecutive failures
        last_processed_at: Timestamp of last successful processing
        created_at: When the subscription was created
    """

    subscription_id: str
    event_type: type[E]
    handler: EventHandlerProtocol[E]
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    state: SubscriptionState = SubscriptionState.ACTIVE
    last_error: Optional[Exception] = None
    error_count: int = 0
    last_processed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    async def process_event(self, event: E) -> None:
        """Process an event with retry logic.

        Args:
            event: The event to process

        Raises:
            Exception: If all retry attempts are exhausted
        """
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.retry_policy.max_attempts:
            try:
                if attempt > 0:
                    # Calculate and wait for backoff
                    delay_ms = self.retry_policy.get_delay_ms(attempt)
                    await asyncio.sleep(delay_ms / 1000.0)

                # Attempt to process the event
                await self.handler.handle(event)

                # Update state on success
                self.error_count = 0
                self.last_error = None
                self.last_processed_at = datetime.utcnow()
                return

            except Exception as e:
                last_error = e
                self.error_count += 1
                self.last_error = e
                attempt += 1

        # If we get here, all retries failed
        self.state = SubscriptionState.FAILED
        if last_error:
            raise last_error


class DurableSubscriptionManager(Generic[E]):
    """Manages durable subscriptions and their lifecycle."""

    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize the subscription manager.

        Args:
            logger: Logger instance for logging subscription events
        """
        self._logger = logger
        self._subscriptions: dict[str, DurableSubscription[E]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        event_type: type[E],
        handler: EventHandlerProtocol[E],
        subscription_id: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> DurableSubscription[E]:
        """Create a new durable subscription.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to process events
            subscription_id: Optional custom subscription ID
            retry_policy: Optional custom retry policy

        Returns:
            The created subscription
        """
        if subscription_id is None:
            subscription_id = f"sub_{int(time.time() * 1000)}"

        subscription = DurableSubscription[event_type](
            subscription_id=subscription_id,
            event_type=event_type,
            handler=handler,
            retry_policy=retry_policy or RetryPolicy(),
        )

        async with self._lock:
            if subscription_id in self._subscriptions:
                raise ValueError(f"Subscription {subscription_id} already exists")
            self._subscriptions[subscription_id] = subscription

        self._logger.info(
            "Created durable subscription",
            subscription_id=subscription_id,
            event_type=event_type.__name__,
        )

        return subscription

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription.

        Args:
            subscription_id: ID of the subscription to remove

        Returns:
            True if the subscription was removed, False if not found
        """
        async with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                self._logger.info(
                    "Removed subscription", subscription_id=subscription_id
                )
                return True
            return False

    async def get_subscription(
        self, subscription_id: str
    ) -> Optional[DurableSubscription[E]]:
        """Get a subscription by ID.

        Args:
            subscription_id: ID of the subscription to retrieve

        Returns:
            The subscription if found, None otherwise
        """
        return self._subscriptions.get(subscription_id)

    async def process_event(self, event: E) -> None:
        """Process an event through all matching subscriptions.

        Args:
            event: The event to process
        """
        event_type = type(event)
        tasks = []

        # Get a snapshot of active subscriptions
        async with self._lock:
            subscriptions = [
                sub
                for sub in self._subscriptions.values()
                if sub.state == SubscriptionState.ACTIVE
                and isinstance(event, sub.event_type)
            ]

        # Process event in parallel for all matching subscriptions
        for subscription in subscriptions:
            tasks.append(
                asyncio.create_task(
                    self._process_for_subscription(subscription, event),
                    name=f"process-{subscription.subscription_id}",
                )
            )

        # Wait for all processing to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_for_subscription(
        self, subscription: DurableSubscription[E], event: E
    ) -> None:
        """Process an event for a specific subscription."""
        try:
            await subscription.process_event(event)
        except Exception as e:
            self._logger.error(
                "Error processing event for subscription",
                subscription_id=subscription.subscription_id,
                event_type=type(event).__name__,
                error=str(e),
                exc_info=True,
            )
