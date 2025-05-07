"""
Decorators for Uno DI system.

This module provides decorators for registering services and components with the DI container.
All dependencies must be passed explicitly from the composition root.
"""

from __future__ import annotations

from typing import Type, TypeVar, Any, Callable, Optional, Dict, Set, List, cast, get_type_hints, get_origin, get_args, Generic, Protocol, runtime_checkable, Union, Awaitable, TypeAlias, Tuple
import inspect
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum, auto
from datetime import datetime
from collections import defaultdict
import re
from packaging import version

from uno.infrastructure.di.service_scope import ServiceScope
from uno.infrastructure.di.interfaces import (
    ServiceLifecycleProtocol,
    ServiceEventHandlerProtocol,
    ServiceEventEmitterProtocol,
    CompositeServiceProtocol,
    AggregateServiceProtocol,
    ServiceHealthCheckProtocol,
    ServiceConstraintValidatorProtocol,
    ServiceInterceptorProtocol,
    ServiceState,
    ServiceHealth
)
from uno.infrastructure.di.errors import (
    ServiceRegistrationError,
    ServiceValidationError,
    ServiceConfigurationError,
    ServiceLifecycleError,
    ServiceConstraintError,
    ServiceVersionError,
    ServiceEventError,
)

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])
TEntity = TypeVar("TEntity", bound=Any)
TQuery = TypeVar("TQuery", bound=Any)
TResult = TypeVar("TResult", bound=Any)
TOptions = TypeVar("TOptions", bound=Any)
TNext = TypeVar("TNext", bound=Any)
TComposite = TypeVar("TComposite", bound=Any)
TAggregate = TypeVar("TAggregate", bound=Any)
TEvent = TypeVar("TEvent", bound=Any)

class ServiceCategory(Enum):
    """
    Categories for services.

    Example:
        ```python
        @service(category=ServiceCategory.APPLICATION)
        class MyService:
            pass
        ```
    """
    APPLICATION = auto()
    FRAMEWORK = auto()
    INFRASTRUCTURE = auto()
    DOMAIN = auto()

class ServiceConstraint(Enum):
    """
    Service constraint types.

    Example:
        ```python
        @service(constraints={ServiceConstraint.SINGLETON_DEPENDENCY})
        class MyService:
            pass
        ```
    """
    SINGLETON_DEPENDENCY = auto()
    SCOPED_DEPENDENCY = auto()
    TRANSIENT_DEPENDENCY = auto()
    REQUIRED_DEPENDENCY = auto()
    OPTIONAL_DEPENDENCY = auto()
    INTERFACE_IMPLEMENTATION = auto()
    LIFECYCLE_MANAGEMENT = auto()
    HEALTH_CHECK = auto()
    CONFIGURATION = auto()

class ServiceEventType(Enum):
    """
    Service event types.

    Example:
        ```python
        @service(event_handlers=[MyEventHandler(ServiceEventType.INITIALIZED)])
        class MyService:
            pass
        ```
    """
    INITIALIZED = auto()
    STARTED = auto()
    PAUSED = auto()
    RESUMED = auto()
    STOPPED = auto()
    ERROR = auto()
    HEALTH_CHANGED = auto()
    STATE_CHANGED = auto()
    CONFIGURATION_CHANGED = auto()

@dataclass
class ServiceVersion:
    """
    Service version information.

    Example:
        ```python
        version = ServiceVersion(1, 0, 0, prerelease="beta", build="123")
        print(version)  # "1.0.0-beta+123"
        ```
    """
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """
        Get the string representation of the version.

        Returns:
            The version string

        Example:
            ```python
            version = ServiceVersion(1, 0, 0, prerelease="beta", build="123")
            print(str(version))  # "1.0.0-beta+123"
            ```
        """
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version_str += f"-{self.prerelease}"
        if self.build:
            version_str += f"+{self.build}"
        return version_str

    @classmethod
    def parse(cls, version_str: str) -> ServiceVersion:
        """
        Parse a version string into a ServiceVersion object.

        Args:
            version_str: The version string to parse

        Returns:
            A ServiceVersion object

        Raises:
            ServiceVersionError: If the version string is invalid

        Example:
            ```python
            version = ServiceVersion.parse("1.0.0-beta+123")
            print(version.major)  # 1
            print(version.minor)  # 0
            print(version.patch)  # 0
            print(version.prerelease)  # "beta"
            print(version.build)  # "123"
            ```
        """
        try:
            v = version.parse(version_str)
            return cls(
                major=v.major,
                minor=v.minor,
                patch=v.micro,
                prerelease=str(v.pre) if v.pre else None,
                build=str(v.local) if v.local else None
            )
        except Exception as e:
            raise ServiceVersionError(f"Invalid version string: {version_str}") from e

