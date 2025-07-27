# Performance Optimization Guide

This guide covers techniques to optimize the performance of your Zenoo RPC applications, from basic optimizations to advanced strategies for high-throughput scenarios.

## Overview

Zenoo RPC is designed for performance from the ground up, but there are several techniques you can use to maximize efficiency:

- **Intelligent Caching** - Reduce redundant RPC calls
- **Batch Operations** - Minimize network round trips
- **Connection Pooling** - Reuse HTTP connections
- **Query Optimization** - Fetch only what you need
- **Async Patterns** - Maximize concurrency
- **Transaction Management** - Ensure data consistency efficiently

## Caching Strategies

### Memory Caching

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def setup_memory_cache():
    async with ZenooClient("localhost", port=8069) as client:
        # Setup memory cache with optimal settings
        await client.cache_manager.setup_memory_cache(
            name="memory",
            max_size=2000,        # Cache up to 2000 items
            default_ttl=300,      # 5 minutes default TTL
            strategy="lru"        # LRU eviction strategy
        )
        
        await client.login("demo", "admin", "admin")
        
        # First call - hits database
        partners1 = await client.model(ResPartner).filter(
            is_company=True
        ).limit(100).all()
        
        # Second call - served from cache
        partners2 = await client.model(ResPartner).filter(
            is_company=True
        ).limit(100).all()
        
        print(f"Cache hit rate: {client.cache_manager.get_stats()['hit_rate']:.2%}")

asyncio.run(setup_memory_cache())
```

### Redis Caching for Production

```python
async def setup_redis_cache():
    async with ZenooClient("localhost", port=8069) as client:
        # Setup Redis cache for production
        await client.cache_manager.setup_redis_cache(
            name="redis",
            redis_url="redis://localhost:6379/0",
            default_ttl=600,      # 10 minutes
            key_prefix="zenoo:",  # Namespace your keys
            serializer="pickle"   # Fast serialization
        )
        
        await client.login("demo", "admin", "admin")
        
        # Cache expensive queries
        expensive_data = await client.model(ResPartner).filter(
            # Complex query that takes time
        ).all()

asyncio.run(setup_redis_cache())
```

### Cache Warming

```python
async def warm_cache(client: ZenooClient):
    """Pre-populate cache with frequently accessed data"""
    
    # Warm up common queries
    cache_warming_queries = [
        # Active companies
        client.model(ResPartner).filter(is_company=True, active=True).all(),
        
        # Countries and states
        client.model(ResCountry).all(),
        client.model(ResCountryState).all(),
        
        # Product categories
        client.model(ProductCategory).all(),
        
        # Common users
        client.model(ResUsers).filter(active=True).all(),
    ]
    
    # Execute all warming queries concurrently
    await asyncio.gather(*cache_warming_queries)
    
    print("Cache warmed up successfully")
```

## Batch Operations

### Bulk Create Operations

```python
async def efficient_bulk_create(client: ZenooClient):
    """Efficiently create large numbers of records"""
    
    # Prepare data for bulk creation
    partners_data = []
    for i in range(1000):
        partners_data.append({
            "name": f"Company {i:04d}",
            "is_company": True,
            "email": f"company{i:04d}@example.com",
            "phone": f"+1-555-{i:04d}"
        })
    
    # Batch size optimization
    batch_size = 100  # Optimal batch size for most cases
    
    all_partners = []
    for i in range(0, len(partners_data), batch_size):
        batch = partners_data[i:i + batch_size]
        
        # Create batch
        partners = await client.model(ResPartner).bulk_create(batch)
        all_partners.extend(partners)
        
        print(f"Created batch {i//batch_size + 1}: {len(partners)} records")
    
    print(f"Total created: {len(all_partners)} partners")
    return all_partners
```

### Bulk Update Operations

```python
async def efficient_bulk_update(client: ZenooClient):
    """Efficiently update large numbers of records"""
    
    # Update all companies without website
    updated_count = await client.model(ResPartner).filter(
        is_company=True,
        website__isnull=True
    ).update({
        "website": "https://company.example.com",
        "comment": "Website added via bulk update"
    })
    
    print(f"Updated {updated_count} companies")
    
    # Batch update with different values
    companies = await client.model(ResPartner).filter(
        is_company=True
    ).limit(100).all()
    
    update_data = []
    for company in companies:
        update_data.append({
            "id": company.id,
            "website": f"https://{company.name.lower().replace(' ', '')}.com",
            "comment": f"Updated on {datetime.now().isoformat()}"
        })
    
    # Bulk update with individual values
    updated_partners = await client.model(ResPartner).bulk_update(update_data)
    print(f"Updated {len(updated_partners)} companies with individual values")
