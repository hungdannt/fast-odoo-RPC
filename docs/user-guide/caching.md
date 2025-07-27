# Caching System Guide

Zenoo RPC includes an intelligent caching system that dramatically improves performance by reducing redundant RPC calls to Odoo. This guide covers all aspects of the caching system, from basic usage to advanced strategies.

## Overview

The caching system provides:

- **Multiple backends** - Memory, Redis, and custom backends
- **TTL (Time To Live)** - Automatic cache expiration
- **LRU eviction** - Intelligent cache management
- **Cache warming** - Pre-populate frequently used data
- **Cache invalidation** - Manual and automatic cache clearing
- **Performance monitoring** - Cache hit/miss statistics

## Cache Backends

### Memory Cache (Default)

Best for development and single-instance deployments:

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def setup_memory_cache():
    async with ZenooClient("localhost", port=8069) as client:
        # Setup memory cache
        await client.cache_manager.setup_memory_cache(
            name="memory",           # Cache name
            max_size=1000,          # Maximum number of items
            default_ttl=300,        # Default TTL in seconds (5 minutes)
            strategy="ttl"          # Cache strategy: "ttl", "lru", "lfu"
        )

        await client.login("demo", "admin", "admin")

        # Queries are automatically cached
        partner_builder = client.model(ResPartner)
        partners = await partner_builder.filter(
            is_company=True
        ).all()  # First call - hits database

        partners = await partner_builder.filter(
            is_company=True
        ).all()  # Second call - served from cache

asyncio.run(setup_memory_cache())
```

### Redis Cache (Production)

Recommended for production and multi-instance deployments:

```python
async def setup_redis_cache():
    async with ZenooClient("localhost", port=8069) as client:
        # Setup Redis cache
        await client.cache_manager.setup_redis_cache(
            name="redis",
            url="redis://localhost:6379/0",
            namespace="zenoo_rpc",
            serializer="json",      # "json", "pickle", "msgpack"
            strategy="ttl",
            max_connections=10,
            enable_fallback=True,   # Fallback to memory cache if Redis fails
            circuit_breaker_threshold=5,
            retry_attempts=3
        )

        await client.login("demo", "admin", "admin")

        # Cached across multiple application instances
        partner_builder = client.model(ResPartner)
        data = await partner_builder.all()

asyncio.run(setup_redis_cache())
```

### Multiple Cache Backends

Use multiple backends for different data types:

```python
async def setup_multiple_caches():
    async with ZenooClient("localhost", port=8069) as client:
        # Fast memory cache for frequently accessed data
        await client.cache_manager.setup_memory_cache(
            name="fast",
            max_size=500,
            default_ttl=60  # 1 minute
        )
        
        # Redis cache for larger, less frequently accessed data
        await client.cache_manager.setup_redis_cache(
            name="persistent",
            redis_url="redis://localhost:6379/1",
            default_ttl=3600  # 1 hour
        )
        
        await client.login("demo", "admin", "admin")
        
        # Use specific cache for queries
        # Fast cache for user data
        users = await client.model(ResUsers).cache("fast").all()
        
        # Persistent cache for reference data
        countries = await client.model(ResCountry).cache("persistent").all()
```

## Cache Configuration

### TTL (Time To Live) Settings

```python
async def configure_ttl():
    async with ZenooClient("localhost", port=8069) as client:
        await client.cache_manager.setup_memory_cache(
            default_ttl=300  # Default 5 minutes
        )
        
        await client.login("demo", "admin", "admin")
        
        # Use default TTL
        partners = await client.model(ResPartner).all()
        
        # Custom TTL for specific queries
        countries = await client.model(ResCountry).cache_ttl(3600).all()  # 1 hour
        
        # No expiration (cache until manually cleared)
        currencies = await client.model(ResCurrency).cache_ttl(0).all()
        
        # Short TTL for frequently changing data
        orders = await client.model(SaleOrder).cache_ttl(60).all()  # 1 minute
```

### Cache Keys

Understanding how cache keys are generated:

```python
# Cache keys are automatically generated based on:
# - Model name
# - Query filters
# - Field selection
# - Ordering
# - Limit/offset

# These queries have different cache keys:
partners1 = await client.model(ResPartner).filter(is_company=True).all()
partners2 = await client.model(ResPartner).filter(is_company=False).all()
partners3 = await client.model(ResPartner).filter(is_company=True).limit(10).all()

