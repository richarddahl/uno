# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Event Sourcing Core Package

This package provides the core event sourcing functionality for the Uno framework.
"""

from __future__ import annotations

from .base import (
    DomainEvent,
    EventEnvelope,
    EventMetadata,
    EventStream,
    EventStreamSlice,
    EventType,
    EventData,
)

from .protocols import (
    DomainEventProtocol,
    EventProcessorProtocol,
    EventHandlerProtocol,
    EventDispatcherProtocol,
    EventRegistryProtocol,
    EventMiddlewareProtocol,
    EventBusProtocol,
    EventProtocol,
)

__all__ = [
    # Core types
    'DomainEvent',
    'EventEnvelope',
    'EventMetadata',
    'EventStream',
    'EventStreamSlice',
    'EventType',
    'EventData',
    
    # Protocols
    'DomainEventProtocol',
    'EventProcessorProtocol',
    'EventHandlerProtocol',
    'EventDispatcherProtocol',
    'EventRegistryProtocol',
    'EventMiddlewareProtocol',
    'EventBusProtocol',
    'EventProtocol',
]
