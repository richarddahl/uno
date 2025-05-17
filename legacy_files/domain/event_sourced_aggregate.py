from uno.snapshots.protocols import SnapshotProtocol


class EventSourcedAggregate:
    async def apply_snapshot(self, snapshot: SnapshotProtocol) -> None:
        """Apply a snapshot to restore the aggregate state."""
        # Implementation for applying the snapshot
        self.state = snapshot.state
        self.version = snapshot.aggregate_version
        self.last_updated = snapshot.created_at
