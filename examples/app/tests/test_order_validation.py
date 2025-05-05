"""
Unit tests for the Order aggregate validate() method.
"""

import pytest
from decimal import Decimal
from typing import Any, Literal

import pytest
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Money, Currency
from examples.app.domain.order import Order
from uno.core.errors.result import Success, Failure


@pytest.mark.parametrize(
    "order_type,is_fulfilled,is_cancelled,expect_success",
    [
        ("purchase", False, False, True),
        ("sale", False, False, True),
        ("purchase", True, True, False),
    ],
)
def test_order_validate_domain_invariants(
    order_type: str, is_fulfilled: bool, is_cancelled: bool, expect_success: bool
):
    # Use valid value objects for all required fields
    measurement = Measurement.from_count(10)
    price = Money.from_value(Decimal('100.00'), Currency.USD).unwrap()
    
    order = Order(
        id="O1",
        aggregate_id="I1",
        lot_id="L1",
        vendor_id="V1",
        measurement=measurement,
        price=price,
        order_type=order_type,
        is_fulfilled=is_fulfilled,
        is_cancelled=is_cancelled,
    )
    result = order.validate()
    if expect_success:
        assert isinstance(result, Success)
    else:
        assert isinstance(result, Failure)
