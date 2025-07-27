# Common Issues and Solutions

This guide covers the most frequently encountered issues when using Zenoo RPC and provides step-by-step solutions to resolve them.

## Connection Issues

### Issue: Cannot Connect to Odoo Server

**Symptoms:**
- `ConnectionError: Cannot connect to Odoo server`
- `TimeoutError: Request timed out`
- `HTTPError: 502 Bad Gateway`

**Solutions:**

```python
# 1. Verify connection parameters
async def test_connection():
    try:
        async with ZenooClient("localhost", port=8069) as client:
            # Test basic connectivity
            health = await client.health_check()
            if health:
                print("Connection successful")
            else:
                print("Server not responding")
                
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        # Check network connectivity, firewall, etc.
```

**Common causes and fixes:**

1. **Wrong host/port:**
   ```python
   # ❌ Wrong
   client = ZenooClient("localhost", port=8080)
   
   # ✅ Correct
   client = ZenooClient("localhost", port=8069)
   ```

2. **Firewall blocking connection:**
   ```bash
   # Test connectivity
   telnet localhost 8069
   curl http://localhost:8069/web/database/selector
   ```

3. **SSL/TLS issues:**
   ```python
   # For self-signed certificates
   client = ZenooClient(
       "https://self-signed-odoo.com",
       verify_ssl=False  # Only for development!
   )
   ```

### Issue: SSL Certificate Verification Failed

**Symptoms:**
- `SSLError: certificate verify failed`
- `SSLError: hostname doesn't match`

**Solutions:**

```python
import ssl

# 1. Disable SSL verification (development only)
client = ZenooClient(
    "https://odoo-server.com",
    verify_ssl=False
)

# 2. Custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

client = ZenooClient(
    "https://odoo-server.com",
    verify_ssl=ssl_context
)

# 3. Add custom CA certificate
ssl_context = ssl.create_default_context(cafile="/path/to/ca-cert.pem")
client = ZenooClient(
    "https://odoo-server.com",
    verify_ssl=ssl_context
)
```

## Authentication Issues

### Issue: Authentication Failed

**Symptoms:**
- `AuthenticationError: Invalid credentials`
- `AuthenticationError: Database not found`
- `AuthenticationError: User not found`

**Solutions:**

```python
async def debug_authentication():
    try:
        async with ZenooClient("localhost", port=8069) as client:
            # 1. Check available databases
            databases = await client.list_databases()
            print(f"Available databases: {databases}")
            
            # 2. Try authentication
            await client.login("demo", "admin", "admin")
            print("Authentication successful")
            
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        
        # Debug steps:
        # 1. Verify database name
        # 2. Check username/password
        # 3. Ensure user has access rights
        # 4. Check if user is active
```

**Common fixes:**

1. **Wrong database name:**
   ```python
   # List available databases first
   databases = await client.list_databases()
   print(f"Available: {databases}")
   
   # Use correct database name
   await client.login("correct_db_name", "admin", "admin")
   ```

2. **Inactive user:**
   ```python
   # Check user status in Odoo:
   # Settings > Users & Companies > Users
   # Ensure user is active and has proper access rights
   ```

3. **Two-factor authentication:**
   ```python
   # If 2FA is enabled, you may need an API key
   await client.login("demo", "admin", "api_key_instead_of_password")
   ```

## Model and Query Issues

### Issue: Model Not Found

**Symptoms:**
- `ModelError: Model 'custom.model' not found`
- `AttributeError: 'NoneType' object has no attribute 'id'`

**Solutions:**

```python
# 1. Check if model exists
async def check_model_exists(client, model_name):
    try:
        # Try to access model
        model = client.model_registry.get(model_name)
        if model:
            print(f"Model {model_name} exists")
        else:
            print(f"Model {model_name} not found")
            
        # Alternative: try a simple query
        result = await client.search_read(model_name, [], ["id"], limit=1)
        print(f"Model accessible: {len(result)} records found")
        
    except Exception as e:
        print(f"Model error: {e}")

# 2. Use dynamic model access
async def use_dynamic_model(client):
    # Instead of using typed models
    partners = await client.search_read(
        "res.partner",
        domain=[("is_company", "=", True)],
        fields=["name", "email"],
        limit=10
    )
```

### Issue: Field Not Found