@dataclass
class ServiceEvent:
    """
    Service event information.

    Example:
        ```python
        event = ServiceEvent(
            type=ServiceEventType.INITIALIZED,
            data={"status": "ok"},
            source="MyService"
        )
        ```
    """
    type: ServiceEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None

@dataclass
class ServiceOptions(Generic[TOptions]):
    """
    Base class for service options.

    Example:
        ```python
        @dataclass
        class MyServiceOptions(ServiceOptions[MyService]):
            max_retries: int = 3
            timeout: int = 30

            def validate(self) -> None:
                if self.max_retries < 0:
                    raise ValueError("max_retries must be non-negative")
                if self.timeout <= 0:
                    raise ValueError("timeout must be positive")
        ```
    """
    def validate(self) -> None:
        """
        Validate the options.
        Override this method to add validation logic.

        Example:
            ```python
            def validate(self) -> None:
                if self.max_retries < 0:
                    raise ValueError("max_retries must be non-negative")
            ```
        """
        pass

@dataclass
class ServiceMetadata:
    """
    Metadata for a service class.

    Example:
        ```python
        metadata = ServiceMetadata(
            scope=ServiceScope.SINGLETON,
            interface=IMyService,
            dependencies={IDependency1, IDependency2},
            category=ServiceCategory.APPLICATION,
            version=ServiceVersion(1, 0, 0)
        )
        ```
    """
    scope: ServiceScope = ServiceScope.TRANSIENT
    interface: Optional[type[Any]] = None
    dependencies: set[type[Any]] = field(default_factory=set)
    required_dependencies: set[type[Any]] = field(default_factory=set)
    optional_dependencies: set[type[Any]] = field(default_factory=set)
    validation_hooks: list[Callable[[type[Any]], None]] = field(default_factory=list)
    category: ServiceCategory = ServiceCategory.APPLICATION
    options_type: Optional[type[ServiceOptions[Any]]] = None
    configuration_keys: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    priority: int = 0
    is_async: bool = False
    requires_initialization: bool = False
    requires_cleanup: bool = False
    interceptors: list[ServiceInterceptorProtocol] = field(default_factory=list)
    health_check: Optional[ServiceHealthCheckProtocol] = None
    lifecycle: Optional[ServiceLifecycleProtocol] = None
    state: ServiceState = ServiceState.INITIALIZED
    health: ServiceHealth = field(default_factory=ServiceHealth)
    constraints: set[ServiceConstraint] = field(default_factory=set)
    composite: Optional[CompositeServiceProtocol] = None
    aggregate: Optional[AggregateServiceProtocol] = None
    constraint_validators: list[ServiceConstraintValidatorProtocol] = field(default_factory=list)
    version: Optional[ServiceVersion] = None
    event_handlers: list[ServiceEventHandlerProtocol] = field(default_factory=list)
    event_emitter: Optional[ServiceEventEmitterProtocol] = None