# Custom cache keys
partners = await client.model(ResPartner).cache_key("my_custom_key").all()
```

## Cache Strategies

### Cache Warming

Pre-populate cache with frequently accessed data:

```python
async def warm_cache(client: ZenooClient):
    """Warm up cache with commonly accessed data"""
    
    # Define warming queries
    warming_queries = [
        # Reference data (rarely changes)
        client.model(ResCountry).cache_ttl(86400).all(),  # 24 hours
        client.model(ResCountryState).cache_ttl(86400).all(),
        client.model(ResCurrency).cache_ttl(86400).all(),
        
        # Master data (changes occasionally)
        client.model(ResPartner).filter(is_company=True).cache_ttl(3600).all(),  # 1 hour
        client.model(ProductCategory).cache_ttl(3600).all(),
        
        # Frequently accessed data
        client.model(ResUsers).filter(active=True).cache_ttl(300).all(),  # 5 minutes
    ]
    
    # Execute all warming queries concurrently
    await asyncio.gather(*warming_queries)
    
    print("Cache warming completed")

# Warm cache on application startup
async def startup():
    async with ZenooClient("localhost", port=8069) as client:
        await client.cache_manager.setup_redis_cache()
        await client.login("demo", "admin", "admin")
        await warm_cache(client)
```

### Conditional Caching

Cache based on conditions:

```python
async def conditional_caching(client: ZenooClient):
    """Apply caching based on data characteristics"""
    
    # Cache reference data for long periods
    countries = await client.model(ResCountry).cache_ttl(86400).all()
    
    # Cache user data for shorter periods
    users = await client.model(ResUsers).cache_ttl(300).all()
    
    # Don't cache frequently changing data
    recent_orders = await client.model(SaleOrder).filter(
        create_date__gte=datetime.now() - timedelta(hours=1)
    ).no_cache().all()
    
    # Cache based on data size
    large_dataset = await client.model(ResPartner).all()
    if len(large_dataset) > 1000:
        # Cache large datasets longer
        await client.model(ResPartner).cache_ttl(1800).all()
```

### Cache Hierarchies

Implement cache hierarchies for optimal performance:

```python
async def cache_hierarchy(client: ZenooClient):
    """Implement L1 (memory) and L2 (Redis) cache hierarchy"""
    
    # L1 Cache - Fast memory cache for hot data
    await client.cache_manager.setup_memory_cache(
        name="l1",
        max_size=200,
        default_ttl=60
    )
    
    # L2 Cache - Redis cache for warm data
    await client.cache_manager.setup_redis_cache(
        name="l2",
        redis_url="redis://localhost:6379/0",
        default_ttl=3600
    )
    
    # Hot data - frequently accessed
    active_users = await client.model(ResUsers).filter(
        active=True
    ).cache("l1").all()
    
    # Warm data - occasionally accessed
    all_partners = await client.model(ResPartner).cache("l2").all()
    
    # Cold data - rarely accessed, no cache
    archived_data = await client.model(ResPartner).filter(
        active=False
    ).no_cache().all()
```

## Cache Management

### Manual Cache Control

```python
async def manual_cache_control(client: ZenooClient):
    """Manually control cache behavior"""
    
    # Force cache refresh
    partners = await client.model(ResPartner).cache_refresh().all()
    
    # Bypass cache for this query
    fresh_data = await client.model(ResPartner).no_cache().all()
    
    # Clear specific cache entries
    await client.cache_manager.clear_cache("memory", "res.partner:*")
    
    # Clear all cache
    await client.cache_manager.clear_all_caches()
    
    # Get cache statistics
    stats = await client.cache_manager.get_stats()
    print(f"Cache hit rate: {stats['hit_rate']:.2%}")
    print(f"Total hits: {stats['hits']}")
    print(f"Total misses: {stats['misses']}")
```

### Cache Invalidation

Automatic and manual cache invalidation:

```python
async def cache_invalidation(client: ZenooClient):
    """Handle cache invalidation"""
    
    # Automatic invalidation on updates
    async with client.transaction() as tx:
        # Update partner
        partner = await client.model(ResPartner).update(1, {
            "name": "Updated Name"
        })
        # Related cache entries automatically invalidated
    
    # Manual invalidation
    await client.cache_manager.invalidate_model_cache("res.partner")
    
    # Invalidate specific patterns
    await client.cache_manager.invalidate_pattern("res.partner:is_company=True:*")
    
    # Time-based invalidation
    await client.cache_manager.setup_auto_invalidation(
        pattern="res.partner:*",
        interval=3600  # Invalidate every hour
    )
```

## Performance Monitoring

### Cache Statistics

```python
async def monitor_cache_performance(client: ZenooClient):
    """Monitor cache performance"""
    
    # Enable detailed statistics
    await client.cache_manager.enable_detailed_stats()
    
    # Perform some operations
    for i in range(100):
        partners = await client.model(ResPartner).filter(
            is_company=True
        ).limit(10).all()
    
    # Get comprehensive statistics
    stats = await client.cache_manager.get_detailed_stats()
    
    print("Cache Performance Report:")
    print(f"Hit Rate: {stats['hit_rate']:.2%}")
    print(f"Miss Rate: {stats['miss_rate']:.2%}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Average Response Time: {stats['avg_response_time']:.3f}s")
    print(f"Cache Size: {stats['cache_size']} items")
    print(f"Memory Usage: {stats['memory_usage']:.2f} MB")
    
    # Per-model statistics
    for model, model_stats in stats['by_model'].items():
        print(f"\n{model}:")
        print(f"  Hit Rate: {model_stats['hit_rate']:.2%}")
        print(f"  Requests: {model_stats['requests']}")
