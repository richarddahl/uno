# Uno Framework Integration Plan

This document provides a detailed implementation plan for integrating the core Uno framework components into a cohesive, production-ready system. The plan focuses on the essential integration points required for immediate usability while maintaining the framework's loosely coupled architecture.

STAY FOCUSED. THE GOAL IS integrating the defined functionatlity, creating new functionality ONLY in support of the integration of the various packages.

## Core Principles

- **Async-first**: All APIs must be async-compatible, and async first, if sync is needed it should be possible to use sync, via the most simple possible means and if needed, via a sync wrapper. goal is async by default, sync by choice.
- **Backward compatibility**: uno is a new framework, not a drop-in replacement for existing code. The goal is to define the canonical method of doing things, with NO REGARD for backward compatibility.
- **Loosely coupled**: Components should work well together but have clear boundaries
- **Idiomatic Python**: Follow modern Python 3.13 standards and practices
- **Protocol-based interfaces**: Use `Protocol` over abstract base classes
- **Progressive disclosure**: Simple for basic use, powerful for advanced needs
- **Consistent error handling**: Standardized error propagation

## Implementation Phases

### Phase 1: Foundation Layer (Week 1)

#### 1A: Core Configuration System

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Create `ConfigRegistrationExtensions` class for DI registration | High | `src/uno/config/di.py` | **In Progress**
| 2 | Add `register_configuration` extension method for DI container | High | `src/uno/config/di.py` | **In Progress**
| 3 | Implement async version of `load_settings` | Medium | `src/uno/config/__init__.py` |
| 4 | Create `AsyncConfigLoader` for remote configuration sources | Medium | `src/uno/config/async_loader.py` |
| 5 | Add caching to `get_config` using DI-friendly pattern | Medium | `src/uno/config/__init__.py` |
| 6 | Standardize type hints across configuration system | High | All config files |
| 7 | Create integration tests for configuration + DI | High | `tests/integration/test_config_di.py` |

**Implementation Notes:**

- Configuration should be registered as singletons in the DI container
- Support both synchronous and asynchronous loading patterns
- Remove backward compatibility with current `get_config` pattern

#### 1B: DI System Enhancements

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Add `resolve_or_default` method to container | High | `src/uno/di/container.py` |
| 2 | Implement factory resolution integration | High | `src/uno/di/factory.py` |
| 3 | Add proper async scope management with context vars | High | `src/uno/di/scope.py` |
| 4 | Create standard bootstrap process | High | `src/uno/di/bootstrap.py` |
| 5 | Implement async initialization and cleanup hooks | Medium | `src/uno/di/lifecycle.py` |
| 6 | Create integration examples for global factory pattern | Medium | `examples/di/factory_integration.py` |
| 7 | Add tests for async scoping | High | `tests/unit/di/test_async_scope.py` |

**Implementation Notes:**

- Remove compatibility with global factory pattern
- Ensure all async operations properly clean up resources
- Create clear documentation of bootstrap process

#### 1C: Logging Integration

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Create `LoggerFactory` for DI registration | High | `src/uno/logging/factory.py` |
| 2 | Update `LoggingSettings` to use `UnoSettings` | Medium | `src/uno/logging/config.py` |
| 3 | Implement async context manager support | High | `src/uno/logging/protocols.py`, `src/uno/logging/logger.py` |
| 4 | Create DI registration extensions | High | `src/uno/logging/di.py` |
| 5 | Add context propagation in async code | High | `src/uno/logging/context.py` |
| 6 | Implement logger scope alignment with DI scopes | Medium | `src/uno/logging/scope.py` |
| 7 | Create integration tests for logging + DI | High | `tests/integration/test_logging_di.py` |

**Implementation Notes:**

- Allow loggers to be injected via constructor
- Remove compatibility with global `get_logger` pattern
- Ensure context is properly maintained across async boundaries

### Phase 2: Event and Error Integration (Week 2)

#### 2A: Error System Integration

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Implement error enrichment from DI context | High | `src/uno/errors/context.py` |
| 2 | Create standard error handlers for events | High | `src/uno/events/error_handling.py` |
| 3 | Implement error factories for each component | High | Various component error factories |
| 4 | Add logging middleware for error capture | Medium | `src/uno/errors/logging.py` |
| 5 | Create standardized error codes across components | Medium | `src/uno/errors/codes.py` |
| 6 | Add async-compatible error handling | High | `src/uno/errors/async_handling.py` |
| 7 | Add tests for error context propagation | High | `tests/unit/errors/test_context_propagation.py` |

**Implementation Notes:**

- Maintain clear error categories
- Ensure rich context is preserved in async operations
- Standardize error code format across all components

#### 2B: Event System Enhancement

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Fix `CompositeSnapshotStrategy.should_snapshot` implementation | Critical | `src/uno/events/snapshots.py` |
| 2 | Fix `InMemorySnapshotStore.get_snapshot` implementation | Critical | `src/uno/events/snapshots.py` |
| 3 | Fix `FileSystemSnapshotStore` methods | Critical | `src/uno/events/snapshots.py` |
| 4 | Implement DI-aware event handler dependency resolution | High | `src/uno/events/handlers.py` |
| 5 | Standardize event serialization and deserialization | High | `src/uno/events/serialization.py` |
| 6 | Create event correlation context | High | `src/uno/events/correlation.py` |
| 7 | Implement DI registration extensions | High | `src/uno/events/di.py` |
| 8 | Add tests for event handler dependency resolution | High | `tests/unit/events/test_di_integration.py` |

