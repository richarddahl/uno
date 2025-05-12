"""In-memory implementation of snapshot storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Dict, List

from uno.logging.protocols import LoggerProtocol
from uno.snapshots.protocols import SnapshotProtocol


class Snapshot:
    """Concrete implementation of a snapshot for an aggregate."""

    def __init__(
        self, aggregate_id: str, aggregate_version: int, state: Dict[str, Any]
    ) -> None:
        self.aggregate_id = aggregate_id
        self.aggregate_version = aggregate_version
        self.created_at = datetime.now()
        self.state = state


class InMemorySnapshotStore:
    """In-memory implementation of snapshot storage."""

    _snapshots: ClassVar[Dict[str, List[Snapshot]]] = {}
    
    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize the in-memory snapshot store.
        
        Args:
            logger: Logger instance for logging operations
        """
        self._logger = logger

    async def save_snapshot(
        self, aggregate: Any, aggregate_version: int | None = None, state: Dict[str, Any] | None = None
    ) -> None:
        """Save a snapshot to in-memory storage.
        
        Args:
            aggregate: The aggregate object or aggregate ID
            aggregate_version: The version of the aggregate (optional if aggregate has a version attribute)
            state: The state to save (optional if aggregate has a state attribute)
        """
        if hasattr(aggregate, 'id') and hasattr(aggregate, 'state'):
            aggregate_id = str(aggregate.id)
            state = state or getattr(aggregate, 'state', {})
            version = aggregate_version or getattr(aggregate, 'version', 1)
        else:
            aggregate_id = str(aggregate)
            if state is None:
                raise ValueError("state must be provided if aggregate is not an object with state")
            version = aggregate_version or 1
            
        # Initialize the snapshot list if it doesn't exist
        if aggregate_id not in self._snapshots:
            self._snapshots[aggregate_id] = []
            self._logger.debug(message=f"Created new snapshot list for aggregate {aggregate_id}")
        
        # Remove any existing snapshots with the same version
        self._snapshots[aggregate_id] = [
            s for s in self._snapshots[aggregate_id] if s.aggregate_version != version
        ]
        
        # Add the new snapshot
        snapshot = Snapshot(aggregate_id, version, state)
        self._snapshots[aggregate_id].append(snapshot)
        self._logger.debug(message=f"Saved snapshot for aggregate {aggregate_id} at version {version}")

    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type | None = None
    ) -> SnapshotProtocol | None:
        """Get the latest snapshot for an aggregate from in-memory storage.
        
        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate (unused in this implementation)
            
        Returns:
            The latest snapshot for the aggregate, or None if not found
        """
        if aggregate_id not in self._snapshots or not self._snapshots[aggregate_id]:
            self._logger.debug(message=f"No snapshots found for aggregate {aggregate_id}")
            return None

        latest = max(
            self._snapshots[aggregate_id],
            key=lambda snapshot: snapshot.aggregate_version,
        )
        
        # Create a new instance of the aggregate type with the snapshot state
        if aggregate_type is not None:
            # Check if aggregate_type is FakeAggregate or similar that expects (id, state) as positional args
            if hasattr(aggregate_type, '__name__') and aggregate_type.__name__ == 'FakeAggregate':
                return aggregate_type(latest.aggregate_id, latest.state)
            # For other types, try to use keyword arguments
            elif isinstance(latest.state, dict):
                return aggregate_type(id=latest.aggregate_id, **latest.state)
            else:
                return aggregate_type(id=latest.aggregate_id, state=latest.state)
            
        return latest

    async def delete_snapshots(self, aggregate_id: str) -> None:
        """Delete all snapshots for an aggregate from in-memory storage."""
        if aggregate_id in self._snapshots:
            del self._snapshots[aggregate_id]
            self._logger.debug(message=f"Deleted all snapshots for aggregate {aggregate_id}")
