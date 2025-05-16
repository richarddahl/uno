# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Service disposal implementation for uno DI system.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, TypeVar

from uno.injection.errors import DisposalError

if TYPE_CHECKING:
    from uno.injection.protocols import ContainerProtocol, ScopeProtocol

T = TypeVar("T")


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

            # Get all scopes safely - if we can't get them from methods, access directly
            try:
                scopes = await self.container.get_scopes()
            except Exception:
                # Direct access if method call fails due to container disposal
                # This is safe because we know the container's implementation
                if hasattr(self.container, "_scopes"):
                    scopes = getattr(self.container, "_scopes", [])
                else:
                    scopes = []

            # Get singleton scope safely
            try:
                singleton_scope = await self.container.get_singleton_scope()
            except Exception:
                # Direct access if method call fails
                singleton_scope = getattr(self.container, "_singleton_scope", None)

            # Then dispose them in the correct order (newest to oldest, except singleton)
            for scope in reversed(list(scopes)):
                if scope != singleton_scope:  # Don't dispose singleton scope yet
                    try:
                        await scope.dispose()
                    except Exception as e:
                        # Log error but continue with other scopes
                        import logging

                        logging.getLogger(__name__).warning(
                            f"Error disposing scope: {e}"
                        )

            # Only dispose singleton scope if it exists
            if singleton_scope is not None:
                await singleton_scope.dispose()

        except Exception as e:
            raise DisposalError(f"Failed to dispose container: {e}") from e

    def add_pending_task(self, task: asyncio.Task[None]) -> None:
        """Add a pending disposal task."""
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
