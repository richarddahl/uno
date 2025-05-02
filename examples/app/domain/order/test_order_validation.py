"""
Unit tests for the Order aggregate validate() method.
"""
import pytest
from examples.app.domain.order.order import Order
from examples.app.domain.value_objects import Quantity, Money, Currency
from uno.core.errors.result import Success, Failure

@pytest.mark.parametrize(
    "order_type,is_fulfilled,is_cancelled,expect_success",
    [
        ("purchase", False, False, True),
        ("sale", False, False, True),
        ("purchase", True, True, False),
    ],
)
def test_order_validate_domain_invariants(order_type, is_fulfilled, is_cancelled, expect_success):
    # Use valid value objects for all required fields
    quantity = Quantity.from_count(10)
    money_result = Money.from_value("100", Currency.USD)
    price_obj = money_result.value if isinstance(money_result, Success) else None
    order = Order(
        id="O1",
        item_id="I1",
        lot_id="L1",
        vendor_id="V1",
        quantity=quantity,
        price=price_obj,
        order_type=order_type,
        is_fulfilled=is_fulfilled,
        is_cancelled=is_cancelled,
    )
    result = order.validate()
    if expect_success:
        assert isinstance(result, Success)
    else:
        assert isinstance(result, Failure)
