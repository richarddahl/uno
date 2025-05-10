# Event Package Refactoring Plan

This document outlines a comprehensive plan to refactor the `events` package in the Uno framework. The goal is to:

1. Restructure the events package to focus on its core responsibilities
2. Move technology-specific implementations to their appropriate packages
3. Use Protocols for composition-based type checking instead of inheritance
4. Eliminate code duplication across packages
5. Ensure all code follows Uno's idiomatic patterns

## Core Issues

Current analysis reveals several structural issues:

1. The `events` package contains code that belongs in other packages (projections, persistence, sagas)
2. Some implementations inherit from Protocols rather than implementing them structurally
3. There's potential code duplication across packages
4. The `events` package should only contain in-memory implementations for development and testing

## Refactoring Strategy

The refactoring will be organized into the following phases:

1. **Protocol Refactoring** - Ensure all protocols follow Uno's idioms
2. **Base Classes Relocation** - Move domain objects and base classes to appropriate packages
3. **Implementation Migration** - Move technology-specific implementations to their packages
4. **Integration and Testing** - Ensure everything works together after refactoring
5. **Linting** - Ignore linting errors in the refactoring process

## Detailed Action Items

### 1. Protocols Refactoring

#### 1.1. Event-related Protocols

- [x] Audit `events/protocols.py` to identify which protocols are truly event-specific
- [x] Remove inheritance from Protocol classes and use `@runtime_checkable` consistently
- [x] Ensure all Protocols have proper name suffixes (e.g., `EventBusProtocol`)
- [x] Verify generic type parameters are properly defined (contravariant for inputs, covariant for outputs)

#### 1.2. Command-related Protocols

- [x] Move `CommandHandler` from `events/protocols.py` to a new `commands/protocols.py` module
- [x] Update imports and ensure all dependent code points to the new location

#### 1.3. Event Store Protocols

- [x] Move `EventStoreProtocol` to `persistence/event_sourcing/protocols.py`
- [x] Update all references to point to the new location

### 2. Base Classes Relocation

#### 2.1. Domain Event Base Classes

- [x] Keep `DomainEvent` and `EventMetadata` in `events/base_event.py` (these are core to events)
- [x] Remove any implementation-specific details from these base classes

#### 2.2. Event Handler Base Classes

- [x] Convert `EventHandler` and `EventHandlerMiddleware` from ABC to Protocol in `events/protocols.py`
- [x] Update error handling to use the standard Uno error pattern

#### 2.3. Command Base Classes

- [x] Move command-related base classes to a new `commands` package
- [x] Update imports throughout the codebase

### 3. Implementation Migration

#### 3.1. Event Bus Implementations

- [x] Keep `InMemoryEventBus` in `events/implementations/bus.py` (for testing/dev)
- [x] Remove class inheritance from `EventBusProtocol`, use structural typing
- [x] Move SQL/Postgres implementations to `persistence/event_sourcing/implementations/postgres/`
- [x] Update imports and references throughout the codebase

#### 3.2. Event Store Implementations

- [x] Keep `InMemoryEventStore` in `events/implementations/store.py` (for testing/dev)
- [x] Remove class inheritance from `EventStoreProtocol`, use structural typing
- [x] Move SQL/Postgres implementations to `persistence/event_sourcing/implementations/postgres/`
- [x] Update imports and dependencies throughout the codebase

### Progress Notes on Implementation Migration

- Successfully updated `InMemoryEventBus` and `InMemoryEventStore` to use structural typing (no inheritance)
- Moved `EventStoreProtocol` to `persistence/event_sourcing/protocols.py` and updated all imports
- Updated `PostgresEventStore` to use structural typing with `Generic[E]` instead of inheriting from `EventStoreProtocol`
- Updated DI container registrations to use the new protocol locations and implementations
- Added proper type handling in the DI module with `cast("LoggerProtocol", ...)`
- Set up appropriate fallbacks for configuration options

#### 3.3. Command Implementations

- [x] Move command implementations to `commands/implementations/`
- [x] Update imports and references throughout the codebase

### Progress Notes on Command Implementation Migration

- Created a new `StructuralCommandBus` in `commands/implementations/structural_bus.py` using structural typing
- Created a backward-compatible `InMemoryCommandBus` in `commands/implementations/memory_bus.py`
- Updated imports in the examples application to use the new implementation
- Added the new implementations to the public API in the commands package
- Ensured all implementations follow Uno's idioms of:
  - Using structural typing instead of inheritance
  - Proper error handling aligned with Uno's error patterns
  - Type checking imports to avoid circular dependencies
  - Clean separation of concerns
- Preserved backward compatibility for existing code

#### 3.4. Event Handler Implementation Migration

- [x] Review event handler middleware implementations
- [x] Remove DI container dependencies from handlers and related components
- [x] Update event handler implementations to use Protocol-based structural typing
- [x] Fix discovery mechanism to follow best practices and reduce complexity

### Progress Notes on Event Handler Implementation Migration

