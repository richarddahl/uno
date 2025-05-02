# Uno Integrated Example App

## Domain Modeling Quickstart

Welcome! This quickstart will help you model your own domain in Uno using modern DDD and event sourcing patterns.

### Steps

1. **Explore the example domain:**
    - Aggregates: [`domain/inventory/item.py`](domain/inventory/item.py), [`domain/inventory/lot.py`](domain/inventory/lot.py)
    - Events: [`domain/events.py`](domain/events.py)
    - Value Objects: [`domain/value_objects.py`](domain/value_objects.py)
2. **Create your own aggregate:**
    - Copy the pattern from `InventoryItem` or `InventoryLot`.
    - Use Pydantic v2, modern type hints, and the Result monad for all construction and error handling.
3. **Define events for your aggregate:**
    - See `PaymentReceived`, `GradeAssignedToLot`, etc. in `events.py`.
    - Implement `create` and `upcast` classmethods.
4. **Add value objects as needed:**
    - See `Quantity`, `Grade`, `Count` in `value_objects.py`.
    - Use validation and Pydantic idioms.
5. **Write tests for your domain logic:**
    - See [`tests/`](tests/) for pytest-based examples.
    - Run all example tests with:
      ```bash
      hatch run test:testV
      ```
6. **No infrastructure or API required!**
   You can model, test, and validate your entire domain layer in isolation.

For a detailed walkthrough, see the [Domain Modeling Guide](../../docs/examples_app/domain_modeling.md).

---

## Uno Example Features

- **Aggregates:** `InventoryItem`, `Vendor` (add your own easily)
- **Event Sourcing:** All state changes are recorded as domain events
- **API Layer:** RESTful endpoints for all aggregates via FastAPI
- **Serialization:** Canonical DTOs using Pydantic v2
- **Testing:** End-to-end tests for all API endpoints
- **Extensibility:** Add new aggregates/events/endpoints with minimal boilerplate
- **Modern Python:** Type hints, Pydantic 2, Python 3.13, strict linting

---

## Uno DDD & Event Sourcing Philosophy

Uno encourages:
- **Explicit domain modeling**: Aggregates, events, and value objects are first-class.
- **Loose coupling**: DI for all services and repositories.
- **Event sourcing**: Every state change is an event; aggregates replay their history.
- **Structured logging** and **centralized config** (see Uno core docs).

---

## Project Structure

```text
app/
  domain/         # Domain models (aggregates, events)
  persistence/    # Event-sourced repositories
  api/            # FastAPI app, DTOs, API logic
  tests/          # End-to-end and integration tests
  __main__.py     # Entrypoint to run the example app
  README.md       # This file
```

---

## Running the Example App

1. **Install Uno in editable mode:**

   ```bash
   pip install -e ../../  # from the root of the uno repo
   ```

2. **Run the example app:**

   ```bash
   python -m examples.app
   ```
   _Note: This does not support hot reload._

   **For hot reload during development:**

   ```bash
   uvicorn examples.app.api.api:app --reload
   ```

3. **Explore the API:**
   - Visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI

---

## Aggregates & API Endpoints

### Value Objects: Strongly-Typed Domain Data

Uno provides a canonical ValueObject base class for small, immutable, and validated domain concepts (e.g., Grade, EmailAddress). ValueObjects are:
- Immutable and compared by value
- Validated on creation (using Pydantic)
- Provide `.to_dict()` and Uno-style error handling

### Example: Grade and EmailAddress

```python
from uno.examples.app.domain.value_objects import Grade, EmailAddress

g = Grade(value=95.5)  # valid
# g = Grade(value=150)  # raises ValidationError

e = EmailAddress(value="foo@bar.com")  # valid
# e = EmailAddress(value="not-an-email")  # raises ValidationError
```

You can use value objects in your aggregates/entities for stronger invariants:

```python
from uno.examples.app.domain.value_objects import Grade
from uno.examples.app.domain.inventory_lot import InventoryLot

class MyLot(InventoryLot):
    grade: Grade | None = None

    # ...
```

### InventoryLot Blending & Traceability

- **Blending:** Inventory lots can be combined, producing a new lot with a weighted average grade (e.g., protein %) and a complete list of all contributing vendors.
- **Traceability:** Every blend operation records all source lots, grades, and vendors in an `InventoryLotsCombined` event. The resulting lot maintains a traceable history of all its origins.
- **API Usage:**
  - **POST /inventory/combine/** — Combine two lots (see API docs for schema)

#### Example: Combine Two Lots

```bash
curl -X POST http://localhost:8000/inventory/combine/ \
  -H 'Content-Type: application/json' \
  -d '{
    "lot_ids": ["lot-1", "lot-2"],
    "new_lot_id": "lot-3"
  }'
```

**Result:**
- The new lot's `grade` is a weighted average of the source lots.
- The new lot's `_source_vendor_ids` contains all unique vendors from the sources.
- The `InventoryLotsCombined` event records all source lot IDs, grades, and vendors for audit/compliance.

---

### InventoryItem

- **POST /inventory/** — Create an item
- **GET /inventory/{item_id}** — Fetch an item
- **PUT /inventory/{item_id}** — Update an item
- **GET /inventory/** — List all items

#### Example: Create an InventoryItem

```bash
curl -X POST http://localhost:8000/inventory/ \
  -H 'Content-Type: application/json' \
  -d '{"id": "sku-123", "name": "Widget", "quantity": 10}'
```

**Response:**
```json
{
  "id": "sku-123",
  "name": "Widget",
  "quantity": 10
}
```

#### Example: Update InventoryItem

```bash
curl -X PUT http://localhost:8000/inventory/sku-123 \
  -H 'Content-Type: application/json' \
  -d '{"name": "Widget Pro", "quantity": 15}'
```

---

### Vendor

- **POST /vendors/** — Create a vendor
- **GET /vendors/{vendor_id}** — Fetch a vendor
- **PUT /vendors/{vendor_id}** — Update a vendor
- **GET /vendors/** — List all vendors

#### Example: Create a Vendor

```bash
curl -X POST http://localhost:8000/vendors/ \
  -H 'Content-Type: application/json' \
  -d '{"id": "vendor-1", "name": "Acme Distilling", "contact_email": "info@acme.com"}'
```

**Response:**
```json
{
  "id": "vendor-1",
  "name": "Acme Distilling",
  "contact_email": "info@acme.com"
}
```

#### Example: Update a Vendor

```bash
curl -X PUT http://localhost:8000/vendors/vendor-1 \
  -H 'Content-Type: application/json' \
  -d '{"name": "Acme Spirits", "contact_email": "hello@acme.com"}'
```

---

## Event Sourcing in Uno

- Every aggregate method (e.g. `create`, `update`) records a domain event.
- The repository stores events, not just current state.
- Aggregates are rebuilt by replaying their event history.
- See `domain/` for event classes (e.g. `InventoryItemCreated`, `VendorCreated`).

---

## Adding a New Aggregate

1. **Define the aggregate and events:**
   - Create `domain/my_aggregate.py` with your class and events.
2. **Add a repository:**
   - Create `persistence/my_aggregate_repository.py` (see vendor/inventory examples).
3. **Create DTOs:**
   - Add `api/my_aggregate_dtos.py`.
4. **Expose API endpoints:**
   - Update `api/api.py` to add your endpoints.
5. **Write tests:**
   - Add `tests/test_my_aggregate_api.py`.

---

## Testing

Run all end-to-end tests:

```bash
hatch run test:test-examplesV
```

---

## License

SPDX-License-Identifier: MIT

---
_This integrated example is for onboarding, regression, and demonstration purposes. For framework core logic, see `uno/core/`. For focused/legacy examples, see the top-level `examples/` directory._
