# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Core schema functionality for UI generation.

This module provides the foundation for schema-driven UI generation,
including common types, field definitions, and schema processing.
"""

from __future__ import annotations

import enum
import inspect
import json
import re
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, TypeVar, cast, get_type_hints

# Keep a simple reference to Config for schema discovery - avoid circular imports
from uno.config.base import Config


class SchemaVersion:
    """Schema version for tracking evolution of UI schemas."""

    def __init__(self, major: int, minor: int, patch: int = 0) -> None:
        """Initialize a schema version.

        Args:
            major: Major version (breaking changes)
            minor: Minor version (non-breaking additions)
            patch: Patch version (documentation/description changes)
        """
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        """Get string representation."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: SchemaVersion) -> bool:
        """Check if this version is compatible with another.

        Args:
            other: Another schema version

        Returns:
            True if compatible (same major version, same or higher minor)
        """
        return self.major == other.major and self.minor >= other.minor


class ValidationLevel(str, Enum):
    """Level of validation strictness."""

    NONE = "none"  # No validation
    BASIC = "basic"  # Type validation only
    STANDARD = "standard"  # Type + field-level constraints
    STRICT = "strict"  # All validations including cross-field


class ValidationScope(str, Enum):
    """Scope of validation rules."""

    ALL = "all"  # Apply to all environments
    DEVELOPMENT = "development"  # Development only
    TESTING = "testing"  # Testing only
    PRODUCTION = "production"  # Production only


class FieldCategory(str, Enum):
    """Category for grouping fields in UI."""

    GENERAL = "general"  # General settings
    SECURITY = "security"  # Security-related settings
    PERFORMANCE = "performance"  # Performance tuning
    LOGGING = "logging"  # Logging and diagnostics
    ADVANCED = "advanced"  # Advanced/expert settings
    EXPERIMENTAL = "experimental"  # Experimental features
    DEPRECATED = "deprecated"  # Deprecated settings


class FieldDisplayType(str, Enum):
    """Widget hint for UI display of field."""

    # Basic input types
    TEXT = "text"  # Simple text input
    PASSWORD = "password"  # Password field (masked)
    TEXTAREA = "textarea"  # Multi-line text area
    SELECT = "select"  # Dropdown select
    MULTISELECT = "multiselect"  # Multi-selection
    CHECKBOX = "checkbox"  # Boolean checkbox
    RADIO = "radio"  # Radio button group
    NUMBER = "number"  # Numeric input
    SLIDER = "slider"  # Slider control
    DATE = "date"  # Date picker
    TIME = "time"  # Time picker
    COLOR = "color"  # Color picker
    FILE = "file"  # File upload

    # Advanced input types
    JSON = "json"  # JSON editor
    CODE = "code"  # Code editor
    MARKDOWN = "markdown"  # Markdown editor
    RICH_TEXT = "rich_text"  # Rich text editor

    # Complex/composed types
    ARRAY = "array"  # Array of items
    OBJECT = "object"  # Nested object
    TABS = "tabs"  # Tabbed container
    CARD = "card"  # Card container

    # Special types
    HIDDEN = "hidden"  # Hidden field
    READONLY = "readonly"  # Read-only display
    CUSTOM = "custom"  # Custom widget

    @classmethod
    def register_custom_type(cls, name: str, value: str) -> None:
        """Register a custom display type at runtime.

        Args:
            name: Name for the enum member
            value: String value for the enum member
        """
        # We can't modify an Enum at runtime, but we can track custom values
        # that the system should recognize
        if not hasattr(cls, "_custom_types"):
            cls._custom_types = {}
        cls._custom_types[value] = name

    @classmethod
    def is_valid_type(cls, value: str) -> bool:
        """Check if a value is a valid display type.

        Args:
            value: Value to check

        Returns:
            True if valid
        """
        try:
            # Check if it's a standard enum value
            cls(value)
            return True
        except ValueError:
            # Check if it's a custom type
            custom_types = getattr(cls, "_custom_types", {})
            return value in custom_types


def discover_config_classes(module: ModuleType | str) -> list[type[Config]]:
    """Discover Config classes in a module or package.

    Args:
        module: Module or package to search in (or its string name)

    Returns:
        List of discovered Config classes
    """
    if isinstance(module, str):
        import importlib

        try:
            module = importlib.import_module(module)
        except ImportError:
            return []

    result: list[type[Config]] = []

    # Find all classes in the module
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Config) and obj is not Config:
            result.append(cast(type[Config], obj))

    # Recursively search submodules
    if hasattr(module, "__path__"):
        import pkgutil

        for _, name, is_pkg in pkgutil.iter_modules(module.__path__):
            import importlib

            full_name = f"{module.__name__}.{name}"
            try:
                submodule = importlib.import_module(full_name)
                result.extend(discover_config_classes(submodule))
            except ImportError:
                continue

    return result


# Define type for schema extension
class SchemaExtensionProtocol:
    """Protocol for schema extensions."""

    @classmethod
    def initialize(cls) -> None:
        """Initialize the extension."""
        ...

    @classmethod
    def get_name(cls) -> str:
        """Get the extension name."""
        ...

    @classmethod
    def extend_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        """Extend a schema with additional metadata or functionality."""
        ...

    @classmethod
    def extend_field(cls, field_schema: dict[str, Any]) -> dict[str, Any]:
        """Extend a field schema with additional metadata or functionality."""
        ...


class SchemaExtensionRegistry:
    """Registry for schema extensions."""

    _extensions: list[type[SchemaExtensionProtocol]] = []

    @classmethod
    def register_extension(cls, extension: type[SchemaExtensionProtocol]) -> None:
        """Register a schema extension.

        Args:
            extension: The extension class
        """
        if extension not in cls._extensions:
            cls._extensions.append(extension)
            extension.initialize()

    @classmethod
    def extend_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        """Apply all registered extensions to a schema.

        Args:
            schema: The schema to extend

        Returns:
            Extended schema
        """
        result = schema.copy()
        for extension in cls._extensions:
            result = extension.extend_schema(result)
        return result

    @classmethod
    def extend_field(cls, field_schema: dict[str, Any]) -> dict[str, Any]:
        """Apply all registered extensions to a field schema.

        Args:
            field_schema: The field schema to extend

        Returns:
            Extended field schema
        """
        result = field_schema.copy()
        for extension in cls._extensions:
            result = extension.extend_field(result)
        return result
