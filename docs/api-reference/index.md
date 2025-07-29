# API Reference

Complete API reference for Zenoo RPC, including all classes, methods, and configuration options. This documentation is generated from the source code and provides detailed information about every public interface.

## Overview

The Zenoo RPC API is organized into several main modules:

- **[Client](client.md)**: Core client functionality and connection management
- **[Models](models/index.md)**: Data models and ORM-like functionality
- **[Query](query/index.md)**: Query building and filtering capabilities
- **[Cache](cache/index.md)**: Caching system and backends
- **[Transaction](transaction/index.md)**: Transaction management and ACID compliance
- **[Batch](batch/index.md)**: Bulk operations and batch processing
- **[Retry](retry/index.md)**: Retry mechanisms and resilience patterns
- **[Exceptions](exceptions/index.md)**: Exception hierarchy and error handling

## Quick Reference

### Core Classes

| Class | Module | Description |
|-------|--------|-------------|
| `ZenooClient` | `zenoo_rpc` | Main client for Odoo RPC operations |
| `QueryBuilder` | `zenoo_rpc.query.builder` | Fluent query building interface |
| `QuerySet` | `zenoo_rpc.query.builder` | Query execution and result handling |
| `BatchManager` | `zenoo_rpc.batch.manager` | Bulk operations management |
| `TransactionManager` | `zenoo_rpc.transaction.manager` | Transaction context management |
| `CacheManager` | `zenoo_rpc.cache.manager` | Cache backend management |

### Common Imports

```python
# Core functionality
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, ResCountry, ResUsers

# Query building
from zenoo_rpc.query.filters import Q
from zenoo_rpc.query.builder import QueryBuilder

# Batch operations
from zenoo_rpc.batch.manager import BatchManager

# Transactions
from zenoo_rpc.transaction.manager import TransactionManager

# Exceptions
from zenoo_rpc.exceptions import (
    ZenooError,
    ValidationError,
    AuthenticationError,
    ConnectionError,
    RequestTimeoutError
)

# Retry mechanisms
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy
from zenoo_rpc.retry.policies import DefaultRetryPolicy
from zenoo_rpc.retry.decorators import async_retry
```

### Basic Usage Pattern

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def main():
    # Create and configure client
    async with ZenooClient("localhost", port=8069) as client:
        # Authenticate
        await client.login("database", "username", "password")
        
        # Setup cache (optional)
        await client.setup_cache_manager(
            backend="memory",
            max_size=1000,
            ttl=300
        )
        
        # Use query builder
        partners = await client.model(ResPartner).filter(
            is_company=True
        ).limit(10).all()
        
        # Direct CRUD operations
        partner_id = await client.create("res.partner", {
            "name": "Test Company",
            "email": "test@company.com",
            "is_company": True
        })
        
        # Batch operations (optional)
        await client.setup_batch_manager()

        async with client.batch() as batch:
            created_ids = await batch.create_many(ResPartner, [
                {"name": "Company 1", "email": "c1@test.com"},
                {"name": "Company 2", "email": "c2@test.com"}
            ])

asyncio.run(main())
```

## API Conventions

### Async/Await Pattern

All Zenoo RPC operations are asynchronous and must be awaited:

```python
# ✅ Correct
partners = await client.search("res.partner", [], limit=10)

# ❌ Incorrect
partners = client.search("res.partner", [])  # Returns coroutine, not data
```

### Context Managers

Use context managers for proper resource management:

```python
# ✅ Correct - Automatic cleanup
async with ZenooClient("localhost") as client:
    await client.login("db", "user", "pass")
    # Operations here

# ✅ Also correct - Manual management
client = ZenooClient("localhost")
try:
    await client.__aenter__()
    await client.login("db", "user", "pass")
    # Operations here
finally:
    await client.__aexit__(None, None, None)
```

### Error Handling

Always handle specific exceptions:

```python
from zenoo_rpc.exceptions import ValidationError, AuthenticationError

try:
    await client.login("db", "user", "wrong_password")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ValidationError as e:
    print(f"Validation error: {e}")
```

### Method Chaining

Query builder supports method chaining:

```python
# Chain multiple operations using search with domain
partners = await client.search_read(
    "res.partner",
    domain=[("is_company", "=", True), ("active", "=", True)],
    fields=["name", "email", "phone"],
    limit=50,
    offset=100,
    order="name"
)
```

## Type Hints

Zenoo RPC provides comprehensive type hints for better IDE support:

```python
from typing import List, Optional
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def get_companies(client: ZenooClient) -> List[dict]:
    """Get all company partners with proper type hints."""
    companies = await client.search_read(
        "res.partner",
        domain=[("is_company", "=", True)],
        fields=["name", "email", "phone"]
    )
    return companies

async def find_partner_by_email(
    client: ZenooClient,
    email: str
) -> Optional[dict]:
    """Find partner by email with optional return type."""
    partners = await client.search_read(
        "res.partner",
        domain=[("email", "=", email)],
        fields=["name", "email", "phone"],
        limit=1
    )
    return partners[0] if partners else None
```

## Configuration Options

### Client Configuration

```python
# Basic configuration
client = ZenooClient(
    host_or_url="localhost",
    port=8069,
    protocol="http",
    timeout=30.0,
    verify_ssl=True
)

