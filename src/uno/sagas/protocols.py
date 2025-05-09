# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the sagas package.

This module contains the core protocols that define the interfaces for saga/process manager
components.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

E = TypeVar("E")  # Event type
C = TypeVar("C")  # Command type


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


class Saga(ABC, Generic[E, C]):
    """
    Base class for sagas/process managers.
    """

    @abstractmethod
    async def start(self, event: E) -> list[C]:
        """
        Start a new saga instance based on the triggering event.
        Returns commands to be executed.
        """
        pass

    @abstractmethod
    async def handle(self, event: E) -> list[C]:
        """
        Handle an event in an ongoing saga.
        Returns commands to be executed.
        """
        pass

    @abstractmethod
    async def complete(self) -> None:
        """
        Mark the saga as completed.
        """
        pass

    @abstractmethod
    async def compensate(self, error: Exception) -> list[C]:
        """
        Compensate for a failure in the saga.
        Returns compensating commands to be executed.
        """
        pass
