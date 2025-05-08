"""
Type definitions for uno DI system.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from uno.infrastructure.di.shared_types import T, ContainerProtocol

# Rename to include Protocol suffix for consistency
ServiceFactoryProtocol = Callable[[ContainerProtocol], T]
AsyncServiceFactoryProtocol = Callable[[ContainerProtocol], Awaitable[T]]
Lifetime = Literal["singleton", "scoped", "transient"]
