# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event sourcing implementations.

This module provides aliases to the in-memory implementations from the events package
for backward compatibility.
"""

from uno.persistence.event_sourcing.implementations.memory.bus import InMemoryEventBus
from uno.persistence.event_sourcing.implementations.memory.event_store import (
    InMemoryEventStore,
)

__all__ = [
    "InMemoryEventBus",
    "InMemoryEventStore",
]
