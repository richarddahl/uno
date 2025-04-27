# Uno Sagas: Event/Command Bus Integration Guide

This guide demonstrates how to orchestrate long-running business processes in Uno using sagas, the event bus, and the command bus. It covers wiring, extension, and testing.

---

## 1. **Saga Pattern Overview**
- **Saga**: Orchestrates a process by reacting to domain events and emitting commands as side effects.
- **EventBus**: Delivers domain events to all subscribers (including sagas).
- **CommandBus**: Delivers commands from sagas to command handlers (which may trigger further domain events).

---

## 2. **Wiring Up a Saga**

```python
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from uno.core.events.event_bus import EventBus
from uno.core.events.command_bus import CommandBus
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga

# Create buses and manager
saga_store = InMemorySagaStore()
manager = SagaManager(saga_store)
manager.register_saga(OrderFulfillmentSaga)
event_bus = EventBus()
command_bus = CommandBus()

# Register command handler (example)
emitted_commands = []
async def command_handler(command):
    emitted_commands.append(command)
command_bus.register_handler(command_handler)

# Wire saga to buses
def saga_handler_factory(saga_id):
    async def saga_handler(event):
        saga = manager._get_or_create_saga(saga_id, "OrderFulfillmentSaga")
        saga.set_command_bus(command_bus)
        await manager.handle_event(saga_id, "OrderFulfillmentSaga", event)
    return saga_handler

saga_id = "order-123"
event_bus.subscribe(saga_handler_factory(saga_id))

# Publish events
events = [
    {"type": "OrderPlaced", "order_id": saga_id},
    {"type": "InventoryReserved"},
    {"type": "PaymentProcessed"},
]
for event in events:
    await event_bus.publish(event)

# Check emitted commands
print(emitted_commands)
```

---

## 3. **Testing Sagas in Event-Driven Context**
- Use pytest and Uno's in-memory buses for integration tests.
- See `tests/sagas/test_order_fulfillment_saga_commandbus.py` for a full example.

---

## 4. **Advanced Saga Patterns**

### Timeout/Retry Saga
A saga can implement timeouts and retries by tracking retry counts and handling timeout events:

```python
class TimeoutSaga(Saga):
    def __init__(self) -> None:
        super().__init__()
        self.data = {"step_completed": False, "retries": 0, "max_retries": 2, "timeout_triggered": False}
        self.status = "waiting_step"

    async def handle_event(self, event: Any) -> None:
        if event["type"] == "StepCompleted":
            self.data["step_completed"] = True
            self.status = "completed"
        elif event["type"] == "Timeout":
            self.data["timeout_triggered"] = True
            if self.data["retries"] < self.data["max_retries"]:
                self.data["retries"] += 1
                self.status = "waiting_step"
                # Retry logic here
            else:
                self.status = "failed"

    async def is_completed(self) -> bool:
        return self.status in ("completed", "failed")
```

### Compensation Chaining Saga
A saga can chain compensations for multi-step processes, compensating in reverse order:

```python
class CompensationChainSaga(Saga):
    def __init__(self) -> None:
        super().__init__()
        self.data = {"step1_completed": False, "step2_completed": False, "compensated": False, "compensation_log": []}
        self.status = "waiting_step1"

    async def handle_event(self, event: Any) -> None:
        if event["type"] == "Step1Completed":
            self.data["step1_completed"] = True
            self.status = "waiting_step2"
        elif event["type"] == "Step2Completed":
            self.data["step2_completed"] = True
            self.status = "completed"
        elif event["type"] == "Step2Failed":
            self.status = "compensating"
            await self.compensate()

    async def compensate(self) -> None:
        if self.data["step2_completed"]:
            self.data["compensation_log"].append("Compensate Step2")
            self.data["step2_completed"] = False
        if self.data["step1_completed"]:
            self.data["compensation_log"].append("Compensate Step1")
            self.data["step1_completed"] = False
        self.data["compensated"] = True
        self.status = "compensated"

    async def is_completed(self) -> bool:
        return self.status in ("completed", "compensated")
```

---

## 5. **Best Practices for Complex Sagas**
- Use `self.data` for all custom state to ensure persistence and recovery.
- Keep side-effect logic (commands, compensations) isolated in methods.
- Use DI to inject command/event buses for testability and flexibility.
- Always provide integration tests for happy path, compensation, and recovery.
- Document all saga transitions and compensation logic for maintainability.

---

## 6. **Monitoring and Admin**
- (Planned) Use the SagaManager API/CLI to inspect running/completed sagas.
- For now, inspect saga state via the saga store directly.

---

## 6. **References**
- [OrderFulfillmentSaga](examples/app/sagas/order_fulfillment_saga.py)
- [SagaManager](src/uno/core/events/saga_manager.py)
- [EventBus](src/uno/core/events/event_bus.py)
- [CommandBus](src/uno/core/events/command_bus.py)

---

Uno Sagas are designed for extensibility, testability, and production-readiness. For questions or contributions, see the Uno documentation or contact the maintainers.
