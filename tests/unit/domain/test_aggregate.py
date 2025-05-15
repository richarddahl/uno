"""Tests for AggregateRoot class."""

from __future__ import annotations

import sys
from abc import abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from uno.domain.aggregate import AggregateRoot
from uno.config.base import UnoSettings as Config
from uno.injection import Container
from uno.events.base import DomainEvent
from uno.logging.protocols import LoggerProtocol

# Type variables for test events
TestEventT = TypeVar("TestEventT", bound="TestEvent")
DeletedEventT = TypeVar("DeletedEventT", bound="DeletedEvent")
RestoredEventT = TypeVar("RestoredEventT", bound="RestoredEvent")

if TYPE_CHECKING:
    from uno.domain.protocols import DomainEventProtocol  # type: ignore[import-not-found]
    from uno.events.publisher import EventPublisherProtocol  # type: ignore[import-not-found]
    from uno.injection import Container
    from uno.config import Config

    # Create a type that's compatible with both TestEvent and DomainEventProtocol
    class TestEventProtocol(DomainEventProtocol, Protocol):  # type: ignore[misc, valid-type]
        event_id: str
        aggregate_id: str
        version: int

        def model_dump(self) -> dict[str, Any]: ...


# Protocol for test aggregates with additional test-specific methods
@runtime_checkable
class TestAggregateProtocol(Protocol):
    """Protocol for test aggregates with additional test-specific methods."""

    applied_events: list[DomainEvent]
    _test_state: dict[str, dict[str, Any]]
    _is_deleted: bool
    _uncommitted_events: list[DomainEvent]

    async def apply_TestEvent(self, event: "TestEventProtocol") -> None: ...

    # Inherited from AggregateRoot
    async def apply(self, event: DomainEvent) -> None: ...
    async def apply_event(self, event: DomainEvent) -> None: ...
    async def publish_events(self, publisher: Any) -> None: ...
    async def get_uncommitted_events(self) -> list[DomainEvent]: ...

    @classmethod
    @abstractmethod
    async def from_events(
        cls, events: list[DomainEvent]
    ) -> "TestAggregateProtocol": ...


# Type aliases for test events
TestEventT = TypeVar("TestEventT", bound="TestEvent")
DeletedEventT = TypeVar("DeletedEventT", bound="DeletedEvent")
RestoredEventT = TypeVar("RestoredEventT", bound="RestoredEvent")


# Protocol for test aggregates with additional test-specific methods
@runtime_checkable
class TestAggregateProtocol(Protocol):
    """Protocol for test aggregates with additional test-specific methods."""

    applied_events: list[DomainEvent]
    _test_state: dict[str, dict[str, Any]]
    _is_deleted: bool
    _uncommitted_events: list[DomainEvent]

    async def apply_TestEvent(self, event: "TestEventProtocol") -> None: ...

    # Inherited from AggregateRoot
    async def apply(self, event: DomainEvent) -> None: ...
    async def apply_event(self, event: DomainEvent) -> None: ...
    async def publish_events(self, publisher: Any) -> None: ...
    async def get_uncommitted_events(self) -> list[DomainEvent]: ...

    @classmethod
    @abstractmethod
    async def from_events(
        cls, events: list[DomainEventProtocol]
    ) -> "TestAggregateProtocol": ...


# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestEvent(DomainEvent):
    """Test event for aggregate testing."""

    event_type: ClassVar[str] = "TestEvent"

    def __init__(
        self,
        event_id: str | None = None,
        aggregate_id: str | None = None,
        version: int = 1,
        timestamp: datetime | None = None,
    ) -> None:
        self._event_id = (
            event_id or f"test-event-{datetime.now(timezone.utc).timestamp()}"
        )
        self._aggregate_id = aggregate_id or "test-aggregate-id"
        self._version = version
        self._timestamp = timestamp or datetime.now(timezone.utc)

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def aggregate_id(self) -> str:
        return self._aggregate_id

    @property
    def version(self) -> int:
        return self._version

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    def model_dump(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TestEvent):
            return False
        return (
            self.event_id == other.event_id
            and self.aggregate_id == other.aggregate_id
            and self.version == other.version
            and self.timestamp == other.timestamp
        )


