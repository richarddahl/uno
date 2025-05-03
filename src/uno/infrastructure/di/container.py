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

from uno.infrastructure.di.service_registration import ServiceRegistration
from uno.infrastructure.di.resolver import ServiceResolver
from uno.infrastructure.di.service_scope import ServiceScope

T = TypeVar("T")
ProviderT = TypeVar("ProviderT")


class ServiceFactory(Protocol[T]):
    def __call__(self, *args: Any, **kwargs: Any) -> T: ...


class ServiceCollection:
    """
    Main API for registering services in Uno DI.

    Auto-registration:
      - To enable auto-registration of all discovered services, set the UNO_DI_AUTO_REGISTER environment variable to 'true',
        or pass auto_register=True to the constructor, or call enable_auto_registration().
      - You may also specify auto_register_packages (list of package names) to control which packages to scan.
      - Explicit registrations always override auto-registrations.
    """

    def __init__(
        self,
        auto_register: bool = True,
        auto_register_packages: list[str] | None = None,
    ):
        import os

        self._registrations = {}
        self._instances = {}
        self._validations = []
        self._resolver_class = ServiceResolver
        # Auto-registration config
        env_flag = os.environ.get("UNO_DI_AUTO_REGISTER", "false").lower() == "true"
        self._auto_register = auto_register if auto_register is not None else env_flag
        self._auto_register_packages = auto_register_packages or []

    def enable_auto_registration(self, packages: list[str] | None = None):
        """Enable auto-registration for the given packages (or existing config)."""
        self._auto_register = True
        if packages:
            self._auto_register_packages = packages
        return self

    def _run_auto_registration(self):
        if self._auto_register:
            from uno.infrastructure.di import discovery

            if self._auto_register_packages:
                for pkg in self._auto_register_packages:
                    discovery.register_services_in_package(pkg, self)
            else:
                discovery.auto_register_services(self)

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
            type(instance), ServiceScope.SINGLETON, {}
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
                        impl, getattr(ServiceScope, kind.upper()), params
                    )
                    reg.condition = predicate  # Attach the condition
                    # Store under both keys for strict DI fallback blocking
                    self._registrations[service_type] = reg
                    return sc

                return _wrap

            sc.add_singleton = wrap_add("singleton")
            sc.add_scoped = wrap_add("scoped")
            sc.add_transient = wrap_add("transient")
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
        # Run auto-registration first
        self._run_auto_registration()

        # Create the resolver
        resolver = (resolver_class or self._resolver_class)(
            registrations=self._registrations,
            instances=self._instances,
            auto_register=self._auto_register,
        )

        # Run validations
        for validation in self._validations:
            validation(self)

        return resolver
