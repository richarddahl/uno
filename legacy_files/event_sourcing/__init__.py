# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Event Sourcing Package

This package provides event sourcing capabilities for the Uno framework.
"""

from __future__ import annotations

# Core exports
from .core import (
    DomainEvent,
    EventEnvelope,
    EventMetadata,
    EventStream,
    EventStreamSlice,
    EventType,
    EventData,
)

# Re-export all public API
__all__ = [
    # Core types
    'DomainEvent',
    'EventEnvelope',
    'EventMetadata',
    'EventStream',
    'EventStreamSlice',
    'EventType',
    'EventData',
    
    # Submodules
    'aggregates',
    'bus',
    'commands',
    'core',
    'implementations',
    'projections',
    'repositories',
    'snapshots',
    'store',
]
