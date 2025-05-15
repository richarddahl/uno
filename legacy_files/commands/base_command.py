# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Command base classes for the Uno framework.

This module provides the base classes for commands in a CQRS architecture.
"""

from __future__ import annotations

from typing import ClassVar


class Command:
    """
    Base class for commands (write-side intent in CQRS/DDD).

    Commands represent an intention to change the system state.
    They are handled by command handlers which may emit domain events
    or directly modify the system state.
    """

    command_type: ClassVar[str] = "command"
