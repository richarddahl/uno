"""
Internal helpers for Uno DI system.

This module contains advanced and internal-only classes/functions for extensibility or testing.
Nothing in this file is considered public API.
"""

import inspect
import logging
import typing
from typing import Any, Generic, TypeVar

from uno.core.errors.definitions import (
    CircularDependencyError,
    ExtraParameterError,
    FactoryError,
    MissingParameterError,
    ScopeError,
    ServiceNotFoundError,
    ServiceRegistrationError,
)
from uno.core.errors.result import ErrorCode, Failure, Success

from .service_scope import ServiceScope

T = TypeVar("T")


class ServiceRegistration(Generic[T]):
    """
    ADVANCED/INTERNAL: Service registration information.

    This class is not intended for typical end-user code, but is exposed for advanced/extensibility scenarios.
    Most users should use ServiceCollection for registrations.

    Holds the configuration for how a service should be resolved, including
    its implementation type or factory, scope, and initialization parameters.
    """

    def __init__(
        self,
        implementation: type[T] | Any,
        scope: Any = None,
        params: dict[str, Any] | None = None,
    ):
        self.implementation = implementation
        self.scope = scope
        self.params = params or {}


class _ServiceResolver:
    # ... (existing code)

    def _get_resolution_plan(self, impl):
        """Return (sig, ctor_params) for impl, using cache if available."""
        if not hasattr(self, "_resolution_cache"):
            self._resolution_cache = {}
        if impl in self._resolution_cache:
            return self._resolution_cache[impl]
        import inspect

        sig = inspect.signature(impl.__init__)
        # If __init__ is object.__init__ or only *args/**kwargs, treat as no required params
        if impl.__init__ is object.__init__:
            ctor_params = []
        else:
            ctor_params = [
                p
                for p in list(sig.parameters.values())[1:]
                if p.kind
                not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            ]
        print(
            f"[UNO DI DEBUG] _get_resolution_plan for {impl}: params={[p.name for p in ctor_params]}"
        )
        self._resolution_cache[impl] = (sig, ctor_params)
        return sig, ctor_params

    def _get_registration_or_error(self, service_type):
        registration = self._registrations.get(service_type)
        if registration is not None:
            # Check for conditional registration
            condition = getattr(registration, 'condition', None)
            if condition is not None and not condition():
                from uno.core.errors.definitions import ServiceNotFoundError
                return Failure(ServiceNotFoundError(f"Conditional registration not satisfied for {service_type}"))
            return Success(registration)
        return Failure(ServiceNotFoundError(str(service_type)))

    """
    INTERNAL USE ONLY.
    Service resolver for dependency injection.

    This class is responsible for low-level service registration, resolution, and scoping.
    Not intended for direct use by application code. All application/service code should use ServiceProvider.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        from uno.core.logging.logger import get_logger

        self._logger: logging.Logger = logger or get_logger("uno.di")
        self._registrations: dict[type, ServiceRegistration] = {}
        self._singletons: dict[type, Any] = {}
        self._resolution_cache: dict[type, tuple] = {}

    def register(
        self, service_type, implementation, scope=ServiceScope.SINGLETON, params=None
    ):
        """
        Register a service type with implementation, scope, and optional params.
        Returns Success(None) or Failure(ServiceRegistrationError).
        """
        if params is None:
            params = {}
        import inspect
        from typing import get_type_hints

        is_protocol = (
            hasattr(service_type, "_is_protocol") and service_type._is_protocol
        )
        if is_protocol:
            missing = []
            for attr in dir(service_type):
                if not attr.startswith("_") and callable(
                    getattr(service_type, attr, None)
                ):
                    if not hasattr(implementation, attr):
                        missing.append(attr)
            if missing:
                return Failure(
                    ServiceRegistrationError(
                        f"Implementation {implementation} does not implement protocol {service_type.__name__}: missing {missing}"
                    )
                )
        elif inspect.isclass(service_type) and inspect.isclass(implementation):
            if not issubclass(implementation, service_type):
                return Failure(
                    ServiceRegistrationError(
                        f"Implementation {implementation} is not a subclass of {service_type}"
                    )
                )
        elif callable(implementation):
            hints = get_type_hints(implementation)
            return_hint = hints.get("return")
            if (
                return_hint
                and inspect.isclass(service_type)
                and not issubclass(return_hint, service_type)
            ):
                return Failure(
                    ServiceRegistrationError(
                        f"Factory {implementation} does not return {service_type}"
                    )
                )
        self._registrations[service_type] = ServiceRegistration(
            implementation, scope, params
        )
        # Invalidate resolution cache for this implementation
        if (
            hasattr(self, "_resolution_cache")
            and implementation in self._resolution_cache
        ):
            del self._resolution_cache[implementation]
        self._logger.debug(
            f"Registered {service_type.__name__} as {implementation} with scope {scope}"
        )
        if service_type in self._singletons:
            del self._singletons[service_type]
            self._logger.debug(f"Cleared singleton cache for {service_type.__name__}")
        return Success(None)

    def prewarm_singletons(self):
        """
        Eagerly instantiate all singleton services and cache them.
        Useful for performance-sensitive applications or to catch errors early.
        """
        for service_type, registration in self._registrations.items():
            if getattr(registration, "scope", None) == ServiceScope.SINGLETON:
                if service_type not in self._singletons:
                    try:
                        self._resolve_singleton(service_type, registration, set())
                    except Exception as e:
                        self._logger.error(
                            f"Failed to prewarm singleton {service_type.__name__}: {e!s}"
                        )

    def register_instance(self, service_type: type, instance: Any) -> None:
        """
        Register an existing instance as a singleton.
        """
        self._singletons[service_type] = instance
        self._logger.debug(f"Registered instance of {service_type.__name__}")

    def resolve(
        self,
        service_type: type,
        scope: Any = None,
        _resolving: set[type] | None = None,
    ):
        """
        Resolve a service by type, optionally within a scope.
        Returns Success(instance) or Failure(error).
        """
        if _resolving is None:
            _resolving = set()
        else:
            _resolving = set(_resolving)

        if service_type in _resolving:
            from uno.core.errors.definitions import CircularDependencyError
            return Failure(CircularDependencyError(f"Circular dependency detected for {service_type}"))
        _resolving.add(service_type)
        print(f"[UNO DI DEBUG] BEFORE add: _resolving={list(_resolving - {service_type})}")
        print(f"[UNO DI DEBUG] AFTER add: _resolving={list(_resolving)}")
        try:
            reg_result = self._get_registration_or_error(service_type)
            if isinstance(reg_result, Failure):
                return self._handle_registration_failure(service_type, reg_result)
            registration = reg_result.value
            return self._resolve_by_lifetime(service_type, registration, scope, _resolving)
        finally:
            _resolving.remove(service_type)

    def _handle_registration_failure(self, service_type, reg_result):
        """
        Handle what to do when registration lookup fails (conditional, abstract, fallback, etc).
        """
        # If present but registration is invalid (e.g., failed condition), or reg_result is MissingParameterError, do NOT fallback instantiate
        from uno.core.errors.definitions import MissingParameterError, ServiceNotFoundError
        # If conditional registration not satisfied, do NOT fallback instantiate
        if isinstance(reg_result.error, ServiceNotFoundError) and 'Conditional registration' in str(reg_result.error):
            return reg_result
        if isinstance(reg_result.error, (ServiceNotFoundError, MissingParameterError)):
            return reg_result
        # Try fallback instantiation only for user-defined, concrete classes
        fallback_instance = self._try_fallback_instantiation(service_type)
        if fallback_instance is not None:
            return Success(fallback_instance)
        return reg_result

    def _try_fallback_instantiation(self, service_type):
        """
        Attempt to instantiate a concrete, user-defined type if not registered at all.
        """
        import inspect
        from uno.core.errors.result import Success, Failure
        from uno.core.errors.definitions import MissingParameterError
        if not (
            inspect.isclass(service_type)
            and not inspect.isabstract(service_type)
            and not getattr(service_type, '_is_protocol', False)
            and hasattr(service_type, '__module__')
            and not service_type.__module__.startswith('builtins')
            and not service_type.__module__.startswith('uno.core.di')
        ):
            return None
        try:
            instance = service_type()
            return Success(instance)
        except Exception as e:
            if isinstance(e, MissingParameterError):
                return Failure(e)

    def _resolve_by_lifetime(self, service_type, registration, scope, _resolving):
        """
        Dispatch to singleton, scoped, or transient resolution logic.
        """
        from uno.core.errors.result import Failure
        from uno.core.errors.definitions import ServiceNotFoundError
        from uno.core.di.service_scope import ServiceScope

        if registration.scope == ServiceScope.SINGLETON:
            print(f"[_resolve_by_lifetime] Scope is SINGLETON")
            return self._resolve_singleton(service_type, registration, _resolving)
        elif registration.scope == ServiceScope.SCOPED:
            print(f"[_resolve_by_lifetime] Scope is SCOPED")
            return self._resolve_scoped(service_type, registration, scope, _resolving)
        elif registration.scope == ServiceScope.TRANSIENT:
            print(f"[_resolve_by_lifetime] Scope is TRANSIENT")
            return self._resolve_transient(registration, _resolving)
        else:
            print(f"[_resolve_by_lifetime] Unknown service scope for {service_type}")
            return Failure(ServiceNotFoundError(f"Unknown service scope for {service_type}"))

    def _resolve_singleton(self, service_type, registration, _resolving):
        if service_type in self._singletons:
            return Success(self._singletons[service_type])
        instance_result = self._create_instance(registration, _resolving=_resolving)
        if isinstance(instance_result, Failure):
            return instance_result
        instance = instance_result.value
        instance = self._maybe_initialize_async(instance)
        self._singletons[service_type] = instance
        return Success(instance)

    def _resolve_scoped(self, service_type, registration, scope, _resolving):
        from uno.core.errors.result import Failure
        from uno.core.errors.definitions import ScopeError
        if scope is None:
            return Failure(ScopeError(f"No active scope for {service_type}"))
        if hasattr(scope, '_instances') and service_type in scope._instances:
            return Success(scope._instances[service_type])
        instance_result = self._create_instance(registration, _resolving=_resolving)
        if isinstance(instance_result, Failure):
            return instance_result
        instance = instance_result.value
        instance = self._maybe_initialize_async(instance)
        scope._instances[service_type] = instance
        return Success(instance)

    def _resolve_transient(self, registration, _resolving):
        return self._create_instance(registration, _resolving=_resolving)

    def _maybe_initialize_async(self, instance):
        """
        If the instance has an async 'initialize' method, do not attempt to run or schedule it.
        Async service initialization must be awaited by the user after DI resolution.
        """
        initialize = getattr(instance, "initialize", None)
        if initialize and not inspect.iscoroutinefunction(initialize):
            initialize()
        return instance

    def _create_instance(
        self, registration: ServiceRegistration, _resolving: set[type] | None = None
    ):
        impl = registration.implementation
        params = registration.params or {}

        if isinstance(impl, type):
            result = self._create_type_instance(impl, params, _resolving)
            return result
        elif callable(impl):
            try:
                return Success(impl(**params))
            except Exception as e:
                return Failure(FactoryError(str(impl), reason=str(e)))

    def _create_type_instance(self, impl, params, _resolving):
        sig, ctor_params = self._get_resolution_plan(impl)
        missing = [
            p.name for p in ctor_params if p.name not in params and p.default is p.empty
        ]
        extra = [k for k in params.keys() if k not in [p.name for p in ctor_params]]
        if missing:
            missing_result = self._resolve_missing_params(
                missing, sig, self._get_constructor_type_hints(impl), params, _resolving
            )
            if isinstance(missing_result, Failure):
                return missing_result
        still_missing_result = self._resolve_still_missing_params(
            sig, ctor_params, impl, params, _resolving
        )
        if isinstance(still_missing_result, Failure):
            return still_missing_result
        params_result = self._build_resolved_params(ctor_params, params, _resolving)
        if isinstance(params_result, Failure):
            return params_result
        # Check for any Failure in resolved parameters (shouldn't happen, but extra safety)
        if any(isinstance(v, Failure) for v in params_result.value.values()):
            # Return the first Failure found
            for v in params_result.value.values():
                if isinstance(v, Failure):
                    return v
        import inspect
        # Disallow instantiating protocols/abstracts
        if inspect.isabstract(impl) or getattr(impl, '_is_protocol', False):
            return Failure(MissingParameterError(str(impl), missing_params=[]))
        try:
            return Success(impl(**params_result.value))
        except Exception as e:
            # If instantiating a protocol/abstract, or missing params, return MissingParameterError
            if inspect.isabstract(impl) or getattr(impl, '_is_protocol', False):
                return Failure(MissingParameterError(str(impl), missing_params=[]))
            if 'missing' in str(e) and 'parameter' in str(e):
                return Failure(MissingParameterError(str(impl), missing_params=[]))
            return Failure(FactoryError(str(impl), reason=str(e)))

    def _resolve_still_missing_params(self, sig, ctor_params, impl, params, _resolving):
        ctor_params_names = [p.name for p in ctor_params]
        still_missing = [
            p
            for p in ctor_params_names
            if p not in params and sig.parameters[p].default is sig.parameters[p].empty
        ]
        if not still_missing:
            return Success(None)
        type_hints = self._get_constructor_type_hints_safe(impl)
        globalns, localns = self._get_eval_namespaces(impl)
        for p in still_missing:
            param_type = self._get_param_type(p, sig, type_hints)
            param_type = self._eval_forward_ref(param_type, globalns, localns, impl)
            registered_type = self._find_registered_type(param_type, impl)
            if registered_type is not None:
                dep_result = self._resolve_param_dependency(
                    p, registered_type, impl, params, _resolving
                )
                if isinstance(dep_result, Failure):
                    return dep_result
        still_missing_final = [
            p
            for p in ctor_params_names
            if p not in params and sig.parameters[p].default is sig.parameters[p].empty
        ]
        if still_missing_final:
            return Failure(
                MissingParameterError(impl.__name__, missing_params=still_missing_final)
            )
        return Success(None)

    def _build_resolved_params(self, ctor_params, params, _resolving):
        resolved_params = {}
        extra = []
        for p in ctor_params:
            if p.name in params:
                resolved_params[p.name] = params[p.name]
            elif (
                _resolving is not None
                and p.annotation != inspect._empty
                and isinstance(p.annotation, type)
                and p.annotation in self._registrations
            ):
                if p.annotation in _resolving:
                    return Failure(CircularDependencyError(p.annotation.__name__))
                result = self.resolve(p.annotation, _resolving=_resolving)
                if isinstance(result, Failure):
                    return result
                resolved_params[p.name] = result.value
            else:
                extra.append(p.name)
        if extra:
            return Failure(
                ExtraParameterError(
                    ctor_params[0].__class__.__name__ if ctor_params else "unknown",
                    extra_params=extra,
                )
            )
        return Success(resolved_params)

    def _get_constructor_type_hints_safe(self, impl):
        import typing

        try:
            return typing.get_type_hints(
                impl.__init__, globalns=impl.__init__.__globals__, localns=None
            )
        except Exception:
            return {}

    def _get_eval_namespaces(self, impl):
        import sys, builtins

        init = getattr(impl, "__init__", None)
        # If __init__ is a wrapper_descriptor (i.e., not a Python function), fallback to module or builtins
        if hasattr(init, "__globals__"):
            globalns = init.__globals__
        elif hasattr(impl, "__module__") and impl.__module__ in sys.modules:
            globalns = sys.modules[impl.__module__].__dict__
        else:
            globalns = vars(builtins)
        localns = (
            sys.modules[impl.__module__].__dict__
            if hasattr(impl, "__module__")
            else globalns
        )
        return globalns, localns

    def _get_param_type(self, param_name, sig, type_hints):
        return type_hints.get(param_name, sig.parameters[param_name].annotation)

    def _eval_forward_ref(self, param_type, globalns, localns, impl):
        if isinstance(param_type, str):
            try:
                return eval(param_type, globalns, localns)
            except Exception:
                # Fallback: search registered types by name/module/qualname (loosened)
                for t in self._registrations:
                    if (
                        t.__name__ == param_type
                        and getattr(t, "__module__", None) == impl.__module__
                    ):
                        return t
        return param_type

    def _find_registered_type(self, param_type, impl):
        import inspect

        def _is_same_type(a, b):
            return a is b or (
                getattr(a, "__name__", None) == getattr(b, "__name__", None)
                and getattr(a, "__module__", None) == getattr(b, "__module__", None)
                and getattr(a, "__qualname__", None) == getattr(b, "__qualname__", None)
            )

        if param_type != inspect._empty and isinstance(param_type, type):
            for t in self._registrations:
                if _is_same_type(param_type, t):
                    return t
        return None

    def _resolve_param_dependency(
        self, param_name, registered_type, impl, params, _resolving
    ):
        result = self.resolve(registered_type, _resolving=_resolving)
        if isinstance(result, Failure):
            return result
        params[param_name] = result.value

    def _get_constructor_type_hints(self, impl):
        try:
            return typing.get_type_hints(impl.__init__)
        except Exception:
            return {}

    def _resolve_missing_params(self, missing, sig, type_hints, params, _resolving):
        if _resolving is None:
            _resolving = set()
        for name in missing:
            annotation = type_hints.get(name)
            if (
                annotation
                and isinstance(annotation, type)
                and annotation in self._registrations
            ):
                if annotation in _resolving:
                    # Circular dependency detected
                    raise CircularDependencyError(
                        f"Circular dependency detected for {annotation.__name__}",
                        ErrorCode.DEPENDENCY_ERROR,
                    )
                result = self.resolve(
                    annotation,
                    _resolving=set(_resolving) if _resolving is not None else None,
                )
                if hasattr(result, "is_success") and result.is_success:
                    params[name] = result.value
                else:
                    return result
