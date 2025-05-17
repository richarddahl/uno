"""Dead letter queue implementation for handling failed events."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    TypeGuard,
    get_type_hints,
    overload,
    get_origin,
    get_args,
)

from typing_extensions import TypeAlias, Protocol, runtime_checkable

# Import Pydantic conditionally to support both v1 and v2
try:
    from pydantic import BaseModel as PydanticBaseModel
    from pydantic.version import VERSION as PYDANTIC_VERSION
    from pydantic.v1 import BaseModel as PydanticV1BaseModel  # type: ignore[attr-defined]
    
    PYDANTIC_AVAILABLE = True
    PYDANTIC_V2 = PYDANTIC_VERSION.startswith('2.')
    
    def is_pydantic_model(obj: object) -> TypeGuard[PydanticBaseModel | PydanticV1BaseModel]:
        """Check if an object is a Pydantic model (v1 or v2)."""
        return isinstance(obj, (PydanticBaseModel, PydanticV1BaseModel))
        
    def model_dump(model: PydanticBaseModel | PydanticV1BaseModel) -> dict[str, Any]:
        """Dump a Pydantic model to a dictionary, handling both v1 and v2."""
        if hasattr(model, 'model_dump'):  # Pydantic v2
            return model.model_dump()  # type: ignore[union-attr]
        return model.dict()  # type: ignore[union-attr]
        
except ImportError:
    PYDANTIC_AVAILABLE = False
    PYDANTIC_V2 = False
    PydanticBaseModel = object  # type: ignore[misc, assignment]
    PydanticV1BaseModel = object  # type: ignore[misc, assignment]
    
    def is_pydantic_model(obj: object) -> bool:  # type: ignore
        """Check if an object is a Pydantic model (always False when Pydantic is not available)."""
        return False
    
    def model_dump(model: object) -> dict[str, Any]:  # type: ignore
        """Dummy implementation when Pydantic is not available."""
        return {}

# Import local modules after Pydantic setup to avoid circular imports
from uno.core.logging import get_logger
from uno.metrics import Metrics
from uno.domain.protocols import DomainEventProtocol
from uno.logging import LoggerProtocol

# Import Callable and Awaitable at the top level to ensure they're always available
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    TypeGuard,
    get_type_hints,
    overload,
    get_origin,
    get_args,
)

# Type variable for generic event type (bound to DomainEventProtocol)
E = TypeVar('E', bound='DomainEventProtocol')  # type: ignore[valid-type, type-arg]

# Type aliases for event data and handlers
EventData = Dict[str, Any]

# Define handler types with proper variance
if TYPE_CHECKING:
    from typing_extensions import TypeAlias, TypeVar
    
    # Type variables for handlers with proper variance
    _T_contra = TypeVar('_T_contra', contravariant=True)
    
    # Handler type aliases with proper variance
    EventHandler: TypeAlias = Callable[[_T_contra], Awaitable[None]]
    DeadLetterHandler: TypeAlias = Callable[['DeadLetterEvent[Any]'], Awaitable[None]]
    RetryPolicy: TypeAlias = Callable[[int], Optional[float]]
    
    # Define a protocol for event handlers
    class EventHandlerProtocol(Protocol[_T_contra]):
        async def __call__(self, event: _T_contra) -> None:
            ...
            
    class DeadLetterHandlerProtocol(Protocol):
        async def __call__(self, event: 'DeadLetterEvent[Any]') -> None:
            ...
            
else:
    # Simplified types for runtime
    from typing import Any, Awaitable, Callable, Optional, TypeVar
    
    # Runtime type aliases (simplified for performance)
    EventHandler = Callable[[Any], Awaitable[None]]
    DeadLetterHandler = Callable[[Any], Awaitable[None]]
    RetryPolicy = Callable[[int], Optional[float]]
    
    # Dummy Protocol class for runtime
    class Protocol:
        pass

# Type aliases for better readability

# Protocol for events that can be serialized to a dictionary
class SerializableEvent(Protocol):
    """Protocol for events that can be serialized to a dictionary."""
    def dict(self) -> dict[str, Any]:
        """Convert the event to a dictionary."""
        ...

# EventData is now defined at the top level

# Type guard to check if an object is a Pydantic model
def is_pydantic_model(obj: Any) -> TypeGuard[Union[PydanticV1BaseModel, PydanticBaseModel]]:
    """Check if an object is a Pydantic model."""
    return (isinstance(obj, PydanticV1BaseModel) or 
           (PYDANTIC_V2 and isinstance(obj, PydanticBaseModel)))

# Re-export type aliases for use in other modules
__all__ = [
    'DeadLetterEvent',
    'DeadLetterQueue',
    'DeadLetterReason',
    'EventHandler',
    'DeadLetterHandler',
]

# Type guard for Pydantic models
def is_pydantic_model(obj: object) -> TypeGuard[Union[PydanticV1BaseModel, PydanticBaseModel]]:
    """Check if an object is a Pydantic model (v1 or v2)."""
    return isinstance(obj, (PydanticV1BaseModel, PydanticBaseModel)) if PYDANTIC_V2 else isinstance(obj, PydanticV1BaseModel)


class DeadLetterReason(str, Enum):
    """Reasons why an event was dead-lettered."""

    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    DESERIALIZATION_ERROR = "deserialization_error"
    HANDLER_ERROR = "handler_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class DeadLetterEvent(Generic[E]):
    """Represents an event that couldn't be processed."""

    event_data: EventData
    event_type: str
    reason: DeadLetterReason
    error_message: str | None = None
    error_type: str | None = None
    traceback: str | None = None
    subscription_id: str | None = None
    attempt_count: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_event(
        cls,
        event: E | dict[str, Any],
        reason: DeadLetterReason,
        error: Exception | None = None,
        subscription_id: str | None = None,
        attempt_count: int = 1,
        **metadata: Any
    ) -> 'DeadLetterEvent[E]':
        """Create a dead letter event from a failed event.
        
        Args:
            event: The original event that failed to process
            reason: The reason for dead-lettering
            error: The exception that caused the failure, if any
            subscription_id: The ID of the subscription that failed
            attempt_count: Number of attempts made to process the event
            **metadata: Additional metadata to include
            
        Returns:
            A new DeadLetterEvent instance
        """
        from uno.core.logging import get_logger
        
        logger = get_logger("uno.event_bus.dead_letter")
        event_data: EventData = {}
        event_type = 'UnknownEvent'
        
        # Handle Pydantic models and other event types
        try:
            if is_pydantic_model(event):
                # Handle Pydantic models
                try:
                    if PYDANTIC_V2:
                        # Pydantic v2 style - use model_dump()
                        event_data = cast('PydanticBaseModel', event).model_dump()
                    else:
                        # Handle Pydantic models using our helper function
                        event_data = model_dump(event)
                except Exception as e:
                    logger.warning(f"Failed to serialize Pydantic model: {e}")
                    # Fallback to object's __dict__
                    event_data = vars(event) if hasattr(event, '__dict__') else {}
                
                # Ensure we have a valid dictionary
                if not isinstance(event_data, dict):
                    # Last resort: get all non-private, non-callable attributes
                    event_data = {
                        k: getattr(event, k)
                        for k in dir(event)
                        if not k.startswith('_') and not callable(getattr(event, k))
                    }
                    
                # If we still don't have a valid dict, use string representation
                if not isinstance(event_data, dict):
                    event_data = {"__repr__": repr(event), "__str__": str(event)}
            except Exception as e:
                logger.warning(f"Failed to serialize event: {e}")
                event_data = {}
                
            # If we still don't have a valid dict, try other serialization methods
            if not event_data:
                try:
                    if hasattr(event, 'dict') and callable(event.dict):
                        # Handle other objects with dict() method
                        try:
                            event_data = event.dict()  # type: ignore[operator]
                        except Exception as e:
                            logger.warning(f"Failed to call dict() on event: {e}")
                            event_data = {}
                    elif hasattr(event, '__dict__'):
                        # Handle objects with __dict__ attribute
                        event_data = vars(event)
                    elif isinstance(event, dict):
                        # Handle plain dictionaries
                        event_data = dict(event)
                    else:
                        # Last resort: convert to string representation
                        event_data = {"__repr__": repr(event), "__str__": str(event)}
                    
                    # Ensure we have a valid dictionary
                    if not isinstance(event_data, dict):
                        event_data = {"__repr__": repr(event), "__str__": str(event)}
                except Exception as e:
                    logger.warning(f"Error during event serialization: {e}")
                    event_data = {"__repr__": repr(event), "__str__": str(event)}
                
            # Get the event type from the event object if available
            if hasattr(event, 'event_type'):
                event_type = str(event.event_type)
            elif isinstance(event, dict) and 'event_type' in event:
                event_type = str(event['event_type'])
                
        except Exception as e:
            logger.warning(
                "Failed to serialize event: %s",
                str(e),
                exc_info=True
            )
            event_data = {"error": f"Failed to serialize event: {str(e)}"}
            event_type = 'SerializationError'
            
        error_message = str(error) if error else None
        error_type = error.__class__.__name__ if error else None

        return cls(
            event_data=event_data,
            event_type=event_type,
            reason=reason,
            error_message=error_message,
            error_type=error_type,
            subscription_id=subscription_id,
            attempt_count=attempt_count,
            **metadata
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for storage."""
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["last_attempt_at"] = self.last_attempt_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeadLetterEvent[E]:
        """Create from a dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_attempt_at" in data and isinstance(data["last_attempt_at"], str):
            data["last_attempt_at"] = datetime.fromisoformat(data["last_attempt_at"])
        return cls(**data)


class DeadLetterQueue(Generic[E]):
    """
    A queue for storing and processing events that failed to be processed.
    
    This provides a way to handle failed events and potentially retry them later.
    
    Features:
    - Configurable retry policies with backoff strategies
    - Metrics integration for monitoring dead-lettered events
    - Thread-safe operations
    - Support for custom event handlers
    """
    
    def __init__(self, metrics: Metrics | None = None, logger: LoggerProtocol | None = None) -> None:
        self._queue: list[DeadLetterEvent[E]] = []
        self._handlers: dict[str, DeadLetterHandler] = {}
        self._metrics = metrics or Metrics.get_instance()
        self._logger = logger or get_logger("uno.event_bus.dead_letter")
        self._lock = asyncio.Lock()
        self._retry_policy: RetryPolicy = self._default_retry_policy
        self._max_retry_attempts = 3
        self._replay_in_progress = False
        self._replay_tasks: Set[asyncio.Task[None]] = set()
        self._replay_semaphore: asyncio.Semaphore | None = None
        
    @staticmethod
    def _default_retry_policy(attempt: int) -> float | None:
        """Default retry policy with exponential backoff.
        
        Args:
            attempt: The current attempt number (1-based)
            
        Returns:
            Delay in seconds before next retry, or None to stop retrying
        """
        if attempt > 3:  # Max 3 attempts by default
            return None
        return 0.5 * (2 ** (attempt - 1))  # Exponential backoff: 0.5s, 1s, 2s

    def set_retry_policy(
        self,
        policy: RetryPolicy | None = None,
        max_attempts: int | None = None
    ) -> None:
        """Set a custom retry policy for failed event processing.
        
        Args:
            policy: A callable that takes an attempt number and returns the delay in seconds
                   before the next retry, or None to stop retrying.
            max_attempts: Maximum number of retry attempts before giving up.
        """
        if policy is not None:
            self._retry_policy = policy
        if max_attempts is not None:
            self._max_retry_attempts = max_attempts

    async def add(
        self,
        event: E | dict[str, Any],
        reason: DeadLetterReason,
        error: Exception | None = None,
        subscription_id: str | None = None,
        attempt_count: int = 1,
        **metadata: Any
    ) -> None:
        """Add an event to the dead letter queue.
        
        Args:
            event: The event that failed to process
            reason: The reason the event is being dead-lettered
            error: The exception that caused the failure, if any
            subscription_id: The ID of the subscription that failed to process the event
            attempt_count: The number of attempts made to process the event
            **metadata: Additional metadata to attach to the dead letter event
        """
        dead_letter_event = DeadLetterEvent.from_event(
            event=event,
            reason=reason,
            error=error,
            subscription_id=subscription_id,
            attempt_count=attempt_count,
            **metadata
        )
        
        async with self._lock:
            self._queue.append(dead_letter_event)
            
        # Log and record metrics
        event_type = event.__class__.__name__ if not isinstance(event, dict) else "dict"
        self._logger.warning(
            "Event dead-lettered",
            event_type=event_type,
            reason=reason.value,
            error=str(error) if error else None,
            subscription_id=subscription_id or "",
            attempt_count=attempt_count,
        )
        
        self._metrics.increment(
            "event.dead_lettered",
            tags={
                "reason": reason.value,
                "event_type": event_type,
                "subscription_id": subscription_id or ""
            }
        )
        
        # Record the error if present
        if error:
            self._metrics.record_exception(
                error,
                tags={
                    "event_type": event_type,
                    "reason": reason.value,
                    "subscription_id": subscription_id or ""
                }
            )

    async def get(self) -> DeadLetterEvent[E]:
        """Get the next dead-lettered event."""
        async with self._lock:
            return self._queue.pop(0)

    async def process(
        self, event: E, next_: EventHandler
    ) -> None:
        """Process an event.
        
        Args:
            event: The event to process
            next_: The next handler in the middleware chain
            
        Raises:
            Exception: If the event processing fails and cannot be dead-lettered
        """
        try:
            await next_(event)
        except Exception as e:
            try:
                await self.add(event, DeadLetterReason.HANDLER_ERROR, error=e)
            except Exception as add_error:
                self._logger.error(
                    "Failed to add event to dead letter queue",
                    error=str(add_error),
                    event_type=type(event).__name__,
                )
                raise  # Re-raise the original error if we can't dead-letter

    def add_handler(self, handler: DeadLetterHandler) -> str:
        """Add a handler for dead letter events.
        
        Args:
            handler: A coroutine function that takes a DeadLetterEvent
            
        Returns:
            A unique ID that can be used to remove the handler later
        """
        handler_id = f"handler_{len(self._handlers)}_{id(handler)}"
        self._handlers[handler_id] = handler  # type: ignore[assignment]
        return handler_id

    def remove_handler(self, handler_id: str) -> None:
        """Remove a dead-letter handler."""
        try:
            del self._handlers[handler_id]
        except KeyError:
            pass
            
    async def replay_events(
        self,
        *,
        max_concurrent: int = 10,
        batch_size: int | None = None,
        filter_fn: Callable[[DeadLetterEvent[E]], bool] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        stop_event: asyncio.Event | None = None
    ) -> tuple[int, int]:
        """Replay dead letters with configurable concurrency.
        
        Args:
            max_concurrent: Maximum number of concurrent event replays
            batch_size: Maximum number of events to process in this batch (None for all)
            filter_fn: Optional filter function to select which events to replay
            progress_callback: Optional callback for progress updates (processed, total)
            stop_event: Optional event to signal early termination
            
        Returns:
            A tuple of (successful_count, failed_count)
            
        Raises:
            RuntimeError: If a replay is already in progress
        """
        if self._replay_in_progress:
            raise RuntimeError("Event replay is already in progress")
            
        self._replay_in_progress = True
        self._replay_semaphore = asyncio.Semaphore(max_concurrent)
        self._replay_tasks = set()
        
        try:
            # Create a copy of the queue to avoid modifying it during iteration
            async with self._lock:
                events_to_replay = self._queue.copy()
                
            # Apply filter if provided
            if filter_fn is not None:
                events_to_replay = [e for e in events_to_replay if filter_fn(e)]
                
            # Apply batch size limit if specified
            if batch_size is not None:
                events_to_replay = events_to_replay[:batch_size]
                
            total_events = len(events_to_replay)
            successful = 0
            failed = 0
            
            # Process events with limited concurrency
            for idx, dead_letter in enumerate(events_to_replay, 1):
                if stop_event and stop_event.is_set():
                    self._logger.info("Replay stopped by user request")
                    break
                    
                # Update progress
                if progress_callback:
                    progress_callback(idx, total_events)
                    
                # Process the event with concurrency control
                task = asyncio.create_task(self._process_single_replay(dead_letter))
                self._replay_tasks.add(task)
                task.add_done_callback(self._replay_tasks.discard)
                
                # Wait for a slot to become available if we've reached max concurrency
                if len(self._replay_tasks) >= max_concurrent:
                    done, _ = await asyncio.wait(
                        self._replay_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Update success/failure counts
                    for completed_task in done:
                        if completed_task.exception() is None:
                            successful += 1
                        else:
                            failed += 1
                            self._logger.error(
                                "Error processing event",
                                exc_info=completed_task.exception()
                            )
            
            # Wait for any remaining tasks to complete
            if self._replay_tasks:
                done, _ = await asyncio.wait(
                    self._replay_tasks,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                # Update success/failure counts for remaining tasks
                for completed_task in done:
                    if completed_task.exception() is None:
                        successful += 1
                    else:
                        failed += 1
                        self._logger.error(
                            "Error processing event",
                            exc_info=completed_task.exception()
                        )
            
            return successful, failed
            
        finally:
            self._replay_in_progress = False
            self._replay_tasks.clear()
            self._replay_semaphore = None
            
    async def _process_single_replay(self, dead_letter: DeadLetterEvent[E]) -> None:
        """Process a single dead letter during replay.
        
        This method is called by `replay_events` for each event being replayed.
        """
        if self._replay_semaphore is None:
            raise RuntimeError("Replay not initialized")
            
        async with self._replay_semaphore:
            try:
                # Reconstruct the original event
                event = self._reconstruct_event(dead_letter)
                
                # Call all handlers
                for handler in self._handlers.values():
                    await handler(event)
                    
                # If we get here, processing was successful
                async with self._lock:
                    if dead_letter in self._queue:
                        self._queue.remove(dead_letter)
                        
            except Exception as e:
                # Update the dead letter with the error
                dead_letter.attempt_count += 1
                dead_letter.last_attempt_at = datetime.utcnow()
                dead_letter.error_message = str(e)
                dead_letter.error_type = type(e).__name__
                
                self._logger.error(
                    "Failed to replay dead letter",
                    exc_info=True,
                    extra={"dead_letter": dead_letter.to_dict()}
                )
                raise
                
    def is_replay_in_progress(self) -> bool:
        """Check if an event replay is currently in progress."""
        return self._replay_in_progress
        
    def cancel_replay(self) -> None:
        """Cancel any in-progress event replay."""
        if not self._replay_in_progress:
            return
            
        for task in self._replay_tasks:
            if not task.done():
                task.cancel()
                
        self._replay_tasks.clear()
        self._replay_in_progress = False
        self._replay_semaphore = None
        
    def _reconstruct_event(self, dead_letter: DeadLetterEvent[E]) -> E:
        """Reconstruct the original event from a dead letter.
        
        This is a simplified implementation. In a real application, you would need
        to implement proper deserialization based on your event model.
        """
        # This is a simplified implementation - in practice, you'd want to use
        # your event deserialization logic here
        event_data = dead_letter.event_data
        
        # If the original event was a Pydantic model, try to reconstruct it
        if hasattr(E, "model_validate"):  # Pydantic v2
            return E.model_validate(event_data)  # type: ignore
        elif hasattr(E, "parse_obj"):  # Pydantic v1
            return E.parse_obj(event_data)  # type: ignore
        else:
            # Fallback to creating a dictionary with the event data
            return event_data  # type: ignore
