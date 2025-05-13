# Fixed import sorting
from unittest.mock import AsyncMock

from uno.domain.aggregate import AggregateRoot
from uno.events.protocols import DomainEventProtocol


class MockEvent:
    event_type = "MockEvent"
    aggregate_id = "test-aggregate"
    version = 1


class MockPublisher:
    async def publish(self, event: DomainEventProtocol) -> None:
        pass


class TestEventSourcing:
    async def test_aggregate_event_publishing(self):
        # Arrange
        from unittest.mock import Mock

        aggregate = AggregateRoot(id="test-aggregate")
        aggregate._logger = Mock()  # Inject mock logger to avoid AttributeError
        mock_publisher = MockPublisher()
        mock_publisher.publish = AsyncMock()

        # Act
        event = MockEvent()
        aggregate.add_event(event)
        await aggregate.publish_events(mock_publisher)

        # Assert
        mock_publisher.publish.assert_called_once_with(event)
        assert len(aggregate.get_uncommitted_events()) == 0
