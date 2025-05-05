# Uno Domain Modeling Guide for Distillery Management

This guide walks you through modeling a distillery management domain in Uno, using modern Domain-Driven Design (DDD) and event sourcing patterns.

## 1. Understanding the Distillery Domain

Distilleries have unique domain concepts and regulatory requirements that make them ideal candidates for DDD and event sourcing:

- **Material Traceability**: Tracking raw materials from receipt through production to finished goods
- **Production Processes**: Mashing, fermentation, distillation, aging, blending, bottling
- **Quality Control**: Measuring and recording quality parameters throughout production
- **Regulatory Compliance**: TTB reporting, proof gallon calculations, tax determinations
- **Inventory Management**: Managing barrels, tanks, and finished goods

Uno separates your business logic (domain) from infrastructure and API, allowing you to model these concepts clearly and test them independently.

## 2. Distillery Domain Structure

The example app organizes the distillery domain into these key components:

- **Aggregates**:  
  - [InventoryItem](../../examples/app/domain/inventory/item.py) - Raw materials, in-process spirits, finished products
  - [InventoryLot](../../examples/app/domain/inventory/lot.py) - Specific batches with quality attributes
  - [Vendor](../../examples/app/domain/vendor/vendor.py) - Suppliers and customers
  - [Order](../../examples/app/domain/order/order.py) - Purchase and sale transactions

- **Events**:  
  - [Inventory Events](../../examples/app/domain/inventory/events.py) - Creation, adjustment, splitting, combining
  - [Vendor Events](../../examples/app/domain/vendor/events.py) - Creation, updates
  - [Order Events](../../examples/app/domain/order/events.py) - Creation, fulfillment, cancellation

- **Value Objects**:  
  - [Measurement](../../examples/app/domain/inventory/measurement.py) - Volume, mass, count
  - [Quality Parameters](../../examples/app/domain/inventory/value_objects.py) - Grade, alcohol content

- **Tests**: [examples/app/tests/](../../examples/app/tests/) - Domain logic validation

## 3. Step-by-Step: Modeling Distillery Concepts

### a. Define a Distillery Aggregate

Let's model a barrel for aging spirits:

```python
# domain/barrel.py
from typing import Self
from pydantic import PrivateAttr, model_validator
from datetime import datetime, timedelta

from uno.core.domain.aggregate import AggregateRoot
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Result, Success
from uno.core.events import DomainEvent

from domain.barrel.events import BarrelCreated, BarrelFilled, BarrelEmptied
from domain.inventory.value_objects import AlcoholContent

class Barrel(AggregateRoot[str]):
    """Represents a barrel used for aging spirits."""
    
    wood_type: str  # e.g., American Oak, French Oak
    char_level: int  # Char level 1-4
    capacity_liters: float
    fill_date: datetime | None = None
    contents_lot_id: str | None = None
    contents_abv: AlcoholContent | None = None
    is_active: bool = True
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)
    
    @classmethod
    def create(
        cls, 
        barrel_id: str, 
        wood_type: str, 
        char_level: int,
        capacity_liters: float
    ) -> Result[Self, Exception]:
        """Create a new barrel for aging spirits."""
        try:
            if not barrel_id:
                return Failure(
                    DomainValidationError("barrel_id is required", details=get_error_context())
                )
            if not wood_type:
                return Failure(
                    DomainValidationError("wood_type is required", details=get_error_context())
                )
            if char_level < 1 or char_level > 4:
                return Failure(
                    DomainValidationError(
                        "char_level must be between 1 and 4", 
                        details=get_error_context()
                    )
                )
            if capacity_liters <= 0:
                return Failure(
                    DomainValidationError(
                        "capacity_liters must be positive", 
                        details=get_error_context()
                    )
                )
                
            barrel = cls(
                id=barrel_id,
                wood_type=wood_type,
                char_level=char_level,
                capacity_liters=capacity_liters
            )
            
            event = BarrelCreated(
                barrel_id=barrel_id,
                wood_type=wood_type,
                char_level=char_level,
                capacity_liters=capacity_liters
            )
            
            barrel._record_event(event)
            return Success(barrel)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))
```

### b. Define Domain Events for Distillery Operations

Events are immutable records of state changes in your domain. For distilleries, events provide the audit trail required for regulatory compliance.

