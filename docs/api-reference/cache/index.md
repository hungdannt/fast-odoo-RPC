# Cache API Reference

The cache module provides intelligent caching with TTL and LRU strategies, supporting both in-memory and Redis backends for high-performance data caching.

## Overview

The cache system consists of:

- **CacheManager**: Main interface for cache operations
- **Backends**: MemoryCache and RedisCache implementations
- **Strategies**: TTL, LRU, and LFU caching strategies
- **Decorators**: Function-level caching decorators
- **Key Management**: Cache key generation and validation

## CacheManager

Main cache management interface coordinating between backends and strategies.

### Constructor

```python
class CacheManager:
    """Main cache manager for Zenoo RPC."""
    
    def __init__(self):
        self.backends: Dict[str, CacheBackend] = {}
        self.strategies: Dict[str, CacheStrategy] = {}
        self.default_backend = "memory"
        self.default_strategy = "ttl"
```

### Setup Methods

#### `async setup_memory_cache(name="memory", max_size=1000, default_ttl=None, strategy="ttl")`

Setup in-memory cache backend.

**Parameters:**

- `name` (str): Backend name (default: "memory")
- `max_size` (int): Maximum cache size (default: 1000)
- `default_ttl` (int, optional): Default TTL in seconds
- `strategy` (str): Cache strategy ("ttl", "lru", "lfu") (default: "ttl")

**Example:**

```python
# Basic memory cache
await client.cache_manager.setup_memory_cache()

# Custom configuration
await client.cache_manager.setup_memory_cache(
    name="custom_memory",
    max_size=5000,
    default_ttl=600,
    strategy="lru"
)
```

#### `async setup_redis_cache(name="redis", url="redis://localhost:6379/0", namespace="zenoo_rpc", strategy="ttl", enable_fallback=True, **kwargs)`

Setup Redis cache backend with production features.

**Parameters:**

- `name` (str): Backend name (default: "redis")
- `url` (str): Redis connection URL
- `namespace` (str): Cache namespace (default: "zenoo_rpc")
- `strategy` (str): Cache strategy (default: "ttl")
- `enable_fallback` (bool): Enable fallback to memory on Redis failure
- `max_connections` (int): Maximum Redis connections (default: 20)
- `retry_attempts` (int): Retry attempts for failed operations (default: 3)
- `circuit_breaker_threshold` (int): Circuit breaker failure threshold (default: 5)

**Example:**

```python
# Basic Redis cache
await client.cache_manager.setup_redis_cache(
    url="redis://localhost:6379/0"
)

# Production Redis cache
await client.cache_manager.setup_redis_cache(
    name="production_redis",
    url="redis://redis-cluster:6379/0",
    namespace="myapp",
    max_connections=50,
    retry_attempts=5,
    enable_fallback=True,
    circuit_breaker_threshold=10
)
```

### Cache Operations

#### `async set(key, value, ttl=None, backend=None)`

Set a value in cache.

**Parameters:**

- `key` (str | CacheKey): Cache key
- `value` (Any): Value to cache
- `ttl` (int, optional): Time to live in seconds
- `backend` (str, optional): Backend name (uses default if None)

**Returns:** `bool` - True if successful

**Example:**

```python
# Simple set
await cache_manager.set("user:123", user_data, ttl=300)

# With specific backend
await cache_manager.set("session:abc", session_data, backend="redis")

# Using CacheKey
from zenoo_rpc.cache.keys import make_cache_key
key = make_cache_key("res.partner", "search", {"domain": [("is_company", "=", True)]})
await cache_manager.set(key, partners_data, ttl=600)
```

#### `async get(key, backend=None)`

Get a value from cache.

**Parameters:**

- `key` (str | CacheKey): Cache key
- `backend` (str, optional): Backend name (uses default if None)

**Returns:** `Any` - Cached value or None if not found

**Example:**

```python
# Simple get
user_data = await cache_manager.get("user:123")

# With specific backend
session_data = await cache_manager.get("session:abc", backend="redis")

# Check if value exists
if user_data is not None:
    print(f"Found cached user: {user_data['name']}")
```

#### `async delete(key, backend=None)`

Delete a value from cache.

**Parameters:**

- `key` (str | CacheKey): Cache key
- `backend` (str, optional): Backend name (uses default if None)

**Returns:** `bool` - True if successful

**Example:**

```python
# Delete specific key
await cache_manager.delete("user:123")

# Delete from specific backend
await cache_manager.delete("session:abc", backend="redis")
```

#### `async exists(key, backend=None)`

Check if a key exists in cache.

**Parameters:**

- `key` (str | CacheKey): Cache key
- `backend` (str, optional): Backend name (uses default if None)

**Returns:** `bool` - True if key exists

**Example:**

```python
if await cache_manager.exists("user:123"):
    print("User data is cached")
```

#### `async clear(backend=None)`

Clear cache.

**Parameters:**

- `backend` (str, optional): Backend name (clears all if None)

**Returns:** `bool` - True if successful

**Example:**

```python
# Clear specific backend
await cache_manager.clear("memory")

# Clear all backends
await cache_manager.clear()
```

