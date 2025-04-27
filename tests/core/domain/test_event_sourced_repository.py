import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from uno.core.domain.event_sourced_repository import EventSourcedRepository
from uno.core.errors.result import Success, Failure
from uno.core.events.deleted_event import DeletedEvent
from uno.core.domain.aggregate import AggregateRoot

class FakeAggregate(AggregateRoot):
    id: str = "fake-id"
    _events: list = []

    @classmethod
    def from_events(cls, events):
        # Accept both MagicMock events and string 'corrupt' for robustness
        if any(getattr(e, 'event_type', None) == "corrupt" or e == "corrupt" for e in events):
            raise ValueError("Corrupt event stream")
        agg = cls()
        agg._events = list(events)
        return agg
    def clear_events(self):
        evts = getattr(self, "_events", [])
        self._events = []
        return evts

@pytest.fixture
def fake_event_store():
    store = AsyncMock()
    store.get_events_by_aggregate_id = AsyncMock()
    store.get_events_by_type = AsyncMock()
    store.save_event = AsyncMock()
    return store

@pytest.fixture
def fake_event_publisher():
    pub = AsyncMock()
    pub.publish = AsyncMock()
    return pub

@pytest.fixture
def fake_logger():
    logger = MagicMock()
    logger.structured_log = MagicMock()
    return logger

@pytest.fixture
def repo(fake_event_store, fake_event_publisher, fake_logger):
    return EventSourcedRepository(FakeAggregate, fake_event_store, fake_event_publisher, fake_logger)

@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing_aggregate(repo, fake_event_store):
    fake_event_store.get_events_by_aggregate_id.return_value = Success([])
    result = await repo.get_by_id("missing-id")
    assert result.is_success and result.value is None

@pytest.mark.asyncio
async def test_get_by_id_returns_failure_on_event_store_error(repo, fake_event_store, fake_logger):
    fake_event_store.get_events_by_aggregate_id.return_value = Failure(Exception("store error"))
    result = await repo.get_by_id("some-id")
    assert not result.is_success and isinstance(result.error, Exception)
    fake_logger.structured_log.assert_called_with("ERROR", ANY, aggregate_id="some-id", error=ANY)

@pytest.mark.asyncio
async def test_get_by_id_returns_failure_on_corrupt_events(repo, fake_event_store, fake_logger):
    # Use a MagicMock event with event_type='corrupt' to trigger ValueError
    corrupt_event = MagicMock()
    corrupt_event.event_type = "corrupt"
    fake_event_store.get_events_by_aggregate_id.return_value = Success([corrupt_event])
    result = await repo.get_by_id("bad-id")
    assert not result.is_success
    fake_logger.structured_log.assert_any_call("ERROR", ANY, aggregate_id="bad-id", exc_info=ANY)

@pytest.mark.asyncio
async def test_list_success_and_failure(repo, fake_event_store, fake_logger):
    # Provide mocks with required attributes
    e1 = MagicMock()
    e1.aggregate_id = "a1"
    e1.event_type = "E"
    e2 = MagicMock()
    e2.aggregate_id = "a2"
    e2.event_type = "E"
    fake_event_store.get_events_by_type.return_value = Success([e1, e2])
    result = await repo.list()
    assert result.is_success and isinstance(result.value, list)
    fake_event_store.get_events_by_type.return_value = Failure(Exception("fail"))
    result2 = await repo.list()
    assert not result2.is_success
    # Check a structured_log call with 'ERROR' and error=... exists
    assert any(
        (len(call.args) > 0 and call.args[0] == "ERROR") and "error" in call.kwargs
        for call in fake_logger.structured_log.mock_calls
    ), "No ERROR structured_log call with error=... found"

@pytest.mark.asyncio
async def test_add_success_and_failures(repo, fake_event_store, fake_event_publisher, fake_logger):
    agg = FakeAggregate()
    event = MagicMock()
    event.event_type = "E"
    event.event_id = "e1"
    event.aggregate_id = "a1"
    agg._events = [event]
    fake_event_store.save_event.return_value = Success(None)
    fake_event_publisher.publish.return_value = Success(None)
    result = await repo.add(agg)
    assert result.is_success
    # Simulate event store failure
    fake_event_store.save_event.return_value = Failure(Exception("save fail"))
    agg._events = [event]
    result2 = await repo.add(agg)
    assert not result2.is_success
    # Simulate publisher failure
    fake_event_store.save_event.return_value = Success(None)
    fake_event_publisher.publish.return_value = Failure(Exception("pub fail"))
    agg._events = [event]
    result3 = await repo.add(agg)
    assert not result3.is_success
    # Check a structured_log call with 'ERROR' and error=... exists
    assert any(
        (len(call.args) > 0 and call.args[0] == "ERROR") and "error" in call.kwargs
        for call in fake_logger.structured_log.mock_calls
    ), "No ERROR structured_log call with error=... found"

@pytest.mark.asyncio
async def test_remove_success_and_failures(repo, fake_event_store, fake_event_publisher, fake_logger):
    # Aggregate exists
    event = MagicMock()
    event.aggregate_id = "a1"
    fake_event_store.get_events_by_aggregate_id.return_value = Success([event])
    fake_event_store.save_event.return_value = Success(None)
    fake_event_publisher.publish.return_value = Success(None)
    result = await repo.remove("a1")
    assert result.is_success
    # Aggregate does not exist
    fake_event_store.get_events_by_aggregate_id.return_value = Success([])
    result2 = await repo.remove("a2")
    assert result2.is_success and result2.value is None
    # Event store failure
    fake_event_store.get_events_by_aggregate_id.return_value = Failure(Exception("fail"))
    result3 = await repo.remove("a3")
    assert not result3.is_success
    # Save deleted event fails
    fake_event_store.get_events_by_aggregate_id.return_value = Success([event])
    fake_event_store.save_event.return_value = Failure(Exception("save fail"))
    result4 = await repo.remove("a4")
    assert not result4.is_success
    # Publish deleted event fails
    fake_event_store.save_event.return_value = Success(None)
    fake_event_publisher.publish.return_value = Failure(Exception("pub fail"))
    result5 = await repo.remove("a5")
    assert not result5.is_success
    # Check a structured_log call with 'ERROR' and error=... exists
    assert any(
        (len(call.args) > 0 and call.args[0] == "ERROR") and "error" in call.kwargs
        for call in fake_logger.structured_log.mock_calls
    ), "No ERROR structured_log call with error=... found"