def service(
    interface: Optional[type[TService]] = None,
    scope: ServiceScope = ServiceScope.TRANSIENT,
    category: ServiceCategory = ServiceCategory.APPLICATION,
    options_type: Optional[type[ServiceOptions[Any]]] = None,
    configuration_keys: Optional[set[str]] = None,
    tags: Optional[set[str]] = None,
    priority: int = 0,
    is_async: bool = False,
    requires_initialization: bool = False,
    requires_cleanup: bool = False,
    interceptors: Optional[list[ServiceInterceptorProtocol]] = None,
    health_check: Optional[ServiceHealthCheckProtocol] = None,
    lifecycle: Optional[ServiceLifecycleProtocol] = None,
    constraints: Optional[set[ServiceConstraint]] = None,
    composite: Optional[CompositeServiceProtocol] = None,
    aggregate: Optional[AggregateServiceProtocol] = None,
    constraint_validators: Optional[list[ServiceConstraintValidatorProtocol]] = None,
    version: Optional[Union[str, ServiceVersion]] = None,
    event_handlers: Optional[list[ServiceEventHandlerProtocol]] = None,
    event_emitter: Optional[ServiceEventEmitterProtocol] = None,
) -> Callable[[type[TService]], type[TService]]:
    """
    Decorator for marking a class as a service.

    This decorator provides type safety, metadata, and validation capabilities.
    While services must be explicitly registered, this decorator helps ensure
    that the service meets certain requirements.

    Args:
        interface: Optional interface that the service must implement
        scope: The default scope for the service (default: TRANSIENT)
        category: The service category (default: APPLICATION)
        options_type: Optional type for service options
        configuration_keys: Optional set of configuration keys required by the service
        tags: Optional set of tags for the service
        priority: Service initialization priority (default: 0)
        is_async: Whether the service has async initialization (default: False)
        requires_initialization: Whether the service requires explicit initialization (default: False)
        requires_cleanup: Whether the service requires explicit cleanup (default: False)
        interceptors: Optional list of service interceptors
        health_check: Optional health check implementation
        lifecycle: Optional lifecycle management implementation
        constraints: Optional set of service constraints
        composite: Optional composite service implementation
        aggregate: Optional aggregate service implementation
        constraint_validators: Optional list of constraint validators
        version: Optional service version (string or ServiceVersion)
        event_handlers: Optional list of event handlers
        event_emitter: Optional event emitter

    Returns:
        A decorator function that marks a class as a service

    Raises:
        ServiceValidationError: If the service does not meet the requirements
        ServiceConfigurationError: If the service configuration is invalid
        ServiceLifecycleError: If the service lifecycle is invalid
        ServiceConstraintError: If service constraints are violated
        ServiceVersionError: If the service version is invalid
        ServiceEventError: If the service event configuration is invalid

    Example:
        ```python
        @service(
            interface=IMyService,
            scope=ServiceScope.SINGLETON,
            category=ServiceCategory.APPLICATION,
            version="1.0.0",
            requires_initialization=True
        )
        class MyService:
            def __init__(self, dependency: IDependency):
                self._dependency = dependency

            def initialize(self) -> None:
                self._dependency.setup()
        ```
    """
    def decorator(cls: type[TService]) -> type[TService]:
        """
        The actual decorator function.

        Args:
            cls: The class to decorate

        Returns:
            The decorated class

        Example:
            ```python
            @service(interface=IMyService)
            class MyService:
                pass
            ```
        """
        # Validate interface implementation
        if interface and not issubclass(cls, interface):
            raise ServiceValidationError(
                f"Service {cls.__name__} must implement interface {interface.__name__}"
            )

        # Get constructor parameters
        params = inspect.signature(cls.__init__).parameters
        dependencies: set[type[Any]] = set()
        required_dependencies: set[type[Any]] = set()
        optional_dependencies: set[type[Any]] = set()

        for param_name, param in params.items():
            if param_name == "self":
                continue

            param_type = param.annotation
            if param_type == inspect._empty:
                continue

            # Handle collection types (e.g., list[IService])
            origin = get_origin(param_type)
            if origin is list:
                args = get_args(param_type)
                if args:
                    param_type = args[0]

            dependencies.add(param_type)
            if param.default == inspect._empty:
                required_dependencies.add(param_type)
            else:
                optional_dependencies.add(param_type)

        # Parse version
        service_version: Optional[ServiceVersion] = None
        if version is not None:
            if isinstance(version, str):
                service_version = ServiceVersion.parse(version)
            else:
                service_version = version

        # Create metadata
        metadata = ServiceMetadata(
            scope=scope,
            interface=interface,
            dependencies=dependencies,
            required_dependencies=required_dependencies,
            optional_dependencies=optional_dependencies,
            category=category,
            options_type=options_type,
            configuration_keys=configuration_keys or set(),
            tags=tags or set(),
            priority=priority,
            is_async=is_async,
            requires_initialization=requires_initialization,
            requires_cleanup=requires_cleanup,
            interceptors=interceptors or [],
            health_check=health_check,
            lifecycle=lifecycle,
            constraints=constraints or set(),
            composite=composite,
            aggregate=aggregate,
            constraint_validators=constraint_validators or [],
            version=service_version,
            event_handlers=event_handlers or [],
            event_emitter=event_emitter,
        )

        # Add validation hooks
        def validate_constructor(cls: type[Any]) -> None:
            if not hasattr(cls, "__init__"):
                raise ServiceValidationError(
                    f"Service {cls.__name__} must have a constructor"
                )
            if len(inspect.signature(cls.__init__).parameters) < 2:
                raise ServiceValidationError(
                    f"Service {cls.__name__} constructor must accept dependencies"
                )

        def validate_interface(cls: type[Any]) -> None:
            if interface:
                for method_name in dir(interface):
                    if not method_name.startswith("_"):
                        if not hasattr(cls, method_name):
                            raise ServiceValidationError(
                                f"Service {cls.__name__} must implement {method_name} from {interface.__name__}"
                            )

        def validate_async(cls: type[Any]) -> None:
            if is_async:
                if not hasattr(cls, "initialize") or not inspect.iscoroutinefunction(getattr(cls, "initialize")):
                    raise ServiceValidationError(
                        f"Async service {cls.__name__} must implement async initialize method"
                    )

        def validate_cleanup(cls: type[Any]) -> None:
            if requires_cleanup:
                if not hasattr(cls, "cleanup"):
                    raise ServiceValidationError(
                        f"Service {cls.__name__} requires cleanup but does not implement cleanup method"
                    )

        def validate_lifecycle(cls: type[Any]) -> None:
            if lifecycle:
                if not isinstance(cls, ServiceLifecycleProtocol):
                    raise ServiceLifecycleError(
                        f"Service {cls.__name__} must implement ServiceLifecycle protocol"
                    )

        def validate_health_check(cls: type[Any]) -> None:
            if health_check:
                if not isinstance(cls, ServiceHealthCheckProtocol):
                    raise ServiceValidationError(
                        f"Service {cls.__name__} must implement ServiceHealthCheck protocol"
                    )

        def validate_composite(cls: type[Any]) -> None:
            if composite:
                if not isinstance(cls, CompositeServiceProtocol):
                    raise ServiceValidationError(
                        f"Service {cls.__name__} must implement CompositeService protocol"
                    )

        def validate_aggregate(cls: type[Any]) -> None:
            if aggregate:
                if not isinstance(cls, AggregateServiceProtocol):
                    raise ServiceValidationError(
                        f"Service {cls.__name__} must implement AggregateService protocol"
                    )

        def validate_constraints(cls: type[Any]) -> None:
            for validator in metadata.constraint_validators:
                try:
                    validator.validate(cls, dependencies)
                except Exception as e:
                    raise ServiceConstraintError(
                        f"Service {cls.__name__} failed constraint validation: {str(e)}"
                    ) from e

        def validate_event_handlers(cls: type[Any]) -> None:
            if event_handlers:
                for handler in event_handlers:
                    if not isinstance(handler, ServiceEventHandlerProtocol):
                        raise ServiceEventError(
                            f"Service {cls.__name__} has invalid event handler: {handler}"
                        )

        def validate_event_emitter(cls: type[Any]) -> None:
            if event_emitter and not isinstance(event_emitter, ServiceEventEmitterProtocol):
                raise ServiceEventError(
                    f"Service {cls.__name__} has invalid event emitter: {event_emitter}"
                )

        metadata.validation_hooks.extend([
            validate_constructor,
            validate_interface,
            validate_async,
            validate_cleanup,
            validate_lifecycle,
            validate_health_check,
            validate_composite,
            validate_aggregate,
            validate_constraints,
            validate_event_handlers,
            validate_event_emitter,
        ])

        # Run validation hooks
        for hook in metadata.validation_hooks:
            hook(cls)

        # Attach metadata to class
        setattr(cls, "__service_metadata__", metadata)

        return cls

    return decorator

