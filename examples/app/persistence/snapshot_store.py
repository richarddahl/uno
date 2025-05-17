"""
In-memory SnapshotStore implementation for Uno example app.
Integrates with uno.event_bus.snapshots.SnapshotStore for demo/testing purposes.
"""

from uno.snapshots import SnapshotStore
from uno.logging import LoggerProtocol
from uno.logging.level import LogLevel
from typing import Any, TypeVar

T = TypeVar("T")


class InMemorySnapshotStore(SnapshotStore):
    def __init__(self, logger: LoggerProtocol) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}
        self.logger = logger

    async def save_snapshot(self, aggregate: Any) -> None:
        aggregate_id = getattr(aggregate, "id", None)
        if not aggregate_id:
            raise ValueError("Aggregate must have an 'id' attribute.")
        data = aggregate.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True
        )
        self._snapshots[aggregate_id] = {
            "type": type(aggregate).__name__,
            "data": data,
        }
        await self.logger.structured_log(
            LogLevel.INFO, f"Snapshot saved for {aggregate_id}"
        )

    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> T | None:
        snap = self._snapshots.get(aggregate_id)
        if not snap or snap["type"] != aggregate_type.__name__:
            return None
        aggregate = aggregate_type(**snap["data"])
        await self.logger.structured_log(
            LogLevel.INFO, f"Snapshot loaded for {aggregate_id}"
        )
        return aggregate

    async def delete_snapshot(self, aggregate_id: str) -> None:
        self._snapshots.pop(aggregate_id, None)
        await self.logger.structured_log(
            LogLevel.INFO, f"Snapshot deleted for {aggregate_id}"
        )
