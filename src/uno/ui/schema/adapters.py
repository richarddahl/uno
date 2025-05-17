# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Framework adapters for schema compatibility.

This module provides adapters to convert schema definitions to formats
compatible with various UI frameworks and form libraries.
"""

from __future__ import annotations

from typing import Any, Callable


class SchemaAdapter:
    """Adapter for converting schemas to framework-specific formats."""

    # Registry of adapters
    _adapters: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    @classmethod
    def register_adapter(
        cls, framework: str, adapter_func: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        """Register a new framework adapter.

        Args:
            framework: Framework identifier
            adapter_func: Function that adapts schemas for the framework
        """
        cls._adapters[framework] = adapter_func

    @classmethod
    def adapt_schema(cls, schema: dict[str, Any], framework: str) -> dict[str, Any]:
        """Convert schema to a framework-specific format.

        Args:
            schema: Standard schema
            framework: Target framework identifier

        Returns:
            Framework-specific schema

        Raises:
            ValueError: If no adapter exists for the framework
        """
        if framework in cls._adapters:
            return cls._adapters[framework](schema)

        # Special handling for known frameworks
        if framework == "react-jsonforms":
            return cls.to_react_jsonforms(schema)
        elif framework == "react-jsonschema":
            return cls.to_react_jsonschema_form(schema)
        elif framework == "vue-formvuelate":
            return cls.to_vue_formvuelate(schema)
        elif framework == "angular":
            return cls.to_angular_json_form(schema)
        elif framework in ["lit", "webcomponents", "web-components"]:
            return cls.to_lit_webcomponents(schema)

        # If no adapter found, return original schema
        return schema

    @staticmethod
    def to_react_jsonforms(schema: dict[str, Any]) -> dict[str, Any]:
        """Convert schema to React JSONForms format.

        Args:
            schema: Standard schema from to_json_schema()

        Returns:
            JSONForms compatible schema
        """
        # JSONForms uses the standard JSON Schema format with some additions
        return {
            "schema": schema["schema"],
            "uiSchema": schema["uiSchema"],
        }

    @staticmethod
    def to_react_jsonschema_form(schema: dict[str, Any]) -> dict[str, Any]:
        """Convert schema to react-jsonschema-form format.

        Args:
            schema: Standard schema from to_json_schema()

        Returns:
            react-jsonschema-form compatible schema
        """
        # react-jsonschema-form uses a slightly different UI schema format
        ui_schema = {}
        for field, ui_props in schema["uiSchema"].items():
            ui_schema[field] = {
                k.replace("ui:", ""): v
                for k, v in ui_props.items()
                if k.startswith("ui:")
            }

        return {
            "schema": schema["schema"],
            "uiSchema": ui_schema,
        }

    @staticmethod
    def to_vue_formvuelate(schema: dict[str, Any]) -> dict[str, Any]:
        """Convert schema to FormVueLate format.

        Args:
            schema: Standard schema from to_json_schema()

        Returns:
            FormVueLate compatible schema
        """
        # FormVueLate uses a flatter structure
        fields = []

        for field_name, field_schema in schema["schema"]["properties"].items():
            ui_props = schema["uiSchema"].get(field_name, {})

            field_def = {
                "name": field_name,
                "label": field_schema.get("title", field_name),
                "type": ui_props.get("ui:widget", "text"),
            }

            if "description" in field_schema:
                field_def["description"] = field_schema["description"]

            if "default" in field_schema:
                field_def["value"] = field_schema["default"]

            if (
                "required" in schema["schema"]
                and field_name in schema["schema"]["required"]
            ):
                field_def["required"] = True

            # Add any additional properties
            for k, v in ui_props.items():
                if not k.startswith("ui:"):
                    field_def[k] = v

            fields.append(field_def)

        return {
            "schema": fields,
            "options": {
                "validateAfterLoad": True,
                "validateAfterChanged": True,
            },
        }

    @staticmethod
    def to_angular_json_form(schema: dict[str, Any]) -> dict[str, Any]:
        """Convert schema to Angular JSON Form format.

        Args:
            schema: Standard schema from to_json_schema()

        Returns:
            Angular JSON Form compatible schema
        """
        # Similar to standard JSON Schema but with some Angular-specific additions
        return {
            "schema": schema["schema"],
            "layout": [
                {
                    "type": "section",
                    "items": [
                        {"key": field_name}
                        for field_name in schema["schema"]["properties"].keys()
                        if not field_name.startswith("_")
                    ],
                }
            ],
        }

    @staticmethod
    def to_lit_webcomponents(schema: dict[str, Any]) -> dict[str, Any]:
        """Convert schema to Lit/WebAwesome web components format.

        Args:
            schema: Standard schema from to_json_schema()

        Returns:
            Web Components compatible schema optimized for Lit
        """
        # Create a structure optimized for Lit-based web components
        # that can be used without build steps or transpilation
        fields = []

        for field_name, field_schema in schema["schema"]["properties"].items():
            ui_props = schema["uiSchema"].get(field_name, {})

            # Determine appropriate web component based on field type
            component_type = "text-field"
            if field_schema.get("type") == "boolean":
                component_type = "checkbox-field"
            elif field_schema.get("type") == "number":
                component_type = "number-field"
            elif field_schema.get("type") == "integer":
                component_type = "number-field"
            elif field_schema.get("type") == "array" and "enum" in field_schema.get("items", {}):
                component_type = "select-field"
            elif field_schema.get("type") == "string" and "enum" in field_schema:
                component_type = "select-field"

            # Override component type if specified in UI schema
            if "ui:widget" in ui_props:
                widget_mapping = {
                    "textarea": "textarea-field",
                    "password": "password-field",
                    "email": "email-field",
                    "date": "date-field",
                    "datetime": "datetime-field",
                    "color": "color-field",
                    "file": "file-field",
                    "radio": "radio-group",
                    "select": "select-field",
                    "checkbox": "checkbox-field",
                    "toggle": "switch-field",
                }
                component_type = widget_mapping.get(ui_props["ui:widget"], component_type)

            field_def = {
                "name": field_name,
                "component": component_type,
                "label": field_schema.get("title", field_name),
                "description": field_schema.get("description", ""),
                "required": field_name in schema["schema"].get("required", []),
                "validations": [],
                "properties": {},
            }

            # Add default value if present
            if "default" in field_schema:
                field_def["value"] = field_schema["default"]

            # Add options for enum types
            if "enum" in field_schema:
                field_def["options"] = [
                    {"label": str(item), "value": item} for item in field_schema["enum"]
                ]
            elif field_schema.get("type") == "array" and "enum" in field_schema.get("items", {}):
                field_def["options"] = [
                    {"label": str(item), "value": item}
                    for item in field_schema["items"]["enum"]
                ]

            # Add validations
            if "minimum" in field_schema:
                field_def["validations"].append({"type": "min", "value": field_schema["minimum"]})
            if "maximum" in field_schema:
                field_def["validations"].append({"type": "max", "value": field_schema["maximum"]})
            if "minLength" in field_schema:
                field_def["validations"].append({"type": "minLength", "value": field_schema["minLength"]})
            if "maxLength" in field_schema:
                field_def["validations"].append({"type": "maxLength", "value": field_schema["maxLength"]})
            if "pattern" in field_schema:
                field_def["validations"].append({"type": "pattern", "value": field_schema["pattern"]})

            # Process additional ui properties as web component attributes
            for k, v in ui_props.items():
                if not k.startswith("ui:"):
                    field_def["properties"][k] = v
                elif k == "ui:disabled":
                    field_def["properties"]["disabled"] = v
                elif k == "ui:readonly":
                    field_def["properties"]["readonly"] = v
                elif k == "ui:autofocus":
                    field_def["properties"]["autofocus"] = v

            fields.append(field_def)

        return {
            "schema": schema["schema"],
            "fields": fields,
            "metadata": {
                "framework": "lit",
                "noTranspilation": True,
                "noBuildStep": True
            }
        }
