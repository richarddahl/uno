# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
UI component registry for schema-driven interfaces.

This module provides a registry system for UI components, renderers,
validators, and transformers that can be used with schema-driven UIs.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, TypeVar, cast

T = TypeVar("T")


class UIComponentRegistry:
    """Registry for custom UI components and renderers.

    This registry allows extension of the schema system with custom
    UI components for different field types and rendering strategies.
    """

    _components: dict[str, type] = {}
    _renderers: dict[str, Callable[..., Any]] = {}
    _validators: dict[str, Callable[..., bool]] = {}
    _transformers: dict[str, Callable[..., Any]] = {}

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
