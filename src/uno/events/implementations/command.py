# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
DEPRECATED: In-memory command bus implementation.

This module provides an in-memory implementation of the command bus for testing
and simple applications.

This module is deprecated and will be removed in a future version.
Use the implementations in uno.commands.implementations instead.
"""

import warnings

from uno.commands.implementations.memory_bus import InMemoryCommandBus

# Re-export the implementation
__all__ = ["InMemoryCommandBus"]

# Issue a deprecation warning when the module is imported
warnings.warn(
    "The uno.events.implementations.command module is deprecated. "
    "Use uno.commands.implementations.memory_bus instead.",
    DeprecationWarning,
    stacklevel=2,
)
