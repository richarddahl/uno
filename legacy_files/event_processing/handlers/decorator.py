# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Decorator implementation for event handlers.

This module provides decorators for marking classes and functions as event handlers
and registering them with the handler registry.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar, cast, get_type_hints

from uno.domain.protocols import DomainEventProtocol
from uno.events.implementations.handlers.base import BaseEventHandler
from uno.events.protocols import EventHandlerProtocol
from uno.logging.protocols import LoggerProtocol

T = TypeVar("T", bound=type[Any])
TEvent = TypeVar("TEvent", bound=DomainEventProtocol)
TResult = TypeVar("TResult")


def handles(
    event_type: type[TEvent] | Sequence[type[TEvent]]
) -> Callable[[T], T]:
    """
    Class decorator to mark a class as an event handler for the specified event type(s).

    The decorated class must be a subclass of BaseEventHandler or implement the
    EventHandlerProtocol interface.

    Args:
        event_type: The event type or types this handler can process

    Returns:
        The decorated class
    """
    if not isinstance(event_type, (list, tuple, set)):
        event_types = (event_type,)
    else:
        event_types = tuple(event_type)

    for et in event_types:
        if not (isinstance(et, type) and issubclass(et, DomainEventProtocol)):
            raise TypeError(
                f"Event type must be a subclass of DomainEventProtocol, got {et}"
            )

    def decorator(cls: T) -> T:
        if not (inspect.isclass(cls) and (
            issubclass(cls, BaseEventHandler) or
            any(
                base.__origin__ is EventHandlerProtocol
                for base in getattr(cls, "__bases__", ())
                if hasattr(base, "__origin__")
            )
        )):
            raise TypeError(
                f"Class {cls.__name__} must be a subclass of BaseEventHandler "
                "or implement EventHandlerProtocol"
            )

        # Store the event types as a class attribute
        cls._event_types = event_types  # type: ignore[attr-defined]
        cls._is_event_handler = True  # type: ignore[attr-defined]
        return cls

    return decorator


def handler(
    event_type: type[TEvent] | Sequence[type[TEvent]]
) -> Callable[[Callable[..., Awaitable[TResult]]], type[BaseEventHandler[TEvent, TResult]]]:
    """
    Function decorator to create an event handler from a function.

    The decorated function will be wrapped in a BaseEventHandler subclass.

    Args:
        event_type: The event type or types this handler can process

    Returns:
        A decorator function that converts the function into an event handler class
    """
    if not isinstance(event_type, (list, tuple, set)):
        event_types = (event_type,)
    else:
        event_types = tuple(event_type)

    for et in event_types:
        if not (isinstance(et, type) and issubclass(et, DomainEventProtocol)):
            raise TypeError(
                f"Event type must be a subclass of DomainEventProtocol, got {et}"
            )

    def decorator(
        func: Callable[..., Awaitable[TResult]]
    ) -> type[BaseEventHandler[TEvent, TResult]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Handler function must be async")

        # Create a unique name for the handler class
        class_name = f"{func.__name__.title()}Handler"

        # Create the handler class
        handler_class = type(
            class_name,
            (BaseEventHandler[TEvent, TResult],),
            {
                "_handle_impl": func,
                "_event_types": event_types,  # type: ignore[attr-defined]
                "_is_event_handler": True,  # type: ignore[attr-defined]
                "__module__": func.__module__,
                "__doc__": func.__doc__,
            },
        )

        # Copy type hints from the function to the class
        if hasattr(func, "__annotations__"):
            handler_class._handle_impl.__annotations__.update(func.__annotations__)  # type: ignore[attr-defined]
            if "return" in func.__annotations__:
                handler_class._handle_impl.__annotations__["return"] = func.__annotations__["return"]  # type: ignore[attr-defined]


        # Copy the function's module and docstring
        handler_class.__module__ = func.__module__
        handler_class.__doc__ = func.__doc__

        return cast(type[BaseEventHandler[TEvent, TResult]], handler_class)

    return decorator
