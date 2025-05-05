# Uno Distillery Management System Example

## Overview

This example application demonstrates how to use Uno to build a production-ready distillery management system using Domain-Driven Design (DDD) and Event Sourcing principles. The system manages inventory items, lots, vendors, and orders with a focus on the specific needs of distillery operations.

## Domain Model

The domain model is organized around key distillery concepts:

### Aggregates

1. **InventoryItem** - Represents raw materials, in-process spirits, or finished products
   - Tracks name and measurement (count, volume, or mass)
   - Supports renaming and measurement adjustments
   - Events: `InventoryItemCreated`, `InventoryItemRenamed`, `InventoryItemAdjusted`

2. **InventoryLot** - Represents a specific batch or lot of an inventory item
   - Tracks source vendor, measurements, and quality grades
   - Supports lot splitting and combining for production processes
   - Maintains audit trail of source lots for compliance
   - Events: `InventoryLotCreated`, `InventoryLotAdjusted`, `InventoryLotSplit`, `InventoryLotsCombined`

3. **Vendor** - Represents suppliers or customers
   - Tracks name and contact information
   - Events: `VendorCreated`, `VendorUpdated`

4. **Order** - Represents purchase or sale orders
   - Links to inventory lots and vendors
   - Tracks price, quantity, and fulfillment status
   - Events: `OrderCreated`, `OrderFulfilled`, `OrderCancelled`

### Value Objects

1. **Measurement** - Composite value object for different measurement types
   - `Count` - Discrete items (each, dozen, case, pallet)
   - `Mass` - Weight measurements (kg, g, lb, oz)
   - `Volume` - Volume measurements (L, mL, gal, oz)

2. **Grade** - Quality assessment for spirits (0-100 scale)

3. **AlcoholContent** - ABV percentage tracking

4. **Money** - Amount with currency for financial transactions

5. **EmailAddress** - Validated email contacts

## Getting Started

### Installation

```bash
# Install Uno in development mode
pip install -e ../../  # from the root of the uno repo

# Run the example app
python -m examples.app
```

### Explore the Domain Model

1. **Examine the aggregates:**
   - [`domain/inventory/item.py`](domain/inventory/item.py) - InventoryItem aggregate
   - [`domain/inventory/lot.py`](domain/inventory/lot.py) - InventoryLot aggregate
   - [`domain/vendor/vendor.py`](domain/vendor/vendor.py) - Vendor aggregate
   - [`domain/order/order.py`](domain/order/order.py) - Order aggregate

2. **Study the events:**
   - [`domain/inventory/events.py`](domain/inventory/events.py) - Inventory events
   - [`domain/vendor/events.py`](domain/vendor/events.py) - Vendor events
   - [`domain/order/events.py`](domain/order/events.py) - Order events

3. **Review value objects:**
   - [`domain/inventory/value_objects.py`](domain/inventory/value_objects.py) - Measurement, Grade, etc.
   - [`domain/inventory/measurement.py`](domain/inventory/measurement.py) - Measurement system
   - [`domain/vendor/value_objects.py`](domain/vendor/value_objects.py) - EmailAddress, etc.

---

## Distillery Management System Features

- **Inventory Tracking:** Track raw materials, in-process spirits, and finished products with appropriate measurements
- **Lot Management:** Manage production batches with quality grades, source tracking, and compliance audit trails
- **Vendor Relations:** Track suppliers and customers with validated contact information
- **Order Processing:** Handle purchase and sale orders with proper financial tracking
- **Measurement System:** Unified system for count, volume, and mass measurements with unit conversions
- **Quality Control:** Track spirit quality with standardized grading
- **Event Sourcing:** All state changes are recorded as domain events for audit and compliance
- **Modern Python:** Type hints, Pydantic 2, Python 3.13, strict linting

## Common Distillery Operations

### 1. Receiving Raw Materials

