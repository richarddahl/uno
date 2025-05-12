# Event Replay and Upcasting Patterns

This document outlines the patterns and best practices for event replay and upcasting in the Uno framework's event sourcing system.

## Event Replay

Event replay is the process of reconstructing an aggregate's state by replaying its historical events. This is a fundamental concept in event sourcing that enables various powerful patterns.

### When to Use Event Replay

1. **Loading Aggregates**: When loading an aggregate from the event store
2. **Rebuilding Read Models**: When rebuilding projections or read models
3. **Auditing**: When examining the history of changes to an aggregate
4. **Testing**: When verifying the behavior of aggregates using historical events

### Event Replay Implementation

The Uno framework provides built-in support for event replay with the `AggregateRoot` base class:

```python
# Loading an aggregate using event replay
events = await event_store.get_events_by_aggregate_id(aggregate_id)
aggregate = MyAggregate.from_events(events)
```

#### Example: Replaying Events on an Aggregate

```python
class Order(AggregateRoot):
    def __init__(self, id: str):
        super().__init__(id)
        self.items = []
        self.status = "new"
        
    @classmethod
    def from_events(cls, events: list[DomainEventProtocol]) -> Self:
        """Create an instance by replaying events."""
        # Create a new instance
        instance = cls(events[0].aggregate_id if events else str(uuid4()))
        
        # Apply all events to reconstruct state
        for event in events:
            instance.apply_event(event)
            
        # Clear uncommitted events as these are historical
        instance.clear_uncommitted_events()
        return instance
        
    def apply_event(self, event: DomainEventProtocol) -> None:
        """Apply an event to update the aggregate state."""
        # Call the appropriate handler based on event type
        handler_method = f"_apply_{event.event_type}"
        handler = getattr(self, handler_method, None)
        
        if handler:
            handler(event)
        else:
            # Log warning about unhandled event
            logging.warning(f"No handler for event {event.event_type}")
            
        # Update version with the event's version
        self.version = event.version
```

## Event Upcasting

Event upcasting is the process of converting events from older versions to newer versions when the event schema has evolved.

### When to Use Upcasting

1. **Schema Evolution**: When you've changed the structure of an event
2. **Business Logic Changes**: When the meaning of certain fields has changed
3. **Data Enrichment**: When you need to add computed fields to older events

### Upcasting Implementation

Uno provides a standardized way to upcast events through the `upcast` method on the `DomainEvent` class:

```python
@classmethod
def upcast(cls, data: dict[str, Any]) -> dict[str, Any]:
    """
    Upcast an event data dictionary from an older version to the current version.
    
    Args:
        data: Event data dictionary from an older version
        
    Returns:
        Updated event data compatible with the current version
    """
    version = data.get("version", 1)
    
    # Call appropriate upcasting function based on version
    if version < cls.version:
        upcast_method = f"_upcast_v{version}_to_v{version + 1}"
        upcast_func = getattr(cls, upcast_method, None)
        
        if upcast_func:
            data = upcast_func(data)
            data["version"] = version + 1
            # Recursively upcast if needed
            return cls.upcast(data)
    
    return data
```

#### Example: Implementing Upcasting in an Event Class

```python
class OrderItemAdded(DomainEvent):
    event_type: ClassVar[str] = "OrderItemAdded"
    version: int = 2
    item_id: str
    product_id: str
    quantity: int
    unit_price: float
    
    # In v1, we didn't have the unit_price field
    
    @classmethod
    def _upcast_v1_to_v2(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Upcast from version 1 to version 2 by adding unit_price."""
        # Copy the data to avoid modifying the original
        result = data.copy()
        
        # Add the missing field with a default value
        if "unit_price" not in result:
            result["unit_price"] = 0.0
            
        return result
```

## Best Practices for Upcasting

1. **Keep it Simple**:
   - Each upcasting method should only handle conversion between adjacent versions
   - Use recursive upcasting for multiple version jumps

2. **Make it Explicit**:
   - Name upcasting methods clearly (e.g., `_upcast_v1_to_v2`)
   - Document what changed between versions

3. **Preserve Information**:
   - Never discard data during upcasting unless absolutely necessary
   - Provide sensible defaults for new required fields

4. **Test Thoroughly**:
   - Write tests for each upcasting transformation
   - Ensure events from all versions can be upcasted correctly

5. **Consider Performance**:
   - Upcasting happens during replay, which can be performance-sensitive
   - Keep transformations efficient, especially for high-volume events

## Advanced Upcasting Patterns

### Event Type Migration

Sometimes, you may need to completely change an event type:

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> DomainEvent:
    """Create an event from dictionary data with potential type migration."""
    event_type = data.get("event_type")
    
    # Handle legacy event types
    if event_type == "ProductAdded": 
        # This was renamed to "OrderItemAdded" in a newer version
        data["event_type"] = "OrderItemAdded"
        # Call the appropriate class's from_dict
        return OrderItemAdded.from_dict(data)
        
    return super().from_dict(data)
```

### Snapshot-Based Optimization

For aggregates with many events, consider using snapshots to optimize replay:

```python
async def get_aggregate(aggregate_id: str) -> Order:
    # Try to load from snapshot first
    snapshot = await snapshot_store.get_latest_snapshot(aggregate_id)
    
    if snapshot:
        # Get only events after the snapshot
        events = await event_store.get_events_by_aggregate_id(
            aggregate_id, 
            after_version=snapshot.version
        )
        
        # Restore from snapshot and apply newer events
        aggregate = Order.from_snapshot(snapshot)
        for event in events:
            aggregate.apply_event(event)
        return aggregate
    else:
        # Fall back to full event replay
        events = await event_store.get_events_by_aggregate_id(aggregate_id)
        return Order.from_events(events)
```

## Integration with Event Store

The event store handles serialization/deserialization and ensures proper upcasting when loading events:

```python
async def get_events_by_aggregate_id(
    self, aggregate_id: str, event_types: list[str] | None = None
) -> list[DomainEvent]:
    """Get events for an aggregate with automatic upcasting."""
    # Fetch serialized events from storage
    raw_events = await self._storage.fetch_events(aggregate_id, event_types)
    
    # Deserialize and upcast each event
    events = []
    for raw_event in raw_events:
        # Find the event class for this event type
        event_type = raw_event.get("event_type")
        event_class = self._event_registry.get_class(event_type)
        
        if event_class:
            # Apply upcasting if needed
            if raw_event.get("version", 1) < event_class.version:
                raw_event = event_class.upcast(raw_event)
                
            # Create the event instance
            event = event_class.from_dict(raw_event)
            events.append(event)
    
    return events
```

## Conclusion

Event replay and upcasting are powerful patterns that enable schema evolution and historical analysis in event-sourced systems. The Uno framework provides robust support for these patterns through its `DomainEvent` base class and `AggregateRoot` implementations.

By following the patterns outlined in this document, you can ensure that your event-sourced system remains flexible and maintainable as your application evolves over time.
