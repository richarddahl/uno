# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
UI components and generators for Uno applications.

This package provides tools for building user interfaces for Uno applications,
including schema-driven UI generation, components, and themes.
"""

from uno.ui.schema import (
    SchemaVersion,
    ValidationLevel,
    ValidationScope,
    FieldCategory,
    FieldDisplayType,
    UIComponentRegistry,
    SchemaRegistry,
    register_discovered_schemas,
    create_api_response,
    discover_config_classes,
    SchemaExtensionRegistry,
    SchemaAdapter,
)

__all__ = [
    # Re-export schema functionality
    "SchemaVersion",
    "ValidationLevel",
    "ValidationScope",
    "FieldCategory",
    "FieldDisplayType",
    "UIComponentRegistry",
    "SchemaRegistry",
    "register_discovered_schemas",
    "create_api_response",
    "discover_config_classes",
    "SchemaExtensionRegistry",
    "SchemaAdapter",
]
