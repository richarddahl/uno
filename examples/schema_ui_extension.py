"""Example demonstrating the extensible schema-driven UI system.

This example shows how to create, extend, and use schemas for UI generation,
including custom components, validators, and framework-specific adaptations.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from uno.config import (
    ConfigField,
    ConfigSchemaRegistry,
    EnhancedConfig,
    FieldCategory,
    FieldDisplayType,
    SchemaVersion,
    ValidationScope,
    UIComponentRegistry,
    SchemaExtensionRegistry,
)


# Define a custom schema extension
class MetricsExtension:
    """Example schema extension that adds metrics tracking capabilities."""

    @classmethod
    def initialize(cls) -> None:
        """Initialize the extension."""
        print("Initializing MetricsExtension...")

    @classmethod
    def get_name(cls) -> str:
        """Get the extension name."""
        return "metrics"

    @classmethod
    def extend_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        """Extend a schema with metrics capabilities.

        Args:
            schema: The schema to extend

        Returns:
            Extended schema
        """
        # Add metrics configuration to the schema
        schema["x-metrics"] = {
            "collect": True,
            "track_changes": True,
            "reporting_interval": 3600,
        }
        return schema

    @classmethod
    def extend_field(cls, field_schema: dict[str, Any]) -> dict[str, Any]:
        """Extend a field schema with metrics capabilities.

        Args:
            field_schema: The field schema to extend

        Returns:
            Extended field schema
        """
        # Add metrics configuration to the field
        field_schema["x-field-metrics"] = {
            "track_changes": True,
            "collect_history": True,
        }
        return field_schema


# Register a custom UI component for React
def register_custom_react_component() -> None:
    """Register a custom React component."""
    UIComponentRegistry.register_component(
        "color-picker-with-preview",
        {
            "component": "ColorPickerWithPreview",
            "props": {
                "showAlpha": True,
                "previewSize": "medium",
            },
        },
    )


# Register a custom validator
def register_custom_validator() -> None:
    """Register a custom validator function."""

    def validate_url(value: str) -> bool:
        """Validate a URL."""
        if not value:
            return True
        return value.startswith(("http://", "https://"))

    UIComponentRegistry.register_validator("url", validate_url)


# Sample application configuration
class ColorScheme(str, Enum):
    """Color scheme options."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    CUSTOM = "custom"


class AppearanceConfig(EnhancedConfig):
    """Application appearance configuration with rich UI metadata."""

    # Class-level schema metadata for UI
    schema_meta = {
        "title": "Appearance Settings",
        "description": "Configure how the application looks and feels",
        "icon": "palette",
        "category": "user_interface",
        "tags": ["ui", "theme", "appearance"],
    }

    # Schema version
    schema_version = SchemaVersion(1, 1, 0)

    # Theme settings
    color_scheme: ColorScheme = ConfigField(
        default=ColorScheme.SYSTEM,
        description="Application color scheme",
        display_name="Color Scheme",
        display_type=FieldDisplayType.RADIO,
        options=["light", "dark", "system", "custom"],
        category=FieldCategory.GENERAL,
        order=1,
        # Extension example - add a custom React component
        custom_components={"react": "radio-with-preview"},
    )

    # Custom theme colors - only visible when color_scheme is CUSTOM
    primary_color: str = ConfigField(
        default="#0066cc",
        description="Primary accent color",
        display_name="Primary Color",
        display_type=FieldDisplayType.COLOR,
        category=FieldCategory.GENERAL,
        order=2,
        depends_on_field="color_scheme",
        depends_on_value="custom",
        # Extension example - use our custom component
        custom_components={"react": "color-picker-with-preview"},
    )

    secondary_color: str = ConfigField(
        default="#6610f2",
        description="Secondary accent color",
        display_name="Secondary Color",
        display_type=FieldDisplayType.COLOR,
        category=FieldCategory.GENERAL,
        order=3,
        depends_on_field="color_scheme",
        depends_on_value="custom",
    )

    # Font settings
    font_family: str = ConfigField(
        default="Inter, system-ui, sans-serif",
        description="Main font family for the application",
        display_name="Font Family",
        display_type=FieldDisplayType.SELECT,
        options=[
            "Inter, system-ui, sans-serif",
            "Roboto, Arial, sans-serif",
            "SF Pro, system-ui, sans-serif",
            "monospace",
        ],
        category=FieldCategory.GENERAL,
        order=4,
    )

    font_size: str = ConfigField(
        default="medium",
        description="Base font size for the application",
        display_name="Font Size",
        display_type=FieldDisplayType.SELECT,
        options=["small", "medium", "large", "x-large"],
        category=FieldCategory.GENERAL,
        order=5,
    )

    # Advanced settings
    custom_css: str = ConfigField(
        default="",
        description="Custom CSS overrides",
        display_name="Custom CSS",
        display_type=FieldDisplayType.TEXTAREA,
        category=FieldCategory.ADVANCED,
        visibility="advanced",
        placeholder="/* Add your custom CSS here */",
        order=1,
    )

    animation_speed: float = ConfigField(
        default=1.0,
        description="Speed multiplier for UI animations",
        display_name="Animation Speed",
        display_type=FieldDisplayType.SLIDER,
        category=FieldCategory.ADVANCED,
        visibility="advanced",
        ui_extensions={"min": 0.5, "max": 2.0, "step": 0.1},
        order=2,
    )

    # Accessibility settings
    high_contrast: bool = ConfigField(
        default=False,
        description="Enable high contrast mode for better visibility",
        display_name="High Contrast Mode",
        display_type=FieldDisplayType.CHECKBOX,
        category=FieldCategory.GENERAL,
        order=6,
    )

    reduce_motion: bool = ConfigField(
        default=False,
        description="Reduce motion in animations for accessibility",
        display_name="Reduce Motion",
        display_type=FieldDisplayType.CHECKBOX,
        category=FieldCategory.GENERAL,
        order=7,
    )

    # URLs with custom validation
    theme_url: str = ConfigField(
        default="",
        description="URL to a custom theme (JSON format)",
        display_name="Theme URL",
        display_type=FieldDisplayType.TEXT,
        category=FieldCategory.ADVANCED,
        visibility="advanced",
        placeholder="https://example.com/theme.json",
        custom_validators=["url"],
        order=3,
    )

    # Extension point example
    custom_renderers = (["theme-preview"],)


