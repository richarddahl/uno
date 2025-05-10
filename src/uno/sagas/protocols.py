# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the sagas package.

This module contains the core protocols that define the interfaces for saga/process manager
components.
"""

from abc import abstractmethod
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

E = TypeVar("E")
E_co = TypeVar("E_co", covariant=True)  # Event type
E_contra = TypeVar("E_contra", contravariant=True)  # Event type
C = TypeVar("C")
C_co = TypeVar("C_co", covariant=True)  # Command type
C_contra = TypeVar("C_contra", contravariant=True)  # Command type


class SagaState:
    """
    Base class for saga/process manager state.
    """

    def __init__(self, saga_id: str, status: str, data: dict[str, Any]):
        self.saga_id = saga_id
        self.status = status  # e.g., 'pending', 'waiting', 'completed', 'failed'
        self.data = data


@runtime_checkable
class SagaStoreProtocol(Protocol):
    """
    Protocol for saga state persistence.

    This protocol defines the interface for saga state storage and retrieval.
    Implementations must provide concrete methods for saving, loading, and deleting
    saga state.
    """

    async def save_state(self, saga_id: str, state: SagaState) -> None:
        """
        Save the current state of a saga.

        Args:
            saga_id: Unique identifier for the saga
            state: Current state of the saga
        """
        ...

    async def load_state(self, saga_id: str) -> SagaState | None:
        """
        Load the state of a saga.

        Args:
            saga_id: Unique identifier for the saga

        Returns:
            The saga's state if found, None otherwise
        """
        ...

    async def delete_state(self, saga_id: str) -> None:
        """
        Delete the state of a saga.

        Args:
            saga_id: Unique identifier for the saga
        """
        ...


@runtime_checkable
class SagaProtocol(Protocol, Generic[E_contra, C_co]):
    """
    Protocol for sagas/process managers.

    Defines the interface for saga components that handle events and maintain state.
    """

    saga_id: str
    saga_state: SagaState

    @abstractmethod
    async def handle_event(self, event: E_contra) -> None:
        """
        Handle an event in the saga.

        Args:
            event: The event to process
        """
        ...

    @abstractmethod
    def is_completed(self) -> bool:
        """
        Check if the saga is completed.

        Returns:
            True if the saga is completed, False otherwise
        """
        ...

    @abstractmethod
    async def compensate(self, error: Exception) -> list[C]:
        """
        Compensate for a failure in the saga.
        Returns compensating commands to be executed.
        """
        ...
