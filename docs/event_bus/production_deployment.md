# Dead Letter Queue Production Deployment Guide

This guide provides best practices and recommendations for deploying the Dead Letter Queue (DLQ) in a production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Deployment Strategies](#deployment-strategies)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Performance Tuning](#performance-tuning)
6. [Security Considerations](#security-considerations)
7. [Disaster Recovery](#disaster-recovery)
8. [Scaling](#scaling)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.13+
- Redis 6.2+ (for persistent storage)
- Prometheus & Grafana (for monitoring)
- Sufficient disk space for event storage

## Configuration

### Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379/0

# Optional with defaults
DLQ_MAX_RETRIES=5
DLQ_RETRY_DELAY=60  # seconds
DLQ_MAX_QUEUE_SIZE=100000
DLQ_RETENTION_DAYS=7
DLQ_CONCURRENCY=10
DLQ_BATCH_SIZE=100
```

### Recommended Configuration

```python
from uno.event_bus.dead_letter import DeadLetterQueue, DeadLetterConfig
from redis.asyncio import Redis

# Initialize with production settings
redis = Redis.from_url("redis://prod-redis:6379/0")

config = DeadLetterConfig(
    max_retries=5,
    retry_delay=60,  # seconds
    max_queue_size=100_000,
    retention_days=7,
)

dlq = DeadLetterQueue(redis=redis, config=config)
```

## Deployment Strategies

### 1. Sidecar Pattern (Recommended)

Deploy the DLQ as a sidecar container alongside your main application:

```yaml
# Kubernetes example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        env:
          - name: DLQ_ENABLED
            value: "true"
          - name: DLQ_REDIS_URL
            value: "redis://dlq-redis:6379/0"
      - name: dlq-sidecar
        image: my-app:latest
        command: ["python", "-m", "uno.cli.main", "dead-letter", "worker"]
        env:
          - name: DLQ_WORKER_MODE
            value: "true"
          - name: DLQ_REDIS_URL
            value: "redis://dlq-redis:6379/0"
```

### 2. Dedicated Service

For high-volume systems, deploy the DLQ as a dedicated service:

```yaml
# docker-compose.prod.yml
services:
  app:
    image: my-app:latest
    environment:
      - DLQ_ENABLED=true
      - DLQ_SERVICE_URL=http://dlq-service:8000

  dlq-service:
    image: my-app:latest
    command: ["python", "-m", "uno.cli.main", "dead-letter", "service"]
    environment:
      - DLQ_SERVICE_PORT=8000
      - DLQ_REDIS_URL=redis://dlq-redis:6379/0
    ports:
      - "8000:8000"
    deploy:
      replicas: 3

  dlq-redis:
    image: redis:7.0
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - dlq-data:/data
    deploy:
      resources:
        limits:
          memory: 4G

volumes:
  dlq-data:
```

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| `dlq_queue_size` | Gauge | Current number of dead letters | > 1000 |
| `dlq_processing_seconds` | Histogram | Time to process dead letters | p99 > 5s |
| `dlq_retry_count` | Counter | Number of retry attempts | > 100/hour |
| `dlq_dlq_errors` | Counter | Failed processing attempts | > 10/minute |

### Example Prometheus Alert Rules

```yaml
groups:
- name: dlq.rules
  rules:
  - alert: HighDLQBacklog
    expr: dlq_queue_size > 1000
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "High number of dead letters in DLQ"
      description: "DLQ has {{ $value }} messages waiting to be processed"

  - alert: DLQProcessingErrors
    expr: rate(dlq_processing_errors_total[5m]) > 10
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate in DLQ processing"
      description: "{{ $value }} errors per second in DLQ processing"
```

### Grafana Dashboard

Import the following dashboard to monitor DLQ health:

1. DLQ Queue Size (Gauge)
2. Processing Time (Histogram)
3. Events Processed (Counter)
4. Error Rate (Graph)
5. Retry Distribution (Pie Chart)

## Performance Tuning

### Redis Configuration

```ini
# Recommended redis.conf settings for DLQ
maxmemory 4gb
maxmemory-policy allkeys-lru
maxmemory-samples 10
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
```

### Tuning Parameters

1. **Batch Size**: Adjust based on event size and network latency
   ```python
   # Optimal batch size depends on your event size
   # Start with 100 and adjust based on performance
   await dlq.replay_events(batch_size=100)
   ```

2. **Concurrency**: Balance between CPU and I/O
   ```python
   # Number of concurrent workers
   # Start with CPU cores * 2
   await dlq.replay_events(max_concurrent=8)
   ```

3. **Retry Policy**: Set appropriate retry limits
   ```python
   config = DeadLetterConfig(
       max_retries=5,
       retry_delay=60,  # Exponential backoff starts at 60s
   )
   ```

## Security Considerations

1. **TLS Encryption**: Always use TLS for Redis connections
   ```python
   redis = Redis(
       host='redis.example.com',
       ssl=True,
       ssl_cert_reqs='required',
       ssl_ca_certs='/path/to/ca.pem'
   )
   ```

2. **Authentication**: Enable Redis AUTH
   ```
   redis://:password@localhost:6379/0
   ```

3. **Network Policies**: Restrict access to Redis instances
   ```yaml
   # NetworkPolicy example for Kubernetes
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-dlq-redis
   spec:
     podSelector:
       matchLabels:
         app: dlq-redis
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: my-app
       ports:
       - protocol: TCP
         port: 6379
   ```

## Disaster Recovery

### Backup Strategy

1. **Redis RDB Snapshots**:
   ```bash
   # In redis.conf
   save 900 1
   save 300 10
   save 60 10000
   ```

2. **AOF Persistence**:
   ```bash
   appendonly yes
   appendfsync everysec
   ```

3. **Scheduled Backups**:
   ```bash
   # Daily backup script
   redis-cli SAVE
   cp /var/lib/redis/dump.rdb /backup/dump-$(date +%Y%m%d).rdb
   ```

### Recovery Procedure

1. **Restore from Backup**:
   ```bash
   # Stop Redis
   systemctl stop redis
   
   # Restore backup
   cp /backup/dump-latest.rdb /var/lib/redis/dump.rdb
   
   # Set correct permissions
   chown redis:redis /var/lib/redis/dump.rdb
   
   # Start Redis
   systemctl start redis
   ```

2. **Verify Data**:
   ```bash
   redis-cli DBSIZE
   redis-cli KEYS "*" | wc -l
   ```

## Scaling

### Horizontal Scaling

1. **Sharding**:
   ```python
   from rediscluster import RedisCluster
   
   startup_nodes = [
       {"host": "redis-node-1", "port": "6379"},
       {"host": "redis-node-2", "port": "6379"},
       {"host": "redis-node-3", "port": "6379"}
   ]
   
   rc = RedisCluster(
       startup_nodes=startup_nodes,
       decode_responses=True,
       ssl=True
   )
   ```

2. **Read Replicas**:
   ```python
   # In redis.conf of read replicas
   replicaof <master-ip> 6379
   ```

### Vertical Scaling

1. **Redis Memory**: Monitor `used_memory` and scale up when approaching 70% of `maxmemory`
2. **CPU**: Scale up when CPU usage is consistently above 70%
3. **Network**: Monitor network throughput and scale as needed

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check for memory leaks in event handlers
   - Reduce `max_queue_size` if events are piling up
   - Enable Redis eviction policies

2. **Slow Processing**
   - Increase `max_concurrent`
   - Optimize event handlers
   - Check Redis and network latency

3. **Connection Issues**
   ```python
   import logging
   
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger('redis')
   logger.setLevel(logging.DEBUG)
   ```

### Debugging Commands

```bash
# Check queue size
redis-cli LLEN dead_letter_queue

# Inspect events
redis-cli LRANGE dead_letter_queue 0 10

# Monitor in real-time
redis-cli MONITOR | grep dead_letter
```

## Support

For production support, contact the Uno Platform team at support@uno.example.com or open an issue at [GitHub Issues](https://github.com/yourorg/uno/issues).
