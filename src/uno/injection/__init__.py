# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

"""
Public API for uno DI system.
"""

from __future__ import annotations

from uno.injection.errors import (
    InjectionError,
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotFoundError,
    SyncInAsyncContextError,
    TypeMismatchError,
    ContainerError,
    CircularDependencyError,
    ContainerDisposedError,
    ScopeDisposedError,
)
from uno.injection.protocols import ContainerProtocol

from .container import Container
from .diagnostics import ContainerStateCapture
from .protocols import (
    AsyncServiceFactoryProtocol,
    Lifetime,
    ScopeProtocol,
    ServiceFactoryProtocol,
    ServiceRegistrationProtocol,
)
from .registration import ServiceRegistration

__all__ = [
    "AsyncServiceFactoryProtocol",
    "Container",
    "ContainerProtocol",
    "InjectionError",
    "DuplicateRegistrationError",
    "Lifetime",
    "ScopeError",
    "ScopeProtocol",
    "ServiceCreationError",
    "ServiceFactoryProtocol",
    "ServiceNotFoundError",
    "ServiceRegistration",
    "ServiceRegistrationProtocol",
    "SyncInAsyncContextError",
    "TypeMismatchError",
    "ContainerStateCapture",
    "ContainerError",
    "CircularDependencyError",
    "ContainerDisposedError",
    "ScopeDisposedError",
]