**Symptoms:**
- `FieldError: Field 'custom_field' not found`
- `KeyError: 'non_existent_field'`

**Solutions:**

```python
async def debug_fields(client):
    # 1. Get available fields
    fields_info = await client.execute_kw(
        "res.partner",
        "fields_get",
        [],
        {}
    )
    
    print("Available fields:")
    for field_name, field_info in fields_info.items():
        print(f"  {field_name}: {field_info.get('type', 'unknown')}")
    
    # 2. Use only existing fields
    partners = await client.search_read(
        "res.partner",
        domain=[],
        fields=["name", "email"],  # Only use existing fields
        limit=5
    )
```

## Performance Issues

### Issue: Slow Query Performance

**Symptoms:**
- Queries taking too long to execute
- High memory usage
- Timeout errors

**Solutions:**

```python
async def optimize_queries(client):
    # 1. Use pagination for large datasets
    page_size = 100
    offset = 0
    
    while True:
        partners = await client.model(ResPartner).limit(page_size).offset(offset).all()
        if not partners:
            break
            
        # Process batch
        await process_batch(partners)
        offset += page_size
    
    # 2. Select only needed fields
    partners = await client.search_read(
        "res.partner",
        domain=[("is_company", "=", True)],
        fields=["name", "email"],  # Only needed fields
        limit=1000
    )
    
    # 3. Use caching
    await client.cache_manager.setup_memory_cache(max_size=1000)
    
    # 4. Use batch operations
    data = [{"name": f"Partner {i}"} for i in range(100)]
    partners = await client.model(ResPartner).bulk_create(data)
```

### Issue: Memory Leaks

**Symptoms:**
- Increasing memory usage over time
- `MemoryError` exceptions
- Application becoming unresponsive

**Solutions:**

```python
import gc
import psutil

async def monitor_memory_usage():
    process = psutil.Process()
    
    # Monitor memory before operation
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform operation
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Process data in batches to avoid memory issues
        for i in range(0, 10000, 100):
            batch = await client.model(ResPartner).limit(100).offset(i).all()
            
            # Process batch
            await process_batch(batch)
            
            # Clear references
            del batch
            
            # Force garbage collection periodically
            if i % 1000 == 0:
                gc.collect()
    
    # Monitor memory after operation
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    print(f"Memory usage: {memory_before:.1f}MB -> {memory_after:.1f}MB")
```

## Cache Issues

### Issue: Cache Not Working

**Symptoms:**
- No performance improvement with caching enabled
- Cache hit rate is 0%
- Stale data being returned

**Solutions:**

```python
async def debug_cache_issues(client):
    # 1. Verify cache is enabled
    cache_info = await client.cache_manager.get_info()
    print(f"Cache backends: {cache_info['backends']}")
    
    # 2. Check cache statistics
    stats = await client.cache_manager.get_stats()
    print(f"Hit rate: {stats.get('hit_rate', 0):.2%}")
    print(f"Total requests: {stats.get('total_requests', 0)}")
    
    # 3. Test cache manually
    cache_key = "test_key"
    await client.cache_manager.set(cache_key, "test_value", ttl=60)
    
    cached_value = await client.cache_manager.get(cache_key)
    if cached_value == "test_value":
        print("Cache is working")
    else:
        print("Cache is not working")
    
    # 4. Clear cache if stale
    await client.cache_manager.clear_all_caches()
```

### Issue: Redis Connection Failed

**Symptoms:**
- `ConnectionError: Error connecting to Redis`
- `RedisError: Redis server not available`

**Solutions:**

```python
async def debug_redis_connection():
    try:
        # Test Redis connection
        import redis.asyncio as redis
        
        redis_client = redis.from_url("redis://localhost:6379/0")
        await redis_client.ping()
        print("Redis connection successful")
        await redis_client.close()
        
    except Exception as e:
        print(f"Redis connection failed: {e}")
        
        # Fallback to memory cache
        await client.cache_manager.setup_memory_cache(
            max_size=1000,
            default_ttl=300
        )
        print("Fallback to memory cache")
```

## Transaction Issues

### Issue: Transaction Deadlocks

**Symptoms:**
- `DeadlockError: Transaction deadlock detected`
- Operations hanging indefinitely

**Solutions:**

