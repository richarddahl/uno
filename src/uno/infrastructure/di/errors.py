# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

"""
Dependency Injection error definitions.
"""

from typing import Any

from uno.core.errors.base import FrameworkError

# -----------------------------------------------------------------------------
# Dependency Injection (DI) error codes
# -----------------------------------------------------------------------------


class DIErrorCode:
    """Error codes for Dependency Injection system."""

    SERVICE_NOT_FOUND = "DI-1001"
    SERVICE_REGISTRATION_FAILED = "DI-1002"
    CIRCULAR_DEPENDENCY = "DI-1003"
    DEPENDENCY_RESOLUTION_FAILED = "DI-1004"
    SCOPE_ERROR = "DI-1005"
    EXTRA_PARAMETER = "DI-1006"
    MISSING_PARAMETER = "DI-1007"
    FACTORY_ERROR = "DI-1008"
    SERVICE_RESOLUTION_FAILED = "DI-1009"
    SERVICE_CONSTRAINT_VIOLATION = "DI-1010"
    SERVICE_CONFIGURATION_ERROR = "DI-1011"
    SERVICE_INTERCEPTION_ERROR = "DI-1012"
    SERVICE_VALIDATION_ERROR = "DI-1013"
    SERVICE_STATE_ERROR = "DI-1014"
    SERVICE_LIFECYCLE_ERROR = "DI-1015"
    SERVICE_EVENT_ERROR = "DI-1016"
    SERVICE_INTERCEPTOR_ERROR = "DI-1017"
    SERVICE_HEALTH_CHECK_ERROR = "DI-1018"
    SERVICE_CONSTRAINT_VALIDATOR_ERROR = "DI-1019"
    SERVICE_MOCK_ERROR = "DI-1020"
    SERVICE_CONTRACT_ERROR = "DI-1021"
    SERVICE_MIDDLEWARE_ERROR = "DI-1022"
    SERVICE_RECOVERY_ERROR = "DI-1023"
    SERVICE_AGGREGATE_ERROR = "DI-1024"
    SERVICE_COMPOSITE_ERROR = "DI-1025"
    SERVICE_CHAIN_ERROR = "DI-1026"
    SERVICE_VERSION_ERROR = "DI-1027"   
    SERVICE_OPTIONS_ERROR = "DI-1028"
    SERVICE_HEALTH_ERROR = "DI-1029"
    SERVICE_RESILIENCE_ERROR = "DI-1030"
    


# -----------------------------------------------------------------------------
# Dependency Injection (DI) error classes
# -----------------------------------------------------------------------------


class ServiceDiscoveryValidationError(FrameworkError):
    """Raised when DI service discovery validation fails."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_REGISTRATION_FAILED,
            **context,
        )


class ServiceNotFoundError(FrameworkError):
    """Raised when a requested service is not registered in the DI container."""

    def __init__(self, service_type: str, **context: Any):
        super().__init__(
            message=f"Service '{service_type}' is not registered.",
            error_code=DIErrorCode.SERVICE_NOT_FOUND,
            service_type=service_type,
            **context,
        )


class ServiceRegistrationError(FrameworkError):
    """Raised when a service registration is invalid or incompatible."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_REGISTRATION_FAILED,
            **context,
        )


class CircularDependencyError(FrameworkError):
    """Raised when a circular dependency is detected during DI resolution."""

    def __init__(self, service_type: str, **context: Any):
        super().__init__(
            message=f"Circular dependency detected for '{service_type}'.",
            error_code=DIErrorCode.CIRCULAR_DEPENDENCY,
            service_type=service_type,
            **context,
        )


class DependencyResolutionError(FrameworkError):
    """Raised when a dependency cannot be resolved in the DI container."""

    def __init__(self, service_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to resolve dependency '{service_type}': {reason}",
            error_code=DIErrorCode.DEPENDENCY_RESOLUTION_FAILED,
            service_type=service_type,
            reason=reason,
            **context,
        )