```python
# domain/barrel/events.py
from datetime import datetime
from typing import ClassVar, Self

from pydantic import ConfigDict, model_validator

from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success
from uno.core.events import DomainEvent

from domain.inventory.value_objects import AlcoholContent

class BarrelCreated(DomainEvent):
    """Event: A new barrel was created for aging spirits."""
    
    barrel_id: str
    wood_type: str
    char_level: int
    capacity_liters: float
    version: int = 1
    model_config = ConfigDict(frozen=True)
    
    @classmethod
    def create(
        cls,
        barrel_id: str,
        wood_type: str,
        char_level: int,
        capacity_liters: float,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """Create a new BarrelCreated event with validation."""
        import logging
        
        logger = logging.getLogger(__name__)
        try:
            if not barrel_id:
                logger.error("[BarrelCreated.create] Invalid barrel_id: %r", barrel_id)
                return Failure(
                    DomainValidationError(
                        "barrel_id is required",
                        details={"barrel_id": barrel_id, **get_error_context()},
                    )
                )
                
            # Additional validations...
            
            event = cls(
                barrel_id=barrel_id,
                wood_type=wood_type,
                char_level=char_level,
                capacity_liters=capacity_liters,
                version=version,
            )
            
            logger.info(
                "[BarrelCreated.create] Event created - barrel_id=%s wood_type=%s",
                barrel_id,
                wood_type,
            )
            return Success(event)
        except Exception as e:
            logger.error("[BarrelCreated.create] Unexpected error: %s", str(e))
            return Failure(
                DomainValidationError(
                    str(e),
                    details={"barrel_id": barrel_id, **get_error_context()},
                )
            )

class BarrelFilled(DomainEvent):
    """Event: A barrel was filled with spirit."""
    
    barrel_id: str
    lot_id: str
    fill_date: datetime
    abv: AlcoholContent
    version: int = 1
    model_config = ConfigDict(frozen=True)
    
    @classmethod
    def create(
        cls,
        barrel_id: str,
        lot_id: str,
        abv: AlcoholContent,
        fill_date: datetime | None = None,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """Create a new BarrelFilled event with validation."""
        # Implementation similar to BarrelCreated
        # ...

class BarrelEmptied(DomainEvent):
    """Event: A barrel was emptied."""
    
    barrel_id: str
    emptied_date: datetime
    destination_lot_id: str | None = None  # Where the spirit went
    reason: str | None = None  # v2 field, added later
    version: int = 2  # Current version
    __version__: ClassVar[int] = 2  # Class-level version for upcasting
    
    model_config = ConfigDict(frozen=True)
    
    @classmethod
    def create(
        cls,
        barrel_id: str,
        emptied_date: datetime | None = None,
        destination_lot_id: str | None = None,
        reason: str | None = None,
        version: int = 2,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """Create a new BarrelEmptied event with validation."""
        # Implementation
        # ...
        
    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """Upcast event to target version."""
        from uno.core.events.base_event import EventUpcasterRegistry
        
        if target_version == self.version:
            return Success(self)
            
        if target_version > self.version:
            # Use upcaster registry to migrate
            data = self.model_dump()
            try:
                upcasted = EventUpcasterRegistry.apply(
                    type(self), data, self.version, target_version
                )
                return type(self).from_dict(upcasted)
            except Exception as exc:
                return Failure(
                    DomainValidationError(
                        f"Upcasting failed: {exc}",
                        details={
                            "from": self.version,
                            "to": target_version,
                            "error": str(exc),
                        },
                    )
                )
                
        return Failure(
            DomainValidationError(
                "Cannot downcast events",
                details={"from": self.version, "to": target_version},
            )
        )

# Define an upcaster function for v1 to v2 migration
def _upcast_barrel_emptied_v1_to_v2(data: dict[str, object]) -> dict[str, object]:
    """Upcast BarrelEmptied from v1 to v2 by adding the 'reason' field."""
    data = dict(data)  # Create a copy to avoid modifying the original
    if data.get("version", 1) == 1:
        data["reason"] = None  # Default value for new field
        data["version"] = 2
    return data

# Register the upcaster with the registry
EventUpcasterRegistry.register_upcaster(
    event_type=BarrelEmptied,
    from_version=1,
    upcaster_fn=_upcast_barrel_emptied_v1_to_v2,
)
```

### d. Define Value Objects for Distillery Quality Parameters

Value objects represent concepts in your domain that are defined by their attributes rather than identity. For distilleries, these include measurements, quality parameters, and regulatory values.

