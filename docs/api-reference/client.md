# ZenooClient API Reference

The `ZenooClient` is the main entry point for all Odoo RPC operations. It provides a modern, async-first interface with comprehensive features for production use.

## Class Definition

```python
class ZenooClient:
    """Main async client for Zenoo-RPC.
    
    This is the primary interface for interacting with Odoo servers. It provides
    a zen-like, modern async API with type safety, intelligent caching, and
    superior developer experience.
    """
```

## Constructor

### `ZenooClient(host_or_url, port=None, protocol=None, timeout=30.0, verify_ssl=True)`

Create a new Zenoo RPC client instance.

**Parameters:**

- `host_or_url` (str): Odoo server host or full URL
  - Host format: `"localhost"`, `"demo.odoo.com"`
  - URL format: `"https://demo.odoo.com"`, `"http://localhost:8069"`
- `port` (int, optional): Port number (default: 80 for HTTP, 443 for HTTPS)
- `protocol` (str, optional): Protocol ("http" or "https", auto-detected from URL)
- `timeout` (float): Request timeout in seconds (default: 30.0)
- `verify_ssl` (bool): Whether to verify SSL certificates (default: True)

**Examples:**

```python
# Host with parameters
client = ZenooClient("localhost", port=8069, protocol="http")

# Full URL
client = ZenooClient("https://demo.odoo.com")

# Custom timeout and SSL settings
client = ZenooClient(
    "myodoo.com",
    port=443,
    protocol="https",
    timeout=60.0,
    verify_ssl=True
)
```

## Authentication Methods

### `async login(database, username, password)`

Authenticate with the Odoo server.

**Parameters:**

- `database` (str): Database name
- `username` (str): Username
- `password` (str): Password

**Returns:** `None` - Raises exception if authentication fails

**Raises:**
- `AuthenticationError`: If authentication fails
- `ConnectionError`: If connection to server fails

**Example:**

```python
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    print("Authentication successful")
    # Check authentication status
    if client.is_authenticated:
        print(f"Logged in as {client.username}")
```

### Session Management

The client automatically manages sessions. Use the context manager for proper cleanup:

**Example:**

```python
async with ZenooClient("localhost") as client:
    await client.login("demo", "admin", "admin")
    # Session automatically cleaned up on exit
```

## Properties

### `is_authenticated`

Check if client is currently authenticated.

**Type:** `bool`

**Example:**

```python
if client.is_authenticated:
    partners = await client.model(ResPartner).all()
else:
    await client.login("demo", "admin", "admin")
```

### `host`

Get the server hostname.

**Type:** `str`

### `port`

Get the server port.

**Type:** `int`

### `protocol`

Get the connection protocol.

**Type:** `str`

### `database`

Get the current database name (after authentication).

**Type:** `Optional[str]`

### `username`

Get the current username (after authentication).

**Type:** `Optional[str]`

### `uid`

Get the current user ID (after authentication).

**Type:** `Optional[int]`

**Example:**

```python
client = ZenooClient("demo.odoo.com", port=443, protocol="https")
await client.login("demo", "admin", "admin")
print(f"Database: {client.database}")
print(f"User: {client.username} (ID: {client.uid})")
```

## Core CRUD Operations

### `async create(model, values, context=None, validate_required=True)`

Create a new record.

**Parameters:**

- `model` (str): Odoo model name (e.g., "res.partner")
- `values` (dict): Record data
- `context` (dict, optional): Execution context
- `validate_required` (bool): Whether to validate required fields (default: True)

**Returns:** `int` - ID of created record

**Raises:**
- `ValidationError`: If data validation fails
- `AccessError`: If user lacks create permissions
- `AuthenticationError`: If not authenticated

**Example:**

```python
partner_id = await client.create("res.partner", {
    "name": "ACME Corporation",
    "email": "contact@acme.com",
    "is_company": True
})
```

### `async read(model, ids, fields=None, context=None)`

Read records by IDs.

**Parameters:**

