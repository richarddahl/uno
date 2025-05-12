"""
Core functionality for the Uno framework.

This package contains fundamental building blocks and utilities used throughout
the Uno framework, including configuration, dependency injection, and tracing.
"""

from .tracing import (
    get_trace_context,
    set_trace_context,
    trace_span,
)

__all__ = [
    "get_trace_context",
    "set_trace_context",
    "trace_span",
]
