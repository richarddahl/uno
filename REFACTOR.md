# Uno Refactor & Migration Master Plan

_Last updated: 2025-04-29_

**THIS IS THE CANONICAL REFACTOR PLAN FOR UNO.**
All progress, architectural decisions, and implementation notes for domain-driven design (DDD), event sourcing, and all related refactorization must be tracked here. Do not use or update any other plan/checklist files. This file supersedes all previous event sourcing or DDD plans (including EVENT_REFACTOR_PLAN.md).

---

## Next Focus
- [x] Refactor service layer for Result/Failure, error context propagation, and repository protocols (done)
- [x] Complete DI integration for API/services using repository protocols (done)
- [x] All API/service tests pass (done)
- [ ] Fix or skip event store tests that require uno.sql (infra dependency)
- [ ] Sweep for Pydantic v2 and type hint modernization
- [ ] Address remaining lint/type warnings
- [ ] Finalize and publish documentation/migration guide

---

### Status Update (2025-04-29)
- InventoryLotCreated, InventoryLotsCombined, and InventoryLotSplit events refactored to use Result-based construction, error context propagation, versioning, upcast methods, and have full test coverage (success, failure, upcast).
- Domain event modernization pattern established (see InventoryLotAdjusted, InventoryLotCreated, InventoryLotsCombined, and InventoryLotSplit).
- Core logging, config, CLI, and DI integration now use Result/Failure and error context propagation.
- All CLI commands robust against config errors (no exceptions leak to user).
- Test suite: all core/CLI/DI tests pass. Remaining failures are due to missing uno.sql (event store infra).
- Lint/type warnings remain; Pydantic v2 and type hint sweep still needed.
- Next: finalize infra error context, uno.sql/test handling, and publish migration guide.

#### Next Steps (as of 2025-04-29)
1. Sweep and refactor all remaining domain events for Result-based construction, error context propagation, versioning, and docstrings/tests (follow InventoryLotCreated/Adjusted pattern).
2. Address lint/type issues, unused imports, and ensure Pydantic v2/type hint compliance throughout domain and event modules.
3. Fix or skip uno.sql-dependent infrastructure tests so all tests can pass in environments without Postgres/uno.sql.
4. Finalize and publish documentation and migration guide for Uno event sourcing, error handling, and DDD patterns.

## 1. Refactor & Migration Checklist

### 1.1 Core Logging & Dependency Injection

- [x] Migrate all core services to use DI-injected `LoggerService` (no global loggers)
- [x] Migrate all middleware (Metrics, CircuitBreaker, etc.) to DI logging
- [x] Migrate all event infrastructure (EventHandlerRegistry, event bus, etc.) to DI logging
- [x] Event bus logs all handler errors (exception or monad Failure) via DI-LoggerService
- [x] Migrate all utilities/integration modules to DI logging
- [x] Add/validate tests for DI logging in utilities/integration modules
- [x] Remove all legacy/global/fallback logger usage (except DI bootstrap exception)
- [x] Ensure all logging uses `structured_log` (no direct `logging.getLogger`)
- [x] Saga/event bus tests robustly assert error logging
- [x] Implement and document strict DI logging contract for all handlers and event infra
- [x] Add/complete DI integration tests
- [x] Remove temporary debug prints from tests and logger (test output clean)
- [x] All CLI commands now handle Result/Failure and error context propagation
- [x] All core logging, config, CLI, and DI integration tests pass (except infra/uno.sql)

### 1.2 Error Handling & Context Propagation

- [x] Implement Result monad and error context propagation in domain layer
    - Entity, AggregateRoot, and ValueObject now use Result-based error handling and context propagation throughout.
    - All core domain tests updated to assert on Success/Failure and error context.
- [x] Implement Result monad and error context propagation in API/handlers
- [x] Refactor all service layer methods to use Result and propagate error context (repository protocols, DI, and error context propagation complete; tested and passing)
- [ ] Refactor all infrastructure/integration modules for error context propagation (service layer done; infra next)
- [ ] Ensure all logging (manual, LoggerService, ErrorLoggingService) includes error context
- [x] Add/complete tests to verify error context in all error paths (service layer done; infra next)
- [x] Event bus/adapters now handle both exceptions and Result monad failures, logging all errors consistently

