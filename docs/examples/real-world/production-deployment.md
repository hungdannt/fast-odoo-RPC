# 🚀 Production Deployment Guide for Zenoo RPC AI Features

This guide provides comprehensive instructions for deploying Zenoo RPC's AI features in production environments, based on real-world Gemini API production patterns and best practices.

## 📋 Prerequisites

### System Requirements

```bash
# Minimum system requirements
CPU: 4+ cores
RAM: 8GB+ (16GB recommended)
Storage: 50GB+ SSD
Network: Stable internet connection with low latency

# Python requirements
Python 3.9+
pip 21.0+
```

### Dependencies Installation

```bash
# Production installation with AI features
pip install zenoo-rpc[ai]

# Additional production dependencies
pip install gunicorn uvicorn redis celery prometheus-client
```

## 🔐 Security Configuration

### API Key Management

```bash
# Environment variables for production
export GEMINI_API_KEY="your-production-gemini-key"
export GEMINI_API_KEY_FALLBACK="your-backup-gemini-key"
export OPENAI_API_KEY="your-openai-key"  # Optional fallback
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional fallback

# Database credentials
export ODOO_DB_HOST="your-odoo-host"
export ODOO_DB_NAME="production_db"
export ODOO_USERNAME="api_user"
export ODOO_PASSWORD="secure_password"

# Security settings
export AI_RATE_LIMIT="1000"  # Requests per hour
export AI_TIMEOUT="60"       # Seconds
export AI_MAX_RETRIES="5"
```

### Secure Configuration File

```python
# config/production.py
import os
from typing import Dict, Any

class ProductionConfig:
    """Production configuration for Zenoo RPC AI features."""
    
    # Odoo Configuration
    ODOO_URL = os.getenv("ODOO_URL", "https://your-odoo-instance.com")
    ODOO_DATABASE = os.getenv("ODOO_DB_NAME")
    ODOO_USERNAME = os.getenv("ODOO_USERNAME")
    ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")
    
    # AI Configuration
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
    AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")
    AI_API_KEY = os.getenv("GEMINI_API_KEY")
    AI_FALLBACK_KEY = os.getenv("GEMINI_API_KEY_FALLBACK")
    
    # Performance Settings
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.1"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4096"))
    AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "60.0"))
    AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "5"))
    
    # Rate Limiting
    AI_RATE_LIMIT = int(os.getenv("AI_RATE_LIMIT", "1000"))
    AI_RATE_WINDOW = int(os.getenv("AI_RATE_WINDOW", "3600"))  # 1 hour
    
    # Monitoring
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT = int(os.getenv("METRICS_PORT", "8000"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate production configuration."""
        required_vars = [
            "ODOO_URL", "ODOO_DB_NAME", "ODOO_USERNAME", 
            "ODOO_PASSWORD", "GEMINI_API_KEY"
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var.replace("ODOO_", "").replace("GEMINI_", "AI_"))]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        
        return True
```

## 🏗️ Production Architecture

### High-Availability Setup

```python
# production_app.py
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from zenoo_rpc import ZenooClient
from config.production import ProductionConfig

class ProductionAIService:
    """Production-ready AI service with high availability."""
    
    def __init__(self):
        self.config = ProductionConfig()
        self.config.validate()
        self.primary_client: Optional[ZenooClient] = None
        self.fallback_client: Optional[ZenooClient] = None
        self.health_status = {"primary": False, "fallback": False}
    
    async def initialize(self):
        """Initialize primary and fallback clients."""
        
        # Primary client
        self.primary_client = ZenooClient(self.config.ODOO_URL)
        await self.primary_client.login(
            self.config.ODOO_DATABASE,
            self.config.ODOO_USERNAME,
            self.config.ODOO_PASSWORD
        )
        
        await self.primary_client.setup_ai(
            provider=self.config.AI_PROVIDER,
            model=self.config.AI_MODEL,
            api_key=self.config.AI_API_KEY,
            temperature=self.config.AI_TEMPERATURE,
            max_tokens=self.config.AI_MAX_TOKENS,
            timeout=self.config.AI_TIMEOUT,
            max_retries=self.config.AI_MAX_RETRIES
        )
        
        self.health_status["primary"] = True
        
        # Fallback client (if fallback key available)
        if self.config.AI_FALLBACK_KEY:
            self.fallback_client = ZenooClient(self.config.ODOO_URL)
            await self.fallback_client.login(
                self.config.ODOO_DATABASE,
                self.config.ODOO_USERNAME,
                self.config.ODOO_PASSWORD
            )
            
            await self.fallback_client.setup_ai(
                provider=self.config.AI_PROVIDER,
                model=self.config.AI_MODEL,
                api_key=self.config.AI_FALLBACK_KEY,
                temperature=self.config.AI_TEMPERATURE,
                max_tokens=self.config.AI_MAX_TOKENS,
                timeout=self.config.AI_TIMEOUT,
                max_retries=self.config.AI_MAX_RETRIES
            )
            
            self.health_status["fallback"] = True
    
    @asynccontextmanager
    async def get_client(self):
        """Get available client with automatic failover."""
        
        if self.health_status["primary"]:
            try:
                yield self.primary_client
                return
            except Exception as e:
                logging.error(f"Primary client failed: {e}")
                self.health_status["primary"] = False
        
        if self.health_status["fallback"] and self.fallback_client:
            try:
                yield self.fallback_client
                return
            except Exception as e:
                logging.error(f"Fallback client failed: {e}")
                self.health_status["fallback"] = False
        
        raise RuntimeError("No available AI clients")
    
    async def health_check(self) -> dict:
        """Perform health check on all clients."""
        
        health = {"status": "healthy", "clients": {}}
        
        # Check primary client
        try:
            if self.primary_client:
                response = await self.primary_client.ai.chat("Health check", max_tokens=5)
                health["clients"]["primary"] = "healthy"
                self.health_status["primary"] = True
        except Exception as e:
            health["clients"]["primary"] = f"unhealthy: {e}"
            self.health_status["primary"] = False
        
        # Check fallback client
        try:
            if self.fallback_client:
                response = await self.fallback_client.ai.chat("Health check", max_tokens=5)
                health["clients"]["fallback"] = "healthy"
                self.health_status["fallback"] = True
        except Exception as e:
            health["clients"]["fallback"] = f"unhealthy: {e}"
            self.health_status["fallback"] = False
        
        # Overall status
        if not any(self.health_status.values()):
            health["status"] = "critical"
        elif not self.health_status["primary"]:
            health["status"] = "degraded"
        
        return health

# Global service instance
ai_service = ProductionAIService()
```

