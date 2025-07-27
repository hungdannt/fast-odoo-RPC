# Cache Strategies API Reference

Advanced caching strategies with TTL, LRU, LFU, and adaptive algorithms for optimal performance and memory management in Zenoo RPC applications.

## Overview

Cache strategies define how cached data is managed, including:

- **Eviction Policies**: TTL, LRU, LFU algorithms for memory management
- **Expiration Handling**: Automatic cleanup and lazy expiration
- **Access Tracking**: Frequency and recency monitoring
- **Performance Optimization**: Aging mechanisms and batch operations
- **Statistics**: Comprehensive metrics for monitoring and tuning

## CacheStrategy Base Class

Abstract base class for all cache strategies.

### Constructor

```python
class CacheStrategy(ABC):
    """Abstract base class for cache strategies."""
    
    def __init__(self, backend: CacheBackend):
        """Initialize cache strategy."""
        self.backend = backend
```

**Parameters:**

- `backend` (CacheBackend): Cache backend to use (MemoryCache or RedisCache)

### Abstract Methods

#### `async get(key)`

Get a value from cache with strategy-specific logic.

**Parameters:**

- `key` (Union[str, CacheKey]): Cache key

**Returns:** `Optional[Any]` - Cached value or None if not found/expired

#### `async set(key, value, **kwargs)`

Set a value in cache with strategy-specific logic.

**Parameters:**

- `key` (Union[str, CacheKey]): Cache key
- `value` (Any): Value to cache
- `**kwargs`: Strategy-specific parameters

**Returns:** `bool` - True if successful

#### `async delete(key)`

Delete a value from cache.

**Parameters:**

- `key` (Union[str, CacheKey]): Cache key

**Returns:** `bool` - True if deleted

#### `async clear()`

Clear all cached values.

**Returns:** `bool` - True if successful

#### `async get_stats()`

Get cache statistics.

**Returns:** `Dict[str, Any]` - Strategy-specific statistics

## TTLCache Strategy

Time To Live cache strategy with automatic expiration.

### Constructor

```python
class TTLCache(CacheStrategy):
    """Time To Live (TTL) cache strategy."""
    
    def __init__(
        self, 
        backend: CacheBackend, 
        default_ttl: int = 300, 
        cleanup_interval: int = 60
    ):
        """Initialize TTL cache strategy."""
```

**Parameters:**

- `backend` (CacheBackend): Cache backend
- `default_ttl` (int): Default TTL in seconds (default: 300)
- `cleanup_interval` (int): Cleanup interval in seconds (default: 60)

**Features:**

- Automatic expiration based on TTL
- Configurable default TTL
- Per-item TTL override
- Lazy expiration on access
- Periodic cleanup of expired items

### Usage Examples

#### Basic TTL Caching

```python
from zenoo_rpc.cache.strategies import TTLCache
from zenoo_rpc.cache.backends import MemoryCache

# Setup TTL cache with 5-minute default TTL
backend = MemoryCache()
cache = TTLCache(backend, default_ttl=300, cleanup_interval=60)

# Set with default TTL
await cache.set("user:123", user_data)

# Set with custom TTL (1 hour)
await cache.set("session:abc", session_data, ttl=3600)

# Get value (automatically checks expiration)
user = await cache.get("user:123")
```

#### TTL with Different Expiration Times

```python
# Short-lived data (30 seconds)
await cache.set("temp:token", token, ttl=30)

# Medium-lived data (5 minutes)
await cache.set("user:profile", profile, ttl=300)

# Long-lived data (1 hour)
await cache.set("config:settings", settings, ttl=3600)

# Permanent until manually deleted (no TTL)
await cache.set("static:data", data, ttl=None)
```

### TTL Statistics

```python
stats = await cache.get_stats()
print(f"Strategy: {stats['strategy']}")
print(f"Default TTL: {stats['default_ttl']} seconds")
print(f"Tracked expiries: {stats['tracked_expiries']}")
print(f"Expired items: {stats['expired_items']}")
```

## LRUCache Strategy

Least Recently Used cache strategy with size-based eviction.

### Constructor

```python
class LRUCache(CacheStrategy):
    """Least Recently Used (LRU) cache strategy."""
    
    def __init__(self, backend: CacheBackend, max_size: int = 1000):
        """Initialize LRU cache strategy."""
```