#### Domain Model Modernization (2025-04-28)
- AggregateRoot, Entity, and ValueObject refactored for:
    - Result-based error handling (Success/Failure, never raise)
    - Error context propagation in all Failure cases
    - Modern Python idioms, type hints, and Pydantic v2 compliance
    - Usage examples and improved docstrings
    - Immutability and validation contracts
- All core domain tests updated for Result contract and error path assertions
- 221/226 tests pass (remaining: infra/uno.sql dependency)
- [x] Fixed event sourcing/DTO mismatch for Vendor aggregate: EmailAddress value object is now correctly reconstructed from event data, resolving API and test failures.

### 1.3 Modern Python & Type Hints

- [ ] Sweep for Pydantic v2 modernization (no deprecated patterns)
- [ ] Sweep and update all type hints for compliance with Uno conventions (PEP 604, etc.)
- [ ] Remove unused imports and fix lint warnings

### 1.4 Performance & Testing

---

## Domain & Event Sourcing Refactor: Canonical Roadmap (Q2 2025)

**All progress, TODOs, and status for domain, DDD, and event sourcing must be tracked here.**

### 1. Aggregate Roots, Value Objects, and Events Modernization
- [x] Refactor all aggregate roots and value objects for:
    - Result-based construction and error context propagation (never raise, always return Success/Failure)
    - Modern Python idioms, PEP 604 type hints, and Pydantic v2 compliance
    - Immutability and validation contracts (`validate()` on all aggregates/VOs)
    - Usage examples and improved docstrings

> **Progress:**
> All major aggregates (InventoryItem, InventoryLot, Vendor) and value objects (Grade, EmailAddress, Money, Quantity, Count, Mass, Volume, Dimension, AlcoholContent) now use Result-based construction, error context propagation, modern type hints, and Pydantic v2. Immutability and validation contracts are enforced on construction. Usage examples and docstrings are present for all major types. Minor types may be swept for uniformity, but functional and documentation completeness is achieved for all core domain types.

- [x] Refactor all inventory domain event classes for:
    - Explicit context propagation
    - Result-based construction (Success/Failure)
    - Versioning and upcasting support
    - Pydantic v2 compliance and type hint modernization
    - Canonical serialization/deserialization
    - Event upcasting and migration patterns

> **Progress:**
> All inventory domain events (InventoryItemCreated, InventoryItemRenamed, InventoryItemAdjusted, InventoryLotCreated, InventoryLotsCombined, InventoryLotSplit, InventoryLotAdjusted) are fully modernized: they use Result-based construction, propagate error context, support versioning and upcasting, are Pydantic v2 compliant, and have usage docstrings/examples. Canonical serialization is handled by Pydantic. 
>
> **Remaining events to modernize:**
> - Order events: OrderCreated, OrderFulfilled, OrderCancelled
> - Vendor events: VendorCreated, VendorUpdated, VendorEmailUpdated
> - PaymentReceived
> - GradeAssignedToLot, MassMeasured, VolumeMeasured
>
> These events need Result-based construction, error context propagation, versioning/upcasting, and Pydantic v2 idioms for full modernization.

### 2. Event Sourcing Infrastructure
- [ ] Implement canonical event serialization (strict, versioned)
- [ ] Implement event upcasting and migration registry
- [ ] Implement snapshotting (pluggable, strategy-driven)
- [ ] Complete event store integrations (in-memory, Postgres, etc.)
- [ ] Ensure all event replay logic reconstructs correct types (aggregate, value object, event)
- [ ] Add event store roundtrip and error propagation tests

### 3. Bounded Contexts & Modularity
- [ ] Support for bounded contexts (modular domain packages)
- [ ] Document context boundaries, integration points, and isolation patterns

### 4. Validation, Invariants, and Testing
- [ ] Expand custom `validate()` contracts for all aggregates and value objects
- [ ] Ensure all domain validation errors propagate context via Failure
- [ ] Add/expand tests for domain invariants, error paths, and event upcasting/migration

### 5. Documentation & Best Practices
- [ ] Finalize and expand documentation for:
    - Domain modeling, DDD, and event sourcing in Uno
    - Result error handling and error context propagation
    - Event upcasting, migration, and serialization
    - Usage examples for all core domain types
    - Bounded contexts and modularity
