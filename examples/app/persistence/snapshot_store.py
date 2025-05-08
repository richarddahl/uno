"""
In-memory SnapshotStore implementation for Uno example app.
Integrates with uno.events.snapshots.SnapshotStore for demo/testing purposes.
"""

from uno.events.snapshots import SnapshotStore, Success, Failure
from uno.errors.result import Result
from uno.infrastructure.logging import LoggerService
from typing import Any, TypeVar

T = TypeVar("T")


class InMemorySnapshotStore(SnapshotStore):
    def __init__(self, logger: LoggerService) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}
        self.logger = logger

    async def save_snapshot(self, aggregate: Any) -> Result[None, Exception]:
        try:
            aggregate_id = getattr(aggregate, "id", None)
            if not aggregate_id:
                return Failure(ValueError("Aggregate must have an 'id' attribute."))
            data = aggregate.model_dump(
                exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True
            )
            self._snapshots[aggregate_id] = {
                "type": type(aggregate).__name__,
                "data": data,
            }
            self.logger.structured_log("INFO", f"Snapshot saved for {aggregate_id}")
            return Success(None)
        except Exception as e:
            self.logger.structured_log("ERROR", f"Failed to save snapshot: {e}")
            return Failure(e)

    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> Result[T | None, Exception]:
        try:
            snap = self._snapshots.get(aggregate_id)
            if not snap or snap["type"] != aggregate_type.__name__:
                return Success(None)
            if not hasattr(aggregate_type, "from_dict"):
                return Failure(
                    ValueError(
                        f"Aggregate type {aggregate_type.__name__} does not implement from_dict method"
                    )
                )
            aggregate = aggregate_type.from_dict(snap["data"])
            self.logger.structured_log("INFO", f"Snapshot loaded for {aggregate_id}")
            return Success(aggregate)
        except Exception as e:
            self.logger.structured_log("ERROR", f"Failed to load snapshot: {e}")
            return Failure(e)

    async def delete_snapshot(self, aggregate_id: str) -> Result[None, Exception]:
        try:
            self._snapshots.pop(aggregate_id, None)
            self.logger.structured_log("INFO", f"Snapshot deleted for {aggregate_id}")
            return Success(None)
        except Exception as e:
            self.logger.structured_log("ERROR", f"Failed to delete snapshot: {e}")
            return Failure(e)
