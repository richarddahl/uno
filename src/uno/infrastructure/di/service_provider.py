"""
Service provider for the Uno DI system.

This module provides the ServiceProvider class which is responsible for
resolving services from the DI container.

Note: All dependencies must be passed explicitly from the composition root.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    runtime_checkable
)
from typing_extensions import ParamSpec, Protocol
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import inspect
import logging
from datetime import datetime, time
import asyncio

from uno.core.errors.definitions import (
    FrameworkError,
    CircularDependencyError,
    DependencyResolutionError,
    ScopeError,
    ExtraParameterError,
    MissingParameterError,
    FactoryError,
    ServiceResolutionError,
    ServiceNotFoundError,
    ServiceDiscoveryValidationError,
)

from uno.infrastructure.di.errors import (
    ServiceRegistrationError,
    ServiceStateError,
    ServiceInitializationError,
    ServiceHealthError,
    ServiceResilienceError,
    ServiceCompositionError,
    ServiceValidationError,
    ServiceStateError,
    ServiceConstraintError,
    ServiceConfigurationError,
    ServiceInterceptionError
)

from uno.infrastructure.di.interfaces import (
    ServiceLifecycleProtocol,
    ServiceEventHandlerProtocol,
    ServiceEventEmitterProtocol,
    ServiceMockProtocol,
    ServiceRecoveryProtocol,
    CompositeServiceProtocol,
    AggregateServiceProtocol,
    ServiceChainProtocol,
    ServiceHealthCheckProtocol,
    ServiceConstraintValidatorProtocol,
    ServiceInterceptorProtocol,
    ServiceMiddlewareProtocol,
    ServiceContractProtocol,
    ServiceState,
    ServiceHealth
)

from uno.infrastructure.di.service_collection import ServiceCollection

from uno.infrastructure.di.decorators import (
    service, singleton, transient, scoped,
    requires_initialization, requires_cleanup, requires_health_check,
    requires_recovery, requires_validation, requires_mocking,
    requires_composition, requires_aggregation, requires_interception,
    requires_middleware, requires_contract
)
from uno.core.errors.result import Result

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])
TEntity = TypeVar("TEntity", bound=Any)
TQuery = TypeVar("TQuery", bound=Any)
TResult = TypeVar("TResult", bound=Any)
TValidator = TypeVar("TValidator", bound=ServiceConstraintValidatorProtocol)
TInterceptor = TypeVar("TInterceptor", bound=ServiceInterceptorProtocol)
TMiddleware = TypeVar("TMiddleware", bound=ServiceMiddlewareProtocol)
TContract = TypeVar("TContract", bound=ServiceContractProtocol)
TComposite = TypeVar("TComposite", bound=Any, covariant=True)
TAggregate = TypeVar("TAggregate", bound=Any, covariant=True)

from uno.infrastructure.di.service_scope import Scope, ServiceScope
from uno.core.errors.result import Failure, Success

class ServiceResolver:
    """Concrete implementation of service resolution.

    Example:
        ```python
        resolver = ServiceResolver(
            registrations=service_collection._registrations,
            named_registrations=service_collection._named_registrations,
            instances=service_collection._instances,
            auto_register=False
        )
        ```
    """

    def __init__(self, 
                 registrations: dict[type[Any], Any], 
                 instances: dict[type[Any], Any], 
                 named_registrations: dict[str, Any] | None = None,
                 auto_register: bool = False) -> None:
        """
        Initialize the service resolver.

        Args:
            registrations: Dictionary of service registrations
            instances: Dictionary of service instances
            named_registrations: Dictionary of named service registrations
            auto_register: Whether to automatically register missing services
        """
        self._registrations = registrations
        self._instances = instances
        self._named_registrations = named_registrations or {}
        self._auto_register = auto_register

    def resolve_named(self, service_type: type[Any], name: str, _resolving: set[type[Any]] | None = None) -> Result[Any, ServiceRegistrationError]:
        """
        Resolve a named service instance.

        Args:
            service_type: The type of service to resolve
            name: The name of the service registration
            _resolving: Set of currently resolving types (for circular dependency detection)

        Returns:
            Success with the resolved service or Failure with an error
        """
        if _resolving is None:
            _resolving = set()

        if service_type in _resolving:
            return Failure(CircularDependencyError(f"Circular dependency detected for {service_type.__name__} (named: {name})"))

        _resolving.add(service_type)

        try:
            # Look for instance first
            if service_type in self._instances:
                return Success(self._instances[service_type])
                
            # Check for named registration
            if name in self._named_registrations:
                registration = self._named_registrations[name]
                if hasattr(registration, 'implementation'):
                    impl = registration.implementation
                    if callable(impl) and not isinstance(impl, type):
                        # It's a factory function
                        result = impl()
                        if isinstance(result, Result):
                            return result
                        return Success(result)
                    elif isinstance(impl, type):
                        # It's a class that needs instantiation
                        # For parameterized services, we need to inspect the constructor and resolve dependencies
                        from inspect import signature, Parameter
                        
                        sig = signature(impl.__init__)
                        params = {}
                        
                        # Skip the 'self' parameter
                        for param_name, param in list(sig.parameters.items())[1:]:
                            # If parameter has a default value and is not provided, use the default
                            if param.default is not Parameter.empty:
                                continue
                                
                            param_type = param.annotation
                            # Special case for named dependencies of the same type as the service
                            if param_type == service_type and param_name == 'service':
                                # When a service depends on the same type as itself, use the "base" version
                                # or the first other named version we can find
                                
                                # If there's a named "base" service, use that
                                if "base" in self._named_registrations:
                                    base_reg = self._named_registrations["base"]
                                    if hasattr(base_reg, 'implementation'):
                                        base_impl = base_reg.implementation
                                        # If it's a class, instantiate it
                                        if isinstance(base_impl, type):
                                            instance = base_impl()
                                            params[param_name] = instance
                                        else:
                                            # It's already an instance or factory
                                            params[param_name] = base_impl
                                    continue
                                
                                # Or try to find the unnamed version
                                if service_type in self._registrations:
                                    # Don't try to use the same named registration we're currently resolving
                                    # to avoid circular dependency
                                    _resolving_copy = _resolving.copy()
                                    base_result = self.resolve(service_type, _resolving_copy)
                                    if base_result.is_success:
                                        params[param_name] = base_result.unwrap()
                                        continue
                                
                                # If we can't find a suitable base implementation,
                                # check if there's another named instance we can use
                                found = False
                                for other_name, other_reg in self._named_registrations.items():
                                    # Skip the current registration to avoid circular dependency
                                    if other_name == name:
                                        continue
                                    
                                    if hasattr(other_reg, 'service_type') and other_reg.service_type == service_type:
                                        if hasattr(other_reg, 'implementation'):
                                            other_impl = other_reg.implementation
                                            if isinstance(other_impl, type):
                                                # It's a class, instantiate it
                                                instance = other_impl()
                                                params[param_name] = instance
                                                found = True
                                                break
                                            else:
                                                # It's already an instance or factory
                                                params[param_name] = other_impl
                                                found = True
                                                break
                                
                                if not found:
                                    named_dep_result = self.resolve_named(service_type, name, _resolving)
                                    if named_dep_result.is_success:
                                        params[param_name] = named_dep_result.unwrap()
                                    else:
                                        return Failure(ServiceRegistrationError(
                                            f"Failed to resolve named dependency {param_name} for named service {name} of type {service_type.__name__}: {str(named_dep_result)}"
                                        ))
                            else:
                                # Check if we have a direct instance of this type first
                                if param_type in self._instances:
                                    # Direct instance found, use it
                                    params[param_name] = self._instances[param_type]
                                    continue
                                    
                                # Otherwise resolve normally
                                dep_result = self.resolve(param_type, _resolving)
                                if dep_result.is_success:
                                    params[param_name] = dep_result.unwrap()
                                else:
                                    return Failure(ServiceRegistrationError(
                                        f"Failed to resolve dependency {param_name} for {service_type.__name__}: {str(dep_result)}"
                                    ))
                        
                        # Create instance with dependencies
                        try:
                            instance = impl(**params)
                            return Success(instance)
                        except Exception as ex:
                            return Failure(ServiceRegistrationError(
                                f"Failed to create instance of {impl.__name__}: {str(ex)}"
                            ))
                    else:
                        # It's an instance
                        return Success(impl)
                else:
                    return Failure(ServiceRegistrationError(f"Invalid registration for named service {name}"))
            else:
                return Failure(ServiceRegistrationError(f"No registration found for named service {name}"))
        except Exception as e:
            return Failure(ServiceRegistrationError(f"Error resolving named service {name}: {str(e)}"))
        finally:
            _resolving.remove(service_type)
            
    def resolve(self, service_type: type[Any], _resolving: set[type[Any]] | None = None) -> Result[Any, ServiceRegistrationError]:
        """
        Resolve a service instance.

        Args:
            service_type: The type of service to resolve
            _resolving: Set of currently resolving types (for circular dependency detection)

        Returns:
            Success with the resolved service or Failure with an error
        """
        if _resolving is None:
            _resolving = set()

        if service_type in _resolving:
            return Failure(ServiceRegistrationError(
                f"Circular dependency detected for {service_type.__name__}",
                code="DI-1003",
                reason="INTERNAL"
            ))

        _resolving.add(service_type)

        try:
            if service_type in self._instances:
                return Success(self._instances[service_type])

            if service_type not in self._registrations:
                if self._auto_register:
                    self._registrations[service_type] = service_type
                else:
                    return Failure(ServiceRegistrationError(f"No registration found for {service_type.__name__}"))

            impl = self._registrations[service_type]
            if isinstance(impl, type):
                return _create_service_instance(impl, self._registrations, self._instances, _resolving)
            elif callable(impl):
                result = impl()
                if isinstance(result, Result):
                    return result
                return Success(result)
            else:
                return Failure(ServiceRegistrationError(f"Invalid registration for {service_type.__name__}"))

        except Exception as e:
            return Failure(ServiceRegistrationError(f"Error resolving {service_type.__name__}: {str(e)}"))
        finally:
            _resolving.remove(service_type)

@runtime_checkable
class CompositeService(Protocol[TComposite]):
    """
    Protocol for composite services.

    Example:
        ```python
        class MyCompositeService(CompositeService[MyService]):
            def compose(self, services: list[Any]) -> MyService:
                return MyService(services)
        ```
    """
    def compose(self, services: list[Any]) -> TComposite:
        """
        Compose multiple services into a single service.

        Args:
            services: The services to compose

        Returns:
            The composed service

        Example:
            ```python
            def compose(self, services: list[Any]) -> MyService:
                return MyService(services)
            ```
        """
        ...

@runtime_checkable
class AggregateService(Protocol[TAggregate]):
    """
    Protocol for aggregate services.

    Example:
        ```python
        class MyAggregateService(AggregateService[MyService]):
            def aggregate(self, services: list[Any]) -> MyService:
                return MyService(services)
        ```
    """
    def aggregate(self, services: list[Any]) -> TAggregate:
        """
        Aggregate multiple services into a single service.

        Args:
            services: The services to aggregate

        Returns:
            The aggregated service

        Example:
            ```python
            def aggregate(self, services: list[Any]) -> MyService:
                return MyService(services)
            ```
        """
        ...

@runtime_checkable
class ServiceChain(Protocol):
    """
    Protocol for service chains.

    Example:
        ```python
        class MyServiceChain(ServiceChain):
            def next(self, service: Any) -> None:
                self._services.append(service)

            def execute(self, *args: Any, **kwargs: Any) -> Any:
                result = None
                for service in self._services:
                    result = service(*args, **kwargs)
                return result
        ```
    """
    def next(self, service: Any) -> None:
        """
        Add a service to the chain.

        Args:
            service: The service to add

        Example:
            ```python
            def next(self, service: Any) -> None:
                self._services.append(service)
            ```
        """
        ...

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the service chain.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the chain execution

        Example:
            ```python
            def execute(self, *args: Any, **kwargs: Any) -> Any:
                result = None
                for service in self._services:
                    result = service(*args, **kwargs)
                return result
            ```
        """
        ...

