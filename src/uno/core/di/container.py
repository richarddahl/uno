# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Scoped dependency injection container for Uno framework.

This module implements a hierarchical dependency injection container that supports
different scopes for services, such as singleton (application), scoped, and transient.
"""

from typing import Any, Protocol, TypeVar

from ._internal import (
    ServiceRegistration,  # advanced/extensibility only
    _ServiceResolver,  # advanced/extensibility only
)
from .service_scope import ServiceScope

T = TypeVar("T")
ProviderT = TypeVar("ProviderT")


class ServiceFactory(Protocol[T]):
    def __call__(self, *args: Any, **kwargs: Any) -> T: ...


class ServiceCollection:
    """
    Main API for registering services in Uno DI.
    """

    def __init__(self):
        self._registrations = {}
        self._instances = {}
        self._validations = []
        self._resolver_class = _ServiceResolver

    def add_singleton(self, service_type, implementation=None, **params):
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SINGLETON, params
        )
        return self

    def add_scoped(self, service_type, implementation=None, **params):
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.SCOPED, params
        )
        return self

    def add_transient(self, service_type, implementation=None, **params):
        impl = implementation or service_type
        self._registrations[service_type] = ServiceRegistration(
            impl, ServiceScope.TRANSIENT, params
        )
        return self

    def add_instance(self, service_type, instance):
        self._instances[service_type] = instance
        # Also add to registrations for discovery/validation
        self._registrations[service_type] = ServiceRegistration(
            instance, ServiceScope.SINGLETON, {}
        )
        return self

    def add_conditional(self, predicate, configure):
        if predicate():
            configure(self)
        return self

    def add_validation(self, validation_fn):
        self._validations.append(validation_fn)
        return self

    def build(self, resolver_class=None):
        resolver = (resolver_class or self._resolver_class)()
        # Register direct instances
        for service_type, instance in getattr(self, "_instances", {}).items():
            resolver.register_instance(service_type, instance)
        # Register other services
        for service_type, registration in self._registrations.items():
            if service_type in getattr(self, "_instances", {}):
                continue  # already registered as instance
            resolver._registrations[service_type] = registration
        for validation in self._validations:
            validation(self)
        return resolver
