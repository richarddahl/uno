"""
AggregateRoot base class for Uno's DDD/event sourcing model.
"""

from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING, Any, cast

from pydantic import ConfigDict

if TYPE_CHECKING:
    from uno.domain.protocols import (
        DomainEventProtocol,
        EventPublisherProtocol,
    )
    from uno.logging.protocols import LoggerProtocol

from uno.domain.entity import Entity
from uno.domain.errors import AggregateNotDeletedError
from uno.events.deleted_event import DeletedEvent
from uno.events.restored_event import RestoredEvent
from uno.injection import Container
from uno.config.base import UnoSettings as Config
from uno.logging.protocols import LoggerProtocol

T_ID = TypeVar("T_ID")


class AggregateRoot(Entity):
    """
    Uno idiom: Protocol-based aggregate root template for DDD/event sourcing.

    Required dependencies (injected via constructor):
      - logger: LoggerProtocol (Uno DI)
      - config: Config (Uno DI)

    - DO NOT inherit from this class; instead, implement all required attributes/methods from AggregateRootProtocol directly.
    - Inherit from Pydantic's BaseModel if validation/serialization is needed.
    - This class serves as a template/example only.
    - All type checking should use AggregateRootProtocol, not this class.
    """

    id: object
    logger: LoggerProtocol
    config: Config

    def __init__(self, id: object, logger: LoggerProtocol, config: Config) -> None:
        if not logger or not isinstance(logger, LoggerProtocol):
            raise ValueError("logger (LoggerProtocol) is required via DI")
        if not config or not isinstance(config, Config):
            raise ValueError("config (Config) is required via DI")
        self.id = id
        self.logger = logger
        self.config = config

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, AggregateRoot) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # Example attributes required by AggregateRootProtocol
    version: int

    # Required by AggregateRootProtocol
    version: int = 0
    _uncommitted_events: list[DomainEventProtocol] = []
    _is_deleted: bool = False
    _pending_events: list[DomainEventProtocol] = []

    async def apply(self, event: DomainEventProtocol) -> None:
        """Apply a domain event to this aggregate.

        Args:
            event: The domain event to apply

        Raises:
            ValueError: If the event is not a valid domain event
        """
        if not isinstance(event, DomainEventProtocol):
            raise ValueError(
                f"Expected DomainEventProtocol, got {type(event).__name__}"
            )

        await self.apply_event(event)
        self.version += 1
        self._pending_events.append(event)

    async def apply_event(self, event: object) -> None:
        """Apply an event to this aggregate.

        Args:
            event: The event to apply
        """
        if isinstance(event, DeletedEvent):
            await self.apply_deleted(event)
        elif isinstance(event, RestoredEvent):
            await self.apply_restored(event)
        else:
            # Use reflection to find and call the appropriate apply_* method
            event_type = type(event).__name__
            method_name = f"apply_{event_type}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if callable(method):
                    (
                        await method(event)
                        if hasattr(method, "__await__")
                        else method(event)
                    )

    async def get_uncommitted_events(self) -> list[DomainEventProtocol]:
        """Get all uncommitted events.

        Returns:
            List of uncommitted domain events

        Note:
            This returns a copy of the pending events list to prevent modification
        """
        return self._pending_events.copy()

    async def clear_uncommitted_events(self) -> None:
        """Clear all uncommitted events.

        Note:
            This moves all pending events to the committed events list
        """
        self._uncommitted_events.extend(self._pending_events)
        self._pending_events.clear()

    # Add any additional Uno idiom methods as needed for your aggregates

    async def apply_deleted(self, event: DeletedEvent) -> None:
        """Handle deleted event.

        Args:
            event: The deleted event
        """
        self._is_deleted = True

    async def apply_restored(self, event: RestoredEvent) -> None:
        """Handle restored event.

        Args:
            event: The restored event
        """
        self._is_deleted = False

    @classmethod
    async def from_events(cls, events: list[DomainEventProtocol]) -> "AggregateRoot":
        """
        Rehydrates an aggregate from a list of events.

        Args:
            events: List of domain events to apply

        Returns:
            The rehydrated aggregate instance.

        Raises:
            ValueError: If no events are provided
            Exception: If rehydration fails
        """
        if not events:
            raise ValueError(f"No events to rehydrate aggregate for {cls.__name__}.")

        # Get required dependencies from DI container
        di = Container()
        logger = await di.resolve(LoggerProtocol)
        config = await di.resolve(Config)

        # Get aggregate ID from first event
        aggregate_id = getattr(events[0], "aggregate_id", None)
        if not aggregate_id:
            raise ValueError("First event is missing aggregate_id")

        # Create instance with required dependencies
        instance = cls(id=aggregate_id, logger=logger, config=config)

        try:
            # Apply all events
            for event in events:
                await instance.apply(event)

            return instance

        except Exception as exc:
            error_msg = f"Error rehydrating aggregate {cls.__name__} from events"
            await logger.error(error_msg, error=str(exc), exc_info=exc)
            raise Exception(f"{error_msg}: {exc}") from exc

    async def assert_not_deleted(self) -> None:
        """
        Ensures the aggregate is not deleted.

        Raises:
            AggregateNotDeletedError: If the aggregate is deleted.
        """
        if self._is_deleted:
            error_msg = f"Cannot perform operation on deleted {self.__class__.__name__} {self.id}"
            await self.logger.warning(
                "Operation attempted on deleted aggregate",
                aggregate_id=self.id,
                aggregate_type=self.__class__.__name__,
            )
            raise AggregateNotDeletedError(error_msg)

    async def publish_events(self, publisher: EventPublisherProtocol) -> None:
        """
        Publishes all uncommitted events using the provided publisher.

        Args:
            publisher: The event publisher to use for publishing events.

        Raises:
            Exception: If publishing fails for any event.
        """
        try:
            events = await self.get_uncommitted_events()
            if not events:
                return

            for event in events:
                await publisher.publish(event)

            await self.clear_uncommitted_events()

        except Exception as exc:
            await self.logger.error(
                "Failed to publish events",
                error=str(exc),
                exc_info=exc,
                aggregate_id=self.id,
                event_count=len(events) if "events" in locals() else 0,
            )
            raise Exception(f"Failed to publish events: {exc}") from exc

    model_config = ConfigDict(frozen=False, extra="forbid")
