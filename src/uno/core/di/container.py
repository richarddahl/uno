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

    Auto-registration:
      - To enable auto-registration of all discovered services, set the UNO_DI_AUTO_REGISTER environment variable to 'true',
        or pass auto_register=True to the constructor, or call enable_auto_registration().
      - You may also specify auto_register_packages (list of package names) to control which packages to scan.
      - Explicit registrations always override auto-registrations.
    """

    def __init__(self, auto_register=None, auto_register_packages=None):
        import os
        self._registrations = {}
        self._instances = {}
        self._validations = []
        self._resolver_class = _ServiceResolver
        # Auto-registration config
        env_flag = os.environ.get("UNO_DI_AUTO_REGISTER", "false").lower() == "true"
        self._auto_register = auto_register if auto_register is not None else env_flag
        self._auto_register_packages = auto_register_packages or []
        print(f"[TEST DEBUG] ServiceCollection.__init__: UNO_DI_AUTO_REGISTER={os.environ.get('UNO_DI_AUTO_REGISTER')}, self._auto_register={self._auto_register}")

    def enable_auto_registration(self, packages=None):
        """Enable auto-registration for the given packages (or existing config)."""
        self._auto_register = True
        if packages:
            self._auto_register_packages = packages
        return self

    def _run_auto_registration(self):
        print(f"[TEST DEBUG] _run_auto_registration: self._auto_register={self._auto_register}")
        if self._auto_register:
            from uno.core.di import discovery
            if self._auto_register_packages:
                for pkg in self._auto_register_packages:
                    discovery.discover_services(pkg, self)
            else:
                discovery.auto_register_services(self)

    def add_singleton(self, service_type, implementation=None, name=None, **params):
        impl = implementation or service_type
        key = (service_type, name) if name else service_type
        self._registrations[key] = ServiceRegistration(
            impl, ServiceScope.SINGLETON, params
        )
        return self

    def add_scoped(self, service_type, implementation=None, name=None, **params):
        impl = implementation or service_type
        key = (service_type, name) if name else service_type
        self._registrations[key] = ServiceRegistration(
            impl, ServiceScope.SCOPED, params
        )
        return self

    def add_transient(self, service_type, implementation=None, name=None, **params):
        impl = implementation or service_type
        key = (service_type, name) if name else service_type
        self._registrations[key] = ServiceRegistration(
            impl, ServiceScope.TRANSIENT, params
        )
        return self

    def add_instance(self, service_type, instance, name=None):
        key = (service_type, name) # Always create tuple key
        self._instances[key] = instance
        # Also add to registrations for discovery/validation, storing the TYPE
        self._registrations[key] = ServiceRegistration(
            type(instance), ServiceScope.SINGLETON, {} # Store type(instance) here
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
                    # Store under both keys for strict DI fallback blocking
                    self._registrations[service_type] = reg
                    self._registrations[(service_type, None)] = reg
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
        # Run auto-registration first; explicit registrations always overwrite
        self._run_auto_registration()

        # Ensure both keys for unnamed registrations are present before passing to resolver
        # This ensures consistent lookup behavior within the resolver
        processed_registrations = self._registrations.copy()
        unnamed_keys = [k for k in processed_registrations if not (isinstance(k, tuple) and k[1] is not None)]
        for k in unnamed_keys:
            tuple_key = (k, None)
            if tuple_key not in processed_registrations:
                processed_registrations[tuple_key] = processed_registrations[k]
        # Debug print: show registrations after auto-registration
        print("[TEST DEBUG] ServiceCollection registrations:")
        for key, reg in processed_registrations.items():
            print(f"  {key}: implementation={getattr(reg, 'implementation', None)}")

        # Create the resolver, passing all registrations (including instances handled by add_instance)
        resolver = (resolver_class or self._resolver_class)(
            registrations=processed_registrations,
            instances=self._instances,  # Pass instances dictionary
            auto_register=self._auto_register
        )

        # Run validations
        for validation in self._validations:
            validation(self) # Validation might need access to the original collection

        # The resolver is now fully configured via __init__.
        # No need to loop and call resolver.register() or patch resolver._registrations afterwards.

        return resolver
