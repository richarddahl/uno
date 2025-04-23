"""
Internal helpers for Uno DI system.

This module contains advanced and internal-only classes/functions for extensibility or testing.
Nothing in this file is considered public API.
"""

# Standard library
import logging
import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast, get_type_hints, get_origin, get_args, Generic
from typing_extensions import Annotated, TypeGuard
from uno.core.errors.result import Success, Failure
from uno.core.errors.definitions import (
    CircularDependencyError,
    MissingParameterError,
    ServiceRegistrationError,
    ServiceNotFoundError,
    ScopeError,
    FactoryError,
    ExtraParameterError,
    ServiceResolutionError,
)
from uno.core.logging.logger import get_logger
from uno.core.di.service_scope import ServiceScope

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


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
        scope: ServiceScope = ServiceScope.SINGLETON,
        params: dict[str, Any] | None = None,
        condition: Callable[[], bool] | None = None,
    ):
        self.implementation = implementation
        self.scope = scope
        self.params = params or {}
        self.condition = condition

    def __repr__(self) -> str:
        return (
            f"ServiceRegistration(implementation={self.implementation}, "
            f"scope={self.scope}, params={self.params}, "
            f"condition={self.condition})"
        )


class _ServiceResolver:
    # ... (existing code)

    def __init__(self, registrations: dict[type, ServiceRegistration], instances: dict[type, Any] | None = None, auto_register: bool = False):
        """
        Initialize the service resolver.
        
        Args:
            registrations: Dictionary of service registrations
            instances: Dictionary of pre-registered instances (effectively singletons)
            auto_register: Whether to auto-register services
        """
        self._registrations = registrations
        self._auto_register = auto_register
        # Initialize singletons cache with pre-registered instances
        self._singletons: dict[type, Any] = instances.copy() if instances else {}
        self._resolution_cache: dict[type, tuple] = {}
        self._logger = get_logger(__name__)

    def _is_concrete_type(self, t: type) -> bool:
        """
        Check if a type is concrete and not abstract.
        """
        if not isinstance(t, type):
            return False
            
        # Check if it's an interface/protocol
        if hasattr(t, '_is_protocol'):
            return False
            
        # Check if it's abstract
        if inspect.isabstract(t):
            return False
            
        # Check if it's a framework service
        if hasattr(t, '__framework_service__') and getattr(t, '__framework_service__', False):
            return True
            
        # Check if it has an __init__ method that can be called
        if not hasattr(t, '__init__'):
            return False
            
        # Check if it has any abstract methods
        try:
            if any(inspect.isabstractmethod(getattr(t, name)) for name in dir(t)):
                return False
        except Exception:
            return False
            
        return True

    def _get_registration_or_error(self, service_type, name=None):
        """
        Get a service registration or return an error if not found or condition not met.
        
        Args:
            service_type: The type of service to get
            name: Optional name for named services
            
        Returns:
            Success with the registration or Failure with an error
        """
        key = service_type
        if key not in self._registrations:
            # Try to auto-register the type if it's concrete and not abstract
            if self._auto_register:
                # First, try to find an implementation in the global registry for this interface
                try:
                    from uno.core.di.decorators import _global_service_registry
                except ImportError:
                    _global_service_registry = []
                impl = None
                scope = ServiceScope.TRANSIENT
                for cls in _global_service_registry:
                    if getattr(cls, "__framework_service_type__", None) is service_type:
                        impl = cls
                        scope = getattr(cls, "__framework_service_scope__", ServiceScope.TRANSIENT)
                        break
                if impl is not None:
                    return self.register(service_type, impl, scope)
                # Fallback: if the requested type itself is concrete and not abstract, register it as itself
                if self._is_concrete_type(service_type):
                    scope = ServiceScope.TRANSIENT
                    if hasattr(service_type, '__framework_service_scope__'):
                        scope = getattr(service_type, '__framework_service_scope__', ServiceScope.TRANSIENT)
                    return self.register(service_type, service_type, scope)
            return Failure(ServiceNotFoundError(f"No registration found for service {service_type.__name__}"))
            
        registration = self._registrations[key]
        if registration.condition and not registration.condition():
            return Failure(ServiceNotFoundError(f"Service condition not met for {service_type.__name__}"))
            
        return Success(registration)

    def register(self, service_type: type[T], implementation: type[T] | None = None, scope: ServiceScope = ServiceScope.TRANSIENT) -> Success[ServiceRegistration[T], ServiceRegistrationError] | Failure[ServiceRegistration[T], ServiceRegistrationError]:
        """
        Register a service with runtime type safety checks.
        
        Args:
            service_type: The type of service to register
            implementation: The implementation type or factory
            scope: The service scope
        Returns:
            Success with the registration or Failure with an error
        """
        import inspect
        try:
            if implementation is None:
                implementation = service_type

            # If implementation is a factory (callable), check its return type
            if callable(implementation) and not isinstance(implementation, type):
                sig = inspect.signature(implementation)
                return_type = sig.return_annotation
                # If no return annotation, fail
                if return_type is inspect.Signature.empty:
                    return Failure(ServiceRegistrationError("Factory must have a return type annotation for DI type safety."))
                # Check that return type is compatible with service_type
                if not (return_type is service_type or (isinstance(return_type, type) and issubclass(return_type, service_type))):
                    return Failure(ServiceRegistrationError(f"Factory return type {return_type} does not match service type {service_type}"))
            # If implementation is a type/class, check subclass/protocol compliance
            elif isinstance(implementation, type):
                # If service_type is a protocol or ABC, check issubclass
                if hasattr(service_type, '_is_protocol') or inspect.isabstract(service_type):
                    if not issubclass(implementation, service_type):
                        return Failure(ServiceRegistrationError(f"{implementation} does not implement protocol or abstract base {service_type}"))
                # Otherwise, check for normal subclassing
                elif not issubclass(implementation, service_type):
                    return Failure(ServiceRegistrationError(f"{implementation} is not a subclass of {service_type}"))
            else:
                # If implementation is not a type or callable, fail
                return Failure(ServiceRegistrationError(f"Implementation must be a type or callable, got {type(implementation)}"))

            registration = ServiceRegistration(implementation, scope)
            key = service_type
            self._registrations[key] = registration
            return Success(registration)
        except Exception as e:
            return Failure(ServiceRegistrationError(f"Failed to register service: {str(e)}", reason=str(e)))

    def register_instance(self, service_type, instance):
        """
        Register an instance for a service type.
        
        Args:
            service_type: The type of service
            instance: The service instance
        """
        self._logger.debug(f"Registered instance of {service_type.__name__}")
        self._singletons[service_type] = instance

    """
    INTERNAL USE ONLY.
    Service resolver for dependency injection.

    This class is responsible for low-level service registration, resolution, and scoping.
    Not intended for direct use by application code. All application/service code should use ServiceProvider.
    """

    def prewarm_singletons(self) -> None:
        """
        Pre-warm all singleton services by resolving them.
        """
        for key in list(self._registrations.keys()):
            registration = self._registrations[key]
            if registration.scope == ServiceScope.SINGLETON:
                service_type = key
                try:
                    result = self.resolve(service_type)
                    if isinstance(result, Failure):
                        self._logger.error(
                            f"Failed to prewarm singleton {service_type.__name__}: {result.error}"
                        )
                except Exception as e:
                    self._logger.error(
                        f"Failed to prewarm singleton {service_type.__name__}: {e!s}"
                    )

    def resolve(
        self,
        service_type: type,
        _resolving: set[type] | None = None,
        scope=None,
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
        print(f"[TEST DEBUG] _ServiceResolver.resolve: service_type={service_type}")
        print(f"[TEST DEBUG] _ServiceResolver registrations keys: {list(self._registrations.keys())}")
        """
        Resolve a service instance.
        
        Args:
            service_type: The type of service to resolve
            _resolving: Set of currently resolving types
            scope: Optional scope for scoped services
            
        Returns:
            Success with the resolved instance or Failure with an error
        """
        if not isinstance(service_type, type):
            return Failure(ServiceRegistrationError(f"Cannot resolve non-type: {service_type}"))
            
        if _resolving is None:
            _resolving = set()
        if service_type in _resolving:
            return Failure(CircularDependencyError(f"Circular dependency detected for {service_type.__name__}"))
        
        try:
            _resolving.add(service_type)
            result = self._get_registration_or_error(service_type)
            if isinstance(result, Failure):
                return result
            
            registration = result.value
            print(f"[TEST DEBUG] _ServiceResolver.resolve: registration for {service_type} = {registration}")
            if registration is None:
                # Fallback: attempt to instantiate concrete, no-arg types for unregistered services
                if self._is_concrete_type(service_type):
                    fallback_result = self._try_fallback_instantiation(service_type)
                    if isinstance(fallback_result, Success):
                        return fallback_result
                    # If fallback fails, return the error
                    return fallback_result
                return Failure(ServiceRegistrationError(f"Service {service_type.__name__} is not registered"))
            
            if registration.condition and not registration.condition():
                return Failure(ServiceNotFoundError(f"Service condition not met for {service_type.__name__}"))
            
            return self._resolve_by_lifetime(service_type, registration, scope, _resolving)
        finally:
            _resolving.discard(service_type)

    def get(self, service_type: type[T]) -> T:
        """
        Get a service instance.
        
        Args:
            service_type: The type of service to get
            
        Returns:
            The service instance
            
        Raises:
            ServiceNotFoundError: If the service cannot be resolved
        """
        result = self._get_registration_or_error(service_type)
        if isinstance(result, Failure):
            raise ServiceRegistrationError(result.error.message)
            
        registration = result.value
        
        # Check if we have a cached instance for singletons
        if service_type in self._singletons:
            return self._singletons[service_type]
            
        # Create the instance
        result = self._create_instance(registration)
        if isinstance(result, Failure):
            raise ServiceRegistrationError(result.error.message)
        instance = result.value
        
        # Cache singleton instances
        if registration.scope == ServiceScope.SINGLETON:
            self._singletons[service_type] = instance
            
        return instance

    def _create_instance(self, registration: ServiceRegistration) -> T:
        """
        Create an instance of a service type.
        
        Args:
            service_type: The type to instantiate
            registration: The service registration
            
        Returns:
            The instantiated service
            
        Raises:
            ServiceResolutionError: If the service cannot be instantiated
        """
        if not hasattr(registration, 'implementation'):
            return Failure(ServiceRegistrationError("Registration object is missing 'implementation' attribute"))
        if isinstance(registration.implementation, type) and inspect.isabstract(registration.implementation):
            return Failure(ServiceRegistrationError(f"Cannot instantiate abstract type: {registration.implementation.__name__}"))
        
        try:
            # Handle factory functions
            if callable(registration.implementation) and not isinstance(registration.implementation, type):
                return registration.implementation()
                
            # Get constructor parameters
            constructor = registration.implementation.__init__
            sig = inspect.signature(constructor)
            params = sig.parameters
            
            # Resolve constructor dependencies
            dependencies = {}
            for param_name, param in params.items():
                if param_name == "self":
                    continue
                    
                annotation = param.annotation
                if annotation == inspect.Parameter.empty:
                    continue
                    
                # Try to resolve the dependency
                dependencies[param_name] = self.get(annotation)
                
            # Create the instance
            return registration.implementation(**dependencies)
            
        except Exception as e:
            raise ServiceResolutionError(f"Failed to create instance of {registration.implementation.__name__}: {str(e)}") from e

    def _handle_registration_failure(self, service_type, reg_result):
        """
        Handle what to do when registration lookup fails (conditional, abstract, fallback, etc).
        
        Args:
            service_type: The type of service
            reg_result: The registration result
            
        Returns:
            Success or Failure with appropriate error
        """
        if isinstance(reg_result, Failure):
            return reg_result
            
        registration = reg_result.value
        if registration.condition and not registration.condition():
            return Failure(ServiceRegistrationError(f"Service condition not met for {service_type.__name__}"))
            
        return Success(None)

    def _try_fallback_instantiation(self, service_type):
        """
        Attempt to instantiate a concrete, user-defined type if not registered at all.
        
        Args:
            service_type: The type of service
            
        Returns:
            Success with the instance or Failure with an error
        """
        if not isinstance(service_type, type):
            return Failure(ServiceRegistrationError(f"Cannot instantiate non-type: {service_type}"))
            
        if service_type.__module__ == "builtins":
            return Failure(ServiceRegistrationError(f"Cannot instantiate built-in type: {service_type}"))
            
        try:
            instance = service_type()
            return Success(instance)
        except Exception as e:
            error_str = str(e)
            # Handle special error cases
            if self._is_abstract_or_protocol(service_type) or (
                "missing" in error_str and "parameter" in error_str
            ):
                return Failure(MissingParameterError(service_type.__name__, ["unknown"], reason=f"Cannot resolve parameter for {service_type.__name__}"))
            return Failure(FactoryError(f"Failed to instantiate {service_type}: {e}"))

    def _resolve_singleton(self, service_type, registration, _resolving):
        if service_type not in self._singletons:
            # Use registration.implementation (which should be a type)
            result = self._create_instance(registration)
            if isinstance(result, Failure):
                return result
            self._singletons[service_type] = result.value
        return Success(self._singletons[service_type])

    def _resolve_scoped(self, service_type, registration, scope, _resolving):
        """
        Resolve a scoped service.
        
        Args:
            service_type: The type of service to resolve
            registration: The service registration
            scope: The scope object
            _resolving: Set of currently resolving types
            
        Returns:
            Success with the service instance or Failure with an error
        """
        if scope is None:
            return Failure(ScopeError(f"No active scope for {service_type}"))
            
        if not hasattr(scope, "_instances"):
            scope._instances = {}
            
        if service_type in scope._instances:
            return Success(scope._instances[service_type])
            
        instance_result = self._create_instance(registration)
        if isinstance(instance_result, Failure):
            return instance_result
            
        instance = self._maybe_initialize_async(instance_result.value)
        scope._instances[service_type] = instance
        return Success(instance)

    def _maybe_initialize_async(self, instance):
        """
        If the instance has an async 'initialize' method, do not attempt to run or schedule it.
        Async service initialization must be awaited by the user after DI resolution.
        """
        initialize = getattr(instance, "initialize", None)
        if initialize and not inspect.iscoroutinefunction(initialize):
            initialize()
        return instance

    def _is_abstract_or_protocol(self, t: type) -> bool:
        """
        Check if a type is abstract or a protocol.
        """
        return inspect.isabstract(t) or hasattr(t, '_is_protocol')

    def _is_concrete_type(self, t: type) -> bool:
        """
        Check if a type is concrete and not abstract.
        """
        if not isinstance(t, type):
            return False
            
        # Check if it's an interface/protocol
        if hasattr(t, '_is_protocol'):
            return False
            
        # Check if it's abstract
        if inspect.isabstract(t):
            return False
            
        # Check if it's a framework service
        if hasattr(t, '__framework_service__') and getattr(t, '__framework_service__', False):
            return True
            
        # Check if it has an __init__ method that can be called
        if not hasattr(t, '__init__'):
            return False
            
        # Check if it has any abstract methods
        try:
            if any(inspect.isabstractmethod(getattr(t, name)) for name in dir(t)):
                return False
        except Exception:
            return False
            
        return True

    def _try_instantiate_impl(self, impl, params):
        print(f"[TEST DEBUG] _try_instantiate_impl: impl={impl}, params={params}")
        try:
            instance = impl(**params)
            print(f"[TEST DEBUG] _try_instantiate_impl: SUCCESS instance={instance}")
            return Success(instance)
        except Exception as e:
            print(f"[TEST DEBUG] _try_instantiate_impl: EXCEPTION {e}")
            error_str = str(e)
            if self._is_abstract_or_protocol(impl) or ("missing" in error_str and "parameter" in error_str):
                return Failure(MissingParameterError(impl.__name__, ["unknown"], reason=f"Cannot resolve parameter for {impl.__name__}"))
            return Failure(FactoryError(f"Failed to instantiate {impl.__name__}: {error_str}"))

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
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
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
            result = self.resolve(registered_type, _resolving=_resolving)
            if isinstance(result, Failure):
                return result
            return Success(result.value)
        except Exception as e:
            return Failure(ServiceRegistrationError(
                f"Failed to resolve parameter '{param_name}' of type {registered_type}: {str(e)}",
                reason=str(e)
            ))

    def _get_resolution_plan(self, t: type) -> tuple[inspect.Signature, list[inspect.Parameter]]:
        """
        Get the resolution plan for a type.
        """
        sig = inspect.signature(t)
        return sig, list(sig.parameters.values())

    def _get_constructor_type_hints_safe(self, t: type) -> dict[str, Any]:
        """
        Get type hints for a constructor safely.
        """
        try:
            return get_type_hints(t.__init__)
        except Exception:
            return {}

    def _get_eval_namespaces(self, t: type) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Get namespaces for evaluating type hints.
        """
        globalns = sys.modules[t.__module__].__dict__
        localns = t.__dict__
        return globalns, localns

    def _get_param_type(
        self, param_name: str, sig: inspect.Signature, type_hints: dict[str, Any]
    ) -> type | None:
        """
        Get the type of a parameter.
        """
        param = sig.parameters.get(param_name)
        if param is None:
            return None
        
        param_type = type_hints.get(param_name)
        if param_type is None:
            return None
        
        return param_type

    def _eval_forward_ref(
        self, t: type, globalns: dict[str, Any], localns: dict[str, Any], impl: type
    ) -> type:
        """
        Evaluate a forward reference type.
        """
        if isinstance(t, str):
            try:
                return eval(t, globalns, localns)
            except Exception:
                return t
        return t

    def _find_registered_type(self, t: type, impl: type) -> type | None:
        """
        Find a registered type that matches the given type.
        """
        if t in self._registrations:
            return t
        
        # Check if the type is a protocol and find an implementation
        if hasattr(t, '_is_protocol'):
            for registered_type in self._registrations:
                if issubclass(registered_type, t):
                    return registered_type
        
        return None

    def _resolve_by_lifetime(
        self,
        service_type: type,
        registration: ServiceRegistration,
        scope=None,
        _resolving: set[type] | None = None,
    ):
        scope = scope or getattr(self, "_scope", None)
        if registration.scope == ServiceScope.SINGLETON:
            if service_type not in self._singletons:
                result = self._create_instance(registration, _resolving)
                if isinstance(result, Success):
                    self._singletons[service_type] = result.value
                else:
                    return result
            return Success(self._singletons[service_type])
        elif registration.scope == ServiceScope.TRANSIENT:
            result = self._create_instance(registration, _resolving)
            if isinstance(result, Failure):
                return result
            return Success(result.value)
        elif registration.scope == ServiceScope.SCOPED:
            if scope is None:
                return Failure(ScopeError("No active scope for scoped service"))
            if service_type not in scope._instances:
                result = self._create_instance(registration, _resolving)
                if isinstance(result, Success):
                    scope._instances[service_type] = result.value
                else:
                    return result
            return Success(scope._instances[service_type])
        else:
            return Failure(ServiceRegistrationError(f"Unknown service scope: {registration.scope}"))

    def _resolve_singleton(
        self,
        service_type: type,
        registration: ServiceRegistration,
        _resolving: set[type],
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
        """
        Resolve a singleton service.
        """
        if service_type not in self._singletons:
            # Use registration.implementation (which should be a type)
            result = self._create_instance(registration, _resolving)
            if isinstance(result, Failure):
                return result
            self._singletons[service_type] = result.value
        return Success(self._singletons[service_type])

    def _resolve_scoped(
        self,
        service_type: type,
        registration: ServiceRegistration,
        scope: Any,
        _resolving: set[type],
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
        """
        Resolve a scoped service.
        """
        if scope is None:
            return Failure(ServiceRegistrationError(f"Cannot resolve scoped service {service_type.__name__} outside of scope"))
            
        if not hasattr(scope, "_instances"):
            scope._instances = {}
            
        if service_type in scope._instances:
            return Success(scope._instances[service_type])
            
        instance_result = self._create_instance(registration)
        if isinstance(instance_result, Failure):
            return instance_result
            
        instance = self._maybe_initialize_async(instance_result.value)
        scope._instances[service_type] = instance
        return Success(instance)

    def _resolve_transient(
        self,
        registration: ServiceRegistration,
        _resolving: set[type],
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
        """
        Resolve a transient service.
        """
        return self._create_instance(registration, _resolving)

    def _create_instance(
        self,
        registration: ServiceRegistration,
        _resolving: set[type] | None = None,
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
        """
        Create an instance of a type using its constructor.
        
        Args:
            registration: The service registration
            _resolving: Set of currently resolving types
            
        Returns:
            Success with the instance or Failure with an error
        """
        print(f"[TEST DEBUG] _create_instance: registration={registration}, type={type(registration)}")
        print(f"[TEST DEBUG] registration.__dict__ = {getattr(registration, '__dict__', str(registration))}")
        if not hasattr(registration, 'implementation'):
            print("[TEST DEBUG] registration is missing 'implementation' attribute!")
            return Failure(ServiceRegistrationError("Registration object is missing 'implementation' attribute"))
        if isinstance(registration.implementation, type) and inspect.isabstract(registration.implementation):
            return Failure(ServiceRegistrationError(f"Cannot instantiate abstract type: {registration.implementation.__name__}"))
        
        # Regular type
        try:
            result = self._resolve_missing_params(registration.implementation, registration.params, _resolving)
            if isinstance(result, Failure):
                return result
            params = result.value
            instance = registration.implementation(**params)
            return Success(instance)
        except Exception as e:
            return Failure(ServiceRegistrationError(
                f"Failed to create instance: {str(e)}",
                reason=str(e)
            ))

    def _resolve_missing_params(
        self,
        impl: type,
        params: dict[str, Any],
        _resolving: set[type],
    ) -> Success[dict[str, Any], ServiceRegistrationError | CircularDependencyError] | Failure[dict[str, Any], ServiceRegistrationError | CircularDependencyError]:
        """
        Resolve missing parameters for a type.
        
        Args:
            impl: The implementation type
            params: Existing parameters
            _resolving: Set of currently resolving types
            
        Returns:
            Success with updated params or Failure with error
        """
        sig, ctor_params = self._get_resolution_plan(impl)
        type_hints = self._get_constructor_type_hints_safe(impl)
        globalns, localns = self._get_eval_namespaces(impl)

        resolved_params = params.copy() if params else {}
        for param in ctor_params:
            # Skip *args and **kwargs
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            param_name = param.name
            if param_name in resolved_params:
                continue

            param_type = self._get_param_type(param_name, sig, type_hints)
            if param_type is None:
                return Failure(MissingParameterError(impl.__name__, [param_name], reason=f"Cannot resolve parameter '{param_name}' for {impl.__name__}"))

            param_type = self._eval_forward_ref(param_type, globalns, localns, impl)

            # Detect circular dependency
            if param_type in _resolving:
                return Failure(CircularDependencyError(f"Circular dependency detected for type '{param_type.__name__}' while resolving parameter '{param_name}' of {impl.__name__}"))

            registered_type = self._find_registered_type(param_type, impl)
            if registered_type is None:
                return Failure(ServiceRegistrationError(f"Cannot resolve parameter '{param_name}' of type {param_type}"))

            result = self._resolve_param_dependency(
                param_name, registered_type, impl, resolved_params, _resolving
            )
            if isinstance(result, Failure):
                return result
            resolved_params[param_name] = result.value

        return Success(resolved_params)

    def _resolve_param_dependency(
        self, param_name, registered_type, impl, params, _resolving
    ) -> Success[T, ServiceRegistrationError | CircularDependencyError] | Failure[T, ServiceRegistrationError | CircularDependencyError]:
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
            result = self.resolve(registered_type, _resolving=_resolving)
            if isinstance(result, Failure):
                return result
            return Success(result.value)
        except Exception as e:
            return Failure(ServiceRegistrationError(
                f"Failed to resolve parameter '{param_name}' of type {registered_type}: {str(e)}",
                reason=str(e)
            ))
