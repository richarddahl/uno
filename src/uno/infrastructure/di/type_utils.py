"""
Type utility functions for Uno DI.

These helpers provide type reflection, protocol/abstract/concrete checks, and safe type hint and namespace extraction for DI resolution.
"""
from typing import Any, get_type_hints
import inspect
import sys
import builtins

def is_abstract_or_protocol(t: type[Any]) -> bool:
    """
    Check if a type is abstract or a protocol.
    """
    return inspect.isabstract(t) or hasattr(t, "_is_protocol")

def is_concrete_type(t: type[Any]) -> bool:
    """
    Check if a type is concrete and not abstract.
    """
    if not isinstance(t, type):
        return False
    # Check if it's an interface/protocol
    if hasattr(t, "_is_protocol"):
        return False
    # Check if it's abstract
    if inspect.isabstract(t):
        return False
    # Check if it's a framework service
    if hasattr(t, "__framework_service__") and getattr(t, "__framework_service__", False):
        return True
    # Check if it has an __init__ method that can be called
    if not hasattr(t, "__init__"):
        return False
    # Check if it has any abstract methods
    try:
        if any(inspect.isabstractmethod(getattr(t, name)) for name in dir(t)):
            return False
    except Exception:
        return False
    return True

def get_constructor_type_hints_safe(impl: type[Any]) -> dict[str, Any]:
    """
    Get type hints for a constructor safely.
    """
    try:
        return get_type_hints(impl.__init__)
    except Exception:
        return {}

def get_eval_namespaces(impl: type[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Get namespaces for evaluating type hints.
    """
    init = getattr(impl, "__init__", None)
    # If __init__ is a wrapper_descriptor (i.e., not a Python function), fallback to module or builtins
    if hasattr(init, "__globals__"):
        globalns = init.__globals__
    elif hasattr(impl, "__module__") and impl.__module__ in sys.modules:
        globalns = sys.modules[impl.__module__].__dict__
    else:
        globalns = vars(builtins)
    localns = sys.modules[impl.__module__].__dict__ if hasattr(impl, "__module__") else globalns
    return globalns, localns