def singleton(
    interface: Optional[type[TService]] = None,
    category: ServiceCategory = ServiceCategory.APPLICATION,
    options_type: Optional[type[ServiceOptions[Any]]] = None,
    configuration_keys: Optional[set[str]] = None,
    tags: Optional[set[str]] = None,
    priority: int = 0,
    is_async: bool = False,
    requires_initialization: bool = False,
    requires_cleanup: bool = False,
    interceptors: Optional[list[ServiceInterceptorProtocol]] = None,
    health_check: Optional[ServiceHealthCheckProtocol] = None,
    lifecycle: Optional[ServiceLifecycleProtocol] = None,
    constraints: Optional[set[ServiceConstraint]] = None,
    composite: Optional[CompositeServiceProtocol] = None,
    aggregate: Optional[AggregateServiceProtocol] = None,
    constraint_validators: Optional[list[ServiceConstraintValidatorProtocol]] = None,
    version: Optional[Union[str, ServiceVersion]] = None,
    event_handlers: Optional[list[ServiceEventHandlerProtocol]] = None,
    event_emitter: Optional[ServiceEventEmitterProtocol] = None,
) -> Callable[[type[TService]], type[TService]]:
    """
    Decorator for marking a class as a singleton service.

    Args:
        interface: Optional interface that the service must implement
        category: The service category (default: APPLICATION)
        options_type: Optional type for service options
        configuration_keys: Optional set of configuration keys required by the service
        tags: Optional set of tags for the service
        priority: Service initialization priority (default: 0)
        is_async: Whether the service has async initialization (default: False)
        requires_initialization: Whether the service requires explicit initialization (default: False)
        requires_cleanup: Whether the service requires explicit cleanup (default: False)
        interceptors: Optional list of service interceptors
        health_check: Optional health check implementation
        lifecycle: Optional lifecycle management implementation
        constraints: Optional set of service constraints
        composite: Optional composite service implementation
        aggregate: Optional aggregate service implementation
        constraint_validators: Optional list of constraint validators
        version: Optional service version (string or ServiceVersion)
        event_handlers: Optional list of event handlers
        event_emitter: Optional event emitter

    Returns:
        A decorator function that marks a class as a singleton service
    """
    return service(
        interface=interface,
        scope=ServiceScope.SINGLETON,
        category=category,
        options_type=options_type,
        configuration_keys=configuration_keys,
        tags=tags,
        priority=priority,
        is_async=is_async,
        requires_initialization=requires_initialization,
        requires_cleanup=requires_cleanup,
        interceptors=interceptors,
        health_check=health_check,
        lifecycle=lifecycle,
        constraints=constraints,
        composite=composite,
        aggregate=aggregate,
        constraint_validators=constraint_validators,
        version=version,
        event_handlers=event_handlers,
        event_emitter=event_emitter,
    )