# URL-based configuration
client = ZenooClient("https://demo.odoo.com")

# Advanced configuration
client = ZenooClient(
    "localhost",
    port=8069,
    timeout=60.0,
    verify_ssl=False  # For development only
)
```

### Cache Configuration

```python
# Setup memory cache (recommended)
cache_manager = await client.setup_cache_manager(
    backend="memory",
    max_size=1000,
    ttl=300
)

# Setup Redis cache
cache_manager = await client.setup_cache_manager(
    backend="redis",
    url="redis://localhost:6379/0",
    enable_fallback=True,
    max_size=1000,
    ttl=300
)

# Manual cache manager setup
if client.cache_manager:
    await client.cache_manager.setup_redis_cache(
        name="redis",
        url="redis://localhost:6379/0",
        namespace="zenoo_rpc",
        enable_fallback=True
    )
```

### Batch Configuration

```python
# Setup batch manager (recommended)
batch_manager = await client.setup_batch_manager(
    max_chunk_size=100,
    max_concurrency=5,
    timeout=300
)

# Manual batch manager setup
from zenoo_rpc.batch.manager import BatchManager

batch_manager = BatchManager(
    client=client,
    max_chunk_size=100,
    max_concurrency=5,
    timeout=300
)
```

### Transaction Configuration

```python
# Transaction manager setup
from zenoo_rpc.transaction.manager import TransactionManager

transaction_manager = TransactionManager(client)

# Usage
async with transaction_manager.transaction() as tx:
    # All operations in this block are transactional
    partner_id = await client.create("res.partner", data)
    await client.write("res.partner", [partner_id], updates)
```

## Performance Considerations

### Connection Pooling

```python
# Reuse client instances when possible
class ServiceClass:
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def operation1(self):
        return await self.client.search("res.partner", [])
    
    async def operation2(self):
        return await self.client.search("res.users", [])
```

### Caching Strategy

```python
# Setup cache manager first
await client.setup_cache_manager(backend="memory", max_size=1000, ttl=300)

# Cache frequently accessed data manually
cache_key = "all_countries"
countries = await client.cache_manager.get(cache_key)
if not countries:
    countries = await client.search_read("res.country", [], fields=["name", "code"])
    await client.cache_manager.set(cache_key, countries, ttl=3600)

# Cache expensive queries
cache_key = "company_count"
partner_count = await client.cache_manager.get(cache_key)
if partner_count is None:
    partner_count = await client.search_count("res.partner", [("is_company", "=", True)])
    await client.cache_manager.set(cache_key, partner_count, ttl=300)
```

### Batch Operations

```python
# Setup batch manager
await client.setup_batch_manager(max_chunk_size=100, max_concurrency=5)

# Use batch operations for bulk data
async with client.batch() as batch:
    # Bulk create
    created_ids = await batch.create_many("res.partner", [
        {"name": "Company 1", "is_company": True},
        {"name": "Company 2", "is_company": True}
    ])

    # Bulk update
    await batch.write_many("res.partner", [
        {"id": 1, "values": {"active": True}},
        {"id": 2, "values": {"active": True}}
    ])

# Alternative: Direct bulk operations
batch_manager = await client.setup_batch_manager()
created_ids = await batch_manager.bulk_create(
    model="res.partner",
    records=large_dataset,
    chunk_size=100
)
```

## Debugging and Logging

### Enable Debug Logging

```python
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("zenoo_rpc")
logger.setLevel(logging.DEBUG)

# Now all Zenoo RPC operations will be logged
```

### Custom Logging

```python
import logging
from zenoo_rpc import ZenooClient

logger = logging.getLogger(__name__)

async def logged_operation():
    async with ZenooClient("localhost") as client:
        logger.info("Connecting to Odoo")
        await client.login("demo", "admin", "admin")
        
        logger.info("Searching for partners")
        partners = await client.search("res.partner", [], limit=100)

        logger.info(f"Found {len(partners)} partners")
```

## Migration Guide

### From odoorpc

```python
# Old odoorpc code
import odoorpc

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('demo', 'admin', 'admin')
partners = odoo.env['res.partner'].search_read(
    [('is_company', '=', True)],
    ['name', 'email']
)

# New Zenoo RPC code
import asyncio
from zenoo_rpc import ZenooClient

async def main():
    async with ZenooClient('localhost', port=8069) as client:
        await client.login('demo', 'admin', 'admin')
        partners = await client.search_read(
            'res.partner',
            domain=[('is_company', '=', True)],
            fields=['name', 'email']
        )

asyncio.run(main())
```

## Version Compatibility

| Zenoo RPC Version | Python Version | Odoo Version |
|-------------------|----------------|--------------|
| 1.0.x | 3.8+ | 13.0+ |
| 1.1.x | 3.9+ | 14.0+ |
| 1.2.x | 3.10+ | 15.0+ |
| 2.0.x | 3.11+ | 16.0+ |

## Next Steps

- Explore detailed [Client API](client.md) documentation
- Learn about [Model Operations](models/index.md)
- Check [Query Building](query/index.md) capabilities
- Understand [Error Handling](exceptions/index.md) patterns
