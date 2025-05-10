# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Command handling for the Uno framework.

This package contains the core components for command handling in a CQRS/DDD architecture.
"""

from .base_command import Command
from .di import register_command_services
from .errors import (
    CommandDispatchError,
    CommandError,
    CommandErrorCode,
    CommandHandlerError,
    CommandNotFoundError,
    CommandValidationError,
)
from .handler import CommandBus
from .implementations.handler import InMemoryCommandBus
from .implementations.memory_bus import InMemoryCommandBus as NewInMemoryCommandBus
from .implementations.structural_bus import StructuralCommandBus
from .protocols import CommandBusProtocol, CommandHandlerProtocol

__all__ = [
    # Base types
    "Command",
    # Protocols
    "CommandBusProtocol",
    "CommandHandlerProtocol",
    # Core components
    "CommandBus",
    # Dependency injection
    "register_command_services",
    # Implementations
    "InMemoryCommandBus",
    "NewInMemoryCommandBus",
    "StructuralCommandBus",
    # Errors
    "CommandDispatchError",
    "CommandError",
    "CommandErrorCode",
    "CommandHandlerError",
    "CommandNotFoundError",
    "CommandValidationError",
]
    "CommandDispatchError",
    "CommandError",
    "CommandErrorCode",
    "CommandHandlerError",
    "CommandNotFoundError",
    "CommandValidationError",
]
