"""
EventStoreProtocol: Protocol for event store implementations.
"""

from typing import Protocol, Any


class EventStoreProtocol(Protocol):
    async def save_event(self, event: Any) -> None: ...
    async def get_events(self, *args, **kwargs) -> list[Any]: ...
    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[Any]: ...