**Parameters:**

- `backend` (CacheBackend): Cache backend
- `max_size` (int): Maximum number of items (default: 1000)

**Features:**

- LRU eviction policy
- Configurable maximum size
- Access order tracking
- Efficient O(1) operations
- Automatic eviction when size limit reached

### Usage Examples

#### Basic LRU Caching

```python
from zenoo_rpc.cache.strategies import LRUCache
from zenoo_rpc.cache.backends import MemoryCache

# Setup LRU cache with 1000 item limit
backend = MemoryCache()
cache = LRUCache(backend, max_size=1000)

# Add items (tracks access order)
await cache.set("item1", data1)
await cache.set("item2", data2)
await cache.set("item3", data3)

# Access item1 (moves to most recently used)
value = await cache.get("item1")

# When cache is full, least recently used items are evicted
for i in range(1001):
    await cache.set(f"item{i}", f"data{i}")
# Oldest items automatically evicted
```

#### LRU for User Sessions

```python
# LRU cache for user sessions (limit to 10,000 active sessions)
session_cache = LRUCache(backend, max_size=10000)

async def get_user_session(session_id: str):
    """Get user session with LRU caching."""
    session = await session_cache.get(f"session:{session_id}")
    if session is None:
        # Load from database
        session = await load_session_from_db(session_id)
        if session:
            await session_cache.set(f"session:{session_id}", session)
    return session

# Most active users stay in cache
# Inactive sessions automatically evicted
```

### LRU Statistics

```python
stats = await cache.get_stats()
print(f"Strategy: {stats['strategy']}")
print(f"Max size: {stats['max_size']}")
print(f"Current size: {stats['current_size']}")
print(f"Access order length: {stats['access_order_length']}")
```

## LFUCache Strategy

Least Frequently Used cache strategy with frequency-based eviction.

### Constructor

```python
class LFUCache(CacheStrategy):
    """Least Frequently Used (LFU) cache strategy."""
    
    def __init__(
        self, 
        backend: CacheBackend, 
        max_size: int = 1000, 
        aging_factor: float = 0.9
    ):
        """Initialize LFU cache strategy."""
```

**Parameters:**

- `backend` (CacheBackend): Cache backend
- `max_size` (int): Maximum number of items (default: 1000)
- `aging_factor` (float): Factor to age frequencies (0.0-1.0, default: 0.9)

**Features:**

- LFU eviction policy
- Configurable maximum size
- Access frequency tracking
- Aging mechanism to prevent stale popular items
- Automatic eviction of least frequently used items

### Usage Examples

#### Basic LFU Caching

```python
from zenoo_rpc.cache.strategies import LFUCache
from zenoo_rpc.cache.backends import MemoryCache

# Setup LFU cache with aging
backend = MemoryCache()
cache = LFUCache(backend, max_size=1000, aging_factor=0.9)

# Add items
await cache.set("popular_item", data1)
await cache.set("rare_item", data2)

# Access popular item multiple times (increases frequency)
for _ in range(10):
    await cache.get("popular_item")

# Access rare item once
await cache.get("rare_item")

# When cache is full, rare_item will be evicted first
# popular_item stays due to higher frequency
```

#### LFU for Content Caching

```python
# LFU cache for content (articles, products, etc.)
content_cache = LFUCache(backend, max_size=5000, aging_factor=0.95)

async def get_article(article_id: str):
    """Get article with LFU caching."""
    article = await content_cache.get(f"article:{article_id}")
    if article is None:
        article = await load_article_from_db(article_id)
        if article:
            await content_cache.set(f"article:{article_id}", article)
    return article

# Popular articles stay in cache
# Unpopular articles get evicted
# Aging prevents old popular items from staying forever
```

### LFU Statistics

```python
stats = await cache.get_stats()
print(f"Strategy: {stats['strategy']}")
print(f"Max size: {stats['max_size']}")
print(f"Aging factor: {stats['aging_factor']}")
print(f"Tracked frequencies: {stats['tracked_frequencies']}")
print(f"Last aging: {stats['last_aging']}")
```

## Strategy Selection Guide

### When to Use TTL

**Best for:**