- `model` (str): Odoo model name
- `ids` (list[int]): List of record IDs
- `fields` (list[str], optional): Fields to read (default: all)
- `context` (dict, optional): Execution context

**Returns:** `list[dict]` - List of record data

**Example:**

```python
# Read all fields
records = await client.read("res.partner", [1, 2, 3])

# Read specific fields
records = await client.read(
    "res.partner", 
    [1, 2, 3], 
    fields=["name", "email", "phone"]
)
```

### `async write(model, ids, values, context=None, check_access=True)`

Update existing records.

**Parameters:**

- `model` (str): Odoo model name
- `ids` (list[int]): List of record IDs to update
- `values` (dict): Update data
- `context` (dict, optional): Execution context
- `check_access` (bool): Whether to check record access (default: True)

**Returns:** `bool` - True if update successful

**Raises:**
- `ValidationError`: If data validation fails
- `AccessError`: If user lacks write permissions
- `AuthenticationError`: If not authenticated

**Example:**

```python
success = await client.write("res.partner", [1, 2], {
    "active": True,
    "customer_rank": 1
})
```

### `async unlink(model, ids, context=None)`

Delete records.

**Parameters:**

- `model` (str): Odoo model name
- `ids` (list[int]): List of record IDs to delete
- `context` (dict, optional): Execution context

**Returns:** `bool` - True if deletion successful

**Example:**

```python
success = await client.unlink("res.partner", [1, 2, 3])
```

## Search Operations

### Using Query Builder (Recommended)

For type-safe searches, use the query builder:

```python
from zenoo_rpc.models.common import ResPartner

# Type-safe search with query builder
companies = await client.model(ResPartner).filter(
    is_company=True
).limit(10).all()

# Get IDs only
company_ids = [partner.id for partner in companies]
```

### Low-Level Search (Advanced)

For direct Odoo API access, use `search_read()` which is available:

### `async search_read(model, domain, fields=None, limit=None, offset=0, order=None, context=None)`

Search and read records in one operation.

**Parameters:**

- `model` (str): Odoo model name
- `domain` (list): Search domain (list of tuples)
- `fields` (list[str], optional): Fields to read (None for all fields)
- `limit` (int, optional): Maximum number of records to return
- `offset` (int): Number of records to skip (default: 0)
- `order` (str, optional): Sort order specification
- `context` (dict, optional): Execution context

**Returns:** `list[dict]` - List of record dictionaries

**Example:**

```python
partners = await client.search_read(
    "res.partner",
    domain=[("is_company", "=", True)],
    fields=["name", "email", "phone"],
    limit=50,
    order="name"
)
```

### `async search_count(model, domain, context=None)`

Count records matching domain.

**Parameters:**

- `model` (str): Odoo model name
- `domain` (list): Search domain (list of tuples)
- `context` (dict, optional): Execution context

**Returns:** `int` - Number of matching records

**Raises:**
- `AuthenticationError`: If not authenticated
- `ZenooError`: If the server returns an error

**Example:**

```python
company_count = await client.search_count("res.partner", [
    ("is_company", "=", True)
])
```

## Model Query Builder

### `model(model_class)`

Get a query builder for a model class.

**Parameters:**

- `model_class` (Type[OdooModel]): Model class

**Returns:** `QueryBuilder` - Query builder instance

**Example:**

```python
from zenoo_rpc.models.common import ResPartner

# Get query builder
partners_query = client.model(ResPartner)

# Chain operations
companies = await partners_query.filter(
    is_company=True
).order_by("name").limit(10).all()
```

## Low-Level Operations

### `async execute_kw(model, method, args, kwargs=None, context=None)`

Execute arbitrary model method.

**Parameters:**

- `model` (str): Odoo model name
- `method` (str): Method name
- `args` (list): Positional arguments
- `kwargs` (dict, optional): Keyword arguments
- `context` (dict, optional): Execution context

**Returns:** `Any` - Method result

**Example:**

```python
# Call custom model method
result = await client.execute_kw(
    "res.partner",
    "custom_method",
    [arg1, arg2],
    {"param": "value"}
)
```

### Server Information

