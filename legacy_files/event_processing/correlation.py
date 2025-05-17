# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Event correlation functionality.

This module provides correlation context for tracing events through the system,
with proper async-first patterns.
"""

from __future__ import annotations

import uuid
import contextlib
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class EventCorrelationContext(BaseModel):
    """
    Correlation context for Uno events.

    Provides correlation identifiers and tracing information for events.
    Follows an async-first approach for all operations.
    """

    correlation_id: str = Field(..., description="Correlation ID for event tracing")
    trace_id: str | None = Field(None, description="Distributed trace ID")
    span_id: str | None = Field(None, description="Current span ID for tracing")
    parent_span_id: str | None = Field(None, description="Parent span ID for tracing")

    # Custom context fields (arbitrary, validated)
    custom: dict[str, Any] = Field(
        default_factory=dict, description="Custom context fields"
    )

    model_config = ConfigDict(
        frozen=True,  # Context objects are immutable
    )

    @classmethod
    def new(
        cls,
        trace_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        custom: dict[str, Any] | None = None,
    ) -> EventCorrelationContext:
        """
        Generate a new correlation context with a unique correlation ID.

        Args:
            trace_id: Optional distributed trace ID
            span_id: Optional span ID for tracing
            parent_span_id: Optional parent span ID for tracing
            custom: Optional custom context fields

        Returns:
            A new correlation context
        """
        return cls(
            correlation_id=str(uuid.uuid4()),
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            custom=custom or {},
        )

    @classmethod
    def from_existing(
        cls,
        correlation_id: str,
        trace_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        custom: dict[str, Any] | None = None,
    ) -> EventCorrelationContext:
        """
        Create context from existing correlation ID.

        Args:
            correlation_id: The existing correlation ID
            trace_id: Optional distributed trace ID
            span_id: Optional span ID for tracing
            parent_span_id: Optional parent span ID for tracing
            custom: Optional custom context fields

        Returns:
            A new correlation context
        """
        return cls(
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            custom=custom or {},
        )

    @classmethod
    def from_metadata(
        cls, metadata: dict[str, Any] | None
    ) -> EventCorrelationContext | None:
        """
        Extract correlation context from event metadata dict.

        Args:
            metadata: The metadata to extract from

        Returns:
            A new correlation context, or None if no correlation ID is found
        """
        if not metadata or "correlation_id" not in metadata:
            return None

        return cls(
            correlation_id=metadata["correlation_id"],
            trace_id=metadata.get("trace_id"),
            span_id=metadata.get("span_id"),
            parent_span_id=metadata.get("parent_span_id"),
            custom={
                k: v
                for k, v in metadata.items()
                if k not in {"correlation_id", "trace_id", "span_id", "parent_span_id"}
            },
        )

    def inject(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Inject correlation context into a metadata dict.

        Args:
            metadata: Optional existing metadata to inject into

        Returns:
            A new dict with correlation context injected
        """
        base = dict(metadata) if metadata else {}
        base["correlation_id"] = self.correlation_id

        if self.trace_id:
            base["trace_id"] = self.trace_id

        if self.span_id:
            base["span_id"] = self.span_id

        if self.parent_span_id:
            base["parent_span_id"] = self.parent_span_id

        base.update(self.custom)
        return base

    @contextlib.asynccontextmanager
    async def span(
        self, span_name: str | None = None
    ) -> AsyncGenerator[EventCorrelationContext, None]:
        """
        Create a new span in the trace.

        This is an async context manager that creates a new span in the trace,
        making the current span the parent of the new span.

        Args:
            span_name: Optional name for the span

        Yields:
            A new correlation context with the new span
        """
        # Create a new span ID
        new_span_id = str(uuid.uuid4())

        # Create a new context with the new span
        new_context = self.__class__(
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            span_id=new_span_id,
            parent_span_id=self.span_id,
            custom=self.custom.copy(),
        )

        if span_name:
            new_context.custom["span_name"] = span_name

        try:
            # Yield the new context to the caller
            yield new_context
        finally:
            # No clean-up needed
            pass
