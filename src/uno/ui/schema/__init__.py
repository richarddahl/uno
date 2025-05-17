# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Schema-driven UI generation for Uno applications.

This package provides tools for generating user interfaces from schema
definitions, with support for various UI frameworks and field types.
"""

from .core import (
    SchemaVersion,
    ValidationLevel,
    ValidationScope,
    FieldCategory,
    FieldDisplayType,
    discover_config_classes,
    SchemaExtensionRegistry,
)
from .components import UIComponentRegistry
from .registry import (
    SchemaRegistry,
    register_discovered_schemas,
    create_api_response,
)
from .adapters import SchemaAdapter

__all__ = [
    # Core schema types
    "SchemaVersion",
    "ValidationLevel",
    "ValidationScope",
    "FieldCategory",
    "FieldDisplayType",
    # Component management
    "UIComponentRegistry",
    # Schema registry
    "SchemaRegistry",
    "register_discovered_schemas",
    "create_api_response",
    # Discovery and extension
    "discover_config_classes",
    "SchemaExtensionRegistry",
    # Framework adapters
    "SchemaAdapter",
]
