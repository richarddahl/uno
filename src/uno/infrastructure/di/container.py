# SPDX-FileCopyrightT_coext: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT_co
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

T_co = TypeVar("T_co", covariant=True)
TService = TypeVar("TService")
ProviderT = TypeVar("ProviderT")


class ServiceFactory(Protocol[T_co]):
    def __call__(self, *args: Any, **kwargs: Any) -> T_co: ...
