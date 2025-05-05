# Uno Framework Refactoring Plan

This document outlines a phased refactoring process to transform Uno into a production-ready, modern Python framework for DDD and event-sourced applications. The plan is prioritized to enable immediate use of domain modeling and event sourcing capabilities while infrastructure concerns are developed in parallel.

## Phase 1: Domain Modeling Essentials (Priority)

These tasks must be completed first to enable using Uno for domain modeling in separate applications.

### Minimal DI Support

- [x] Initial DI implementation exists in uno.infrastructure.di
  - [x] Basic service registration with ServiceCollection
  - [x] Service lifecycle management (singleton, scoped, transient)
  - [x] Service resolution infrastructure

- [ ] Simplify and stabilize dependency injection core
  - [ ] Remove auto-discovery/auto-registration complexity
    - [x] Currently enabled by default via UNO_DI_AUTO_REGISTER
    - [ ] Remove auto-registration to enforce explicit dependencies
    - [ ] Simplify registration API to focus on domain needs
  - [ ] Create explicit registration API with fluent interface
    - [ ] Add builder pattern for service registration
    - [ ] Simplify registration methods for domain services
    - [ ] Add type safety with proper generics
  - [ ] Implement type-safe service resolution
    - [ ] Add proper type hints for service resolution
    - [ ] Implement generic type resolution
    - [ ] Add validation for service implementations

- [ ] Add dependency graph analysis
  - [ ] Implement circular dependency detection
    - [ ] Add dependency graph construction
    - [ ] Detect and report circular dependencies
    - [ ] Add clear error messages for cycles
  - [ ] Create debug visualization
    - [ ] Add dependency tree visualization
    - [ ] Create service dependency graph
    - [ ] Add debugging tools for dependency resolution

- [ ] Improve error handling
  - [ ] Add Result-based service resolution
    - [ ] Implement Result pattern for service resolution
    - [ ] Add error context propagation
    - [ ] Create specific DI-related error types
  - [ ] Add context-rich error messages
    - [ ] Include dependency chain in errors
    - [ ] Add resolution hints for common issues
    - [ ] Create troubleshooting documentation

- [ ] Create simple container configuration
  - [ ] Add environment-based configuration
    - [ ] Support different profiles (dev, test, prod)
    - [ ] Add conditional registration based on environment
    - [ ] Implement configuration validation
  - [ ] Add basic configuration options
    - [ ] Strict mode for dependency validation
    - [ ] Service resolution validation
    - [ ] Configuration validation

- [ ] Adapt domain objects for DI compatibility
  - [ ] Update `AggregateRoot` initialization
    - [ ] Make service dependencies explicit via constructor injection
    - [ ] Add optional factory methods for container-based creation
    - [ ] Create validation for required dependencies
  - [ ] Refactor domain services
    - [ ] Define domain service interface protocol hierarchy
    - [ ] Implement constructor injection patterns
    - [ ] Add explicit dependency documentation
  - [ ] Enhance repository implementations
    - [ ] Update repository initialization with explicit dependencies
    - [ ] Create factory methods for container-based creation
    - [ ] Add debugging/logging of dependency resolution

- [ ] Implement testing support for DI
  - [ ] Create test-specific container
    - [ ] Add mock service registration helpers
    - [ ] Implement fixture support for common services
    - [ ] Create container state verification tools
  - [ ] Add service mocking utilities
    - [ ] Implement auto-mocking container
    - [ ] Create service verification helpers
    - [ ] Add dependency stub generation
  - [ ] Enable domain object testing
    - [ ] Create mock repositories factory
    - [ ] Implement domain service test doubles
    - [ ] Add integration test helpers for domain + DI

- [ ] Provide documentation and examples
  - [ ] Create DI usage guide for domain modeling
    - [ ] Document service registration patterns
    - [ ] Add examples for common domain services
    - [ ] Create troubleshooting guide for DI issues
  - [ ] Add migration guide from old DI pattern
    - [ ] Document changes in service registration
    - [ ] Provide examples of refactored code
    - [ ] Add automatic migration scripts if feasible
  - [ ] Document testing patterns with DI
    - [ ] Show examples of domain object testing with DI
    - [ ] Demonstrate service mocking strategies
    - [ ] Create patterns for integration testing

### Core Domain Model Stabilization

- [ ] Complete and stabilize base domain classes
  - [ ] Ensure `Entity`, `AggregateRoot`, and `ValueObject` are fully typed and tested
  - [ ] Fix any bugs in identity handling and equality operations
  - [ ] Complete validation hooks and invariant enforcement
  - [ ] Add helpers for common domain operations

### Event Definition System

- [ ] Stabilize event definition and versioning
  - [ ] Ensure `DomainEvent` base class is complete with proper versioning support
  - [ ] Fix any issues with event registration system
  - [ ] Complete event serialization/deserialization (without persistence dependencies)
  - [ ] Add comprehensive event validation with clear error messages

