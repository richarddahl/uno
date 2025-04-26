"""
Saga and process manager base classes for Uno event sourcing.
"""
from abc import ABC, abstractmethod
from typing import Any

class Saga(ABC):
    """
    Base class for sagas (process managers) coordinating long-running business processes.
    """
    @abstractmethod
    async def handle_event(self, event: Any) -> None:
        """Handle an event as part of the saga orchestration."""
        pass

    @abstractmethod
    async def is_completed(self) -> bool:
        """Return True if the saga has completed."""
        pass