- Data with natural expiration (sessions, tokens, temporary data)
- Content that becomes stale over time
- APIs with rate limiting
- Cache warming scenarios

**Example Use Cases:**

```python
# User sessions (expire after inactivity)
ttl_cache = TTLCache(backend, default_ttl=1800)  # 30 minutes

# API rate limiting
await ttl_cache.set(f"rate_limit:{user_id}", request_count, ttl=3600)

# Temporary computations
await ttl_cache.set("expensive_calc", result, ttl=600)
```

### When to Use LRU

**Best for:**

- Dynamic workloads with temporal locality
- User-specific data (profiles, preferences)
- Recently accessed data is likely to be accessed again
- Memory-constrained environments

**Example Use Cases:**

```python
# User profiles (recent users more likely to return)
lru_cache = LRUCache(backend, max_size=10000)

# Database query results
await lru_cache.set(f"query:{hash}", results)

# File system cache
await lru_cache.set(f"file:{path}", content)
```

### When to Use LFU

**Best for:**

- Predictable access patterns
- Popular content that remains popular
- Skewed workloads (80/20 rule)
- Long-running applications

**Example Use Cases:**

```python
# Popular products/articles
lfu_cache = LFUCache(backend, max_size=5000, aging_factor=0.9)

# Configuration data
await lfu_cache.set("config:main", config)

# Static assets
await lfu_cache.set(f"asset:{name}", content)
```

## Advanced Patterns

### Hybrid Caching Strategy

```python
class HybridCache:
    """Combines multiple strategies for optimal performance."""
    
    def __init__(self, backend: CacheBackend):
        # Hot data: LFU for popular items
        self.hot_cache = LFUCache(backend, max_size=1000)
        
        # Warm data: LRU for recent items
        self.warm_cache = LRUCache(backend, max_size=5000)
        
        # Cold data: TTL for temporary items
        self.cold_cache = TTLCache(backend, default_ttl=3600)
    
    async def get(self, key: str, tier: str = "auto"):
        """Get from appropriate cache tier."""
        if tier == "hot" or tier == "auto":
            value = await self.hot_cache.get(key)
            if value is not None:
                return value
        
        if tier == "warm" or tier == "auto":
            value = await self.warm_cache.get(key)
            if value is not None:
                # Promote to hot cache if accessed frequently
                await self.hot_cache.set(key, value)
                return value
        
        if tier == "cold" or tier == "auto":
            return await self.cold_cache.get(key)
        
        return None
    
    async def set(self, key: str, value: Any, tier: str = "warm"):
        """Set in appropriate cache tier."""
        if tier == "hot":
            return await self.hot_cache.set(key, value)
        elif tier == "warm":
            return await self.warm_cache.set(key, value)
        elif tier == "cold":
            return await self.cold_cache.set(key, value)
        else:
            # Default to warm tier
            return await self.warm_cache.set(key, value)
```

### Adaptive Strategy Selection

```python
class AdaptiveCache:
    """Automatically selects best strategy based on access patterns."""
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self.strategies = {
            "ttl": TTLCache(backend, default_ttl=300),
            "lru": LRUCache(backend, max_size=1000),
            "lfu": LFUCache(backend, max_size=1000)
        }
        self.current_strategy = "lru"  # Default
        self.access_patterns = {}
        self.evaluation_interval = 1000  # Evaluate every 1000 operations
        self.operation_count = 0
    
    async def get(self, key: str):
        """Get with adaptive strategy selection."""
        self.operation_count += 1
        
        # Track access patterns
        self._track_access(key)
        
        # Evaluate and switch strategy if needed
        if self.operation_count % self.evaluation_interval == 0:
            await self._evaluate_strategy()
        
        return await self.strategies[self.current_strategy].get(key)
    
    async def set(self, key: str, value: Any, **kwargs):
        """Set with current strategy."""
        return await self.strategies[self.current_strategy].set(key, value, **kwargs)
    
    def _track_access(self, key: str):
        """Track access patterns for strategy evaluation."""
        if key not in self.access_patterns:
            self.access_patterns[key] = {
                "count": 0,
                "last_access": time.time(),
                "first_access": time.time()
            }
        
        pattern = self.access_patterns[key]
        pattern["count"] += 1
        pattern["last_access"] = time.time()
    
    async def _evaluate_strategy(self):
        """Evaluate and potentially switch strategy."""
        # Analyze access patterns
        total_accesses = sum(p["count"] for p in self.access_patterns.values())
        unique_keys = len(self.access_patterns)
        
        # Calculate metrics
        avg_frequency = total_accesses / unique_keys if unique_keys > 0 else 0
        temporal_locality = self._calculate_temporal_locality()
        
        # Strategy selection logic
        if temporal_locality > 0.7:
            # High temporal locality -> LRU
            self.current_strategy = "lru"
        elif avg_frequency > 5:
            # High frequency access -> LFU
            self.current_strategy = "lfu"
        else:
            # Default to TTL for mixed patterns
            self.current_strategy = "ttl"
    
    def _calculate_temporal_locality(self) -> float:
        """Calculate temporal locality score."""
        current_time = time.time()
        recent_threshold = 300  # 5 minutes
        
        recent_accesses = sum(
            1 for p in self.access_patterns.values()
            if current_time - p["last_access"] < recent_threshold
        )
        
        total_keys = len(self.access_patterns)
        return recent_accesses / total_keys if total_keys > 0 else 0
```