### Statistics and Monitoring

#### `async get_stats(backend=None)`

Get cache statistics.

**Parameters:**

- `backend` (str, optional): Backend name (all backends if None)

**Returns:** `Dict[str, Any]` - Statistics data

**Example:**

```python
# Get all stats
stats = await cache_manager.get_stats()
print(f"Total hits: {stats['total_hits']}")
print(f"Total misses: {stats['total_misses']}")
print(f"Hit rate: {stats['total_hits'] / (stats['total_hits'] + stats['total_misses']):.2%}")

# Get specific backend stats
redis_stats = await cache_manager.get_stats("redis")
```

## Cache Backends

### MemoryCache

In-memory cache backend with TTL and LRU support.

```python
class MemoryCache(CacheBackend):
    """In-memory cache backend."""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        cleanup_interval: int = 60
    ):
        """Initialize memory cache."""
```

**Features:**

- TTL (Time To Live) support
- LRU (Least Recently Used) eviction
- Thread-safe operations
- Memory usage tracking
- Automatic cleanup of expired items

**Example:**

```python
# Direct usage (usually not needed)
from zenoo_rpc.cache.backends import MemoryCache

cache = MemoryCache(max_size=5000, default_ttl=300)
await cache.set("key1", "value1", ttl=60)
value = await cache.get("key1")
```

### RedisCache

Enterprise-grade Redis cache backend with advanced features.

```python
class RedisCache(CacheBackend):
    """Enhanced Redis cache backend."""
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        namespace: str = "zenoo_rpc",
        serializer: str = "json",
        max_connections: int = 20,
        retry_attempts: int = 3,
        circuit_breaker_threshold: int = 5,
        enable_fallback: bool = True,
        **kwargs
    ):
        """Initialize Redis cache."""
```

**Enhanced Features:**

- Connection pool management
- Circuit breaker pattern for fault tolerance
- Exponential backoff retry with jitter
- Health checking and automatic reconnection
- Comprehensive metrics and observability
- Graceful shutdown and resource cleanup
- Fallback mechanisms for high availability

**Example:**

```python
# Direct usage (usually not needed)
from zenoo_rpc.cache.backends import RedisCache

cache = RedisCache(
    url="redis://localhost:6379/0",
    namespace="myapp",
    max_connections=50,
    enable_fallback=True
)
await cache.connect()
await cache.set("key1", {"data": "value"}, ttl=300)
value = await cache.get("key1")
await cache.close()
```

## Cache Strategies

### TTLCache

Time To Live cache strategy with automatic expiration.

```python
class TTLCache(CacheStrategy):
    """TTL cache strategy."""
    
    def __init__(
        self,
        backend: CacheBackend,
        default_ttl: int = 300,
        cleanup_interval: int = 60
    ):
        """Initialize TTL cache strategy."""
```

**Features:**

- Automatic expiration based on TTL
- Configurable default TTL
- Per-item TTL override
- Lazy expiration on access

**Example:**

```python
# Used automatically by CacheManager
await cache_manager.setup_memory_cache(strategy="ttl", default_ttl=300)
```

### LRUCache

Least Recently Used cache strategy with size-based eviction.

```python
class LRUCache(CacheStrategy):
    """LRU cache strategy."""
    
    def __init__(
        self,
        backend: CacheBackend,
        max_size: int = 1000
    ):
        """Initialize LRU cache strategy."""
```

**Features:**

- LRU eviction policy
- Configurable maximum size
- Access order tracking
- Efficient O(1) operations

**Example:**

```python
# Used automatically by CacheManager
await cache_manager.setup_memory_cache(strategy="lru", max_size=1000)
```

### LFUCache

Least Frequently Used cache strategy.

```python
class LFUCache(CacheStrategy):
    """LFU cache strategy."""
    
    def __init__(
        self,
        backend: CacheBackend,
        max_size: int = 1000
    ):
        """Initialize LFU cache strategy."""
```

**Features:**

- LFU eviction policy
- Frequency tracking
- Configurable maximum size
- Efficient operations

## Cache Decorators

### `@async_cached`

Enhanced async cache decorator with advanced features.

```python
def async_cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    backend: Optional[str] = None,
    cache_manager: Optional[CacheManager] = None,
    skip_cache: Optional[Callable] = None,
    key_builder: Optional[Callable] = None,
    prevent_stampede: bool = True,
    enable_metrics: bool = True,
    stale_while_revalidate: bool = False,
    stale_ttl: Optional[int] = None
):
    """Enhanced async cache decorator."""
```

**Features:**

- Cache stampede prevention
- Comprehensive metrics and monitoring
- Stale-while-revalidate pattern support
- Circuit breaker integration hooks
- Thread-safe async operations

**Example:**

```python
from zenoo_rpc.cache.decorators import async_cached

@async_cached(ttl=300, prevent_stampede=True, enable_metrics=True)
async def get_partner_data(client, partner_id):
    """Get partner data with caching."""
    return await client.model(ResPartner).filter(id=partner_id).first()

# Usage
partner = await get_partner_data(client, 123)
```