```python
# Create a vendor
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.vendor.value_objects import EmailAddress

vendor_result = Vendor.create(
    vendor_id="supplier-123",
    name="Grain Supplier Inc.",
    contact_email=EmailAddress(value="contact@grainsupplier.com")
)
vendor = vendor_result.unwrap()

# Create an inventory item for the raw material
from examples.app.domain.inventory.item import InventoryItem

barley_result = InventoryItem.create(
    aggregate_id="barley-001",
    name="Malted Barley",
    measurement=5000  # 5000 kg
)
barley = barley_result.unwrap()

# Create a specific lot of this material
from examples.app.domain.inventory.lot import InventoryLot

lot_result = InventoryLot.create(
    lot_id="lot-barley-001",
    aggregate_id="barley-001",
    measurement=5000,
    vendor_id="supplier-123",
    purchase_price=2500.00
)
lot = lot_result.unwrap()
```

### 2. Production Process - Mashing and Fermentation

```python
# Split the barley lot for a specific production batch
from examples.app.domain.inventory.lot import InventoryLot

# Get the source lot
source_lot = repository.get("lot-barley-001").unwrap()

# Split off 500kg for this production batch
split_result = source_lot.split(
    new_lot_ids=["mash-batch-001"],
    split_quantities=[500],
    reason="Production batch #42"
)

# Create a new inventory item for the mash
mash_result = InventoryItem.create(
    aggregate_id="mash-001",
    name="Fermented Mash",
    measurement=1200  # 1200 liters after adding water
)
```

### 3. Distillation and Quality Control

```python
# Create a new lot for the distilled spirit
from examples.app.domain.inventory.value_objects import Grade, AlcoholContent

# Create the distilled spirit inventory item
spirit_result = InventoryItem.create(
    aggregate_id="spirit-001",
    name="Raw Whiskey",
    measurement=150  # 150 liters of distilled spirit
)

# Create a lot with quality information
from examples.app.domain.inventory.measurement import Measurement, Volume
from examples.app.domain.inventory.value_objects import VolumeUnit

volume = Volume(value=150, unit=VolumeUnit.LITER)
measurement = Measurement.from_volume(volume)

spirit_lot_result = InventoryLot.create(
    lot_id="spirit-batch-001",
    aggregate_id="spirit-001",
    measurement=measurement,
    vendor_id=None  # Produced internally
)
spirit_lot = spirit_lot_result.unwrap()

# Assign quality grade and alcohol content
from examples.app.domain.inventory.events import GradeAssignedToLot
from examples.app.domain.vendor.value_objects import EmailAddress

grade_event = GradeAssignedToLot.create(
    lot_id="spirit-batch-001",
    grade=Grade(value=92.5),  # High quality
    assigned_by=EmailAddress(value="master.distiller@example.com")
).unwrap()

# Record the event
spirit_lot._record_event(grade_event)
```

### 4. Aging and Blending

```python
# After aging, combine multiple spirit lots for blending
from examples.app.domain.inventory.lot import InventoryLot

# Get the aged lots to be blended
lot1 = repository.get("aged-lot-001").unwrap()
lot2 = repository.get("aged-lot-002").unwrap()

# Combine the lots
combined_result = InventoryLot.combine_lots(
    lot_ids=["aged-lot-001", "aged-lot-002"],
    new_lot_id="blended-batch-001"
)
blended_lot = combined_result.unwrap()

# The blended lot automatically has:
# - Combined measurement from source lots
# - Weighted average grade based on source lot grades
# - Complete audit trail of source lots for compliance
```

### 5. Bottling and Sales

```python
# Create a finished product inventory item
bottled_result = InventoryItem.create(
    aggregate_id="whiskey-premium",
    name="Premium Aged Whiskey",
    measurement=750  # 750ml bottles
)

# Create an order for a customer
from examples.app.domain.order.order import Order
from examples.app.domain.inventory.value_objects import Money, Currency

order_result = Order.create(
    order_id="order-001",
    aggregate_id="whiskey-premium",
    lot_id="blended-batch-001",
    vendor_id="customer-456",  # The customer
    measurement=120,  # 120 bottles
    price=Money(amount=59.99, currency=Currency.USD),
    order_type="sale"
)
order = order_result.unwrap()

# Fulfill the order
order.fulfill(120)  # Fulfill the complete order

# This automatically updates inventory
```

