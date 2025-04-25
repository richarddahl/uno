"""
Event handler discovery utilities.

This module provides utilities for discovering event handlers that have been
decorated with the @handles or @function_handler decorators or otherwise
marked as event handlers.
"""

import importlib
import inspect
import pkgutil
import sys
from types import ModuleType
from typing import Any, cast

from uno.core.events.async_utils import FunctionHandlerAdapter
from uno.core.events.handlers import EventHandler, EventHandlerRegistry
from uno.core.logging.logger import LoggerService


def discover_handlers(
    search_target: str | ModuleType | dict[str, Any],
    registry: EventHandlerRegistry | None = None,
    logger: LoggerService | None = None
) -> list[Any]:
    """
    Discover event handlers in the given module or package.
    
    This function looks for classes decorated with @handles, functions
    decorated with @function_handler, or any objects with the _is_event_handler
    attribute set to True.
    
    Args:
        search_target: The module, package, or dictionary to search for handlers
        registry: Optional registry to register discovered handlers
        logger: Optional logger for logging discovery progress
        
    Returns:
        A list of discovered handlers
    """
    handlers = []
    
    # Create logger if needed
    if logger is None:
        logger = LoggerService(name="uno.events.discovery")
    
    # Convert string module path to module
    if isinstance(search_target, str):
        try:
            search_target = importlib.import_module(search_target)
        except ImportError as e:
            logger.error(f"Error importing module {search_target}: {e}")
            return []
    
    # Handle dictionary of globals
    if isinstance(search_target, dict):
        for name, obj in search_target.items():
            # Skip non-relevant items
            if name.startswith('_'):
                continue
                
            # Process the object
            handler = _process_potential_handler(obj, name, logger)
            if handler:
                handlers.append(handler)
        
        return handlers
    
    # It's a module - walk its contents
    for _, name, is_pkg in pkgutil.iter_modules(search_target.__path__, search_target.__name__ + '.'):
        # For each module in the package
        if is_pkg:
            # For packages, recursively search
            try:
                module = importlib.import_module(name)
                sub_handlers = discover_handlers(module, registry, logger)
                handlers.extend(sub_handlers)
            except ImportError as e:
                logger.error(f"Error importing package {name}: {e}")
                continue
        else:
            # For modules, import and search
            try:
                module = importlib.import_module(name)
                for attr_name in dir(module):
                    if attr_name.startswith('_'):
                        continue
                    
                    # Get the attribute
                    try:
                        attr = getattr(module, attr_name)
                        handler = _process_potential_handler(attr, f"{name}.{attr_name}", logger)
                        if handler:
                            handlers.append(handler)
                    except (AttributeError, ImportError):
                        continue
            except ImportError as e:
                logger.error(f"Error importing module {name}: {e}")
                continue
    
    # Register handlers if a registry was provided
    if registry:
        for handler in handlers:
            if hasattr(handler, "_event_type") and hasattr(handler, "_is_event_handler"):
                event_type = handler._event_type
                # Handle class-based handlers that need to be instantiated
                if inspect.isclass(handler) and issubclass(handler, EventHandler):
                    try:
                        registry.register_handler(event_type, handler())
                    except Exception as e:
                        logger.error(f"Error instantiating handler {handler.__name__}: {e}")
                # Handle function handlers
                elif callable(handler) and not isinstance(handler, EventHandler):
                    adapter = FunctionHandlerAdapter(handler, event_type)
                    registry.register_handler(event_type, adapter)
                # Handle pre-instantiated handlers
                else:
                    registry.register_handler(event_type, handler)
    
    return handlers


def _process_potential_handler(obj: Any, name: str, logger: LoggerService) -> Any | None:
    """
    Process a potential handler object.
    
    Args:
        obj: The object to check
        name: Name of the object for logging
        logger: Logger for logging discovery
        
    Returns:
        The handler if it's a valid handler, None otherwise
    """
    # Check if the object is already marked as an event handler
    if hasattr(obj, '_is_event_handler') and getattr(obj, '_is_event_handler', False):
        logger.debug(f"Found handler: {name}")
        return obj
            
    # Check if it's a class that inherits from EventHandler
    if (inspect.isclass(obj) and issubclass(obj, EventHandler) and obj != EventHandler and 
        hasattr(obj, '_is_event_handler') and getattr(obj, '_is_event_handler', False)):
        logger.debug(f"Found handler class: {name}")
        return obj
    
    return None


def register_handlers_from_modules(
    modules: list[str | ModuleType],
    registry: EventHandlerRegistry,
    logger: LoggerService | None = None
) -> int:
    """
    Discover and register handlers from multiple modules.
    
    This is a convenience function for discovering and registering handlers
    from multiple modules or packages.
    
    Args:
        modules: List of module names or module objects to search
        registry: Registry to register discovered handlers
        logger: Optional logger for logging discovery progress
        
    Returns:
        Number of handlers registered
    """
    count = 0
    
    # Create logger if needed
    if logger is None:
        logger = LoggerService(name="uno.events.discovery")
    
    for module in modules:
        handlers = discover_handlers(module, registry, logger)
        count += len(handlers)
    
    return count
