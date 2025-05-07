"""
Type utility functions for Uno DI.

This module provides utility functions for working with types during dependency injection,
including checking for abstract types, concrete types, and handling type hints.
"""

from __future__ import annotations

from typing import Any, Type, Dict, get_type_hints, get_origin, get_args
import inspect
import sys
from abc import ABC, ABCMeta


def is_abstract_or_protocol(t: type[Any]) -> bool:
    """
    Check if a type is abstract or a protocol.

    Args:
        t: The type to check

    Returns:
        True if the type is abstract or a protocol, False otherwise
    """
    if inspect.isabstract(t):
        return True
        
    if hasattr(t, "__origin__") and t.__origin__ is type:
        return True
        
    if hasattr(t, "_is_protocol") and t._is_protocol:
        return True
        
    return False


def is_concrete_type(t: type[Any]) -> bool:
    """
    Check if a type is concrete (not abstract or protocol).

    Args:
        t: The type to check

    Returns:
        True if the type is concrete, False otherwise
    """
    if not inspect.isclass(t):
        return False
        
    if is_abstract_or_protocol(t):
        return False
        
    if t.__module__ == "typing":
        return False
        
    return True


def get_constructor_type_hints_safe(impl: type[Any]) -> dict[str, Any]:
    """
    Safely get type hints for a class constructor.

    Args:
        impl: The class to get type hints for

    Returns:
        Dictionary of parameter names to types
    """
    try:
        return get_type_hints(impl.__init__)
    except Exception:
        return {}


def get_eval_namespaces(impl: type[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Get the global and local namespaces for evaluating type hints.

    Args:
        impl: The class to get namespaces for

    Returns:
        Tuple of (global_namespace, local_namespace)
    """
    globalns = sys.modules[impl.__module__].__dict__
    localns = impl.__dict__
    return globalns, localns 