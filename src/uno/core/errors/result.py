# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Result objects for functional error handling in the Uno framework.

This module implements the Result pattern (also known as the Either pattern)
for handling errors in a functional way without relying on exceptions.
"""

import functools
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
    Awaitable,
)

from uno.core.errors.base import ErrorCode, FrameworkError, get_error_context

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
U = TypeVar("U")


@runtime_checkable
class HasToDict(Protocol):
    """
    Protocol for objects that can be converted to dictionaries.
    """

    def to_dict(self) -> dict[str, Any]: ...


class Result(Generic[T, E], ABC):
    """Abstract base class for Result monad."""

    @property
    @abstractmethod
    def is_success(self) -> bool: ...

    @property
    @abstractmethod
    def is_failure(self) -> bool: ...

    @abstractmethod
    def map(self, func: Callable[[T], U]) -> "Result[U, E]": ...

    @abstractmethod
    def flat_map(self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]": ...

    @abstractmethod
    def unwrap(self) -> T: ...

    @abstractmethod
    def unwrap_or(self, default: T) -> T: ...

    @abstractmethod
    def unwrap_or_else(self, func: Callable[[E], T]) -> T: ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    def ensure(self, predicate: Callable[[T], bool], error: E) -> "Result[T, E]":
        """
        Return Failure if predicate is False for a Success value, else self.
        """
        if self.is_success and not predicate(self.unwrap()):
            return Failure(error)
        return self

    def recover(self, func: Callable[[E], T]) -> "Result[T, E]":
        """
        Transform a Failure into a Success by applying func to the error.
        """
        if self.is_failure:
            return Success(func(self.error))  # type: ignore[attr-defined]
        return self

    async def map_async(self, func: Callable[[T], 'Awaitable[U]']) -> "Result[U, E]":
        """
        Map the value of a Success asynchronously.
        """
        if self.is_success:
            try:
                return Success(await func(self.unwrap()))
            except Exception as e:
                return Failure(cast("E", e))
        return self  # type: ignore

    async def flat_map_async(self, func: Callable[[T], 'Awaitable[Result[U, E]]']) -> "Result[U, E]":
        """
        Flat map the value of a Success asynchronously.
        """
        if self.is_success:
            try:
                return await func(self.unwrap())
            except Exception as e:
                return Failure(cast("E", e))
        return self  # type: ignore


@dataclass(frozen=True)
class Success(Result[T, E], Generic[T, E]):
    """
    Represents a successful result with a value.

    Attributes:
        value: The successful result value
    """

    value: T

    @property
    def is_success(self) -> bool:
        """Check if the result is successful."""
        return True

    @property
    def is_failure(self) -> bool:
        """Check if the result is a failure."""
        return False

    @property
    def error(self) -> None:
        """Get the error if the result is a failure."""
        return None

    def map(self, func: Callable[[T], U]) -> "Result[U, E]":
        """
        Map the value of a successful result.

        Args:
            func: The function to apply to the value

        Returns:
            A new Success with the mapped value, or the original Failure
        """
        try:
            return Success(func(self.value))
        except Exception as e:
            return Failure(cast("E", e))  # Cast captured exception to E

    def flat_map(self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """
        Apply a function that returns a Result to the value of a successful result.

        Args:
            func: The function to apply to the value

        Returns:
            The Result returned by the function, or the original Failure
        """
        try:
            return func(self.value)
        except Exception as e:
            return Failure(cast("E", e))  # Cast captured exception to E

    def on_success(self, func: Callable[[T], Any]) -> "Success[T, E]":
        """
        Execute a function with the value if the result is successful.

        Args:
            func: The function to execute

        Returns:
            The original Result
        """
        with suppress(Exception):
            func(self.value)
        return self

    def on_failure(self, func: Callable[[E], Any]) -> "Success[T, E]":
        """
        Execute a function with the error if the result is a failure.

        Args:
            func: The function to execute

        Returns:
            The original Result
        """
        # No-op for Success
        return self

    # Backward compatibility methods for tests
    def unwrap(self) -> T:
        """
        Unwrap a successful result to get its value.

        Returns:
            The value of the successful result

        Raises:
            RuntimeError: If the result is a failure
        """
        return self.value

    def unwrap_or(self, default: T) -> T:
        """
        Unwrap a result, returning a default value if it's a failure.

        Args:
            default: The default value to return if the result is a failure

        Returns:
            The value of the successful result, or the default value
        """
        return self.value

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """
        Unwrap a result, computing a default value from the error if it's a failure.

        Args:
            func: The function to compute the default value from the error

        Returns:
            The value of the successful result, or the computed default value
        """
        return self.value

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result to a dictionary.

        Returns:
            A dictionary representation of the result
        """
        if isinstance(self.value, dict):
            return {"status": "success", "data": self.value}
        elif isinstance(self.value, HasToDict):
            return {"status": "success", "data": self.value.to_dict()}
        else:
            return {"status": "success", "data": self.value}

    def __str__(self) -> str:
        """String representation of a successful result."""
        return f"Success({self.value})"

    def __repr__(self) -> str:
        """Detailed string representation of a successful result."""
        return f"Success({self.value!r})"


