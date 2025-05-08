"""
Saga and process manager base classes for Uno event sourcing.
"""

from abc import ABC, abstractmethod
from typing import Any

from uno.events.saga_store import SagaState


class Saga(ABC):
    """
    Base class for sagas (process managers) coordinating long-running business processes.
    Provides standardized state hydration and persistence via SagaState.
    Subclasses should store all custom state in self.data and may extend _serialize_extra/_hydrate_extra for advanced needs.
    """

    def __init__(self):
        self.saga_id: str | None = None
        self.status: str = "pending"
        self.data: dict[str, Any] = {}

    @abstractmethod
    async def handle_event(self, event: Any) -> None:
        """Handle an event as part of the saga orchestration."""
        pass

    @abstractmethod
    async def is_completed(self) -> bool:
        """Return True if the saga has completed."""
        pass

    def get_state(self) -> SagaState:
        """Final: returns SagaState for persistence. Subclasses should not override; use _serialize_extra for extra fields."""
        state = SagaState(
            saga_id=self.saga_id or "", status=self.status, data=self.data.copy()
        )
        self._serialize_extra(state)
        return state

    def load_state(self, state: SagaState) -> None:
        """Final: loads state from SagaState. Subclasses should not override; use _hydrate_extra for extra fields."""
        self.saga_id = state.saga_id
        self.status = state.status
        self.data = state.data.copy()
        self._hydrate_extra(state)

    def _serialize_extra(self, state: SagaState) -> None:
        """Hook: Subclasses can extend to serialize extra fields into state.data."""
        pass

    def _hydrate_extra(self, state: SagaState) -> None:
        """Hook: Subclasses can extend to hydrate extra fields from state.data."""
        pass
