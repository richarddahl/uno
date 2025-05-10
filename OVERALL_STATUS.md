# Uno Framework: Overall Integration Status

## Executive Summary

The Uno framework consists of several core packages that provide the foundation for a modern, async-first Python application development framework. Based on the status reports of individual packages, the framework has solid building blocks but requires focused integration work to become a cohesive, production-ready system.

This document outlines the critical integration work needed to transform these components from separate modules into a unified, idiomatic Python framework that developers can use immediately, while maintaining a loosely coupled architecture.

## Integration Philosophy

The integration strategy for Uno should follow these principles:

1. **Loosely coupled, highly cohesive**: Components should have clear boundaries but work seamlessly together
2. **Async-first throughout**: Consistent async patterns across all modules
3. **Pythonic API design**: Follow Python idioms and conventions
4. **Minimal dependencies**: Essential functionality without bloat
5. **Consistent error handling**: Predictable error propagation and context
6. **Progressive disclosure**: Simple for basic use cases, powerful for advanced needs

## Current Architecture

The Uno framework currently consists of these core packages:

- **uno.config**: Configuration management
- **uno.di**: Dependency injection
- **uno.domain**: Domain-driven design primitives
- **uno.errors**: Error handling system
- **uno.events**: Event sourcing and message handling
- **uno.logging**: Structured logging

Each component has varying levels of completeness and integration with other components.

## Critical Integration Points

### 1. Core Component Relationships

```
┌─────────────┐     ┌─────────────┐
│  uno.config ├────►│   uno.di    │
└─────┬───────┘     └──────┬──────┘
      │                    │
      ▼                    ▼
┌─────────────┐     ┌─────────────┐
│ uno.logging ├────►│  uno.errors │
└─────┬───────┘     └──────┬──────┘
      │                    │
      ▼                    ▼
┌─────────────┐     ┌─────────────┐
│ uno.events  ├────►│ uno.domain  │
└─────────────┘     └─────────────┘
```

### 2. Service Registration and Initialization

Currently, many packages use global singletons with factory functions (`get_logger()`, `get_event_bus()`, etc.). These should be properly integrated with the DI system while maintaining compatibility with both patterns.

## Integration Priorities

### Priority 1: Core Infrastructure Layer

The following foundational integrations need to be implemented first:

1. **Config ↔ DI**: Configuration-based service registration
2. **DI ↔ Logging**: Injectable loggers with proper scoping
3. **Errors ↔ Logging**: Standardized error logging patterns

### Priority 2: Domain and Events Integration

1. **Events ↔ Domain**: Proper domain event publishing
2. **DI ↔ Events**: Service resolution for event handlers
3. **Error handling in events**: Consistent error propagation

### Priority 3: Common Patterns and Documentation

1. **Application bootstrapping**: Standard startup sequence
2. **Documentation of integration patterns**: How components work together
3. **Test utilities for integrated components**: Testing the whole system

## Package-Specific Integration Tasks

### uno.config Integration

```python
# Current pattern: direct environment variable access
config = LoggingSettings.load()

# Target pattern: DI-friendly, consistent configuration
# 1. Register configuration in DI container
await container.register_singleton(LoggingSettings, lambda c: LoggingSettings.from_env())
# 2. Access via DI
logger_config = await container.resolve(LoggingSettings)
```

**Tasks:**

1. **DI Integration (High)**: Create registration extensions for all configuration classes
2. **Async Support (Medium)**: Add non-blocking loading methods for remote configurations
3. **Type Hints (High)**: Ensure consistent Python 3.13 type hints throughout

### uno.di Integration

```python
# Current pattern: mixed global factories and DI
logger = get_logger(__name__)  # Global factory
bus = container.resolve(EventBusProtocol)  # DI

# Target pattern: consistent DI with factory fallbacks
logger = container.resolve_or_default(
    LoggerProtocol, 
    lambda: get_logger(__name__)
)
```

**Tasks:**

1. **Factory Integration (High)**: Add methods to reconcile global factories with DI
2. **Scoped Service Resolution (High)**: Ensure proper async scoping for request contexts
3. **Async Lifecycle (Medium)**: Implement async initialization and cleanup hooks

### uno.logging Integration

```python
# Current pattern: manual context passing
logger.info("Processing request", request_id=request.id)

# Target pattern: auto context from DI scope and structured logging
with logger.context(request_id=request.id):
    logger.info("Processing request")  # Context automatically included
```

**Tasks:**

1. **DI Integration (High)**: Create logger factory for DI registration
2. **Config Integration (Medium)**: Use uno.config for logger configuration
3. **Async Context (High)**: Add async context manager support

### uno.errors Integration

```python
# Current pattern: direct error creation
raise ValueError("Something went wrong")

# Target pattern: structured error with context
raise UnoError(
    message="Invalid configuration value",
    error_code="CONFIG_INVALID_VALUE",
    category=ErrorCategory.CONFIG,
    field_name="database_url"
)
```

**Tasks:**

