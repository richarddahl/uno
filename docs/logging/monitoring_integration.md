# Integration with Monitoring Tools

## Overview

The Uno logging system integrates with various monitoring and observability tools to provide comprehensive insights into application behavior. This integration allows logs to be correlated with metrics, traces, and other observability data for a complete view of system performance and health.

## Distributed Tracing Integration

### OpenTelemetry Integration

Uno's logging system automatically integrates with OpenTelemetry to correlate logs with traces:

```python
from uno.core.logging.logger import LoggerService
from uno.core.tracing import get_tracer

# Get a logger and tracer
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Create a span
with tracer.start_as_current_span("operation_name") as span:
    # Current span context is automatically added to logs
    logger.info("Operation started")
    
    # Perform operation
    result = perform_operation()
    
    # Log with additional context
    logger.info("Operation completed", extra={"result": result})
```

The logs will automatically include:

- `trace_id`: The trace identifier
- `span_id`: The span identifier
- `trace_flags`: Tracing flags like sampled status

### Manual Trace Context

You can also manually add trace context:

```python
from uno.core.logging import logging_context
from opentelemetry import trace

# Get current span
current_span = trace.get_current_span()
trace_id = current_span.get_span_context().trace_id
span_id = current_span.get_span_context().span_id

# Add trace context to logs
with logging_context(trace_id=trace_id, span_id=span_id):
    logger.info("Processing with trace context")
```

## Metrics Integration

### Logs-Based Metrics

Extract metrics from logs:

```python
from uno.core.logging import register_metrics_extractor

# Define a metrics extractor
def extract_api_metrics(log_record):
    if "api_response_time_ms" in log_record:
        # Record a histogram metric
        return {
            "name": "api_response_time",
            "type": "histogram",
            "value": log_record["api_response_time_ms"],
            "labels": {
                "endpoint": log_record.get("api_endpoint", "unknown"),
                "status": log_record.get("api_status", "unknown")
            }
        }
    return None

# Register the extractor
register_metrics_extractor(extract_api_metrics)

# Usage in code
logger.info("API request completed", extra={
    "api_endpoint": "/users",
    "api_status": 200,
    "api_response_time_ms": 45
})
```

### Logging Performance Metrics

Expose logging system performance:

```python
from uno.core.logging import configure_logging

configure_logging(
    metrics_enabled=True,
    metrics_output="prometheus"
)
```

## Integration with Specific Monitoring Systems

### Datadog Integration

Configure for Datadog:

```python
from uno.core.logging import configure_logging

configure_logging(
    handlers={
        "datadog": {
            "enabled": True,
            "api_key": "your-datadog-api-key",
            "service": "uno-application",
            "source": "python",
            "tags": ["env:production", "region:us-west"]
        }
    }
)
```

Log with Datadog-specific attributes:

```python
logger.info("User login", extra={
    "dd.trace_id": trace_id,
    "dd.span_id": span_id,
    "service": "authentication-service",
    "env": "production"
})
```

### ELK Stack Integration

Configure for the ELK Stack (Elasticsearch, Logstash, Kibana):

```python
from uno.core.logging import configure_logging

configure_logging(
    format="JSON",  # Use JSON format for ELK
    handlers={
        "file": {
            "path": "/var/log/uno/application.log",
            "format": "JSON"
        }
    }
)
```

When using Logstash, you can direct logs to it via TCP:

```python
configure_logging(
    handlers={
        "logstash": {
            "host": "logstash.example.com",
            "port": 5000,
            "ssl_enabled": True,
            "ssl_verify": True,
            "additional_fields": {
                "application": "uno",
                "environment": "production"
            }
        }
    }
)
```

### Prometheus Integration

For Prometheus metrics exposure:

```python
from uno.core.logging import configure_logging

configure_logging(
    metrics_enabled=True,
    metrics_output="prometheus",
    prometheus_port=9090
)
```

This will expose metrics like:

- `uno_logging_total{level="info"}`: Counter of logs by level
- `uno_logging_errors_total`: Counter of logging errors
- `uno_logging_latency_seconds`: Histogram of logging latency