```python
async def handle_deadlocks(client):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with client.transaction() as tx:
                # Your transaction operations
                partner = await client.model(ResPartner).update(1, {
                    "name": "Updated Name"
                })
                return partner
                
        except DeadlockError as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            
            # Exponential backoff
            wait_time = 2 ** retry_count
            await asyncio.sleep(wait_time)
            print(f"Deadlock detected, retrying in {wait_time}s...")
```

### Issue: Transaction Timeout

**Symptoms:**
- `TransactionTimeoutError: Transaction timed out`
- Long-running operations failing

**Solutions:**

```python
async def handle_transaction_timeouts(client):
    try:
        # Increase timeout for long operations
        async with client.transaction(timeout=300) as tx:  # 5 minutes
            # Long-running operation
            result = await perform_bulk_operation(client)
            
    except TransactionTimeoutError:
        # Break operation into smaller chunks
        await perform_operation_in_chunks(client)

async def perform_operation_in_chunks(client):
    chunk_size = 100
    total_processed = 0
    
    while True:
        async with client.transaction(timeout=60) as tx:  # Shorter timeout
            # Process chunk
            chunk_result = await process_chunk(client, chunk_size, total_processed)
            
            if not chunk_result:
                break
                
            total_processed += len(chunk_result)
            print(f"Processed {total_processed} records")
```

## Data Validation Issues

### Issue: Validation Errors

**Symptoms:**
- `ValidationError: Invalid field value`
- `ValidationError: Required field missing`

**Solutions:**

```python
from pydantic import ValidationError

async def handle_validation_errors(client):
    try:
        # Create partner with validation
        partner = await client.model(ResPartner).create({
            "name": "Test Partner",
            "email": "invalid-email"  # This will fail validation
        })
        
    except ValidationError as e:
        print(f"Validation error: {e}")
        
        # Fix validation issues
        partner = await client.model(ResPartner).create({
            "name": "Test Partner",
            "email": "valid@email.com"  # Valid email
        })

# Custom validation
async def validate_before_create(client, data):
    """Validate data before sending to Odoo"""
    
    # Check required fields
    required_fields = ["name"]
    for field in required_fields:
        if not data.get(field):
            raise ValueError(f"Required field '{field}' is missing")
    
    # Validate email format
    if "email" in data and data["email"]:
        import re
        email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_pattern, data["email"]):
            raise ValueError("Invalid email format")
    
    # Create record
    return await client.model(ResPartner).create(data)
```

## Debugging Tools

### Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Specific loggers
logging.getLogger('zenoo_rpc').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.INFO)

async def debug_operations(client):
    # Operations will be logged with full details
    partners = await client.model(ResPartner).all()
```

### Performance Profiling

```python
import time
import cProfile
import pstats

async def profile_operations():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your operations here
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        partners = await client.model(ResPartner).all()
    
    profiler.disable()
    
    # Print profiling results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

### Network Debugging

```python
async def debug_network_issues():
    # Enable request/response logging
    import httpx
    
    async with httpx.AsyncClient() as http_client:
        # Test direct HTTP requests
        response = await http_client.get("http://localhost:8069/web/database/selector")
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        # Test JSON-RPC endpoint
        rpc_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "version"
            },
            "id": 1
        }
        
        response = await http_client.post(
            "http://localhost:8069/jsonrpc",
            json=rpc_data
        )
        print(f"RPC Response: {response.json()}")
```

## Getting Help

If you're still experiencing issues after trying these solutions:

1. **Check the logs** - Enable debug logging to see detailed error information
2. **Search GitHub Issues** - Look for similar issues in the repository
3. **Create a minimal reproduction** - Isolate the problem to the smallest possible code
4. **Ask for help** - Post in GitHub Discussions with:
   - Your code
   - Error messages
   - Environment details (Python version, Odoo version, etc.)
   - Steps to reproduce

## Prevention Tips

1. **Always use context managers** for client connections
2. **Handle exceptions appropriately** for your use case
3. **Monitor performance** in production
4. **Keep dependencies updated**
5. **Test thoroughly** before deploying
6. **Use appropriate timeouts** for your operations
7. **Implement proper logging** for debugging

Remember: Most issues are related to configuration, network connectivity, or data validation. Start with the basics and work your way up to more complex debugging techniques.
