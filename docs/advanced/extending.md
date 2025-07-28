# Extending Zenoo RPC

Learn how to extend Zenoo RPC with custom models, transports, and functionality.

## Custom Models

### Creating Custom Model Classes

```python
from zenoo_rpc.models.base import OdooModel
from zenoo_rpc.models.fields import CharField, IntegerField, BooleanField

class CustomPartner(OdooModel):
    """Custom partner model with additional functionality."""
    
    class Meta:
        model_name = "res.partner"
    
    # Custom fields
    custom_field = CharField(max_length=100)
    priority = IntegerField(default=1)
    is_vip = BooleanField(default=False)
    
    async def get_orders(self):
        """Get all orders for this partner."""
        return await self.client.model("sale.order").filter(
            partner_id=self.id
        ).all()
    
    async def mark_as_vip(self):
        """Mark partner as VIP."""
        await self.update(is_vip=True, priority=10)
```

### Model Registry

```python
from zenoo_rpc.models.registry import register_model

# Register custom model
register_model("res.partner", CustomPartner)

# Use in client
async with ZenooClient("localhost") as client:
    await client.login("demo", "admin", "admin")
    
    # Will use CustomPartner class
    partner = await client.model("res.partner").create(
        name="VIP Customer",
        is_vip=True
    )
    
    # Custom methods available
    orders = await partner.get_orders()
```

## Custom Transports

### HTTP Transport Extension

```python
from zenoo_rpc.transport.http import HTTPTransport
import aiohttp

class CustomHTTPTransport(HTTPTransport):
    """Custom HTTP transport with additional features."""
    
    async def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_headers = {}
    
    def add_custom_header(self, key: str, value: str):
        """Add custom header to all requests."""
        self.custom_headers[key] = value
    
    async def _make_request(self, method: str, url: str, **kwargs):
        """Override to add custom headers."""
        headers = kwargs.get("headers", {})
        headers.update(self.custom_headers)
        kwargs["headers"] = headers
        
        return await super()._make_request(method, url, **kwargs)
```

### WebSocket Transport

```python
import asyncio
import websockets
from zenoo_rpc.transport.base import BaseTransport

class WebSocketTransport(BaseTransport):
    """WebSocket transport for real-time communication."""
    
    def __init__(self, url: str):
        self.url = url
        self.websocket = None
        self.message_queue = asyncio.Queue()
    
    async def connect(self):
        """Connect to WebSocket server."""
        self.websocket = await websockets.connect(self.url)
        asyncio.create_task(self._message_listener())
    
    async def _message_listener(self):
        """Listen for incoming messages."""
        async for message in self.websocket:
            await self.message_queue.put(message)
    
    async def send_request(self, data: dict) -> dict:
        """Send request via WebSocket."""
        await self.websocket.send(json.dumps(data))
        response = await self.message_queue.get()
        return json.loads(response)
```

## Custom Cache Backends

### Redis Cluster Backend

```python
from zenoo_rpc.cache.backends import CacheBackend
import aioredis

class RedisClusterBackend(CacheBackend):
    """Redis Cluster cache backend."""
    
    def __init__(self, nodes: list, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes
        self.cluster = None
    
    async def connect(self):
        """Connect to Redis cluster."""
        self.cluster = aioredis.RedisCluster(
            startup_nodes=self.nodes,
            decode_responses=True
        )
    
    async def get(self, key: str) -> Any:
        """Get value from cluster."""
        data = await self.cluster.get(key)
        return self._deserialize(data) if data else None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cluster."""
        data = self._serialize(value)
        await self.cluster.set(key, data, ex=ttl)
```

## Custom Retry Strategies

### Custom Backoff Strategy

```python
from zenoo_rpc.retry.strategies import RetryStrategy
import math

class SinusoidalBackoffStrategy(RetryStrategy):
    """Sinusoidal backoff strategy."""
    
    def __init__(self, base_delay: float = 1.0, amplitude: float = 2.0):
        super().__init__()
        self.base_delay = base_delay
        self.amplitude = amplitude
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay using sinusoidal function."""
        delay = self.base_delay + self.amplitude * math.sin(attempt)
        return max(0.1, delay)  # Minimum 0.1 seconds
```

## Plugin System

