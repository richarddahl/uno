# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Service discovery for Uno framework.

This module provides utilities for discovering services in the codebase
and automatically registering them with the dependency injection container.
"""

import importlib
import inspect
import logging
import pathlib
import pkgutil
from collections.abc import Iterator
from typing import Any, TypeVar

from uno.core.di.container import ServiceCollection, ServiceScope
from uno.core.di.provider import ServiceProvider, get_service_provider

T = TypeVar("T")


def validate_service_discovery(modules, service_collection, logger=None, strict=False):
    """
    Warn if likely service classes are not registered for DI.
    """
    import inspect
    from uno.core.di.provider import ServiceLifecycle
    try:
        from uno.core.di.interfaces import DomainServiceProtocol
    except ImportError:
        DomainServiceProtocol = None

    logger = logger or logging.getLogger("uno.discovery")
    registered_types = set(service_collection._registrations.keys())
    warnings = []

    for module in modules:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            # Skip builtins or likely non-service classes
            if name.startswith('_'):
                continue
            # Check if class is a likely service
            is_lifecycle = ServiceLifecycle and issubclass(obj, ServiceLifecycle) and obj is not ServiceLifecycle
            is_domain_service = DomainServiceProtocol and issubclass(obj, DomainServiceProtocol)
            is_named_service = name.endswith('Service')
            if not (is_lifecycle or is_domain_service or is_named_service):
                continue
            # Check if registered (decorator or explicit)
            if hasattr(obj, "__framework_service__") and obj.__framework_service__:
                continue
            if obj in registered_types:
                continue
            # Not registered: warn
            msg = f"Likely service class '{name}' in module '{module.__name__}' is not registered for DI (missing decorator or explicit registration)."
            warnings.append(msg)
            logger.warning(msg)
    if strict and warnings:
        raise RuntimeError("Service discovery validation failed: " + "\n".join(warnings))


def find_modules(package_name: str) -> Iterator[str]:
    """
    Find all modules in a package.

    Args:
        package_name: The name of the package to search

    Yields:
        Module names
    """
    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)

    if package_path:
        for _, name, is_pkg in pkgutil.iter_modules(package_path):
            full_name = f"{package_name}.{name}"
            yield full_name

            if is_pkg:
                yield from find_modules(full_name)


def get_class_metadata(cls: type) -> dict[str, Any]:
    """
    Get metadata for a service class.

    Args:
        cls: The class to get metadata for

    Returns:
        A dictionary of metadata
    """
    is_service = hasattr(cls, "__framework_service__") and cls.__framework_service__

    if not is_service:
        return {}

    service_type = getattr(cls, "__framework_service_type__", cls)
    scope = getattr(cls, "__framework_service_scope__", ServiceScope.SINGLETON)

    return {"is_service": is_service, "service_type": service_type, "scope": scope}


def discover_services(
    package_name: str,
    service_collection: ServiceCollection | None = None,
    logger: logging.Logger | None = None,
) -> ServiceCollection:
    """
    Discover and register services in a package.

    Args:
        package_name: The name of the package to search
        service_collection: Optional service collection to add services to
        logger: Optional logger for diagnostic information

    Returns:
        A service collection with all discovered services
    """
    logger = logger or logging.getLogger("uno.discovery")
    service_collection = service_collection or ServiceCollection()

    module_names = list(find_modules(package_name))
    logger.info(f"Discovered {len(module_names)} modules in {package_name}")

    # Import all modules
    modules = []
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            modules.append(module)
        except ImportError as e:
            logger.warning(f"Error importing module {module_name}: {e}")

    # Find all classes in the modules
    service_count = 0
    for module in modules:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            # Skip classes not defined in this module
            if obj.__module__ != module.__name__:
                continue

            # Get metadata
            metadata = get_class_metadata(obj)
            if not metadata.get("is_service", False):
                continue

            # Register the service
            service_type = metadata["service_type"]
            scope = metadata["scope"]

            if scope == ServiceScope.SINGLETON:
                service_collection.add_singleton(service_type, obj)
            elif scope == ServiceScope.SCOPED:
                service_collection.add_scoped(service_type, obj)
            elif scope == ServiceScope.TRANSIENT:
                service_collection.add_transient(service_type, obj)

            service_count += 1
            logger.debug(
                f"Discovered service {obj.__name__} as {service_type.__name__} with scope {scope.name}"
            )

    logger.info(f"Discovered {service_count} services in {package_name}")

    # Run discovery validation (strict mode: raise error if missing)
    validate_service_discovery(modules, service_collection, logger=logger, strict=True)
    return service_collection


def register_services_in_package(
    package_name: str,
    provider: ServiceProvider | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """
    Discover and register services in a package.

    Args:
        package_name: The name of the package to search
        provider: Optional service provider to register services with
        logger: Optional logger for diagnostic information
    """
    provider = provider or get_service_provider()
    logger = logger or logging.getLogger("uno.discovery")

    services = discover_services(package_name, logger=logger)

    # Register with the provider
    extension_name = package_name.split(".")[-1]
    provider.register_extension(extension_name, services)
    logger.info(
        f"Registered services from {package_name} as extension '{extension_name}'"
    )


def scan_directory_for_services(
    directory: str | pathlib.Path,
    base_package: str,
    provider: ServiceProvider | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """
    Scan a directory for packages containing services.

    Args:
        directory: The directory to scan
        base_package: The base package name
        provider: Optional service provider to register services with
        logger: Optional logger for diagnostic information
    """
    provider = provider or get_service_provider()
    logger = logger or logging.getLogger("uno.discovery")

    path = pathlib.Path(directory) if isinstance(directory, str) else directory

    # Find all subdirectories with an __init__.py file
    packages = [
        d.name for d in path.iterdir() if d.is_dir() and (d / "__init__.py").exists()
    ]

    logger.info(f"Found {len(packages)} packages in {path}")

    # Register services in each package
    for package in packages:
        package_name = f"{base_package}.{package}"
        try:
            register_services_in_package(package_name, provider, logger)
        except Exception as e:
            logger.error(f"Error registering services in {package_name}: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                import traceback

                logger.debug(traceback.format_exc())
