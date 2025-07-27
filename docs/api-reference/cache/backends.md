# Cache Backends API Reference

Production-ready cache backends with MemoryCache for development and RedisCache for enterprise deployments, featuring connection pooling, circuit breakers, and fallback mechanisms.

## Overview

Cache backends provide the storage layer for caching strategies:

- **MemoryCache**: In-memory storage with TTL and LRU support
- **RedisCache**: Enterprise Redis backend with resilience patterns
- **Connection Management**: Pooling, health checks, automatic reconnection
- **Fault Tolerance**: Circuit breakers, retry logic, fallback mechanisms
- **Monitoring**: Comprehensive metrics and observability

## CacheBackend Base Class

Abstract base class for all cache backends.

### Abstract Methods

```python
class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the cache backend."""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the cache backend."""
    
    @abstractmethod
    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from cache."""
    
    @abstractmethod
    async def set(self, key: Union[str, CacheKey], value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
    
    @abstractmethod
    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from cache."""
    
    @abstractmethod
    async def exists(self, key: Union[str, CacheKey]) -> bool:
        """Check if a key exists."""
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values."""
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
```

## MemoryCache Backend

In-memory cache backend with TTL and LRU support for development and testing.

### Constructor

```python
class MemoryCache(CacheBackend):
    """In-memory cache backend with TTL and LRU support."""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        cleanup_interval: int = 60,
    ):
        """Initialize memory cache."""
```

**Parameters:**

- `max_size` (int): Maximum number of items to store (default: 1000)
- `default_ttl` (Optional[int]): Default TTL in seconds (default: None)
- `cleanup_interval` (int): Cleanup interval in seconds (default: 60)

**Features:**

- TTL (Time To Live) support
- LRU (Least Recently Used) eviction
- Thread-safe operations
- Memory usage tracking
- Automatic cleanup of expired items

### Usage Examples

#### Basic Memory Cache

```python
from zenoo_rpc.cache.backends import MemoryCache

# Create memory cache
cache = MemoryCache(max_size=1000, default_ttl=300)

# Connect (no-op for memory cache)
await cache.connect()

# Set values
await cache.set("user:123", {"name": "John", "email": "john@example.com"})
await cache.set("session:abc", session_data, ttl=1800)  # 30 minutes

# Get values
user = await cache.get("user:123")
session = await cache.get("session:abc")

# Check existence
exists = await cache.exists("user:123")

# Delete values
await cache.delete("user:123")

# Clear all
await cache.clear()

# Disconnect
await cache.disconnect()
```

#### Memory Cache with TTL

```python
# Cache with default TTL
cache = MemoryCache(max_size=500, default_ttl=600)  # 10 minutes default

await cache.connect()

# Uses default TTL
await cache.set("config", app_config)

# Override TTL for specific items
await cache.set("temp_token", token, ttl=60)  # 1 minute
await cache.set("permanent", data, ttl=None)  # No expiration

# Items expire automatically
await asyncio.sleep(61)
token = await cache.get("temp_token")  # Returns None (expired)
config = await cache.get("config")     # Still available
```

### Memory Cache Statistics

```python
stats = await cache.get_stats()
print(f"Backend: {stats['backend']}")
print(f"Max size: {stats['max_size']}")
print(f"Current size: {stats['current_size']}")
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Memory usage: {stats['memory_usage']} bytes")
print(f"Expired items: {stats['expired_items']}")
```

## RedisCache Backend

Enterprise Redis backend with production-ready features for high-availability deployments.

### Constructor

```python
class RedisCache(CacheBackend):
    """Enhanced Redis cache backend with production-ready features."""
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        namespace: str = "zenoo_rpc",
        serializer: str = "json",
        max_connections: int = 20,
        retry_attempts: int = 3,
        retry_backoff_base: float = 0.1,
        retry_backoff_max: float = 60.0,
        health_check_interval: int = 30,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        enable_fallback: bool = True,
    ):
        """Initialize enhanced Redis cache."""
```

**Parameters:**

- `url` (str): Redis connection URL (default: "redis://localhost:6379/0")
- `namespace` (str): Cache namespace for key isolation (default: "zenoo_rpc")
- `serializer` (str): Serialization method - "json" or "pickle" (default: "json")
- `max_connections` (int): Maximum connections in pool (default: 20)
- `retry_attempts` (int): Number of retry attempts (default: 3)
- `retry_backoff_base` (float): Base delay for exponential backoff (default: 0.1)
- `retry_backoff_max` (float): Maximum delay for exponential backoff (default: 60.0)
- `health_check_interval` (int): Health check interval in seconds (default: 30)
- `circuit_breaker_threshold` (int): Failures before circuit opens (default: 5)
- `circuit_breaker_timeout` (int): Circuit breaker timeout in seconds (default: 60)
- `socket_timeout` (int): Socket timeout in seconds (default: 5)
- `socket_connect_timeout` (int): Socket connect timeout in seconds (default: 5)
- `enable_fallback` (bool): Enable fallback to memory cache (default: True)

