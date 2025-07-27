# Frequently Asked Questions (FAQ)

Common questions and answers about Zenoo RPC usage, troubleshooting, and best practices.

## General Questions

### Q: What is Zenoo RPC and how does it differ from odoorpc?

**A:** Zenoo RPC is a modern, async-first Python library for interacting with Odoo servers. Key differences from odoorpc:

- **Async/Await Support**: Built for modern async Python applications
- **Type Safety**: Full type hints and Pydantic model validation
- **Performance**: HTTP/2 support, connection pooling, intelligent caching
- **Developer Experience**: Fluent query API, IDE autocompletion
- **Enterprise Features**: Batch operations, retry mechanisms, circuit breakers

```python
# odoorpc (synchronous)
import odoorpc
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('demo', 'admin', 'admin')
partners = odoo.env['res.partner'].search_read([('is_company', '=', True)])

# Zenoo RPC (asynchronous, type-safe)
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    partners = await client.model(ResPartner).filter(is_company=True).all()
```

### Q: Is Zenoo RPC compatible with all Odoo versions?

**A:** Zenoo RPC is currently tested and verified with **Odoo 18.0 only**. While it uses standard JSON-RPC protocols that should be consistent across Odoo versions, compatibility with other versions is not yet verified:

- **Odoo 18.0**: ✅ Tested and supported (latest version)
- **Odoo 12.0-17.0**: ⚠️ Compatibility unknown (testing planned for v0.2.0)

We plan to add comprehensive version testing for older Odoo versions in upcoming releases.

### Q: Can I use Zenoo RPC in synchronous code?

**A:** Zenoo RPC is designed for async/await patterns, but you can use it in synchronous code with `asyncio.run()`:

```python
import asyncio
from zenoo_rpc import ZenooClient

def sync_function():
    """Use Zenoo RPC in synchronous code."""
    
    async def async_operation():
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            return await client.search("res.partner", [])
    
    # Run async code from sync function
    return asyncio.run(async_operation())

# Usage
partners = sync_function()
```

## Installation & Setup

### Q: How do I install Zenoo RPC with all optional dependencies?

**A:** Install with optional dependencies for full functionality:

```bash
# Basic installation
pip install zenoo-rpc

# With Redis support
pip install zenoo-rpc[redis]

# With development tools
pip install zenoo-rpc[dev]

# With all optional dependencies
pip install zenoo-rpc[redis,dev]

# From source (latest development version)
pip install git+https://github.com/tuanle96/zenoo-rpc.git
```

### Q: What are the minimum system requirements?

**A:** Zenoo RPC requirements:

- **Python**: 3.8 or later (3.11+ recommended for best performance)
- **Memory**: 64MB minimum (more for caching and batch operations)
- **Network**: HTTP/HTTPS access to Odoo server
- **Optional**: Redis server for distributed caching

### Q: How do I configure Zenoo RPC for production use?

**A:** Production configuration example:

```python
from zenoo_rpc import ZenooClient

# Production client configuration
async def create_production_client():
    client = ZenooClient(
        host="odoo.company.com",
        port=443,  # HTTPS
        use_ssl=True,
        verify_ssl=True,
        
        # Connection optimization
        max_connections=50,
        max_keepalive_connections=20,
        timeout=30.0,
        
        # Performance features
        http2=True,
        
        # Security headers
        headers={
            "User-Agent": "CompanyApp/1.0 (ZenooRPC)",
            "X-Forwarded-For": "10.0.0.1"
        }
    )
    
    # Setup caching
    await client.setup_cache_manager(
        backend="redis",
        url="redis://redis.company.com:6379/0",
        default_ttl=300,
        max_size=10000
    )
    
    # Setup batch processing
    await client.setup_batch_manager(
        max_chunk_size=100,
        max_concurrency=10
    )
    
    return client
```

## Authentication & Security

### Q: How do I handle authentication errors?

**A:** Common authentication issues and solutions:

```python
from zenoo_rpc.exceptions import AuthenticationError

async def handle_auth_errors():
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "wrong_password")
    
    except AuthenticationError as e:
        if "Access Denied" in str(e):
            print("Invalid username or password")
        elif "database" in str(e).lower():
            print("Database does not exist")
        else:
            print(f"Authentication failed: {e}")
            
        # Debug steps:
        # 1. Check available databases
        databases = await client.list_databases()
        print(f"Available databases: {databases}")
        
        # 2. Verify Odoo server is accessible
        version = await client.version()
        print(f"Odoo version: {version}")
```

### Q: How do I implement secure authentication in production?