### `@cache_result`

Decorator for caching Odoo operation results.

```python
def cache_result(
    model: str,
    operation: str,
    ttl: Optional[int] = None,
    backend: Optional[str] = None,
    invalidate_on: Optional[List[str]] = None
):
    """Cache Odoo operation results."""
```

**Example:**

```python
from zenoo_rpc.cache.decorators import cache_result

@cache_result("res.partner", "search", ttl=300)
async def search_partners(client, domain, **kwargs):
    """Search partners with caching."""
    return await client.search_read("res.partner", domain, **kwargs)

# Usage
partners = await search_partners(client, [("is_company", "=", True)])
```

## Cache Key Management

### `CacheKey`

Structured cache key with metadata.

```python
@dataclass
class CacheKey:
    """Structured cache key."""
    key: str
    namespace: str
    model: Optional[str] = None
    operation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
```

### `make_cache_key()`

Generate cache key for Odoo operations.

```python
def make_cache_key(
    model: str,
    operation: str,
    params: Optional[Dict[str, Any]] = None,
    namespace: str = "zenoo_rpc",
    include_hash: bool = True
) -> CacheKey:
    """Generate cache key for Odoo operations."""
```

**Example:**

```python
from zenoo_rpc.cache.keys import make_cache_key

# Generate key for search operation
key = make_cache_key(
    model="res.partner",
    operation="search",
    params={"domain": [("is_company", "=", True)], "limit": 10}
)

# Use key for caching
await cache_manager.set(key, search_results, ttl=300)
```

### `make_model_cache_key()`

Generate cache key for model records.

```python
def make_model_cache_key(
    model: str,
    record_id: Union[int, List[int]],
    fields: Optional[List[str]] = None,
    namespace: str = "zenoo_rpc"
) -> CacheKey:
    """Generate cache key for model records."""
```

**Example:**

```python
from zenoo_rpc.cache.keys import make_model_cache_key

# Single record
key = make_model_cache_key("res.partner", 123, ["name", "email"])

# Multiple records
key = make_model_cache_key("res.partner", [1, 2, 3], ["name", "email"])
```

## Cache Integration with QuerySet

### Query-Level Caching

```python
# Cache query results
partners = await client.model(ResPartner).filter(
    is_company=True
).cache(
    key="all_companies",
    ttl=600,
    backend="redis"
).all()

# Cache with auto-generated key
partners = await client.model(ResPartner).filter(
    customer_rank__gt=0
).cache(ttl=300).all()

# Cache count queries
count = await client.model(ResPartner).filter(
    is_company=True
).cache(ttl=600).count()
```

### Cache Invalidation

```python
# Manual invalidation
await cache_manager.delete("all_companies")

# Pattern-based invalidation (Redis only)
await cache_manager.delete_pattern("res.partner:*")

# Model-based invalidation
await cache_manager.invalidate_model("res.partner")
```

## Error Handling

### Cache Exceptions

```python
from zenoo_rpc.cache.exceptions import CacheError, CacheBackendError

try:
    await cache_manager.set("key", "value")
except CacheBackendError as e:
    print(f"Cache backend error: {e}")
except CacheError as e:
    print(f"Cache error: {e}")
```

### Graceful Degradation

```python
async def get_data_with_fallback(key, fetch_func):
    """Get data with cache fallback."""
    try:
        # Try cache first
        cached_data = await cache_manager.get(key)
        if cached_data is not None:
            return cached_data
    except CacheError:
        # Cache error, continue to fetch
        pass
    
    # Fetch fresh data
    data = await fetch_func()
    
    try:
        # Try to cache result
        await cache_manager.set(key, data, ttl=300)
    except CacheError:
        # Cache error, but we have data
        pass
    
    return data
```

## Performance Considerations

### Cache Sizing

```python
# Memory cache sizing
await cache_manager.setup_memory_cache(
    max_size=10000,  # Adjust based on available memory
    strategy="lru"   # Use LRU for memory management
)

# Redis cache with connection pooling
await cache_manager.setup_redis_cache(
    max_connections=50,  # Adjust based on load
    retry_attempts=3,
    circuit_breaker_threshold=10
)
```

### TTL Strategy

```python
# Different TTL for different data types
await cache_manager.set("user:123", user_data, ttl=300)      # 5 minutes
await cache_manager.set("config:app", config_data, ttl=3600) # 1 hour
await cache_manager.set("static:countries", countries, ttl=86400) # 1 day
```

### Cache Warming

```python
async def warm_cache(client):
    """Warm up cache with frequently accessed data."""
    
    # Cache all countries
    countries = await client.model(ResCountry).all()
    await cache_manager.set("all_countries", countries, ttl=86400)
    
    # Cache active partners
    partners = await client.model(ResPartner).filter(active=True).all()
    await cache_manager.set("active_partners", partners, ttl=3600)
```

## Next Steps

- Learn about [Cache Strategies](strategies.md) in detail
- Explore [Cache Backends](backends.md) configuration
- Check [Cache Decorators](decorators.md) for function-level caching
- Understand [Cache Keys](keys.md) management
