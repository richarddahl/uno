"""
Distributed tracing context management for the Uno framework.

This module provides utilities for managing distributed tracing context
across service boundaries. It supports the W3C Trace Context specification
and integrates with the error handling and logging systems.
"""

from __future__ import annotations

import contextlib
import contextvars
import uuid
from collections.abc import Iterator
from typing import Any

# Context variables for distributed tracing
trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)
span_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "span_id", default=None
)
parent_span_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "parent_span_id", default=None
)


def get_trace_context() -> dict[str, str | None]:
    """Get the current trace context as a dictionary.

    Returns:
        Dict containing trace context (trace_id, span_id, parent_span_id)
    """
    return {
        "trace_id": trace_id_var.get() or str(uuid.uuid4()),
        "span_id": span_id_var.get() or str(uuid.uuid4()),
        "parent_span_id": parent_span_id_var.get(),
    }


def set_trace_context(
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
) -> None:
    """Set the current trace context.

    Args:
        trace_id: The trace ID. If None, a new one will be generated.
        span_id: The current span ID. If None, a new one will be generated.
        parent_span_id: The parent span ID. Optional.
    """
    if trace_id is not None:
        trace_id_var.set(trace_id)
    if span_id is not None:
        span_id_var.set(span_id)
    if parent_span_id is not None:
        parent_span_id_var.set(parent_span_id)


@contextlib.contextmanager
def trace_span(name: str, **context: Any) -> Iterator[dict[str, Any]]:
    """Context manager for creating a new trace span.

    Args:
        name: The name of the span
        **context: Additional context to include in the span

    Yields:
        The span context dictionary
    """
    current_trace_id = trace_id_var.get() or str(uuid.uuid4())
    current_span_id = str(uuid.uuid4())
    parent_span_id = span_id_var.get()

    # Set new context
    token_trace = trace_id_var.set(current_trace_id)
    token_span = span_id_var.set(current_span_id)
    token_parent = parent_span_id_var.set(parent_span_id)

    try:
        span_context = {
            "trace_id": current_trace_id,
            "span_id": current_span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            **context,
        }
        yield span_context
    except Exception as e:
        # Include error in span context if an exception occurs
        span_context["error"] = str(e)
        raise
    finally:
        # Restore previous context
        trace_id_var.reset(token_trace)
        span_id_var.reset(token_span)
        parent_span_id_var.reset(token_parent)