class DeletedEvent(DomainEvent):
    """Test event for delete operation."""

    event_type: ClassVar[str] = "DeletedEvent"

    def __init__(
        self,
        event_id: str,
        aggregate_id: str,
        timestamp: datetime | None = None,
        **kwargs,
    ):
        super().__init__(
            event_id=event_id,
            aggregate_id=aggregate_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            **kwargs,
        )


class RestoredEvent(DomainEvent):
    """Test event for restore operation."""

    event_type: ClassVar[str] = "RestoredEvent"

    def __init__(
        self,
        event_id: str,
        aggregate_id: str,
        timestamp: datetime | None = None,
        **kwargs,
    ):
        super().__init__(
            event_id=event_id,
            aggregate_id=aggregate_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            **kwargs,
        )


class TestAggregate(AggregateRoot):
    """Test implementation of AggregateRoot for testing."""

    def __init__(self, id: str, logger: LoggerProtocol, config: Config) -> None:
        """Initialize a new TestAggregate instance."""
        super().__init__(id, logger, config)
        self.applied_events: list[DomainEvent] = []
        self._test_state: dict[str, dict[str, Any]] = {}
        self._is_deleted: bool = False
        self._uncommitted_events: list[DomainEvent] = []
        self._version: int = 0

    async def apply_TestEvent(self, event: DomainEvent) -> None:
        """Handle TestEvent."""
        if not isinstance(event, TestEvent):
            raise TypeError(f"Expected TestEvent, got {type(event).__name__}")

        self.applied_events.append(event)
        self._test_state[event.event_id] = event.model_dump()
        self._version += 1

    @property
    def version(self) -> int:
        """Get the current version of the aggregate."""
        return self._version

    @classmethod
    async def from_events(cls, events: list[DomainEvent]) -> "TestAggregate":
        """Create aggregate from events."""
        if not events:
            raise ValueError("At least one event is required")

        # Create a mock logger and config for testing
        mock_logger = MagicMock(spec=LoggerProtocol)
        mock_config = MagicMock(spec=Config)

        # Create aggregate with the first event's aggregate_id
        aggregate = cls(
            id=events[0].aggregate_id, logger=mock_logger, config=mock_config
        )

        # Apply all events to the aggregate
        for event in events:
            if not isinstance(event, TestEvent):
                raise TypeError(f"Expected TestEvent, got {type(event).__name__}")
            await aggregate.apply(event)

        return aggregate


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock(spec=LoggerProtocol)
    logger.debug = AsyncMock()
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.critical = AsyncMock()
    logger.__aenter__.return_value = logger
    return logger


@pytest.fixture
def mock_config() -> Mock:
    """Create a mock config."""
    return MagicMock(spec=Config)


@pytest.fixture
async def aggregate(mock_logger: Mock, mock_config: Mock) -> TestAggregate:
    """Create a test aggregate instance."""
    # Configure the mock logger to return itself for context manager
    mock_logger.__aenter__.return_value = mock_logger
    return TestAggregate(id="test-id", logger=mock_logger, config=mock_config)


@pytest.fixture
def test_event() -> TestEvent:
    """Create a test event."""
    return TestEvent()


@pytest.fixture
def test_aggregate() -> TestAggregate:
    """Create a test aggregate."""
    mock_logger = MagicMock(spec=LoggerProtocol)
    mock_config = MagicMock(spec=Config)
    return TestAggregate("test-id", mock_logger, mock_config)


