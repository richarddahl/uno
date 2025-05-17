# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Config schema extractor for the Uno documentation system.

This module provides an extractor for config classes.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, get_type_hints

from uno.docs.schema import DocumentationType, ExampleInfo, FieldInfo, SchemaInfo


class ConfigExtractor:
    """Extractor for Config classes."""

    async def can_extract(self, item: Any) -> bool:
        """
        Determine if this extractor can handle a given item.

        Args:
            item: The item to check

        Returns:
            True if this extractor can handle the item
        """
        # Check if it's a class
        if not inspect.isclass(item):
            return False

        # Check if it's a Config class or subclass
        try:
            from uno.config import Config

            return issubclass(item, Config) and item is not Config
        except (ImportError, TypeError):
            return False

    async def extract_schema(self, item: Any) -> SchemaInfo:
        """
        Extract documentation schema from a Config class.

        Args:
            item: The Config class to extract schema from

        Returns:
            Documentation schema for the Config class
        """
        # Basic class info
        schema = SchemaInfo(
            name=item.__name__,
            module=item.__module__,
            description=self._extract_docstring(item),
            type=DocumentationType.CONFIG,
        )

        # Get base classes
        for base in item.__bases__:
            # Skip object and skip base Config class itself
            try:
                from uno.config import Config

                if (
                    base is not object
                    and base is not Config
                    and issubclass(base, Config)
                ):
                    schema.base_classes.append(base.__name__)
            except (ImportError, TypeError):
                continue

        # Get fields
        try:
            model_fields = getattr(item, "model_fields", {})
            for field_name, field_info in model_fields.items():
                if not field_name.startswith("_"):  # Skip private fields
                    field_info_obj = self._extract_field_info(
                        item, field_name, field_info
                    )
                    schema.fields.append(field_info_obj)
        except Exception:
            # If we can't extract fields, just continue with what we have
            pass

        # Generate example
        example = self._generate_example(item)
        if example:
            schema.examples.append(example)

        return schema

    def _extract_docstring(self, obj: Any) -> str:
        """Extract a clean description from an object's docstring."""
        if not obj.__doc__:
            return ""

        # Parse the docstring to extract just the description
        doc = obj.__doc__.strip()

        # Handle multi-line docstrings
        lines = [line.strip() for line in doc.split("\n")]

        # Remove empty lines at the beginning
        while lines and not lines[0]:
            lines.pop(0)

        # Extract the description (text before any @param, Args:, etc.)
        description_lines = []
        for line in lines:
            if line.startswith(("@", "Args:", "Returns:", "Raises:")):
                break
            description_lines.append(line)

        return " ".join(description_lines).strip()

    def _extract_field_info(
        self, config_class: type, field_name: str, field_info: Any
    ) -> FieldInfo:
        """Extract documentation info for a specific configuration field."""
        # Default values for field info
        type_name = "Any"
        type_hint = "Any"
        default_value = None
        description = ""
        is_required = False

        # Try to get more specific information if available
        try:
            # Get type information
            annotations = get_type_hints(config_class)
            if field_name in annotations:
                type_hint_obj = annotations[field_name]
                type_name = getattr(type_hint_obj, "__name__", str(type_hint_obj))
                type_hint = str(type_hint_obj)

            # Get default value
            if hasattr(field_info, "default") and field_info.default is not ...:
                if isinstance(field_info.default, str):
                    default_value = f'"{field_info.default}"'
                else:
                    default_value = str(field_info.default)

            # Get description
            if hasattr(field_info, "description") and field_info.description:
                description = field_info.description

            # Check if required
            if hasattr(field_info, "is_required"):
                is_required = bool(field_info.is_required())
        except Exception:
            # If we can't extract more specific info, just use the defaults
            pass

        # Check if it's a secure field
        is_secure = False
        secure_handling = None

        try:
            # Try to get json_schema_extra which might contain secure field info
            json_schema = getattr(field_info, "json_schema_extra", {}) or {}
            if json_schema.get("secure", False):
                is_secure = True
                handling_value = json_schema.get("handling", "mask")
                secure_handling = str(handling_value)
        except Exception:
            pass

        # Return the field info
        return FieldInfo(
            name=field_name,
            type_name=type_name,
            type_hint=type_hint,
            default_value=default_value,
            description=description,
            is_required=is_required,
            is_secure=is_secure,
            secure_handling=secure_handling,
        )

    def _generate_example(self, config_class: type) -> ExampleInfo | None:
        """Generate an example for using the config class."""
        class_name = config_class.__name__
        module_name = config_class.__module__

        # Create a basic example - only if we can get some fields
        try:
            model_fields = getattr(config_class, "model_fields", {})
            if not model_fields:
                return None

            example_lines = [
                f"from {module_name} import {class_name}",
                f"from uno.config import load_settings, Environment",
                "",
                f"# Load settings for development environment",
                f"settings = await load_settings({class_name}, env=Environment.DEVELOPMENT)",
                "",
                f"# Access configuration settings",
            ]

            # Add examples for accessing fields
            field_examples = []

            for i, field_name in enumerate(model_fields.keys(), 1):
                if field_name.startswith("_"):
                    continue

                # Skip after a few examples to keep it readable
                if i > 3:
                    break

                field_examples.append(f"{field_name} = settings.{field_name}")

            # Handle the case with no fields
            if not field_examples:
                field_examples.append("# No fields found in this configuration class")

            # Combine the examples
            example_lines.extend(field_examples)

            return ExampleInfo(
                title="Basic Usage",
                code="\n".join(example_lines),
                language="python",
            )
        except Exception:
            # If we can't generate an example, return None
            return None
