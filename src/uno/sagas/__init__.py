# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Public API for the Uno sagas package.

This module exports the public API for sagas/process managers in the Uno framework,
providing orchestration and coordination capabilities for long-running processes.
"""

from uno.sagas.errors import (
    SagaAlreadyExistsError,
    SagaCompensationError,
    SagaError,
    SagaNotFoundError,
    SagaStoreError,
)
from uno.sagas.implementations.memory import InMemorySagaStore
from uno.sagas.manager import SagaManager
from uno.sagas.protocols import SagaProtocol, SagaState, SagaStoreProtocol

__all__ = [
    # Core protocols, errors, implementations and manager - sorted alphabetically
    "InMemorySagaStore",
    "SagaAlreadyExistsError",
    "SagaCompensationError",
    "SagaError",
    "SagaManager",
    "SagaNotFoundError",
    "SagaProtocol",
    "SagaState",
    "SagaStoreError",
    "SagaStoreProtocol",
]
