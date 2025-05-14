"""
Type definitions for uno DI system.
"""

from typing import Any
from uno.types import T
from typing import TypeVar

T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
