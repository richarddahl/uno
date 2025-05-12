"""
Error factory pattern for Uno core components.
Ensures consistent error creation and context propagation.
"""

from uno.errors.base import UnoError
from uno.errors.context import enrich_error
from uno.di import injectable
from typing import Any


@injectable
def make_error(message: str, code: str, **context: Any) -> UnoError:
    """Create a UnoError with context enrichment.

    Args:
        message: Error message
        code: Error code string
        **context: Additional context for enrichment
    Returns:
        UnoError enriched with context
    """
    err = UnoError(message=message, code=code, **context)
    return enrich_error(err)