---

## Uno DDD & Event Sourcing Philosophy

Uno encourages:

- **Explicit domain modeling**: Aggregates, events, and value objects are first-class.
- **Loose coupling**: Dependency Injection (DI) for all services and repositories. Service registration order matters: LoggerService must be registered before services that depend on it.
- **Event sourcing**: Every state change is an event; aggregates replay their history.
- **Structured logging** and **centralized config** (see Uno core docs). LoggerService is injected into all services for consistent, contextual logging.

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

4. **Run all tests:**

   ```bash
   hatch run test:testV
   ```

---

## Aggregates & API Endpoints

### Value Objects: Strongly-Typed Domain Data

Uno provides a canonical ValueObject base class for small, immutable, and validated domain concepts (e.g., Grade, EmailAddress). ValueObjects leverage Pydantic's built-in validation and are:

- Immutable and compared by value
- Validated using Pydantic's built-in field constraints and validators
- Serializable with Pydantic's model_dump/model_serialize features
- Compatible with Uno's Result-based error handling

### Example: Grade and EmailAddress

```python
from uno.examples.app.domain.value_objects import Grade, EmailAddress
from uno.core.errors.result import Success, Failure

# Direct construction with validation
g = Grade(raw_value=95.5)  # valid
# g = Grade(raw_value=150)  # raises ValidationError - value outside allowed range

# Using specialized Pydantic types
e = EmailAddress(value="foo@bar.com")  # valid - uses Pydantic's EmailStr validation
# e = EmailAddress(value="not-an-email")  # raises ValidationError

# Result pattern for error handling
result = Grade.from_value(95.5)  # Returns Success(Grade)
if result.is_success:
    grade = result.value
else:
    # Handle validation error
    error = result.error
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

## Event Sourcing for Regulatory Compliance

Distilleries are subject to strict regulatory requirements. The event sourcing approach in Uno provides built-in compliance capabilities:

### Complete Audit Trail

- Every state change is recorded as an immutable event with timestamps and user attribution
- Full history of all inventory movements, quality assessments, and production processes
- Chain of custody for all materials from receipt through production to sale

### TTB Compliance Features

- Track production volumes and losses at each stage (required for TTB reporting)
- Document alcohol content measurements throughout the process
- Maintain complete lot genealogy for recall capabilities
- Record proof gallons for tax calculations

### Example: Retrieving Complete Lot History

```python
# Get all events for a specific lot
from examples.app.persistence.repository import EventStore

event_store = EventStore()
result = event_store.get_events_by_aggregate_id("lot-whiskey-001")

if isinstance(result, Success):
    events = result.unwrap()
    
    # Process events chronologically
    for event in events:
        if isinstance(event, InventoryLotCreated):
            print(f"Lot created on {event.timestamp} with {event.measurement}")
        elif isinstance(event, GradeAssignedToLot):
            print(f"Quality grade {event.grade} assigned by {event.assigned_by}")
        elif isinstance(event, InventoryLotSplit):
            print(f"Split into lots: {event.new_lot_ids}")
        # etc.
