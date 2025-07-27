# ZenooClient Usage Guide

The `ZenooClient` is the main entry point for all interactions with Odoo servers. This guide covers configuration, connection management, and advanced usage patterns.

## Basic Usage

### Creating a Client

```python
from zenoo_rpc import ZenooClient

# Basic connection
client = ZenooClient("localhost", port=8069)

# HTTPS connection
client = ZenooClient("https://myodoo.com")

# Full URL
client = ZenooClient("http://localhost:8069")
```

### Context Manager (Recommended)

Always use the client as an async context manager for proper resource cleanup:

```python
import asyncio

async def main():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        # Your operations here
        # Client automatically closes connections on exit

asyncio.run(main())
```

## Configuration Options

### Connection Parameters

```python
client = ZenooClient(
    host="localhost",           # Odoo server hostname
    port=8069,                  # Odoo server port
    protocol="http",            # Protocol: "http" or "https"
    timeout=30.0,               # Request timeout in seconds
    max_connections=100,        # Maximum concurrent connections
    max_keepalive_connections=20, # Keep-alive connections
    verify_ssl=True,            # SSL certificate verification
    http2=True                  # Enable HTTP/2 support
)
```

### Advanced Configuration

```python
import httpx
from zenoo_rpc import ZenooClient

# Custom transport configuration
transport = httpx.AsyncHTTPTransport(
    retries=3,
    limits=httpx.Limits(
        max_connections=200,
        max_keepalive_connections=50
    )
)

client = ZenooClient(
    "localhost",
    port=8069,
    transport=transport
)
```

## Authentication

### Basic Authentication

```python
async with ZenooClient("localhost", port=8069) as client:
    # Standard login
    await client.login("database_name", "username", "password")
    
    # Check authentication status
    if client.is_authenticated:
        print(f"Logged in as {client.username} on {client.database}")
        print(f"User ID: {client.uid}")
```

### Authentication with Error Handling

```python
from zenoo_rpc.exceptions import AuthenticationError

async def safe_login():
    async with ZenooClient("localhost", port=8069) as client:
        try:
            await client.login("demo", "admin", "admin")
            return client
        except AuthenticationError as e:
            print(f"Login failed: {e}")
            return None
```

### Session Management

```python
# Get session information
session_info = await client.get_session_info()
print(f"Session ID: {session_info.get('session_id')}")
print(f"User context: {session_info.get('user_context')}")

# Logout (optional - context manager handles this)
await client.logout()
```

## Health Checks and Server Information

### Server Health Check

```python
# Check if server is reachable
is_healthy = await client.health_check()
if not is_healthy:
    print("Server is not responding")
    return

# Get server version information
version_info = await client.get_server_version()
print(f"Server version: {version_info.get('server_version')}")
print(f"Protocol version: {version_info.get('protocol_version')}")
```

### Database Operations

```python
# List available databases
databases = await client.list_databases()
print(f"Available databases: {databases}")

# Check if database exists
if "demo" in databases:
    await client.login("demo", "admin", "admin")
```

## Model Access

### Type-Safe Model Access

```python
from zenoo_rpc.models.common import ResPartner, ProductProduct

# Get query builder for a model
partners = client.model(ResPartner)
products = client.model(ProductProduct)

# Execute queries
all_partners = await partners.all()
companies = await partners.filter(is_company=True).all()
```

### Dynamic Model Access

```python
# Access models by name (less type-safe)
partner_data = await client.search_read(
    "res.partner",
    domain=[("is_company", "=", True)],
    fields=["name", "email"],
    limit=10
)
```

## Low-Level RPC Operations

### Direct RPC Calls

```python
# Execute arbitrary methods
result = await client.execute_kw(
    "res.partner",
    "search_read",
    [],
    {
        "domain": [("is_company", "=", True)],
        "fields": ["name", "email"],
        "limit": 5
    }
)

# Call custom methods
custom_result = await client.execute_kw(
    "res.partner",
    "custom_method",
    [arg1, arg2],
    {"keyword_arg": "value"}
)
```

### Raw JSON-RPC Calls

```python
# For advanced use cases
response = await client.json_rpc_call(
    "object",
    "execute_kw",
    {
        "db": client.database,
        "uid": client.uid,
        "password": client.password,
        "model": "res.partner",
        "method": "search",
        "args": [[("is_company", "=", True)]],
        "kwargs": {"limit": 10}
    }
)
```