class NotificationConfig(EnhancedConfig):
    """Notification settings with UI metadata."""

    # Class-level schema metadata for UI
    schema_meta = {
        "title": "Notification Settings",
        "description": "Configure how and when you receive notifications",
        "icon": "notifications",
        "category": "user_preferences",
        "tags": ["notifications", "alerts"],
    }

    # Schema version
    schema_version = SchemaVersion(1, 0, 0)

    # General settings
    enabled: bool = ConfigField(
        default=True,
        description="Enable notifications",
        display_name="Enable Notifications",
        display_type=FieldDisplayType.CHECKBOX,
        category=FieldCategory.GENERAL,
        order=1,
    )

    # Sound settings - depends on notifications being enabled
    sound_enabled: bool = ConfigField(
        default=True,
        description="Play sound for notifications",
        display_name="Sound Notifications",
        display_type=FieldDisplayType.CHECKBOX,
        category=FieldCategory.GENERAL,
        order=2,
        depends_on_field="enabled",
        depends_on_value=True,
    )

    sound_volume: int = ConfigField(
        default=50,
        description="Volume for notification sounds (0-100)",
        display_name="Sound Volume",
        display_type=FieldDisplayType.SLIDER,
        category=FieldCategory.GENERAL,
        order=3,
        depends_on_field="sound_enabled",
        depends_on_value=True,
        ui_extensions={"min": 0, "max": 100, "step": 1},
    )

    # Custom sound file - advanced setting
    custom_sound_file: str = ConfigField(
        default="",
        description="Path to custom notification sound file",
        display_name="Custom Sound File",
        display_type=FieldDisplayType.FILE,
        category=FieldCategory.ADVANCED,
        visibility="advanced",
        order=1,
        depends_on_field="sound_enabled",
        depends_on_value=True,
        ui_extensions={"accept": ".mp3,.wav,.ogg"},
    )


async def main() -> None:
    """Run the example."""
    # Register our extension and components
    SchemaExtensionRegistry.register_extension(MetricsExtension)
    register_custom_react_component()
    register_custom_validator()

    # Register our config classes
    ConfigSchemaRegistry.register(AppearanceConfig)
    ConfigSchemaRegistry.register(NotificationConfig)

    # Get list of registered schemas
    all_schemas = ConfigSchemaRegistry.list_schemas()
    categories = ConfigSchemaRegistry.list_categories()

    print(f"Registered {len(all_schemas)} schemas in {len(categories)} categories")
    print(f"Categories: {', '.join(categories)}")

    # Generate and save schema for React JSON Forms
    react_schema = AppearanceConfig.to_json_schema(ui_framework="react")

    # Save the schema to file
    output_dir = Path.cwd()
    with open(output_dir / "appearance_react.json", "w") as f:
        json.dump(react_schema, f, indent=2)

    print(f"\nGenerated React schema saved to: {output_dir / 'appearance_react.json'}")

    # Generate schema for Vue for comparison
    vue_response = ConfigSchemaRegistry.get_schema_ui(
        f"{NotificationConfig.__module__}.{NotificationConfig.__name__}",
        ui_framework="vue-formvuelate",
    )

    # Save the Vue schema
    with open(output_dir / "notifications_vue.json", "w") as f:
        json.dump(vue_response, f, indent=2)

    print(f"Generated Vue schema saved to: {output_dir / 'notifications_vue.json'}")

    # Demo how to extend a field with additional UI metadata
    AppearanceConfig.register_ui_component(
        "primary_color", "angular", "material-color-picker"
    )

    # Register a custom validator for the theme URL field
    AppearanceConfig.register_field_validator("theme_url", "url")

    # Get full schema with extensions applied
    full_schema = ConfigSchemaRegistry.get_schema_ui(
        f"{AppearanceConfig.__module__}.{AppearanceConfig.__name__}",
    )

    # Show some parts of the schema with extensions
    print("\nSchema with extensions applied:")
    if "x-metrics" in full_schema["schema"]:
        print(f"Metrics extension applied: {full_schema['schema']['x-metrics']}")

    # Show field extensions
    for field_name in ["primary_color", "theme_url"]:
        if field_name in full_schema["uiSchema"]:
            field_ui = full_schema["uiSchema"][field_name]
            print(f"\nField '{field_name}' UI schema:")
            for key, value in field_ui.items():
                if key.startswith("x-"):
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
