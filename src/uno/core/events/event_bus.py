"""
Simple in-memory event bus for Uno, suitable for testing and integration with sagas/process managers.
"""
from typing import Callable, Any, Awaitable, List

class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[Callable[[Any], Awaitable[None]]] = []

    def subscribe(self, handler: Callable[[Any], Awaitable[None]]) -> None:
        self._subscribers.append(handler)

    async def publish(self, event: Any) -> None:
        for handler in self._subscribers:
            await handler(event)
