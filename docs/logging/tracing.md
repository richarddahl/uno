# Uno Logging: Trace & Correlation IDs

## Overview
Trace/correlation/request IDs enable end-to-end observability and distributed tracing in Uno applications. Uno's logging system makes it easy to propagate and log these IDs in every log record.

## How to Use

### Generate a New Trace Context
```python
trace_context = logger_service.new_trace_context()
```

### Use a Trace Scope
```python
with logger_service.trace_scope(logger_service, trace_context=trace_context):
    logger.info("Inside a trace scope!")
```

### Nested Trace Scopes
```python
with logger_service.trace_scope(logger_service, correlation_id="outer"):
    logger.info("Outer scope")
    with logger_service.trace_scope(logger_service, correlation_id="inner"):
        logger.info("Inner scope")
```

## Best Practices
- Always use `trace_scope` for request/operation boundaries
- Pass trace/correlation IDs across service boundaries for distributed tracing
- Use `structured_log` to log trace context explicitly if needed

## Output
- Trace/correlation IDs are present in the `context` field of all structured/JSON logs
- Field names: `correlation_id`, `trace_id`, etc.
