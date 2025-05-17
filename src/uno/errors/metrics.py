# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error metrics integration for Uno.
Tracks error occurrences, types, and rates for observability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from uno.injection import ServiceRegistration

if TYPE_CHECKING:
    from uno.errors import UnoError

T = TypeVar("T")


def register_service(interface: type[T] | None = None, *, lifetime: str = "transient"):
    """Decorator to register a service with the DI container.

    Args:
        interface: The interface/abstract class that this service implements.
                 If None, the class itself is used as the interface.
        lifetime: The lifetime of the service ("singleton", "scoped", or "transient").
    """

    def decorator(cls: type[T]) -> type[T]:
        nonlocal interface
        if interface is None:
            interface = cls
        ServiceRegistration(interface, cls, lifetime)
        return cls

    return decorator


@register_service(lifetime="singleton")
class ErrorMetrics:
    """Tracks error metrics for Uno error handling.

    This service is registered as a singleton since we want to maintain
    error counts across the application lifetime.
    """

    def __init__(self) -> None:
        """Initialize the error metrics collector."""
        self.error_counts: dict[str, int] = {}

    def record_error(self, error: Exception) -> None:
        """Record an error occurrence.

        Args:
            error: The error that occurred.
        """
        error_name = error.__class__.__name__
        self.error_counts[error_name] = self.error_counts.get(error_name, 0) + 1

        # If it's an UnoError, record additional context
        if isinstance(error, Exception):
            # Use getattr to safely access code attribute
            if hasattr(error, "code"):
                code = getattr(error, "code", "")
                self.error_counts[f"{error_name}:{code}"] = (
                    self.error_counts.get(f"{error_name}:{code}", 0) + 1
                )

    async def arecord_error(self, error: Exception) -> None:
        self.record_error(error)

    def get_error_count(self, error_type: str) -> int:
        return self.error_counts.get(error_type, 0)

    def reset(self) -> None:
        self.error_counts.clear()
