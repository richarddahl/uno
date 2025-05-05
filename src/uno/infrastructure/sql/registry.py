# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""Registry for SQL configuration classes."""

from typing import TYPE_CHECKING, Any, ClassVar

from uno.core.errors import FrameworkError
from uno.infrastructure.sql.interfaces import (
    EngineFactoryProtocol,
)  # DI protocol for engine factories

if TYPE_CHECKING:
    from uno.infrastructure.sql.config import SQLConfig


class SQLConfigRegistry:
    """Registry of all SQLConfig classes.

    This class maintains a registry of all SQLConfig subclasses for
    dynamic registration and discovery.

    Attributes:
        _registry: Dictionary of registered SQLConfig classes by name
    """

    _registry: ClassVar[dict[str, type["SQLConfig"]]] = {}

    @classmethod
    def register(cls, config_class: type["SQLConfig"]) -> None:
        """Register a SQLConfig class in the registry.

        Args:
            config_class: SQLConfig class to register

        Raises:
            FrameworkError: If a class with the same name already exists in the registry
                         and it's not the same class
        """
        if config_class.__name__ in cls._registry:
            # Skip if trying to register the same class again
            existing_class = cls._registry[config_class.__name__]
            if config_class.__module__ == existing_class.__module__:
                return
            raise FrameworkError(
                f"SQLConfig class: {config_class.__name__} already exists in the registry.",
                "DUPLICATE_SQLCONFIG",
            )
        cls._registry[config_class.__name__] = config_class

    @classmethod
    def get(cls, name: str) -> type["SQLConfig"] | None:
        """Get a SQLConfig class by name.

        Args:
            name: Name of the SQLConfig class

        Returns:
            SQLConfig class if found, None otherwise
        """
        return cls._registry.get(name)

    @classmethod
    def all(cls) -> dict[str, type["SQLConfig"]]:
        """Get all registered SQLConfig classes.

        Returns:
            Dictionary of all registered SQLConfig classes
        """
        return dict(cls._registry)

    @classmethod
    def emit_all(
        cls,
        connection: Any | None = None,  # type: ignore  # Forward ref/circular import workaround
        engine_factory: EngineFactoryProtocol
        | None = None,  # DI: injected, type-hinted with Protocol for extensibility
        config: Any | None = None,  # type: ignore  # Forward ref/circular import workaround
        exclude: list[str] | None = None,
    ) -> None:
        """
        Emit SQL for all registered SQLConfig classes.

        Args:
            connection: Existing connection to use (required; must be provided via DI)
            engine_factory: (UNUSED, for DI compatibility only)
            config: (UNUSED, for DI compatibility only)
            exclude: List of config class names to exclude

        Raises:
            FrameworkError: If SQL emission fails
        """
        exclude = exclude or []
        if connection is None:
            raise RuntimeError(
                "emit_all requires a connection provided via DI; engine/connection construction is forbidden here."
            )
        for name, config_cls in cls._registry.items():
            if name in exclude:
                continue
            config_instance = config_cls(
                connection_config=config, engine_factory=engine_factory
            )
            config_instance.emit_sql(connection)