@dataclass
class RetryPolicy:
    """
    Configuration for service retry behavior.

    Example:
        ```python
        policy = RetryPolicy(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            timeout=30.0
        )
        ```
    """
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 10.0  # seconds
    backoff_factor: float = 2.0
    timeout: float = 30.0  # seconds

@dataclass
class CircuitBreakerPolicy:
    """
    Configuration for circuit breaker behavior.

    Example:
        ```python
        policy = CircuitBreakerPolicy(
            failure_threshold=5,
            reset_timeout=60.0,
            half_open_timeout=10.0
        )
        ```
    """
    failure_threshold: int = 5
    reset_timeout: float = 60.0  # seconds
    half_open_timeout: float = 10.0  # seconds

def _is_abstract_or_protocol(t: type[Any]) -> bool:
    """
    Check if a type is abstract or a protocol.

    Args:
        t: The type to check

    Returns:
        True if the type is abstract or a protocol, False otherwise

    Example:
        ```python
        is_abstract = _is_abstract_or_protocol(MyAbstractClass)
        is_protocol = _is_abstract_or_protocol(MyProtocol)
        ```
    """
    return inspect.isabstract(t) or hasattr(t, "_is_protocol")

def _is_concrete_type(t: type[Any]) -> bool:
    """
    Check if a type is concrete and not abstract.

    Args:
        t: The type to check

    Returns:
        True if the type is concrete, False otherwise

    Example:
        ```python
        is_concrete = _is_concrete_type(MyConcreteClass)
        ```
    """
    # Check if it's an interface/protocol
    if hasattr(t, "_is_protocol"):
        return False
    # Check if it's abstract
    if inspect.isabstract(t):
        return False
    # Check if it's a framework service
    if hasattr(t, "__framework_service__") and getattr(
        t, "__framework_service__", False
    ):
        return True
    # Check if it has an __init__ method that can be called
    if not hasattr(t, "__init__"):
        return False
    # Check if it has any abstract methods
    try:
        if any(getattr(getattr(t, name), "__isabstractmethod__", False) for name in dir(t)):
            return False
    except Exception:
        return False
    return True

