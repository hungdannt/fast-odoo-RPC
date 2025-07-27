# Production Deployment

This tutorial covers best practices for deploying Zenoo RPC applications in production environments, including configuration, monitoring, security, and scalability considerations.

## Prerequisites

- Understanding of [Configuration](../user-guide/configuration.md)
- Knowledge of [Error Handling](../user-guide/error-handling.md)
- Familiarity with containerization and orchestration

## Production Configuration

### Environment-Based Configuration

```python
# config/production.py
import os
from zenoo_rpc import ZenooClient

class ProductionConfig:
    """Production configuration for Zenoo RPC."""
    
    # Odoo Connection
    ODOO_HOST = os.getenv("ODOO_HOST", "odoo.company.com")
    ODOO_PORT = int(os.getenv("ODOO_PORT", "443"))
    ODOO_PROTOCOL = os.getenv("ODOO_PROTOCOL", "https")
    ODOO_DATABASE = os.getenv("ODOO_DATABASE")
    ODOO_USERNAME = os.getenv("ODOO_USERNAME")
    ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")
    
    # Connection Settings
    CONNECTION_TIMEOUT = float(os.getenv("CONNECTION_TIMEOUT", "30.0"))
    MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "100"))
    VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"
    
    # Cache Configuration
    CACHE_BACKEND = os.getenv("CACHE_BACKEND", "redis")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))
    
    # Retry Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    
    # Monitoring
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

async def create_production_client():
    """Create a production-ready Zenoo RPC client."""
    config = ProductionConfig()
    
    client = ZenooClient(
        host_or_url=config.ODOO_HOST,
        port=config.ODOO_PORT,
        protocol=config.ODOO_PROTOCOL,
        timeout=config.CONNECTION_TIMEOUT,
        verify_ssl=config.VERIFY_SSL
    )
    
    # Setup cache manager
    if config.CACHE_BACKEND == "redis":
        await client.cache_manager.setup_redis_cache(
            name="production_cache",
            url=config.REDIS_URL,
            namespace="zenoo_rpc",
            strategy="ttl",
            enable_fallback=True,
            circuit_breaker_threshold=config.CIRCUIT_BREAKER_THRESHOLD
        )
    else:
        await client.cache_manager.setup_memory_cache(
            name="production_cache",
            max_size=1000,
            strategy="ttl"
        )
    
    # Setup batch manager
    from zenoo_rpc.batch.manager import BatchManager
    client.batch_manager = BatchManager(
        client=client,
        max_chunk_size=100,
        max_concurrency=10,
        timeout=300
    )
    
    # Setup transaction manager
    from zenoo_rpc.transaction.manager import TransactionManager
    client.transaction_manager = TransactionManager(client)
    
    return client
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from health_check import check_health; asyncio.run(check_health())"

# Default command
CMD ["python", "-m", "app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    environment:
      - ODOO_HOST=odoo.company.com
      - ODOO_PORT=443
      - ODOO_PROTOCOL=https
      - ODOO_DATABASE=${ODOO_DATABASE}
      - ODOO_USERNAME=${ODOO_USERNAME}
      - ODOO_PASSWORD=${ODOO_PASSWORD}
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=INFO
      - ENABLE_METRICS=true
    depends_on:
      - redis
    ports:
      - "8000:8000"
      - "9090:9090"  # Metrics port
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

volumes:
  redis_data:
  prometheus_data:
```

## Application Structure

### Production Application Layout

```python
# app/__init__.py
"""Production Zenoo RPC application."""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import Optional

from .config import ProductionConfig, create_production_client
from .monitoring import setup_monitoring
from .health import HealthChecker

class ZenooRPCApplication:
    """Production Zenoo RPC application."""
    
    def __init__(self):
        self.client: Optional[ZenooClient] = None
        self.config = ProductionConfig()
        self.health_checker: Optional[HealthChecker] = None
        self._shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Application startup."""
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create client
        self.client = await create_production_client()
        
        # Authenticate
        await self.client.login(
            self.config.ODOO_DATABASE,
            self.config.ODOO_USERNAME,
            self.config.ODOO_PASSWORD
        )
        
        # Setup monitoring
        if self.config.ENABLE_METRICS:
            await setup_monitoring(self.client, self.config.METRICS_PORT)
        
        # Setup health checker
        self.health_checker = HealthChecker(self.client)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logging.info("Application started successfully")
    
    async def shutdown(self):
        """Application shutdown."""
        logging.info("Shutting down application...")
        
        if self.client:
            await self.client.close()
        
        logging.info("Application shutdown complete")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logging.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_event.set()
    
    async def run(self):
        """Run the application."""
        await self.startup()
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        finally:
            await self.shutdown()

# app/main.py
async def main():
    """Main application entry point."""
    app = ZenooRPCApplication()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Health Checks

```python
# app/health.py
import asyncio
import time
from typing import Dict, Any
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError

class HealthChecker:
    """Health check implementation for Zenoo RPC."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Check database connection
        try:
            start_time = time.time()
            await self.client.search_count("res.users", [])
            response_time = (time.time() - start_time) * 1000
            
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": response_time
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check cache connection
        if hasattr(self.client, 'cache_manager'):
            try:
                await self.client.cache_manager.set("health_check", "ok", ttl=10)
                value = await self.client.cache_manager.get("health_check")
                
                health_status["checks"]["cache"] = {
                    "status": "healthy" if value == "ok" else "degraded"
                }
            except Exception as e:
                health_status["checks"]["cache"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # Check memory usage
        import psutil
        memory_percent = psutil.virtual_memory().percent
        health_status["checks"]["memory"] = {
            "status": "healthy" if memory_percent < 80 else "warning",
            "usage_percent": memory_percent
        }
        
        return health_status
    
    async def liveness_probe(self) -> bool:
        """Simple liveness probe for Kubernetes."""
        try:
            return self.client.is_authenticated
        except Exception:
            return False
    
    async def readiness_probe(self) -> bool:
        """Readiness probe for Kubernetes."""
        try:
            health = await self.check_health()
            return health["status"] in ["healthy", "warning"]
        except Exception:
            return False

# Health check endpoint for HTTP servers
async def check_health() -> Dict[str, Any]:
    """Standalone health check function."""
    # This would be called by your HTTP framework
    # Implementation depends on your specific setup
    pass
```

## Monitoring and Observability

### Metrics Collection

```python
# app/monitoring.py
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from zenoo_rpc import ZenooClient

# Prometheus metrics
REQUEST_COUNT = Counter(
    'zenoo_rpc_requests_total',
    'Total number of RPC requests',
    ['method', 'model', 'status']
)

REQUEST_DURATION = Histogram(
    'zenoo_rpc_request_duration_seconds',
    'RPC request duration in seconds',
    ['method', 'model']
)

CACHE_HITS = Counter(
    'zenoo_rpc_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'zenoo_rpc_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

ACTIVE_CONNECTIONS = Gauge(
    'zenoo_rpc_active_connections',
    'Number of active connections'
)

class MetricsCollector:
    """Collect and expose metrics for Zenoo RPC."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        
    async def record_request(self, method: str, model: str, duration: float, status: str):
        """Record request metrics."""
        REQUEST_COUNT.labels(method=method, model=model, status=status).inc()
        REQUEST_DURATION.labels(method=method, model=model).observe(duration)
    
    async def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        CACHE_HITS.labels(cache_type=cache_type).inc()
    
    async def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        CACHE_MISSES.labels(cache_type=cache_type).inc()
    
    async def update_connection_count(self, count: int):
        """Update active connection count."""
        ACTIVE_CONNECTIONS.set(count)

async def setup_monitoring(client: ZenooClient, port: int = 9090):
    """Setup monitoring and metrics collection."""
    # Start Prometheus metrics server
    start_http_server(port)
    
    # Initialize metrics collector
    metrics_collector = MetricsCollector(client)
    
    # Monkey patch client methods to collect metrics
    original_execute_kw = client.execute_kw
    
    async def instrumented_execute_kw(model, method, args, **kwargs):
        start_time = time.time()
        status = "success"
        
        try:
            result = await original_execute_kw(model, method, args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            await metrics_collector.record_request(method, model, duration, status)
    
    client.execute_kw = instrumented_execute_kw
    
    return metrics_collector
```

### Logging Configuration

```python
# app/logging_config.py
import logging
import logging.config
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process',
                          'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': JSONFormatter,
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/zenoo_rpc.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'zenoo_rpc': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'app': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    }
}

def setup_logging():
    """Setup logging configuration."""
    logging.config.dictConfig(LOGGING_CONFIG)
```

## Security Considerations

### SSL/TLS Configuration

```python
# app/security.py
import ssl
from zenoo_rpc import ZenooClient

def create_secure_client(host: str, cert_file: str = None, key_file: str = None):
    """Create a client with enhanced SSL configuration."""
    
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    # Configure minimum TLS version
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Configure cipher suites
    ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
    
    # Client certificate authentication if provided
    if cert_file and key_file:
        ssl_context.load_cert_chain(cert_file, key_file)
    
    client = ZenooClient(
        host_or_url=host,
        protocol="https",
        verify_ssl=True
    )
    
    return client

