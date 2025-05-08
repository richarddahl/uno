"""
Configuration-related error classes for the Uno framework.

This module contains error classes that represent configuration-related exceptions.
"""

from typing import Any, Dict
from uno.errors.base import UnoError


class ConfigNotFoundError(UnoError):
    """Error raised when a configuration setting is not found."""


class ConfigInvalidError(UnoError):
    """Error raised when a configuration setting is invalid."""


class ConfigTypeMismatchError(UnoError):
    """Error raised when a configuration setting has the wrong type."""
