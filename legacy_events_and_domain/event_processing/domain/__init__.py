# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Domain module for the Uno framework.

This module provides the core domain abstractions for DDD implementation.
"""

from __future__ import annotations

from uno.domain.errors import (
    DomainError,
    DomainValidationError,
    ErrorCategory,
    ErrorSeverity,
)
from uno.domain.protocols import (
    AggregateRootProtocol,
    DomainEventProtocol,
    EntityProtocol,
    RepositoryProtocol,
    ValueObjectProtocol,
)

__all__ = [
    # Protocol exports
    "AggregateRootProtocol",
    "DomainEventProtocol",
    "EntityProtocol",
    "RepositoryProtocol",
    "ValueObjectProtocol",
    # Error exports
    "DomainError",
    "DomainValidationError",
    "ErrorCategory",
    "ErrorSeverity",
]