## 📊 Monitoring and Observability

### Metrics Collection

```python
# monitoring/metrics.py
import time
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps

# Metrics definitions
ai_requests_total = Counter(
    'zenoo_ai_requests_total',
    'Total AI requests',
    ['provider', 'model', 'operation', 'status']
)

ai_request_duration = Histogram(
    'zenoo_ai_request_duration_seconds',
    'AI request duration',
    ['provider', 'model', 'operation']
)

ai_token_usage = Counter(
    'zenoo_ai_tokens_total',
    'Total AI tokens used',
    ['provider', 'model', 'type']
)

ai_errors_total = Counter(
    'zenoo_ai_errors_total',
    'Total AI errors',
    ['provider', 'model', 'error_type']
)

active_connections = Gauge(
    'zenoo_active_connections',
    'Active Odoo connections'
)

def monitor_ai_operation(operation_name: str):
    """Decorator to monitor AI operations."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success metrics
                duration = time.time() - start_time
                ai_requests_total.labels(
                    provider='gemini',
                    model='gemini-2.5-flash-lite',
                    operation=operation_name,
                    status='success'
                ).inc()
                
                ai_request_duration.labels(
                    provider='gemini',
                    model='gemini-2.5-flash-lite',
                    operation=operation_name
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # Record error metrics
                ai_requests_total.labels(
                    provider='gemini',
                    model='gemini-2.5-flash-lite',
                    operation=operation_name,
                    status='error'
                ).inc()
                
                ai_errors_total.labels(
                    provider='gemini',
                    model='gemini-2.5-flash-lite',
                    error_type=type(e).__name__
                ).inc()
                
                raise
        
        return wrapper
    return decorator

def start_metrics_server(port: int = 8000):
    """Start Prometheus metrics server."""
    start_http_server(port)
    logging.info(f"Metrics server started on port {port}")
```

### Logging Configuration

```python
# logging_config.py
import logging
import logging.handlers
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_production_logging():
    """Setup production logging configuration."""
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/zenoo_ai.log',
        maxBytes=100*1024*1024,  # 100MB
        backupCount=10
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/zenoo_ai_errors.log',
        maxBytes=50*1024*1024,  # 50MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
```

## 🔄 Rate Limiting and Circuit Breaker

```python
# resilience/rate_limiter.py
import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional

class RateLimiter:
    """Token bucket rate limiter for AI API calls."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    async def acquire(self, key: str = "default") -> bool:
        """Acquire permission to make a request."""
        
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove old requests
        while self.requests[key] and self.requests[key][0] < window_start:
            self.requests[key].popleft()
        
        # Check if we can make a request
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        
        return False

class CircuitBreaker:
    """Circuit breaker for AI API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Reset on success
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise
```

## 🚀 Deployment Scripts

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')"