### Creating Plugins

```python
from zenoo_rpc.plugins.base import Plugin

class AuditPlugin(Plugin):
    """Plugin for auditing all operations."""
    
    def __init__(self):
        self.audit_log = []
    
    async def before_request(self, method: str, params: dict):
        """Called before each request."""
        self.audit_log.append({
            "timestamp": datetime.now(),
            "method": method,
            "params": params,
            "type": "request"
        })
    
    async def after_response(self, method: str, response: dict):
        """Called after each response."""
        self.audit_log.append({
            "timestamp": datetime.now(),
            "method": method,
            "response": response,
            "type": "response"
        })
    
    def get_audit_log(self) -> list:
        """Get audit log."""
        return self.audit_log.copy()

# Register plugin
client.register_plugin(AuditPlugin())
```

## Middleware System

### Request/Response Middleware

```python
from zenoo_rpc.middleware.base import Middleware

class LoggingMiddleware(Middleware):
    """Middleware for request/response logging."""
    
    async def process_request(self, request: dict) -> dict:
        """Process outgoing request."""
        logger.info(f"Outgoing request: {request['method']}")
        return request
    
    async def process_response(self, response: dict) -> dict:
        """Process incoming response."""
        logger.info(f"Incoming response: {response.get('result', 'error')}")
        return response

# Add middleware
client.add_middleware(LoggingMiddleware())
```

## Event System

### Custom Event Handlers

```python
from zenoo_rpc.events import EventHandler

class CustomEventHandler(EventHandler):
    """Custom event handler."""
    
    async def on_connection_established(self, client):
        """Called when connection is established."""
        print(f"Connected to {client.host}")
    
    async def on_error(self, error: Exception):
        """Called when error occurs."""
        print(f"Error occurred: {error}")
    
    async def on_cache_hit(self, key: str, value: Any):
        """Called on cache hit."""
        print(f"Cache hit: {key}")

# Register event handler
client.register_event_handler(CustomEventHandler())
```

## Configuration Extensions

### Custom Configuration Providers

```python
from zenoo_rpc.config.base import ConfigProvider

class DatabaseConfigProvider(ConfigProvider):
    """Load configuration from database."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def load_config(self) -> dict:
        """Load configuration from database."""
        query = "SELECT key, value FROM config WHERE active = true"
        rows = await self.db.fetch(query)
        
        return {row["key"]: row["value"] for row in rows}

# Use custom config provider
config_provider = DatabaseConfigProvider(db_connection)
client = ZenooClient.from_config_provider(config_provider)
```

## Testing Extensions

### Custom Test Fixtures

```python
import pytest
from zenoo_rpc.testing import MockClient

@pytest.fixture
async def mock_client():
    """Create mock client for testing."""
    client = MockClient()
    
    # Setup mock responses
    client.mock_response("res.partner", "search_read", [
        {"id": 1, "name": "Test Partner"}
    ])
    
    yield client
    await client.close()

# Use in tests
async def test_custom_functionality(mock_client):
    partners = await mock_client.model("res.partner").all()
    assert len(partners) == 1
    assert partners[0].name == "Test Partner"
```

## Performance Extensions

### Custom Performance Monitors

```python
from zenoo_rpc.performance.monitors import PerformanceMonitor
import time

class CustomPerformanceMonitor(PerformanceMonitor):
    """Custom performance monitoring."""
    
    def __init__(self):
        self.metrics = {}
    
    async def start_operation(self, operation: str):
        """Start timing operation."""
        self.metrics[operation] = {
            "start_time": time.time(),
            "count": self.metrics.get(operation, {}).get("count", 0) + 1
        }
    
    async def end_operation(self, operation: str):
        """End timing operation."""
        if operation in self.metrics:
            duration = time.time() - self.metrics[operation]["start_time"]
            self.metrics[operation]["total_time"] = (
                self.metrics[operation].get("total_time", 0) + duration
            )
    
    def get_metrics(self) -> dict:
        """Get performance metrics."""
        return self.metrics.copy()
```

## Next Steps

- [Architecture Overview](architecture.md) - Understand the internal design
- [Performance Considerations](performance.md) - Optimize your extensions
- [Contributing Guide](../contributing/index.md) - Contribute your extensions