```

## Connection Optimization

### HTTP/2 and Connection Pooling

```python
async def optimized_client_setup():
    """Setup client with optimal connection settings"""
    
    client = ZenooClient(
        "localhost",
        port=8069,
        # Enable HTTP/2 for multiplexing
        http2=True,
        
        # Optimize connection pooling
        max_connections=200,           # Total connections
        max_keepalive_connections=50,  # Persistent connections
        
        # Timeout optimization
        timeout=30.0,                  # Reasonable timeout
        
        # Enable compression
        headers={
            "Accept-Encoding": "gzip, deflate, br"
        }
    )
    
    return client
```

### Connection Reuse

```python
async def reuse_connections():
    """Demonstrate efficient connection reuse"""
    
    # ✅ Good - Reuse single client for multiple operations
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Multiple operations with same client
        tasks = [
            client.model(ResPartner).filter(is_company=True).all(),
            client.model(ProductProduct).filter(active=True).all(),
            client.model(SaleOrder).filter(state="sale").all(),
        ]
        
        results = await asyncio.gather(*tasks)
        
    # ❌ Bad - Multiple clients for each operation
    # This creates unnecessary connection overhead
```

## Query Optimization

### Field Selection

```python
async def optimize_field_selection(client: ZenooClient):
    """Only fetch fields you actually need"""
    
    # ❌ Bad - Fetches all fields
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).all()
    
    # ✅ Good - Only fetch needed fields
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).fields(["name", "email", "phone"]).all()
    
    # ✅ Better - Use specific queries for specific needs
    partner_names = await client.search_read(
        "res.partner",
        domain=[("is_company", "=", True)],
        fields=["name"],
        limit=1000
    )
```

### Relationship Optimization

```python
async def optimize_relationships(client: ZenooClient):
    """Efficiently handle relationship fields"""
    
    # ✅ Prefetch related data
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).prefetch("country_id", "state_id").all()
    
    # Now accessing relationships is fast
    for partner in partners:
        if partner.country_id:
            country = await partner.country_id  # Already prefetched
            print(f"{partner.name} - {country.name}")
    
    # ✅ Use joins for complex queries
    us_companies = await client.model(ResPartner).filter(
        is_company=True,
        country_id__code="US",
        state_id__name__ilike="california%"
    ).all()
```

### Pagination Optimization

```python
async def optimize_pagination(client: ZenooClient):
    """Efficiently handle large datasets"""
    
    page_size = 100  # Optimal page size
    offset = 0
    all_records = []
    
    while True:
        # Use cursor-based pagination when possible
        records = await client.model(ResPartner).filter(
            is_company=True,
            id__gt=offset  # Cursor-based pagination
        ).order_by("id").limit(page_size).all()
        
        if not records:
            break
        
        all_records.extend(records)
        offset = records[-1].id  # Update cursor
        
        # Process batch immediately to save memory
        await process_batch(records)
    
    return len(all_records)

async def process_batch(records):
    """Process records in batches to save memory"""
    # Process the batch
    for record in records:
        # Do something with the record
        pass
```

## Async Patterns

### Concurrent Operations

```python
async def concurrent_operations(client: ZenooClient):
    """Execute multiple operations concurrently"""
    
    # ✅ Good - Concurrent execution
    async def get_partners():
        return await client.model(ResPartner).filter(is_company=True).all()
    
    async def get_products():
        return await client.model(ProductProduct).filter(active=True).all()
    
    async def get_orders():
        return await client.model(SaleOrder).filter(state="sale").all()
    
    # Execute all queries concurrently
    partners, products, orders = await asyncio.gather(
        get_partners(),
        get_products(),
        get_orders()
    )
    
    print(f"Loaded {len(partners)} partners, {len(products)} products, {len(orders)} orders")
```

### Semaphore for Rate Limiting

```python
async def rate_limited_operations(client: ZenooClient):
    """Use semaphore to limit concurrent operations"""
    
    # Limit to 10 concurrent operations
    semaphore = asyncio.Semaphore(10)
    
    async def process_partner(partner_id):
        async with semaphore:
            partner = await client.model(ResPartner).get(partner_id)
            # Process partner
            await asyncio.sleep(0.1)  # Simulate processing
            return partner
    
    # Process many partners with rate limiting
    partner_ids = list(range(1, 101))
    tasks = [process_partner(pid) for pid in partner_ids]
    
    results = await asyncio.gather(*tasks)
    print(f"Processed {len(results)} partners with rate limiting")
