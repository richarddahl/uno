"""
Saga state and persistence protocols for Uno event sourcing.
"""

from abc import ABC, abstractmethod
from typing import Any


class SagaState:
    """
    Base class for saga/process manager state.
    """

    def __init__(self, saga_id: str, status: str, data: dict[str, Any]):
        self.saga_id = saga_id
        self.status = status  # e.g., 'pending', 'waiting', 'completed', 'failed'
        self.data = data


class SagaStore(ABC):
    """
    Protocol for saga state persistence.
    """

    @abstractmethod
    async def save_state(self, saga_id: str, state: SagaState) -> None:
        pass

    @abstractmethod
    async def load_state(self, saga_id: str) -> SagaState | None:
        pass

    @abstractmethod
    async def delete_state(self, saga_id: str) -> None:
        pass


class InMemorySagaStore(SagaStore):
    def __init__(self):
        self._store: dict[str, SagaState] = {}

    async def save_state(self, saga_id: str, state: SagaState) -> None:
        self._store[saga_id] = state

    async def load_state(self, saga_id: str) -> SagaState | None:
        return self._store.get(saga_id)

    async def delete_state(self, saga_id: str) -> None:
        self._store.pop(saga_id, None)
