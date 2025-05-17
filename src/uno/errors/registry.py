"""Unified error registry implementation for the Uno framework."""

import threading
import logging
from typing import Any, Dict


class ErrorRegistry:
    """Singleton registry for all error codes and categories in the Uno framework."""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls) -> "ErrorRegistry":
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._categories = {}
                instance._codes = {}
                cls._instance = instance
            return cls._instance

    def __init__(self) -> None:
        """Initialize registry attributes if not already present."""
        if not hasattr(self, "_categories"):
            self._categories = {}
        if not hasattr(self, "_codes"):
            self._codes = {}

    def register_category(self, name: str, parent: Any = None) -> Any:
        """Register a category in the registry.

        Args:
            name: The category name
            parent: Optional parent category

        Returns:
            The registered ErrorCategory
        """
        with self._lock:
            if name in self._categories:
                return self._categories[name]

            from uno.errors.base import ErrorCategory

            category = ErrorCategory(name, parent)
            self._categories[name] = category
            return category

    def register_code(self, code: str, category_name: str) -> Any:
        """Register a code in the registry.

        Args:
            code: The error code
            category_name: The category name

        Returns:
            The registered ErrorCode
        """
        with self._lock:
            key = f"{category_name}.{code}"
            if key in self._codes:
                return self._codes[key]

            # Get or create the category first
            category = self.get_category(category_name)

            # Then create and register the code
            from uno.errors.base import ErrorCode

            error_code = ErrorCode(code, category)
            self._codes[key] = error_code

            # Also register by code name alone for backward compatibility
            self._codes[code] = error_code

            return error_code

    def get_category(self, name: str, parent: Any = None) -> Any:
        """Get or create a category.

        Args:
            name: The category name
            parent: Optional parent category

        Returns:
            The ErrorCategory
        """
        with self._lock:
            if name in self._categories:
                return self._categories[name]
            return self.register_category(name, parent)

    def get_code(self, code: str, category_name: str = "INTERNAL") -> Any:
        """Get or create an error code.

        Args:
            code: The error code
            category_name: The category name (defaults to INTERNAL)

        Returns:
            The ErrorCode
        """
        with self._lock:
            # Try full key first
            key = f"{category_name}.{code}"
            if key in self._codes:
                return self._codes[key]

            # Then try just code (for backward compatibility)
            if code in self._codes:
                return self._codes[code]

            # Not found, register a new one
            return self.register_code(code, category_name)

    def lookup_code(self, code: str) -> Any:
        """Look up an error code without creating it if missing.

        Args:
            code: The error code string

        Returns:
            The ErrorCode or None if not found
        """
        # First check direct code lookup
        if code in self._codes:
            return self._codes[code]

        # Then try all registered keys
        for key, error_code in self._codes.items():
            if key.endswith(f".{code}") or error_code.code == code:
                return error_code

        # Not found
        logging.warning(f"Error code '{code}' not found in registry, returning None")
        return None


# Create a single instance for use throughout the app
registry = ErrorRegistry()
