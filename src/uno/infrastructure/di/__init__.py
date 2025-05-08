# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

"""
Public API for uno DI system.
"""

from __future__ import annotations

from uno.infrastructure.di.shared_types import ContainerProtocol
from .container import Container
from .protocols import (
    ScopeProtocol,
    ServiceProtocol,
    ServiceRegistrationProtocol,
)
from .registration import ServiceRegistration
from .types import (
    AsyncServiceFactoryProtocol,
    Lifetime,
    ServiceFactoryProtocol,
)

__all__ = [
    "AsyncServiceFactoryProtocol",
    "Container",
    "ContainerProtocol",
    "Lifetime",
    "ScopeProtocol",
    "ServiceProtocol",
    "ServiceFactoryProtocol",
    "ServiceRegistration",
    "ServiceRegistrationProtocol",
]
