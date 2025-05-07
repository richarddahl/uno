# SPDX-FileCopyrightT_coext: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT_co
# uno framework
"""
Service collection implementation for Uno DI.

This module provides the ServiceCollection class, which is responsible for registering
services with the DI container. It maintains service registrations and handles
service lifetime management.

Note: All dependencies must be passed explicitly from the composition root.
"""

from __future__ import annotations
import inspect
from pydantic import BaseModel
from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Protocol,
    runtime_checkable,
)
from collections import defaultdict
from functools import wraps
from datetime import datetime
from dataclasses import dataclass
from enum import auto, Enum

from uno.infrastructure.di.errors import (
    ServiceRegistrationError,
    CircularDependencyError,
    ServiceValidationError,
    ServiceStateError,
    ServiceConfigurationError,
    ServiceConstraintError,
)
from uno.infrastructure.di.interfaces import (
    ServiceConstraintValidatorProtocol,
    ServiceLifecycleProtocol,
)
from uno.infrastructure.di.service_scope import ServiceScope

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])
TEntity = TypeVar("TEntity", bound=Any)
TQuery = TypeVar("TQuery", bound=Any)
TResult = TypeVar("TResult", bound=Any)
TOptions = TypeVar("TOptions", bound=Any)
TNext = TypeVar("TNext", bound=Any, contravariant=True)
TMock = TypeVar("TMock", bound=Any, covariant=True)

class ServiceState(Enum):
    """
    Service state enumeration.

    Example:
        ```python
        # Check service state
        if service.state == ServiceState.RUNNING:
            print("Service is running")
        ```
    """
    INITIALIZED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()

@dataclass
class ServiceHealth:
    """
    Service health information.

    Example:
        ```python
        # Create health info
        health = ServiceHealth(
            is_healthy=True,
            last_check=datetime.now(UTC),
            error_count=0,
            recovery_attempts=0,
            state=ServiceState.RUNNING,
            details={"status": "ok"}
        )
        ```
    """
    is_healthy: bool
    last_check: datetime
    error_count: int
    recovery_attempts: int
    state: ServiceState
    details: dict[str, Any]

@runtime_checkable
class ServiceContract(Protocol):
    """
    Protocol for service contracts.

    Example:
        ```python
        class MyServiceContract(ServiceContract):
            def validate_input(self, *args: Any, **kwargs: Any) -> None:
                if not args:
                    raise ServiceValidationError("No arguments provided")

            def validate_output(self, result: Any) -> None:
                if result is None:
                    raise ServiceValidationError("Result cannot be None")
        ```
    """
    def validate_input(self, *args: Any, **kwargs: Any) -> None:
        """
        Validate service method input.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Raises:
            ServiceValidationError: If validation fails

        Example:
            ```python
            def validate_input(self, *args: Any, **kwargs: Any) -> None:
                if not args:
                    raise ServiceValidationError("No arguments provided")
            ```
        """
        ...

    def validate_output(self, result: Any) -> None:
        """
        Validate service method output.

        Args:
            result: The method result

        Raises:
            ServiceValidationError: If validation fails

        Example:
            ```python
            def validate_output(self, result: Any) -> None:
                if result is None:
                    raise ServiceValidationError("Result cannot be None")
            ```
        """
        ...

@runtime_checkable
class ServiceMock(Protocol[TMock]):
    """
    Protocol for service mocks.

    Example:
        ```python
        class MyServiceMock(ServiceMock[MyService]):
            def setup(self) -> None:
                self._mock = Mock()

            def verify(self) -> None:
                self._mock.verify()

            def reset(self) -> None:
                self._mock.reset()

            def get_mock(self) -> MyService:
                return self._mock
        ```
    """
    def setup(self) -> None:
        """
        Setup the mock.

        Example:
            ```python
            def setup(self) -> None:
                self._mock = Mock()
            ```
        """
        ...

    def verify(self) -> None:
        """
        Verify mock expectations.

        Example:
            ```python
            def verify(self) -> None:
                self._mock.verify()
            ```
        """
        ...

    def reset(self) -> None:
        """
        Reset the mock state.

        Example:
            ```python
            def reset(self) -> None:
                self._mock.reset()
            ```
        """
        ...

    def get_mock(self) -> TMock:
        """
        Get the mock instance.

        Returns:
            The mock instance

        Example:
            ```python
            def get_mock(self) -> MyService:
                return self._mock
            ```
        """
        ...

