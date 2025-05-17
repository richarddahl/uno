# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Enhanced schema validation for the Uno configuration system.

This module extends Pydantic's validation capabilities with Uno-specific
features like schema versioning, compatibility checks, and conditional validation.
"""

from __future__ import annotations

import inspect
import json
import re
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Protocol,
    TypeVar,
    cast,
    get_type_hints,
    Literal,
)

from pydantic import BaseModel, Field, create_model, field_validator
from pydantic.fields import FieldInfo
from pydantic_core import PydanticCustomError

from uno.config.base import Config
from uno.config.environment import Environment
from uno.config.errors import ConfigValidationError

T = TypeVar("T", bound=Config)


class SchemaVersion:
    """Schema version for configuration classes."""

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


class FieldMetadata:
    """Extended metadata for configuration fields."""

    def __init__(
        self,
        description: str | None = None,
        example: Any = None,
        deprecated: bool = False,
        required_in: ValidationScope = ValidationScope.ALL,
        format_pattern: str | None = None,
        min_version: SchemaVersion | None = None,
        max_version: SchemaVersion | None = None,
        aliases: list[str] | None = None,
    ) -> None:
        """Initialize field metadata.

        Args:
            description: Human-readable description
            example: Example value
            deprecated: Whether this field is deprecated
            required_in: Which environments require this field
            format_pattern: Regex pattern for string values
            min_version: Minimum schema version this field appeared in
            max_version: Maximum schema version this field exists in
            aliases: Alternative names for this field
        """
        self.description = description
        self.example = example
        self.deprecated = deprecated
        self.required_in = required_in
        self.format_pattern = format_pattern
        self.min_version = min_version
        self.max_version = max_version
        self.aliases = aliases or []


# Extension registry system for UI components and validators
class UIComponentRegistry:
    """Registry for custom UI components and renderers.

    This registry allows extension of the schema system with custom
    UI components for different field types and rendering strategies.
    """

    _components: ClassVar[dict[str, type]] = {}
    _renderers: ClassVar[dict[str, Callable[..., Any]]] = {}
    _validators: ClassVar[dict[str, Callable[..., bool]]] = {}
    _transformers: ClassVar[dict[str, Callable[..., Any]]] = {}

    @classmethod
    def register_component(cls, component_type: str, component_class: type) -> None:
        """Register a custom UI component for a field type.

        Args:
            component_type: Identifier for the component type
            component_class: The component class or factory
        """
        cls._components[component_type] = component_class

    @classmethod
    def register_renderer(
        cls, renderer_id: str, renderer_func: Callable[..., Any]
    ) -> None:
        """Register a custom renderer function.

        Args:
            renderer_id: Identifier for the renderer
            renderer_func: Function that renders a field
        """
        cls._renderers[renderer_id] = renderer_func

    @classmethod
    def register_validator(
        cls, validator_id: str, validator_func: Callable[..., bool]
    ) -> None:
        """Register a custom field validator.

        Args:
            validator_id: Identifier for the validator
            validator_func: Validation function
        """
        cls._validators[validator_id] = validator_func

    @classmethod
    def register_transformer(
        cls, transformer_id: str, transformer_func: Callable[..., Any]
    ) -> None:
        """Register a data transformer.

        Args:
            transformer_id: Identifier for the transformer
            transformer_func: Function that transforms data
        """
        cls._transformers[transformer_id] = transformer_func

    @classmethod
    def get_component(cls, component_type: str) -> type | None:
        """Get a registered component by type.

        Args:
            component_type: Component type identifier

        Returns:
            The component class or None if not found
        """
        return cls._components.get(component_type)

    @classmethod
    def get_renderer(cls, renderer_id: str) -> Callable[..., Any] | None:
        """Get a registered renderer.

        Args:
            renderer_id: Renderer identifier

        Returns:
            The renderer function or None if not found
        """
        return cls._renderers.get(renderer_id)

    @classmethod
    def get_validator(cls, validator_id: str) -> Callable[..., bool] | None:
        """Get a registered validator.

        Args:
            validator_id: Validator identifier

        Returns:
            The validator function or None if not found
        """
        return cls._validators.get(validator_id)

    @classmethod
    def get_transformer(cls, transformer_id: str) -> Callable[..., Any] | None:
        """Get a registered transformer.

        Args:
            transformer_id: Transformer identifier

        Returns:
            The transformer function or None if not found
        """
        return cls._transformers.get(transformer_id)


# Extension mechanism through plugins
class SchemaExtension(Protocol):
    """Protocol for schema extensions.

    Schema extensions can add functionality to the schema system,
    such as custom validation, transformation, or UI rendering.
    """

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
        """Extend a schema with additional metadata or functionality.

        Args:
            schema: The schema to extend

        Returns:
            Extended schema
        """
        ...

    @classmethod
    def extend_field(cls, field_schema: dict[str, Any]) -> dict[str, Any]:
        """Extend a field schema with additional metadata or functionality.

        Args:
            field_schema: The field schema to extend

        Returns:
            Extended field schema
        """
        ...


class SchemaExtensionRegistry:
    """Registry for schema extensions."""

    _extensions: ClassVar[list[type[SchemaExtension]]] = []

    @classmethod
    def register_extension(cls, extension: type[SchemaExtension]) -> None:
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


# Enhance FieldDisplayType with extensibility
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


# Make ConfigField more extensible with custom metadata
def ConfigField(
    default: Any = ...,
    *,
    description: str | None = None,
    example: Any = None,
    deprecated: bool = False,
    required_in: ValidationScope = ValidationScope.ALL,
    format_pattern: str | None = None,
    min_version: SchemaVersion | None = None,
    max_version: SchemaVersion | None = None,
    aliases: list[str] | None = None,
    # UI-specific metadata
    display_name: str | None = None,
    category: FieldCategory = FieldCategory.GENERAL,
    display_type: FieldDisplayType | str | None = None,
    options: list[Any] | None = None,
    help_text: str | None = None,
    placeholder: str | None = None,
    visibility: Literal["always", "advanced", "never"] = "always",
    order: int | None = None,
    depends_on_field: str | None = None,
    depends_on_value: Any = None,
    ui_readonly: bool = False,
    # Extension mechanism
    custom_validators: list[str] | None = None,
    custom_transformers: list[str] | None = None,
    custom_renderers: list[str] | None = None,
    custom_components: dict[str, str] | None = None,
    ui_extensions: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Create a field with enhanced configuration metadata.

    Args:
        default: Default value for the field
        description: Human-readable description
        example: Example value
        deprecated: Whether this field is deprecated
        required_in: Which environments require this field
        format_pattern: Regex pattern for string values
        min_version: Minimum schema version this field appeared in
        max_version: Maximum schema version this field exists in
        aliases: Alternative names for this field
        display_name: User-friendly name to display in UI
        category: Category for grouping in UI
        display_type: Widget type hint for UI
        options: Options for select/radio fields
        help_text: Extended help text for tooltips
        placeholder: Placeholder text for input fields
        visibility: When to show this field in UI
        order: Ordering priority within a category (lower = earlier)
        depends_on_field: Another field this one depends on
        depends_on_value: Required value of depends_on_field to show this field
        ui_readonly: Whether field should be read-only in UI
        custom_validators: List of validator IDs to apply
        custom_transformers: List of transformer IDs to apply
        custom_renderers: List of renderer IDs to use
        custom_components: Custom UI components for different frameworks
        ui_extensions: Additional UI-specific metadata for custom extensions
        **kwargs: Additional field parameters passed to Field

    Returns:
        Field with enhanced metadata
    """
    field_info = Field(
        default,
        description=description,
        json_schema_extra=kwargs.pop("json_schema_extra", {}),
        **kwargs,
    )

    # Add our extended metadata to the field
    field_info.json_schema_extra = field_info.json_schema_extra or {}

    # Core metadata
    field_info.json_schema_extra.update(
        {
            "example": example,
            "deprecated": deprecated,
            "required_in": required_in.value,
            "format_pattern": format_pattern,
            "min_version": str(min_version) if min_version else None,
            "max_version": str(max_version) if max_version else None,
            "aliases": aliases or [],
        }
    )

    # Process display_type to handle custom types
    if display_type is not None:
        if isinstance(display_type, FieldDisplayType):
            display_type_value = display_type.value
        elif isinstance(display_type, str) and FieldDisplayType.is_valid_type(
            display_type
        ):
            display_type_value = display_type
        else:
            # Fallback to text for invalid types
            display_type_value = FieldDisplayType.TEXT.value
    else:
        display_type_value = None

    # UI-specific metadata
    field_info.json_schema_extra.update(
        {
            "ui:display_name": display_name,
            "ui:category": category.value,
            "ui:display_type": display_type_value,
            "ui:options": options,
            "ui:help_text": help_text or description,
            "ui:placeholder": placeholder,
            "ui:visibility": visibility,
            "ui:order": order,
            "ui:depends_on_field": depends_on_field,
            "ui:depends_on_value": depends_on_value,
            "ui:readonly": ui_readonly,
        }
    )

    # Extension metadata
    field_info.json_schema_extra.update(
        {
            "x-validators": custom_validators or [],
            "x-transformers": custom_transformers or [],
            "x-renderers": custom_renderers or [],
            "x-components": custom_components or {},
            "x-ui-extensions": ui_extensions or {},
        }
    )

    return field_info


