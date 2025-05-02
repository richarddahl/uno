# Uno Domain Modeling Guide

This guide walks you through modeling your own domain in Uno, using modern DDD and event sourcing patterns.

## 1. Overview

Uno separates your business logic (domain) from infrastructure and API. You can start modeling and testing your aggregates, events, and value objects immediately—no infra required!

## 2. Example Structure

- Aggregates: [examples/app/domain/inventory/item.py](../../examples/app/domain/inventory/item.py)
- Events: [examples/app/domain/events.py](../../examples/app/domain/events.py)
- Value Objects: [examples/app/domain/value_objects.py](../../examples/app/domain/value_objects.py)
- Tests: [examples/app/tests/](../../examples/app/tests/)

## 3. Step-by-Step: Model Your First Aggregate

### a. Define an Aggregate

```python
# mydomain/aggregate.py
from uno.core.domain import AggregateRoot, DomainEvent
from uno.core.errors import Result, Success, Failure, DomainValidationError, get_error_context

class MyAggregate(AggregateRoot[str]):
    name: str

    @classmethod
    def create(cls, aggregate_id: str, name: str) -> Result["MyAggregate", Exception]:
        if not aggregate_id or not name:
            return Failure(DomainValidationError("Missing required fields", details=get_error_context()))
        agg = cls(id=aggregate_id, name=name)
        agg._record_event(MyAggregateCreated(aggregate_id, name))
        return Success(agg)
```

### b. Define Events

```python
# mydomain/events.py
from uno.core.domain import DomainEvent
from uno.core.errors import Result, Success, Failure, DomainValidationError

class MyAggregateCreated(DomainEvent):
    aggregate_id: str
    name: str
    version: int = 1

    @classmethod
    def create(cls, aggregate_id: str, name: str, version: int = 1) -> Result["MyAggregateCreated", Exception]:
        if not aggregate_id or not name:
            return Failure(DomainValidationError("Missing required fields"))
        return Success(cls(aggregate_id=aggregate_id, name=name, version=version))

    def upcast(self, target_version: int) -> Result["MyAggregateCreated", Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented"))
```

### c. Define Value Objects

```python
# mydomain/value_objects.py
from uno.core.domain import ValueObject
from uno.core.errors import Result, Success, Failure, DomainValidationError

class SKU(ValueObject):
    value: str

    @classmethod
    def from_value(cls, value: str) -> Result["SKU", Exception]:
        if not value or len(value) < 3:
            return Failure(DomainValidationError("SKU must be at least 3 chars"))
        return Success(cls(value=value))
```

### d. Write and Run Tests

```python
# tests/test_mydomain.py
from mydomain.aggregate import MyAggregate

def test_create_aggregate_success():
    result = MyAggregate.create("A123", "Test Aggregate")
    assert result.is_success
    agg = result.value
    assert agg.name == "Test Aggregate"
```

Run all tests:

```bash
hatch run test:testV
```

## 4. Best Practices

- Always use the Result monad for construction and error handling.
- Use Pydantic v2 for all models.
- Implement `validate()` methods for invariants.
- Use upcasting for event versioning.

## 5. Explore More Examples

- [InventoryItem](../../examples/app/domain/inventory/item.py)
- [InventoryLot](../../examples/app/domain/inventory/lot.py)
- [PaymentReceived](../../examples/app/domain/events.py)
- [Quantity](../../examples/app/domain/value_objects.py)

## 6. Next Steps

- Add more aggregates, events, and value objects as needed.
- Use the example tests as a template for your own.
- When ready, integrate with Uno’s infrastructure and API layers.

---

## Need Help?

- Join the Uno community chat (see project root README)
- Open an issue or PR for improvements!
