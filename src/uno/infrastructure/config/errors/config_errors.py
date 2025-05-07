"""
Configuration-related error classes for the Uno framework.

This module contains error classes that represent configuration-related exceptions.
"""

from typing import Any, Dict
from uno.core.errors.base import FrameworkError

class ConfigNotFoundError(FrameworkError):
    """Error raised when a configuration setting is not found."""

class ConfigInvalidError(FrameworkError):
    """Error raised when a configuration setting is invalid."""

class ConfigTypeMismatchError(FrameworkError):
    """Error raised when a configuration setting has the wrong type."""