### Result-Based Error Handling (Core)

- [ ] Enhance `Result` monad for domain operations
  - [ ] Ensure `Success`/`Failure` types are fully featured and stable
  - [ ] Add helpers for common domain error patterns
  - [ ] Create domain-specific error types and taxonomies
  - [ ] Add clear error context propagation

### Type System Modernization (Essential Parts)

- [ ] Fix critical type issues
  - [ ] Convert core domain types to modern syntax (`X | Y` not `Union[X, Y]`)
  - [ ] Ensure Pydantic models use v2 patterns in domain classes
  - [ ] Fix mypy errors in domain and event code
  - [ ] Document type usage patterns for domain modeling

### Documentation for Domain Modeling

- [ ] Create essential documentation
  - [ ] Add "Getting Started with Domain Modeling" guide
  - [ ] Document event definition and versioning patterns
  - [ ] Create examples of domain objects and events
  - [ ] Document error handling patterns for domain operations

## Phase 2: Event Sourcing Essentials (High Priority)

These components enable basic event sourcing capabilities without full infrastructure integration.

### Memory-Based Event Sourcing

- [ ] Implement in-memory event store for development
  - [ ] Create simple `InMemoryEventStore` implementation
  - [ ] Add basic event repository functionality
  - [ ] Support loading/saving aggregates without persistence
  - [ ] Add basic snapshotting support

### Event Upcast System Completion

- [ ] Ensure event schema evolution works reliably
  - [ ] Complete event versioning and upcasting system
  - [ ] Create helpers for defining event upcasters
  - [ ] Add validation for upcasted events
  - [ ] Document event schema evolution patterns

### Basic Aggregate Testing Support

- [ ] Add testing utilities for events and aggregates
  - [ ] Create `TestEventStore` implementation
  - [ ] Add fixtures for testing aggregates with events
  - [ ] Create helpers for asserting on event sequences
  - [ ] Add documentation for testing event-sourced aggregates

## Phase 3: Core Infrastructure (Medium Priority)

These components can be developed while domain modeling is underway.

### Basic Event Publication

- [ ] Implement simple event dispatching
  - [ ] Create in-memory event dispatcher
  - [ ] Support subscription to domain events
  - [ ] Add basic handler registration
  - [ ] Document event subscription patterns

### Simple Configuration System

- [ ] Stabilize configuration for domain components
  - [ ] Ensure type-safe configuration for domain services
  - [ ] Add environment variable support
  - [ ] Create configuration validation
  - [ ] Document configuration patterns

## Phase 4: Production Infrastructure (Future)

These components can be deferred until domain modeling is well established.

### Persistence and Integration

- [ ] Add durable event storage
  - [ ] Implement SQL event store
  - [ ] Add NoSQL adapters
  - [ ] Implement optimistic concurrency
  - [ ] Create projection framework

### Advanced Event Processing

- [ ] Implement reliable event publication
  - [ ] Add outbox pattern
  - [ ] Create idempotent event handlers
  - [ ] Implement event routing
  - [ ] Add dead-letter queues

### Production Features

- [ ] Add observability and security
  - [ ] Implement structured logging
  - [ ] Add metrics and tracing
  - [ ] Create secrets management
  - [ ] Implement authentication/authorization hooks

## Phase 5: Developer Experience (Future)

These components enhance productivity but aren't essential for initial use.

### Advanced Documentation

- [ ] Complete comprehensive documentation
  - [ ] Create architectural guides
  - [ ] Add pattern catalog
  - [ ] Create video tutorials
  - [ ] Document integration patterns

### Developer Tooling

- [ ] Add productivity tools
  - [ ] Create CLI scaffolding tools
  - [ ] Add code generators
  - [ ] Implement debugging utilities
  - [ ] Create visualization tools

## Implementation Strategy for Parallel Development

For your specific need to use domain modeling while refactoring:

1. **Establish a clear API boundary**
   - Create a stable public API for domain modeling
   - Mark experimental/unstable features clearly

2. **Version and package thoughtfully**
   - Use a separate namespace for stable components (e.g., `uno.domain.stable`)
   - Consider shipping domain components as a separate package initially

3. **Document known limitations**
   - Clearly identify what works and what doesn't
   - Provide workarounds for incomplete features

4. **Create a minimal example application**
   - Build a reference app showing the stable usage patterns
   - Use this to validate the domain modeling experience

## Immediate Next Steps

1. Create a stable domain modeling package with:
   - Core domain classes (Entity, AggregateRoot, ValueObject)
   - Event definition and versioning system
   - Result monad for error handling
   - In-memory implementations for development

2. Document the stable patterns for:
   - Defining domain objects
   - Creating and evolving events
   - Handling domain errors
   - Testing domain logic

This approach allows you to start using Uno for domain modeling immediately while continuing to enhance the infrastructure components in parallel.