```

## Transaction Optimization

### Efficient Transaction Usage

```python
async def optimize_transactions(client: ZenooClient):
    """Use transactions efficiently"""
    
    # ✅ Good - Group related operations in transactions
    async with client.transaction() as tx:
        # Create company
        company = await client.model(ResPartner).create({
            "name": "New Company",
            "is_company": True
        })
        
        # Create contacts for the company
        contacts_data = [
            {
                "name": "John Doe",
                "parent_id": company.id,
                "email": "john@company.com"
            },
            {
                "name": "Jane Smith", 
                "parent_id": company.id,
                "email": "jane@company.com"
            }
        ]
        
        contacts = await client.model(ResPartner).bulk_create(contacts_data)
        
        # All operations committed atomically
    
    # ❌ Bad - Too many small transactions
    # Creates unnecessary overhead
```

### Savepoints for Complex Operations

```python
async def use_savepoints(client: ZenooClient):
    """Use savepoints for complex nested operations"""
    
    async with client.transaction() as tx:
        # Main operation
        company = await client.model(ResPartner).create({
            "name": "Complex Company",
            "is_company": True
        })
        
        # Create savepoint for risky operation
        savepoint = await tx.savepoint("contacts_creation")
        
        try:
            # Risky operation that might fail
            contacts = await create_complex_contacts(client, company.id)
            await savepoint.release()
            
        except Exception as e:
            # Rollback to savepoint, keep main operation
            await savepoint.rollback()
            print(f"Contact creation failed: {e}")
            
        # Transaction continues with company created
```

## Monitoring and Profiling

### Performance Monitoring

```python
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def performance_monitor(operation_name: str):
    """Monitor operation performance"""
    start_time = time.time()
    start_memory = get_memory_usage()
    
    try:
        yield
    finally:
        end_time = time.time()
        end_memory = get_memory_usage()
        
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        
        print(f"{operation_name}:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Memory: {memory_delta:.2f}MB")

async def monitored_operations(client: ZenooClient):
    """Example of monitoring operations"""
    
    async with performance_monitor("Bulk Partner Creation"):
        partners = await efficient_bulk_create(client)
    
    async with performance_monitor("Cache Warming"):
        await warm_cache(client)

def get_memory_usage():
    """Get current memory usage in MB"""
    import psutil
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024
```

### Query Performance Analysis

```python
async def analyze_query_performance(client: ZenooClient):
    """Analyze and optimize query performance"""
    
    # Enable query logging
    client.enable_query_logging()
    
    # Execute queries
    await client.model(ResPartner).filter(
        is_company=True,
        country_id__code="US"
    ).all()
    
    # Get query statistics
    stats = client.get_query_stats()
    
    print("Query Performance:")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Average duration: {stats['avg_duration']:.3f}s")
    print(f"  Cache hit rate: {stats['cache_hit_rate']:.2%}")
    print(f"  Slowest query: {stats['slowest_query']:.3f}s")
```

## Best Practices Summary

### Do's ✅

1. **Use caching** for frequently accessed data
2. **Batch operations** when creating/updating multiple records
3. **Reuse client connections** across operations
4. **Fetch only needed fields** to reduce data transfer
5. **Use concurrent operations** with asyncio.gather()
6. **Group related operations** in transactions
7. **Monitor performance** in production

### Don'ts ❌

1. **Don't create new clients** for each operation
2. **Don't fetch all fields** when you only need a few
3. **Don't use individual operations** for bulk data
4. **Don't ignore caching** opportunities
5. **Don't use blocking operations** in async code
6. **Don't create unnecessary transactions**
7. **Don't ignore memory usage** in long-running processes

## Production Configuration

```python
async def production_setup():
    """Optimal configuration for production"""
    
    client = ZenooClient(
        host="production-odoo.com",
        port=443,
        protocol="https",
        
        # Performance settings
        http2=True,
        max_connections=100,
        max_keepalive_connections=25,
        timeout=60.0,
        
        # Security settings
        verify_ssl=True,
        
        # Headers
        headers={
            "User-Agent": "MyApp/1.0 (Zenoo-RPC)",
            "Accept-Encoding": "gzip, deflate, br"
        }
    )
    
    # Setup Redis cache
    await client.cache_manager.setup_redis_cache(
        redis_url="redis://cache-server:6379/0",
        default_ttl=300,
        max_size=10000
    )
    
    return client
```

This guide provides a comprehensive overview of performance optimization techniques. Apply these strategies based on your specific use case and always measure the impact of optimizations in your environment.

## Next Steps

- [Testing Strategies](testing.md) - Test your optimized code
- [Production Deployment](production-deployment.md) - Deploy with confidence
- [Caching Guide](../user-guide/caching.md) - Deep dive into caching
- [Batch Operations](../user-guide/batch-operations.md) - Master bulk operations
