# Configuration

Zenoo RPC provides extensive configuration options to customize behavior, optimize performance, and integrate with your application architecture. This guide covers all configuration aspects from basic setup to advanced tuning.

## Basic Configuration

### Client Configuration

```python
from zenoo_rpc import ZenooClient

# Basic configuration with direct parameters
client = ZenooClient(
    host_or_url="localhost",
    port=8069,
    protocol="http",  # or "https"
    timeout=30.0,
    verify_ssl=True
)

# Alternative: Full URL
client = ZenooClient("https://myodoo.company.com")

# Alternative: Host with protocol
client = ZenooClient(
    "localhost",
    port=8069,
    protocol="https",
    timeout=60.0
)
```

### Environment-Based Configuration

```python
import os
from zenoo_rpc import ZenooClient

# Load configuration from environment variables
host = os.getenv("ZENOO_HOST", "localhost")
port = int(os.getenv("ZENOO_PORT", "8069"))
protocol = os.getenv("ZENOO_PROTOCOL", "http")
timeout = float(os.getenv("ZENOO_TIMEOUT", "30.0"))

# Environment variables:
# ZENOO_HOST=localhost
# ZENOO_PORT=8069
# ZENOO_PROTOCOL=https
# ZENOO_TIMEOUT=30

client = ZenooClient(
    host_or_url=host,
    port=port,
    protocol=protocol,
    timeout=timeout
)
```

### Configuration Files

```python
from zenoo_rpc.config import load_config_from_file

# Load from YAML file
config = load_config_from_file("zenoo_config.yaml")

# Load from JSON file
config = load_config_from_file("zenoo_config.json")

client = ZenooClient(config=config)
```

Example YAML configuration:

```yaml
# zenoo_config.yaml
server:
  host: "production-odoo.company.com"
  port: 443
  protocol: "https"
  timeout: 60.0

connection:
  max_retries: 5
  retry_delay: 2.0
  connection_pool_size: 20
  keep_alive: true

cache:
  backend: "redis"
  url: "redis://localhost:6379/0"
  default_ttl: 300
  max_memory: "100MB"

batch:
  max_chunk_size: 100
  max_concurrent_chunks: 5
  enable_progress_tracking: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Connection Configuration

### HTTP Transport Settings

```python
from zenoo_rpc.config import HTTPTransportConfig

transport_config = HTTPTransportConfig(
    timeout=30.0,
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=5.0,
    http2=True,  # Enable HTTP/2
    verify_ssl=True,
    ssl_cert_path="/path/to/cert.pem",
    ssl_key_path="/path/to/key.pem"
)

client = ZenooClient(
    host="secure-odoo.company.com",
    transport_config=transport_config
)
```

### Connection Pooling

```python
from zenoo_rpc.config import ConnectionPoolConfig

pool_config = ConnectionPoolConfig(
    max_pool_size=50,
    min_pool_size=5,
    max_overflow=10,
    pool_timeout=30.0,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True  # Validate connections before use
)

await client.setup_connection_pool(pool_config)
```

### Authentication Configuration

```python
from zenoo_rpc.config import AuthConfig

# Basic authentication
auth_config = AuthConfig(
    database="production_db",
    username="api_user",
    password="secure_password"
)

# API key authentication (if supported)
auth_config = AuthConfig(
    database="production_db",
    api_key="your-api-key-here"
)

# OAuth2 authentication
auth_config = AuthConfig(
    database="production_db",
    oauth2_token="oauth2-token",
    oauth2_refresh_token="refresh-token"
)

await client.authenticate(auth_config)
```

## Performance Configuration

### Cache Configuration

```python
from zenoo_rpc.config import CacheConfig

# Memory cache configuration
memory_cache_config = CacheConfig(
    backend="memory",
    max_size=1000,  # Maximum number of cached items
    default_ttl=300,  # Default TTL in seconds
    cleanup_interval=60  # Cleanup expired items every 60 seconds
)

# Redis cache configuration
redis_cache_config = CacheConfig(
    backend="redis",
    url="redis://localhost:6379/0",
    password="redis_password",
    max_connections=20,
    default_ttl=600,
    key_prefix="zenoo:",
    serializer="pickle"  # or "json", "msgpack"
)

# Multi-level cache configuration
multilevel_cache_config = CacheConfig(
    backend="multilevel",
    levels=[
        {"backend": "memory", "max_size": 100, "ttl": 60},
        {"backend": "redis", "url": "redis://localhost:6379/0", "ttl": 3600}
    ]
)

