# Uno Framework Onboarding Guide

Welcome to Uno! This guide will help you get started as a contributor or user of the Uno event sourcing and DDD framework.

---

## Quickstart

1. **Clone the repository:**

   ```bash
   git clone <your-fork-or-upstream-url>
   cd uno
   ```

2. **Install dependencies:**

   ```bash
   pip install -e .[dev]
   ```

3. **Run the tests:**

   ```bash
   hatch run test:testV
   ```

4. **Launch the example app:**

   ```bash
   hatch run dev:examples/app
   # or follow README instructions
   ```

---

## Project Structure

- `src/uno/` — Uno framework core (DI, events, logging, config, errors)
- `examples/app/` — Example inventory management app (reference aggregates, API, persistence)
- `tests/` — Core and app tests (pytest)
- `docs/` — Documentation, guides, and API references

---

## How to Add a New Aggregate or Event

1. **Create a new aggregate/event class** in your domain module (see `examples/app/domain/`).
2. **Inherit from `AggregateRoot` or `DomainEvent`** as appropriate.
3. **Add versioning:**
   - Use `__version__` for events.
   - Register upcasters in `EventUpcasterRegistry` if schema evolves.
4. **Write tests** in `tests/` or `examples/app/tests/`.

---

## Event Upcasting & Schema Evolution

Uno supports versioned events and seamless upcasting. See:

- [examples/inventory_upcasting.py](../examples/inventory_upcasting.py)
- [docs/events_upcasting.md](./events_upcasting.md)

**How to upcast:**

- Define new event versions with `__version__`.
- Register upcasters via `EventUpcasterRegistry.register(NewVersion, from_version=OldVersion, upcaster=func)`.
- Use `.from_dict()` to load and upcast legacy events.

---

## Uno CLI (Codegen & Admin)

Uno provides a CLI for code generation, diagnostics, and admin tasks. Example usage:

```bash
# Scaffold a new aggregate (creates examples/app/domain/inventoryitem.py)
hatch run uno.cli generate-aggregate InventoryItem

# Scaffold a new event (creates examples/app/domain/inventoryadded_event.py)
hatch run uno.cli generate-event InventoryAdded

# Show logging configuration
hatch run uno.cli logging-config-show
```

See [docs/logging/cli.md](./logging/cli.md) for more logging CLI commands and usage tips.

---

## CLI Usage

Here are some common CLI commands to get you started:

```bash
# Generate a new aggregate
hatch run uno.cli generate-aggregate MyAggregate

# Generate a new event
hatch run uno.cli generate-event MyEvent

# Run the example app
hatch run dev:examples/app

# Show Uno's version
hatch run uno.cli version
```

---

## Extending Uno

- **Add new modules:** Place new framework code in `src/uno/`, and new example/domain code in `examples/app/domain/`.
- **Contribute to the CLI:** Edit `src/uno/cli.py` to add new commands (e.g., code generators, admin tools). Use `typer` for easy command definitions.
- **Add tests:** All new features should have tests in `tests/` or `examples/app/tests/`.
- **Update docs:** Document new features in `docs/`, and cross-link relevant guides.

---

## Troubleshooting & Tips

- If you see import errors, check your virtualenv and PYTHONPATH.
- If CLI commands fail, ensure you are running via `hatch run uno.cli ...` from the repo root.
- For logging/admin issues, see [docs/logging/cli.md](./logging/cli.md).
- For event upcasting issues, see [docs/events_upcasting.md](./events_upcasting.md) and `examples/inventory_upcasting.py`.
- If tests fail, run `hatch run test:testV` and review error output.

---

## Uno API Reference (Core Extension Points)

### 1. Dependency Injection (DI)
Register a service implementation:
```python
from uno.core.di import ServiceProvider
from mymodule import MyService, MyServiceImpl
ServiceProvider().register(MyService, implementation=MyServiceImpl)
```

### 2. Defining a Domain Event
```python
from uno.core.events.base_event import DomainEvent
class InventoryAdded(DomainEvent):
    item_name: str
    quantity: float
```

### 3. Using Uno Logger
```python
from uno.core.logging import LoggerService
logger = LoggerService().get_logger(__name__)
logger.info("Something happened")
```

### 4. Customizing Config
```python
from uno.core.config import UnoConfig
config = UnoConfig()
print(config.some_setting)
```

### 5. Error Handling
```python
from uno.core.errors import Success, Failure
result = do_something()
if isinstance(result, Success):
    ...
else:
    ...
```

### 6. CLI Usage
See the CLI section above, or run:
```bash
hatch run uno.cli --help
```

For more, see the respective docs in `docs/` and code examples in `examples/`.

---

## Coding Conventions

- Use modern Python 3.13 and Pydantic v2
- Type hints everywhere, no legacy code
- DI for all services and handlers
- Use Uno's logger/config exclusively
- All public classes/functions must have docstrings
- Use pytest fixtures for tests

---

## Contribution Workflow

- Fork, branch, and PR as usual
- Run all tests and lint before PR
- Add notes or links to the checklist in `REFACTOR_CHECKLIST.md`
- For questions, see `docs/` or ask in the project chat

---

Happy hacking! 🚀
