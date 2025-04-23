# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Scoped dependency injection container for Uno framework.

Public API:
- ServiceCollection: Main API for registering services
- ServiceScope: Enum for service lifetimes
- ServiceFactory: Protocol for service factories

Internal/advanced classes (ServiceRegistration, _ServiceResolver) are not part of the public API.
"""

from typing import Any, Protocol, TypeVar

# Internal use only: advanced/extensibility classes
from ._internal import ServiceRegistration, _ServiceResolver
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
        # Use a wrapper to attach the predicate as a 'condition' attribute
        def conditional_register(sc):
            original_add_singleton = sc.add_singleton
            original_add_scoped = sc.add_scoped
            original_add_transient = sc.add_transient

            def wrap_add(kind):
                def _wrap(service_type, implementation=None, **params):
                    impl = implementation or service_type
                    reg = ServiceRegistration(
                        impl,
                        getattr(ServiceScope, kind.upper()),
                        params
                    )
                    reg.condition = predicate  # Attach the condition
                    self._registrations[service_type] = reg
                    return sc
                return _wrap

            sc.add_singleton = wrap_add('singleton')
            sc.add_scoped = wrap_add('scoped')
            sc.add_transient = wrap_add('transient')
            try:
                configure(sc)
            finally:
                sc.add_singleton = original_add_singleton
                sc.add_scoped = original_add_scoped
                sc.add_transient = original_add_transient

        conditional_register(self)
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
