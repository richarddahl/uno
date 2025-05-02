# Vendor Bounded Context

This package contains all aggregates, events, and value objects specific to the Vendor domain.

- Place all vendor-specific domain logic here.
- Use `events.py` for vendor events.
- Use `vendor.py` for aggregates/entities.
- Add value objects here if they are only relevant to the Vendor context; otherwise, keep them in `domain/value_objects.py`.