def _resolve_param_dependency(
    resolver: Any,
    param_name: str,
    registered_type: type[Any],
    impl: type[Any],
    params: dict[str, Any],
    _resolving: set[type[Any]]
) -> Result[Any, ServiceRegistrationError]:
    """
    Resolve a parameter dependency.

    Args:
        resolver: The service resolver or dictionary of instances
        param_name: Name of the parameter
        registered_type: The type to resolve
        impl: The implementation type
        params: Existing parameters
        _resolving: Set of currently resolving types

    Returns:
        Success with the resolved value or Failure with an error

    Example:
        ```python
        result = _resolve_param_dependency(
            resolver,
            "dependency",
            IDependency,
            MyService,
            {},
            set()
        )
        if result.is_success:
            value = result.unwrap()
        ```
    """
    try:
        # Handle different resolver types
        if isinstance(resolver, ServiceResolver):
            # If we have a proper ServiceResolver
            if registered_type in resolver._instances:
                return Success(resolver._instances[registered_type])
            
            # Try resolving through resolver
            return resolver.resolve(registered_type, _resolving=_resolving)
        elif isinstance(resolver, dict):
            # If resolver is actually a dictionary of instances
            if registered_type in resolver:
                return Success(resolver[registered_type])
        
        # Try to resolve by parameter name as a last resort
        for inst_type, inst in getattr(resolver, '_instances', {}).items():
            if inst_type.__name__.lower() == param_name.lower():
                return Success(inst)
            
        # Fall back to looking for existing params
        if param_name in params:
            return Success(params[param_name])
            
        return Failure(
            ServiceRegistrationError(
                f"Could not resolve dependency {param_name} of type {registered_type.__name__} for {impl.__name__}"
            )
        )
    except Exception as e:
        return Failure(
            ServiceRegistrationError(
                f"Failed to resolve dependency {param_name} for {impl.__name__}: {str(e)}"
            )
        )

