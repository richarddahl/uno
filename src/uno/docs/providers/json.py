# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
JSON documentation provider for the Uno framework.

This module generates JSON documentation that can be served via a REST API
for runtime documentation of components.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from uno.docs.schema import DocumentableItem, FieldInfo, SchemaInfo


class JsonProvider:
    """Provider that generates JSON documentation for API use."""

    async def generate(
        self,
        items: list[DocumentableItem],
        output_path: str | None = None,
        **options: Any,
    ) -> str:
        """
        Generate JSON documentation for the given items.

        Args:
            items: List of items to document
            output_path: Optional path to write documentation to
            **options: Additional options:
                - pretty: Whether to pretty-print the JSON (default: True)
                - include_examples: Whether to include examples (default: True)
                - include_fields: Whether to include fields (default: True)
                - root_key: Root key for the JSON output (default: "items")

        Returns:
            Generated JSON documentation as a string
        """
        # Extract options
        pretty = options.get("pretty", True)
        include_examples = options.get("include_examples", True)
        include_fields = options.get("include_fields", True)
        root_key = options.get("root_key", "items")

        # Create the documentation data
        docs_data: dict[str, Any] = {
            root_key: [],
            "metadata": {
                "count": len(items),
                "types": {},
                "generated_at": options.get("timestamp", None),
            },
        }

        # Maintain a type count
        type_counts: dict[str, int] = {}

        # Process all items
        for item in items:
            # Create the item documentation
            item_doc = await self.generate_for_item(
                item, include_examples=include_examples, include_fields=include_fields
            )

            # Add to the documents list
            docs_data[root_key].append(item_doc)

            # Update type counts
            item_type = item.schema.type.value
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

        # Add type counts to metadata
        docs_data["metadata"]["types"] = type_counts

        # Serialize to JSON
        if pretty:
            json_str = json.dumps(docs_data, indent=2)
        else:
            json_str = json.dumps(docs_data)

        # Write to output path if specified
        if output_path:
            output_path = Path(output_path)
            os.makedirs(output_path.parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)

        return json_str

    async def generate_for_item(
        self, item: DocumentableItem, **options: Any
    ) -> dict[str, Any]:
        """
        Generate JSON documentation for a single item.

        Args:
            item: The item to document
            **options: Additional options:
                - include_examples: Whether to include examples
                - include_fields: Whether to include fields

        Returns:
            Generated JSON documentation for the item as a dictionary
        """
        schema = item.schema
        include_examples = options.get("include_examples", True)
        include_fields = options.get("include_fields", True)

        # Create the base item documentation
        item_doc: dict[str, Any] = {
            "name": schema.name,
            "module": schema.module,
            "type": schema.type.value,
            "description": schema.description,
        }

        # Add base classes if any
        if schema.base_classes:
            item_doc["base_classes"] = schema.base_classes

        # Add extra info if any
        if schema.extra_info:
            item_doc["extra_info"] = schema.extra_info

        # Add fields if requested
        if include_fields and schema.fields:
            item_doc["fields"] = [self._field_to_dict(field) for field in schema.fields]

        # Add examples if requested
        if include_examples and schema.examples:
            item_doc["examples"] = [
                {
                    "title": example.title,
                    "language": example.language,
                    "code": example.code,
                    "description": example.description,
                }
                for example in schema.examples
            ]

        return item_doc

    def _field_to_dict(self, field: FieldInfo) -> dict[str, Any]:
        """Convert a FieldInfo object to a dictionary for JSON serialization."""
        field_dict = {
            "name": field.name,
            "type": field.type_name,
            "type_hint": field.type_hint,
            "description": field.description,
            "required": field.is_required,
        }

        if field.default_value:
            field_dict["default_value"] = field.default_value

        if field.is_secure:
            field_dict["is_secure"] = True
            if field.secure_handling:
                field_dict["secure_handling"] = field.secure_handling

        if field.validators:
            field_dict["validators"] = field.validators

        if field.extra_info:
            field_dict["extra_info"] = field.extra_info

        return field_dict

    async def lookup_item(
        self,
        items: list[DocumentableItem],
        name: str | None = None,
        module: str | None = None,
        item_type: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Look up a specific item by name, module, and/or type.

        This is useful for serving documentation via a REST API where
        clients want to query for specific items.

        Args:
            items: List of items to search
            name: Optional item name to match
            module: Optional module name to match
            item_type: Optional item type to match

        Returns:
            The matched item's documentation or None if not found
        """
        for item in items:
            schema = item.schema

            # Check if the item matches all provided criteria
            name_match = name is None or schema.name == name
            module_match = module is None or schema.module == module
            type_match = item_type is None or schema.type.value == item_type

            if name_match and module_match and type_match:
                return await self.generate_for_item(item)

        return None

    async def query_items(
        self,
        items: list[DocumentableItem],
        name_pattern: str | None = None,
        module_pattern: str | None = None,
        item_type: str | None = None,
        has_field: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query for items matching certain criteria.

        This is useful for serving documentation via a REST API where
        clients want to search for items.

        Args:
            items: List of items to search
            name_pattern: Optional pattern to match against item names
            module_pattern: Optional pattern to match against module names
            item_type: Optional item type to match
            has_field: Optional field name that must be present

        Returns:
            List of matching items' documentation
        """
        import re

        matches = []

        # Compile patterns if provided
        name_regex = re.compile(name_pattern) if name_pattern else None
        module_regex = re.compile(module_pattern) if module_pattern else None

        for item in items:
            schema = item.schema

            # Check if the item matches all provided criteria
            name_match = (
                name_regex is None or name_regex.search(schema.name) is not None
            )

            module_match = (
                module_regex is None or module_regex.search(schema.module) is not None
            )

            type_match = item_type is None or schema.type.value == item_type

            field_match = has_field is None or any(
                field.name == has_field for field in schema.fields
            )

            if name_match and module_match and type_match and field_match:
                item_doc = await self.generate_for_item(item)
                matches.append(item_doc)

        return matches