@pytest.mark.asyncio
async def test_apply_event(
    test_aggregate: TestAggregate, test_event: TestEvent
) -> None:
    """Test applying an event to the aggregate."""
    # Apply the event
    await test_aggregate.apply(test_event)  # type: ignore[arg-type]

    # Check that the event was applied
    assert len(test_aggregate.applied_events) == 1
    assert test_aggregate.applied_events[0] == test_event
    assert test_aggregate.version == 1
    assert test_event.event_id in test_aggregate._test_state
    assert test_aggregate._test_state[test_event.event_id] == test_event.model_dump()


@pytest.mark.asyncio
async def test_from_events() -> None:
    """Test creating an aggregate from events."""
    # Create test events
    events = [
        TestEvent(aggregate_id="test-id", version=1),
        TestEvent(aggregate_id="test-id", version=2),
        TestEvent(aggregate_id="test-id", version=3),
    ]

    # Rehydrate aggregate with proper type casting
    aggregate = await TestAggregate.from_events(events)  # type: ignore[arg-type]

    # Verify the aggregate was properly initialized
    assert aggregate.id == "test-id"
    assert len(aggregate.applied_events) == 3

    # Check version is set correctly
    assert aggregate.version == 3  # Should be set by applying 3 events


@pytest.mark.asyncio
async def test_assert_not_deleted(aggregate: TestAggregate) -> None:
    """Test assert_not_deleted method."""
    # Should not raise when not deleted
    await aggregate.assert_not_deleted()

    # Mark as deleted
    await aggregate.apply(DeletedEvent(event_id="delete-1", aggregate_id="test-id"))

    # Should raise when deleted
    with pytest.raises(Exception, match="Aggregate has been deleted"):
        await aggregate.assert_not_deleted()


@pytest.mark.asyncio
async def test_publish_events(aggregate: TestAggregate) -> None:
    """Test publishing events."""
    # Create a mock publisher
    mock_publisher = AsyncMock()

    # Apply an event
    event = TestEvent(event_id="event-1", aggregate_id="test-id")
    await aggregate.apply(event)

    # Publish events with proper type casting
    await aggregate.publish_events(cast(Any, mock_publisher))

    # Verify publisher was called with the correct event
    mock_publisher.publish.assert_awaited_once()

    # Get the published event from the mock
    published_event = mock_publisher.publish.call_args[0][0]
    assert isinstance(published_event, TestEvent)
    assert published_event.aggregate_id == "test-id"

    # Verify events were cleared from pending
    pending_events = await aggregate.get_uncommitted_events()
    assert len(pending_events) == 0

    # The event should still be in the uncommitted events list until explicitly cleared
    assert len(aggregate._uncommitted_events) == 1


@pytest.mark.asyncio
async def test_publish_events_empty(aggregate: TestAggregate) -> None:
    """Test publishing events when there are no events."""
    # Create a mock publisher
    mock_publisher = AsyncMock()

    # Publish events with proper type casting
    from uno.events.publisher import EventPublisherProtocol

    publisher = cast(EventPublisherProtocol, mock_publisher)
    await aggregate.publish_events(publisher)  # type: ignore[arg-type]

    # Verify publisher was not called
    mock_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_events_error(aggregate: TestAggregate) -> None:
    """Test error handling when publishing events fails."""
    # Create a test event
    event = TestEvent(event_id="event-1", aggregate_id="test-id")
    await aggregate.apply(event)

    # Create a mock publisher that raises an exception
    mock_publisher = AsyncMock()
    mock_publisher.publish.side_effect = Exception("Publish failed")

    # Publish events - should raise the exception
    with pytest.raises(Exception, match="Publish failed"):
        await aggregate.publish_events(mock_publisher)  # type: ignore[arg-type]

    # Verify events were not cleared from pending
    pending_events = await aggregate.get_uncommitted_events()
    assert len(pending_events) == 1

    # Verify events were not moved to committed
    assert hasattr(aggregate, "_uncommitted_events")
    assert len(aggregate._uncommitted_events) == 0  # type: ignore[attr-defined]
