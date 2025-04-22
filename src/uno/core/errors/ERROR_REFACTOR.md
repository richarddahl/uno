# Uno Error Refactor Checklist

## Refactor Review Summary (2025-04-21)
- All core error-raising functions in the specified files have been refactored to use the `Success`/`Failure` monad pattern.
- Work remains to update all call sites, refactor/remove try/except blocks, add transitional wrappers if needed, review special cases, update/expand tests, and finalize documentation.

## Objective
Migrate all domain, validation, and framework error handling in Uno to use the `Success`/`Failure` result monad system, eliminating exception-based error propagation for business logic.

---

## Checklist

### 1. Identify Exception-Raising Locations
- [x] Search codebase for all `raise` statements.
- [x] Catalog all locations where domain, validation, or framework errors are raised.

### 2. Refactor Error-Raising Functions
- [x] Change function signatures to return `Success` or `Failure` (not exceptions) for all business/domain/validation errors.
- [x] Replace `raise <Error>` with `return Failure(<Error>)` in these functions.
- [x] Update docstrings to reflect new return type and pattern.

#### **Files/Lines Updated**
- [x] `src/uno/core/errors/definitions.py:630` — now uses `return Failure(ValidationError(...))`
- [x] `src/uno/core/di/provider.py:84, 99, 233, 268, 298, 325, 501` — now uses `return Failure(...)`
- [x] `src/uno/core/errors/catalog.py:44` — now uses `return Failure(ValueError(...))`

### 3. Update Call Sites
- [ ] Update all code that calls these functions to handle `Success`/`Failure` results instead of relying on exceptions.
- [ ] Remove or refactor `try/except` blocks that only handle business/domain/validation errors.

  _Note: Still in progress. Requires codebase-wide search and update of all call sites and exception handling._

### 4. Transitional Wrappers (If Needed)
- [ ] For legacy or third-party code that still raises exceptions, wrap calls with a utility to convert exceptions to `Failure`.

  _Note: Review needed for legacy/third-party integrations. Not yet implemented._

### 5. Special Cases
- [ ] Review internal errors (e.g., `RuntimeError` in result monad) and decide if they should remain as exceptions (for API misuse) or be handled via `Failure`.

  _Note: Needs explicit review/decision. Not yet finalized._

### 6. Testing
- [ ] Update and expand tests to assert on `Success`/`Failure` results, not exceptions.

  _Note: Test suite update in progress. Some tests may still assert on exceptions._

### 7. Documentation
- [ ] Update documentation to describe the new error handling pattern and provide examples.

  _Note: Documentation update pending. Examples and migration notes to be added._

---

## Example Refactor

**Before:**
```python
def do_something(...):
    ...
    if error_condition:
        raise ValidationError(...)
```

**After:**
```python
def do_something(...):
    ...
    if error_condition:
        return Failure(ValidationError(...))
```

---

## Progress Tracking
- [x] All relevant functions refactored
- [ ] All call sites updated
- [ ] All tests passing
- [ ] Documentation updated

---

## Notes
- Only use exceptions for truly unexpected, unrecoverable errors (e.g., programming errors, API misuse).
- All domain/business/validation errors must use the `Success`/`Failure` monad pattern.
