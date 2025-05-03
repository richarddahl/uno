# Vendor Bounded Context

This package contains all aggregates, events, and value objects specific to the Vendor domain.

## Structure

- `aggregates/`: Vendor aggregate root and related entities
- `events/`: Domain events specific to Vendor lifecycle
- `value_objects/`: Value objects specific to Vendor domain

## Usage

```python
from uno.domain.vendor.aggregates import Vendor
from uno.domain.vendor.events import VendorCreated
```

## Domain Invariants

- A Vendor must have a unique ID
- A Vendor must have a valid name (non-empty string)
- A Vendor must have a valid contact email address

## Cross-Context Dependencies

- None (all vendor-specific logic is contained within this context)

## Testing

All tests for this context are located in `uno/tests/domain/vendor/`.