# Run application
CMD ["python", "production_app.py"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  zenoo-ai:
    build: .
    ports:
      - "8000:8000"  # Application
      - "8001:8001"  # Health check
      - "8002:8002"  # Metrics
    environment:
      - ODOO_URL=${ODOO_URL}
      - ODOO_DB_NAME=${ODOO_DB_NAME}
      - ODOO_USERNAME=${ODOO_USERNAME}
      - ODOO_PASSWORD=${ODOO_PASSWORD}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_API_KEY_FALLBACK=${GEMINI_API_KEY_FALLBACK}
      - LOG_LEVEL=INFO
      - ENABLE_METRICS=true
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

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
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

volumes:
  redis_data:
  prometheus_data:
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zenoo-ai
  labels:
    app: zenoo-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: zenoo-ai
  template:
    metadata:
      labels:
        app: zenoo-ai
    spec:
      containers:
      - name: zenoo-ai
        image: zenoo-ai:latest
        ports:
        - containerPort: 8000
        - containerPort: 8001
        - containerPort: 8002
        env:
        - name: ODOO_URL
          valueFrom:
            secretKeyRef:
              name: zenoo-secrets
              key: odoo-url
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: zenoo-secrets
              key: gemini-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: zenoo-ai-service
spec:
  selector:
    app: zenoo-ai
  ports:
  - name: app
    port: 8000
    targetPort: 8000
  - name: health
    port: 8001
    targetPort: 8001
  - name: metrics
    port: 8002
    targetPort: 8002
```

## 📈 Performance Optimization

### Caching Strategy

```python
# caching/ai_cache.py
import json
import hashlib
from typing import Optional, Any
import redis

class AIResponseCache:
    """Redis-based cache for AI responses."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.default_ttl = 3600  # 1 hour
    
    def _generate_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate cache key from request parameters."""
        
        key_data = {
            'prompt': prompt,
            'model': model,
            'temperature': temperature
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return f"ai_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def get(self, prompt: str, model: str, temperature: float) -> Optional[str]:
        """Get cached response."""
        
        key = self._generate_key(prompt, model, temperature)
        cached_response = self.redis_client.get(key)
        
        if cached_response:
            return cached_response.decode('utf-8')
        
        return None
    
    async def set(self, prompt: str, model: str, temperature: float, 
                  response: str, ttl: Optional[int] = None) -> None:
        """Cache AI response."""
        
        key = self._generate_key(prompt, model, temperature)
        cache_ttl = ttl or self.default_ttl
        
        self.redis_client.setex(key, cache_ttl, response)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        
        keys = self.redis_client.keys(f"ai_cache:*{pattern}*")
        if keys:
            return self.redis_client.delete(*keys)
        return 0
```

## 🔍 Troubleshooting

### Common Issues and Solutions

```python
# troubleshooting/diagnostics.py
import asyncio
import logging
from typing import Dict, List

class ProductionDiagnostics:
    """Production diagnostics and troubleshooting."""
    
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive diagnostics."""
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Check AI API connectivity
        results['checks']['ai_connectivity'] = await self._check_ai_connectivity()
        
        # Check Odoo connectivity
        results['checks']['odoo_connectivity'] = await self._check_odoo_connectivity()
        
        # Check system resources
        results['checks']['system_resources'] = await self._check_system_resources()
        
        # Check rate limits
        results['checks']['rate_limits'] = await self._check_rate_limits()
        
        return results
    
    async def _check_ai_connectivity(self) -> Dict[str, Any]:
        """Check AI API connectivity."""
        
        try:
            # Test Gemini API
            async with ai_service.get_client() as client:
                response = await client.ai.chat("Test", max_tokens=5)
                return {
                    'status': 'healthy',
                    'response_time': 0.5,  # Would measure actual time
                    'provider': 'gemini'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'provider': 'gemini'
            }
    
    async def _check_odoo_connectivity(self) -> Dict[str, Any]:
        """Check Odoo connectivity."""
        
        try:
            async with ai_service.get_client() as client:
                # Test basic Odoo operation
                result = await client.search('res.users', [], limit=1)
                return {
                    'status': 'healthy',
                    'response_time': 0.2,  # Would measure actual time
                    'records_found': len(result)
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg()
        }
    
    async def _check_rate_limits(self) -> Dict[str, Any]:
        """Check rate limit status."""
        
        # This would check actual rate limit usage
        return {
            'requests_remaining': 950,  # Example
            'reset_time': '2024-01-01T12:00:00Z',
            'current_usage': '5%'
        }
```

## 📚 Best Practices Summary

### 1. **Security**
- Use environment variables for all secrets
- Implement API key rotation
- Enable request logging and monitoring
- Use HTTPS for all communications

### 2. **Reliability**
- Implement circuit breakers and retries
- Use multiple API keys for failover
- Monitor health endpoints
- Set up alerting for failures

### 3. **Performance**
- Cache AI responses when appropriate
- Use rate limiting to avoid API limits
- Monitor response times and optimize
- Scale horizontally with load balancers

### 4. **Monitoring**
- Collect comprehensive metrics
- Set up alerting for critical issues
- Use structured logging
- Monitor costs and usage

### 5. **Deployment**
- Use containerization for consistency
- Implement blue-green deployments
- Automate testing and validation
- Have rollback procedures ready

---

**🎯 This production deployment guide ensures your Zenoo RPC AI features run reliably, securely, and efficiently in production environments!**
