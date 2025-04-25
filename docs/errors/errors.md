# Uno Core Errors - Developer Documentation

_This document provides an in-depth look at the error handling system within `uno.core.errors`, guiding developers on usage, extension, and integration._

---

## Table of Contents

1. [Introduction](#introduction)
2. [Design Philosophy](#design-philosophy)
3. [Error Types & Structure](#error-types--structure)
4. [Usage Patterns](#usage-patterns)
5. [Extending the Error System](#extending-the-error-system)
6. [Integration Guidelines](#integration-guidelines)
7. [Testing & Debugging](#testing--debugging)
8. [Frequently Asked Questions](#frequently-asked-questions)
9. [Troubleshooting](#troubleshooting)
10. [References](#references)

---

## Introduction

`uno.core.errors` offers a comprehensive, extensible mechanism for error definition and propagation. It ensures that all errors are expressive, traceable, and actionable.

## Design Philosophy

- **Consistency**: All Uno modules follow similar patterns for raising and handling errors.
- **Extensibility**: New error types can be created with minimal boilerplate.
- **Meaningful Metadata**: Attach codes and context to aid in automated and manual diagnosis.
- **Separation of Concerns**: Domain logic and error handling are cleanly separated.

## Error Types & Structure

### Base Error: `FrameworkError`

All core errors inherit from `FrameworkError`, which extends the default language error/exception. Its main features:

- `message` (str): Description of the error.
- `code` (str): Error identifier (e.g., `"DATA_NOT_FOUND"`).
- `context` (dict): Structured details relevant to the error.

#### Example Definition

```python
class FrameworkError(Exception):
    def __init__(self, message, code=None, context=None):
        super().__init__(message)
        self.code = code
        self.context = context or {}
```

## Usage Patterns

### Raising Errors

```python
from uno.core.errors import FrameworkError

raise FrameworkError("Missing configuration.", code="CONFIG_MISSING", context={"file": "settings.yaml"})
```

### Handling & Logging

```python
try:
    ...
except FrameworkError as err:
    logger.error(f"Caught Error [{err.code}]: {err} | Context: {err.context}")
    if err.code == "CONFIG_MISSING":
        # Recovery logic
```

### Wrapping Lower-Level Errors

You can wrap third-party/library errors for consistency:

```python
try:
    db.connect()
except SomeLibraryError as ex:
    raise FrameworkError("Database unavailable", code="DB_UNAVAILABLE", context={"original": repr(ex)})
```

## Extending the Error System

### Creating Domain-Specific Errors

Define your own types for further granularity:

```python
class ValidationError(FrameworkError):
    def __init__(self, message, context=None):
        super().__init__(message, code="VALIDATION_FAIL", context=context)
```

### Best Practices

- Use descriptive `code` values for programmatic checks.
- Populate `context` with any data useful for debugging (input values, request IDs, etc.).
- Document all custom error classes.

## Integration Guidelines

- Catch and handle `FrameworkError` in orchestrator-level code.
- Surface only user-appropriate error messages to external clients or interfaces.
- Log full context for internal audits and debugging.

## Testing & Debugging

- Write tests anticipating specific error codes and contexts.
- Use logging to trace error origination.
- Review stack traces for error propagation paths.

## Frequently Asked Questions

**Q:** _Should I use standard exceptions or only FrameworkError?_  
**A:** Favor `FrameworkError` for all application logic errors; reserve standard exceptions for truly exceptional runtime failures.

**Q:** _Can I attach objects in the context?_  
**A:** Yes, as long as they are serializable; avoid very large or complex references.

## Troubleshooting

- **Problem:** Unexpected error types caught  
  **Solution:** Ensure all raises in your modules use `FrameworkError` or its descendants.

- **Problem:** Context is missing or unhelpful  
  **Solution:** Audit all errors for context population; automate this in custom error class constructors if possible.

## References

- [`src/uno/core/errors/README.md`](../../src/uno/core/errors/README.md)
- Python [Exception documentation](https://docs.python.org/3/library/exceptions.html)