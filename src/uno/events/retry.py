from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


class RetryError(Exception):
    """
    Raised when all retry attempts fail.
    """
    def __init__(self, last_exception: Exception, attempts: int) -> None:
        super().__init__(f"Retry failed after {attempts} attempts: {last_exception!s}")
        self.last_exception = last_exception
        self.attempts = attempts


async def retry_async(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """
    Retry an async function on failure with exponential backoff.

    Args:
        func: The async function to retry.
        *args: Positional arguments for the function.
        max_attempts: Maximum number of attempts.
        delay: Initial delay between attempts (seconds).
        backoff: Backoff multiplier for delay.
        exceptions: Exception types to catch and retry on.
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the function if successful.

    Raises:
        RetryError: If all attempts fail.
    """
    attempt = 0
    current_delay = delay
    while attempt < max_attempts:
        try:
            return await func(*args, **kwargs)
        except exceptions as exc:
            attempt += 1
            if attempt >= max_attempts:
                raise RetryError(last_exception=exc, attempts=attempt) from exc
            await asyncio.sleep(current_delay)
            current_delay *= backoff
