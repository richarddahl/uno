"""
AggregateRoot base class for Uno's DDD/event sourcing model.
"""

from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING

from pydantic import ConfigDict, PrivateAttr

if TYPE_CHECKING:
    from uno.domain.protocols import (
        AggregateRootProtocol,
        DomainEventProtocol,
        EventPublisherProtocol,
    )
    from uno.logging.protocols import LoggerProtocol

from uno.domain.entity import Entity
from uno.domain.errors import AggregateNotDeletedError, DomainValidationError
from uno.events.deleted_event import DeletedEvent
from uno.events.restored_event import RestoredEvent
from uno.core.di import DIContainer
from uno.core.config import Config
from uno.core.logging import LoggerProtocol

T_ID = TypeVar("T_ID")


class AggregateRoot:
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

    # Example methods required by AggregateRootProtocol
    def apply(self, event: "DomainEventProtocol") -> None:
        ...

    def apply_event(self, event: object) -> None:
        ...

    def get_uncommitted_events(self) -> list["DomainEventProtocol"]:
        ...

    def clear_uncommitted_events(self) -> None:
        ...

    # Add any additional Uno idiom methods as needed for your aggregates

            getattr(self, handler_name)(event)
        # Defensive: fallback if event_type string doesn't match
        elif isinstance(event, DeletedEvent):
            self.apply_deleted(event)
        elif isinstance(event, RestoredEvent):
            self.apply_restored(event)

    def apply_deleted(self, event: DeletedEvent) -> None:
        self._is_deleted = True

    def apply_restored(self, event: RestoredEvent) -> None:
        self._is_deleted = False

    @classmethod
    def from_events(cls, events: list[DomainEventProtocol]) -> AggregateRootProtocol:
        """
        Rehydrates an aggregate from a list of events.
        Returns:
            The rehydrated aggregate instance.
        Raises:
            Exception: If no events are provided or rehydration fails.
        """
        if not events:
            raise Exception(f"No events to rehydrate aggregate for {cls.__name__}.")
        try:
            instance = cls(id=getattr(events[0], "aggregate_id", None))
            for event in events:
                instance.apply_event(event)
                instance.version += 1
            return instance
        except Exception as exc:
            raise Exception(
                f"Error rehydrating aggregate {cls.__name__} from events: {exc}"
            ) from exc

    def assert_not_deleted(self) -> None:
        """
        Ensures the aggregate is not deleted.
        Raises:
            AggregateNotDeletedError: If the aggregate is deleted.
        """
        if self.is_deleted:
            self._logger.error(f"Aggregate {self.id} is deleted and cannot be mutated.")
            raise AggregateNotDeletedError(
                f"Aggregate {self.id} is deleted and cannot be mutated."
            )

    async def publish_events(self, publisher: EventPublisherProtocol) -> None:
        """
        Publishes all uncommitted events using the provided publisher.

        Args:
            publisher: The event publisher to use for publishing events.

        Raises:
            Exception: If publishing fails for any event.
        """
        for event in self.get_uncommitted_events():
            try:
                await publisher.publish(event)
                self._logger.info(
                    f"Published event {event.event_type} for aggregate {self.id}."
                )
            except Exception as exc:
                self._logger.error(f"Failed to publish event {event.event_type}: {exc}")
                raise

        # Clear events after successful publishing
        self.clear_events()

    model_config = ConfigDict(frozen=False, extra="forbid")
