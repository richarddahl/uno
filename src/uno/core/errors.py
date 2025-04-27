"""
Uno core custom domain errors for event sourcing and DDD.
"""

from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)

class Success(Generic[T, E]):
    def __init__(self, value: T):
        self.value = value
        self.is_success = True
        self.is_failure = False
        self.error = None

class Failure(Generic[T, E]):
    def __init__(self, error: E):
        self.value = None
        self.is_success = False
        self.is_failure = True
        self.error = error