def scoped(
    interface: Optional[type[TService]] = None,
    category: ServiceCategory = ServiceCategory.APPLICATION,
    options_type: Optional[type[ServiceOptions[Any]]] = None,
    configuration_keys: Optional[set[str]] = None,
    tags: Optional[set[str]] = None,
    priority: int = 0,
    is_async: bool = False,
    requires_initialization: bool = False,
    requires_cleanup: bool = False,
    interceptors: Optional[list[ServiceInterceptorProtocol]] = None,
    health_check: Optional[ServiceHealthCheckProtocol] = None,
    lifecycle: Optional[ServiceLifecycleProtocol] = None,
    constraints: Optional[set[ServiceConstraint]] = None,
    composite: Optional[CompositeServiceProtocol] = None,
    aggregate: Optional[AggregateServiceProtocol] = None,
    constraint_validators: Optional[list[ServiceConstraintValidatorProtocol]] = None,
    version: Optional[Union[str, ServiceVersion]] = None,
    event_handlers: Optional[list[ServiceEventHandlerProtocol]] = None,
    event_emitter: Optional[ServiceEventEmitterProtocol] = None,
) -> Callable[[type[TService]], type[TService]]:
    """
    Decorator for marking a class as a scoped service.

    Args:
        interface: Optional interface that the service must implement
        category: The service category (default: APPLICATION)
        options_type: Optional type for service options
        configuration_keys: Optional set of configuration keys required by the service
        tags: Optional set of tags for the service
        priority: Service initialization priority (default: 0)
        is_async: Whether the service has async initialization (default: False)
        requires_initialization: Whether the service requires explicit initialization (default: False)
        requires_cleanup: Whether the service requires explicit cleanup (default: False)
        interceptors: Optional list of service interceptors
        health_check: Optional health check implementation
        lifecycle: Optional lifecycle management implementation
        constraints: Optional set of service constraints
        composite: Optional composite service implementation
        aggregate: Optional aggregate service implementation
        constraint_validators: Optional list of constraint validators
        version: Optional service version (string or ServiceVersion)
        event_handlers: Optional list of event handlers
        event_emitter: Optional event emitter

    Returns:
        A decorator function that marks a class as a scoped service
    """
    return service(
        interface=interface,
        scope=ServiceScope.SCOPED,
        category=category,
        options_type=options_type,
        configuration_keys=configuration_keys,
        tags=tags,
        priority=priority,
        is_async=is_async,
        requires_initialization=requires_initialization,
        requires_cleanup=requires_cleanup,
        interceptors=interceptors,
        health_check=health_check,
        lifecycle=lifecycle,
        constraints=constraints,
        composite=composite,
        aggregate=aggregate,
        constraint_validators=constraint_validators,
        version=version,
        event_handlers=event_handlers,
        event_emitter=event_emitter,
    )

