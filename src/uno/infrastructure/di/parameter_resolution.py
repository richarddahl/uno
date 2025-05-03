from typing import Any, TYPE_CHECKING
from uno.core.errors.definitions import (
    CircularDependencyError,
    MissingParameterError,
    ServiceRegistrationError,
)
from uno.core.errors.result import Failure, Success

if TYPE_CHECKING:
    from .service_registration import ServiceRegistration


def resolve_missing_params(
    resolver, impl: type, params: dict[str, Any], _resolving: set[type]
):
    """
    Deprecated: Use resolver._instantiate_with_injection for all DI instantiations.
    """
    return resolver._instantiate_with_injection(impl, params, None)



def resolve_param_dependency(
    resolver, param_name, registered_type, impl, params, _resolving
):
    """
    Resolve a parameter dependency.
    Args:
        param_name: Name of the parameter
        registered_type: The type to resolve
        impl: The implementation type
        params: Existing parameters
        _resolving: Set of currently resolving types
    Returns:
        Success with the resolved value or Failure with an error
    """
    try:
        result = resolver.resolve(registered_type, _resolving=_resolving)
        if isinstance(result, Failure):
            return result
        return Success(result.value)
    except Exception as e:
        return Failure(
            ServiceRegistrationError(
                f"Failed to resolve parameter '{param_name}' of type {registered_type}: {e!s}",
                reason=str(e),
            )
        )

def get_param_type(param_name, sig, type_hints):
    return type_hints.get(param_name, sig.parameters[param_name].annotation)

def find_registered_type(resolver, param_type, impl):
    import inspect
    def _is_same_type(a, b):
        return a is b or (
            getattr(a, "__name__", None) == getattr(b, "__name__", None)
            and getattr(a, "__module__", None) == getattr(b, "__module__", None)
            and getattr(a, "__qualname__", None) == getattr(b, "__qualname__", None)
        )
    if param_type != inspect._empty and isinstance(param_type, type):
        for t in resolver._registrations:
            if _is_same_type(param_type, t):
                return t
    return None

def eval_forward_ref(resolver, param_type, globalns, localns, impl):
    if isinstance(param_type, str):
        try:
            return eval(param_type, globalns, localns)
        except Exception:
            for t in resolver._registrations:
                if (
                    t.__name__ == param_type
                    and getattr(t, "__module__", None) == impl.__module__
                ):
                    return t
    return param_type