await client.setup_cache_manager(redis_cache_config)
```

### Batch Operation Configuration

```python
from zenoo_rpc.config import BatchConfig

batch_config = BatchConfig(
    max_chunk_size=200,  # Records per chunk
    max_concurrent_chunks=10,  # Concurrent processing
    chunk_timeout=30.0,  # Timeout per chunk
    enable_progress_tracking=True,
    progress_callback=custom_progress_callback,
    error_handling="continue",  # "stop" or "continue"
    retry_failed_chunks=True,
    max_chunk_retries=3
)

await client.setup_batch_manager(batch_config)
```

### Query Optimization Configuration

```python
from zenoo_rpc.config import QueryConfig

query_config = QueryConfig(
    default_limit=1000,  # Default query limit
    max_limit=10000,  # Maximum allowed limit
    enable_query_cache=True,
    query_cache_ttl=300,
    prefetch_batch_size=50,
    lazy_loading=True,
    optimize_joins=True
)

client.set_query_config(query_config)
```

## Retry and Resilience Configuration

### Retry Configuration

```python
from zenoo_rpc.config import RetryConfig
from zenoo_rpc.retry import ExponentialBackoff

retry_config = RetryConfig(
    strategy=ExponentialBackoff(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True
    ),
    retry_on_exceptions=[
        "NetworkError",
        "TimeoutError",
        "ServerError"
    ],
    circuit_breaker=True,
    circuit_breaker_threshold=10,
    circuit_breaker_timeout=60.0
)

await client.setup_retry_manager(retry_config)
```

### Circuit Breaker Configuration

```python
from zenoo_rpc.config import CircuitBreakerConfig

circuit_breaker_config = CircuitBreakerConfig(
    failure_threshold=5,  # Open after 5 failures
    recovery_timeout=30.0,  # Try recovery after 30 seconds
    half_open_max_calls=3,  # Test with 3 calls in half-open
    success_threshold=2,  # Need 2 successes to close
    expected_exceptions=[
        "NetworkError",
        "TimeoutError"
    ]
)

await client.setup_circuit_breaker(circuit_breaker_config)
```

## Logging Configuration

### Basic Logging Setup

```python
from zenoo_rpc.config import LoggingConfig
import logging

logging_config = LoggingConfig(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        {
            "type": "console",
            "level": "INFO"
        },
        {
            "type": "file",
            "filename": "zenoo_rpc.log",
            "level": "DEBUG",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5
        }
    ]
)

client.setup_logging(logging_config)
```

### Structured Logging

```python
from zenoo_rpc.config import StructuredLoggingConfig

structured_logging_config = StructuredLoggingConfig(
    format="json",
    include_context=True,
    include_performance_metrics=True,
    sensitive_fields=["password", "api_key"],  # Fields to mask
    correlation_id_header="X-Correlation-ID"
)

client.setup_structured_logging(structured_logging_config)
```

## Security Configuration

### SSL/TLS Configuration

```python
from zenoo_rpc.config import SSLConfig

ssl_config = SSLConfig(
    verify_ssl=True,
    ca_cert_path="/path/to/ca-cert.pem",
    client_cert_path="/path/to/client-cert.pem",
    client_key_path="/path/to/client-key.pem",
    ssl_version="TLSv1_2",  # Minimum TLS version
    ciphers="HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA"
)

client = ZenooClient(
    host="secure-odoo.company.com",
    port=443,
    protocol="https",
    ssl_config=ssl_config
)
```

### API Security Configuration

```python
from zenoo_rpc.config import SecurityConfig

security_config = SecurityConfig(
    api_key_header="X-API-Key",
    rate_limiting=True,
    max_requests_per_minute=1000,
    request_signing=True,
    signing_algorithm="HMAC-SHA256",
    signing_secret="your-signing-secret",
    encrypt_sensitive_data=True,
    encryption_key="your-encryption-key"
)

client.setup_security(security_config)
```

## Monitoring Configuration

### Metrics Configuration

```python
from zenoo_rpc.config import MetricsConfig

metrics_config = MetricsConfig(
    enabled=True,
    backend="prometheus",  # or "statsd", "datadog"
    endpoint="http://prometheus:9090",
    namespace="zenoo_rpc",
    labels={
        "service": "my-service",
        "environment": "production"
    },
    collect_query_metrics=True,
    collect_cache_metrics=True,
    collect_retry_metrics=True
)

client.setup_metrics(metrics_config)
```

### Health Check Configuration

```python
from zenoo_rpc.config import HealthCheckConfig

