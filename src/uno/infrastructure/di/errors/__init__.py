"""
Dependency Injection (DI) error classes for the Uno framework.

This module contains error classes that represent DI-related exceptions.
"""

from .di_errors import (
    ServiceDiscoveryValidationError,
    ServiceNotFoundError,
    ServiceRegistrationError,
    CircularDependencyError,
    DependencyResolutionError,
    ScopeError,
    ExtraParameterError,
    MissingParameterError,
    FactoryError,
    ServiceResolutionError,
    ServiceInitializationError,
    ServiceHealthError,
    ServiceResilienceError,
    ServiceCompositionError,
    ServiceValidationError,
    ServiceStateError,
    ServiceConstraintError,
    ServiceConfigurationError,
    ServiceInterceptionError,
    ServiceLifecycleError,
    ServiceVersionError,
    ServiceEventError,
)

__all__ = [
    "ServiceDiscoveryValidationError",
    "ServiceNotFoundError",
    "ServiceRegistrationError",
    "CircularDependencyError",
    "DependencyResolutionError",
    "ScopeError",
    "ExtraParameterError",
    "MissingParameterError",
    "FactoryError",
    "ServiceResolutionError",
    "ServiceInitializationError",
    "ServiceHealthError",
    "ServiceResilienceError",
    "ServiceCompositionError",
    "ServiceValidationError",
    "ServiceStateError",
    "ServiceConstraintError",
    "ServiceConfigurationError",
    "ServiceInterceptionError",
    "ServiceLifecycleError",
    "ServiceVersionError",
    "ServiceEventError",
]
