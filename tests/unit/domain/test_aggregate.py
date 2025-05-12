import inspect
import pytest
from uno.domain.protocols import AggregateRootProtocol, DomainEventProtocol
from examples.app.domain.order.order import Order
from examples.app.domain.order.events import OrderCreated


def test_order_conforms_to_aggregate_root_protocol() -> None:
    assert issubclass(Order, AggregateRootProtocol)
    required_methods = [
        method_name
        for method_name, method in inspect.getmembers(AggregateRootProtocol)
        if inspect.isfunction(method) and not method_name.startswith("_")
    ]
    for method_name in required_methods:
        assert hasattr(Order, method_name)
        assert callable(getattr(Order, method_name, None))


def test_order_event_sourcing_methods() -> None:
    order = Order.create(
        order_id="o1",
        aggregate_id="a1",
        lot_id="l1",
        vendor_id="v1",
        measurement=1,
        price=OrderCreated.create(
            price=1,
            order_id="o1",
            aggregate_id="a1",
            lot_id="l1",
            vendor_id="v1",
            measurement=1,
            order_type="purchase",
        ).price,
        order_type="purchase",
    )
    assert hasattr(order, "add_event")
    assert hasattr(order, "apply_event")
    assert hasattr(Order, "from_events")
    assert callable(order.add_event)
    assert callable(order.apply_event)
    assert callable(Order.from_events)
    # Test event sourcing roundtrip
    events = order._domain_events.copy()
    replayed = Order.from_events(events)
    assert replayed.aggregate_id == order.aggregate_id
    assert replayed.lot_id == order.lot_id
    assert replayed.vendor_id == order.vendor_id
    assert replayed.measurement == order.measurement
    assert replayed.price == order.price
    assert replayed.order_type == order.order_type