**Enhanced Features:**

- Singleton connection pool management
- Circuit breaker pattern for fault tolerance
- Exponential backoff retry with jitter
- Health checking and automatic reconnection
- Comprehensive metrics and observability
- Graceful shutdown and resource cleanup
- Transaction-aware cache invalidation
- Fallback mechanisms for high availability

### Usage Examples

#### Basic Redis Cache

```python
from zenoo_rpc.cache.backends import RedisCache

# Create Redis cache
cache = RedisCache(
    url="redis://localhost:6379/0",
    namespace="myapp",
    max_connections=20
)

# Connect to Redis
await cache.connect()

# Set values with TTL
await cache.set("user:123", user_data, ttl=3600)  # 1 hour
await cache.set("session:abc", session_data, ttl=1800)  # 30 minutes

# Get values
user = await cache.get("user:123")
session = await cache.get("session:abc")

# Graceful shutdown
await cache.disconnect()
```

#### Production Redis Configuration

```python
# Production-ready Redis cache
cache = RedisCache(
    url="redis://redis-cluster:6379/0",
    namespace="production",
    serializer="json",
    max_connections=50,
    retry_attempts=5,
    retry_backoff_base=0.2,
    retry_backoff_max=30.0,
    health_check_interval=15,
    circuit_breaker_threshold=10,
    circuit_breaker_timeout=120,
    socket_timeout=10,
    socket_connect_timeout=10,
    enable_fallback=True
)

await cache.connect()

# Cache operations with automatic retry and fallback
try:
    await cache.set("critical_data", data, ttl=7200)
    result = await cache.get("critical_data")
except Exception as e:
    # Automatic fallback to memory cache if Redis fails
    print(f"Redis error, using fallback: {e}")
```

#### Redis with Authentication and SSL

```python
# Redis with authentication and SSL
cache = RedisCache(
    url="rediss://username:password@redis.example.com:6380/0",
    namespace="secure_app",
    max_connections=30,
    socket_timeout=15,
    enable_fallback=True
)

await cache.connect()
```

### Circuit Breaker Pattern

The Redis backend implements circuit breaker pattern for fault tolerance:

```python
# Circuit breaker states:
# - CLOSED: Normal operation
# - OPEN: Redis is failing, use fallback
# - HALF_OPEN: Testing if Redis is back online

cache = RedisCache(
    circuit_breaker_threshold=5,  # Open after 5 failures
    circuit_breaker_timeout=60,   # Test recovery after 60 seconds
    enable_fallback=True          # Use memory cache when circuit is open
)

# Operations automatically use fallback when circuit is open
await cache.set("key", "value")  # May use fallback if Redis is down
value = await cache.get("key")   # May return from fallback cache
```

### Connection Pool Management

```python
# Connection pool configuration
cache = RedisCache(
    url="redis://localhost:6379/0",
    max_connections=20,           # Pool size
    socket_timeout=5,             # Individual operation timeout
    socket_connect_timeout=5,     # Connection establishment timeout
    health_check_interval=30      # Health check frequency
)

# Pool is managed automatically
await cache.connect()  # Creates connection pool

# Multiple concurrent operations share the pool
tasks = [
    cache.set(f"key{i}", f"value{i}")
    for i in range(100)
]
await asyncio.gather(*tasks)  # Uses connection pool efficiently
```

### Retry Logic with Exponential Backoff

```python
cache = RedisCache(
    retry_attempts=5,             # Retry up to 5 times
    retry_backoff_base=0.1,       # Start with 100ms delay
    retry_backoff_max=30.0        # Cap at 30 seconds
)

# Automatic retry with exponential backoff:
# Attempt 1: immediate
# Attempt 2: ~100ms delay
# Attempt 3: ~200ms delay
# Attempt 4: ~400ms delay
# Attempt 5: ~800ms delay
await cache.set("key", "value")
```

### Fallback Mechanism

```python
# Redis with memory cache fallback
cache = RedisCache(
    url="redis://localhost:6379/0",
    enable_fallback=True  # Automatic fallback to MemoryCache
)

await cache.connect()

# When Redis is available
await cache.set("key1", "value1")  # Stored in Redis
value = await cache.get("key1")    # Retrieved from Redis

# When Redis fails (network issues, server down, etc.)
await cache.set("key2", "value2")  # Stored in fallback memory cache
value = await cache.get("key2")    # Retrieved from fallback cache

# Fallback is transparent to application code
```

### Redis Statistics

```python
stats = await cache.get_stats()
print(f"Backend: {stats['backend']}")
print(f"Connected: {stats['connected']}")
print(f"Circuit state: {stats['circuit_state']}")
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Connection errors: {stats['connection_errors']}")
print(f"Circuit breaker trips: {stats['circuit_breaker_trips']}")
print(f"Fallback hits: {stats['fallback_hits']}")
print(f"Total operations: {stats['total_operations']}")
```

## Serialization

Both backends support multiple serialization formats:

### JSON Serialization (Default)

```python
# JSON serializer (human-readable, cross-language compatible)
cache = RedisCache(serializer="json")

# Supports basic Python types
await cache.set("data", {
    "string": "value",
    "number": 42,
    "boolean": True,
    "list": [1, 2, 3],
    "dict": {"nested": "value"}
})
```

### Pickle Serialization

```python
# Pickle serializer (supports complex Python objects)
cache = RedisCache(serializer="pickle")

# Supports any pickleable Python object
import datetime
from dataclasses import dataclass

@dataclass
class User:
    name: str
    created_at: datetime.datetime

user = User("John", datetime.datetime.now())
await cache.set("user", user)  # Serialized with pickle
retrieved_user = await cache.get("user")  # Deserialized back to User object
```

## Error Handling

### Connection Errors

```python
try:
    cache = RedisCache(url="redis://invalid-host:6379/0")
    await cache.connect()
except ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    # Use fallback or handle gracefully
```

### Operation Errors

```python
try:
    await cache.set("key", "value")
    value = await cache.get("key")
except Exception as e:
    print(f"Cache operation failed: {e}")
    # Fallback mechanism handles this automatically if enabled
```

### Graceful Degradation

```python
# Cache operations with graceful degradation
async def get_user_data(user_id: str):
    try:
        # Try cache first
        cached_data = await cache.get(f"user:{user_id}")
        if cached_data:
            return cached_data
    except Exception:
        # Cache failure, continue without caching
        pass
    
    # Load from database
    user_data = await load_user_from_db(user_id)
    
    try:
        # Try to cache for next time
        await cache.set(f"user:{user_id}", user_data, ttl=3600)
    except Exception:
        # Cache failure, but we have the data
        pass
    
    return user_data
```

## Performance Monitoring

### Backend Comparison

```python
async def compare_backends():
    """Compare performance of different backends."""
    
    # Memory cache
    memory_cache = MemoryCache(max_size=1000)
    await memory_cache.connect()
    
    # Redis cache
    redis_cache = RedisCache(url="redis://localhost:6379/0")
    await redis_cache.connect()
    
    # Test workload
    test_data = {"key": f"value_{i}" for i in range(100)}
    
    for name, cache in [("Memory", memory_cache), ("Redis", redis_cache)]:
        start_time = time.time()
        
        # Write test
        for key, value in test_data.items():
            await cache.set(key, value)
        
        # Read test
        for key in test_data.keys():
            await cache.get(key)
        
        end_time = time.time()
        stats = await cache.get_stats()
        
        print(f"{name} Cache:")
        print(f"  Time: {end_time - start_time:.3f}s")
        print(f"  Hit rate: {stats.get('hit_rate', 0):.2%}")
        print()
```

### Health Monitoring

```python
async def monitor_cache_health():
    """Monitor cache backend health."""
    
    cache = RedisCache(health_check_interval=10)
    await cache.connect()
    
    while True:
        stats = await cache.get_stats()
        
        # Check connection health
        if not stats.get('connected', False):
            print("⚠️  Cache disconnected")
        
        # Check circuit breaker
        if stats.get('circuit_state') == 'open':
            print("🔴 Circuit breaker open - using fallback")
        
        # Check error rates
        error_rate = stats.get('error_rate', 0)
        if error_rate > 0.1:  # 10% error rate
            print(f"⚠️  High error rate: {error_rate:.2%}")
        
        await asyncio.sleep(30)  # Check every 30 seconds
```

## Best Practices

### 1. Choose Appropriate Backend

```python
# ✅ Good: Use MemoryCache for development/testing
if environment == "development":
    cache = MemoryCache(max_size=1000)

# ✅ Good: Use RedisCache for production
elif environment == "production":
    cache = RedisCache(
        url=redis_url,
        max_connections=50,
        enable_fallback=True
    )
```

### 2. Configure Connection Pooling

```python
# ✅ Good: Size pool based on concurrency needs
cache = RedisCache(
    max_connections=min(50, expected_concurrent_operations * 2),
    socket_timeout=5,
    socket_connect_timeout=5
)
```

### 3. Enable Fallback for High Availability

```python
# ✅ Good: Always enable fallback in production
cache = RedisCache(
    url=redis_url,
    enable_fallback=True,  # Automatic fallback to memory cache
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60
)
```

### 4. Monitor and Alert

```python
# ✅ Good: Regular health monitoring
async def cache_health_check():
    stats = await cache.get_stats()
    
    # Alert on high error rates
    if stats.get('error_rate', 0) > 0.05:
        await send_alert("High cache error rate")
    
    # Alert on circuit breaker trips
    if stats.get('circuit_breaker_trips', 0) > 0:
        await send_alert("Cache circuit breaker activated")
```

## Next Steps

- Learn about [Cache Strategies](strategies.md) for eviction policies
- Explore [Cache Manager](../manager.md) for high-level cache management
- Check [Cache Performance](../../performance/caching.md) for optimization techniques