- [ ] Provide reference implementations and migration guides

### 6. Performance & Modernization
- [ ] Benchmark domain/event sourcing operations for performance regressions
- [ ] Sweep for Pydantic v2, type hints, and lint/type warning resolution across all domain and infra modules
- [ ] Remove unused imports and fix all lint/type warnings

---

**This section is canonical. All future domain/event sourcing design, implementation, and migration work must be planned and tracked here.**

- [x] Implement and document logging performance benchmarks
- [ ] Benchmark DI performance
- [ ] Add/complete integration tests for DI and logging
- [ ] Ensure all event store and infra tests pass (skip or mock Postgres if `uno.sql` unavailable)
  - [x] Refactor MetricsMiddleware and related middleware for strict DI logging
  - [x] Add/validate tests for MetricsMiddleware logging and metrics
  - [x] Refactor CircuitBreakerMiddleware for strict DI logging
  - [x] Add/validate tests for CircuitBreakerMiddleware logging and error handling
  - [x] Refactor EventHandlerRegistry to require DI-injected LoggerService
  - [x] Replace legacy logging calls with structured_log
  - [x] Update documentation for DI-logging, structured logging, CLI/admin config, and benchmarks
  - [x] Ensure all tests pass and logger is required
  - [x] Remove all legacy/global logging from event registry
  - [ ] Add or update tests for those modules to verify logging and error handling
  - [ ] Add DI integration tests (in progress)
  - [x] Add logging performance benchmarks (complete)
  - [ ] Finalize and publish user guide
  - [ ] Sweep for Pydantic/type hint modernization in all event infrastructure
  - [ ] Implement or stub `uno.sql` for Postgres event store tests, or update tests to skip if not available

- **Upcoming Milestones:**
  - [ ] Finalize and publish user guide
  - [ ] Sweep for Pydantic/type hint modernization in all event infrastructure
  - [ ] Implement or stub `uno.sql` for Postgres event store tests, or update tests to skip if not available

- **Upcoming Milestones:**
  - [ ] Migrate all remaining modules/utilities to strict DI logging
  - [x] Audit/refactor service layer for error context propagation and Result usage (repository protocols, DI, and error context propagation complete; tested and passing)
  - [ ] Add or update tests to verify error context in all error paths (service/integration)
  - [ ] Complete documentation and user guides
  - [ ] Benchmark DI performance (ongoing)

- **Long-Term:**
  - [ ] Complete domain model implementation
  - [ ] Implement event sourcing
  - [ ] Create infrastructure integrations
  - [ ] Add comprehensive tests
  - [ ] Modernize codebase (fix deprecation warnings, update Pydantic/type hints)
  - [ ] Consolidate duplicated code

---

**Note:**
- As of 2025-04-28, event bus and adapters now fully support monad-based error handling. All handler errors—whether raised as exceptions or returned as `Failure`—are logged via DI-LoggerService using structured logging. Saga/event bus tests now robustly assert error logging and error context propagation. Temporary debug prints have been removed for clean output.

## 1. Core Components & Roadmap

### 1.1 Error Handling (`uno.core.errors`)

- [x] Complete monad-based error handling with all combinators (`map`, `flat_map`, `ensure`, `recover`, `map_async`, `flat_map_async`)
- [x] Create comprehensive examples and documentation for Result monad usage (sync, async, chaining, migration)
- [ ] Ensure consistent error context propagation
- [ ] Integrate error handling with logging system
- [ ] Optimize context management for performance (caching `inspect.signature`)
- [ ] Add `ParamSpec` and `Concatenate` to decorator wrappers
- [ ] Extract common base for sync and async error context managers

#### **Milestone: Monad-based Error Handling Complete**

- All domain and service logic now uses the Result monad for error handling (no exceptions for expected errors)
- New combinators (`ensure`, `recover`, `map_async`, `flat_map_async`) are implemented and documented
- Canonical examples and migration tips are present in both the core README and developer docs
- Next: continue integration with logging, propagate error context, and ensure all modules/services follow the new pattern

---

### 1.1.1 Error Context Propagation Audit & Checklist

