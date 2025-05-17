# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Schema registry for UI schema management.

This module provides a registry system for schemas that can be
used to generate user interfaces dynamically.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypeVar, get_type_hints

from uno.config.base import Config
from uno.ui.schema.core import discover_config_classes
from uno.ui.schema.adapters import SchemaAdapter


T = TypeVar("T", bound=Config)


class SchemaRegistry:
    """Registry for schemas that can be used to generate UIs.

    This class provides a centralized registry for schemas,
    allowing UI components to discover and access available schemas.
    """

    _schemas: dict[str, type[Config]] = {}
    _schemas_by_category: dict[str, list[str]] = {}
    _metadata_cache: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(cls, config_class: type[Config]) -> None:
        """Register a configuration class.

        Args:
            config_class: The configuration class to register
        """
        module_name = config_class.__module__
        class_name = config_class.__name__
        schema_id = f"{module_name}.{class_name}"
        cls._schemas[schema_id] = config_class

        # Index by category if available
        if hasattr(config_class, "get_schema_info"):
            schema_info = config_class.get_schema_info()
            category = schema_info["ui:metadata"]["category"]
            if category not in cls._schemas_by_category:
                cls._schemas_by_category[category] = []
            if schema_id not in cls._schemas_by_category[category]:
                cls._schemas_by_category[category].append(schema_id)

            # Cache metadata
            cls._metadata_cache[schema_id] = schema_info

    @classmethod
    def get_schema(cls, schema_id: str) -> type[Config] | None:
        """Get a registered schema by ID.

        Args:
            schema_id: Schema identifier (module.class)

        Returns:
            Configuration class or None if not found
        """
        return cls._schemas.get(schema_id)

    @classmethod
    def list_schemas(
        cls, category: str | None = None, tag: str | None = None
    ) -> list[dict[str, Any]]:
        """List all registered schemas with basic metadata.

        Args:
            category: Optional category to filter by
            tag: Optional tag to filter by

        Returns:
            List of schema metadata dictionaries
        """
        result = []

        # If category specified, only list schemas in that category
        schema_ids = []
        if category:
            schema_ids = cls._schemas_by_category.get(category, [])
        else:
            schema_ids = list(cls._schemas.keys())

        for schema_id in schema_ids:
            config_class = cls._schemas[schema_id]

            # Get schema info, using cache if available
            if schema_id in cls._metadata_cache:
                schema_info = cls._metadata_cache[schema_id]
            elif hasattr(config_class, "get_schema_info"):
                schema_info = config_class.get_schema_info()
                cls._metadata_cache[schema_id] = schema_info
            else:
                # Fallback for regular Config classes
                schema_info = {
                    "name": config_class.__name__,
                    "description": config_class.__doc__ or "",
                    "version": "1.0.0",
                    "ui:metadata": {
                        "title": config_class.__name__,
                        "description": config_class.__doc__ or "",
                        "category": "general",
                        "tags": [],
                    },
                }

            # Filter by tag if specified
            if tag and tag not in schema_info["ui:metadata"]["tags"]:
                continue

            result.append(
                {
                    "id": schema_id,
                    "name": schema_info["name"],
                    "title": schema_info["ui:metadata"]["title"],
                    "description": schema_info["description"],
                    "version": schema_info["version"],
                    "category": schema_info["ui:metadata"]["category"],
                    "tags": schema_info["ui:metadata"]["tags"],
                }
            )

        return result

    @classmethod
    def list_categories(cls) -> list[str]:
        """List all available categories.

        Returns:
            List of category names
        """
        return list(cls._schemas_by_category.keys())

    @classmethod
    def search_schemas(cls, query: str) -> list[dict[str, Any]]:
        """Search for schemas matching a query string.

        Args:
            query: Search query

        Returns:
            List of matching schema metadata
        """
        result = []
        query = query.lower()

        for schema_id, config_class in cls._schemas.items():
            # Get schema info
            if schema_id in cls._metadata_cache:
                schema_info = cls._metadata_cache[schema_id]
            elif hasattr(config_class, "get_schema_info"):
                schema_info = config_class.get_schema_info()
            else:
                continue

            # Check for matches in name, title, description
            name = schema_info["name"].lower()
            title = schema_info["ui:metadata"]["title"].lower()
            description = schema_info["description"].lower()

            if query in name or query in title or query in description:
                result.append(
                    {
                        "id": schema_id,
                        "name": schema_info["name"],
                        "title": schema_info["ui:metadata"]["title"],
                        "description": schema_info["description"],
                        "version": schema_info["version"],
                        "category": schema_info["ui:metadata"]["category"],
                        "tags": schema_info["ui:metadata"]["tags"],
                    }
                )

        return result

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the metadata cache."""
        cls._metadata_cache.clear()

    @classmethod
    def get_schema_ui(
        cls, schema_id: str, ui_framework: str | None = None
    ) -> dict[str, Any]:
        """Get UI schema for a specific schema ID.

        Args:
            schema_id: Schema identifier
            ui_framework: Optional UI framework to generate schema for

        Returns:
            UI schema data

        Raises:
            ValueError: If schema ID is not found
        """
        config_class = cls.get_schema(schema_id)
        if not config_class:
            raise ValueError(f"Schema ID not found: {schema_id}")

        if hasattr(config_class, "to_json_schema"):
            schema = config_class.to_json_schema(ui_framework=None)

            # Apply framework-specific adaptations if needed
            if ui_framework:
                return SchemaAdapter.adapt_schema(schema, ui_framework)
            return schema

        # Fallback for regular Config classes
        return create_api_response(config_class, include_json_schema=True)[
            "json_schema"
        ]


async def register_discovered_schemas(module: Any) -> list[str]:
    """Discover and register all schema classes in a module.

    Args:
        module: Module or package to search in

    Returns:
        List of registered schema IDs
    """
    config_classes = discover_config_classes(module)
    registered_ids = []

    for config_class in config_classes:
        module_name = config_class.__module__
        class_name = config_class.__name__
        schema_id = f"{module_name}.{class_name}"
        SchemaRegistry.register(config_class)
        registered_ids.append(schema_id)

    return registered_ids


def create_api_response(
    config_class: type[Config] | str,
    include_json_schema: bool = True,
    include_ui_schema: bool = True,
    ui_framework: str | None = None,
) -> dict[str, Any]:
    """Create a complete API response with schema information.

    This function is useful for creating REST API responses that
    include all necessary schema information for UI integration.

    Args:
        config_class: Configuration class or schema ID
        include_json_schema: Whether to include JSON Schema
        include_ui_schema: Whether to include UI Schema
        ui_framework: Optional UI framework to adapt schema for

    Returns:
        Complete schema information for API responses

    Raises:
        ValueError: If schema ID is not found in registry
    """
    # Resolve schema ID to class if needed
    if isinstance(config_class, str):
        resolved_class = SchemaRegistry.get_schema(config_class)
        if not resolved_class:
            raise ValueError(f"Schema ID not found in registry: {config_class}")
        config_class = resolved_class

    # Get basic schema info
    if hasattr(config_class, "get_schema_info"):
        schema_info = config_class.get_schema_info()
    else:
        # Fallback for regular Config classes
        schema_info = {
            "name": config_class.__name__,
            "version": "1.0.0",
            "description": config_class.__doc__ or "",
            "fields": {
                name: {
                    "type": str(get_type_hints(config_class).get(name, Any)),
                    "required": field.is_required(),
                    "description": field.description or "",
                }
                for name, field in config_class.model_fields.items()
                if not name.startswith("_")
            },
            "ui:metadata": {
                "title": config_class.__name__,
                "description": config_class.__doc__ or "",
                "category": "general",
                "tags": [],
            },
        }

    # Build response
    response = {
        "schema_info": schema_info,
    }

    # Add JSON Schema if requested
    if include_json_schema and hasattr(config_class, "to_json_schema"):
        # Get base schema
        json_schema = config_class.to_json_schema(ui_framework=None)

        # Apply framework-specific adaptations if needed
        if ui_framework:
            response["json_schema"] = SchemaAdapter.adapt_schema(
                json_schema, ui_framework
            )
            response["ui_framework"] = ui_framework
        else:
            response["json_schema"] = json_schema

    return response