```python
# domain/quality/value_objects.py
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar

from pydantic import ConfigDict, Field, field_validator

from uno.core.domain import ValueObject

class SpiritType(Enum):
    """Types of spirits produced in the distillery."""
    WHISKEY = "whiskey"
    BOURBON = "bourbon"
    RYE = "rye"
    VODKA = "vodka"
    GIN = "gin"
    RUM = "rum"
    
    def __str__(self) -> str:
        return self.value

class AlcoholContent(ValueObject):
    """Value object representing alcohol by volume (ABV)."""
    
    # Constant for maximum ABV percentage
    MAX_ABV_PERCENT: ClassVar[float] = 100.0
    
    percentage: float  # ABV percentage
    proof: float | None = None  # US proof (ABV × 2)
    
    model_config = ConfigDict(frozen=True)
    
    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v: float | int | str) -> float:
        """Validate alcohol content percentage."""
        if not isinstance(v, float):
            v = float(str(v))
        if v < 0 or v > cls.MAX_ABV_PERCENT:
            raise ValueError(
                f"Alcohol content must be between 0 and {cls.MAX_ABV_PERCENT}%"
            )
        return v
    
    @field_validator("proof")
    @classmethod
    def validate_proof(cls, v: float | None, info: Any) -> float | None:
        """Calculate proof if not provided."""
        if v is None:
            # US proof is ABV × 2
            percentage = info.data.get("percentage", 0)
            return percentage * 2
        return v
    
    def __str__(self) -> str:
        """Return string representation of alcohol content."""
        return f"{self.percentage}% ABV ({self.proof} proof)"
    
    def tax_per_proof_gallon(self, volume_gallons: float) -> Decimal:
        """Calculate federal excise tax based on proof gallons."""
        # Current tax rate per proof gallon (as of 2025)
        TAX_RATE = Decimal("2.70")
        
        # Proof gallons = volume in gallons × (proof ÷ 100)
        proof_gallons = Decimal(str(volume_gallons)) * (Decimal(str(self.proof)) / Decimal("100"))
        
        return proof_gallons * TAX_RATE

class SensorySample(ValueObject):
    """Value object representing a sensory evaluation of a spirit."""
    
    aroma: int = Field(ge=1, le=10)  # 1-10 scale
    taste: int = Field(ge=1, le=10)   # 1-10 scale
    finish: int = Field(ge=1, le=10)  # 1-10 scale
    notes: str | None = None
    
    model_config = ConfigDict(frozen=True)
    
    def overall_score(self) -> float:
        """Calculate the overall sensory score."""
        return (self.aroma + self.taste + self.finish) / 3
    
    def __str__(self) -> str:
        return f"Sensory: {self.overall_score():.1f}/10 (A:{self.aroma} T:{self.taste} F:{self.finish})"

### e. Define Repositories for Data Access

Repositories encapsulate data access and storage for aggregates. They provide a layer of abstraction between your domain model and the underlying storage technology.

```python
# domain/repository/barrel_repository.py
from typing import Self

from uno.core.domain.repository import Repository
from uno.core.errors.result import Failure, Success
from uno.core.events.event_store import EventStore

from domain.barrel import Barrel

class BarrelRepository(Repository[Barrel, str]):
    """Repository for Barrel aggregates using event sourcing."""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        
    async def get(self, barrel_id: str) -> Success[Barrel, None] | Failure[None, Exception]:
        """Retrieve a barrel by ID by replaying its events."""
        result = await self.event_store.get_events_by_aggregate_id(barrel_id)
        
        if isinstance(result, Failure):
            return result
            
        events = result.unwrap()
        if not events:
            return Failure(BarrelNotFoundError(barrel_id))
            
        # Replay events to reconstruct the barrel
        barrel = Barrel.replay_from_events(barrel_id, events)
        return Success(barrel)
        
    async def save(self, barrel: Barrel) -> Success[None, None] | Failure[None, Exception]:
        """Save barrel events to the event store."""
        # Save all uncommitted events
        for event in barrel.get_uncommitted_events():
            result = await self.event_store.save_event(event)
            if isinstance(result, Failure):
                return result
                
        # Clear uncommitted events after successful save
        barrel.clear_uncommitted_events()
        return Success(None)

### f. Write and Run Tests