- Updated `EventHandlerRegistry` to remove DI container dependencies
- Updated `EventHandlerDecorator` to remove container references
- Implemented proper Protocol-based structural typing for all handler components
- Refactored `AsyncEventHandlerAdapter` to use modern Python type annotations
- Created a properly typed `NextMiddlewareCallable` Protocol for middleware
- Refactored the handler discovery process for better maintainability
- Addressed linting issues throughout the handler implementations
- Implemented modern Python type annotations (`|` instead of `Union`, etc.)
- Fixed import ordering in all handler implementation files

### 4. Package Structure Updates

#### 4.1. Events Package Structure

```
src/uno/events/
├── __init__.py        # Public API
├── base_event.py      # DomainEvent and EventMetadata classes
├── config.py          # Events config
├── errors.py          # Event-specific errors
├── event_handler.py   # Generic event handling
├── protocols.py       # Event-specific protocols
└── implementations/   # ONLY in-memory implementations
    ├── __init__.py
    ├── bus.py         # InMemoryEventBus
    └── store.py       # InMemoryEventStore
```

#### 4.2. Commands Package Structure

```
src/uno/commands/
├── __init__.py
├── base_command.py    # Command base classes
├── errors.py          # Command-specific errors
├── protocols.py       # Command-specific protocols
├── handler.py         # Command handling
└── implementations/   # ONLY in-memory implementations
    ├── __init__.py
    └── handler.py     # InMemoryCommandHandler
```

#### 4.3. Persistence Package Updates

```
src/uno/persistence/
└── event_sourcing/
    ├── __init__.py
    ├── errors.py
    ├── protocols.py   # EventStoreProtocol moved here
    └── implementations/
        ├── __init__.py
        ├── memory/
        │   ├── __init__.py
        │   ├── event_store.py  # Alias to InMemoryEventStore
        │   └── bus.py          # Alias to InMemoryEventBus
        └── postgres/
            ├── __init__.py
            ├── event_store.py  # PostgresEventStore
            └── bus.py          # PostgresEventBus
```

### 5. Import and Dependency Updates

#### 5.1. Public API Updates

- [ ] Update `__init__.py` files to expose the correct public API
- [ ] Add proper `__all__` declarations following isort ordering
- [ ] Document breaking changes for migration

#### 5.2. Imports Audit

- [ ] Audit all imports throughout the codebase
- [ ] Fix circular imports if any are created during refactoring
- [ ] Use import guards (`if TYPE_CHECKING`) for type imports

#### 5.3. DI Container Updates  

- [ ] Update dependency injection bindings
- [ ] Ensure services are registered in the correct packages

### 6. Testing Strategy

#### 6.1. Unit Test Migration

- [ ] Update imports in all affected tests
- [ ] Ensure all tests pass after refactoring
- [ ] Add tests for any new functionality or edge cases

#### 6.2. Integration Tests

- [ ] Create integration tests that verify the components work together
- [ ] Test with both in-memory and real implementations

### 7. Documentation Updates

#### 7.1. Code Documentation

- [ ] Update docstrings for all affected modules, classes, and functions
- [ ] Ensure type hints are correct and follow Python 3.13 style

#### 7.2. Migration Guide

- [ ] Document breaking changes and how to migrate
- [ ] Provide examples of the new usage patterns

## Implementation Checklist

### Phase 1: Protocol Refactoring

- [ ] Review and update all Protocol definitions
- [ ] Convert all inheritance-based implementations to structural typing
- [ ] Move protocols to their appropriate packages
- [ ] Update imports throughout the codebase

### Phase 2: Base Class Relocation

- [ ] Identify and relocate non-event specific base classes
- [ ] Create new package structure for commands
- [ ] Update imports in all affected files

### Phase 3: Implementation Migration

- [x] Move SQL/Postgres implementations to persistence
- [x] Update in-memory implementations to use structural typing
- [x] Update command implementations to use structural typing
- [x] Update event handler implementations to use structural typing
- [x] Add implementation aliases for backward compatibility
- [x] Remove DI container dependencies from event handlers
- [ ] Update remaining DI container bindings

### Phase 4: Testing and Verification

- [ ] Run unit tests and fix failures
- [ ] Update integration tests
- [ ] Verify all functionality works as expected
- [ ] Check for performance regressions

### Phase 5: Documentation and Cleanup

- [ ] Update documentation with new structure
- [ ] Create migration guide for breaking changes
- [ ] Clean up any deprecated code
- [ ] Final code review

## Migration Path

To ensure minimal disruption during refactoring:

1. First implement structural protocols correctly in each package
2. Move implementations package by package, verifying tests pass after each move
3. Keep temporary aliases for backward compatibility during transition
4. Only remove deprecated code paths after everything is verified working

## Conclusion

This refactoring will result in a more maintainable and idiomatic structure for the Uno framework's event system. By properly separating concerns and following the composition over inheritance principle, the codebase will be more flexible, testable, and maintainable.