def transient(
    interface: Optional[type[TService]] = None,
    category: ServiceCategory = ServiceCategory.APPLICATION,
    options_type: Optional[type[ServiceOptions[Any]]] = None,
    configuration_keys: Optional[set[str]] = None,
    tags: Optional[set[str]] = None,
    priority: int = 0,
    is_async: bool = False,
    requires_initialization: bool = False,
    requires_cleanup: bool = False,
    interceptors: Optional[list[ServiceInterceptorProtocol]] = None,
    health_check: Optional[ServiceHealthCheckProtocol] = None,
    lifecycle: Optional[ServiceLifecycleProtocol] = None,
    constraints: Optional[set[ServiceConstraint]] = None,
    composite: Optional[CompositeServiceProtocol] = None,
    aggregate: Optional[AggregateServiceProtocol] = None,
    constraint_validators: Optional[list[ServiceConstraintValidatorProtocol]] = None,
    version: Optional[Union[str, ServiceVersion]] = None,
    event_handlers: Optional[list[ServiceEventHandlerProtocol]] = None,
    event_emitter: Optional[ServiceEventEmitterProtocol] = None,
) -> Callable[[type[TService]], type[TService]]:
    """
    Decorator for marking a class as a transient service.

    Args:
        interface: Optional interface that the service must implement
        category: The service category (default: APPLICATION)
        options_type: Optional type for service options
        configuration_keys: Optional set of configuration keys required by the service
        tags: Optional set of tags for the service
        priority: Service initialization priority (default: 0)
        is_async: Whether the service has async initialization (default: False)
        requires_initialization: Whether the service requires explicit initialization (default: False)
        requires_cleanup: Whether the service requires explicit cleanup (default: False)
        interceptors: Optional list of service interceptors
        health_check: Optional health check implementation
        lifecycle: Optional lifecycle management implementation
        constraints: Optional set of service constraints
        composite: Optional composite service implementation
        aggregate: Optional aggregate service implementation
        constraint_validators: Optional list of constraint validators
        version: Optional service version (string or ServiceVersion)
        event_handlers: Optional list of event handlers
        event_emitter: Optional event emitter

    Returns:
        A decorator function that marks a class as a transient service
    """
    return service(
        interface=interface,
        scope=ServiceScope.TRANSIENT,
        category=category,
        options_type=options_type,
        configuration_keys=configuration_keys,
        tags=tags,
        priority=priority,
        is_async=is_async,
        requires_initialization=requires_initialization,
        requires_cleanup=requires_cleanup,
        interceptors=interceptors,
        health_check=health_check,
        lifecycle=lifecycle,
        constraints=constraints,
        composite=composite,
        aggregate=aggregate,
        constraint_validators=constraint_validators,
        version=version,
        event_handlers=event_handlers,
        event_emitter=event_emitter,
    )

