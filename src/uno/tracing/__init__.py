"""
Distributed tracing package for the Uno framework.

This package provides utilities for managing distributed tracing context
across service boundaries. It supports the W3C Trace Context specification
and integrates with the error handling and logging systems.
"""

from __future__ import annotations

from uno.tracing.context import (
    get_trace_context,
    set_trace_context,
    trace_span,
)

__all__ = [
    "get_trace_context",
    "set_trace_context",
    "trace_span",
]