**Goal:** Ensure all errors (including Result failures) have relevant context attached and are logged with context everywhere in Uno.

#### Checklist for Error Context Propagation

- [x] **Domain Layer** _(InventoryItem aggregate)_
  - [x] All domain methods use `with_error_context`/`with_async_error_context` or explicitly attach context to raised errors and Failure objects (see InventoryItem.create, rename, adjust_quantity).
  - [x] Custom errors (e.g., `DomainValidationError`) are always constructed with the current context (InventoryItem domain).
- [x] **Service Layer**
  - [x] All service methods use context managers/decorators or attach context to errors and Failure objects (repository protocols, DI, and error context propagation complete)
  - [x] Failures returned from service methods include relevant context (tested and passing)
- [x] **API & Command/Event Handlers** _(InventoryItem API)_
  - [x] All handlers unwrap Result and propagate error context to HTTP errors (see /inventory/ POST endpoint).
  - [x] All errors logged (manually or via ErrorLoggingService) include error context (InventoryItem API).
- [ ] **Infrastructure/Integration**
  - [ ] All integration/infra modules attach context to errors and log with context.
- [x] **Result Monad Usage** _(Inventory domain)_
  - [x] All `Failure(...)` instantiations include context if available.
  - [x] All `from_exception`/`from_awaitable` usages ensure context is attached to errors (where present in domain).
- [ ] **Logging**
  - [ ] All logging of errors (manual, LoggerService, ErrorLoggingService) includes error context.

**Progress Note (2025-04-28):**

- InventoryItem domain and API now consistently propagate error context, unwrap Results, and return/raise errors with context. All related tests have been updated and pass. Remaining work is needed for service, infrastructure, and logging layers.

**Next Steps:**

1. Audit and refactor service layer methods for error context propagation and Result usage.
2. Extend error context propagation and structured logging to infrastructure/integration modules.
3. Ensure all logging (manual and via LoggerService/ErrorLoggingService) includes error context.
4. Add or update tests to verify error context is present in all error paths (service/integration).
5. Update developer documentation with concrete context propagation patterns and examples.

### 1.2 Dependency Injection (`uno.core.di`)

- [x] LoggerService and LoggingConfigService are DI-injected singletons; legacy global loggers removed.
- [x] All main app repositories/services registered via DI with explicit constructor injection.
- [ ] Refactor all infrastructure/event modules to use DI for logging/config.
- [ ] Add DI integration tests and document best practices.
- [ ] Remove any remaining legacy/global patterns.
- [ ] Expand service registration with cleaner, less repetitive API
- [ ] Add caching for reflection to improve performance
- [ ] Implement comprehensive DI integration tests
- [ ] Add proper error handling in DI resolution
- [ ] Document best practices for service registration
- [ ] Optimize container build and service resolution
- [ ] Ensure strict DI enforcement (no global state)
- [ ] Add scope management examples and documentation

### 1.2.1 Uno Event Handler Logging: Strict DI Contract

- **All event handler registration, event bus, and registry usage must inject a DI-managed `LoggerService`.**
- Legacy or fallback logger logic is not supported—strict DI only.
- All handlers (class-based, function, or module) must use the injected `LoggerService` for logging. Never use `logging.getLogger` directly in handlers or event infra.
- Decorators for handler registration also require the logger:

  ```python
  @handles(UserCreatedEvent, logger)
  class MyHandler(EventHandler):
      ...
  ```

- For function handlers, use the DI logger for all logging calls.
- Example usage:

  ```python
  from uno.core.logging.logger import LoggerService, LoggingConfig
  from uno.core.events.handlers import EventHandlerRegistry

  logger = LoggerService(LoggingConfig())
  registry = EventHandlerRegistry(logger)
  ```

**Migration Checklist:**

- [x] Remove all direct or fallback `logging.getLogger` usages in event infra.
- [x] Require logger injection everywhere event handlers are registered, discovered, or dispatched.
- [x] Update all tests and examples to use DI logger.
- [x] Document the strict DI logging contract in REFACTOR.md and LOG_REFACTOR.md.
- [x] Sweep for and update any legacy logger usage in event-related modules/utilities.
- [x] Ensure type and lint compliance in all event handler examples.
- [ ] Sweep for Pydantic deprecation warnings and modernize type hints.
- [ ] Finish error context propagation integration.
- [ ] Implement and test structured logging for all components.

