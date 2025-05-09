"""
Type definitions for uno DI system.
"""

from typing import Any, TypeVar

T = TypeVar("T", bound=Any)
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
