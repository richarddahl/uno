# Domain and Events Modules Refactoring Analysis

## Domain Module Analysis

### Key Components

- **Repository Pattern**: Base abstract repository interface in `repository.py`
- **Aggregate Pattern**: Aggregate root implementation in `aggregate.py`
- **Event Sourcing**: Event sourced repository in `event_sourced_repository.py`
- **Entity**: Base entity class in `entity.py`
- **Value Objects**: Value object implementations in `value_object.py`
- **Domain Errors**: Domain-specific errors in `errors.py`

### Current Implementation Patterns

- Simple abstract interfaces with async methods
- No explicit DI container usage
- May be using direct imports rather than dependency injection
- Error handling appears to be mixed between exception-based and Result monad approach

### Refactoring Needs

- Update all components to use constructor-based DI
- Replace any Result-based error handling with exception-based approach
- Refactor error classes to extend from UnoError
- Add structured logging
- Implement configuration via Pydantic models

## Events Module Analysis

### Key Components

- **Event Bus**: Event publishing and subscriptions in `bus.py` and `event_bus.py`
- **Event Store**: Event persistence in `event_store.py` and implementations
- **Command Bus**: Command handling in `command_bus.py`
- **Event Handlers**: Handler registration and dispatch in `handlers.py`
- **Middleware**: Processing pipelines in `middleware.py` and the `middleware/` directory
- **Sagas**: Saga implementation in `sagas.py`, `saga_store.py`, `saga_manager.py`
- **Projections**: Projections in `projections.py`
- **Errors**: Error handling in `errors.py` and the `errors/` directory

### Current Implementation Patterns

- Using Result monad for error handling (Success/Failure)
- Custom logging approaches
- Manual handler registration
- Direct dependencies rather than DI container resolution
- Postgres-specific implementations tightly coupled

### Refactoring Needs

- Replace Result monad with exception-based error handling
- Refactor error classes to extend from UnoError
- Update to use DI container for handler resolution
- Implement structured logging via DI-injected loggers
- Create proper configuration classes

## Test Impact Analysis

- Domain tests will need updating to use DI container
- Event handler tests will need to be refactored for exception-based approach
- Integration tests will need updates to use the new systems
- Need to verify all error handling flows

## Example App Impact

- Will need to update bootstrapping to use DI container
- Update all handler registrations
- Convert to structured logging
- Update configuration handling