### 1.2.2 Guidance for Legacy Code and DI-Logging Migration

- **Ignore all files under `src/legacy/` for DI logging migration.** These are reference/archival only and not part of the active Uno codebase.
- **Exception:** The DI system's `ServiceProvider` in `src/uno/core/di/provider.py` uses a classic logger fallback (`logger or logging.getLogger(...)`). This is necessary for DI system bootstrapping (chicken-and-egg problem): you cannot inject a LoggerService before the DI system itself is initialized. This is the **only allowed exception** to strict DI-logging in core code. All other modules/utilities must require DI-injected `LoggerService` and use `structured_log` exclusively.

### 1.3 Logging (`uno.core.logging`)

- [x] LoggerService, LoggingConfigService, and ErrorLoggingService implemented and tested.
- [x] Structured logging, JSON output, and runtime config are available.
- [x] All API modules use strict DI logging.
- [ ] Migrate all infra/event modules/utilities to strict DI logging.
- [ ] Expose LoggingConfigService via admin/CLI.
- [ ] Benchmark logging performance and optimize as needed.
- [ ] Finalize and publish user/developer documentation.
- [ ] Sweep for Pydantic deprecation warnings and modernize type hints.
- [ ] Finish error context propagation integration.
- [ ] Implement and test structured logging for all components.

### 1.4 Domain (`uno.core.domain`)

- [ ] Complete aggregate root implementation
- [ ] Add comprehensive value objects support
- [ ] Implement domain events
- [ ] Add validation within domain objects
- [ ] Create bounded context support
- [ ] Provide examples of domain modeling
- [ ] Document DDD patterns and best practices
- [ ] Complete integration with event sourcing

### 1.5 Events (`uno.core.events`)

- [ ] Implement event sourcing
- [ ] Add concrete event store implementations
- [ ] Create event handlers
- [ ] Implement snapshotting
- [ ] Complete saga persistence
- [ ] Add circuit breaker and retry mechanisms
- [ ] Optimize for high-throughput scenarios
- [ ] Document event modeling best practices

### 1.6 Configuration (`uno.core.config`)

- [ ] Implement runtime configuration
- [ ] Add environment-based config loading
- [ ] Implement validation for all configs
- [ ] Add dynamic configuration updates
- [ ] Create centralized config management
- [ ] Automate config class generation for environments
- [ ] Document configuration overriding patterns
- [ ] Optimize settings initialization

### 1.7 Services (`uno.core.services`)

- [ ] Implement core service interfaces/protocols
- [ ] Add service lifecycle management
- [ ] Create service contracts
- [ ] Expand beyond current HashService
- [ ] Add common service implementations (caching, messaging, etc.)
- [ ] Document service patterns
- [ ] Add service integration tests
- [ ] Implement performance metrics for services

---

## 2. Code Quality & Modernization

### 2.1 DRYness

- [ ] Consolidate duplicated logic in error contexts
- [ ] DRY up service registration methods
- [ ] Extract common configuration/environment selection logic
- [ ] Create shared serialization utilities
- [ ] Factor out repeated patterns in service implementations
- [ ] Remove boilerplate through better abstractions
- [ ] Standardize on canonical serialization logic

### 2.2 Modern Python Idioms

- [ ] Ensure consistent use of modern type hints (X | Y not Union[X, Y])
- [ ] Use Pydantic 2 properly throughout (ConfigDict not class Config)
- [ ] Apply Protocol-based interfaces consistently
- [ ] Remove any legacy exception handling
- [ ] Use dataclasses where appropriate
- [ ] Apply modern Python 3.13+ features consistently
- [ ] Ensure no Python keywords are used as identifiers
- [ ] Prevent shadowing of built-ins or package names

### 2.3 Performance

- [ ] Test logging performance under load
- [ ] Optimize contextvars usage in error handling
- [ ] Cache inspect.signature results
- [ ] Add performance monitoring hooks
- [ ] Optimize BaseSettings initialization
- [ ] Document performance best practices

---

## 3. Documentation, Testing, and Usage

### 3.1 Documentation

