# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

"""
Public API for uno DI system.
"""

from __future__ import annotations

from uno.di.errors import (
    DIError,
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotRegisteredError,
    SyncInAsyncContextError,
    TypeMismatchError,
)
from uno.di.protocols import ContainerProtocol

from .container import Container
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
    "DIError",
    "DuplicateRegistrationError",
    "Lifetime",
    "ScopeError",
    "ScopeProtocol",
    "ServiceCreationError",
    "ServiceFactoryProtocol",
    "ServiceNotRegisteredError",
    "ServiceRegistration",
    "ServiceRegistrationProtocol",
    "SyncInAsyncContextError",
    "TypeMismatchError",
]