```

### Reporting Capabilities

- Generate TTB-compliant reports directly from event history
- Calculate production efficiency and losses
- Provide complete traceability for audits
- Document chain of custody for quality certifications

---

## Extending the Distillery Management System

### Adding New Distillery-Specific Aggregates

1. **Define the aggregate and events:**

   ```python
   # domain/barrel.py
   from typing import Self
   from pydantic import PrivateAttr
   from uno.core.domain.aggregate import AggregateRoot
   from uno.core.errors.result import Success, Failure, Result
   
   class Barrel(AggregateRoot[str]):
       wood_type: str  # e.g., American Oak, French Oak
       char_level: int  # Char level 1-4
       age_in_months: int = 0
       contents_lot_id: str | None = None
       is_active: bool = True
       _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)
       
       @classmethod
       def create(cls, barrel_id: str, wood_type: str, char_level: int) -> Result[Self, Exception]:
           # Implementation using Uno patterns
           pass
           
       def fill(self, lot_id: str) -> Result[None, Exception]:
           # Implementation
           pass
           
       def empty(self) -> Result[None, Exception]:
           # Implementation
           pass
   ```

2. **Define events for the new aggregate:**

   ```python
   # domain/barrel/events.py
   from uno.core.events import DomainEvent
   
   class BarrelCreated(DomainEvent):
       barrel_id: str
       wood_type: str
       char_level: int
       
       @classmethod
       def create(cls, barrel_id: str, wood_type: str, char_level: int):
           # Implementation using Uno patterns
           pass
   
   class BarrelFilled(DomainEvent):
       barrel_id: str
       lot_id: str
       filled_date: datetime
       
       # Implementation
   ```

3. **Add a repository:**

   ```python
   # persistence/barrel_repository.py
   from uno.core.domain.repository import Repository
   from domain.barrel import Barrel
   
   class BarrelRepository(Repository[Barrel, str]):
       # Implementation using Uno patterns
       pass
   ```

4. **Create API endpoints:**

   ```python
   # api/barrel_api.py
   from fastapi import APIRouter, Depends
   
   router = APIRouter(prefix="/barrels", tags=["barrels"])
   
   @router.post("/")
   async def create_barrel(barrel_data: BarrelCreateDTO):
       # Implementation
       pass
   ```

### Common Distillery-Specific Extensions

1. **Barrel Management**
   - Track individual barrels, their contents, and aging process
   - Monitor fill dates, rotation schedules, and tasting notes

2. **Blending Formulas**
   - Define and track proprietary blending recipes
   - Record blending decisions and outcomes

3. **Sensory Analysis**
   - Track tasting notes and sensory evaluations
   - Monitor flavor development during aging

4. **Regulatory Reporting**
   - Generate TTB-required reports automatically
   - Track excise tax calculations

5. **Production Scheduling**
   - Plan distillation runs and bottling operations
   - Optimize resource allocation

---

## Testing

Run all end-to-end and API tests:

```bash
hatch run test:testV
```

## Conclusion

The Uno Distillery Management System example demonstrates how to build a robust, event-sourced application for managing distillery operations. By leveraging Uno's core principles of Domain-Driven Design and Event Sourcing, this system provides:

- **Regulatory Compliance:** Complete audit trails and chain of custody for all materials
- **Quality Control:** Tracking of quality measurements throughout the production process
- **Production Traceability:** Full genealogy of all products from raw materials to finished goods
- **Extensibility:** Easy addition of distillery-specific features like barrel management or blending formulas

The example serves as both a practical implementation guide and a reference architecture for building your own domain-specific applications with Uno. By following the patterns demonstrated here, you can create maintainable, testable, and compliant systems for complex regulatory environments like distilleries.

## License

SPDX-License-Identifier: MIT

---
_This integrated example is for onboarding, regression, and demonstration purposes. For framework core logic, see `uno/core/`. For focused examples, see the top-level `examples/` directory._

---

## Modern API and Service Layer Idioms

- **Result-based Error Handling:** All service and API methods return `Result`, `Success`, or `Failure`. Errors are propagated with context and only converted to HTTP exceptions at the API boundary.
- **Dependency Injection:** All services receive dependencies (including `LoggerService`) via DI. Register `LoggerService` before other services in your DI container.
- **Type Hints & Pydantic v2:** All DTOs and domain models use Pydantic v2 and modern Python type hints (`str`, `int`, `X | Y` not `Union[X, Y]`).
- **Logging:** Use the injected logger for all business and API logic. Avoid print statements.
- **Testing:** Use pytest with fixtures and follow the `Fake`/`Mock` naming convention for test objects.
