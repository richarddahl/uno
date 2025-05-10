# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event bus alias.

This module provides an alias to the in-memory event bus from the events package
for backward compatibility.
"""

from uno.events.implementations.bus import InMemoryEventBus

__all__ = ["InMemoryEventBus"]
