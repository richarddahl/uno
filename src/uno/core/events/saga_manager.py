"""
Saga orchestration engine for Uno event sourcing.
"""
from typing import Any, Type
from uno.core.events.sagas import Saga
from uno.core.events.saga_store import SagaStore, SagaState

class SagaManager:
    """
    Orchestrates saga lifecycle: event routing, state persistence, and recovery.
    """
    def __init__(self, saga_store: SagaStore) -> None:
        self._saga_store = saga_store
        self._saga_types: dict[str, Type[Saga]] = {}
        self._active_sagas: dict[str, Saga] = {}

    def list_active_sagas(self) -> list[dict[str, str]]:
        """
        Returns a list of all currently active sagas with their IDs and statuses.
        This is an in-memory stub for admin/monitoring, to be extended for persistence.
        """
        return [
            {"saga_id": saga.saga_id, "type": saga.__class__.__name__, "status": saga.status}
            for saga in self._active_sagas.values()
        ]

    def register_saga(self, saga_type: Type[Saga]) -> None:
        self._saga_types[saga_type.__name__] = saga_type

    async def handle_event(self, saga_id: str, saga_type: str, event: Any) -> None:
        # Load or create saga state
        state = await self._saga_store.load_state(saga_id)
        saga_cls = self._saga_types[saga_type]
        saga = saga_cls()  # Assumes no-arg init; pass state/data if needed
        if state:
            # Optionally hydrate saga with state
            if hasattr(saga, 'load_state'):
                saga.load_state(state)
        await saga.handle_event(event)
        # Persist updated state if saga provides it
        if hasattr(saga, 'get_state'):
            new_state = saga.get_state()
            await self.saga_store.save_state(saga_id, new_state)
        # Optionally clean up if saga is complete
        if await saga.is_completed():
            await self.saga_store.delete_state(saga_id)