### Grafana Loki Integration

Configure for Grafana Loki:

```python
from uno.core.logging import configure_logging

configure_logging(
    handlers={
        "loki": {
            "url": "http://loki:3100/loki/api/v1/push",
            "tags": {
                "app": "uno",
                "environment": "production"
            },
            "batch_size": 100,
            "timeout": 5.0
        }
    }
)
```

## Advanced Monitoring Integration

### Health Checks Based on Logs

Configure log-based health checks:

```python
from uno.core.logging import configure_log_health_checks

configure_log_health_checks({
    "error_rate": {
        "window_seconds": 60,
        "threshold": 5,  # 5 errors per minute is unhealthy
        "levels": ["ERROR", "CRITICAL"]
    },
    "database_errors": {
        "window_seconds": 300,
        "pattern": "database connection",
        "threshold": 3
    }
})
```

### Alerting Based on Logs

Configure log-based alerts:

```python
from uno.core.logging import configure_log_alerts

configure_log_alerts({
    "security_alert": {
        "pattern": "authentication failed",
        "count_threshold": 5,
        "time_window_seconds": 60,
        "cooldown_seconds": 300,
        "channels": ["slack", "email"],
        "severity": "high"
    },
    "database_alert": {
        "pattern": "database connection failed",
        "count_threshold": 3,
        "time_window_seconds": 180,
        "channels": ["pagerduty", "slack"],
        "severity": "critical"
    }
})
```

### Log Sampling for High-Volume Systems

Use sampling for high-volume production systems:

```python
from uno.core.logging import configure_logging

configure_logging(
    sampling={
        "debug": 0.01,  # Sample 1% of debug logs
        "info": 0.1,    # Sample 10% of info logs
        "warning": 1.0, # Keep all warning logs
        "error": 1.0,   # Keep all error logs
        "critical": 1.0 # Keep all critical logs
    }
)
```

## Cross-Service Correlation

### Microservices Request Tracing

Trace requests across microservices:

```python
from uno.core.logging.logger import LoggerService
from uno.core.tracing import get_current_trace_context

logger = get_logger(__name__)

def handle_request(request):
    # Extract trace context from incoming request
    trace_context = get_current_trace_context(request)
    
    with logging_context(**trace_context):
        logger.info("Processing request")
        
        # Make downstream request with trace context
        response = make_downstream_request(
            url="http://other-service/api",
            headers=trace_context
        )
        
        logger.info("Request processed", extra={"status": response.status})
```

### Centralized Logging

Configure for centralized logging:

```python
from uno.core.logging import configure_logging

configure_logging(
    centralized_logging={
        "enabled": True,
        "service": "order-service",
        "environment": "production",
        "version": "1.2.3",
        "region": "us-west-2",
        "format": "JSON"
    }
)
```

## Visualization and Analysis

### Creating Custom Dashboards

Use the log data for custom dashboards:

```python
# Log with metrics that can be visualized
logger.info("API request processed", extra={
    "endpoint": "/users",
    "method": "GET",
    "status": 200,
    "response_time_ms": 120,
    "user_id": "user-123",
    "resource": "user",
    "resource_id": "user-456"
})
```

This structured data can be used to create dashboards showing:

- API response time by endpoint
- Success/failure rates
- Resource usage patterns
- User activity

### Log Analytics Queries

Example queries for common log analytics platforms:

#### Elasticsearch Query

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "ERROR" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "aggs": {
    "errors_over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "interval": "1m"
      }
    }
  }
}
```

#### Loki Query

```
{app="uno"} | json | level="ERROR" | unwrap response_time_ms | rate(5m)
```

## Summary

The Uno logging system provides deep integration with modern monitoring and observability platforms, allowing you to:

1. Correlate logs with traces for end-to-end visibility
2. Generate metrics from logs for performance monitoring
3. Set up alerts based on log patterns
4. Sample logs appropriately for high-volume systems
5. Visualize log data in dashboards

These capabilities enable comprehensive monitoring of your application, helping you identify and resolve issues quickly while gaining insights into system behavior.