def _find_registered_type(resolver: ServiceResolver, param_type: type[Any], impl: type[Any]) -> type[Any] | None:
    """
    Find a registered type that matches the parameter type.
    """
    def _is_same_type(a: type[Any], b: type[Any]) -> bool:
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


def _validate_constructor_params(
    impl: type[Any],
    params: dict[str, Any],
    resolver: ServiceResolver,
    _resolving: set[type[Any]]
) -> Result[dict[str, Any], ServiceRegistrationError]:
    """
    Validate constructor parameters.

    Args:
        impl: The implementation type
        params: The parameters to validate
        resolver: The service resolver
        _resolving: Set of currently resolving types

    Returns:
        Success with validated parameters or Failure with an error

    Example:
        ```python
        result = _validate_constructor_params(
            MyService,
            {"param1": value1},
            resolver,
            set()
        )
        if result.is_success:
            validated_params = result.value
        ```
    """
    try:
        # Get constructor signature
        sig = inspect.signature(impl.__init__)
        validated_params = {}

        # Check each parameter
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Skip if parameter is already provided
            if param_name in params:
                validated_params[param_name] = params[param_name]
                continue

            # Get parameter type
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                if param.default == inspect.Parameter.empty:
                    return Failure(
                        ServiceRegistrationError(
                            f"Parameter '{param_name}' in {impl.__name__} has no type annotation"
                        )
                    )
                validated_params[param_name] = param.default
                continue

            # For parameter resolution, try to find a match based on either type or name
            # First check if we already have a registered instance of this exact type
            try:
                if isinstance(resolver, ServiceResolver):
                    # We have a proper ServiceResolver object
                    instance_result = resolver.resolve(param_type, _resolving)
                    if instance_result.is_success:
                        validated_params[param_name] = instance_result.unwrap()
                        continue
            except Exception:
                # Failed to resolve via the resolver, will fall through to dependency resolution
                pass
                
            # If no instance found, resolve dependency normally
            result = _resolve_param_dependency(
                resolver, param_name, param_type, impl, params, _resolving
            )
            if isinstance(result, Failure):
                return result
            validated_params[param_name] = result.unwrap()

        return Success(validated_params)
    except Exception as e:
        return Failure(
            ServiceRegistrationError(
                f"Failed to validate constructor parameters for {impl.__name__}: {str(e)}"
            )
        )

def _create_service_instance(
    impl: type[Any],
    params: dict[str, Any],
    resolver: ServiceResolver,
    _resolving: set[type[Any]]
) -> Result[Any, ServiceRegistrationError]:
    """
    Create a service instance.

    Args:
        impl: The implementation type
        params: The parameters to use
        resolver: The service resolver
        _resolving: Set of currently resolving types

    Returns:
        Success with the created instance or Failure with an error

    Example:
        ```python
        result = _create_service_instance(
            MyService,
            {"param1": value1},
            resolver,
            set()
        )
        if result.is_success:
            instance = result.value
        ```
    """
    try:
        # Validate parameters
        result = _validate_constructor_params(impl, params, resolver, _resolving)
        if isinstance(result, Failure):
            return result

        # Create instance
        instance = impl(**result.unwrap())
        return Success(instance)
    except Exception as e:
        return Failure(
            ServiceRegistrationError(
                f"Failed to create instance of {impl.__name__}: {str(e)}"
            )
        )

def _validate_service_implementation(
    impl: type[Any],
    resolver: ServiceResolver,
    _resolving: set[type[Any]]
) -> Result[None, ServiceRegistrationError]:
    """
    Validate a service implementation.

    Args:
        impl: The implementation type
        resolver: The service resolver
        _resolving: Set of currently resolving types

    Returns:
        Success if validation passes or Failure with an error

    Example:
        ```python
        result = _validate_service_implementation(
            MyService,
            resolver,
            set()
        )
        if result.is_success:
            # Implementation is valid
            pass
        ```
    """
    try:
        # Check if type is concrete
        if not _is_concrete_type(impl):
            return Failure(
                ServiceRegistrationError(
                    f"Type {impl.__name__} is not a concrete type"
                )
            )

        # Try to create instance
        result = _create_service_instance(impl, {}, resolver, _resolving)
        if isinstance(result, Failure):
            return result

        return Success(None)
    except Exception as e:
        return Failure(
            ServiceRegistrationError(
                f"Failed to validate service implementation {impl.__name__}: {str(e)}"
            )
        )