## Performance Monitoring

### Strategy Comparison

```python
async def compare_strategies():
    """Compare performance of different strategies."""
    backend = MemoryCache()
    
    strategies = {
        "TTL": TTLCache(backend, default_ttl=300),
        "LRU": LRUCache(backend, max_size=1000),
        "LFU": LFUCache(backend, max_size=1000)
    }
    
    # Test workload
    for strategy_name, strategy in strategies.items():
        start_time = time.time()
        
        # Simulate workload
        for i in range(1000):
            await strategy.set(f"key{i}", f"value{i}")
            if i % 2 == 0:  # 50% read rate
                await strategy.get(f"key{i//2}")
        
        end_time = time.time()
        stats = await strategy.get_stats()
        
        print(f"{strategy_name} Strategy:")
        print(f"  Time: {end_time - start_time:.3f}s")
        print(f"  Hit rate: {stats.get('hit_rate', 'N/A')}")
        print(f"  Memory usage: {stats.get('memory_usage', 'N/A')}")
        print()
```

## Best Practices

### 1. Choose Strategy Based on Access Patterns

```python
# ✅ Good: Match strategy to workload
# For user sessions (temporal locality)
session_cache = LRUCache(backend, max_size=10000)

# For popular content (frequency matters)
content_cache = LFUCache(backend, max_size=5000)

# For temporary data (natural expiration)
temp_cache = TTLCache(backend, default_ttl=300)
```

### 2. Monitor and Tune Parameters

```python
# ✅ Good: Regular monitoring
async def monitor_cache_performance():
    stats = await cache.get_stats()
    
    hit_rate = stats.get('hit_rate', 0)
    if hit_rate < 0.8:  # Less than 80% hit rate
        print("Consider increasing cache size or adjusting strategy")
    
    memory_usage = stats.get('memory_usage', 0)
    if memory_usage > 0.9:  # Over 90% memory usage
        print("Consider reducing cache size or implementing eviction")
```

### 3. Use Appropriate Sizing

```python
# ✅ Good: Size based on available memory and workload
import psutil

available_memory = psutil.virtual_memory().available
cache_memory_limit = available_memory * 0.1  # Use 10% of available memory

# Estimate items based on average item size
avg_item_size = 1024  # 1KB average
max_items = int(cache_memory_limit / avg_item_size)

cache = LRUCache(backend, max_size=max_items)
```

### 4. Combine Strategies When Appropriate

```python
# ✅ Good: Use multiple strategies for different data types
class MultiTierCache:
    def __init__(self):
        # Fast tier: Small, frequently accessed data
        self.l1_cache = LFUCache(memory_backend, max_size=100)
        
        # Medium tier: Recent data
        self.l2_cache = LRUCache(memory_backend, max_size=1000)
        
        # Slow tier: Large, less frequent data with TTL
        self.l3_cache = TTLCache(redis_backend, default_ttl=3600)
```

## Next Steps

- Learn about [Cache Backends](backends.md) for storage implementation details
- Explore [Cache Manager](../manager.md) for high-level cache management
- Check [Cache Performance](../../performance/caching.md) for optimization techniques
