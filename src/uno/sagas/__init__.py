# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Public API for the Uno sagas package.

This module exports the public API for sagas/process managers in the Uno framework,
providing orchestration and coordination capabilities for long-running processes.
"""

from uno.sagas.errors import (
    SagaError,
    SagaStoreError,
    SagaNotFoundError,
    SagaAlreadyExistsError,
    SagaCompensationError,
)
from uno.sagas.protocols import Saga, SagaState, SagaStore
from uno.sagas.implementations.memory import InMemorySagaStore

__all__ = [
    # Core protocols
    "Saga",
    "SagaState",
    "SagaStore",
    # Errors
    "SagaError",
    "SagaStoreError",
    "SagaNotFoundError",
    "SagaAlreadyExistsError",
    "SagaCompensationError",
    # Implementations
    "InMemorySagaStore",
]