def validate_with_pattern(value: str, pattern: str | None, field_name: str) -> str:
    """Validate a string value against a regex pattern.

    Args:
        value: String value to validate
        pattern: Regex pattern to check against
        field_name: Name of the field being validated

    Returns:
        The original value if valid

    Raises:
        PydanticCustomError: If validation fails
    """
    if not pattern or not isinstance(value, str):
        return value

    if not re.match(pattern, value):
        raise PydanticCustomError(
            "format_pattern",
            f"Value for {field_name} does not match pattern: {pattern}",
            {"pattern": pattern},
        )

    return value


class EnhancedConfig(Config):
    """Base configuration class with enhanced schema validation.

    This class extends the base Config class with additional validation
    features and schema metadata.
    """

    # Schema version information
    schema_version: ClassVar[SchemaVersion] = SchemaVersion(1, 0, 0)

    # Validation configuration
    model_config = {
        **Config.model_config,
        "validate_default": True,
    }

    # Add fields to track schema version and validation level
    validation_level: ValidationLevel = ValidationLevel.STANDARD

    @field_validator("*", mode="after")
    @classmethod
    def validate_format_patterns(cls, value: Any, info: Any) -> Any:
        """Validate format patterns for string fields.

        Args:
            value: Field value
            info: Validation info

        Returns:
            Validated value
        """
        field_name = info.field_name
        if field_name is None:
            return value

        # Skip validation if level is not high enough
        if hasattr(cls, "validation_level"):
            level = getattr(cls, "validation_level")
            if level == ValidationLevel.NONE or level == ValidationLevel.BASIC:
                return value

        # Get field metadata
        field = cls.model_fields.get(field_name)
        if not field or not field.json_schema_extra:
            return value

        # Validate pattern if present
        pattern = field.json_schema_extra.get("format_pattern")
        if pattern and isinstance(value, str):
            return validate_with_pattern(value, pattern, field_name)

        return value

    @classmethod
    def validate_for_environment(cls, env: Environment) -> list[ConfigValidationError]:
        """Validate configuration for a specific environment.

        This checks if all fields required for the environment are present
        and validates any environment-specific rules.

        Args:
            env: Environment to validate for

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[ConfigValidationError] = []

        # Check all fields for environment requirements
        for field_name, field in cls.model_fields.items():
            if not field.json_schema_extra:
                continue

            required_in = field.json_schema_extra.get("required_in", "all")

            # Check if field is required in this environment
            is_required = required_in == "all" or required_in == env.value

            if is_required and field.is_required():
                errors.append(
                    ConfigValidationError(
                        f"Field '{field_name}' is required in {env.value} environment",
                        config_key=field_name,
                    )
                )

        return errors

    @classmethod
    def get_schema_info(cls) -> dict[str, Any]:
        """Get schema information including version and field metadata.

        Returns:
            Dictionary with schema information
        """
        version = getattr(cls, "schema_version", SchemaVersion(1, 0, 0))

        # Build field info with metadata
        fields: dict[str, dict[str, Any]] = {}

        for field_name, field in cls.model_fields.items():
            field_type = get_type_hints(cls).get(field_name, Any)

            field_info = {
                "type": str(field_type),
                "required": field.is_required(),
                "description": field.description or "",
            }

            # Add extended metadata if available
            if field.json_schema_extra:
                for key, value in field.json_schema_extra.items():
                    if key != "json_schema_extra":
                        field_info[key] = value

            fields[field_name] = field_info

        # Add UI-specific metadata at the class level
        schema_meta = getattr(cls, "schema_meta", {})

        return {
            "name": cls.__name__,
            "version": str(version),
            "fields": fields,
            "description": cls.__doc__ or "",
            "ui:metadata": {
                "title": schema_meta.get("title", cls.__name__),
                "description": schema_meta.get("description", cls.__doc__ or ""),
                "icon": schema_meta.get("icon"),
                "category": schema_meta.get("category", "general"),
                "order": schema_meta.get("order"),
                "tags": schema_meta.get("tags", []),
            },
        }

    @classmethod
    def to_json_schema(cls, ui_framework: str | None = None) -> dict[str, Any]:
        """Convert to JSON Schema format compatible with UI form generators.

        Args:
            ui_framework: Optional UI framework to generate framework-specific schema for
                          (e.g., 'react', 'vue', 'angular', etc.)

        Returns:
            JSON Schema representation with UI extensions
        """
        schema_info = cls.get_schema_info()

        # Create JSON Schema structure
        json_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": schema_info["ui:metadata"]["title"],
            "description": schema_info["ui:metadata"]["description"],
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

        # Add UI Schema for form generation tools
        ui_schema: dict[str, Any] = {}

        # Process each field
        for field_name, field_info in schema_info["fields"].items():
            # Skip internal fields
            if field_name.startswith("_"):
                continue

            # Add to properties
            field_type = field_info["type"]
            property_schema = {
                "title": field_info.get("ui:display_name", field_name),
                "description": field_info.get("description", ""),
                "default": field_info.get("default"),
            }

            # Set JSON Schema type based on Python type
            if "int" in field_type:
                property_schema["type"] = "integer"
            elif "float" in field_type:
                property_schema["type"] = "number"
            elif "bool" in field_type:
                property_schema["type"] = "boolean"
            elif "str" in field_type:
                property_schema["type"] = "string"
                if field_info.get("format_pattern"):
                    property_schema["pattern"] = field_info["format_pattern"]
            elif "list" in field_type or "set" in field_type:
                property_schema["type"] = "array"
            elif "dict" in field_type:
                property_schema["type"] = "object"
            else:
                # Default to string for complex types
                property_schema["type"] = "string"

            # Handle enums
            if "Enum" in field_type or "Literal" in field_type:
                if field_info.get("ui:options"):
                    property_schema["enum"] = field_info["ui:options"]

            # Add field to schema
            json_schema["properties"][field_name] = property_schema

            # Track required fields
            if field_info.get("required", False):
                json_schema["required"].append(field_name)

            # Add UI-specific metadata to ui_schema
            ui_field = {}

            # Set widget type
            if field_info.get("ui:display_type"):
                ui_field["ui:widget"] = field_info["ui:display_type"]

            # Add other UI metadata
            if field_info.get("ui:help_text"):
                ui_field["ui:help"] = field_info["ui:help_text"]

            if field_info.get("ui:placeholder"):
                ui_field["ui:placeholder"] = field_info["ui:placeholder"]

            if field_info.get("ui:readonly"):
                ui_field["ui:readonly"] = True

            if field_info.get("ui:order") is not None:
                ui_field["ui:order"] = field_info["ui:order"]

            if field_info.get("ui:depends_on_field"):
                ui_field["ui:dependencies"] = {
                    field_info["ui:depends_on_field"]: {
                        "oneOf": [
                            {
                                "const": field_info["ui:depends_on_value"],
                                "required": [field_name],
                            }
                        ]
                    }
                }

            # Add extension metadata
            for ext_key in [
                "x-validators",
                "x-transformers",
                "x-renderers",
                "x-components",
                "x-ui-extensions",
            ]:
                if ext_key in field_info and field_info[ext_key]:
                    ui_field[ext_key] = field_info[ext_key]

            # Framework-specific customizations
            if (
                ui_framework
                and "x-components" in field_info
                and ui_framework in field_info["x-components"]
            ):
                ui_field["ui:widget"] = field_info["x-components"][ui_framework]

            # Add to ui_schema if we have any UI metadata
            if ui_field:
                ui_schema[field_name] = ui_field

        # Apply schema extensions
        json_schema = SchemaExtensionRegistry.extend_schema(json_schema)

        # For each property, apply field extensions
        for field_name, field_schema in json_schema["properties"].items():
            json_schema["properties"][field_name] = (
                SchemaExtensionRegistry.extend_field(field_schema)
            )

        return {
            "schema": json_schema,
            "uiSchema": ui_schema,
            "framework": ui_framework,
        }

    @classmethod
    def register_ui_component(
        cls, field_name: str, framework: str, component_name: str
    ) -> None:
        """Register a custom UI component for a field in a specific framework.

        Args:
            field_name: Name of the field
            framework: UI framework (e.g., 'react', 'vue')
            component_name: Name of the component to use
        """
        field = cls.model_fields.get(field_name)
        if not field or not field.json_schema_extra:
            return

        if "x-components" not in field.json_schema_extra:
            field.json_schema_extra["x-components"] = {}

        field.json_schema_extra["x-components"][framework] = component_name

    @classmethod
    def register_field_validator(cls, field_name: str, validator_id: str) -> None:
        """Register a custom validator for a field.

        Args:
            field_name: Name of the field
            validator_id: ID of the validator to register
        """
        field = cls.model_fields.get(field_name)
        if not field or not field.json_schema_extra:
            return

        if "x-validators" not in field.json_schema_extra:
            field.json_schema_extra["x-validators"] = []

        if validator_id not in field.json_schema_extra["x-validators"]:
            field.json_schema_extra["x-validators"].append(validator_id)

    @classmethod
    def register_field_transformer(cls, field_name: str, transformer_id: str) -> None:
        """Register a custom transformer for a field.

        Args:
            field_name: Name of the field
            transformer_id: ID of the transformer to register
        """
        field = cls.model_fields.get(field_name)
        if not field or not field.json_schema_extra:
            return

        if "x-transformers" not in field.json_schema_extra:
            field.json_schema_extra["x-transformers"] = []

        if transformer_id not in field.json_schema_extra["x-transformers"]:
            field.json_schema_extra["x-transformers"].append(transformer_id)

    @classmethod
    def register_field_renderer(cls, field_name: str, renderer_id: str) -> None:
        """Register a custom renderer for a field.

        Args:
            field_name: Name of the field
            renderer_id: ID of the renderer to register
        """
        field = cls.model_fields.get(field_name)
        if not field or not field.json_schema_extra:
            return

        if "x-renderers" not in field.json_schema_extra:
            field.json_schema_extra["x-renderers"] = []

        if renderer_id not in field.json_schema_extra["x-renderers"]:
            field.json_schema_extra["x-renderers"].append(renderer_id)


# Enhanced ConfigSchemaRegistry with more capabilities
class ConfigSchemaRegistry:
    """Registry for configuration schemas.

    This class provides a centralized registry for configuration schemas,
    allowing UI components to discover and access available configurations.
    """

    _schemas: ClassVar[dict[str, type[Config]]] = {}
    _schemas_by_category: ClassVar[dict[str, list[str]]] = {}
    _metadata_cache: ClassVar[dict[str, dict[str, Any]]] = {}

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

        # Index by category
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
            return config_class.to_json_schema(ui_framework=ui_framework)

        # Fallback for regular Config classes
        return create_api_response(config_class, include_json_schema=True)[
            "json_schema"
        ]


# Adaptation layer for framework-specific schema generation
class SchemaAdapter:
    """Adapter for converting schemas to framework-specific formats."""

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
    def to_vue_formvuelate(schema: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert schema to FormVueLate format.

        Args:
            schema: Standard schema from to_json_schema()

        Returns:
            FormVueLate compatible schema array
        """
        # FormVueLate uses a flatter structure
        result = []

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

            result.append(field_def)

        return result

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