Get server information using available methods:

```python
# Get server version
version = await client.get_server_version()

# List available databases
databases = await client.list_databases()

# Check server health
health = await client.health_check()
```

## Context Managers

### `async __aenter__()` / `async __aexit__()`

Async context manager support for automatic resource cleanup.

**Example:**

```python
# Automatic cleanup
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    # Operations here
# Client automatically closed

# Manual management
client = ZenooClient("localhost", port=8069)
try:
    await client.__aenter__()
    await client.login("demo", "admin", "admin")
    # Operations here
finally:
    await client.__aexit__(None, None, None)
```

## Manager Properties

### `cache_manager`

Access to cache management functionality.

**Type:** `CacheManager`

**Example:**

```python
# Setup memory cache
await client.cache_manager.setup_memory_cache(
    name="default",
    max_size=1000,
    strategy="ttl"
)

# Setup Redis cache
await client.cache_manager.setup_redis_cache(
    name="redis",
    url="redis://localhost:6379/0"
)
```

### `batch_manager`

Access to batch operations (when configured).

**Type:** `BatchManager` (optional)

**Example:**

```python
from zenoo_rpc.batch.manager import BatchManager

# Setup batch manager
client.batch_manager = BatchManager(client=client)

# Use batch operations
async with client.batch_manager.batch() as batch_context:
    created_ids = await client.batch_manager.bulk_create(
        model="res.partner",
        records=[{"name": "Company 1"}, {"name": "Company 2"}]
    )
```

### `transaction_manager`

Access to transaction management (when configured).

**Type:** `TransactionManager` (optional)

**Example:**

```python
from zenoo_rpc.transaction.manager import TransactionManager

# Setup transaction manager
client.transaction_manager = TransactionManager(client)

# Use transactions
async with client.transaction_manager.transaction() as tx:
    partner_id = await client.create("res.partner", data)
    await client.write("res.partner", [partner_id], updates)
```

## Configuration Methods

### `async close()`

Close the client and cleanup resources.

**Example:**

```python
await client.close()
```

### Context Management

Context is passed per operation rather than set globally:

**Example:**

```python
# Pass context to individual operations
partners = await client.search_read(
    "res.partner",
    domain=[("is_company", "=", True)],
    context={
        "lang": "en_US",
        "tz": "UTC",
        "active_test": False
    }
)
```

## Error Handling

All client methods can raise the following exceptions:

- `AuthenticationError`: Authentication failures
- `ValidationError`: Data validation errors
- `AccessError`: Permission denied errors
- `ConnectionError`: Network connection issues
- `RequestTimeoutError`: Request timeout
- `ZenooError`: Base exception for all Zenoo RPC errors

**Example:**

```python
from zenoo_rpc.exceptions import AuthenticationError, ValidationError

try:
    await client.login("demo", "admin", "wrong_password")
except AuthenticationError as e:
    print(f"Login failed: {e}")

try:
    await client.create("res.partner", {"name": ""})  # Invalid data
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Thread Safety

The `ZenooClient` is **not thread-safe**. Each thread should use its own client instance or proper synchronization mechanisms.

**Example:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def worker_task(worker_id):
    # Each worker gets its own client
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        # Worker operations here

async def main():
    # Run multiple workers
    tasks = [worker_task(i) for i in range(5)]
    await asyncio.gather(*tasks)
```

## Performance Tips

1. **Reuse client instances** when possible
2. **Use context managers** for automatic cleanup
3. **Enable caching** for frequently accessed data
4. **Use batch operations** for bulk data
5. **Configure appropriate timeouts** for your use case

**Example:**

```python
from zenoo_rpc.models.common import ResPartner, ResUsers

# Good: Reuse client
class MyService:
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def operation1(self):
        return await self.client.model(ResPartner).all()

    async def operation2(self):
        return await self.client.model(ResUsers).all()

# Usage
async with ZenooClient("localhost") as client:
    await client.login("demo", "admin", "admin")
    service = MyService(client)
    
    result1 = await service.operation1()
    result2 = await service.operation2()
```