class ServiceProvider(Generic[TService]):
    """Service provider that manages service lifetimes and dependencies.
    
    Args:
        collection: A ServiceCollection containing the services to manage
        
    Attributes:
        _collection: The service collection containing registered services
        _resolver: The service resolver for resolving dependencies
        _disposal_order: The order in which services should be disposed
        _lifecycle_queue: Queue of services that implement ServiceLifecycleProtocol
        _metrics: Optional metrics collector
        _circuit_breakers: Optional circuit breaker manager
        _fallback_services: Optional fallback service registry
        _retry_policies: Optional retry policy manager
    """

    def __init__(self, collection: "ServiceCollection[TService]") -> None:
        """
        Initialize the service provider.
        
        Args:
            collection: A ServiceCollection containing the services to manage
        """
        self._collection = collection
        # Convert collection registrations to the format expected by ServiceResolver
        resolver_registrations = {}
        for service_type, registration in collection._registrations.items():
            if hasattr(registration, 'implementation'):
                resolver_registrations[service_type] = registration.implementation
            else:
                # If the registration format is unexpected, use the registration directly
                resolver_registrations[service_type] = registration
                
        self._resolver = ServiceResolver(
            registrations=resolver_registrations,
            instances=collection._instances,
            named_registrations=collection._named_registrations,
            auto_register=False,
        )
        self._disposal_order: list[type[TService]] = []
        self._lifecycle_queue: list[TService] = []
        self._shutdown = False
        self._initialized = False  
        self._metrics: MetricsCollector | None = None
        self._circuit_breakers: CircuitBreakerManager | None = None
        self._fallback_services: FallbackServiceRegistry | None = None
        self._retry_policies: RetryPolicyManager | None = None
        self._logger = logging.getLogger(__name__ + ".ServiceProvider")

    def resolve(self, service_type: type[TService], name: str | None = None) -> Result[TService, ServiceRegistrationError]:
        """
        Resolve a service instance.

        Args:
            service_type: The type of service to resolve
            name: Optional name for named service resolution

        Returns:
            A Result containing the service instance or an error

        Example:
            ```python
            # Resolve default service
            result = provider.resolve(IMyService)
            if result.is_success:
                service = result.unwrap()
            
            # Resolve named service
            result = provider.resolve(IMyService, name="my_named_service")
            if result.is_success:
                service = result.unwrap()
            ```
        """
        try:
            if name:
                return self._resolver.resolve_named(service_type, name)
            else:
                return self._resolver.resolve(service_type)
        except Exception as e:
            return Failure(ServiceRegistrationError(
                f"Failed to resolve service {service_type.__name__}: {str(e)}"
            ))

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        self.shutdown()

    def get_services(self, service_type: type[TService]) -> list[TService]:
        """
        Get all service instances of a specific type.

        Args:
            service_type: The type of service to get

        Returns:
            List of service instances

        Example:
            ```python
            services = provider.get_services(IMyService)
            ```
        """
        services: list[TService] = []
        
        # Get all registered services of this type
        if service_type in self._collection._registrations:
            for registration in self._collection._registrations[service_type]:
                result = self.resolve(service_type, registration.name)
                if result.is_success:
                    services.append(result.unwrap())
        
        return services

    def initialize(self) -> None:
        """
        Initialize all services.

        This method will initialize all services in the collection that
        require initialization.

        Raises:
            ServiceStateError: If the provider is already initialized or shutdown

        Example:
            ```python
            await provider.initialize()
            ```
        """
        if self._shutdown:
            raise ServiceStateError("Service provider is shutdown")

        if hasattr(self, '_initialized') and self._initialized:
            raise ServiceStateError("Service provider already initialized")

        self._initialized = True
        self._lifecycle_queue = []

        # Initialize services in reverse disposal order
        for service_type in reversed(self._disposal_order):
            service = self.resolve(service_type)
            if isinstance(service, ServiceLifecycleProtocol):
                self._lifecycle_queue.append(service)

    def shutdown(self) -> None:
        """
        Shutdown all services.

        This method will shutdown all services in the collection that
        require cleanup.

        Raises:
            ServiceStateError: If the provider is not initialized or already shutdown

        Example:
            ```python
            provider.shutdown()
            ```
        """
        if self._shutdown:
            raise ServiceStateError("Service provider already shutdown")

        if not hasattr(self, '_initialized') or not self._initialized:
            raise ServiceStateError("Service provider not initialized")

        # Shutdown services in disposal order
        for service_type in self._disposal_order:
            service = self.resolve(service_type)
            if isinstance(service, ServiceLifecycleProtocol):
                service.shutdown()

        self._shutdown = True

    async def initialize(self) -> Result[None, ServiceStateError]:
        """
        Initialize all services.

        This method will initialize all services in the collection that
        require initialization.

        Raises:
            ServiceStateError: If the provider is already initialized or shutdown

        Example:
            ```python
            await provider.initialize()
            ```
        """
        if self._initialized:
            return Failure(ServiceStateError("Service provider is already initialized"))
        if self._shutdown:
            return Failure(ServiceStateError("Service provider is shutdown"))

        try:
            # Get all registered services that implement ServiceLifecycleProtocol and are singletons
            for service_type, registration in self._collection._registrations.items():
                if not isinstance(registration, _ServiceRegistration):
                    continue
                
                if registration.scope != ServiceScope.SINGLETON:
                    continue
                
                if not issubclass(registration.implementation, ServiceLifecycleProtocol):
                    continue
                
                result = self.resolve(service_type)
                if result.is_success:
                    service = result.unwrap()
                    if inspect.iscoroutinefunction(service.initialize):
                        await service.initialize()
                    else:
                        service.initialize()
            self._initialized = True
            return Success(None)
        except Exception as e:
            self._logger.error(f"Failed to initialize services: {str(e)}")
            return Failure(ServiceStateError(f"Failed to initialize services: {str(e)}"))

    def register_retry_policy(
        self,
        service_type: type[TService],
        policy: RetryPolicy
    ) -> None:
        """
        Register a retry policy for a service.

        Args:
            service_type: The type of service to register the policy for
            policy: The retry policy to register

        Example:
            ```python
            policy = RetryPolicy(
                max_attempts=3,
                initial_delay=1.0,
                max_delay=10.0,
                backoff_factor=2.0,
                timeout=30.0
            )
            provider.register_retry_policy(IMyService, policy)
            ```
        """
        if not hasattr(service_type, "__requires_retry__"):
            raise ServiceRegistrationError(
                f"Service {service_type.__name__} does not support retry policies"
            )
        self._collection.register_retry_policy(service_type, policy)

    def register_circuit_breaker(
        self,
        service_type: type[TService],
        policy: CircuitBreakerPolicy
    ) -> None:
        """
        Register a circuit breaker for a service.

        Args:
            service_type: The type of service to register the circuit breaker for
            policy: The circuit breaker policy to register

        Example:
            ```python
            policy = CircuitBreakerPolicy(
                failure_threshold=5,
                reset_timeout=60.0,
                half_open_timeout=10.0
            )
            provider.register_circuit_breaker(IMyService, policy)
            ```
        """
        if not hasattr(service_type, "__requires_circuit_breaker__"):
            raise ServiceRegistrationError(
                f"Service {service_type.__name__} does not support circuit breakers"
            )
        self._collection.register_circuit_breaker(service_type, policy)

    def register_fallback(
        self,
        service_type: type[TService],
        fallback_type: type[TService]
    ) -> None:
        """
        Register a fallback service.

        Args:
            service_type: The type of service to register the fallback for
            fallback_type: The type of fallback service to register

        Example:
            ```python
            provider.register_fallback(IMyService, MyFallbackService)
            ```
        """
        if not hasattr(service_type, "__requires_fallback__"):
            raise ServiceRegistrationError(
                f"Service {service_type.__name__} does not support fallbacks"
            )
        self._collection.register_fallback(service_type, fallback_type)

    def _update_metrics(self, service_type: type[Any], success: bool, duration: float) -> None:
        """
        Update service metrics.

        Args:
            service_type: The type of service
            success: Whether the call was successful
            duration: The duration of the call in seconds
        """
        metrics = self._metrics[service_type]
        metrics["calls"] += 1
        if not success:
            metrics["failures"] += 1
        metrics["total_time"] += duration
        metrics["last_call"] = datetime.now(UTC)

    def _check_circuit_breaker(self, service_type: type[Any]) -> bool:
        """
        
        Args:
            service_type: The type of service to check

        Returns:
            True if the circuit is closed (service can be called), False if open
        """
        if service_type not in self._circuit_breakers:
            return True

        circuit = self._circuit_breakers[service_type]
        policy = circuit["policy"]
        now = datetime.now(UTC)

        if circuit["state"] == "open":
            if circuit["last_failure"] and (now - circuit["last_failure"]).total_seconds() > policy.reset_timeout:
                circuit["state"] = "half-open"
                circuit["half_open_time"] = now
                return True
            return False

        if circuit["state"] == "half-open":
            if circuit["half_open_time"] and (now - circuit["half_open_time"]).total_seconds() > policy.half_open_timeout:
                circuit["state"] = "closed"
                circuit["failures"] = 0
                return True
            return False

        return True

    def _update_circuit_breaker(self, service_type: type[Any], success: bool) -> None:
        """
        Update a service's circuit breaker state.

        Args:
            service_type: The type of service
            success: Whether the call was successful
        """
        if service_type not in self._circuit_breakers:
            return

        circuit = self._circuit_breakers[service_type]
        policy = circuit["policy"]

        if not success:
            circuit["failures"] += 1
            circuit["last_failure"] = datetime.now(UTC)
            if circuit["failures"] >= policy.failure_threshold:
                circuit["state"] = "open"
        else:
            if circuit["state"] == "half-open":
                circuit["state"] = "closed"
                circuit["failures"] = 0

    async def _execute_with_resilience(
        self,
        service_type: type[Any],
        operation: Callable[[], Any],
        retry_policy: RetryPolicy | None = None,
    ) -> Any:
        """
        Execute an operation with resilience features.

        Args:
            service_type: The type of service
            operation: The operation to execute
            retry_policy: Optional retry policy to use

        Returns:
            The result of the operation

        Raises:
            ServiceResilienceError: If all retry attempts fail
        """
        if not self._check_circuit_breaker(service_type):
            if service_type in self._fallback_services:
                fallback_type = self._fallback_services[service_type]
                return await self._execute_with_resilience(fallback_type, operation, retry_policy)
            raise ServiceResilienceError(
                f"Circuit breaker is open for service {service_type.__name__}"
            )

        policy = retry_policy or self._retry_policies.get(service_type)
        if not policy:
            start_time = time.time()
            try:
                result = operation()
                self._update_metrics(service_type, True, time.time() - start_time)
                self._update_circuit_breaker(service_type, True)
                return result
            except Exception as e:
                self._update_metrics(service_type, False, time.time() - start_time)
                self._update_circuit_breaker(service_type, False)
                raise

        attempt = 0
        delay = policy.initial_delay
        start_time = time.time()

        while attempt < policy.max_attempts:
            try:
                result = operation()
                self._update_metrics(service_type, True, time.time() - start_time)
                self._update_circuit_breaker(service_type, True)
                return result
            except Exception as e:
                attempt += 1
                if attempt == policy.max_attempts:
                    self._update_metrics(service_type, False, time.time() - start_time)
                    self._update_circuit_breaker(service_type, False)
                    raise ServiceResilienceError(
                        f"Operation failed after {attempt} attempts: {str(e)}",
                        reason=str(e),
                    ) from e

                if time.time() - start_time > policy.timeout:
                    raise ServiceResilienceError(
                        f"Operation timed out after {time.time() - start_time:.2f} seconds"
                    )

                await asyncio.sleep(min(delay, policy.max_delay))
                delay *= policy.backoff_factor

    def get_service_metrics(self) -> dict[type[Any], dict[str, Any]]:
        """
        Get metrics for all services.

        Returns:
            A dictionary mapping service types to their metrics
        """
        return dict(self._metrics)

    def get_circuit_breaker_state(self, service_type: type[Any]) -> dict[str, Any]:
        """
        Get the current state of a service's circuit breaker.

        Args:
            service_type: The type of service

        Returns:
            A dictionary containing the circuit breaker state
        """
        if service_type not in self._circuit_breakers:
            return {"state": "not_configured"}
        return dict(self._circuit_breakers[service_type])

    def can_resolve(self, service_type: type[Any], name: str | None = None) -> bool:
        """
        Check if a service can be resolved.

        Args:
            service_type: The type of service to check
            name: Optional name for named service registration

        Returns:
            True if the service can be resolved, False otherwise
        """
        try:
            if name:
                registration = self._collection.get_named_registration(name)
                if registration is None:
                    return False
                return self._resolver.can_resolve(registration.service_type)
            return self._resolver.can_resolve(service_type)
        except Exception:
            return False

    def get_all_services(self) -> list[type[Any]]:
        """
        Get all registered service types.

        Returns:
            A list of registered service types
        """
        return list(self._collection._registrations.keys())

    def create_scope(self, scope_id: str | None = None) -> Result["Scope[Any]", ServiceStateError]:
        """
        Create a new service scope for resolving scoped services.

        Args:
            scope_id: Optional identifier for the scope
        Returns:
            Result containing a Scope instance or a ServiceStateError
        """
        # Guard: Check for broken or missing state
        if not hasattr(self, '_collection') or self._collection is None:
            return Failure(ServiceStateError("DI-0016", "ServiceProvider collection is None or missing."))
        if not hasattr(self._collection, '_registrations') or self._collection._registrations is None:
            return Failure(ServiceStateError("DI-0016", "ServiceProvider registrations are None or missing."))
        try:
            from uno.infrastructure.di.service_scope import Scope
            scope = Scope(self, self._collection, scope_id)
            return Success(scope)
        except Exception as e:
            return Failure(ServiceStateError(f"Failed to create scope: {e}"))

    async def async_create_scope(self, scope_id: str | None = None) -> Result["Scope[Any]", ServiceStateError]:
        """
        Asynchronously create a new service scope for resolving scoped services.

        Args:
            scope_id: Optional identifier for the scope
        Returns:
            Result containing a Scope instance or a ServiceStateError
        """
        try:
            from uno.infrastructure.di.service_scope import Scope
            scope = Scope(self, self._collection, scope_id)
            return Success(scope)
        except Exception as e:
            return Failure(ServiceStateError(f"Failed to create async scope: {e}"))

    def _build_disposal_order(self) -> None:
        """
        Build the disposal order based on service dependencies.
        Services that depend on other services will be disposed after their dependencies.
        """
        # Build dependency graph
        graph: dict[type[Any], set[type[Any]]] = defaultdict(set)
        for service_type, registration in self._collection._registrations.items():
            if isinstance(registration.implementation, type):
                # Get constructor parameters
                params = inspect.signature(registration.implementation.__init__).parameters
                for param_name, param in params.items():
                    if param_name != "self":
                        param_type = param.annotation
                        if param_type != inspect._empty:
                            # Find registered type that matches parameter type
                            registered_type = _find_registered_type(
                                self._resolver, param_type, registration.implementation
                            )
                            if registered_type:
                                graph[service_type].add(registered_type)

        # Topological sort for disposal order
        visited: set[type[Any]] = set()
        temp: set[type[Any]] = set()
        order: list[type[Any]] = []

        def visit(node: type[Any]) -> None:
            if node in temp:
                raise CircularDependencyError(
                    f"Circular dependency detected involving {node.__name__}"
                )
            if node in visited:
                return
            temp.add(node)
            for dependency in graph[node]:
                visit(dependency)
            temp.remove(node)
            visited.add(node)
            order.append(node)

        for service_type in self._collection._registrations:
            if service_type not in visited:
                visit(service_type)

        # Update disposal order
        self._disposal_order = [
            service
            for service in self._lifecycle_queue
            if service.__class__ in order
        ]
        self._disposal_order.sort(
            key=lambda s: order.index(s.__class__),
            reverse=True
        )

    def register_lifecycle_service(self, service_type: type) -> None:
        """
        Explicitly register a service type for lifecycle management.
        The service must be registered as a singleton and implement ServiceLifecycle.

        Args:
            service_type: The type of service to register

        Raises:
            ValueError: If the service is not registered
            TypeError: If the service implementation is not a type or does not implement ServiceLifecycle
        """
        # Find the registration
        registration = self._collection._registrations.get(service_type)
        if registration is None:
            raise ValueError(f"Service {service_type.__name__} is not registered.")
        if not isinstance(registration.implementation, type):
            raise TypeError(f"Service {service_type.__name__} implementation is not a type.")
        if not issubclass(registration.implementation, ServiceLifecycleProtocol):
            raise TypeError(f"Service {service_type.__name__} does not implement ServiceLifecycle.")
        if registration.scope != ServiceScope.SINGLETON:
            raise TypeError(
                f"Service {service_type.__name__} implements ServiceLifecycle but is not registered as a singleton. Lifecycle services must be singleton."
            )
        # Get the instance (will instantiate singleton if needed)
        service_instance = self.get_service(service_type).value
        if service_instance not in self._lifecycle_queue:
            self._lifecycle_queue.append(service_instance)
            self._build_disposal_order()

    def register_health_check(self, service_type: type[Any], check: Callable[[], bool]) -> None:
        """
        Register a health check for a service.

        Args:
            service_type: The type of service to check
            check: The health check function
        """
        self._health_checks[service_type] = check

    async def check_health(self) -> dict[type[Any], bool]:
        """
        Check the health of all services with registered health checks.

        Returns:
            A dictionary mapping service types to their health status

        Raises:
            ServiceHealthError: If a health check fails
        """
        results: dict[type[Any], bool] = {}
        for service_type, check in self._health_checks.items():
            try:
                results[service_type] = check()
            except Exception as e:
                raise ServiceHealthError(
                    f"Health check failed for service {service_type.__name__}: {str(e)}",
                    reason=str(e),
                ) from e
        return results

    async def configure_services(self, services: "ServiceCollection[TService]") -> None:
        """
        Configure additional services in the provider.

        Args:
            services: A ServiceCollection containing additional services to register

        Raises:
            ServiceInitializationError: If service configuration fails
        """
        try:
            self._collection._registrations.update(services._registrations)
            self._collection._instances.update(services._instances)
            self._collection._named_registrations.update(services._named_registrations)
            
            # Initialize any new singleton services
            for service_type, registration in services._registrations.items():
                if registration.scope == ServiceScope.SINGLETON:
                    service = self.get_service(service_type).value  # Always instantiate
                    if isinstance(service, ServiceLifecycleProtocol):
                        if service not in self._lifecycle_queue:
                            self._lifecycle_queue.append(service)
                        init_method = getattr(service, "initialize", None)
                        if init_method:
                            if inspect.iscoroutinefunction(init_method):
                                await init_method()
                            else:
                                init_method()
            self._resolver = ServiceResolver(
                registrations=self._collection._registrations,
                instances=self._collection._instances,
                auto_register=False,
            )
            self._build_disposal_order()
        except Exception as e:
            raise ServiceCompositionError(
                f"Service chain execution failed: {str(e)}",
                reason=str(e),
            ) from e
        return result

    def get_health(self) -> dict[str, ServiceHealth]:
        """
        Get the health status of all services.

        Returns:
            A dictionary mapping service types to their health information

        Example:
            ```python
            health = provider.get_health()
            for service_type, health_info in health.items():
                print(f"{service_type.__name__}: {health_info.status}")
            ```
        """
        health: dict[str, ServiceHealth] = {}
        for service_type in self._collection.get_services():
            if hasattr(service_type, "__requires_health_check__"):
                service = self.get_service(service_type)
                if hasattr(service, "get_health"):
                    health[service_type.__name__] = service.get_health()
        return health

    def get_state(self) -> dict[str, ServiceState]:
        """
        Get state information for all services.

        Returns:
            A dictionary mapping service types to their state information

        Example:
            ```python
            states = provider.get_state()
            for service_type, state in states.items():
                print(f"{service_type.__name__}: {state}")
            ```
        """
        states: dict[str, ServiceState] = {}
        for service_type in self._collection.get_services():
            if hasattr(service_type, "__requires_state__"):
                service = self.get_service(service_type)
                if hasattr(service, "get_state"):
                    states[service_type.__name__] = service.get_state()
        return states

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        """
        Get metrics for all services.

        Returns:
            A dictionary mapping service types to their metrics

        Example:
            ```python
            metrics = provider.get_metrics()
            for service_type, service_metrics in metrics.items():
                print(f"{service_type.__name__}: {service_metrics}")
            ```
        """
        metrics: dict[str, dict[str, Any]] = {}
        for service_type in self._collection.get_services():
            if hasattr(service_type, "__requires_metrics__"):
                service = self.get_service(service_type)
                if hasattr(service, "get_metrics"):
                    metrics[service_type.__name__] = service.get_metrics()
        return metrics

class ServiceChainImpl:
    """
    Implementation of the ServiceChain protocol.
    """

    def __init__(self) -> None:
        """Initialize a new ServiceChainImpl instance."""
        self._services: list[Any] = []

    def next(self, service: Any) -> None:
        """
        Add a service to the chain.

        Args:
            service: The service to add
        """
        self._services.append(service)

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the service chain.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the chain execution
        """
        result = None
        for service in self._services:
            try:
                if inspect.iscoroutinefunction(service):
                    result = await service(*args, **kwargs)
                else:
                    result = service(*args, **kwargs)
                args = (result,)
                kwargs = {}
            except Exception as e:
                raise ServiceCompositionError(
                    f"Service chain execution failed: {str(e)}",
                    reason=str(e),
                ) from e
        return result

__all__ = [
    "ServiceProvider",
    "RetryPolicy",
    "CircuitBreakerPolicy",
    "CompositeService",
    "AggregateService",
    "ServiceChain",
    "TService",
    "TImplementation",
    "TFactory",
    "TEntity",
    "TQuery",
    "TResult",
    "TValidator",
    "TInterceptor",
    "TMiddleware",
    "TContract",
    "TComposite",
    "TAggregate"
]
