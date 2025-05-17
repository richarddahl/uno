# Uno Domain System – Issues and Review

This document lists all issues and concerns identified in the current implementation of the Uno Domain-Driven Design (DDD) system as of 2025-05-13.

## General Principles & Compliance

- [ ] **Type Hint Consistency:** Sweep for legacy typing (`Optional`, `Union`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`X | None`, `X | Y`).
- [ ] **No Built-in Shadowing:** Audit for class/function/constant names that shadow Python built-ins or imported package names.
- [ ] **No Python Keywords as Identifiers:** Confirm no accidental use of Python keywords as identifiers.
- [ ] **Pydantic v2 Compliance:** Ensure all Pydantic usage is v2 idiomatic (use `ConfigDict`, not `class Config`).

## DDD Patterns & Protocols

- [ ] **Protocol/Implementation Divergence:** There is inconsistency between protocol signatures (async methods in `AggregateRootProtocol`, `EntityProtocol`, etc.) and concrete implementations (many are sync). Align protocol and implementation, or document why divergence is necessary.
- [ ] **Aggregate/Entity/ValueObject Patterns:** Ensure all aggregates, entities, and value objects enforce invariants and validation via Pydantic validators, and that these are covered by tests.
- [ ] **Event Sourcing Consistency:** The event sourcing flow (rehydration, event application, publishing) is split between sync and async methods. Standardize on async.
- [ ] **Repository Protocols:** Confirm all repositories implement the full protocol (async CRUD, event sourcing, snapshotting if supported), and that type bounds are respected throughout.
- [ ] **Event Sourced Aggregate:** `EventSourcedAggregate` is a stub with no base class or protocol enforcement. Expand or document its intended usage.
- [ ] **Minimal/Empty Files:** `repository.py` is empty. Remove or implement as needed.

## Error Handling & Logging

- [ ] **Error Context Propagation:** Ensure all domain errors propagate full context (aggregate id, event type, etc.) for debugging. Audit custom error classes for completeness.
- [ ] **Logger Injection:** Logger is injected as an attribute but sometimes used without checks (`self._logger.error`). Always check for logger presence or enforce via DI.

## Extensibility, Testability, and Documentation

- [ ] **Internal Documentation:** Some internal/private methods lack docstrings or usage notes. Add for maintainers.
- [ ] **Test Coverage:** No evidence of comprehensive unit tests for error paths, event upcasting, or invariant enforcement. Add/expand tests for these scenarios.
- [ ] **Snapshotting:** Snapshot logic is minimal and not integrated with aggregates or repositories. Specify design or remove if not implemented.
- [ ] **Config/DI Integration:** `config.py` and `di.py` exist but their integration with the domain layer is unclear. Document or refactor.

## Production Readiness Review: Event Sourcing (`src/uno/events`) & DDD (`src/uno/domain`)

- **Issue**: Most models use Pydantic v2, but some config patterns (e.g., `ConfigDict` vs. `class Config`) and type hints may not fully align with Uno’s rules (modern Python, no `Optional`, use `X | None`, etc.).
- **Recommendation**: Audit all models for Pydantic v2 compliance and modern type hints. Replace legacy/deprecated patterns. Ensure all type hints follow Uno conventions.

### 4. Dependency Injection, Config, and Logging

- **Issue**: DI, config, and logging are present in many places, but not always enforced or documented. Some classes accept logger/config via constructor but do not document or validate DI usage.
- **Recommendation**: Enforce DI for logger, config, and other dependencies in all extensible classes. Document required dependencies and validate in constructors. Use Uno’s DI/config/logging systems everywhere.

### 5. Testability and Extensibility

- **Issue**: Some core classes are tightly coupled via inheritance, making them harder to test or extend. Minimal/no tests for error paths, upcasting, and edge cases in some modules.
- **Recommendation**: Refactor to favor composition and Protocols over inheritance. Expand test coverage, especially for error paths, upcasting, and invariants. Use pytest fixtures and Uno’s test conventions.

### 6. Documentation and Examples

- **Issue**: Some modules/classes lack docstrings or usage examples. Event upcasting/versioning and repository usage are not always documented.
- **Recommendation**: Add comprehensive docstrings, usage examples, and migration guides for all public APIs, especially for event upcasting, repository patterns, and aggregate lifecycle.

### 7. Event Sourcing/DDD Gaps

- **Issue**: Some DDD/event sourcing features (e.g., snapshotting, event upcasting, invariant enforcement) are present but not fully implemented or enforced.
- **Recommendation**: Finalize and enforce all event sourcing/DDD patterns. Add validation and error handling for snapshotting, upcasting, and invariant enforcement.

---

**Action Items:**

1. Refactor all base classes to Protocols; remove forced inheritance
2. Sweep for exceptions, ensure all use UnoError subclasses and the new error handling system
3. Audit for Pydantic v2/type hint modernization
4. Enforce/document DI, config, logging usage
5. Expand test coverage for error paths, upcasting, invariants
6. Add/expand documentation and usage examples
7. Finalize and enforce event sourcing/DDD patterns

## Minor/Other Issues

- [ ] **Circular Imports:** Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially with protocols and errors.
- [ ] **Serialization Contract:** The canonical serialization contract is described in docstrings but should be enforced by tests and utilities.
- [ ] **Redundant/Unused Code:** Remove dead code or stubs (e.g., empty files, unused imports).

---

**Next Steps:**

- Sweep all domain code for modern type hints and Uno idioms
- Standardize sync/async usage in protocols and implementations
- Improve test coverage for invariants, event sourcing, and error paths
- Expand documentation, especially for maintainers and advanced DDD patterns
- Audit for circular imports, dead code, and protocol/implementation mismatches

*Generated by automated review on 2025-05-13.*