class ScopeError(FrameworkError):
    """Raised when there is an error related to DI service scopes."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SCOPE_ERROR,
            **context,
        )


class ExtraParameterError(FrameworkError):
    """Raised when extra parameters are provided to a DI service constructor."""

    def __init__(self, service_type: str, extra_params: list[str], **context: Any):
        super().__init__(
            message=f"Extra parameters {extra_params} provided for '{service_type}'.",
            error_code=DIErrorCode.EXTRA_PARAMETER,
            service_type=service_type,
            extra_params=extra_params,
            **context,
        )


class MissingParameterError(FrameworkError):
    """Raised when required parameters are missing for a DI service constructor."""

    def __init__(self, service_type: str, missing_params: list[str], **context: Any):
        super().__init__(
            message=f"Missing required parameters {missing_params} for '{service_type}'.",
            error_code=DIErrorCode.MISSING_PARAMETER,
            service_type=service_type,
            missing_params=missing_params,
            **context,
        )


class FactoryError(FrameworkError):
    """Raised when a DI factory callable fails to produce a service instance."""

    def __init__(self, service_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Factory failed to create instance of '{service_type}': {reason}",
            error_code=DIErrorCode.FACTORY_ERROR,
            service_type=service_type,
            reason=reason,
            **context,
        )


class ServiceResolutionError(FrameworkError):
    """Raised when a service cannot be resolved from the DI container."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_RESOLUTION_FAILED,
            **context,
        )

class ServiceInitializationError(FrameworkError):
    """Raised when service initialization fails."""

    def __init__(self, message: str, reason: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_REGISTRATION_FAILED,
            reason=reason,
            **context,
        )


class ServiceConstraintError(FrameworkError):
    """Raised when a service constraint is violated."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_CONSTRAINT_VIOLATION,
            **context,
        )


class ServiceConfigurationError(FrameworkError):
    """Raised when there is an error in service configuration."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_CONFIGURATION_ERROR,
            **context,
        )


class ServiceInterceptionError(FrameworkError):
    """Raised when there is an error in service interception."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_INTERCEPTION_ERROR,
            **context,
        )


class ServiceValidationError(FrameworkError):
    """Raised when service validation fails."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_VALIDATION_ERROR,
            **context,
        )


class ServiceStateError(FrameworkError):
    """Raised when there is an error in service state management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_STATE_ERROR,
            **context,
        ) 

class ServiceLifecycleError(FrameworkError):
    """Raised when there is an error in service lifecycle management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_LIFECYCLE_ERROR,
            **context,
        )

class ServiceEventError(FrameworkError):
    """Raised when there is an error in service event management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_EVENT_ERROR,
            **context,
        )

class ServiceInterceptorError(FrameworkError):
    """Raised when there is an error in service interceptor management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_INTERCEPTOR_ERROR,
            **context,
        )

class ServiceHealthCheckError(FrameworkError):
    """Raised when there is an error in service health check management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_HEALTH_CHECK_ERROR,
            **context,
        )

class ServiceConstraintValidatorError(FrameworkError):
    """Raised when there is an error in service constraint validator management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_CONSTRAINT_VALIDATOR_ERROR,
            **context,
        )

class ServiceMockError(FrameworkError):
    """Raised when there is an error in service mock management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_MOCK_ERROR,
            **context,
        )

class ServiceContractError(FrameworkError):
    """Raised when there is an error in service contract management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_CONTRACT_ERROR,
            **context,
        )

class ServiceMiddlewareError(FrameworkError):
    """Raised when there is an error in service middleware management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_MIDDLEWARE_ERROR,
            **context,
        )       

class ServiceRecoveryError(FrameworkError):
    """Raised when there is an error in service recovery management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_RECOVERY_ERROR,
            **context,
        )

class ServiceAggregateError(FrameworkError):
    """Raised when there is an error in service aggregate management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_AGGREGATE_ERROR,
            **context,  
        )

class ServiceCompositeError(FrameworkError):
    """Raised when there is an error in service composite management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_COMPOSITE_ERROR,
            **context,
        )

class ServiceChainError(FrameworkError):
    """Raised when there is an error in service chain management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_CHAIN_ERROR,
            **context,
        )

class ServiceVersionError(FrameworkError):
    """Raised when there is an error in service version management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_VERSION_ERROR,
            **context,
        )

class ServiceOptionsError(FrameworkError):
    """Raised when there is an error in service options management."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_OPTIONS_ERROR,
            **context,
        )

class ServiceHealthError(FrameworkError):
    """Raised when there is an error in service health checks."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_HEALTH_ERROR,
            **context,
        )


class ServiceResilienceError(FrameworkError):
    """Raised when there is an error in service resilience mechanisms."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_RESILIENCE_ERROR,
            **context,
        )

class ServiceCompositionError(FrameworkError):
    """Raised when there is an error in service composition configuration."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=DIErrorCode.SERVICE_COMPOSITE_ERROR,
            **context,
        )