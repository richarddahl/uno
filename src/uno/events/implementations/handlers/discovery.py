# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Handler discovery functionality for event handlers.

This module provides discovery mechanisms for automatically finding and registering
event handlers from modules and packages.
"""

import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uno.events.implementations.handlers.registry import EventHandlerRegistry
    from uno.logging.protocols import LoggerProtocol


async def discover_handlers(
    package: str | ModuleType,
    logger: "LoggerProtocol",
    registry: "EventHandlerRegistry | None" = None,
) -> "EventHandlerRegistry":
    """
    Discover event handlers in a package.

    This function scans a package and its subpackages for event handlers,
    automatically registering them with the registry. Handlers can be:

    1. Objects that implement the EventHandlerProtocol
    2. Classes decorated with @handles(event_type)
    3. Functions decorated with @function_handler(event_type)
    4. Any object with an _is_event_handler attribute set to True

    Args:
        package: The package/module to scan
        logger: Logger for structured logging
        registry: Optional registry to use

    Returns:
        The registry with discovered handlers
    """
    # Import registry here to avoid circular imports
    from uno.events.implementations.handlers.registry import EventHandlerRegistry
    
    # Create the registry if not provided
    if registry is None:
        registry = EventHandlerRegistry(logger)

    # Set up handler decorator if it exists
    from uno.events.implementations.handlers.decorator import EventHandlerDecorator
    if hasattr(EventHandlerDecorator, "set_registry"):
        EventHandlerDecorator.set_registry(registry)

    # Process the package
    await _process_package(package, logger, registry)
    
    return registry


async def _process_package(
    package: str | ModuleType,
    logger: "LoggerProtocol",
    registry: "EventHandlerRegistry",
) -> None:
    """
    Process a package to discover handlers.
    
    Args:
        package: The package to process
        logger: Logger for structured logging
        registry: The registry to register handlers with
    """
    # Get the package as a module
    if isinstance(package, str):
        try:
            package_module = importlib.import_module(package)
        except ImportError as e:
            logger.error(
                "Error importing package", package=package, error=str(e), exc_info=e
            )
            return
    else:
        package_module = package

    # Get the package directory
    package_path = getattr(package_module, "__path__", None)
    if not package_path:
        logger.error(
            "Package has no __path__ attribute", package=package_module.__name__
        )
        return

    # Store discovered handler count before scanning
    initial_handler_count = sum(
        len(handlers) for handlers in registry._handlers.values()
    )
    
    # Process all modules in the package
    await _process_modules(package_module, logger, registry)
    
    # Calculate number of new handlers discovered
    final_handler_count = sum(len(handlers) for handlers in registry._handlers.values())
    new_handlers = final_handler_count - initial_handler_count

    logger.info(
        "Discovered event handlers",
        new_handlers=new_handlers,
        total_handlers=final_handler_count,
    )


async def _process_modules(
    pkg: ModuleType, logger: "LoggerProtocol", registry: "EventHandlerRegistry"
) -> None:
    """
    Process all modules in a package recursively.
    
    Args:
        pkg: The package to process
        logger: Logger for structured logging
        registry: The registry to register handlers with
    """
    pkg_path = pkg.__path__
    if not pkg_path:
        return

    for _, name, is_pkg in pkgutil.iter_modules(pkg_path):
        full_name = f"{pkg.__name__}.{name}"

        try:
            module = importlib.import_module(full_name)
            
            # Process the current module for handlers
            await _find_handlers_in_module(module, logger, registry)
            
            # Process subpackages recursively
            if is_pkg:
                await _process_modules(module, logger, registry)
                
        except ImportError as e:
            logger.warning(
                "Error importing module during handler discovery",
                module=full_name,
                error=str(e),
            )


async def _find_handlers_in_module(
    module: ModuleType, logger: "LoggerProtocol", registry: "EventHandlerRegistry"
) -> None:
    """
    Find and register handlers in a module.
    
    Args:
        module: The module to search
        logger: Logger for structured logging
        registry: The registry to register handlers with
    """
    for item_name in dir(module):
        try:
            item = getattr(module, item_name)

            # Check for class-based handlers
            if inspect.isclass(item):
                await _process_class_handler(item, logger, registry)
            # Check for function/decorated handlers
            elif hasattr(item, "_is_event_handler") and item._is_event_handler:
                await _process_decorated_handler(item, logger, registry)

        except (AttributeError, TypeError):
            # Skip items that can't be accessed or aren't handlers
            pass


async def _process_class_handler(
    cls: type, logger: "LoggerProtocol", registry: "EventHandlerRegistry"
) -> None:
    """
    Process a class that might be a handler.
    
    Args:
        cls: The class to process
        logger: Logger for structured logging
        registry: The registry to register handlers with
    """
    # Skip if already registered
    if getattr(cls, "_registered_with_discovery", False):
        return
        
    # Check if it has a handle method
    if hasattr(cls, "handle") and callable(cls.handle):
        try:
            # Try to instantiate and register the handler
            instance = cls()
            
            # Get the event type from the class or instance
            event_type = getattr(cls, "_event_type", None)
            if event_type is None and hasattr(instance, "event_type"):
                event_type = instance.event_type
                
            if event_type:
                await registry.register_handler(event_type, instance)
                cls._registered_with_discovery = True
                
                await logger.debug(
                    "Registered handler class",
                    handler=cls.__name__,
                    event_type=event_type,
                )
        except Exception as e:
            # Probably needs constructor arguments
            await logger.debug(
                "Couldn't auto-instantiate handler class",
                handler=cls.__name__,
                error=str(e),
            )


async def _process_decorated_handler(
    handler: object, logger: "LoggerProtocol", registry: "EventHandlerRegistry"
) -> None:
    """
    Process a decorated handler.
    
    Args:
        handler: The handler to process
        logger: Logger for structured logging
        registry: The registry to register handlers with
    """
    # Skip if already registered
    if getattr(handler, "_registered_with_discovery", False):
        return
        
    event_type = getattr(handler, "_event_type", None)
    if event_type:
        await registry.register_handler(event_type, handler)
        handler._registered_with_discovery = True
        
        await logger.debug(
            "Registered decorated handler",
            handler=handler.__name__,
            event_type=event_type,
        )
