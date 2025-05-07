"""
Dependency Injection (DI) error classes for the Uno framework.

This module contains error classes that represent DI-related exceptions.
"""

from typing import Any, List
from uno.core.errors.base import FrameworkError

class ServiceDiscoveryValidationError(FrameworkError):
    """Raised when DI service discovery validation fails."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DI-0001",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(message, error_code, details=details, **kwargs)


class ServiceNotFoundError(FrameworkError):
    """Raised when a requested service is not registered in the DI container."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DI-0002",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(message, error_code, details=details, **kwargs)


class ServiceRegistrationError(FrameworkError):
    """Raised when a service registration is invalid or incompatible."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DI-0003",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(message, error_code, details=details, **kwargs)


class CircularDependencyError(FrameworkError):
    """Raised when a circular dependency is detected during DI resolution."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DI-0004",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(message, error_code, details=details, **kwargs)


class DependencyResolutionError(FrameworkError):
    """Raised when a dependency cannot be resolved in the DI container."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0005",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ScopeError(FrameworkError):
    """Raised when there is an error related to DI service scopes."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0006",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ExtraParameterError(FrameworkError):
    """Raised when extra parameters are provided to a DI service constructor."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0007",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class MissingParameterError(FrameworkError):
    """Raised when required parameters are missing for a DI service constructor."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0008",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class FactoryError(FrameworkError):
    """Raised when a DI factory callable fails to produce a service instance."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0009",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceResolutionError(FrameworkError):
    """Raised when a service cannot be resolved in the DI container."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0010",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceInitializationError(FrameworkError):
    """Raised when a service fails to initialize."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0011",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceHealthError(FrameworkError):
    """Raised when a service health check fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0012",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceResilienceError(FrameworkError):
    """Raised when a service resilience policy fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0013",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceCompositionError(FrameworkError):
    """Raised when a service composition fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0014",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceValidationError(FrameworkError):
    """Raised when service validation fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0015",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceStateError(FrameworkError):
    """Raised when a service is in an invalid state."""
    def __init__(
        self,
        message: str,
        error_code: str = "DI-0016",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(message, error_code, details=details, **kwargs)


class ServiceConstraintError(FrameworkError):
    """Raised when service constraints are violated."""
    def __init__(
        self,
        message: str,
        error_code: str = "DI-0017",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(message, error_code, details=details, **kwargs)


class ServiceConfigurationError(FrameworkError):
    """Raised when service configuration is invalid."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0018",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceInterceptionError(FrameworkError):
    """Raised when service interception fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0019",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceLifecycleError(FrameworkError):
    """Raised when service lifecycle operations fail."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0020",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceVersionError(FrameworkError):
    """Raised when service versioning fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0021",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )

class ServiceEventError(FrameworkError):
    """Raised when service event handling fails."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "DI-0022",
        details: dict[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )
