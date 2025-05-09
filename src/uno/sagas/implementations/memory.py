# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory implementations for the sagas package.

This module provides memory-based implementations of saga stores for testing
and simple use cases.
"""

from typing import Dict
from uno.sagas.protocols import SagaState, SagaStore


class InMemorySagaStore(SagaStore):
    """
    In-memory implementation of a saga store.

    This is useful for testing and simple applications where persistence is not required.
    """

    def __init__(self):
        self._store: Dict[str, SagaState] = {}

    async def save_state(self, saga_id: str, state: SagaState) -> None:
        """Save saga state."""
        self._store[saga_id] = state

    async def load_state(self, saga_id: str) -> SagaState | None:
        """Load saga state."""
        return self._store.get(saga_id)

    async def delete_state(self, saga_id: str) -> None:
        """Delete saga state."""
        self._store.pop(saga_id, None)
