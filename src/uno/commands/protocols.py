# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the commands package.

This module contains the core protocols that define the interfaces for command handling.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

C = TypeVar("C")  # Generic command type
T = TypeVar("T")  # Return type


@runtime_checkable
class CommandHandlerProtocol(Protocol[C, T]):
    """
    Protocol for command handlers.

    Defines the interface for components that process commands and produce results.
    """

    async def handle(self, command: C) -> T: ...


@runtime_checkable
class CommandBusProtocol(Protocol):
    """
    Protocol for command buses (dispatching commands).

    Defines the interface for components that dispatch commands to their handlers.
    """

    async def dispatch(self, command: Any) -> Any: ...

    def register_handler(
        self, command_type: type, handler: CommandHandlerProtocol
    ) -> None: ...
