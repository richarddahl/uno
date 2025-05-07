"""
Parameter resolution utilities for Uno DI.

This module provides functions for resolving constructor parameters during
dependency injection. It handles type hints, forward references, and parameter
validation.
"""

from __future__ import annotations

from typing import Any, Type, Dict, List, Optional, get_type_hints, get_origin, get_args
import inspect
from dataclasses import dataclass

from uno.infrastructure.di.errors import (
    MissingParameterError,
    ExtraParameterError,
    ServiceRegistrationError,
)
from uno.core.errors.result import Result, Success, Failure


def resolve_missing_params(
    impl: type[Any],
    params: dict[str, Any],
    resolver: Any,
    _resolving: set[type[Any]]
) -> Result[dict[str, Any], ServiceRegistrationError]:
    """
    Resolve missing parameters for a service implementation.

    Args:
        impl: The service implementation type
        params: Current parameter dictionary
        resolver: The service resolver
        _resolving: Set of types currently being resolved

    Returns:
        Result containing the updated parameter dictionary or an error
    """
    try:
        type_hints = get_type_hints(impl.__init__)
        missing_params = []
        
        for param_name, param_type in type_hints.items():
            if param_name == 'return':
                continue
                
            if param_name not in params:
                result = resolve_param_dependency(resolver, param_name, param_type, impl, params, _resolving)
                if result.is_success:
                    params[param_name] = result.value
                else:
                    missing_params.append(param_name)
                    
        if missing_params:
            return Failure(MissingParameterError(impl.__name__, missing_params))
            
        return Success(params)
    except Exception as e:
        return Failure(ServiceRegistrationError(str(e)))


def resolve_param_dependency(
    resolver: Any,
    param_name: str,
    param_type: type[Any],
    impl: type[Any],
    params: dict[str, Any],
    _resolving: set[type[Any]]
) -> Result[Any, ServiceRegistrationError]:
    """
    Resolve a parameter dependency.

    Args:
        resolver: The service resolver
        param_name: Name of the parameter
        param_type: Type of the parameter
        impl: The service implementation type
        params: Current parameter dictionary
        _resolving: Set of types currently being resolved

    Returns:
        Result containing the resolved parameter value or an error
    """
    try:
        registered_type = find_registered_type(resolver, param_type, impl)
        if registered_type:
            return Success(resolver.resolve(registered_type))
            
        # Handle forward references
        if isinstance(param_type, str):
            param_type = eval_forward_ref(resolver, param_type, impl)
            
        # Handle Optional types
        origin = get_origin(param_type)
        if origin is Optional:
            return Success(None)
            
        return Failure(ServiceRegistrationError(f"Could not resolve dependency for {param_name}"))
    except Exception as e:
        return Failure(ServiceRegistrationError(str(e)))


def get_param_type(param: inspect.Parameter) -> type[Any]:
    """
    Get the type of a parameter.

    Args:
        param: The parameter to get the type for

    Returns:
        The parameter type
    """
    if param.annotation == inspect.Parameter.empty:
        return Any
    return param.annotation


def find_registered_type(resolver: Any, param_type: type[Any], impl: type[Any]) -> Optional[type[Any]]:
    """
    Find a registered type that matches the parameter type.

    Args:
        resolver: The service resolver
        param_type: The parameter type to match
        impl: The service implementation type

    Returns:
        The matching registered type or None
    """
    for registered_type in resolver._registrations:
        if _is_same_type(registered_type, param_type):
            return registered_type
    return None


def eval_forward_ref(resolver: Any, param_type: str, impl: type[Any]) -> type[Any]:
    """
    Evaluate a forward reference type.

    Args:
        resolver: The service resolver
        param_type: The forward reference type string
        impl: The service implementation type

    Returns:
        The evaluated type
    """
    globalns = impl.__module__.__dict__
    localns = impl.__dict__
    return eval(param_type, globalns, localns)


def _is_same_type(a: type[Any], b: type[Any]) -> bool:
    """
    Check if two types are the same.

    Args:
        a: First type
        b: Second type

    Returns:
        True if the types are the same, False otherwise
    """
    if a is b:
        return True
        
    origin_a = get_origin(a)
    origin_b = get_origin(b)
    
    if origin_a is not origin_b:
        return False
        
    args_a = get_args(a)
    args_b = get_args(b)
    
    if len(args_a) != len(args_b):
        return False
        
    return all(_is_same_type(arg_a, arg_b) for arg_a, arg_b in zip(args_a, args_b)) 