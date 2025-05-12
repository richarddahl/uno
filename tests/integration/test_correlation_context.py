"""
Integration tests for Uno event correlation context.
"""
import pytest
from uno.events.correlation import EventCorrelationContext

def test_correlation_id_is_unique() -> None:
    ctx1 = EventCorrelationContext.new()
    ctx2 = EventCorrelationContext.new()
    assert ctx1.correlation_id != ctx2.correlation_id
    assert isinstance(ctx1.correlation_id, str)
    assert isinstance(ctx2.correlation_id, str)

def test_correlation_context_from_existing() -> None:
    cid = "test-correlation-1234"
    ctx = EventCorrelationContext.from_existing(cid)
    assert ctx.correlation_id == cid