**Implementation Notes:**

- Ensure all event serialization follows canonical pattern
- Fix the incomplete method implementations in snapshots.py
- Align event handler registration with DI container

#### 2C: Domain Integration

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Implement `AggregateRoot` base class | High | `src/uno/domain/aggregate_root.py` |
| 2 | Create `Entity` base class | High | `src/uno/domain/entity.py` |
| 3 | Implement `Repository` protocol | High | `src/uno/domain/repository.py` |
| 4 | Add domain event publishing integration | High | `src/uno/domain/events.py` |
| 5 | Create domain validation framework | Medium | `src/uno/domain/validation.py` |
| 6 | Update domain package `__init__.py` to expose new classes | High | `src/uno/domain/__init__.py` |
| 7 | Add tests for aggregate event sourcing | High | `tests/unit/domain/test_aggregate.py` |

**Implementation Notes:**

- Ensure aggregate roots can publish events via DI
- Maintain immutability of value objects
- Create DDD-compliant abstractions

### Phase 3: Documentation and Testing (Week 3)

#### 3A: Integration Examples

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Create a complete sample application | High | `examples/todo_app/` |
| 2 | Add documentation for common integration patterns | High | `docs/integration_patterns.md` |
| 3 | Create application templates | Medium | `templates/basic_app/`, `templates/api_app/` |
| 4 | Add bootstrapping examples | High | `examples/bootstrapping/` |
| 5 | Create DI setup examples | High | `examples/di_setup/` |

**Implementation Notes:**

- Sample application should use all core components
- Provide clear explanations in example code
- Document common pitfalls and solutions

#### 3B: Testing Utilities

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Create test helpers for DI container setup | High | `src/uno/testing/di.py` |
| 2 | Implement mock factories for common components | High | `src/uno/testing/mocks.py` |
| 3 | Add test fixtures for event testing | High | `src/uno/testing/events.py` |
| 4 | Create base test classes for Uno applications | Medium | `src/uno/testing/base_test.py` |
| 5 | Add documentation for testing approaches | Medium | `docs/testing.md` |

**Implementation Notes:**

- Test helpers should be simple to use
- Mock objects should follow Protocol interfaces
- Document common testing patterns

#### 3C: Package Structure Standardization

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1 | Audit and standardize package structures | High | All packages |
| 2 | Ensure consistent public APIs through `__all__` | High | All `__init__.py` files |
| 3 | Consolidate duplicate implementations | Medium | Various |
| 4 | Create structure validation test | Low | `tools/validate_structure.py` |
| 5 | Update documentation to reflect standard structure | Medium | `docs/package_structure.md` |

**Implementation Notes:**

- Follow package structure recommendations from OVERALL_STATUS.md
- Ensure proper type hinting throughout
- Remove backward compatibility! uno is a new framework, not a drop-in replacement for existing code.

## Critical Fixes Needed Immediately

The following issues must be addressed immediately as they involve incomplete implementations that would prevent the framework from functioning:

1. **In `src/uno/events/snapshots.py`:**
   - Fix `CompositeSnapshotStrategy.should_snapshot` - it should return `True` if any strategy returns `True`
   - Complete `InMemorySnapshotStore.get_snapshot` implementation to check if the snapshot exists
   - Fix `FileSystemSnapshotStore` methods with proper exception handling and validation

2. **In `uno.domain` package:**
   - Implement the basic `AggregateRoot` class as it's a fundamental building block
   - Add `Entity` base class to complete the domain model types
   - Create `Repository` protocol for data access abstraction

3. **In DI system:**
   - Add proper async scoping to prevent memory leaks and resource issues
   - Implement resolver for global factories to bridge current and future patterns

## Integration Points Checklist

This checklist covers the essential integration points between components:

### Configuration Integration

- [ ] Config + DI: Register configuration as injectable services
- [ ] Config + Logging: Use UnoSettings for logger configuration
- [ ] Config + Events: Configure event system via DI

### DI Integration

- [ ] DI + Logging: Injectable logger factory
- [ ] DI + Events: Handler dependency resolution
- [ ] DI + Domain: Injectable repositories
- [ ] DI + Global factories: Bridge for existing factory approach

### Error Handling Integration

- [ ] Errors + Logging: Automatic context enrichment
- [ ] Errors + Events: Standard error middleware
- [ ] Errors + DI: Error context from container

### Event System Integration

- [ ] Events + Domain: Publishing from aggregates
- [ ] Events + Persistence: Event storage abstraction
- [ ] Events + DI: Handler dependency resolution

## Conclusion

By following this integration plan, the Uno framework will achieve a cohesive, production-ready state without requiring major rework of existing components. The focus remains on making the current functionality work together seamlessly, with an emphasis on:

1. **Async-first behavior** throughout the system
2. **Dependency injection** as the primary composition mechanism
3. **Clear protocols** defining component boundaries
4. **Idiomatic Python** usage following modern standards

This approach delivers an immediately usable framework while laying the groundwork for future enhancements.
