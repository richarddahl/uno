# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Interface protocols for the Uno configuration system.

This module defines the protocols (interfaces) that configuration components
should implement. These protocols are intentionally NOT runtime_checkable
to ensure type safety at compile time only.
"""

from __future__ import annotations

from typing import (
    Any,
    Awaitable,
    ClassVar,
    ParamSpec,
    Protocol,
    TypeVar,
    runtime_checkable,
    overload,
)

from uno.config.environment import Environment


P = ParamSpec("P")
R = TypeVar("R", covariant=True)


@runtime_checkable
class SecureAccessibleProtocol(Protocol[P, R]):
    """Protocol for functions that require secure access.

    This protocol defines the interface for functions that have been
    decorated with @requires_secure_access, allowing type checkers to
    understand they require secure configuration to be initialized.
    """

    # This attribute is set by the decorator to mark functions
    # that require secure access
    __requires_secure_access__: bool

    # Handle no-argument functions and methods separately for better type checking
    @overload
    def __call__(self) -> Awaitable[R]:
        """Call signature for functions with no arguments."""
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        """Call signature for functions with arguments."""
        ...


class ModelWithSecureFieldsProtocol(Protocol):
    """Protocol for models that contain secure fields.

    This protocol defines the interface for models that use SecureField,
    ensuring they track which fields are secure.
    """

    _secure_fields: ClassVar[set[str]]


class ConfigProtocol(Protocol):
    """
    Protocol defining the interface for Uno configuration objects.

    This protocol is NOT runtime_checkable and should be used
    for static type checking only.
    """

    model_config: ClassVar[dict[str, Any]]

    @classmethod
    async def from_env(cls, env: Environment | None = None) -> ConfigProtocol:
        """
        Load settings from environment or specific env file.

        Args:
            env: The environment to load settings for

        Returns:
            Configured settings instance
        """
        ...


class ConfigManagerProtocol(Protocol):
    """
    Protocol defining the interface for configuration management.

    This protocol is NOT runtime_checkable and should be used
    for static type checking only.
    """

    async def load_settings(
        self,
        settings_class: type[ConfigProtocol],
        env: Environment | None = None,
        config_path: str | None = None,
        override_values: dict[str, object] | None = None,
    ) -> ConfigProtocol:
        """
        Load settings with explicit control over sources and priorities.

        Args:
            settings_class: The settings class to instantiate
            env: The environment to load settings for
            config_path: Optional path to configuration files
            override_values: Optional override values

        Returns:
            Configured settings instance
        """
        ...

    async def get_config(self, settings_class: type[ConfigProtocol]) -> ConfigProtocol:
        """
        Get configuration for a component with caching.

        Args:
            settings_class: The settings class to retrieve

        Returns:
            Configured settings instance (cached if previously loaded)
        """
        ...
