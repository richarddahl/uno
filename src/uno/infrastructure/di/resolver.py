"""
Core resolver logic for Uno Dependency Injection system.

This module contains the main service resolution logic, previously implemented within _internal.py.
"""

from uno.infrastructure.di.service_registration import ServiceRegistration
from uno.infrastructure.di.service_scope import ServiceScope
from uno.core.errors.result import Failure, Success
from uno.core.errors.definitions import (
    CircularDependencyError,
    ServiceRegistrationError,
    ServiceNotFoundError,
    FactoryError,
    MissingParameterError,
    ScopeError,
    ExtraParameterError,
    ServiceResolutionError,
)
from uno.infrastructure.di.parameter_resolution import (
    resolve_missing_params,
    resolve_param_dependency,
    get_param_type,
    find_registered_type,
    eval_forward_ref,
)
from uno.infrastructure.di.type_utils import (
    is_abstract_or_protocol,
    is_concrete_type,
    get_constructor_type_hints_safe,
    get_eval_namespaces,
)
from typing import Any
import logging


class ServiceResolver:
    """
    Uno DI Service Resolver.

    Uno eagerly instantiates singleton services at provider initialization (not lazily on first access).
    This design ensures predictable startup, early error detection, and optimal runtime performance.
    """

    def _instantiate_with_injection(
        self, impl: type[Any], params: dict[str, Any], scope: Any
    ) -> (
        Success[Any, ServiceRegistrationError] | Failure[Any, ServiceRegistrationError]
    ):
        self._logger.debug(
            f"DI: ENTER _instantiate_with_injection for {impl} with params={params} scope={scope}"
        )
        import inspect

        sig = inspect.signature(impl.__init__)
        self._logger.debug(f"DI: constructor signature for {impl}: {sig}")
        for name, param in sig.parameters.items():
            self._logger.debug(
                f"DI: param '{name}', kind={param.kind}, annotation={param.annotation}, default={param.default}"
            )
        ctor_params = {}
        for name, param in sig.parameters.items():
            # Defensive: skip 'self', *args, **kwargs, and any param named 'args' or 'kwargs'
            if name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                self._logger.debug(
                    f"DI: skipping param '{name}' of kind '{param.kind}' for {impl} (VAR_POSITIONAL/VAR_KEYWORD)"
                )
                continue
            if name in ("args", "kwargs"):
                self._logger.debug(f"DI: skipping param '{name}' by name for {impl}")
                continue
            if param.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                self._logger.debug(
                    f"DI: skipping param '{name}' of kind '{param.kind}' for {impl}"
                )
                continue
            if name in params:
                ctor_params[name] = params[name]
            elif param.default is not inspect.Parameter.empty:
                # Use default value
                continue
            else:
                dep_type = param.annotation
                if dep_type is inspect.Parameter.empty:
                    self._logger.debug(
                        f"DI: MISSING TYPE ANNOTATION for param '{name}' in {impl}"
                    )
                    return Failure(
                        ServiceRegistrationError(
                            f"Cannot resolve parameter '{name}' for {impl}: missing type annotation"
                        )
                    )
                # Failsafe: assert that we are not processing *args/**kwargs or their names
                assert name not in ("args", "kwargs"), (
                    f"DI Failsafe: Attempted to process forbidden param name '{name}' for {impl}"
                )
                assert param.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ), (
                    f"DI Failsafe: Attempted to process forbidden param kind '{param.kind}' for '{name}' in {impl}"
                )
                dep_result = self.resolve(dep_type, scope=scope)
                if isinstance(dep_result, Failure):
                    self._logger.debug(
                        f"DI: FAILED to resolve dependency '{name}' for {impl}: {dep_result.error}"
                    )
                    return Failure(
                        ServiceRegistrationError(
                            f"Failed to resolve dependency '{name}' for {impl}: {dep_result.error}"
                        )
                    )
                ctor_params[name] = dep_result.value
        # Failsafe: check after loop
        for name, param in sig.parameters.items():
            assert name not in ("args", "kwargs"), (
                f"DI Failsafe: Post-loop found forbidden param name '{name}' for {impl}"
            )
            assert param.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ), (
                f"DI Failsafe: Post-loop found forbidden param kind '{param.kind}' for '{name}' in {impl}"
            )
        try:
            instance = impl(**ctor_params)
            self._logger.debug(
                f"DI: EXIT _instantiate_with_injection for {impl} SUCCESS instance={instance}"
            )
            return Success(instance)
        except Exception as e:
            self._logger.debug(
                f"DI: EXIT _instantiate_with_injection for {impl} FAILURE error={e}"
            )
            return Failure(
                ServiceRegistrationError(f"Failed to instantiate {impl}: {e}")
            )

    def get(self, service_type: type[Any]) -> Any:
        """
        Get a service instance. Returns the raw instance, raising ServiceRegistrationError if not found or failed.
        Args:
            service_type: The type of service to get
        Returns:
            The resolved service instance
        Raises:
            ServiceRegistrationError: If the service cannot be resolved
        """
        result = self.resolve(service_type)
        if isinstance(result, Failure):
            raise ServiceRegistrationError(str(result.error))
        # Legacy compatibility: if result is a monad, unwrap to raw instance
        if hasattr(result, "value"):
            return result.value
        return result

    def register(
        self,
        service_type: type[Any],
        implementation: type[Any] | None = None,
        scope: ServiceScope = ServiceScope.TRANSIENT,
    ) -> (
        Success[ServiceRegistration[Any], ServiceRegistrationError]
        | Failure[ServiceRegistration[Any], ServiceRegistrationError]
    ):
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
                if return_type is inspect.Signature.empty:
                    return Failure(
                        ServiceRegistrationError(
                            "Factory must have a return type annotation for DI type safety."
                        )
                    )
                if not (
                    return_type is service_type
                    or (
                        isinstance(return_type, type)
                        and issubclass(return_type, service_type)
                    )
                ):
                    return Failure(
                        ServiceRegistrationError(
                            f"Factory return type {return_type} does not match service type {service_type}"
                        )
                    )
            elif isinstance(implementation, type):
                if hasattr(service_type, "_is_protocol") or inspect.isabstract(
                    service_type
                ):
                    if not issubclass(implementation, service_type):
                        return Failure(
                            ServiceRegistrationError(
                                f"{implementation} does not implement protocol or abstract base {service_type}"
                            )
                        )
                elif not issubclass(implementation, service_type):
                    return Failure(
                        ServiceRegistrationError(
                            f"{implementation} is not a subclass of {service_type}"
                        )
                    )
            else:
                return Failure(
                    ServiceRegistrationError(
                        f"Implementation must be a type or callable, got {type(implementation)}"
                    )
                )
            registration = ServiceRegistration(implementation, scope)
            key = service_type
            self._registrations[key] = registration
            return Success(registration)
        except Exception as e:
            return Failure(
                ServiceRegistrationError(
                    f"Failed to register service: {e!s}", reason=str(e)
                )
            )

    def prewarm_singletons(self) -> None:
        """
        Eagerly instantiate all singleton services and cache them.
        Useful for performance-sensitive applications or to catch errors early.
        """
        for service_type, registration in self._registrations.items():
            if registration.scope == ServiceScope.SINGLETON:
                if service_type not in self._singletons:
                    try:
                        self.resolve(service_type)
                    except Exception as e:
                        self._logger.error(
                            f"Failed to prewarm singleton {service_type}: {e}"
                        )
                        raise

    """
    Main service resolver for Uno DI system.
    Handles registration lookup, instantiation, and lifecycle management.
    """

    def __init__(
        self,
        registrations: dict[type[Any], ServiceRegistration[Any]],
        instances: dict[type[Any], Any] | None = None,
        auto_register: bool = False,
    ) -> None:
        self._registrations = registrations
        self._auto_register = auto_register
        self._singletons: dict[type, Any] = instances.copy() if instances else {}
        self._resolution_cache: dict[type, tuple] = {}
        self._logger = logging.getLogger("uno.di.resolver")
        self._logger.setLevel(logging.DEBUG)

    def _get_registration_or_error(
        self, service_type: type[Any], name: str | None = None
    ) -> Any:
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
                try:
                    from uno.infrastructure.di.decorators import (
                        _global_service_registry,
                    )
                except ImportError:
                    _global_service_registry = []
                impl = None
                scope = ServiceScope.TRANSIENT
                for cls in _global_service_registry:
                    if getattr(cls, "__framework_service_type__", None) is service_type:
                        impl = cls
                        scope = getattr(
                            cls, "__framework_service_scope__", ServiceScope.TRANSIENT
                        )
                        break
                if impl is not None:
                    return self.register(service_type, impl, scope)
                from uno.infrastructure.di.type_utils import is_concrete_type

                if is_concrete_type(service_type):
                    scope = ServiceScope.TRANSIENT
                    if hasattr(service_type, "__framework_service_scope__"):
                        scope = getattr(
                            service_type,
                            "__framework_service_scope__",
                            ServiceScope.TRANSIENT,
                        )
                    return self.register(service_type, service_type, scope)
            return Failure(
                ServiceNotFoundError(
                    f"No registration found for service {service_type.__name__}"
                )
            )
        registration = self._registrations[key]
        if registration.condition and not registration.condition():
            return Failure(
                ServiceNotFoundError(
                    f"Service condition not met for {service_type.__name__}"
                )
            )
        return Success(registration)

    def resolve(
        self, service_type: type[Any], scope: Any = None
    ) -> Success[Any, Exception] | Failure[Any, Exception]:
        """
        Resolve an instance of the given service type.
        Always returns a Success(instance) or Failure(error), never raises.
        """
        # Check for singleton instance
        if service_type in self._singletons:
            return Success(self._singletons[service_type])

        result = self._get_registration_or_error(service_type)
        if isinstance(result, Failure):
            self._logger.error(f"Failed to resolve {service_type}: {result.error}")
            return Failure(result.error)
        registration = result.value
        try:
            if registration.scope == ServiceScope.SINGLETON:
                impl = registration.implementation
                params = registration.params or {}
                if callable(impl) and isinstance(impl, type):
                    import inspect

                    sig = inspect.signature(impl.__init__)
                    ctor_params = {}
                    for name, param in sig.parameters.items():
                        if name == "self":
                            continue
                        if name in params:
                            ctor_params[name] = params[name]
                        elif param.default is not inspect.Parameter.empty:
                            # Use default value
                            continue
                        else:
                            dep_type = param.annotation
                            if dep_type is inspect.Parameter.empty:
                                return Failure(
                                    ServiceRegistrationError(
                                        f"Cannot resolve parameter '{name}' for {impl}: missing type annotation"
                                    )
                                )
                            dep_result = self.resolve(dep_type, scope=scope)
                            if isinstance(dep_result, Failure):
                                return Failure(
                                    ServiceRegistrationError(
                                        f"Failed to resolve dependency '{name}' for {impl}: {dep_result.error}"
                                    )
                                )
                            ctor_params[name] = dep_result.value
                    instance = impl(**ctor_params)
                elif callable(impl):
                    instance = impl()
                else:
                    instance = impl
                self._singletons[service_type] = instance
                return Success(instance)
            elif registration.scope == ServiceScope.SCOPED:
                if scope is None:
                    return Failure(
                        ScopeError(
                            f"Attempted to resolve SCOPED service {service_type} with no active scope."
                        )
                    )
                instance = scope.get_instance(service_type)
                if instance is not None:
                    return Success(instance)
                impl = registration.implementation
                params = registration.params or {}
                if callable(impl) and isinstance(impl, type):
                    result = self._instantiate_with_injection(impl, params, scope)
                    if isinstance(result, Failure):
                        return result
                    instance = result.value
                elif callable(impl):
                    instance = impl()
                else:
                    instance = impl
                scope.set_instance(service_type, instance)
                return Success(instance)
            elif registration.scope == ServiceScope.TRANSIENT:
                impl = registration.implementation
                params = registration.params or {}
                if callable(impl) and isinstance(impl, type):
                    result = self._instantiate_with_injection(impl, params, scope)
                    if isinstance(result, Failure):
                        return result
                    instance = result.value
                elif callable(impl):
                    instance = impl()
                else:
                    instance = impl
                return Success(instance)
            else:
                return Failure(
                    ServiceRegistrationError(
                        f"Unsupported service scope for {service_type}: {registration.scope}"
                    )
                )
        except Exception as e:
            self._logger.error(f"Failed to instantiate {service_type}: {e}")
            return Failure(
                ServiceRegistrationError(f"Failed to instantiate {service_type}: {e}")
            )
