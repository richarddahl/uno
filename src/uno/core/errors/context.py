"""Error context management system."""

from typing import Any, Dict, Optional
from contextlib import contextmanager
import threading


_thread_local = threading.local()


class ErrorContext:
    """Context object for error information."""
    
    def __init__(self, data: Optional[dict[str, Any]] = None) -> None:
        """Initialize a new error context."""
        self.data = data or {}

    def update(self, data: dict[str, Any]) -> None:
        """Update the context with new data."""
        self.data.update(data)


class ErrorContextManager:
    """Context manager for error context."""
    
    def __init__(self, context: Optional[ErrorContext] = None) -> None:
        """Initialize a new error context manager."""
        self._context = context or ErrorContext()
        self._previous_context: Optional[ErrorContext] = None

    def __enter__(self) -> ErrorContext:
        """Enter the context."""
        self._previous_context = get_error_context()
        set_error_context(self._context)
        return self._context

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context."""
        if self._previous_context is not None:
            set_error_context(self._previous_context)
        else:
            clear_error_context()


def get_error_context() -> Optional[ErrorContext]:
    """Get the current error context."""
    return getattr(_thread_local, 'error_context', None)


def set_error_context(context: ErrorContext) -> None:
    """Set the current error context."""
    _thread_local.error_context = context


def clear_error_context() -> None:
    """Clear the current error context."""
    if hasattr(_thread_local, 'error_context'):
        del _thread_local.error_context
