# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""Patch for making registry registrations idempotent."""

from uno.persistence.sql.config import SQLConfig
from uno.persistence.sql.registry import SQLConfigRegistry

# Save the original register method
original_register = SQLConfigRegistry.register


# Completely replace the register method to skip duplicates
def patched_register(cls, config_class: type["SQLConfig"]) -> None:
    """
    Register a SQLConfig class in the registry, skip if already registered.

    Args:
        config_class: SQLConfig class to register
    """
    if config_class.__name__ in cls._registry:
        # Skip registering the same class again
        return

    # Just add to the registry directly
    cls._registry[config_class.__name__] = config_class


# Apply the monkey patch
SQLConfigRegistry.register = classmethod(patched_register)