def framework_service(
    service_type: Optional[type[Any]] = None,
    options_type: Optional[type[ServiceOptions[Any]]] = None,
    configuration_keys: Optional[set[str]] = None,
    tags: Optional[set[str]] = None,
    priority: int = 0,
    is_async: bool = False,
    requires_initialization: bool = False,
    requires_cleanup: bool = False,
    interceptors: Optional[list[ServiceInterceptorProtocol]] = None,
    health_check: Optional[ServiceHealthCheckProtocol] = None,
    lifecycle: Optional[ServiceLifecycleProtocol] = None,
    constraints: Optional[set[ServiceConstraint]] = None,
    composite: Optional[CompositeServiceProtocol] = None,
    aggregate: Optional[AggregateServiceProtocol] = None,
    constraint_validators: Optional[list[ServiceConstraintValidatorProtocol]] = None,
    version: Optional[Union[str, ServiceVersion]] = None,
    event_handlers: Optional[list[ServiceEventHandlerProtocol]] = None,
    event_emitter: Optional[ServiceEventEmitterProtocol] = None,
) -> Callable[[type[TService]], type[TService]]:
    """
    Mark a class as a framework service for DI registration.

    This decorator is a convenience wrapper around @service(scope=ServiceScope.SINGLETON)
    that indicates the service is part of the Uno framework core. Framework services
    are always registered as singletons and should be used for core framework functionality.

    Args:
        service_type: Optional service type to register against (for interface implementations)
        options_type: Optional type for service options
        configuration_keys: Optional set of configuration keys required by the service
        tags: Optional set of tags for the service
        priority: Service initialization priority (default: 0)
        is_async: Whether the service has async initialization (default: False)
        requires_initialization: Whether the service requires explicit initialization (default: False)
        requires_cleanup: Whether the service requires explicit cleanup (default: False)
        interceptors: Optional list of service interceptors
        health_check: Optional health check implementation
        lifecycle: Optional lifecycle management implementation
        constraints: Optional set of service constraints
        composite: Optional composite service implementation
        aggregate: Optional aggregate service implementation
        constraint_validators: Optional list of constraint validators
        version: Optional service version (string or ServiceVersion)
        event_handlers: Optional list of event handlers
        event_emitter: Optional event emitter

    Returns:
        The decorated class
    """
    def decorator(cls: type[TService]) -> type[TService]:
        setattr(cls, "_di_framework_service", True)
        if service_type is not None:
            setattr(cls, "_di_service_type", service_type)
        return singleton(
            interface=service_type,
            category=ServiceCategory.FRAMEWORK,
            options_type=options_type,
            configuration_keys=configuration_keys,
            tags=tags,
            priority=priority,
            is_async=is_async,
            requires_initialization=requires_initialization,
            requires_cleanup=requires_cleanup,
            interceptors=interceptors,
            health_check=health_check,
            lifecycle=lifecycle,
            constraints=constraints,
            composite=composite,
            aggregate=aggregate,
            constraint_validators=constraint_validators,
            version=version,
            event_handlers=event_handlers,
            event_emitter=event_emitter,
        )(cls)
    return decorator

def requires_initialization(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring initialization.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_initialization
        class MyService:
            def initialize(self) -> None:
                pass
        ```
    """
    setattr(cls, "__requires_initialization__", True)
    return cls

def requires_cleanup(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring cleanup.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_cleanup
        class MyService:
            def cleanup(self) -> None:
                pass
        ```
    """
    setattr(cls, "__requires_cleanup__", True)
    return cls

def requires_health_check(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring health checks.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_health_check
        class MyService:
            def check_health(self) -> bool:
                return True
        ```
    """
    setattr(cls, "__requires_health_check__", True)
    return cls

def requires_recovery(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring recovery.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_recovery
        class MyService:
            def recover(self) -> None:
                pass
        ```
    """
    setattr(cls, "__requires_recovery__", True)
    return cls

def requires_validation(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring validation.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_validation
        class MyService:
            def validate(self) -> None:
                pass
        ```
    """
    setattr(cls, "__requires_validation__", True)
    return cls

def requires_mocking(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring mocking.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_mocking
        class MyService:
            def mock(self) -> None:
                pass
        ```
    """
    setattr(cls, "__requires_mocking__", True)
    return cls

def requires_composition(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring composition.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_composition
        class MyService:
            def compose(self, services: list[Any]) -> Any:
                pass
        ```
    """
    setattr(cls, "__requires_composition__", True)
    return cls

def requires_aggregation(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring aggregation.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_aggregation
        class MyService:
            def aggregate(self, services: list[Any]) -> Any:
                pass
        ```
    """
    setattr(cls, "__requires_aggregation__", True)
    return cls

def requires_interception(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring interception.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_interception
        class MyService:
            def intercept(self, service: Any) -> Any:
                pass
        ```
    """
    setattr(cls, "__requires_interception__", True)
    return cls

def requires_middleware(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring middleware.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_middleware
        class MyService:
            def middleware(self, service: Any) -> Any:
                pass
        ```
    """
    setattr(cls, "__requires_middleware__", True)
    return cls

def requires_contract(cls: type[TService]) -> type[TService]:
    """
    Decorator for marking a service as requiring a contract.

    Args:
        cls: The class to decorate

    Returns:
        The decorated class

    Example:
        ```python
        @requires_contract
        class MyService:
            def contract(self) -> Any:
                pass
        ```
    """
    setattr(cls, "__requires_contract__", True)
    return cls
