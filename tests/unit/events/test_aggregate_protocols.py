import logging
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from examples.app.domain.inventory.value_objects import Money
from examples.app.domain.order.events import (
    OrderCancelled,
    OrderCreated,
    OrderFulfilled,
)
from examples.app.domain.order.order import Order
from examples.app.domain.vendor.events import (
    VendorCreated,
    VendorEmailUpdated,
    VendorUpdated,
)
from examples.app.domain.vendor.value_objects import EmailAddress
from examples.app.domain.vendor.vendor import Vendor
from uno.domain.aggregate import AggregateRoot
from uno.events.base import DomainEvent


def create_test_email(email_str: str) -> EmailAddress:
    """Helper to create an EmailAddress instance for testing."""
    return EmailAddress(value=email_str)


def create_test_money(amount: str = "100.00", currency: str = "USD") -> Money:
    """Helper to create a Money instance for testing."""
    return Money(amount=Decimal(amount), currency=currency)


@pytest.fixture(autouse=True)
def setup_logging(monkeypatch):
    """Set up test logger for all tests."""
    # Create a mock logger
    mock_logger = MagicMock(spec=logging.Logger)

    # Patch the logger in the AggregateRoot class
    from uno.domain.aggregate import AggregateRoot

    # Save the original __init__ method
    original_init = AggregateRoot.__init__

    # Create a patched __init__ method
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._logger = mock_logger

    # Apply the patch
    monkeypatch.setattr(AggregateRoot, "__init__", patched_init)

    yield

    # The monkeypatch fixture will automatically undo the patch


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
def test_domain_event_protocol_conformance(
    event_cls: type[DomainEvent],
) -> None:
    # Instead of using issubclass(), we'll check the protocol members directly
    # since the protocol has non-method members and isn't runtime checkable

    # Check required protocol methods/attributes
    required_attrs = {
        # Class attributes
        "event_type": str,
        "version": int,
        # Instance attributes
        "event_id": str,
        "aggregate_id": str,
        # Methods
        "to_dict": callable,
        "from_dict": callable,
        "upcast": callable,
        "serialize": callable,
        "deserialize": callable,
    }

    # Create a properly initialized instance with required fields
    if event_cls is OrderCreated:
        instance = event_cls.create(
            order_id="O1",
            aggregate_id="A1",
            lot_id="L1",
            vendor_id="V1",
            measurement=1.0,
            price=create_test_money(),
            order_type="purchase",
        )
    elif event_cls is OrderFulfilled:
        instance = event_cls.create(
            order_id="O1", fulfilled_measurement=1.0, aggregate_id="A1"
        )
    elif event_cls is OrderCancelled:
        instance = event_cls.create(order_id="O1", reason="Test", aggregate_id="A1")
    elif event_cls is VendorCreated:
        instance = event_cls.create(
            vendor_id="V1", name="Test Vendor", contact_email="test@example.com"
        )
    elif event_cls is VendorUpdated:
        instance = event_cls.create(
            vendor_id="V1", name="Updated Vendor", contact_email="updated@example.com"
        )
    elif event_cls is VendorEmailUpdated:
        instance = event_cls.create(
            vendor_id="V1",
            old_email=create_test_email("old@example.com"),
            new_email=create_test_email("new@example.com"),
        )
    else:
        raise ValueError(f"Unhandled event type: {event_cls.__name__}")

    # Verify all required attributes exist and have the correct type
    for attr, expected_type in required_attrs.items():
        value = getattr(instance, attr, None)
        assert value is not None, f"Missing required attribute: {attr}"
        if expected_type is not callable:  # Skip callable checks for methods
            actual_type = type(value).__name__
            expected_type_name = expected_type.__name__
            assert isinstance(
                value, expected_type
            ), f"{attr} has incorrect type: {actual_type}, expected {expected_type_name}"


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

    # Create appropriate aggregate and test event
    if aggregate_cls is Order:
        # Create Order with proper value objects
        agg = aggregate_cls.create(
            order_id="O1",
            aggregate_id="A1",
            lot_id="L1",
            vendor_id="V1",
            measurement=1.0,
            price=create_test_money(),
            order_type="purchase",
        )
        # Clear any events from creation
        agg.clear_events()
        # Create an event for testing
        event = OrderCreated.create(
            order_id="O1",
            aggregate_id="A1",
            lot_id="L1",
            vendor_id="V1",
            measurement=1.0,
            price=create_test_money(),
            order_type="purchase",
        )
    else:
        # Create Vendor with proper value objects
        agg = aggregate_cls.create(
            vendor_id="V1",
            name="Test Vendor",
            contact_email=create_test_email("test@example.com"),
        )
        # Clear any events from creation
        agg.clear_events()
        # Create an event for testing
        event = VendorUpdated.create(
            vendor_id="V1",
            name="Updated Vendor",
            contact_email=create_test_email("updated@example.com"),
            aggregate_id="V1",  # Add required aggregate_id
        )

    # Test event handling
    agg.add_event(event)
    assert event in agg.get_uncommitted_events()
    agg.clear_events()
    assert not agg.get_uncommitted_events()