- [x] Complete API documentation for all core modules (including new Result combinators)
- [x] Create usage guides and canonical examples for monad-style error handling (sync, async, chaining, migration)
- [ ] Document mental models behind key patterns
- [ ] Add real-world DDD scenario walkthroughs
- [ ] Provide migration guides for legacy codebases
- [ ] Add comprehensive user/developer guides
- [ ] Document DDD, event sourcing, and Uno-specific best practices
- [ ] Document configuration and deployment patterns

### 3.2 Testing

- [ ] Add integration tests for all components (CRUD, replay, error cases)
- [ ] Expand tests for aggregate, snapshot, and saga flows
- [ ] Cover edge cases, error handling, and performance
- [ ] Add snapshotting and replay benchmarks
- [ ] Add infrastructure integration tests
- [ ] Implement cross-component tests
- [ ] Test high-throughput scenarios
- [ ] Verify error context propagation

---

## 4. Integration and Infrastructure

- [ ] Complete infrastructure/application integration
- [ ] Implement service contracts across components
- [ ] Add cross-component communication
- [ ] Create infrastructure adapters for persistence
- [ ] Implement event store integrations (Postgres, file, etc.)
- [ ] Add saga orchestration infrastructure
- [ ] Implement unit of work patterns
- [ ] Create projections and read models
- [ ] Add messaging infrastructure

---

## 5. Legacy Code Migration & SQL Emitters

### 5.1 Principles

Only extract and port components that are (1) unique, (2) still needed, and (3) can be refactored to fit Uno's DI/config/logging/error handling standards. All other code will be deprecated and removed.

### 5.2 SQL Emitters Migration Checklist

| File/Class                | Purpose                                              | Needed in Uno? | Integration Action                                        | Notes |
|---------------------------|------------------------------------------------------|:--------------:|----------------------------------------------------------|-------|
| **database.py**           | DB/role/schema/bootstrap, teardown                   |      ✅        | Refactor for DI/config/logging, add tests                | Core DB setup/migration |
| **event_store.py**        | Event sourcing tables, triggers, processors          |      ✅        | Refactor for DI/config/logging, add tests                | Core event sourcing |
| **grants.py**             | Table/role grants                                   |      ✅        | Refactor for DI/config/logging if programmatic grants    | Only if Uno manages grants |
| **graph.py**              | Knowledge graph (Apache AGE) integration            |      ✅        | Refactor for DI/config/logging, add tests                | Required for knowledge graph support |
| **security.py**           | Row-level security, user/group policies             |      ✅        | Refactor for DI/config/logging if RLS needed             | Needed for advanced security, RLS |
| **table.py**              | Table creation, DDL                                 |      ✅        | Refactor for DI/config/logging, add tests                | Needed for migrations, schema mgmt |
| **triggers.py**           | Middleware triggers                                 |      ✅        | Refactor for DI/config/logging, add tests                | Needed for audit, CDC, etc. |
| **vector.py**             | pgvector extension (vector store)                   |      ✅        | Refactor for DI/config/logging, add tests                | Required for vector search/RAG |
| **vector_temp.py**        | Temp/experimental vector emitter                    |      ❓        | Review, refactor or deprecate                            | Only if needed, else deprecate |

**Legend:**

- ✅ = Required for Uno's architecture (core, knowledge graph, or vector search)
- ❓ = Review for necessity (experimental/legacy)

#### Next Steps

- [ ] For each emitter marked ✅, refactor to use DI for config/logging, remove legacy/global patterns, and add/expand tests.
- [ ] For `vector_temp.py`, review and decide whether to port or deprecate.
- [ ] Ensure all new/ported emitters are documented and tested.

### 5.3 SQL Execution/Factory Services

- [ ] Do **not** port `SQLEmitterFactoryService` or `SQLExecutionService` as-is.
- [ ] If dynamic emitter registration is needed, design a new DI-based registry/factory pattern.
- [ ] Ensure all SQL execution uses Uno's DI-managed database/session providers.

### 5.4 Database Core

- [ ] Review `legacy/database` for any unique pooling, optimization, or session helpers not present in Uno's new providers.
- [ ] Extract only:
  - Advanced query optimizers (if not already present)
  - Streaming/query cache helpers (if needed)
  - Any unique error handling patterns
