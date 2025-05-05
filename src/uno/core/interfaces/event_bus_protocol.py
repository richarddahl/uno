"""
EventBusProtocol: Abstract base class for event bus implementations.
Extend this protocol for event bus DI and event publishing.
"""

from typing import Protocol, Any


class EventBusProtocol(Protocol):
    """Protocol for event bus implementations."""

    def publish(self, event: Any) -> None: ...
    def subscribe(self, handler: Any) -> None: ...
