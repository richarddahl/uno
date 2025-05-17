"""
Context implementation for the Uno metrics system.
"""

from __future__ import annotations

from typing import Any, TypeVar, Optional
from contextvars import ContextVar, Token
from collections.abc import Iterator


T = TypeVar("T")

class ContextKey:
    """A key that can be used to identify a context value."""

    def __init__(self, name: str) -> None:
        """Initialize a context key with a name."""
        self._name = name

    @property
    def name(self) -> str:
        """Get the name of the context key."""
        return self._name

    def __hash__(self) -> int:
        """Get the hash of the context key."""
        return hash(self._name)

    def __eq__(self, other: Any) -> bool:
        """Check if two context keys are equal."""
        if not isinstance(other, ContextKey):
            return False
        return self._name == other._name

    def __str__(self) -> str:
        """Get the string representation of the context key."""
        return self._name


class ContextValue:
    """A value that can be associated with a context key."""

    def __init__(self, value: Any) -> None:
        """Initialize a context value with a value."""
        self._value = value

    @property
    def value(self) -> Any:
        """Get the value of the context."""
        return self._value

    def __str__(self) -> str:
        """Get the string representation of the context value."""
        return str(self._value)


class Context:
    """A context that can be used to manage context values."""

    def __init__(self, values: Optional[Mapping[ContextKey, ContextValue]] = None) -> None:
        """Initialize a context with optional initial values."""
        self._values: dict[ContextKey, ContextValue] = dict(values or {})

    def get(self, key: ContextKey, default: T | None = None) -> T | None:
        """Get a value from the context."""
        return self._values.get(key, default)

    def set(self, key: ContextKey, value: ContextValue) -> Token:
        """Set a value in the context."""
        token = ContextVar(key.name).set(value)
        self._values[key] = value
        return token

    def reset(self, token: Token) -> None:
        """Reset a context value to its previous state."""
        ContextVar(self._values[token].name).reset(token)
        del self._values[token]

    def copy(self) -> Context:
        """Create a copy of the context."""
        return Context(self._values.copy())

    def merge(self, other: Context) -> Context:
        """Merge with another context."""
        result = self.copy()
        result._values.update(other._values)
        return result


class ContextProvider:
    """A provider that can create and manage contexts."""

    def __init__(self) -> None:
        """Initialize a context provider."""
        self._current = Context()

    @property
    def current(self) -> Context:
        """Get the current context."""
        return self._current

    def new(self) -> Context:
        """Create a new context."""
        return Context()

    def with_context(self, context: Context) -> Context:
        """Create a context manager for the given context."""
        return context


class ContextFactory:
    """A factory that can create contexts."""

    def create(self) -> Context:
        """Create a new context."""
        return Context()

    def from_dict(self, data: dict[str, Any]) -> Context:
        """Create a context from a dictionary."""
        values = {
            ContextKey(key): ContextValue(value)
            for key, value in data.items()
        }
        return Context(values)

    def to_dict(self, context: Context) -> dict[str, Any]:
        """Convert a context to a dictionary."""
        return {
            key.name: value.value
            for key, value in context._values.items()
        }