```

### Cache Health Monitoring

```python
async def cache_health_monitoring(client: ZenooClient):
    """Monitor cache health and performance"""
    
    # Set up health monitoring
    await client.cache_manager.setup_health_monitoring(
        check_interval=60,  # Check every minute
        alert_threshold=0.5  # Alert if hit rate < 50%
    )
    
    # Custom health checks
    async def custom_health_check():
        stats = await client.cache_manager.get_stats()
        
        # Check hit rate
        if stats['hit_rate'] < 0.7:
            print("WARNING: Low cache hit rate")
        
        # Check memory usage
        if stats.get('memory_usage', 0) > 500:  # MB
            print("WARNING: High cache memory usage")
        
        # Check Redis connection (if using Redis)
        if not await client.cache_manager.check_redis_health():
            print("ERROR: Redis connection failed")
    
    await custom_health_check()
```

## Advanced Patterns

### Cache-Aside Pattern

```python
async def cache_aside_pattern(client: ZenooClient, partner_id: int):
    """Implement cache-aside pattern manually"""
    
    cache_key = f"partner:{partner_id}"
    
    # Try to get from cache first
    partner = await client.cache_manager.get(cache_key)
    
    if partner is None:
        # Cache miss - fetch from database
        partner = await client.model(ResPartner).get(partner_id)
        
        if partner:
            # Store in cache
            await client.cache_manager.set(
                cache_key, 
                partner, 
                ttl=300
            )
    
    return partner
```

### Write-Through Caching

```python
async def write_through_caching(client: ZenooClient):
    """Implement write-through caching"""
    
    async def update_partner_with_cache(partner_id: int, data: dict):
        # Update in database
        partner = await client.model(ResPartner).update(partner_id, data)
        
        # Update cache immediately
        cache_key = f"partner:{partner_id}"
        await client.cache_manager.set(cache_key, partner, ttl=300)
        
        return partner
    
    # Usage
    updated_partner = await update_partner_with_cache(1, {
        "name": "Updated Name"
    })
```

### Cache Preloading

```python
async def cache_preloading(client: ZenooClient):
    """Preload related data to avoid N+1 queries"""
    
    # Get partners with preloaded countries
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).prefetch("country_id").all()
    
    # Preload countries into cache
    country_ids = {p.country_id.id for p in partners if p.country_id}
    countries = await client.model(ResCountry).filter(
        id__in=list(country_ids)
    ).cache_ttl(3600).all()
    
    # Now accessing country data is fast
    for partner in partners:
        if partner.country_id:
            country = await partner.country_id  # From cache
            print(f"{partner.name} - {country.name}")
```

## Best Practices

### Do's ✅

1. **Use appropriate TTL** based on data change frequency
2. **Cache reference data** for long periods
3. **Monitor cache performance** regularly
4. **Warm cache** on application startup
5. **Use Redis** for production deployments
6. **Implement cache hierarchies** for optimal performance
7. **Clear cache** when data is updated

### Don'ts ❌

1. **Don't cache frequently changing data** for long periods
2. **Don't ignore cache memory usage**
3. **Don't cache sensitive data** without encryption
4. **Don't rely solely on caching** for performance
5. **Don't forget to handle cache failures**
6. **Don't cache large objects** unnecessarily
7. **Don't use caching** for real-time data requirements

## Configuration Examples

### Development Configuration

```python
# Development - Simple memory cache
await client.cache_manager.setup_memory_cache(
    max_size=500,
    default_ttl=300
)
```

### Production Configuration

```python
# Production - Redis with monitoring
await client.cache_manager.setup_redis_cache(
    redis_url="redis://cache-cluster:6379/0",
    default_ttl=600,
    max_connections=20,
    key_prefix="myapp:",
    enable_monitoring=True
)
```

### High-Performance Configuration

```python
# High-performance - Multi-tier caching
await client.cache_manager.setup_memory_cache(
    name="l1",
    max_size=1000,
    default_ttl=60
)

await client.cache_manager.setup_redis_cache(
    name="l2", 
    redis_url="redis://cache-cluster:6379/0",
    default_ttl=3600,
    max_connections=50
)
```

The caching system is a powerful tool for optimizing Zenoo RPC performance. Use it wisely based on your application's data access patterns and performance requirements.

## Next Steps

- [Performance Optimization](../tutorials/performance-optimization.md) - Comprehensive performance guide
- [Batch Operations](batch-operations.md) - Optimize bulk operations
- [Transactions](transactions.md) - Ensure data consistency
- [Configuration](configuration.md) - Advanced configuration options