```python
# tests/domain/barrel/test_barrel.py
import pytest
from datetime import datetime
from uno.core.errors.result import Success, Failure

from domain.barrel import Barrel
from domain.inventory.value_objects import AlcoholContent

class TestBarrel:
    def test_create_success(self):
        # Test creating a barrel with valid parameters
        result = Barrel.create(
            barrel_id="barrel-123",
            wood_type="American Oak",
            char_level=3,
            capacity_liters=200.0
        )
        
        # Assert success and check properties
        assert isinstance(result, Success)
        barrel = result.unwrap()
        assert barrel.id == "barrel-123"
        assert barrel.wood_type == "American Oak"
        assert barrel.char_level == 3
        assert barrel.capacity_liters == 200.0
        assert barrel.is_active is True
        assert barrel.contents_lot_id is None
        
        # Check that an event was recorded
        events = barrel.get_uncommitted_events()
        assert len(events) == 1
        assert events[0].barrel_id == "barrel-123"
    
    def test_create_failure_invalid_char_level(self):
        # Test creating a barrel with invalid char level
        result = Barrel.create(
            barrel_id="barrel-123",
            wood_type="American Oak",
            char_level=5,  # Invalid: must be 1-4
            capacity_liters=200.0
        )
        
        # Assert failure and check error details
        assert isinstance(result, Failure)
        assert "char_level must be between 1 and 4" in str(result.error)
        
    def test_fill_barrel(self):
        # Create a barrel first
        barrel = Barrel.create(
            barrel_id="barrel-123",
            wood_type="American Oak",
            char_level=3,
            capacity_liters=200.0
        ).unwrap()
        
        # Clear events from creation
        barrel.clear_uncommitted_events()
        
        # Fill the barrel
        fill_date = datetime.now()
        result = barrel.fill(
            lot_id="spirit-lot-456",
            abv=AlcoholContent(percentage=62.5),
            fill_date=fill_date
        )
        
        # Assert success and check updated state
        assert isinstance(result, Success)
        assert barrel.contents_lot_id == "spirit-lot-456"
        assert barrel.contents_abv.percentage == 62.5
        assert barrel.fill_date == fill_date
        
        # Check that a fill event was recorded
        events = barrel.get_uncommitted_events()
        assert len(events) == 1
        assert events[0].barrel_id == "barrel-123"
        assert events[0].lot_id == "spirit-lot-456"
```

## 4. Regulatory Compliance Through Event Sourcing

Event sourcing is particularly valuable for distilleries due to strict regulatory requirements. The Uno framework provides built-in support for:

### a. TTB Reporting and Audit Trails

- **Complete Chain of Custody**: Every material movement is recorded as an event
- **Production Volume Tracking**: Events capture exact quantities at each production stage
- **Proof Gallon Calculations**: Value objects handle tax calculations based on alcohol content
- **Lot Genealogy**: Events like `InventoryLotSplit` and `InventoryLotsCombined` maintain complete traceability

### b. Example: Generating a TTB Report

```python
# reports/ttb_report.py
from datetime import datetime, timedelta
from typing import List

from uno.core.errors.result import Result, Success, Failure
from uno.core.events.event_store import EventStore

from domain.barrel.events import BarrelFilled, BarrelEmptied
from domain.inventory.events import InventoryLotCreated, InventoryLotAdjusted

async def generate_monthly_production_report(
    event_store: EventStore,
    start_date: datetime,
    end_date: datetime
) -> Result[dict, Exception]:
    """Generate a TTB-compliant monthly production report."""
    # Get all relevant events for the reporting period
    events_result = await event_store.get_events_by_date_range(start_date, end_date)
    if isinstance(events_result, Failure):
        return events_result
        
    events = events_result.unwrap()
    
    # Calculate production volumes, proof gallons, and taxes
    production_data = {
        "raw_materials_received": [],
        "spirits_produced": [],
        "spirits_bottled": [],
        "tax_determined": 0.0,
    }
    
    # Process events to build the report
    for event in events:
        if isinstance(event, InventoryLotCreated):
            # Handle new inventory
            pass
        elif isinstance(event, BarrelFilled):
            # Track spirit production
            pass
        elif isinstance(event, BarrelEmptied):
            # Track spirit movement
            pass
            
    return Success(production_data)
```

## 5. Implement Service Layer and API Endpoints

- **Implement Service Layer**: Create services that orchestrate operations across aggregates
- **Add API Endpoints**: Expose your domain model through a REST API
- **Integrate with External Systems**: Connect to measurement devices, barcode scanners, etc.
- **Implement Reporting**: Create TTB-compliant reports from event history
- **Add User Authentication**: Implement user roles for different distillery operations
- **Expand Test Coverage**: Add tests for error paths and edge cases
- **Optimize Performance**: Implement caching and query optimizations for reports

## 6. Reference Implementation

For a complete reference implementation, explore these examples in the Uno codebase:

- [InventoryItem](../../examples/app/domain/inventory/item.py) - Raw materials and finished products
- [InventoryLot](../../examples/app/domain/inventory/lot.py) - Batches with quality attributes
- [Vendor](../../examples/app/domain/vendor/vendor.py) - Suppliers and customers
- [Order](../../examples/app/domain/order/order.py) - Purchase and sale transactions
- [Inventory Events](../../examples/app/domain/inventory/events.py) - State changes in inventory
- [Value Objects](../../examples/app/domain/inventory/value_objects.py) - Domain concepts like measurements

---

## Need Help?

- Join the Uno community chat (see project root README)
- Open an issue or PR for improvements!