- [ ] Refactor each extracted component to:
  - Use Uno's config, error, and logging systems
  - Register via DI, no global managers
  - Remove direct instantiation and legacy config
- [ ] Add tests for each refactored component.

### 5.5 Deprecation

- [ ] Mark all unported legacy modules as deprecated in `src/legacy`.
- [ ] Add a removal date/plan for deprecated code.

### 5.6 Tracking & Documentation

- [ ] Document all new/refactored components and their DI patterns.
- [ ] Add checkboxes for each extracted/refactored component in this section.
- [ ] Update this plan as progress is made.

---

## 6. Event Sourcing, DDD, and Advanced Storage

### 6.1 Current State Assessment

- [x] `DomainEvent`: Canonical, immutable, Pydantic-based event model with upcasting, hash chaining, and deterministic serialization.
- [x] `Event Store` (abstract/in-memory): Canonical serialization, result-based error handling, DI/logging integration.
- [ ] `Event Store` (production-grade, e.g. Postgres, file): Needs full implementation and tests.
- [x] `EventSourcedRepository`: Generic, DI-ready repository for aggregates, using event store and publisher.
- [ ] `AggregateRoot`/`ValueObject`: Needs full documentation, examples, and bounded context support.
- [x] `Event Handler Framework`: Handler/middleware/registry system for event-driven workflows, async/sync, discovery.
- [x] `Snapshots`: Protocols and strategies for snapshotting, with Postgres/SQL support.
- [x] `Unit of Work`: Abstract and in-memory/Postgres UoW patterns for transactional event persistence.
- [ ] `Sagas`/`Projections`: Orchestration and integration incomplete.

### 6.2 Integration Points

- [x] DI/Logging/Error Handling: All core event components are DI-injectable, use structured logging, and monad-style error handling.
- [ ] Tests: More aggregate, snapshot, and saga tests needed.
- [ ] Docs: Comprehensive guide and migration plan missing.

### 6.3 Implementation Plan: PostgresEventStore

- Class: `PostgresEventStore(EventStore[E])`
- Location: `src/uno/core/events/postgres_event_store.py`
- Implements all abstract methods from `EventStore` using async Postgres access.
- Table: `uno_events` (UUID PK, aggregate_id, event_type, version, timestamp, payload)
- Indexes: On `aggregate_id`, `event_type`, and (`aggregate_id`, `version`).
- Methods: `save_event`, `get_events`, `replay`, etc. (see detailed plan in legacy docs)
- Concurrency: Use Postgres transactions for atomicity. Enforce optimistic concurrency by checking (`aggregate_id`, `version`).
- Testing: Integration tests (pytest) for CRUD, replay, error, upcasting, etc.

---

## 7. Architectural Decisions

- All event and domain abstractions must be DI-injectable, use structured logging, and monad-based error handling.
- Canonical event serialization and hash chaining are enforced for all persistence and transport.
- Event upcasting and migration must be first-class, with registry-based versioning.
- Snapshots are pluggable and strategy-driven.
- All code must use modern Python (3.13+), Pydantic 2, and Uno idioms.
- No legacy code should be registered or imported into Uno unless it has been refactored for DI, config, and error handling compliance.

---

## 8. Critical Issues Blocking Production Use

- [ ] **Incomplete Core Implementations**: Domain model, event sourcing
- [ ] **Integration Gaps**: Components are isolated with unclear integration points
- [ ] **Documentation**: Comprehensive documentation for APIs and patterns
- [ ] **Testing**: Integration tests, performance benchmarks, error handling tests
- [ ] **Modern Python Usage**: Update Pydantic, fix type hints, use consistent patterns
- [ ] **Infrastructure Integration**: Complete missing event store, saga, and UoW integrations
- [ ] **Strict DI Enforcement**: Ensure all core services use DI, not globals
- [ ] **Error Handling Consistency**: Ensure monad-based error handling throughout

---

## 9. Next Steps (Prioritized & Tracked)

### Immediate (Sprint)

#### Domain Refactor Roadmap (Q2 2025)

