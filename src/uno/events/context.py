# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Context for event processing.

This module provides context objects for working with events,
ensuring proper context propagation and cancellation support.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, Self, AsyncGenerator, TypeVar
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from uno.domain.protocols import DomainEventProtocol

T = TypeVar("T", bound="DomainEventProtocol")


class EventContext(BaseModel):
    """
    Context information for event processing.

    This class provides a standardized way to pass context information
    along with events through the event processing pipeline.
    """

    correlation_id: str | None = Field(None, description="Correlation ID for tracing")
    causation_id: str | None = Field(
        None, description="ID of the event that caused this event"
    )
    user_id: str | None = Field(
        None, description="ID of the user who caused this event"
    )
    source: str | None = Field(None, description="Source system or component")
    cancellation_token: Any = Field(
        None, description="Token that can be used to cancel processing"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(
        frozen=True,  # Context objects are immutable
        arbitrary_types_allowed=True,
    )

    @classmethod
    def create(
        cls,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        user_id: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        cancellation_token: Any = None,
    ) -> Self:
        """
        Create a new context with the specified values.

        Args:
            correlation_id: Correlation ID for tracing
            causation_id: ID of the event that caused this event
            user_id: ID of the user who caused this event
            source: Source system or component
            metadata: Additional metadata
            cancellation_token: Token that can be used to cancel processing

        Returns:
            A new context instance
        """
        return cls(
            correlation_id=correlation_id,
            causation_id=causation_id,
            user_id=user_id,
            source=source,
            metadata=metadata or {},
            cancellation_token=cancellation_token,
        )

    def with_cancellation(self, cancellation_token: Any) -> Self:
        """
        Create a new context with the specified cancellation token.

        Args:
            cancellation_token: Token that can be used to cancel processing

        Returns:
            A new context instance with the cancellation token
        """
        return self.model_copy(update={"cancellation_token": cancellation_token})


class EventHandlerContext(BaseModel):
    """
    Context object passed to event handlers and middleware.

    Encapsulates the event and any relevant metadata for processing.
    """

    event: DomainEventProtocol
    metadata: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(
        default_factory=dict
    )  # Added from other implementation
    cancellation_token: Any = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Canonical serialization: returns dict using Uno contract.

        Uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).

        Returns:
            Dictionary representation of the context
        """
        return self.model_dump(
            exclude={"cancellation_token"},
            exclude_none=True,
            exclude_unset=True,
            by_alias=True,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create a context from a dictionary.

        Args:
            data: Dictionary containing context data

        Returns:
            A new context instance
        """
        return cls.model_validate(data)

    def get_typed_event(self, event_type: type[T]) -> T:
        """
        Get the event as a specific type.

        This is a convenience method for handlers that know the
        expected event type and want to avoid repetitive casting.

        Args:
            event_type: The expected event type

        Returns:
            The event cast to the specified type

        Raises:
            TypeError: If the event is not of the expected type
        """
        if not isinstance(self.event, event_type):
            raise TypeError(
                f"Expected event of type {event_type.__name__}, got {type(self.event).__name__}"
            )

        return self.event  # Type system will handle the cast

    def with_extra(self, key: str, value: Any) -> Self:
        """
        Return a new context with an extra value added.

        This is a convenience method for adding extra data to the context
        without mutating the original context.

        Args:
            key: The key for the extra data
            value: The value to add

        Returns:
            A new context with the extra data added
        """
        new_extra = self.extra.copy()
        new_extra[key] = value
        return self.model_copy(update={"extra": new_extra})

    @contextlib.asynccontextmanager
    async def cancellation_scope(self) -> AsyncGenerator[None, None]:
        """
        Context manager for cancellation handling.

        Use this to create a scope that can be cancelled if the
        cancellation token is triggered.

        Example:
            ```python
            async with context.cancellation_scope():
                # This code will be cancelled if the token is triggered
                await some_long_running_operation()
            ```

        Raises:
            asyncio.CancelledError: If cancellation is triggered

        Yields:
            None
        """
        if self.cancellation_token is None:
            # No cancellation, just yield
            yield
            return

        # Setup cancellation monitoring
        monitor_task = None

        # Define a monitoring coroutine that will cancel the current task
        async def monitor_cancellation():
            current_task = asyncio.current_task()
            if current_task is None:
                return

            try:
                # Different types of cancellation tokens might have different interfaces
                if hasattr(self.cancellation_token, "wait"):
                    await self.cancellation_token.wait()
                elif hasattr(self.cancellation_token, "cancelled"):
                    await self.cancellation_token.cancelled()
                elif isinstance(self.cancellation_token, asyncio.Event):
                    await self.cancellation_token.wait()
                else:
                    # If the token doesn't have a standard interface, wait forever
                    # The context manager will clean up when exiting
                    while True:
                        await asyncio.sleep(0.1)

                # If we get here, the token was triggered, so cancel the task
                current_task.cancel()
            except asyncio.CancelledError:
                # The monitor task itself was cancelled, which is fine
                pass

        # Start monitoring in a separate task
        monitor_task = asyncio.create_task(monitor_cancellation())

        try:
            # Yield control back to the caller
            yield
        finally:
            # Always clean up the monitor task
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await monitor_task
