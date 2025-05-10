# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event store alias.

This module provides an alias to the in-memory event store from the events package
for backward compatibility.
"""

from uno.events.implementations.store import InMemoryEventStore

__all__ = ["InMemoryEventStore"]