1. **Standardized Error Factory (High)**: Create error factories for each component
2. **Logger Integration (High)**: Ensure errors capture logging context
3. **DI Context Enrichment (Medium)**: Add service resolution context to errors

### uno.events Integration

```python
# Current pattern: mixed handler registration
@handles("user_created")
class UserCreatedHandler:
    async def handle(self, event): ...

# Target pattern: consistent registration with DI
@handles("user_created")
class UserCreatedHandler:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
        
    async def handle(self, event): ...
```

**Tasks:**

1. **DI Integration (High)**: Ensure handlers can resolve dependencies
2. **Domain Event Standardization (High)**: Consistent patterns for domain events
3. **Error Handling (High)**: Proper error propagation in event handling

### uno.domain Integration

```python
# Current pattern: basic value objects
class UserId(ValueObject):
    value: str

# Target pattern: domain model with event sourcing
class User(AggregateRoot):
    def create(cls, user_id: UserId, name: str) -> User:
        user = cls(id=user_id)
        user.apply(UserCreatedEvent(user_id=user_id, name=name))
        return user
```

**Tasks:**

1. **Events Integration (High)**: Proper domain event raising from aggregates
2. **Repository Pattern (High)**: Standard async repository interfaces
3. **Validation Integration (Medium)**: Consistent validation patterns

## Code Structure Recommendations

### Package Organization

Adopt a consistent structure across all packages:

```
uno.{package}/
├── __init__.py       # Public API exports
├── protocols.py      # Interface definitions
├── errors.py         # Package-specific errors
├── config.py         # Package configuration
├── implementations/  # Concrete implementations
├── extensions/       # Integration with other packages
└── utils/            # Helper utilities
```

### Module Boundaries

1. **Explicit public APIs**: Clear `__all__` list in each `__init__.py`
2. **Protocol-based interfaces**: Use protocols over abstract base classes
3. **Implementation separation**: Keep implementations separate from interfaces

### Idiomatic Python Patterns

1. **Type hints**: Use modern Python 3.13 style throughout

   ```python
   # Good
   def get_user(user_id: str) -> User | None: ...
   
   # Avoid
   def get_user(user_id: Optional[str]) -> Optional[User]: ...
   ```

2. **Async patterns**: Consistent async/await usage

   ```python
   # Good
   async def get_user(user_id: str) -> User: ...
   
   # Avoid
   def get_user(user_id: str) -> Awaitable[User]: ...
   ```

3. **Context managers**: For resource management

   ```python
   # Good
   async with container.create_scope() as scope:
       service = await scope.resolve(ServiceType)
   
   # Avoid
   scope = await container.create_scope()
   try:
       service = await scope.resolve(ServiceType)
   finally:
       await scope.dispose()
   ```

4. **Dependency injection**: Constructor injection pattern

   ```python
   # Good
   class UserService:
       def __init__(self, repository: UserRepositoryProtocol):
           self.repository = repository
   
   # Avoid
   class UserService:
       @inject
       def set_repository(self, repository: UserRepositoryProtocol):
           self.repository = repository
   ```

## Immediate Integration Roadmap

### Phase 1: Foundation (Week 1)

1. **Core Configuration System**
   - Implement DI registration for config classes
   - Create standard pattern for component configuration
   - Add async-friendly config loading

2. **DI System Enhancements**
   - Add resolver for global factories
   - Implement async scopes properly
   - Create standard container bootstrap process

3. **Logging Integration**
   - Standardize structured logging patterns
   - Add DI integration for loggers
   - Implement context propagation in async code

### Phase 2: Events and Errors (Week 2)

1. **Error System Integration**
   - Implement error enrichment from DI context
   - Add standard error handling middleware for event system
   - Create error factories for each component

2. **Event System Enhancement**
   - Ensure handler dependency resolution
   - Standardize event serialization and deserialization
   - Create common patterns for event correlation

3. **Domain Events Foundation**
   - Implement basic aggregate root with event sourcing
   - Create standard repository pattern
   - Add event publishing from domain objects

### Phase 3: Documentation and Examples (Week 3)

1. **Integration Examples**
   - Create a sample application using all components
   - Document common integration patterns
   - Add templates for new applications

2. **Testing Utilities**
   - Implement test helpers for integrated components
   - Create base test classes for Uno applications
   - Add fixture factories for testing

3. **Package Structure Standardization**
   - Audit and standardize all package structures
   - Ensure consistent public APIs
   - Verify integration points with tests

## Conclusion

The Uno framework has solid individual components that need focused integration work. By prioritizing the essential integration points identified in this document, the framework can quickly become a cohesive, production-ready system while maintaining its loosely coupled architecture.

The focus should be on making the existing functionality work together seamlessly, rather than adding new features. This approach will deliver an immediately usable library that follows Python best practices and provides a strong foundation for future enhancements.

Standardizing the package structure, module boundaries, and coding patterns across all components will ensure a consistent and intuitive developer experience, making Uno approachable for new users while powerful enough for complex applications.
