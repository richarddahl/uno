# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Uno Events Package

This package provides event sourcing and event handling capabilities for the Uno framework.
"""

from __future__ import annotations

# Re-export from event_sourcing.core
from uno.event_sourcing.core import (
    DomainEvent,
    EventEnvelope,
    EventMetadata,
    EventStream,
    EventStreamSlice,
    EventType,
    EventData,
)

# Event Processing
from uno.event_processing import (
    AsyncEventHandlerAdapter,
    EventHandlerRegistry,
    handles,
    handler,
    register_event_handler,
)

# Re-export commonly used types and functions
__all__ = [
    # Core event types
    'DomainEvent',
    'EventEnvelope',
    'EventMetadata',
    'EventStream',
    'EventStreamSlice',
    'EventType',
    'EventData',
    
    # Event Processing
    'AsyncEventHandlerAdapter',
    'EventHandlerRegistry',
    'handles',
    'handler',
    'register_event_handler',
]
