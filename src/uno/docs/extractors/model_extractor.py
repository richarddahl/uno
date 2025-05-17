# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Model extractor for documenting Pydantic models, dataclasses, and other data structures.

This extractor discovers and documents data models, extracting field information,
validations, and relationships between models.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from enum import Enum
from typing import Any, get_type_hints

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo as PydanticFieldInfo

from uno.docs.protocols import SchemaExtractorProtocol
from uno.docs.schema import DocumentationType, ExampleInfo, FieldInfo, SchemaInfo


class ModelExtractor:
    """
    Extractor for data model classes to generate schema documentation.

    This extractor works with Pydantic models, dataclasses, and other structured
    data types to document their fields, validators, and relationships.
    """

    async def can_extract(self, item: Any) -> bool:
        """
        Determine if this extractor can handle a given item.

        Args:
            item: The item to check

        Returns:
            True if this item is a supported data model type
        """
        # Check if it's a class
        if not inspect.isclass(item):
            return False

        # Check if it's a Pydantic model
        if issubclass(item, BaseModel):
            return True

        # Check if it's a dataclass
        if dataclasses.is_dataclass(item):
            return True

        # We could add more model types here (SQLAlchemy, etc.)

        return False

    async def extract_schema(self, item: Any) -> SchemaInfo:
        """
        Extract documentation schema from a data model class.

        Args:
            item: The model class to extract schema from

        Returns:
            Documentation schema for the model
        """
        # Get basic class info
        name = item.__name__
        module = item.__module__
        description = inspect.getdoc(item) or f"{name} data model"

        # Extract base classes
        base_classes = []
        for base in item.__bases__:
            if base is not object and base is not BaseModel:
                base_classes.append(f"{base.__module__}.{base.__name__}")

        # Extract fields based on the model type
        if issubclass(item, BaseModel):
            fields = await self._extract_pydantic_fields(item)
        elif dataclasses.is_dataclass(item):
            fields = await self._extract_dataclass_fields(item)
        else:
            fields = []

        # Create examples
        examples = await self._create_examples(item, fields)

        # Create schema info
        schema = SchemaInfo(
            name=name,
            module=module,
            description=description,
            type=DocumentationType.MODEL,
            fields=fields,
            base_classes=base_classes,
            examples=examples,
        )

        return schema

    async def _extract_pydantic_fields(
        self, model_class: type[BaseModel]
    ) -> list[FieldInfo]:
        """Extract field information from a Pydantic model."""
        fields = []

        # Get model schema (works in Pydantic v2)
        try:
            model_schema = model_class.model_json_schema()
        except AttributeError:
            # Fallback for older Pydantic versions
            model_schema = getattr(model_class, "schema", lambda: {})()

        properties = model_schema.get("properties", {})
        required_fields = model_schema.get("required", [])

        # Get type hints
        type_hints = get_type_hints(model_class)

        # Process each field
        for name, field_info in model_class.model_fields.items():
            # Skip private fields
            if name.startswith("_"):
                continue

            # Get field type
            field_type = type_hints.get(name, Any)
            type_name = self._get_type_name(field_type)

            # Get field properties
            field_props = properties.get(name, {})
            description = field_props.get("description", "") or getattr(
                field_info, "description", ""
            )

            # Determine if field is required
            is_required = name in required_fields

            # Get default value
            default_value = None
            if (
                field_info.default is not inspect.Parameter.empty
                and field_info.default is not None
            ):
                default_value = str(field_info.default)
            elif field_info.default_factory is not None:
                default_value = "<factory>"

            # Extract validators from field
            validators = []

            # Pydantic constraints as validators
            for constraint in [
                "min_length",
                "max_length",
                "pattern",
                "minimum",
                "maximum",
                "gt",
                "ge",
                "lt",
                "le",
                "multiple_of",
            ]:
                if constraint in field_props:
                    validators.append(f"{constraint}={field_props[constraint]}")

            # Create field info
            field = FieldInfo(
                name=name,
                type_name=type_name,
                type_hint=str(field_type),
                default_value=default_value,
                description=description,
                is_required=is_required,
                validators=validators,
                extra_info={
                    "json_schema": field_props,
                },
            )

            fields.append(field)

        return fields

    async def _extract_dataclass_fields(self, dataclass_type: type) -> list[FieldInfo]:
        """Extract field information from a dataclass."""
        fields = []

        # Get dataclass fields
        dc_fields = dataclasses.fields(dataclass_type)

        # Get type hints
        type_hints = get_type_hints(dataclass_type)

        # Process each field
        for field in dc_fields:
            # Get field type
            field_type = type_hints.get(field.name, Any)
            type_name = self._get_type_name(field_type)

            # Get field description from docstring (not built into dataclasses)
            # Try to get it from class variables or docstring
            description = ""

            # Get default value
            default_value = None
            if field.default is not dataclasses.MISSING:
                default_value = str(field.default)
            elif field.default_factory is not dataclasses.MISSING:
                default_value = "<factory>"

            # Create field info
            field_info = FieldInfo(
                name=field.name,
                type_name=type_name,
                type_hint=str(field_type),
                default_value=default_value,
                description=description,
                is_required=field.default is dataclasses.MISSING
                and field.default_factory is dataclasses.MISSING,
            )

            fields.append(field_info)

        return fields

    def _get_type_name(self, type_hint: Any) -> str:
        """Get a simplified type name for a type hint."""
        # Handle optional type
        origin = getattr(type_hint, "__origin__", None)
        args = getattr(type_hint, "__args__", [])

        # Union type (Optional is Union[T, None])
        if origin is not None and origin.__name__ in ("Union", "_Union"):
            # If second type is NoneType, we have Optional
            if args and args[-1] is type(None):
                return f"{self._get_type_name(args[0])} | None"
            else:
                return " | ".join(self._get_type_name(arg) for arg in args)

        # List, Dict, etc.
        elif origin is not None:
            if origin is list:
                return f"list[{self._get_type_name(args[0])}]"
            elif origin is dict:
                return f"dict[{self._get_type_name(args[0])}, {self._get_type_name(args[1])}]"
            elif origin is set:
                return f"set[{self._get_type_name(args[0])}]"
            else:
                return origin.__name__

        # Enum
        elif inspect.isclass(type_hint) and issubclass(type_hint, Enum):
            return f"Enum({', '.join(repr(e.name) for e in type_hint)})"

        # Standard types
        elif hasattr(type_hint, "__name__"):
            return type_hint.__name__

        # Fallback
        return str(type_hint).replace("typing.", "")

    async def _create_examples(
        self, model_class: type, fields: list[FieldInfo]
    ) -> list[ExampleInfo]:
        """Create example usage for model."""
        examples = []

        # Try to create an example instance
        if issubclass(model_class, BaseModel):
            example = await self._create_pydantic_example(model_class, fields)
        elif dataclasses.is_dataclass(model_class):
            example = await self._create_dataclass_example(model_class, fields)
        else:
            return examples  # No examples if unknown model type

        # Basic instance example
        instance_example = ExampleInfo(
            title="Model instance",
            code=example,
            language="python",
            description=f"Example of creating a {model_class.__name__} instance",
        )
        examples.append(instance_example)

        # JSON serialization example (if available)
        if issubclass(model_class, BaseModel):
            json_example = ExampleInfo(
                title="JSON serialization",
                code=f"""import json

# Create model instance
{example}

# Convert to JSON
json_data = model.model_dump_json(indent=2)
print(json_data)

# Parse from JSON
parsed_model = {model_class.__name__}.model_validate_json(json_data)
""",
                language="python",
                description=f"Example of JSON serialization with {model_class.__name__}",
            )
            examples.append(json_example)

        return examples

    async def _create_pydantic_example(
        self, model_class: type[BaseModel], fields: list[FieldInfo]
    ) -> str:
        """Create an example for a Pydantic model."""
        arg_strings = []

        for field in fields:
            # Skip fields with default values to keep the example concise
            if not field.is_required:
                continue

            # Generate a sample value based on type
            sample_value = self._generate_sample_value(field.type_name)
            arg_strings.append(f"{field.name}={sample_value}")

        # Create the example code
        args_str = ", ".join(arg_strings)
        return f"""from {model_class.__module__} import {model_class.__name__}

# Create a model instance
model = {model_class.__name__}({args_str})
"""

    async def _create_dataclass_example(
        self, dataclass_type: type, fields: list[FieldInfo]
    ) -> str:
        """Create an example for a dataclass."""
        arg_strings = []

        for field in fields:
            # Skip fields with default values to keep the example concise
            if not field.is_required:
                continue

            # Generate a sample value based on type
            sample_value = self._generate_sample_value(field.type_name)
            arg_strings.append(f"{field.name}={sample_value}")

        # Create the example code
        args_str = ", ".join(arg_strings)
        return f"""from {dataclass_type.__module__} import {dataclass_type.__name__}

# Create a dataclass instance
instance = {dataclass_type.__name__}({args_str})
"""

    def _generate_sample_value(self, type_name: str) -> str:
        """Generate a sample value string for a given type."""
        if type_name == "str":
            return '"example"'
        elif type_name == "int":
            return "42"
        elif type_name == "float":
            return "3.14"
        elif type_name == "bool":
            return "True"
        elif type_name.startswith("list"):
            return "[]"
        elif type_name.startswith("dict"):
            return "{}"
        elif type_name.startswith("set"):
            return "set()"
        elif type_name.endswith(" | None"):
            base_type = type_name.split(" | ")[0]
            return self._generate_sample_value(base_type)
        elif type_name.startswith("Enum"):
            # Try to extract first enum value
            try:
                first_value = type_name.split("(")[1].split(",")[0].strip("'\"")
                return f"{type_name.split('(')[0]}.{first_value}"
            except (IndexError, ValueError):
                return "..."
        else:
            # For custom or complex types, use a placeholder
            return "..."