@runtime_checkable
class ServiceRecovery(Protocol):
    """
    Protocol for service recovery.

    Example:
        ```python
        class MyServiceRecovery(ServiceRecovery):
            async def recover(self) -> bool:
                try:
                    await self._service.restart()
                    return True
                except Exception:
                    return False

            def can_recover(self) -> bool:
                return self._service.is_recoverable()
        ```
    """
    async def recover(self) -> bool:
        """
        Attempt to recover the service.

        Returns:
            True if recovery was successful, False otherwise

        Example:
            ```python
            async def recover(self) -> bool:
                try:
                    await self._service.restart()
                    return True
                except Exception:
                    return False
            ```
        """
        ...

    def can_recover(self) -> bool:
        """
        Check if the service can be recovered.

        Returns:
            True if the service can be recovered, False otherwise

        Example:
            ```python
            def can_recover(self) -> bool:
                return self._service.is_recoverable()
            ```
        """
        ...

@runtime_checkable
class ServiceMiddleware(Protocol[TNext]):
    """
    Protocol for service middleware.

    Example:
        ```python
        class LoggingMiddleware(ServiceMiddleware[Callable]):
            async def __call__(self, next: Callable, *args: Any, **kwargs: Any) -> Any:
                print(f"Before: {args}, {kwargs}")
                result = await next(*args, **kwargs)
                print(f"After: {result}")
                return result
        ```
    """
    async def __call__(self, next: TNext, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the middleware.

        Args:
            next: The next middleware or service method
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the middleware chain

        Example:
            ```python
            async def __call__(self, next: Callable, *args: Any, **kwargs: Any) -> Any:
                print(f"Before: {args}, {kwargs}")
                result = await next(*args, **kwargs)
                print(f"After: {result}")
                return result
            ```
        """
        ...

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
class InterceptionOptions:
    """
    Options for service method interception.

    Example:
        ```python
        options = InterceptionOptions(
            middleware=[LoggingMiddleware()],
            validate_contract=True,
            verify_behavior=True
        )
        ```
    """
    middleware: list[ServiceMiddleware[Any]] | None = None
    validate_contract: bool = False
    verify_behavior: bool = False

    def __post_init__(self) -> None:
        """
        Initialize default values.

        Example:
            ```python
            def __post_init__(self) -> None:
                if self.middleware is None:
                    self.middleware = []
            ```
        """
        if self.middleware is None:
            self.middleware = []

class _ServiceRegistration:
    """
    A service registration in the DI container.

    This class maintains metadata about a service, including its type,
    implementation, and lifetime.

    Note: All dependencies must be passed explicitly from the composition root.

    Example:
        ```python
        registration = _ServiceRegistration(
            service_type=IMyService,
            implementation=MyService,
            scope=ServiceScope.SINGLETON,
            name="default",
            options=MyServiceOptions(),
            interception=InterceptionOptions()
        )
        ```
    """

    def __init__(
        self,
        service_type: type[Any],
        implementation: type[Any] | Callable[[], Any],
        scope: ServiceScope,
        name: str | None = None,
        options: ServiceOptions[Any] | None = None,
        interception: InterceptionOptions | None = None,
    ) -> None:
        """
        Initialize a new ServiceRegistration instance.

        Args:
            service_type: The type of service to register
            implementation: The implementation type or factory function
            scope: The service lifetime scope
            name: Optional name for named service registration
            options: Optional service options
            interception: Optional interception options

        Example:
            ```python
            registration = _ServiceRegistration(
                service_type=IMyService,
                implementation=MyService,
                scope=ServiceScope.SINGLETON,
                name="default",
                options=MyServiceOptions(),
                interception=InterceptionOptions()
            )
            ```
        """
        self.service_type = service_type
        self.implementation = implementation
        self.scope = scope
        self.name = name
        self.options = options
        self.interception = interception or InterceptionOptions()
        self._dependencies: set[type[Any]] = set()
        self._required_dependencies: set[type[Any]] = set()
        self._optional_dependencies: set[type[Any]] = set()
        self._registration_time = datetime.now()
        self._initialization_time: datetime | None = None
        self._last_health_check: datetime | None = None
        self._health_status: bool | None = None
        self._contract_validators: dict[str, Callable[..., None]] = {}
        self._behavior_verifiers: dict[str, Callable[..., None]] = {}
        self._contracts: dict[str, ServiceContract] = {}
        self._mocks: dict[str, ServiceMock[Any]] = {}
        self._recovery: ServiceRecovery | None = None
        self._state: ServiceState = ServiceState.INITIALIZED
        self._health: ServiceHealth = ServiceHealth(
            is_healthy=True,
            last_check=datetime.now(),
            error_count=0,
            recovery_attempts=0,
            state=ServiceState.INITIALIZED,
            details={},
        )

    def __repr__(self) -> str:
        """Get a string representation of the registration."""
        name_str = f" (name='{self.name}')" if self.name else ""
        options_str = f" (options={self.options})" if self.options else ""
        interception_str = f" (interception={self.interception})" if self.interception else ""
        state_str = f" (state={self._state.name})"
        return f"ServiceRegistration({self.service_type.__name__}, scope={self.scope.name}{name_str}{options_str}{interception_str}{state_str})"

    def add_contract_validator(self, method_name: str, validator: Callable[..., None]) -> None:
        """
        Add a contract validator for a method.

        Args:
            method_name: The name of the method to validate
            validator: The validation function
        """
        self._contract_validators[method_name] = validator

    def add_behavior_verifier(self, method_name: str, verifier: Callable[..., None]) -> None:
        """
        Add a behavior verifier for a method.

        Args:
            method_name: The name of the method to verify
            verifier: The verification function
        """
        self._behavior_verifiers[method_name] = verifier

    def add_contract(self, method_name: str, contract: ServiceContract) -> None:
        """
        Add a contract for a method.

        Args:
            method_name: The name of the method
            contract: The contract to add
        """
        self._contracts[method_name] = contract

    def add_mock(self, method_name: str, mock: ServiceMock[Any]) -> None:
        """
        Add a mock for a method.

        Args:
            method_name: The name of the method
            mock: The mock to add
        """
        self._mocks[method_name] = mock

    def set_recovery(self, recovery: ServiceRecovery) -> None:
        """
        Set the recovery mechanism for the service.

        Args:
            recovery: The recovery mechanism
        """
        self._recovery = recovery

    def update_state(self, state: ServiceState, details: dict[str, Any] | None = None) -> None:
        """
        Update the service state.

        Args:
            state: The new state
            details: Optional state details
        """
        self._state = state
        self._health.state = state
        if details:
            self._health.details.update(details)

    def update_health(self, is_healthy: bool, error: Exception | None = None) -> None:
        """
        Update the service health.

        Args:
            is_healthy: Whether the service is healthy
            error: Optional error that occurred
        """
        self._health.is_healthy = is_healthy
        self._health.last_check = datetime.now()
        if not is_healthy:
            self._health.error_count += 1
            if error:
                self._health.details["last_error"] = str(error)
        else:
            self._health.error_count = 0
            self._health.recovery_attempts = 0

class ServiceCollection:
    """
    A collection of service registrations.

    This class maintains service registrations and handles service lifetime management.
    It provides methods for registering services with different lifetimes.

    Note: All dependencies must be passed explicitly from the composition root.
    """

    def __init__(self) -> None:
        """Initialize a new ServiceCollection instance."""
        self._registrations: dict[type[Any], _ServiceRegistration] = {}
        self._instances: dict[type[Any], Any] = {}
        self._named_registrations: dict[str, _ServiceRegistration] = {}
        self._validations: list[Callable[[], None]] = []
        self._constraints: list[Callable[[_ServiceRegistration], None]] = []
        self._options_validators: dict[type[ServiceOptions[Any]], Callable[[ServiceOptions[Any]], None]] = {}
        self._global_middleware: list[ServiceMiddleware[Any]] = []
        self._mock_mode: bool = False

    def enable_mock_mode(self) -> None:
        """
        Enable mock mode for the service collection.
        This allows for mocking and contract validation.
        """
        self._mock_mode = True

    def disable_mock_mode(self) -> None:
        """
        Disable mock mode for the service collection.
        """
        self._mock_mode = False

    def add_global_middleware(self, middleware: ServiceMiddleware[Any]) -> None:
        """
        Add global middleware to be applied to all services.

        Args:
            middleware: The middleware to add
        """
        self._global_middleware.append(middleware)

    def _wrap_method(
        self,
        registration: _ServiceRegistration,
        method_name: str,
        method: Callable[..., Any],
    ) -> Callable[..., Any]:
        """
        Wrap a method with middleware, validation, and testing.

        Args:
            registration: The service registration
            method_name: The name of the method
            method: The method to wrap

        Returns:
            The wrapped method
        """
        @wraps(method)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            # Check if in test mode and mock exists
            if self._mock_mode and method_name in registration._mocks:
                mock = registration._mocks[method_name]
                return mock.get_mock()(*args, **kwargs)

            # Validate contract if exists
            if method_name in registration._contracts:
                contract = registration._contracts[method_name]
                try:
                    contract.validate_input(*args, **kwargs)
                except Exception as e:
                    raise ServiceValidationError(
                        f"Contract validation failed for {method_name}: {str(e)}",
                        reason=str(e),
                    ) from e

            # Build middleware chain
            chain = method
            for middleware in reversed(registration.interception.middleware or []):
                chain = lambda next=chain, m=middleware: m(next, *args, **kwargs)

            # Add global middleware
            for middleware in reversed(self._global_middleware):
                chain = lambda next=chain, m=middleware: m(next, *args, **kwargs)

            # Execute method
            try:
                result = await chain()
            except Exception as e:
                registration.update_health(False, e)
                if registration._recovery and registration._recovery.can_recover():
                    registration._health.recovery_attempts += 1
                    if await registration._recovery.recover():
                        registration.update_health(True)
                        return await wrapped(*args, **kwargs)
                raise ServiceStateError(
                    f"Method execution failed: {str(e)}",
                    reason=str(e),
                ) from e

            # Validate contract output if exists
            if method_name in registration._contracts:
                contract = registration._contracts[method_name]
                try:
                    contract.validate_output(result)
                except Exception as e:
                    raise ServiceValidationError(
                        f"Contract validation failed for {method_name}: {str(e)}",
                        reason=str(e),
                    ) from e

            registration.update_health(True)
            return result

        return wrapped

    def _apply_interception(self, registration: _ServiceRegistration) -> None:
        """
        Apply interception to a service registration.

        Args:
            registration: The service registration to apply interception to
        """
        if not isinstance(registration.implementation, type):
            return

        for name, method in inspect.getmembers(registration.implementation, inspect.isfunction):
            if not name.startswith("_"):
                setattr(
                    registration.implementation,
                    name,
                    self._wrap_method(registration, name, method),
                )

    def _validate_implementation(self, service_type: type[TService], implementation: type[TService] | Callable[[], TService]) -> None:
        """
        Validate the implementation type.

        Args:
            service_type: The type of service to register
            implementation: The implementation type or factory function

        Raises:
            ServiceRegistrationError: If the implementation is invalid
        """
        # Check if implementation is a type
        if isinstance(implementation, type):
            # Special handling for Pydantic models
            if issubclass(service_type, BaseModel):
                if not issubclass(implementation, service_type):
                    raise ServiceRegistrationError(
                        f"Implementation type must be a subclass of {service_type.__name__}, got {implementation.__name__}",
                        reason="Invalid implementation type",
                    )
            # For protocol types, check if implementation provides all required methods
            elif hasattr(service_type, '__protocol__'):
                protocol_methods = {
                    name for name in dir(service_type)
                    if not name.startswith('_') and 
                    not hasattr(getattr(service_type, name), '__isabstractmethod__')
                }
                implementation_methods = {
                    name for name in dir(implementation)
                    if not name.startswith('_')
                }
                if not protocol_methods.issubset(implementation_methods):
                    missing_methods = protocol_methods - implementation_methods
                    raise ServiceRegistrationError(
                        f"Implementation type {implementation.__name__} is missing required protocol methods: {', '.join(missing_methods)}",
                        reason="Invalid implementation type",
                    )
            else:
                # For regular types, check if implementation is a subclass
                if not issubclass(implementation, service_type):
                    raise ServiceRegistrationError(
                        f"Implementation type must be a subclass of {service_type.__name__}, got {implementation.__name__}",
                        reason="Invalid implementation type",
                    )
        elif not callable(implementation):
            raise ServiceRegistrationError(
                f"Implementation must be a type or callable, got {type(implementation).__name__}",
                reason="Invalid implementation type",
            )

    def _validate_dependencies(self, registration: _ServiceRegistration) -> None:
        """
        Validate service dependencies.

        Args:
            registration: The service registration to validate

        Raises:
            ServiceRegistrationError: If dependencies are invalid
            CircularDependencyError: If a circular dependency is detected
        """
        if not isinstance(registration.implementation, type):
            return

        # Get constructor parameters
        params = inspect.signature(type(registration.implementation).__init__).parameters
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

            # Check if parameter type is registered
            if param_type in self._registrations:
                registration._dependencies.add(param_type)
                if param.default == inspect._empty:
                    registration._required_dependencies.add(param_type)
                else:
                    registration._optional_dependencies.add(param_type)

        # Check for circular dependencies
        visited: set[type[Any]] = set()
        temp: set[type[Any]] = set()

        def visit(node: type[Any]) -> None:
            if node in temp:
                raise CircularDependencyError(
                    f"Circular dependency detected involving {node.__name__}"
                )
            if node in visited:
                return
            temp.add(node)
            for dependency in self._registrations[node]._dependencies:
                visit(dependency)
            temp.remove(node)
            visited.add(node)

        visit(registration.service_type)

    def _validate_constraints(self, registration: _ServiceRegistration) -> None:
        """
        Validate service constraints.

        Args:
            registration: The service registration to validate

        Raises:
            ServiceConstraintError: If constraints are violated
        """
        # Singleton services can't depend on scoped services
        if registration.scope == ServiceScope.SINGLETON:
            for dependency in registration._dependencies:
                dep_registration = self._registrations[dependency]
                if dep_registration.scope == ServiceScope.SCOPED:
                    raise ServiceConstraintError(
                        f"Singleton service {registration.service_type.__name__} cannot depend on scoped service {dependency.__name__}"
                    )

        # Run custom constraints
        for constraint in self._constraints:
            constraint(registration)

    def _validate_options(self, options: ServiceOptions[Any]) -> None:
        """
        Validate service options.

        Args:
            options: The service options to validate

        Raises:
            ServiceConfigurationError: If options are invalid
        """
        # Run built-in validation
        try:
            options.validate()
        except Exception as e:
            raise ServiceConfigurationError(
                f"Options validation failed: {str(e)}",
                reason=str(e),
            ) from e

        # Run custom validation
        validator = self._options_validators.get(type(options))
        if validator:
            try:
                validator(options)
            except Exception as e:
                raise ServiceConfigurationError(
                    f"Custom options validation failed: {str(e)}",
                    reason=str(e),
                ) from e

    def add_service(
        self,
        service_type: type[TService],
        implementation: type[TService] | Callable[[], TService] | None = None,
        scope: ServiceScope = ServiceScope.TRANSIENT,
        name: str | None = None,
        options: ServiceOptions[Any] | None = None,
        interception: InterceptionOptions | None = None,
    ) -> None:
        """
        Register a service with the specified lifetime scope.

        Args:
            service_type: The type of service to register
            implementation: The implementation type or factory function
            scope: The service lifetime scope (default: TRANSIENT)
            name: Optional name for named service registration
            options: Optional service options
            interception: Optional interception options

        Raises:
            ServiceRegistrationError: If the service registration is invalid
            CircularDependencyError: If a circular dependency is detected
            ServiceConstraintError: If service constraints are violated
            ServiceConfigurationError: If service options are invalid
        """
        if implementation is None:
            implementation = service_type

        # Validate implementation type
        self._validate_implementation(service_type, implementation)

        # Check for duplicate registration
        if service_type in self._registrations:
            raise ServiceRegistrationError(
                f"Service type {service_type.__name__} is already registered"
            )

        # Check for duplicate named registration
        if name and name in self._named_registrations:
            raise ServiceRegistrationError(
                f"Named service '{name}' is already registered"
            )

        # Validate options if provided
        if options:
            self._validate_options(options)

        registration = _ServiceRegistration(
            service_type=service_type,
            implementation=implementation,
            scope=scope,
            name=name,
            options=options,
            interception=interception,
        )

        # Validate dependencies and constraints
        self._validate_dependencies(registration)
        self._validate_constraints(registration)

        # Apply interception
        self._apply_interception(registration)

    def add_singleton(
        self,
        service_type: type[T],
        implementation_type: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        options: ServiceOptions[T] | None = None,
        requires_initialization: bool = False,
        requires_cleanup: bool = False,
        constraints: list[ServiceConstraintValidator] | None = None,
        name: str | None = None,
    ) -> "ServiceCollection":
        """
        Add a singleton service registration.

        Args:
            service_type: The service type to register
            implementation_type: Optional implementation type
            factory: Optional factory function
            options: Optional configuration options
            requires_initialization: Whether the service requires initialization
            requires_cleanup: Whether the service requires cleanup
            constraints: Optional list of constraint validators
            name: Optional name for named service registration

        Returns:
            The service collection for chaining

        Raises:
            ServiceRegistrationError: If registration is invalid
        """
        if service_type in self._registrations and not name:
            raise ServiceRegistrationError(
                f"Service {service_type.__name__} is already registered",
                reason="Duplicate registration",
            )

        # Validate implementation type
        if implementation_type:
            if not issubclass(implementation_type, service_type):
                raise ServiceRegistrationError(
                    f"Implementation type {implementation_type.__name__} must be a subclass of {service_type.__name__}",
                    reason="Invalid implementation type",
                )
            # Check if service requires lifecycle
            if requires_initialization or requires_cleanup:
                if not issubclass(implementation_type, ServiceLifecycleProtocol) or not Protocol in implementation_type.__mro__:
                    raise ServiceRegistrationError(
                        f"Service {service_type.__name__} requires lifecycle but implementation {implementation_type.__name__} does not implement ServiceLifecycleProtocol",
                        reason="Missing lifecycle implementation",
                    )

        # Validate constraints
        if constraints:
            for constraint in constraints:
                if not isinstance(constraint, ServiceConstraintValidatorProtocol):
                    raise ServiceRegistrationError(
                        f"Invalid constraint validator for {service_type.__name__}",
                        reason="Invalid constraint type",
                    )

        # --- Singleton instance creation/caching ---
        if factory is not None:
            instance = factory()
        elif implementation_type is not None:
            instance = implementation_type()
        else:
            raise ServiceRegistrationError(
                f"No implementation or factory provided for singleton {service_type.__name__}",
                reason="Missing implementation",
            )

        registration = _ServiceRegistration(
            service_type=service_type,
            implementation=lambda: instance,
            scope=ServiceScope.SINGLETON,
            name=name,
            options=options,
            interception=InterceptionOptions(
                middleware=[],
                validate_contract=False,
                verify_behavior=False,
            ),
        )

        if name:
            self._named_registrations[name] = registration
        else:
            self._registrations[service_type] = registration
        self._instances[service_type] = instance

        return self

    def add_scoped(
        self,
        service_type: type[T],
        implementation_type: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        options: ServiceOptions[T] | None = None,
        requires_initialization: bool = False,
        requires_cleanup: bool = False,
        constraints: list[ServiceConstraintValidator] | None = None,
    ) -> "ServiceCollection":
        """
        Add a scoped service registration.

        Args:
            service_type: The service type to register
            implementation_type: Optional implementation type
            factory: Optional factory function
            options: Optional configuration options
            requires_initialization: Whether the service requires initialization
            requires_cleanup: Whether the service requires cleanup
            constraints: Optional list of constraint validators

        Returns:
            The service collection for chaining

        Raises:
            ServiceRegistrationError: If registration is invalid
        """
        if service_type in self._registrations:
            raise ServiceRegistrationError(
                f"Service {service_type.__name__} is already registered",
                reason="Duplicate registration",
            )

        # Validate implementation type
        if implementation_type and not issubclass(implementation_type, service_type):
            raise ServiceRegistrationError(
                f"Implementation type {implementation_type.__name__} must be a subclass of {service_type.__name__}",
                reason="Invalid implementation type",
            )

        # Validate factory
        if factory and not callable(factory):
            raise ServiceRegistrationError(
                f"Factory for {service_type.__name__} must be callable",
                reason="Invalid factory",
            )

        # Validate lifecycle requirements
        if requires_initialization or requires_cleanup:
            if implementation_type:
                if not issubclass(implementation_type, ServiceLifecycleProtocol):
                    raise ServiceRegistrationError(
                        f"Service {implementation_type.__name__} requires lifecycle but does not implement ServiceLifecycleProtocol",
                        reason="Missing lifecycle implementation",
                    )
            elif factory:
                # For factory-created services, we can't validate lifecycle at registration time
                pass

        # Validate constraints
        if constraints:
            for constraint in constraints:
                if not isinstance(constraint, ServiceConstraintValidatorProtocol):
                    raise ServiceRegistrationError(
                        f"Invalid constraint validator for {service_type.__name__}",
                        reason="Invalid constraint type",
                    )

        self._registrations[service_type] = _ServiceRegistration(
            service_type=service_type,
            implementation=factory or implementation_type,
            scope=ServiceScope.SCOPED,
            options=options or {},
            interception=InterceptionOptions(
                middleware=[],
                validate_contract=False,
                verify_behavior=False,
            ),
        )

        return self

    def add_transient(
        self,
        service_type: type[T],
        implementation_type: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        options: ServiceOptions[T] | None = None,
        requires_initialization: bool = False,
        requires_cleanup: bool = False,
        constraints: list[ServiceConstraintValidator] | None = None,
    ) -> "ServiceCollection":
        """
        Add a transient service registration.

        Args:
            service_type: The service type to register
            implementation_type: Optional implementation type
            factory: Optional factory function
            options: Optional configuration options
            requires_initialization: Whether the service requires initialization
            requires_cleanup: Whether the service requires cleanup
            constraints: Optional list of constraint validators

        Returns:
            The service collection for chaining

        Raises:
            ServiceRegistrationError: If registration is invalid
        """
        if service_type in self._registrations:
            raise ServiceRegistrationError(
                f"Service {service_type.__name__} is already registered",
                reason="Duplicate registration",
            )

        # Validate implementation type
        if implementation_type and not issubclass(implementation_type, service_type):
            raise ServiceRegistrationError(
                f"Implementation type {implementation_type.__name__} must be a subclass of {service_type.__name__}",
                reason="Invalid implementation type",
            )

        # Validate factory
        if factory and not callable(factory):
            raise ServiceRegistrationError(
                f"Factory for {service_type.__name__} must be callable",
                reason="Invalid factory",
            )

        # Validate lifecycle requirements
        if requires_initialization or requires_cleanup:
            if implementation_type:
                if not issubclass(implementation_type, ServiceLifecycleProtocol):
                    raise ServiceRegistrationError(
                        f"Service {implementation_type.__name__} requires lifecycle but does not implement ServiceLifecycleProtocol",
                        reason="Missing lifecycle implementation",
                    )
            elif factory:
                # For factory-created services, we can't validate lifecycle at registration time
                pass

        # Validate constraints
        if constraints:
            for constraint in constraints:
                if not isinstance(constraint, ServiceConstraintValidator):
                    raise ServiceRegistrationError(
                        f"Invalid constraint validator for {service_type.__name__}",
                        reason="Invalid constraint type",
                    )

        self._registrations[service_type] = _ServiceRegistration(
            service_type=service_type,
            implementation=factory or implementation_type,
            scope=ServiceScope.TRANSIENT,
            options=options or {},
            interception=InterceptionOptions(
                middleware=[],
                validate_contract=False,
                verify_behavior=False,
            ),
        )

        return self

    def add_instance(
        self,
        service_type: type[TService],
        instance: TService,
        name: str | None = None,
        options: ServiceOptions[Any] | None = None,
    ) -> None:
        """
        Register a singleton instance.

        Args:
            service_type: The type of service to register
            instance: The service instance
            name: Optional name for named service registration
            options: Optional service options

        Raises:
            ServiceRegistrationError: If the instance is not of the correct type
            ServiceConfigurationError: If service options are invalid
        """
        if not isinstance(instance, service_type):
            raise ServiceRegistrationError(
                f"DI-1002: Implementation instance must be of type {service_type.__name__} (got {type(instance).__name__})"
            )

        # Validate options if provided
        if options:
            self._validate_options(options)

        registration = _ServiceRegistration(
            service_type=service_type,
            implementation=lambda: instance,
            scope=ServiceScope.SINGLETON,
            name=name,
            options=options,
        )

        if name:
            self._named_registrations[name] = registration
        self._registrations[service_type] = registration
        self._instances[service_type] = instance

    def add_validation(self, validation: Callable[[], None]) -> None:
        """
        Add a validation hook.

        Args:
            validation: The validation function to call
        """
        self._validations.append(validation)

    def add_constraint(self, constraint: Callable[[_ServiceRegistration], None]) -> None:
        """
        Add a service constraint.

        Args:
            constraint: The constraint function to call
        """
        self._constraints.append(constraint)

    def add_options_validator(
        self,
        options_type: type[ServiceOptions[Any]],
        validator: Callable[[ServiceOptions[Any]], None],
    ) -> None:
        """
        Add a validator for service options.

        Args:
            options_type: The type of options to validate
            validator: The validation function to call
        """
        self._options_validators[options_type] = validator

    def validate(self) -> None:
        """
        Run all validation hooks.

        Raises:
            ValueError: If any validation hook fails
        """
        for validation in self._validations:
            try:
                validation()
            except Exception as e:
                raise ValueError(f"Validation failed: {str(e)}") from e

    def get_named_registration(self, name: str) -> _ServiceRegistration | None:
        """
        Get a named service registration.

        Args:
            name: The name of the service registration

        Returns:
            The service registration, or None if not found
        """
        return self._named_registrations.get(name)

    def is_registered(self, service_type: type[Any], name: str | None = None) -> bool:
        """
        Check if a service is registered.

        Args:
            service_type: The type of service to check
            name: Optional name for named service registration

        Returns:
            True if the service is registered, False otherwise
        """
        if name:
            return name in self._named_registrations
        return service_type in self._registrations

    def remove_service(self, service_type: type[Any], name: str | None = None) -> None:
        """
        Remove a service registration.

        Args:
            service_type: The type of service to remove
            name: Optional name for named service registration

        Raises:
            KeyError: If the service is not registered
        """
        if name:
            if name not in self._named_registrations:
                raise KeyError(f"Named service '{name}' not registered")
            del self._named_registrations[name]
        if service_type not in self._registrations:
            raise KeyError(f"Service type {service_type.__name__} not registered")
        del self._registrations[service_type]
        if service_type in self._instances:
            del self._instances[service_type]

    def get_services(self, service_type: type[TService]) -> list[_ServiceRegistration]:
        """
        Get all registered services of a specific type.

        Args:
            service_type: The type of service to get

        Returns:
            A list of service registrations
        """
        return [
            registration
            for registration in self._registrations.values()
            if issubclass(registration.service_type, service_type)
        ]

    def get_dependency_graph(self) -> dict[type[Any], set[type[Any]]]:
        """
        Get the dependency graph for all registered services.

        Returns:
            A dictionary mapping service types to their dependencies
        """
        graph: dict[type[Any], set[type[Any]]] = defaultdict(set)
        for service_type, registration in self._registrations.items():
            graph[service_type] = registration._dependencies
        return dict(graph)

    def get_service_metrics(self) -> dict[type[Any], dict[str, Any]]:
        """
        Get metrics for all registered services.

        Returns:
            A dictionary mapping service types to their metrics
        """
        metrics: dict[type[Any], dict[str, Any]] = {}
        for service_type, registration in self._registrations.items():
            metrics[service_type] = {
                "registration_time": registration._registration_time,
                "initialization_time": registration._initialization_time,
                "last_health_check": registration._last_health_check,
                "health_status": registration._health_status,
                "dependencies": list(registration._dependencies),
                "required_dependencies": list(registration._required_dependencies),
                "optional_dependencies": list(registration._optional_dependencies),
                "scope": registration.scope,
                "has_options": registration.options is not None,
            }
        return metrics

    def build_provider(self) -> ServiceProvider:
        """Build a service provider from the registered services.

        Returns:
            A new ServiceProvider instance

        Raises:
            ValueError: If validation fails
        """
        self.validate()
        from uno.infrastructure.di.service_provider import ServiceProvider
        return ServiceProvider(self)

    def build_service_provider(self) -> Any:
        """
        Build a service provider from the registered services.

        Returns:
            A new ServiceProvider instance

        Raises:
            ValueError: If validation fails
        """
        self.validate()
        from uno.infrastructure.di.service_provider import ServiceProvider
        return ServiceProvider(self)