##### Service Layer Modernization Checklist
- [ ] Ensure every `Failure` returned from service methods includes contextual details in `DomainValidationError.details`.
- [ ] Add or improve error context details in all `Failure` returns (consider a helper for standardization).
- [ ] Expand/verify test coverage for all error paths (repo, domain, logging), asserting error context.
- [ ] Refactor to use repository interfaces/protocols for service/infra decoupling.
- [ ] Update log messages to use structured format for critical events/errors.
- [ ] Apply this service layer pattern to all remaining aggregates/services.
- [ ] Add/update docstrings/examples for service methods showing error handling.

- Canonical plan: see EVENT_REFACTOR_PLAN.md for all event sourcing and DDD progress, decisions, and implementation notes.
- [x] Fix event sourcing/DTO mismatch for Vendor (EmailAddress value object wrapping)
- [ ] Sweep all aggregates for value object/DTO consistency (ensure all event replay reconstructs correct types)
- [ ] Refactor event classes for explicit context propagation and Result-based construction
- [ ] Expand domain validation and invariant enforcement (validate() contracts for all aggregates/value objects)
- [ ] Modernize all type hints (PEP 604, Uno conventions) and Pydantic usage (v2 compliance)
- [ ] Add/complete documentation for domain modeling, Result error handling, and event sourcing best practices
- [ ] Add integration tests for event store roundtrips and error propagation
- [ ] Finalize user/developer documentation for Uno domain modeling, Result error handling, and best practices
- [ ] Track all further progress and decisions in EVENT_REFACTOR_PLAN.md only

- [x] Refactor InMemoryEventStore for strict DI logging
- [x] Create/validate tests for InMemoryEventStore logging
- [x] Refactor MetricsMiddleware and related middleware for strict DI logging
- [x] Add/validate tests for MetricsMiddleware logging and metrics
- [x] Refactor CircuitBreakerMiddleware for strict DI logging
- [x] Add/validate tests for CircuitBreakerMiddleware logging and error handling
- [x] Refactor EventHandlerRegistry to require DI-injected LoggerService
- [x] Replace legacy logging calls with structured_log
- [x] Update documentation for DI-logging and structured logging requirements
- [x] Ensure all tests pass and logger is required
- [x] Remove all legacy/global logging from event registry
- [ ] Add or update tests for those modules to verify logging and error handling
- [ ] Add DI integration tests and logging performance benchmarks
- [ ] Finalize and publish migration/user guide
- [ ] Sweep for Pydantic/type hint modernization in all event infrastructure
- [ ] Implement or stub `uno.sql` for Postgres event store tests, or update tests to skip if not available

### Short-Term

- [ ] Migrate all modules/utilities to strict DI logging
- [ ] Add or update tests to verify error context in all error paths (service/integration)
- [ ] Complete documentation and user guides
- [ ] Benchmark logging and DI performance

### Long-Term

- [ ] Complete domain model implementation
- [ ] Implement event sourcing
- [ ] Create infrastructure integrations
- [ ] Add comprehensive tests
- [ ] Modernize codebase (fix deprecation warnings)
- [ ] Consolidate duplicated code
- [ ] Add benchmarks and performance tests

---

## Blockers & Risks

- [ ] **Event Store Integration:** Postgres event store tests may be blocked due to missing `uno.sql` module. Must implement/stub or update tests to skip if not available. InMemoryEventStore is fully tested and compliant.
- [ ] **Documentation:** Logging/DI migration guide and user docs need to be finalized.
- [ ] **Performance:** Logging and DI performance benchmarks outstanding.
- [ ] **Modern Python:** Sweep for Pydantic deprecation warnings, update type hints, and ensure idiomatic 3.13+ usage.
- [ ] **Lint:** Sweep for unused imports and fix warnings after all refactors.

---

_This checklist is a living document. Update it as implementation progresses. Mark items as complete [x] when they pass review and testing._

---

## Notes

- CircuitBreakerMiddleware is now fully migrated to DI-injected LoggerService, with all tests passing and legacy/global loggers removed.
- There is a warning about event_type shadowing in FakeEvent in the tests; this is safe for test usage but could be cleaned up for strictness.
- Performance benchmarks and DI integration tests are still outstanding.
- Next step: migrate EventHandlerRegistry to strict DI logging and add/validate tests for it.
