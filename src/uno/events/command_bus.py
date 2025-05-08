"""
Simple in-memory command bus for Uno, suitable for testing and integration with sagas/process managers.
"""

from typing import Callable, Any, Awaitable, List


class CommandBus:
    def __init__(self) -> None:
        self._handlers: list[Callable[[Any], Awaitable[None]]] = []

    def register_handler(self, handler: Callable[[Any], Awaitable[None]]) -> None:
        self._handlers.append(handler)

    async def dispatch(self, command: Any) -> None:
        for handler in self._handlers:
            await handler(command)
