# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Implementation modules for the projections package.

This package contains concrete implementations of the projection protocols.
"""

from uno.projections.implementations.memory import InMemoryProjectionStore

__all__ = [
    "InMemoryProjectionStore",
]
