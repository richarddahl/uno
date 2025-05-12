import inspect
import pytest
from uno.domain.protocols import DomainEventProtocol
from uno.events.base_event import DomainEvent
from uno.domain.aggregate import AggregateRoot
from examples.app.domain.order.order import Order
from examples.app.domain.order.events import (
    OrderCreated,
    OrderFulfilled,
    OrderCancelled,
)
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.vendor.events import (
    VendorCreated,
    VendorUpdated,
    VendorEmailUpdated,
)


@pytest.mark.parametrize(
    "event_cls",
    [
        OrderCreated,
        OrderFulfilled,
        OrderCancelled,
        VendorCreated,
        VendorUpdated,
        VendorEmailUpdated,
    ],
)
def test_domain_event_protocol_conformance(event_cls: type[DomainEvent]) -> None:
    assert issubclass(event_cls, DomainEventProtocol)
    # Check required protocol methods/attributes
    for attr in (
        "event_id",
        "aggregate_id",
        "event_type",
        "version",
        "to_dict",
        "from_dict",
        "upcast",
        "serialize",
        "deserialize",
    ):
        assert hasattr(event_cls, attr) or hasattr(event_cls(), attr)


@pytest.mark.parametrize("aggregate_cls", [Order, Vendor])
def test_aggregate_root_event_methods(aggregate_cls: type[AggregateRoot]) -> None:
    # Check canonical event sourcing methods
    for method in (
        "add_event",
        "apply_event",
        "from_events",
        "publish_events",
        "clear_events",
    ):
        assert hasattr(aggregate_cls, method) or hasattr(aggregate_cls(), method)

    # Ensure add_event and clear_events work as expected
    agg = aggregate_cls.__new__(aggregate_cls)
    agg._domain_events = []
    event = (
        OrderCreated(
            order_id="O1",
            aggregate_id="A1",
            lot_id="L1",
            vendor_id="V1",
            measurement=1,
            price=1,
            order_type="purchase",
        )
        if aggregate_cls is Order
        else VendorCreated(
            vendor_id="V1", name="Test", contact_email="test@example.com"
        )
    )
    agg.add_event(event)
    assert event in agg._domain_events
    agg.clear_events()
    assert not agg._domain_events
