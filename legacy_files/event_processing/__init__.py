# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Event Processing Package

This package provides event processing capabilities for the Uno framework.
"""

from __future__ import annotations

# Core imports
from .registry import EventHandlerRegistry, register_event_handler, AsyncEventHandlerAdapter
from .handlers.decorator import handles, handler

# Re-export core types and functions
__all__ = [
    # Core components
    'AsyncEventHandlerAdapter',
    'EventHandlerRegistry',
    'register_event_handler',
    
    # Handler decorators
    'handles',
    'handler',
    
    # Submodules
    'handlers',
    'middleware',
    'metrics',
    'pipeline',
    'tracing',
    
    # Core functionality
    'config',
    'context',
    'correlation',
    'injection',
]