**A:** Production authentication best practices:

```python
import os
from cryptography.fernet import Fernet

class SecureAuthManager:
    def __init__(self):
        # Use environment variables for credentials
        self.host = os.getenv("ODOO_HOST")
        self.database = os.getenv("ODOO_DATABASE")
        self.username = os.getenv("ODOO_USERNAME")
        
        # Encrypt stored passwords
        key = os.getenv("ENCRYPTION_KEY").encode()
        self.cipher = Fernet(key)
        encrypted_password = os.getenv("ODOO_PASSWORD_ENCRYPTED")
        self.password = self.cipher.decrypt(encrypted_password.encode()).decode()
    
    async def get_authenticated_client(self):
        client = ZenooClient(self.host, port=443, use_ssl=True)
        await client.login(self.database, self.username, self.password)
        return client

# Environment variables:
# ODOO_HOST=odoo.company.com
# ODOO_DATABASE=production
# ODOO_USERNAME=api_user
# ODOO_PASSWORD_ENCRYPTED=gAAAAABh...
# ENCRYPTION_KEY=your-encryption-key
```

### Q: How do I handle session timeouts?

**A:** Implement automatic session refresh:

```python
import time
from zenoo_rpc.exceptions import AuthenticationError

class SessionManager:
    def __init__(self, client, database, username, password):
        self.client = client
        self.database = database
        self.username = username
        self.password = password
        self.last_login = 0
        self.session_timeout = 3600  # 1 hour
    
    async def ensure_authenticated(self):
        """Ensure client is authenticated, refresh if needed."""
        current_time = time.time()
        
        if current_time - self.last_login > self.session_timeout:
            await self.refresh_session()
    
    async def refresh_session(self):
        """Refresh authentication session."""
        try:
            await self.client.login(self.database, self.username, self.password)
            self.last_login = time.time()
        except AuthenticationError:
            # Handle re-authentication failure
            raise
    
    async def call_with_retry(self, method, *args, **kwargs):
        """Call method with automatic session refresh on auth failure."""
        try:
            await self.ensure_authenticated()
            return await method(*args, **kwargs)
        except AuthenticationError:
            # Try refreshing session once
            await self.refresh_session()
            return await method(*args, **kwargs)
```

## Performance & Optimization

### Q: How can I improve query performance?

**A:** Performance optimization strategies:

```python
# ❌ Inefficient: N+1 queries
async def inefficient_queries():
    partner_ids = await client.search("res.partner", [], limit=100)
    partners = []
    for partner_id in partner_ids:
        partner = await client.read("res.partner", [partner_id])
        partners.append(partner[0])
    return partners

# ✅ Efficient: Single query
async def efficient_queries():
    return await client.search_read("res.partner", [], limit=100)

# ✅ Even better: With caching and field selection
async def optimized_queries():
    return await (
        client.model(ResPartner)
        .filter(active=True)
        .only("id", "name", "email")  # Select only needed fields
        .limit(100)
        .cache(ttl=300)  # Cache for 5 minutes
        .all()
    )
```

### Q: How do I optimize batch operations?

**A:** Batch operation optimization:

```python
# ✅ Optimal batch size (usually 50-200 records)
async def optimized_batch_create():
    large_dataset = [{"name": f"Partner {i}"} for i in range(1000)]
    
    async with client.batch_context(max_chunk_size=100) as batch:
        batch.create("res.partner", large_dataset)
        results = await batch.execute()
    
    return results

# ✅ Concurrent batch processing
async def concurrent_batches():
    datasets = [
        [{"name": f"Batch1-{i}"} for i in range(100)],
        [{"name": f"Batch2-{i}"} for i in range(100)],
        [{"name": f"Batch3-{i}"} for i in range(100)]
    ]
    
    tasks = []
    for dataset in datasets:
        task = create_batch(dataset)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results

async def create_batch(data):
    async with client.batch_context() as batch:
        batch.create("res.partner", data)
        return await batch.execute()
```

### Q: When should I use caching and what are the best practices?

**A:** Caching best practices:

```python
# ✅ Cache read-heavy, rarely changing data
async def cache_static_data():
    # Cache countries (rarely change)
    countries = await (
        client.model(ResCountry)
        .cache(ttl=3600)  # 1 hour
        .all()
    )
    
    # Cache user preferences (user-specific)
    user_prefs = await (
        client.model(ResUsers)
        .filter(id=client.uid)
        .cache(ttl=300, key_prefix=f"user_{client.uid}")
        .first()
    )

# ❌ Don't cache frequently changing data
async def avoid_caching():
    # Don't cache real-time data
    current_stock = await client.model(StockQuant).all()  # No cache
    
    # Don't cache user-specific data without proper keys
    my_orders = await client.model(SaleOrder).filter(
        user_id=client.uid
    ).all()  # No cache or use user-specific key

# ✅ Cache invalidation strategy
async def cache_with_invalidation():
    # Cache with tags for selective invalidation
    partners = await (
        client.model(ResPartner)
        .filter(is_company=True)
        .cache(ttl=600, tags=["partners", "companies"])
        .all()
    )
    
    # Invalidate cache when data changes
    await client.create("res.partner", {"name": "New Company"})
    await client.cache_manager.invalidate_tags(["partners", "companies"])
```

## Error Handling

### Q: How do I handle network timeouts and connection errors?

**A:** Robust error handling with retries:

```python
from zenoo_rpc.retry import async_retry, ExponentialBackoffStrategy
from zenoo_rpc.exceptions import NetworkError, TimeoutError

@async_retry(
    max_attempts=3,
    strategy=ExponentialBackoffStrategy(base_delay=1.0, multiplier=2.0)
)
async def robust_operation():
    """Operation with automatic retry on network errors."""
    try:
        return await client.search("res.partner", [])
    except (NetworkError, TimeoutError) as e:
        print(f"Network error, will retry: {e}")
        raise  # Re-raise to trigger retry
    except Exception as e:
        print(f"Non-retryable error: {e}")
        raise

# Manual retry with custom logic
async def manual_retry():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            return await client.search("res.partner", [])
        except (NetworkError, TimeoutError) as e:
            if attempt == max_attempts - 1:
                raise  # Last attempt, give up
            
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
```

### Q: How do I handle Odoo-specific errors (ValidationError, AccessError, etc.)?

**A:** Handle Odoo business logic errors:

```python
from zenoo_rpc.exceptions import ValidationError, AccessError, UserError

async def handle_odoo_errors():
    try:
        # This might fail due to validation rules
        partner = await client.create("res.partner", {
            "name": "",  # Empty name might be invalid
            "email": "invalid-email"  # Invalid email format
        })
    
    except ValidationError as e:
        print(f"Validation failed: {e}")
        # Handle validation errors (fix data and retry)
        
    except AccessError as e:
        print(f"Access denied: {e}")
        # Handle permission errors (check user rights)
        
    except UserError as e:
        print(f"Business rule violation: {e}")
        # Handle business logic errors
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Handle other errors

# Graceful error handling with fallbacks
async def create_partner_with_fallback(partner_data):
    """Create partner with graceful error handling."""
    try:
        return await client.create("res.partner", partner_data)
    
    except ValidationError as e:
        # Try with minimal required data
        minimal_data = {"name": partner_data.get("name", "Unknown")}
        return await client.create("res.partner", minimal_data)
    
    except AccessError:
        # Log the attempt and return None
        print(f"Access denied for partner creation: {partner_data}")
        return None
```

## Models & Data Types

### Q: How do I work with custom Odoo models?

**A:** Define custom models for type safety:

```python
from zenoo_rpc.models.base import OdooModel
from zenoo_rpc.models.fields import CharField, DateTimeField, Many2OneField
from typing import ClassVar, Optional
from datetime import datetime

class CustomModel(OdooModel):
    """Custom Odoo model definition."""
    
    _odoo_name: ClassVar[str] = "custom.model"
    
    # Define fields with proper types
    name: str = CharField(description="Model name")
    description: Optional[str] = CharField(description="Description")
    created_date: Optional[datetime] = DateTimeField(description="Creation date")
    partner_id: Optional[int] = Many2OneField("res.partner", description="Related partner")

# Usage with type safety
async def work_with_custom_model():
    # Type-safe queries
    records = await client.model(CustomModel).filter(
        name__ilike="test"
    ).all()
    
    # IDE autocompletion works
    for record in records:
        print(f"Name: {record.name}")
        print(f"Created: {record.created_date}")
        
        # Type checking catches errors
        # record.invalid_field  # This would be caught by type checker

# Dynamic model for unknown structures
async def work_with_dynamic_model():
    # Use generic model for unknown structures
    records = await client.search_read("unknown.model", [])
    
    # Access as dictionaries
    for record in records:
        print(f"ID: {record['id']}")
        print(f"Fields: {record.keys()}")
```

### Q: How do I handle Many2one and One2many relationships?

**A:** Relationship handling patterns:

```python
# Many2one relationships
async def work_with_many2one():
    # Get partner with country information
    partner = await (
        client.model(ResPartner)
        .filter(id=1)
        .prefetch_related("country_id")  # Avoid N+1 queries
        .first()
    )
    
    if partner.country_id:
        print(f"Country: {partner.country_id.name}")

# One2many relationships
async def work_with_one2many():
    # Get partner with all contacts
    company = await (
        client.model(ResPartner)
        .filter(id=1, is_company=True)
        .prefetch_related("child_ids")  # Load contacts
        .first()
    )
    
    for contact in company.child_ids:
        print(f"Contact: {contact.name}")

# Many2many relationships
async def work_with_many2many():
    # Get partner with categories
    partner = await (
        client.model(ResPartner)
        .filter(id=1)
        .prefetch_related("category_id")  # Load categories
        .first()
    )
    
    for category in partner.category_id:
        print(f"Category: {category.name}")

# Manual relationship loading
async def manual_relationship_loading():
    # Get partner
    partner = await client.model(ResPartner).filter(id=1).first()
    
    # Manually load country
    if partner.country_id:
        country = await client.model(ResCountry).filter(
            id=partner.country_id
        ).first()
        print(f"Country: {country.name}")
```

## Migration & Integration

### Q: How do I migrate from odoorpc to Zenoo RPC?

**A:** Migration guide with examples:

```python
# Before (odoorpc)
import odoorpc

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('demo', 'admin', 'admin')

# Search and read
partner_ids = odoo.env['res.partner'].search([('is_company', '=', True)])
partners = odoo.env['res.partner'].browse(partner_ids)

# Create
new_partner = odoo.env['res.partner'].create({
    'name': 'Test Company',
    'is_company': True
})

# After (Zenoo RPC)
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def migrated_code():
    async with ZenooClient('localhost', port=8069) as client:
        await client.login('demo', 'admin', 'admin')
        
        # Search and read (single query)
        partners = await client.model(ResPartner).filter(
            is_company=True
        ).all()
        
        # Create
        new_partner = await client.create('res.partner', {
            'name': 'Test Company',
            'is_company': True
        })

# Migration helper function
def migrate_odoorpc_code(odoorpc_function):
    """Helper to wrap odoorpc code for gradual migration."""
    
    async def async_wrapper(*args, **kwargs):
        # Convert sync odoorpc call to async Zenoo RPC
        # This is a simplified example
        result = await asyncio.get_event_loop().run_in_executor(
            None, odoorpc_function, *args, **kwargs
        )
        return result
    
    return async_wrapper
```

### Q: How do I integrate Zenoo RPC with web frameworks (FastAPI, Django, Flask)?

**A:** Web framework integration examples:

```python
# FastAPI integration
from fastapi import FastAPI, Depends
from zenoo_rpc import ZenooClient

app = FastAPI()

# Dependency for client
async def get_odoo_client():
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    try:
        yield client
    finally:
        await client.close()

@app.get("/partners")
async def get_partners(client: ZenooClient = Depends(get_odoo_client)):
    return await client.model(ResPartner).filter(is_company=True).all()

# Django integration (using async views in Django 4.1+)
from django.http import JsonResponse
from asgiref.sync import sync_to_async

class PartnerViewSet:
    def __init__(self):
        self.client = None
    
    async def get_client(self):
        if not self.client:
            self.client = ZenooClient("localhost", port=8069)
            await self.client.login("demo", "admin", "admin")
        return self.client
    
    async def list_partners(self, request):
        client = await self.get_client()
        partners = await client.model(ResPartner).filter(is_company=True).all()
        return JsonResponse({"partners": [p.dict() for p in partners]})

# Flask integration (using asyncio)
from flask import Flask, jsonify
import asyncio

app = Flask(__name__)

@app.route('/partners')
def get_partners():
    async def async_get_partners():
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            return await client.model(ResPartner).filter(is_company=True).all()
    
    partners = asyncio.run(async_get_partners())
    return jsonify([p.dict() for p in partners])
```

## Best Practices

### Q: What are the recommended patterns for production applications?

**A:** Production-ready patterns:

```python
# 1. Connection management
class OdooService:
    def __init__(self):
        self.client = None
        self._lock = asyncio.Lock()
    
    async def get_client(self):
        async with self._lock:
            if not self.client:
                self.client = ZenooClient("localhost", port=8069)
                await self.client.login("demo", "admin", "admin")
                
                # Setup production features
                await self.client.setup_cache_manager(backend="redis")
                await self.client.setup_batch_manager()
        
        return self.client
    
    async def close(self):
        if self.client:
            await self.client.close()

# 2. Error handling and logging
import logging

logger = logging.getLogger(__name__)

async def robust_operation(service: OdooService):
    try:
        client = await service.get_client()
        result = await client.search("res.partner", [])
        logger.info(f"Successfully retrieved {len(result)} partners")
        return result
    
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        # Handle error appropriately
        raise

# 3. Configuration management
from dataclasses import dataclass
import os

@dataclass
class OdooConfig:
    host: str = os.getenv("ODOO_HOST", "localhost")
    port: int = int(os.getenv("ODOO_PORT", "8069"))
    database: str = os.getenv("ODOO_DATABASE", "demo")
    username: str = os.getenv("ODOO_USERNAME", "admin")
    password: str = os.getenv("ODOO_PASSWORD", "admin")
    use_ssl: bool = os.getenv("ODOO_SSL", "false").lower() == "true"
    
    # Performance settings
    max_connections: int = int(os.getenv("ODOO_MAX_CONNECTIONS", "20"))
    timeout: float = float(os.getenv("ODOO_TIMEOUT", "30.0"))
    
    # Cache settings
    cache_backend: str = os.getenv("CACHE_BACKEND", "memory")
    cache_url: str = os.getenv("CACHE_URL", "redis://localhost:6379/0")
    cache_ttl: int = int(os.getenv("CACHE_TTL", "300"))

async def create_configured_client(config: OdooConfig):
    client = ZenooClient(
        host=config.host,
        port=config.port,
        use_ssl=config.use_ssl,
        max_connections=config.max_connections,
        timeout=config.timeout
    )
    
    await client.login(config.database, config.username, config.password)
    
    if config.cache_backend == "redis":
        await client.setup_cache_manager(
            backend="redis",
            url=config.cache_url,
            default_ttl=config.cache_ttl
        )
    
    return client
```

### Q: How do I monitor and debug production issues?

**A:** Production monitoring and debugging:

```python
# 1. Metrics collection
import time
from collections import defaultdict

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
    
    def record_operation(self, operation: str, duration: float, success: bool):
        self.metrics[f"{operation}_duration"].append(duration)
        self.counters[f"{operation}_total"] += 1
        if success:
            self.counters[f"{operation}_success"] += 1
        else:
            self.counters[f"{operation}_error"] += 1
    
    def get_stats(self):
        stats = {}
        for operation, durations in self.metrics.items():
            if durations:
                stats[operation] = {
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "count": len(durations)
                }
        
        stats.update(dict(self.counters))
        return stats

# 2. Health checks
async def health_check(client: ZenooClient) -> dict:
    """Comprehensive health check."""
    health = {"status": "healthy", "checks": {}}
    
    try:
        # Test basic connectivity
        start = time.time()
        version = await client.version()
        health["checks"]["connectivity"] = {
            "status": "ok",
            "response_time": time.time() - start,
            "version": version
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["connectivity"] = {
            "status": "error",
            "error": str(e)
        }
    
    try:
        # Test authentication
        start = time.time()
        await client.call("common", "authenticate", 
                         client.database, client.username, client.password, {})
        health["checks"]["authentication"] = {
            "status": "ok",
            "response_time": time.time() - start
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["authentication"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test cache if available
    if hasattr(client, 'cache_manager') and client.cache_manager:
        try:
            await client.cache_manager.set("health_check", "ok", ttl=10)
            cached = await client.cache_manager.get("health_check")
            health["checks"]["cache"] = {
                "status": "ok" if cached == "ok" else "error"
            }
        except Exception as e:
            health["checks"]["cache"] = {
                "status": "error",
                "error": str(e)
            }
    
    return health

# 3. Alerting
async def check_and_alert():
    """Monitor system and send alerts."""
    health = await health_check(client)
    
    if health["status"] != "healthy":
        # Send alert (email, Slack, etc.)
        await send_alert(f"Odoo health check failed: {health}")
    
    # Check performance metrics
    stats = metrics_collector.get_stats()
    avg_response_time = stats.get("search_duration", {}).get("avg", 0)
    
    if avg_response_time > 5.0:  # 5 second threshold
        await send_alert(f"High response time detected: {avg_response_time:.2f}s")
```

## Next Steps

For more detailed information, check out:

- [Debugging Guide](debugging.md) for detailed troubleshooting techniques
- [API Reference](../api-reference/index.md) for complete API documentation
- [Performance Guide](../advanced/performance.md) for optimization strategies
- [Security Guide](../advanced/security.md) for production security
- [Examples](../examples/index.md) for practical usage examples