health_config = HealthCheckConfig(
    enabled=True,
    endpoint="/health",
    port=8080,
    checks=[
        "database_connection",
        "cache_connection",
        "memory_usage",
        "response_time"
    ],
    thresholds={
        "response_time_ms": 1000,
        "memory_usage_percent": 80,
        "cache_hit_rate_percent": 70
    }
)

client.setup_health_checks(health_config)
```

## Environment-Specific Configuration

### Development Configuration

```python
from zenoo_rpc.config import DevelopmentConfig

dev_config = DevelopmentConfig(
    debug=True,
    log_level="DEBUG",
    enable_query_logging=True,
    enable_performance_profiling=True,
    mock_external_services=True,
    auto_reload=True
)

client = ZenooClient(config=dev_config)
```

### Production Configuration

```python
from zenoo_rpc.config import ProductionConfig

prod_config = ProductionConfig(
    debug=False,
    log_level="WARNING",
    enable_metrics=True,
    enable_health_checks=True,
    connection_pool_size=100,
    cache_backend="redis",
    retry_enabled=True,
    circuit_breaker_enabled=True
)

client = ZenooClient(config=prod_config)
```

### Testing Configuration

```python
from zenoo_rpc.config import TestingConfig

test_config = TestingConfig(
    use_test_database=True,
    mock_external_calls=True,
    disable_cache=True,
    fast_retries=True,  # Shorter delays for testing
    enable_test_fixtures=True
)

client = ZenooClient(config=test_config)
```

## Configuration Validation

### Schema Validation

```python
from zenoo_rpc.config import ConfigValidator

# Validate configuration before use
validator = ConfigValidator()

try:
    validated_config = validator.validate(config)
    client = ZenooClient(config=validated_config)
    
except ConfigValidationError as e:
    print(f"Configuration validation failed: {e}")
    for error in e.errors:
        print(f"  {error.field}: {error.message}")
```

### Runtime Configuration Updates

```python
# Update configuration at runtime
await client.update_config({
    "cache.default_ttl": 600,
    "batch.max_chunk_size": 150,
    "retry.max_attempts": 3
})

# Get current configuration
current_config = client.get_config()
print(f"Current cache TTL: {current_config.cache.default_ttl}")
```

## Configuration Best Practices

### 1. Use Environment-Specific Configurations

```python
# Good: Separate configs for different environments
if os.getenv("ENVIRONMENT") == "production":
    config = load_config_from_file("prod_config.yaml")
elif os.getenv("ENVIRONMENT") == "staging":
    config = load_config_from_file("staging_config.yaml")
else:
    config = load_config_from_file("dev_config.yaml")
```

### 2. Secure Sensitive Configuration

```python
# Good: Use environment variables for secrets
config = ClientConfig(
    host=os.getenv("ODOO_HOST"),
    username=os.getenv("ODOO_USERNAME"),
    password=os.getenv("ODOO_PASSWORD"),  # From environment
    api_key=os.getenv("ODOO_API_KEY")     # From environment
)

# Avoid: Hardcoding secrets
config = ClientConfig(
    username="admin",
    password="hardcoded_password"  # Never do this!
)
```

### 3. Validate Configuration Early

```python
# Good: Validate configuration at startup
try:
    config = load_config_from_file("config.yaml")
    validator = ConfigValidator()
    validated_config = validator.validate(config)
    client = ZenooClient(config=validated_config)
    
except ConfigValidationError as e:
    logger.error(f"Invalid configuration: {e}")
    sys.exit(1)
```

### 4. Monitor Configuration Changes

```python
# Good: Log configuration changes
def on_config_change(old_config, new_config):
    changes = compare_configs(old_config, new_config)
    logger.info(f"Configuration updated: {changes}")

client.set_config_change_callback(on_config_change)
```

### 5. Use Configuration Profiles

```python
# Good: Use profiles for different scenarios
profiles = {
    "high_performance": {
        "connection_pool_size": 100,
        "cache_backend": "redis",
        "batch_max_chunk_size": 500
    },
    "low_latency": {
        "timeout": 5.0,
        "max_retries": 1,
        "cache_backend": "memory"
    },
    "reliable": {
        "max_retries": 10,
        "circuit_breaker_enabled": True,
        "retry_exponential_backoff": True
    }
}

# Apply profile
config = apply_profile(base_config, profiles["high_performance"])
```

## Next Steps

- Learn about [Performance Optimization](../tutorials/performance-optimization.md) for performance tuning
- Explore [Production Deployment](../tutorials/production-deployment.md) for production configuration
- Check [Security Best Practices](../advanced/security.md) for security configuration
