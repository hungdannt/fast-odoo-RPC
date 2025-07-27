# Monitoring and Observability

This section covers monitoring and observability features for Zenoo RPC applications.

## Overview

Zenoo RPC provides built-in monitoring capabilities to help you track performance, debug issues, and maintain healthy applications.

## Metrics Collection

### Built-in Metrics

Zenoo RPC automatically collects:

- Request/response times
- Error rates
- Cache hit/miss ratios
- Connection pool statistics
- Retry attempt counts

### Custom Metrics

You can add custom metrics for your specific use cases:

```python
from zenoo_rpc.monitoring import metrics

# Custom counter
metrics.increment('custom.operation.count')

# Custom timing
with metrics.timer('custom.operation.duration'):
    # Your operation here
    pass
```

## Logging

### Structured Logging

Zenoo RPC uses structured logging for better observability:

```python
import logging
from zenoo_rpc import ZenooClient

# Configure logging
logging.basicConfig(level=logging.INFO)

async with ZenooClient("localhost") as client:
    # All operations are automatically logged
    await client.login("db", "user", "password")
```

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that may cause application failure

## Health Checks

### Built-in Health Checks

```python
from zenoo_rpc.monitoring import health

# Check connection health
health_status = await health.check_connection(client)

# Check cache health
cache_status = await health.check_cache(client.cache)
```

### Custom Health Checks

```python
from zenoo_rpc.monitoring import health

@health.register_check("custom_service")
async def check_custom_service():
    # Your health check logic
    return {"status": "healthy", "details": "Service is running"}
```

## Performance Monitoring

### Request Tracing

Enable request tracing to track individual requests:

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.monitoring import tracing

async with ZenooClient("localhost", enable_tracing=True) as client:
    # Requests are automatically traced
    with tracing.span("user_operation"):
        users = await client.model("res.users").search([])
```

### Performance Profiling

```python
from zenoo_rpc.monitoring import profiler

# Profile a specific operation
with profiler.profile("complex_operation"):
    # Your complex operation
    result = await complex_operation()
```

## Integration with External Systems

### Prometheus

```python
from zenoo_rpc.monitoring.exporters import PrometheusExporter

# Export metrics to Prometheus
exporter = PrometheusExporter(port=8000)
exporter.start()
```

### Grafana Dashboards

Pre-built Grafana dashboards are available for visualizing Zenoo RPC metrics.

### APM Integration

Zenoo RPC integrates with popular APM solutions:

- New Relic
- Datadog
- Elastic APM
- Jaeger

## Alerting

### Built-in Alerts

Configure alerts for common issues:

```python
from zenoo_rpc.monitoring import alerts

# Alert on high error rate
alerts.configure_error_rate_alert(threshold=0.05)

# Alert on slow responses
alerts.configure_latency_alert(threshold_ms=1000)
```

### Custom Alerts

```python
@alerts.register_alert("custom_condition")
async def check_custom_condition(metrics):
    if metrics.get("custom_metric") > threshold:
        return alerts.Alert(
            level="warning",
            message="Custom condition triggered"
        )
```

## Best Practices

1. **Monitor Key Metrics**: Focus on error rates, latency, and throughput
2. **Set Up Alerts**: Configure alerts for critical issues
3. **Use Structured Logging**: Include context in log messages
4. **Regular Health Checks**: Implement comprehensive health checks
5. **Performance Profiling**: Profile critical operations regularly

## Troubleshooting

Common monitoring issues and solutions:

### High Memory Usage

```python
# Monitor memory usage
from zenoo_rpc.monitoring import memory

memory_stats = memory.get_stats()
if memory_stats.usage > threshold:
    # Take action
    pass
```

### Connection Pool Exhaustion

```python
# Monitor connection pool
pool_stats = client.transport.pool.get_stats()
if pool_stats.active_connections > threshold:
    # Scale up or investigate
    pass
```

## See Also

- [Debugging Guide](debugging.md)
- [Performance Optimization](../tutorials/performance-optimization.md)
- [Production Deployment](../tutorials/production-deployment.md)
