"""Persistence for event bus subscriptions."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseModel, Field

from uno.domain.protocols import DomainEventProtocol
from uno.logging import LoggerProtocol
from uno.event_bus.dead_letter import DeadLetterEvent, DeadLetterReason

E = TypeVar("E", bound=DomainEventProtocol)


class SubscriptionState(str, Enum):
    """State of a subscription."""

    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass
class StoredSubscription(Generic[E]):
    """A subscription that can be persisted."""

    subscription_id: str
    event_type: str
    handler_module: str
    handler_name: str
    state: SubscriptionState = SubscriptionState.ACTIVE
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for storage."""
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        result["state"] = self.state.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StoredSubscription[E]:
        """Create from a dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if "state" in data and isinstance(data["state"], str):
            data["state"] = SubscriptionState(data["state"])
        return cls(**data)


class SubscriptionStore(ABC, Generic[E]):
    """Abstract base class for subscription storage."""

    @abstractmethod
    async def save(self, subscription: StoredSubscription[E]) -> None:
        """Save a subscription.
        
        Args:
            subscription: The subscription to save
        """
        raise NotImplementedError

    @abstractmethod
    async def load(self, subscription_id: str) -> Optional[StoredSubscription[E]]:
        """Load a subscription by ID.
        
        Args:
            subscription_id: The ID of the subscription to load
            
        Returns:
            The subscription if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, subscription_id: str) -> bool:
        """Delete a subscription.
        
        Args:
            subscription_id: The ID of the subscription to delete
            
        Returns:
            True if the subscription was deleted, False if not found
        """
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self, state: Optional[SubscriptionState] = None
    ) -> AsyncIterator[StoredSubscription[E]]:
        """List all subscriptions, optionally filtered by state.
        
        Args:
            state: If provided, only return subscriptions with this state
            
        Yields:
            StoredSubscription objects matching the criteria
        """
        raise NotImplementedError


class InMemorySubscriptionStore(SubscriptionStore[E]):
    """In-memory implementation of SubscriptionStore."""

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._store: Dict[str, StoredSubscription[E]] = {}
        self._lock = asyncio.Lock()

    async def save(self, subscription: StoredSubscription[E]) -> None:
        """Save a subscription."""
        async with self._lock:
            self._store[subscription.subscription_id] = subscription

    async def load(self, subscription_id: str) -> Optional[StoredSubscription[E]]:
        """Load a subscription by ID."""
        return self._store.get(subscription_id)

    async def delete(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        async with self._lock:
            if subscription_id in self._store:
                del self._store[subscription_id]
                return True
            return False

    async def list_all(
        self, state: Optional[SubscriptionState] = None
    ) -> AsyncIterator[StoredSubscription[E]]:
        """List all subscriptions, optionally filtered by state."""
        for sub in self._store.values():
            if state is None or sub.state == state:
                yield sub


class SubscriptionPersistence(Generic[E]):
    """Manages persistence of subscriptions."""

    def __init__(
        self, store: SubscriptionStore[E], logger: LoggerProtocol
    ) -> None:
        """Initialize with a subscription store.
        
        Args:
            store: The subscription store to use
            logger: Logger instance for logging
        """
        self._store = store
        self._logger = logger

    async def save_subscription(
        self, subscription: StoredSubscription[E]
    ) -> None:
        """Save a subscription.
        
        Args:
            subscription: The subscription to save
        """
        try:
            await self._store.save(subscription)
            self._logger.debug(
                "Subscription saved",
                subscription_id=subscription.subscription_id,
                event_type=subscription.event_type,
            )
        except Exception as e:
            self._logger.error(
                "Failed to save subscription",
                subscription_id=subscription.subscription_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def load_subscription(
        self, subscription_id: str
    ) -> Optional[StoredSubscription[E]]:
        """Load a subscription by ID.
        
        Args:
            subscription_id: The ID of the subscription to load
            
        Returns:
            The subscription if found, None otherwise
        """
        try:
            return await self._store.load(subscription_id)
        except Exception as e:
            self._logger.error(
                "Failed to load subscription",
                subscription_id=subscription_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription.
        
        Args:
            subscription_id: The ID of the subscription to delete
            
        Returns:
            True if the subscription was deleted, False if not found
        """
        try:
            result = await self._store.delete(subscription_id)
            if result:
                self._logger.debug(
                    "Subscription deleted", subscription_id=subscription_id
                )
            return result
        except Exception as e:
            self._logger.error(
                "Failed to delete subscription",
                subscription_id=subscription_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def list_subscriptions(
        self, state: Optional[SubscriptionState] = None
    ) -> List[StoredSubscription[E]]:
        """List all subscriptions, optionally filtered by state.
        
        Args:
            state: If provided, only return subscriptions with this state
            
        Returns:
            List of matching subscriptions
        """
        try:
            return [sub async for sub in self._store.list_all(state=state)]
        except Exception as e:
            self._logger.error(
                "Failed to list subscriptions",
                state=state.value if state else None,
                error=str(e),
                exc_info=True,
            )
            raise