# Add this helper function to create API responses with adapters
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
            (e.g., 'react-jsonforms', 'react-jsonschema', 'vue-formvuelate', 'angular')

    Returns:
        Complete schema information for API responses

    Raises:
        ValueError: If schema ID is not found in registry
    """
    # Resolve schema ID to class if needed
    if isinstance(config_class, str):
        resolved_class = ConfigSchemaRegistry.get_schema(config_class)
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
            adapted_schema = None
            if ui_framework == "react-jsonforms":
                adapted_schema = SchemaAdapter.to_react_jsonforms(json_schema)
            elif ui_framework == "react-jsonschema":
                adapted_schema = SchemaAdapter.to_react_jsonschema_form(json_schema)
            elif ui_framework == "vue-formvuelate":
                adapted_schema = SchemaAdapter.to_vue_formvuelate(json_schema)
            elif ui_framework == "angular":
                adapted_schema = SchemaAdapter.to_angular_json_form(json_schema)

            if adapted_schema:
                response["json_schema"] = adapted_schema
                response["ui_framework"] = ui_framework
            else:
                response["json_schema"] = json_schema
        else:
            response["json_schema"] = json_schema

    return response


async def register_discovered_schemas(module: Any) -> list[str]:
    """Discover and register all configuration classes in a module.

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
        ConfigSchemaRegistry.register(config_class)
        registered_ids.append(schema_id)

    return registered_ids