# Environment variable validation
def validate_environment():
    """Validate required environment variables."""
    import os
    
    required_vars = [
        'ODOO_HOST',
        'ODOO_DATABASE', 
        'ODOO_USERNAME',
        'ODOO_PASSWORD'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    # Validate password strength
    password = os.getenv('ODOO_PASSWORD')
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")
```

## Kubernetes Deployment

### Kubernetes Manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zenoo-rpc-app
  labels:
    app: zenoo-rpc-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: zenoo-rpc-app
  template:
    metadata:
      labels:
        app: zenoo-rpc-app
    spec:
      containers:
      - name: app
        image: zenoo-rpc-app:latest
        ports:
        - containerPort: 8000
        - containerPort: 9090
        env:
        - name: ODOO_HOST
          value: "odoo.company.com"
        - name: ODOO_DATABASE
          valueFrom:
            secretKeyRef:
              name: odoo-credentials
              key: database
        - name: ODOO_USERNAME
          valueFrom:
            secretKeyRef:
              name: odoo-credentials
              key: username
        - name: ODOO_PASSWORD
          valueFrom:
            secretKeyRef:
              name: odoo-credentials
              key: password
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: zenoo-rpc-service
spec:
  selector:
    app: zenoo-rpc-app
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
---
apiVersion: v1
kind: Secret
metadata:
  name: odoo-credentials
type: Opaque
data:
  database: <base64-encoded-database-name>
  username: <base64-encoded-username>
  password: <base64-encoded-password>
```

## Performance Optimization

### Connection Pooling

```python
# app/performance.py
import asyncio
from zenoo_rpc import ZenooClient

class ConnectionPool:
    """Connection pool for Zenoo RPC clients."""
    
    def __init__(self, host: str, max_connections: int = 10):
        self.host = host
        self.max_connections = max_connections
        self._pool = asyncio.Queue(maxsize=max_connections)
        self._created_connections = 0
    
    async def get_client(self) -> ZenooClient:
        """Get a client from the pool."""
        try:
            # Try to get existing client
            client = self._pool.get_nowait()
            if client.is_authenticated:
                return client
        except asyncio.QueueEmpty:
            pass
        
        # Create new client if pool is not full
        if self._created_connections < self.max_connections:
            client = await self._create_client()
            self._created_connections += 1
            return client
        
        # Wait for available client
        return await self._pool.get()
    
    async def return_client(self, client: ZenooClient):
        """Return a client to the pool."""
        if client.is_authenticated:
            await self._pool.put(client)
        else:
            # Replace disconnected client
            new_client = await self._create_client()
            await self._pool.put(new_client)
    
    async def _create_client(self) -> ZenooClient:
        """Create and authenticate a new client."""
        client = ZenooClient(self.host)
        await client.login("database", "username", "password")
        return client
    
    async def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            client = await self._pool.get()
            await client.close()

# Usage with context manager
class PooledClient:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.client = None
    
    async def __aenter__(self):
        self.client = await self.pool.get_client()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.pool.return_client(self.client)
```

## Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database connectivity tested
- [ ] Cache backend (Redis) available
- [ ] Monitoring systems configured
- [ ] Log aggregation setup
- [ ] Health check endpoints implemented
- [ ] Security scanning completed

### Deployment

- [ ] Blue-green deployment strategy
- [ ] Rolling updates configured
- [ ] Circuit breakers enabled
- [ ] Rate limiting implemented
- [ ] Load balancing configured
- [ ] Auto-scaling policies set

### Post-Deployment

- [ ] Health checks passing
- [ ] Metrics being collected
- [ ] Logs being aggregated
- [ ] Performance monitoring active
- [ ] Error tracking functional
- [ ] Backup procedures tested
- [ ] Disaster recovery plan validated

## Best Practices

### 1. Configuration Management

```python
# ✅ Good: Use environment variables
ODOO_HOST = os.getenv("ODOO_HOST")

# ❌ Avoid: Hardcoded values
ODOO_HOST = "production.odoo.com"
```

### 2. Error Handling

```python
# ✅ Good: Comprehensive error handling
try:
    result = await client.create("res.partner", data)
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    # Handle gracefully
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    # Implement fallback
```

### 3. Resource Management

```python
# ✅ Good: Use context managers
async with ZenooClient(host) as client:
    await client.login(db, user, password)
    # Operations here
# Client automatically closed
```

### 4. Monitoring

```python
# ✅ Good: Comprehensive monitoring
@metrics.timer('operation_duration')
async def business_operation():
    try:
        result = await client.operation()
        metrics.counter('operation_success').inc()
        return result
    except Exception as e:
        metrics.counter('operation_error').inc()
        raise
```

## Next Steps

- Learn about [Advanced Queries](advanced-queries.md) for optimizing production queries
- Explore [Performance Optimization](performance-optimization.md) for scaling strategies
- Check [Security Best Practices](../advanced/security.md) for enhanced security measures
