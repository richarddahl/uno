"""
Service disposal implementation for uno DI system.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from uno.di.protocols import ContainerProtocol, ScopeProtocol

T = TypeVar("T")


class DisposalError(Exception):
    """Base class for disposal-related errors."""

    pass


class _DisposalManager:
    """Manages service disposal for the container."""

    def __init__(self, container: ContainerProtocol) -> None:
        self.container = container
        self._pending_tasks: set[asyncio.Task[None]] = set()

    async def dispose_service(self, service: Any) -> None:
        """Safely dispose a service if it supports disposal."""
        if hasattr(service, "dispose"):
            dispose = service.dispose
            if asyncio.iscoroutinefunction(dispose):
                await dispose()
            else:
                dispose()

    async def wait_for_pending_tasks(self) -> None:
        """Wait for all pending disposal tasks to complete."""
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks)
            self._pending_tasks.clear()

    async def dispose_container(self) -> None:
        """Dispose the container and all its services."""
        try:
            await self.wait_for_pending_tasks()

            # Get all scopes from the container using protocol method
            scopes = await self.container.get_scopes()
            for scope in reversed(scopes):
                await scope.dispose()

            # Get the singleton scope using protocol method
            singleton_scope = await self.container.get_singleton_scope()
            await singleton_scope.dispose()
        except Exception as e:
            raise DisposalError(f"Failed to dispose container: {e}") from e

    def add_pending_task(self, task: asyncio.Task[None]) -> None:
        """Add a pending disposal task."""
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
