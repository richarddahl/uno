"""Decorator utils for the Uno event system.

This module provides decorators for registering event handlers with the event system
in a more declarative way, simplifying registration and discovery.

Examples:
    ```python
    # Class-based handler with decorator
    @handles(UserCreatedEvent)
    class UserCreatedHandler(EventHandler):
        async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
            event = context.get_typed_event(UserCreatedEvent)
            # Handle event...
            return Success(None)
    
    # Function-based handler with decorator
    @function_handler(UserCreatedEvent)
    async def log_user_created(context: EventHandlerContext) -> Result[None, Exception]:
        event = context.get_typed_event(UserCreatedEvent)
        # Handle event...
        return Success(None)
    ```
"""

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from uno.core.errors.result import Result
from uno.core.events.async_utils import FunctionHandlerAdapter
from uno.core.events.context import EventHandlerContext

T = TypeVar("T", bound=Callable)
HandlerFunc = TypeVar("HandlerFunc", bound=Callable[[EventHandlerContext], Result[Any, Exception] | Awaitable[Result[Any, Exception]]])


class EventHandlerDecorator:
    """Base class for all event handler decorators.
    
    This class provides common functionality for decorators that mark classes and
    functions as event handlers that can be automatically discovered and registered.
    """
    
    # Registry for automatic registration when decorators are applied
    _registry = None
    
    @classmethod
    def set_registry(cls, registry):
        """Set the registry for automatic registration.
        
        Args:
            registry: The EventHandlerRegistry to register handlers with
        """
        cls._registry = registry
    
    @classmethod
    def handles(cls, event_type):
        """Decorator for marking a class as an event handler.
        
        This decorator marks a class as handling a specific event type and allows
        it to be automatically discovered and registered with the event system.
        
        Args:
            event_type: The event type (string or class) that this handler processes
            
        Returns:
            A decorator function
        """
        def decorator(handler):
            event_type_str = cls._get_event_type_str(event_type)
            
            # Store the event type on the handler for later discovery
            handler._event_type = event_type_str
            handler._is_event_handler = True
            
            # If we have a registry, register the handler right away
            if cls._registry is not None:
                # Only instantiate if it's a class, not an instance
                if inspect.isclass(handler):
                    cls._registry.register_handler(event_type_str, handler())
                else:
                    cls._registry.register_handler(event_type_str, handler)
            
            return handler
        
        return decorator
    
    @staticmethod
    def _get_event_type_str(event_type):
        """Convert an event type to its string representation.
        
        This method handles various input formats for event types, including strings,
        classes with an event_type attribute, and classes that should use their name.
        
        Args:
            event_type: String, class, or object with event_type attribute
            
        Returns:
            The event type as a string
        """
        if isinstance(event_type, str):
            return event_type
        
        if hasattr(event_type, "event_type"):
            return cast('str', event_type.event_type)
        
        return event_type.__name__.lower()


# Create a global instance of the decorator for use throughout the application
handles = EventHandlerDecorator.handles


def function_handler(event_type):
    """
    Decorator for function-based event handlers.
    
    This decorator wraps a function as an event handler for a specific event type
    and allows it to be automatically discovered and registered with the event system.
    
    Args:
        event_type: The event type this handler processes
        
    Returns:
        The decorated function
    """
    def decorator(func: HandlerFunc) -> HandlerFunc:
        event_type_str = EventHandlerDecorator._get_event_type_str(event_type)
        
        # Mark the function for discovery
        func._event_type = event_type_str
        func._is_event_handler = True
        
        # If we have a registry, register an adapter right away
        if EventHandlerDecorator._registry is not None:
            adapter = FunctionHandlerAdapter(func, event_type_str)
            EventHandlerDecorator._registry.register_handler(event_type_str, adapter)
        
        return func
    
    return decorator