@dataclass(frozen=True)
class Failure(Result[T, E], Generic[T, E]):
    """
    Represents a failed result with an error.

    Attributes:
        error: The error that caused the failure
        traceback: The traceback at the time of failure (optional)
    """

    error: E
    traceback: str | None = None

    def __post_init__(self) -> None:
        """Initialize the traceback if not provided."""
        if self.traceback is None:
            # We can't set attributes directly due to frozen=True
            object.__setattr__(self, "traceback", "".join(traceback.format_exc()))

    @property
    def is_success(self) -> bool:
        """Check if the result is successful."""
        return False

    @property
    def is_failure(self) -> bool:
        """Check if the result is a failure."""
        return True

    @property
    def value(self) -> None:
        """Get the value if the result is successful."""
        return None

    def map(self, func: Callable[[T], U]) -> "Result[U, E]":
        """
        Map the value of a successful result.

        Args:
            func: The function to apply to the value

        Returns:
            The original Failure
        """
        # No-op for Failure, return self typed for U, E
        return cast("Failure[U, E]", self)

    def flat_map(self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """
        Apply a function that returns a Result to the value of a successful result.

        Args:
            func: The function to apply to the value

        Returns:
            The original Failure
        """
        # No-op for Failure, return self typed for U, E
        return cast("Failure[U, E]", self)

    def on_success(self, func: Callable[[T], Any]) -> "Failure[T, E]":
        """
        Execute a function with the value if the result is successful.

        Args:
            func: The function to execute

        Returns:
            The original Result
        """
        # No-op for Failure
        return self

    def on_failure(self, func: Callable[[E], Any]) -> "Failure[T, E]":
        """
        Execute a function with the error if the result is a failure.

        Args:
            func: The function to execute

        Returns:
            The original Result
        """
        with suppress(Exception):
            func(self.error)
        return self

    # Backward compatibility methods for tests
    def unwrap(self) -> T:
        """
        Unwrap a successful result to get its value.

        Raises:
            RuntimeError: Since this is a failure
        """
        raise RuntimeError(f"Cannot unwrap a Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """
        Unwrap a result, returning a default value if it's a failure.

        Args:
            default: The default value to return if the result is a failure

        Returns:
            The default value since this is a failure
        """
        return default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """
        Unwrap a result, computing a default value from the error if it's a failure.

        Args:
            func: The function to compute the default value from the error

        Returns:
            The computed default value since this is a failure
        """
        return func(self.error)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result to a dictionary.

        Returns:
            A dictionary representation of the result
        """
        if isinstance(self.error, FrameworkError):
            return {"status": "error", "error": self.error.to_dict()}
        else:
            # Create a generic error structure
            error_detail = {
                "message": str(self.error),
                "error_code": ErrorCode.UNKNOWN_ERROR,
                "context": get_error_context(),
            }
            if hasattr(self.error, "__dict__"):
                # Include any public attributes of the exception
                for key, value in self.error.__dict__.items():
                    if not key.startswith("_") and key not in error_detail:
                        error_detail[key] = value

            return {"status": "error", "error": error_detail}

    def __str__(self) -> str:
        """String representation of a failed result."""
        return f"Failure({self.error})"

    def __repr__(self) -> str:
        """Detailed string representation of a failed result."""
        return f"Failure({self.error!r})"


def of(value: T) -> Success[T, Any]:  # Error type is effectively 'Any' here
    """
    Create a successful result with a value.

    Args:
        value: The value

    Returns:
        A successful result
    """
    return Success(value)


def failure(error: E) -> Failure[Any, E]:  # Value type is effectively 'Any' here
    """
    Create a failed result with an error.

    Args:
        error: The error

    Returns:
        A failed result
    """
    return Failure(error)


def from_exception(func: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """
    Decorator to convert a function that might raise exceptions to one that returns a Result.

    Args:
        func: The function to decorate

    Returns:
        A function that returns a Result
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
        try:
            return Success(func(*args, **kwargs))
        except Exception as e:
            return Failure(e)

    return wrapper


async def from_awaitable(awaitable: Any) -> Result[T, Exception]:
    """
    Convert an awaitable that might raise exceptions to a Result.

    Args:
        awaitable: The awaitable

    Returns:
        A Result
    """
    try:
        return Success(await awaitable)
    except Exception as e:
        return Failure(e)


def combine(results: list[Result[T, E]]) -> Result[list[T], E]:
    """
    Combine multiple Results into a single Result.

    Args:
        results: The Results to combine

    Returns:
        A Success with a list of values if all Results are successful,
        or the first Failure
    """
    values: list[T] = []
    for result in results:
        if result.is_failure:
            # The failure carries its specific error type E
            return cast("Failure[list[T], E]", result)
        if result.value is not None:  # Check for None to satisfy type checker
            values.append(result.value)
    return Success(values)


def combine_dict(results: dict[str, Result[T, E]]) -> Result[dict[str, T], E]:
    """
    Combine multiple Results in a dictionary into a single Result.

    Args:
        results: The Results to combine

    Returns:
        A Success with a dictionary of values if all Results are successful,
        or the first Failure
    """
    values: dict[str, T] = {}
    for key, result in results.items():
        if result.is_failure:
            # The failure carries its specific error type E
            return cast("Failure[dict[str, T], E]", result)
        if result.value is not None:  # Check for None to satisfy type checker
            values[key] = result.value
    return Success(values)
