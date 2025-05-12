"""Type stubs for test_snapshots.py"""

from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

def asyncio_test(func: T) -> T: ...

T = TypeVar('T', bound=Callable[..., Coroutine[Any, Any, None]])
