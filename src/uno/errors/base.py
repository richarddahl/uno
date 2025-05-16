# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Base error classes and utilities for the Uno error handling system.

This module provides the foundation for structured error handling with
error codes, contextual information, and error categories.
"""

import logging
from datetime import UTC, datetime
import inspect
import os
from enum import Enum
from typing import Any, ClassVar, Final


class ErrorSeverity(str, Enum):
    """Severity levels for errors across Uno (logging, domain, infra, etc)."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    FATAL = "fatal"


class ErrorCategory:
    """Base class for error categories with hierarchical support."""

    # Registry of all categories by name for validation
    _registry: dict[str, "ErrorCategory"] = {}

    def __init__(self, name: str, parent: "ErrorCategory | None" = None) -> None:
        """Initialize a new error category.

        Args:
            name: Unique identifier for this category
            parent: Optional parent category for hierarchical structure
        """
        if name in ErrorCategory._registry:
            raise ValueError(f"Error category '{name}' already exists")

        self.name = name
        self.parent = parent
        ErrorCategory._registry[name] = self

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ErrorCategory):
            return False
        return self.name == other.name

    def is_subcategory_of(self, category: "ErrorCategory") -> bool:
        """Check if this category is a subcategory of the given category."""
        current: "ErrorCategory | None" = self
        while current:
            if current == category:
                return True
            current = current.parent
        return False

    def get_all_subcategories(self) -> set["ErrorCategory"]:
        """Get this category and all its subcategories recursively.

        Returns:
            A set containing this category and all its subcategories.
        """
        result = {self}
        queue = [self]

        while queue:
            current = queue.pop(0)
            # Find direct children
            for category in ErrorCategory._registry.values():
                if category.parent == current and category not in result:
                    result.add(category)
                    queue.append(category)

        return result

    @staticmethod
    def is_error_in_category(error: "UnoError", category: "ErrorCategory") -> bool:
        """Check if an error's category is within a category or its subcategories.

        Args:
            error: The error to check
            category: The category to check against

        Returns:
            True if the error's category is the given category or any of its subcategories.
        """
        return error.category.is_subcategory_of(category)

    @staticmethod
    def filter_errors_by_category(
        errors: list["UnoError"], category: "ErrorCategory"
    ) -> list["UnoError"]:
        """Filter a list of errors to those in a category or any of its subcategories.

        Args:
            errors: The list of errors to filter
            category: The category to filter by

        Returns:
            A list of errors that belong to the given category or any of its subcategories.
        """
        subcategories = category.get_all_subcategories()
        return [error for error in errors if error.category in subcategories]

    @classmethod
    def get_all(cls) -> list["ErrorCategory"]:
        """Get all registered categories.

        Returns:
            A list of all registered error categories
        """
        return list(cls._registry.values())

    @classmethod
    def get_by_name(cls, name: str) -> "ErrorCategory | None":
        """Get a category by its name.

        Args:
            name: Category name to look up

        Returns:
            The category if found, None otherwise
        """
        return cls._registry.get(name)

    @classmethod
    def get_or_create(
        cls, name: str, parent: "ErrorCategory | None" = None
    ) -> "ErrorCategory":
        existing = cls.get_by_name(name)
        if existing is not None:
            return existing
        return cls(name, parent=parent)


INTERNAL: Final = ErrorCategory.get_or_create("INTERNAL")


class ErrorCode:
    """Base class for error codes with hierarchical support and category association."""

    # Registry of all error codes by name
    _registry: ClassVar[dict[str, "ErrorCode"]] = {}

    def __init__(
        self,
        code: str,
        category: ErrorCategory = INTERNAL,
        parent: "ErrorCode | None" = None,
    ) -> None:
        """Initialize a new error code.

        Args:
            code: Unique identifier for this error code
            category: The category this error code belongs to
            parent: Optional parent error code for hierarchical structure
        """
        if code in ErrorCode._registry:
            raise ValueError(f"Error code '{code}' already exists")

        self.code = code
        self.category = category
        self.parent = parent
        ErrorCode._registry[code] = self

    def __str__(self) -> str:
        return self.code

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ErrorCode):
            return False
        return self.code == other.code

    def is_subcode_of(self, parent_code: "ErrorCode") -> bool:
        """Check if this error code is a subcode of the given error code.

        Args:
            parent_code: The potential parent error code

        Returns:
            Whether this code is a subcode of the given code
        """
        current: "ErrorCode | None" = self
        while current:
            if current == parent_code:
                return True
            current = current.parent
        return False

    def get_all_subcodes(self) -> set["ErrorCode"]:
        """Get this error code and all its subcodes recursively.

        Returns:
            A set containing this error code and all its subcodes
        """
        result = {self}
        queue = [self]

        while queue:
            current = queue.pop(0)
            # Find direct children
            for code in ErrorCode._registry.values():
                if code.parent == current and code not in result:
                    result.add(code)
                    queue.append(code)

        return result

    @classmethod
    def get_by_code(
        cls, code: str, *, raise_if_missing: bool = True
    ) -> "ErrorCode | None":
        """Get an error code by its string representation.

        Args:
            code: The error code string
            raise_if_missing: Whether to raise if the code is not found (defaults to True)

        Returns:
            The ErrorCode object if found, None if not found and raise_if_missing is False

        Raises:
            ValueError: If the error code is not found and raise_if_missing is True
        """
        error_code = cls._registry.get(code)
        if error_code is None:
            if raise_if_missing:
                raise ValueError(f"Error code '{code}' not found in registry")
            else:
                logging.warning(
                    f"Error code '{code}' not found in registry, returning None"
                )
                return None
        return error_code

    @classmethod
    def filter_by_category(cls, category: ErrorCategory) -> list["ErrorCode"]:
        """Filter error codes by category.

        Args:
            category: The category to filter by

        Returns:
            List of error codes belonging to the specified category or its subcategories
        """
        # Get all subcategories
        subcategories = category.get_all_subcategories()

        # Filter error codes by category
        return [
            code for code in cls._registry.values() if code.category in subcategories
        ]

    @classmethod
    def get_or_create(cls, name: str, category: "ErrorCategory") -> "ErrorCode":
        existing = cls.get_by_code(name, raise_if_missing=False)
        if existing is not None:
            return existing
        return cls(name, category=category)


