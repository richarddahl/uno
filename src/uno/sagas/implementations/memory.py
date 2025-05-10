# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory implementations for the sagas package.

This module provides memory-based implementations of saga stores for testing
and simple use cases.
"""

from typing import TYPE_CHECKING

from uno.sagas.protocols import SagaState

if TYPE_CHECKING:
    from uno.sagas.protocols import SagaStoreProtocol  # Used only for type checking


class InMemorySagaStore:  # implements SagaStoreProtocol
    """
    In-memory implementation of a saga store.

    This is useful for testing and simple applications where persistence is not required.
    Implements SagaStoreProtocol via structural typing (not inheritance).
    """

    def __init__(self) -> None:
        self._store: dict[str, SagaState] = {}

    async def save_state(self, saga_id: str, state: SagaState) -> None:
        """Save saga state to the in-memory store."""
        self._store[saga_id] = state

    async def load_state(self, saga_id: str) -> SagaState | None:
        """Load saga state from the in-memory store."""
        return self._store.get(saga_id)

    async def delete_state(self, saga_id: str) -> None:
        """Delete saga state from the in-memory store."""
        self._store.pop(saga_id, None)
