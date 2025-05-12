# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Event handler discovery functionality.

This module provides a way to discover and register event handlers from modules
and packages using an async-first approach without DI container dependencies.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import asyncio
from types import ModuleType
from typing import Any, cast

from uno.events.protocols import (
    EventHandlerProtocol,
    EventRegistryProtocol,
    EventDiscoveryProtocol,
)
from uno.events.registry import EventHandlerRegistry
from uno.logging.protocols import LoggerProtocol


class EventHandlerDiscovery(EventDiscoveryProtocol):
    """
    Event handler discovery implementation.

    Discovers event handlers in modules and packages.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Initialize the discovery service.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger

    async def discover_handlers(
        self,
        package: str | ModuleType,
        registry: EventRegistryProtocol | None = None,
    ) -> EventRegistryProtocol:
        """
        Discover event handlers in a package.

        This method scans a package and its subpackages for event handlers,
        automatically registering them with the registry.

        Args:
            package: The package or module to scan for handlers
            registry: Optional registry to register handlers with

        Returns:
            The registry with discovered handlers
        """
        # Create registry if not provided
        if registry is None:
            registry = EventHandlerRegistry(self.logger)

        # Process the package
        await self._process_package(package, registry)

        return registry

    async def _process_package(
        self,
        package: str | ModuleType,
        registry: EventRegistryProtocol,
    ) -> None:
        """
        Process a package to discover handlers.

        Args:
            package: The package to process
            registry: The registry to register handlers with
        """
        # Get the package as a module
        if isinstance(package, str):
            try:
                package_module = importlib.import_module(package)
            except ImportError as e:
                await self.logger.error(
                    "Error importing package",
                    package=package,
                    error=str(e),
                    exc_info=e,
                )
                return
        else:
            package_module = package

        # Get the package path
        package_path = getattr(package_module, "__path__", None)
        if not package_path:
            await self.logger.debug(
                "Module is not a package, scanning directly",
                module=package_module.__name__,
            )
            await self._scan_module(package_module, registry)
            return

        # Initial handler count for reporting
        handlers_before = await self._get_handler_count(registry)

        # Scan the root module first
        await self._scan_module(package_module, registry)

        # Scan all submodules
        for _, name, is_pkg in pkgutil.iter_modules(package_path):
            # Form the full module name
            full_name = f"{package_module.__name__}.{name}"

            try:
                module = importlib.import_module(full_name)

                if is_pkg:
                    # If it's a package, recursively process it
                    await self._process_package(module, registry)
                else:
                    # Otherwise scan the module
                    await self._scan_module(module, registry)
            except ImportError as e:
                await self.logger.error(
                    "Error importing module",
                    module=full_name,
                    error=str(e),
                    exc_info=e,
                )
                continue

        # Report handlers found
        handlers_after = await self._get_handler_count(registry)
        handlers_found = handlers_after - handlers_before

        if handlers_found > 0:
            await self.logger.info(
                "Discovered event handlers in package",
                package=package_module.__name__,
                handlers_found=handlers_found,
                total_handlers=handlers_after,
            )
        else:
            await self.logger.debug(
                "No handlers found in package",
                package=package_module.__name__,
            )

    async def _get_handler_count(self, registry: EventRegistryProtocol) -> int:
        """
        Get the total number of handlers in the registry.

        Args:
            registry: The registry to count handlers in

        Returns:
            The total number of handlers
        """
        # Since the protocol doesn't define a way to get all handlers,
        # we need to use internal details if possible or estimate
        if hasattr(registry, "_handlers") and isinstance(registry._handlers, dict):
            return sum(len(handlers) for handlers in registry._handlers.values())
        return 0

    async def _scan_module(
        self,
        module: ModuleType,
        registry: EventRegistryProtocol,
    ) -> None:
        """
        Scan a module for event handlers.

        Args:
            module: The module to scan
            registry: The registry to register handlers with
        """
        # Look for handler classes that implement EventHandlerProtocol
        for _, obj in inspect.getmembers(module):
            # Skip if not a class or callable
            if not (inspect.isclass(obj) or inspect.isfunction(obj) or callable(obj)):
                continue

            # Case 1: Object implements EventHandlerProtocol
            if (
                inspect.isclass(obj)
                and hasattr(obj, "handle")
                and callable(obj.handle)
                and not inspect.isabstract(obj)
            ):
                # Check if the class already has event type info
                event_type = getattr(obj, "_event_type", None)
                if event_type:
                    try:
                        # Create an instance if possible
                        if hasattr(obj, "__init__"):
                            sig = inspect.signature(obj.__init__)
                            # Simple heuristic: We can instantiate if it only requires self
                            # or has defaults for all other params
                            can_instantiate = all(
                                param.default is not inspect.Parameter.empty
                                for name, param in sig.parameters.items()
                                if name != "self"
                            )

                            if can_instantiate:
                                instance = obj()
                                await registry.register(
                                    event_type, cast(EventHandlerProtocol, instance)
                                )
                                await self.logger.debug(
                                    "Registered handler class instance",
                                    handler=f"{obj.__module__}.{obj.__qualname__}",
                                    event_type=event_type,
                                )
                    except Exception as e:
                        await self.logger.error(
                            "Error instantiating handler class",
                            handler=f"{obj.__module__}.{obj.__qualname__}",
                            error=str(e),
                            exc_info=e,
                        )

            # Case 2: Function with _is_event_handler attribute
            if (
                (inspect.isfunction(obj) or callable(obj))
                and hasattr(obj, "_is_event_handler")
                and hasattr(obj, "_event_type")
            ):
                event_type = getattr(obj, "_event_type")
                await registry.register(event_type, obj)
                await self.logger.debug(
                    "Registered decorated handler function",
                    handler=f"{obj.__module__}.{obj.__qualname__}",
                    event_type=event_type,
                )


async def discover_handlers(
    package: str | ModuleType,
    logger: LoggerProtocol,
    registry: EventRegistryProtocol | None = None,
) -> EventRegistryProtocol:
    """
    Discover event handlers in a package.

    This is a convenience function that creates an EventHandlerDiscovery
    and uses it to discover handlers.

    Args:
        package: The package or module to scan for handlers
        logger: Logger for structured logging
        registry: Optional registry to register handlers with

    Returns:
        The registry with discovered handlers
    """
    discovery = EventHandlerDiscovery(logger)
    return await discovery.discover_handlers(package, registry)