# Define base error categories and codes here
INTERNAL_ERROR: Final = ErrorCode.get_or_create("INTERNAL_ERROR", INTERNAL)


class UnoError(Exception):
    """
    Base error class for Uno errors.
    Should only be subclassed for package-specific errors, not instantiated directly.
    """

    # Add type annotations for class attributes
    message: str
    code: ErrorCode
    severity: ErrorSeverity
    context: dict[str, Any] | None
    timestamp: datetime

    def add_context(self, key: str, value: Any) -> "UnoError":
        """Add a key-value pair to the error context and return self for chaining."""
        if not hasattr(self, "context") or self.context is None:
            self.context = {}
        self.context[key] = value
        return self

    def __new__(cls, *args: Any, **kwargs: Any) -> "UnoError":
        if cls is UnoError:
            raise TypeError(
                "Do not instantiate UnoError directly; subclass it for specific errors."
            )
        return super().__new__(cls)

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new UnoError (never instantiate directly).

        Args:
            code: ErrorCode object containing the code and category
            message: Human-readable error message
            severity: Severity level of the error
            context: Additional contextual information
            **kwargs: Ignored. Accepts arbitrary keyword arguments for subclass compatibility.
        """
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)

        full_context = context or {}
        full_context.update(kwargs)

        self.code: ErrorCode = code
        self.message = message
        self.category = code.category  # Get category from the ErrorCode
        self.severity = severity
        self.context = full_context
        self.timestamp = datetime.now(UTC)

    @classmethod
    async def async_init(
        cls,
        message: str,
        code: ErrorCode,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "UnoError":
        """
        Async factory for UnoError. Subclasses may override for richer async context.
        """
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        return cls(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )

    def with_context(self, context: dict[str, Any]) -> "UnoError":
        """Return a new error with additional context."""
        # Combine the original context with the new context
        # The __init__ will handle merging this with any kwargs
        combined_context = {**(self.context or {}), **context}

        # Get the class of the current instance (supports subclasses)
        error_class = self.__class__

        # Create a new instance with the same attributes as the original
        new_error = error_class(
            message=self.message,
            code=self.code,
            severity=self.severity,
            context=combined_context,
        )

        # Copy any additional attributes that might have been added
        for attr_name, attr_value in self.__dict__.items():
            if attr_name not in (
                "code",
                "message",
                "category",
                "severity",
                "context",
                "timestamp",
            ):
                setattr(new_error, attr_name, attr_value)

        # Ensure __cause__ is properly copied as well
        if hasattr(self, "__cause__") and self.__cause__ is not None:
            new_error.__cause__ = self.__cause__

        return new_error

    def __str__(self) -> str:
        """Get string representation of the error.

        Returns:
            String in format 'code: message'
        """
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the error.

        Returns:
            Dictionary with all error properties
        """
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.name,
            "severity": self.severity.name,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


def get_error_context() -> dict[str, Any]:
    """
    Get context information about where an error occurred.

    Returns contextual information about the calling frame including:
    - file_name: The name of the file
    - line_number: The line number where the error occurred
    - function_name: The name of the function where the error occurred
    - timestamp: The UTC timestamp when the error occurred

    Returns:
        dict[str, Any]: A dictionary with error context information
    """
    # Get the frame 1 level up (caller of this function)
    current_frame = inspect.currentframe()
    if current_frame is None:
        # If we can't get a frame (rare but possible), return minimal context
        return {
            "file_name": "unknown",
            "line_number": 0,
            "function_name": "unknown",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    caller_frame = current_frame.f_back
    if caller_frame is None:
        # This would be very unusual, but let's handle it anyway
        return {
            "file_name": "unknown",
            "line_number": 0,
            "function_name": "unknown",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    frame_info = inspect.getframeinfo(caller_frame)

    # Extract relevant information
    file_name = os.path.basename(frame_info.filename)
    line_number = frame_info.lineno
    function_name = frame_info.function

    # Create and return the context dictionary
    return {
        "file_name": file_name,
        "line_number": line_number,
        "function_name": function_name,
        "timestamp": datetime.now(UTC).isoformat(),
    }
