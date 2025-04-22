"""
Internal helpers for Uno DI system.

This module contains advanced and internal-only classes/functions for extensibility or testing.
Nothing in this file is considered public API.
"""

import inspect
import logging
import typing
from typing import Any, Generic, TypeVar
from uno.core.errors.base import FrameworkError, ErrorCode
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

class CircularDependencyError(FrameworkError):
    """Raised when a circular dependency is detected during service resolution."""
    pass

class ServiceRegistrationError(FrameworkError):
    """Raised for errors during service registration."""
    pass

class _ServiceResolver:
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

    def register(self, service_type, implementation, scope=ServiceScope.SINGLETON, params=None):
        """
        Register a service type with implementation, scope, and optional params.
        Raises ServiceRegistrationError if the implementation is not compatible with the service_type.
        """
        if params is None:
            params = {}
        # Type/protocol check logic
        import inspect
        from typing import get_type_hints, Protocol
        # Check if service_type is a Protocol
        is_protocol = hasattr(service_type, '_is_protocol') and service_type._is_protocol
        if is_protocol:
            # Structural check: implementation must have all protocol methods
            missing = []
            for attr in dir(service_type):
                if not attr.startswith('_') and callable(getattr(service_type, attr, None)):
                    if not hasattr(implementation, attr):
                        missing.append(attr)
            if missing:
                raise ServiceRegistrationError(
                    f"Implementation {implementation} does not implement protocol {service_type.__name__}: missing {missing}",
                    "SERVICE_REGISTRATION_PROTOCOL_MISMATCH"
                )
        elif inspect.isclass(service_type) and inspect.isclass(implementation):
            if not issubclass(implementation, service_type):
                raise ServiceRegistrationError(
                    f"Implementation {implementation} is not a subclass of {service_type}",
                    "SERVICE_REGISTRATION_TYPE_MISMATCH"
                )
        elif callable(implementation):
            # Factory: try to check return type if possible
            hints = get_type_hints(implementation)
            return_hint = hints.get('return')
            if return_hint and inspect.isclass(service_type) and not issubclass(return_hint, service_type):
                raise ServiceRegistrationError(
                    f"Factory {implementation} does not return {service_type}",
                    "SERVICE_REGISTRATION_FACTORY_RETURN_TYPE_MISMATCH"
                )
        self._registrations[service_type] = ServiceRegistration(implementation, scope, params)
        self._logger.debug(f"Registered {service_type.__name__} as {implementation} with scope {scope}")
        # Clear singleton cache for this type if it exists
        if service_type in self._singletons:
            del self._singletons[service_type]
            self._logger.debug(f"Cleared singleton cache for {service_type.__name__}")

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
                        self._logger.error(f"Failed to prewarm singleton {service_type.__name__}: {e!s}")

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
    ) -> Any:
        """
        Resolve a service by type, optionally within a scope.
        """
        if _resolving is None:
            _resolving = set()
        import logging
        logging.debug(f"RESOLVE: Checking {service_type} (id={id(service_type)}) in _resolving: {[f'{t} (id={id(t)})' for t in _resolving]}")
        if service_type in _resolving:
            raise CircularDependencyError(
                f"Circular dependency detected for {service_type.__name__}",
                ErrorCode.DEPENDENCY_ERROR,
            )
        _resolving.add(service_type)
        try:
            registration = self._get_registration_or_error(service_type)
            if registration.scope == ServiceScope.SINGLETON:
                return self._resolve_singleton(service_type, registration, _resolving)
            elif registration.scope == ServiceScope.SCOPED:
                return self._resolve_scoped(
                    service_type, registration, scope, _resolving
                )
            else:
                return self._resolve_transient(registration, _resolving)
        finally:
            _resolving.remove(service_type)


    def _get_registration_or_error(self, service_type):
        registration = self._registrations.get(service_type)
        if not registration:
            raise FrameworkError(
                f"Service {service_type.__name__} is not registered",
                error_code=ErrorCode.DEPENDENCY_ERROR,
            )
        return registration

    def _resolve_singleton(self, service_type, registration, _resolving):
        if service_type not in self._singletons:
            instance = self._create_instance(registration, _resolving=_resolving)
            instance = self._maybe_initialize_async(instance)
            self._singletons[service_type] = instance
        return self._singletons[service_type]

    def _resolve_scoped(self, service_type, registration, scope, _resolving):
        if scope is None:
            raise FrameworkError(
                f"Cannot resolve scoped service {service_type.__name__} outside of a scope",
                error_code=ErrorCode.DEPENDENCY_ERROR,
            )
        if service_type not in scope._instances:
            instance = self._create_instance(registration, _resolving=_resolving)
            instance = self._maybe_initialize_async(instance)
            scope._instances[service_type] = instance
        return scope._instances[service_type]

    def _resolve_transient(self, registration, _resolving):
        instance = self._create_instance(registration, _resolving=_resolving)
        return self._maybe_initialize_async(instance)

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
    ) -> Any:
        impl = registration.implementation
        params = registration.params or {}

        if isinstance(impl, type):
            return self._create_type_instance(impl, params, _resolving)
        elif callable(impl):
            return impl(**params)
        else:
            return impl

    def _create_type_instance(self, impl, params, _resolving):
        sig, ctor_params, missing, extra = self._inspect_constructor_params(impl, params)
        if missing:
            self._resolve_missing_params(missing, sig, self._get_constructor_type_hints(impl), params, _resolving)
        self._resolve_still_missing_params(sig, ctor_params, impl, params, _resolving)
        resolved_params = self._build_resolved_params(ctor_params, params, _resolving)
        return impl(**resolved_params)

    def _resolve_still_missing_params(self, sig, ctor_params, impl, params, _resolving):
        ctor_params_names = [p.name for p in ctor_params]
        still_missing = [
            p for p in ctor_params_names
            if p not in params and sig.parameters[p].default is sig.parameters[p].empty
        ]
        if not still_missing:
            return
        type_hints = self._get_constructor_type_hints_safe(impl)
        globalns, localns = self._get_eval_namespaces(impl)
        for p in still_missing:
            param_type = self._get_param_type(p, sig, type_hints)
            param_type = self._eval_forward_ref(param_type, globalns, localns, impl)
            registered_type = self._find_registered_type(param_type, impl)
            if registered_type is not None:
                self._resolve_param_dependency(p, registered_type, impl, params, _resolving)
        # After attempting to resolve all, check again for missing
        still_missing_final = [
            p for p in ctor_params_names
            if p not in params and sig.parameters[p].default is sig.parameters[p].empty
        ]
        if still_missing_final:
            raise FrameworkError(
                f"Missing required parameters {still_missing_final} for {impl.__name__}",
                error_code=ErrorCode.DEPENDENCY_ERROR,
            )

    def _get_constructor_type_hints_safe(self, impl):
        import typing
        try:
            return typing.get_type_hints(impl.__init__, globalns=impl.__init__.__globals__, localns=None)
        except Exception:
            return {}

    def _get_eval_namespaces(self, impl):
        import sys
        globalns = impl.__init__.__globals__
        localns = sys.modules[impl.__module__].__dict__ if hasattr(impl, '__module__') else globalns
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
                getattr(a, '__name__', None) == getattr(b, '__name__', None)
                and getattr(a, '__module__', None) == getattr(b, '__module__', None)
                and getattr(a, '__qualname__', None) == getattr(b, '__qualname__', None)
            )
        if param_type != inspect._empty and isinstance(param_type, type):
            for t in self._registrations:
                if _is_same_type(param_type, t):
                    return t
        return None

    def _resolve_param_dependency(self, param_name, registered_type, impl, params, _resolving):
        if _resolving is not None:
            if registered_type in _resolving:
                raise CircularDependencyError(
                    f"Circular dependency detected for {registered_type.__name__}",
                    ErrorCode.DEPENDENCY_ERROR,
                )
            import logging
            logging.debug(f"PARAM: About to resolve {registered_type} (id={id(registered_type)}) for param '{param_name}' in {impl} (id={id(impl)}), _resolving={[f'{t} (id={id(t)})' for t in _resolving]}")
            _resolving.add(registered_type)
            try:
                params[param_name] = self.resolve(registered_type, _resolving=_resolving)
            finally:
                _resolving.remove(registered_type)
                logging.debug(f"PARAM: After resolving {registered_type} (id={id(registered_type)}), _resolving={[f'{t} (id={id(t)})' for t in _resolving]}")


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
                    raise CircularDependencyError(
                        f"Circular dependency detected for {p.annotation.__name__}",
                        ErrorCode.DEPENDENCY_ERROR,
                    )
                resolved_params[p.name] = self.resolve(
                    p.annotation, _resolving=_resolving
                )
            else:
                extra.append(p.name)
        if extra:
            raise FrameworkError(
                f"Extra parameters {extra} provided for {ctor_params[0].__class__.__name__ if ctor_params else 'unknown'}",
                error_code=ErrorCode.DEPENDENCY_ERROR,
            )
        return resolved_params


    def _inspect_constructor_params(self, impl, params):
        sig = inspect.signature(impl.__init__)
        ctor_params = list(sig.parameters.values())[1:]
        missing = [
            p.name
            for p in ctor_params
            if p.name not in params and p.default is p.empty
        ]
        extra = [
            k for k in params.keys() if k not in [p.name for p in ctor_params]
        ]
        return sig, ctor_params, missing, extra

    def _get_constructor_type_hints(self, impl):
        try:
            return typing.get_type_hints(impl.__init__)
        except Exception:
            return {}

    def _resolve_missing_params(
        self, missing, sig, type_hints, params, _resolving
    ):
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
                _resolving.add(annotation)
                try:
                    params[name] = self.resolve(annotation, _resolving=_resolving)
                finally:
                    _resolving.remove(annotation)