## Connection Pooling and Performance

### HTTP/2 Support

```python
# Enable HTTP/2 for better performance
client = ZenooClient(
    "localhost",
    port=8069,
    http2=True  # Enables HTTP/2 multiplexing
)
```

### Connection Limits

```python
# Configure connection pooling
client = ZenooClient(
    "localhost",
    port=8069,
    max_connections=200,        # Total connections
    max_keepalive_connections=50  # Persistent connections
)
```

### Timeout Configuration

```python
# Global timeout
client = ZenooClient("localhost", port=8069, timeout=60.0)

# Per-request timeout
result = await client.execute_kw(
    "res.partner",
    "search",
    [],
    timeout=10.0  # Override global timeout
)
```

## Error Handling

### Connection Errors

```python
from zenoo_rpc.exceptions import ConnectionError, TimeoutError

try:
    async with ZenooClient("unreachable-server.com") as client:
        await client.health_check()
except ConnectionError as e:
    print(f"Cannot connect to server: {e}")
except TimeoutError as e:
    print(f"Request timed out: {e}")
```

### Authentication Errors

```python
from zenoo_rpc.exceptions import AuthenticationError

try:
    await client.login("wrong_db", "wrong_user", "wrong_pass")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Handle login failure
```

## Advanced Features

### Custom Headers

```python
# Add custom headers to all requests
client = ZenooClient(
    "localhost",
    port=8069,
    headers={
        "User-Agent": "MyApp/1.0",
        "X-Custom-Header": "value"
    }
)
```

### Proxy Support

```python
# Use HTTP proxy
client = ZenooClient(
    "localhost",
    port=8069,
    proxies={
        "http://": "http://proxy.company.com:8080",
        "https://": "http://proxy.company.com:8080"
    }
)
```

### SSL Configuration

```python
import ssl

# Custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

client = ZenooClient(
    "https://self-signed-odoo.com",
    verify_ssl=ssl_context
)
```

## Client State and Properties

### Accessing Client Information

```python
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    
    # Client properties
    print(f"Host: {client.host}")
    print(f"Port: {client.port}")
    print(f"Database: {client.database}")
    print(f"Username: {client.username}")
    print(f"User ID: {client.uid}")
    print(f"Authenticated: {client.is_authenticated}")
    print(f"Base URL: {client.base_url}")
```

### Session Context

```python
# Access user context
user_context = client.context
print(f"Language: {user_context.get('lang')}")
print(f"Timezone: {user_context.get('tz')}")

# Modify context for requests
custom_context = {**user_context, "active_test": False}
result = await client.execute_kw(
    "res.partner",
    "search",
    [],
    context=custom_context
)
```

## Best Practices

### 1. Always Use Context Manager

```python
# ✅ Good - Automatic cleanup
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    # Operations here

# ❌ Bad - Manual cleanup required
client = ZenooClient("localhost", port=8069)
try:
    await client.login("demo", "admin", "admin")
    # Operations here
finally:
    await client.close()
```

### 2. Reuse Client Instances

```python
# ✅ Good - Reuse connection
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    
    # Multiple operations with same client
    partners = await client.model(ResPartner).all()
    products = await client.model(ProductProduct).all()

# ❌ Bad - Multiple clients
for operation in operations:
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        # Single operation
```

### 3. Handle Errors Gracefully

```python
from zenoo_rpc.exceptions import ZenooError

async def robust_operation():
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            return await client.model(ResPartner).all()
    except ZenooError as e:
        logger.error(f"Zenoo RPC error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []
```

### 4. Configure Appropriate Timeouts

```python
# Different timeouts for different operations
client = ZenooClient(
    "localhost",
    port=8069,
    timeout=30.0  # Default timeout
)

# Quick operations
await client.health_check()

# Long-running operations with custom timeout
large_dataset = await client.execute_kw(
    "large.model",
    "export_data",
    [],
    timeout=300.0  # 5 minutes
)
```

## Next Steps

- [Models & Type Safety](models.md) - Learn about Pydantic models
- [Query Builder](queries.md) - Master the query system
- [Caching System](caching.md) - Optimize performance
- [Error Handling](error-handling.md) - Handle errors gracefully
