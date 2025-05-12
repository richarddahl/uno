from uno.snapshots.implementations.memory import (
    EventCountSnapshotStrategy,
    InMemorySnapshotStore,
    TimeBasedSnapshotStrategy,
)
from uno.snapshots.protocols import SnapshotStoreProtocol


class TestSnapshots:
    async def test_event_count_strategy(self):
        strategy = EventCountSnapshotStrategy(threshold=5)
        aggregate_id = "agg1"
        # Should not snapshot if below threshold
        assert not await strategy.should_snapshot(aggregate_id, 0)
        assert not await strategy.should_snapshot(aggregate_id, 4)
        # Should snapshot at threshold
        assert await strategy.should_snapshot(aggregate_id, 5)
        # Should snapshot above threshold
        assert await strategy.should_snapshot(aggregate_id, 10)

    async def test_time_based_strategy(self):
        import datetime as _datetime
        from unittest.mock import patch
        strategy = TimeBasedSnapshotStrategy(minutes_threshold=1)  # 60 seconds for test
        aggregate_id = "agg2"

        # Patch datetime to control time
        base = _datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=_datetime.timezone.utc)
        with patch("uno.snapshots.implementations.memory.strategies.datetime") as mock_dt:
            mock_dt.now.return_value = base
            mock_dt.timezone = _datetime.timezone
            # First call should snapshot
            assert await strategy.should_snapshot(aggregate_id, 1)

            # Less than threshold later: should not snapshot
            mock_dt.now.return_value = base + _datetime.timedelta(seconds=30)
            assert not await strategy.should_snapshot(aggregate_id, 2)

            # At threshold: should snapshot
            mock_dt.now.return_value = base + _datetime.timedelta(seconds=60)
            assert await strategy.should_snapshot(aggregate_id, 3)
