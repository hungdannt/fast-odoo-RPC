"""
Cache manager for OdooFlow.

This module provides the main cache management interface,
coordinating between different backends and strategies.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union, Type
import logging

from .backends import CacheBackend, MemoryCache, RedisCache
from .strategies import CacheStrategy, TTLCache, LRUCache, LFUCache
from .keys import CacheKey, make_cache_key, make_model_cache_key, make_query_cache_key
from .exceptions import CacheError, CacheBackendError

logger = logging.getLogger(__name__)


class CacheManager:
    """Main cache manager for OdooFlow.

    This class provides a unified interface for caching operations,
    supporting multiple backends and strategies with intelligent
    cache key management and performance optimization.

    Features:
    - Multiple cache backends (Memory, Redis)
    - Multiple cache strategies (TTL, LRU, LFU)
    - Automatic cache key generation
    - Cache invalidation patterns
    - Performance monitoring
    - Multi-level caching

    Example:
        >>> # Setup cache manager
        >>> cache_manager = CacheManager()
        >>> await cache_manager.setup_memory_cache(max_size=1000, default_ttl=300)
        >>>
        >>> # Cache query results
        >>> key = make_query_cache_key("res.partner", [("is_company", "=", True)])
        >>> await cache_manager.set(key, query_results, ttl=60)
        >>>
        >>> # Retrieve cached results
        >>> cached_results = await cache_manager.get(key)
    """

    def __init__(self):
        """Initialize cache manager."""
        self.backends: Dict[str, CacheBackend] = {}
        self.strategies: Dict[str, CacheStrategy] = {}
        self.default_backend = "memory"
        self.default_strategy = "ttl"

        # Cache configuration
        self.config = {
            "enabled": True,
            "default_ttl": 300,  # 5 minutes
            "max_key_length": 250,
            "namespace": "odooflow",
        }

        # Statistics
        self.stats = {
            "total_gets": 0,
            "total_sets": 0,
            "total_deletes": 0,
            "total_hits": 0,
            "total_misses": 0,
        }

    async def setup_memory_cache(
        self,
        name: str = "memory",
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        strategy: str = "ttl",
    ) -> None:
        """Setup in-memory cache backend.

        Args:
            name: Backend name
            max_size: Maximum cache size
            default_ttl: Default TTL in seconds
            strategy: Cache strategy ("ttl", "lru", "lfu")
        """
        # Create memory backend
        backend = MemoryCache(
            max_size=max_size, default_ttl=default_ttl or self.config["default_ttl"]
        )

        # Create strategy
        cache_strategy = self._create_strategy(strategy, backend, max_size=max_size)

        # Register
        self.backends[name] = backend
        self.strategies[name] = cache_strategy

        if name == "memory":
            self.default_backend = name

    def add_backend(self, name: str, backend: CacheBackend) -> None:
        """Add a cache backend.

        Args:
            name: Backend name
            backend: Cache backend instance
        """
        self.backends[name] = backend

    def add_strategy(self, name: str, strategy: CacheStrategy) -> None:
        """Add a cache strategy.

        Args:
            name: Strategy name
            strategy: Cache strategy instance
        """
        self.strategies[name] = strategy

    def set_default_backend(self, name: str) -> None:
        """Set the default backend.

        Args:
            name: Backend name
        """
        if name in self.backends:
            self.default_backend = name
        else:
            raise ValueError(f"Backend '{name}' not found")

    async def setup_redis_cache(
        self,
        name: str = "redis",
        url: str = "redis://localhost:6379/0",
        namespace: str = None,
        serializer: str = "json",
        strategy: str = "ttl",
        max_connections: int = 10,
        enable_fallback: bool = True,
        circuit_breaker_threshold: int = 5,
        retry_attempts: int = 3,
        **kwargs
    ) -> None:
        """Setup enhanced Redis cache backend.

        Args:
            name: Backend name
            url: Redis connection URL
            namespace: Cache namespace
            serializer: Serialization method
            strategy: Cache strategy
            max_connections: Maximum connections
            enable_fallback: Enable fallback to memory cache
            circuit_breaker_threshold: Circuit breaker failure threshold
            retry_attempts: Number of retry attempts
            **kwargs: Additional Redis backend parameters
        """
        # Create enhanced Redis backend
        backend = RedisCache(
            url=url,
            namespace=namespace or self.config["namespace"],
            serializer=serializer,
            max_connections=max_connections,
            enable_fallback=enable_fallback,
            circuit_breaker_threshold=circuit_breaker_threshold,
            retry_attempts=retry_attempts,
            **kwargs
        )

        # Connect to Redis
        await backend.connect()

        # Create strategy
        cache_strategy = self._create_strategy(strategy, backend)

        # Register
        self.backends[name] = backend
        self.strategies[name] = cache_strategy

        logger.info(f"Setup Redis cache '{name}' with {strategy} strategy")

    def _create_strategy(
        self, strategy_type: str, backend: CacheBackend, **kwargs
    ) -> CacheStrategy:
        """Create a cache strategy instance.

        Args:
            strategy_type: Strategy type ("ttl", "lru", "lfu")
            backend: Cache backend
            **kwargs: Strategy-specific arguments

        Returns:
            CacheStrategy instance
        """
        if strategy_type == "ttl":
            return TTLCache(
                backend,
                default_ttl=kwargs.get("default_ttl", self.config["default_ttl"]),
            )
        elif strategy_type == "lru":
            return LRUCache(backend, max_size=kwargs.get("max_size", 1000))
        elif strategy_type == "lfu":
            return LFUCache(backend, max_size=kwargs.get("max_size", 1000))
        else:
            raise CacheError(f"Unknown cache strategy: {strategy_type}")

    async def get(
        self, key: Union[str, CacheKey], backend: Optional[str] = None
    ) -> Optional[Any]:
        """Get a value from cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            Cached value or None
        """
        if not self.config["enabled"]:
            return None

        backend_name = backend or self.default_backend
        strategy = self.strategies.get(backend_name)

        if not strategy:
            logger.warning(f"Cache backend '{backend_name}' not found")
            return None

        try:
            self.stats["total_gets"] += 1
            value = await strategy.get(key)

            if value is not None:
                self.stats["total_hits"] += 1
            else:
                self.stats["total_misses"] += 1

            return value

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: Union[str, CacheKey],
        value: Any,
        ttl: Optional[int] = None,
        backend: Optional[str] = None,
    ) -> bool:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            backend: Backend name (uses default if None)

        Returns:
            True if successful
        """
        if not self.config["enabled"]:
            return False

        backend_name = backend or self.default_backend
        strategy = self.strategies.get(backend_name)

        if not strategy:
            logger.warning(f"Cache backend '{backend_name}' not found")
            return False

        try:
            self.stats["total_sets"] += 1
            return await strategy.set(key, value, ttl=ttl)

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(
        self, key: Union[str, CacheKey], backend: Optional[str] = None
    ) -> bool:
        """Delete a value from cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            True if key existed and was deleted
        """
        if not self.config["enabled"]:
            return False

        backend_name = backend or self.default_backend
        strategy = self.strategies.get(backend_name)

        if not strategy:
            return False

        try:
            self.stats["total_deletes"] += 1
            return await strategy.delete(key)

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def exists(
        self, key: Union[str, CacheKey], backend: Optional[str] = None
    ) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            True if key exists
        """
        value = await self.get(key, backend)
        return value is not None

    async def clear(self, backend: Optional[str] = None) -> bool:
        """Clear cache.

        Args:
            backend: Backend name (clears all if None)

        Returns:
            True if successful
        """
        if backend:
            strategy = self.strategies.get(backend)
            if strategy:
                return await strategy.clear()
            return False
        else:
            # Clear all backends
            results = []
            for strategy in self.strategies.values():
                results.append(await strategy.clear())
            return all(results)

    async def invalidate_pattern(
        self, pattern: str, backend: Optional[str] = None
    ) -> int:
        """Invalidate cache keys matching a pattern.

        Args:
            pattern: Key pattern (supports wildcards)
            backend: Backend name (uses default if None)

        Returns:
            Number of keys invalidated
        """
        if not self.config["enabled"]:
            return 0

        backend_name = backend or self.default_backend
        strategy = self.strategies.get(backend_name)

        if not strategy:
            logger.warning(f"Cache backend '{backend_name}' not found")
            return 0

        try:
            # For memory cache, we can iterate through keys
            backend = getattr(strategy, "backend", strategy)

            # Check for MemoryCache with _data attribute
            if hasattr(backend, "_data") and hasattr(backend._data, "keys"):
                import fnmatch

                keys_to_delete = []

                for key in backend._data.keys():
                    if fnmatch.fnmatch(str(key), pattern):
                        keys_to_delete.append(key)

                for key in keys_to_delete:
                    await strategy.delete(key)

                return len(keys_to_delete)

            # Check for other cache implementations with cache attribute
            elif hasattr(backend, "cache") and hasattr(backend.cache, "keys"):
                import fnmatch

                keys_to_delete = []

                for key in backend.cache.keys():
                    if fnmatch.fnmatch(str(key), pattern):
                        keys_to_delete.append(key)

                for key in keys_to_delete:
                    await strategy.delete(key)

                return len(keys_to_delete)

            # For Redis cache, use SCAN with pattern
            elif hasattr(strategy, "redis"):
                count = 0
                async for key in strategy.redis.scan_iter(match=pattern):
                    await strategy.delete(key)
                    count += 1
                return count

            else:
                logger.warning(
                    f"Pattern invalidation not supported for backend '{backend_name}'"
                )
                return 0

        except Exception as e:
            logger.error(f"Pattern invalidation error: {e}")
            return 0

    async def invalidate_model(self, model: str, backend: Optional[str] = None) -> int:
        """Invalidate all cache entries for a model.

        Args:
            model: Odoo model name
            backend: Backend name (uses default if None)

        Returns:
            Number of keys invalidated
        """
        pattern = f"{model}:*"
        return await self.invalidate_pattern(pattern, backend)

    async def get_stats(self, backend: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics.

        Args:
            backend: Backend name (all backends if None)

        Returns:
            Dictionary with cache statistics
        """
        if backend:
            strategy = self.strategies.get(backend)
            if strategy:
                backend_stats = await strategy.get_stats()
                backend_stats.update(self.stats)
                return backend_stats
            return {}
        else:
            # Aggregate stats from all backends
            all_stats = {"manager": self.stats, "backends": {}}

            # Initialize aggregated totals
            total_hits = 0
            total_misses = 0
            total_size = 0

            for name, strategy in self.strategies.items():
                backend_stats = await strategy.get_stats()
                all_stats["backends"][name] = backend_stats

                # Aggregate totals
                total_hits += backend_stats.get("hits", 0)
                total_misses += backend_stats.get("misses", 0)
                total_size += backend_stats.get("size", 0)

            # Add aggregated totals
            all_stats["total_hits"] = total_hits
            all_stats["total_misses"] = total_misses
            all_stats["total_size"] = total_size

            return all_stats

    def enable(self) -> None:
        """Enable caching."""
        self.config["enabled"] = True
        logger.info("Cache enabled")

    def disable(self) -> None:
        """Disable caching."""
        self.config["enabled"] = False
        logger.info("Cache disabled")

    def is_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self.config["enabled"]

    async def close(self) -> None:
        """Close all cache backends."""
        for backend in self.backends.values():
            if hasattr(backend, "close"):
                await backend.close()

        logger.info("Cache manager closed")

    # Convenience methods for common cache operations

    async def cache_query_result(
        self,
        model: str,
        domain: List[Any],
        result: Any,
        fields: Optional[List[str]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache a query result.

        Args:
            model: Odoo model name
            domain: Search domain
            result: Query result to cache
            fields: Fields included in result
            ttl: Time to live

        Returns:
            True if cached successfully
        """
        key = make_query_cache_key(model, domain, fields)
        return await self.set(key, result, ttl=ttl)

    async def get_cached_query_result(
        self, model: str, domain: List[Any], fields: Optional[List[str]] = None
    ) -> Optional[Any]:
        """Get a cached query result.

        Args:
            model: Odoo model name
            domain: Search domain
            fields: Fields included in result

        Returns:
            Cached result or None
        """
        key = make_query_cache_key(model, domain, fields)
        return await self.get(key)

    async def cache_model_record(
        self,
        model: str,
        record_id: Union[int, List[int]],
        record_data: Any,
        fields: Optional[List[str]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache a model record.

        Args:
            model: Odoo model name
            record_id: Record ID or list of IDs
            record_data: Record data to cache
            fields: Fields included in data
            ttl: Time to live

        Returns:
            True if cached successfully
        """
        key = make_model_cache_key(model, record_id, fields)
        return await self.set(key, record_data, ttl=ttl)

    async def get_cached_model_record(
        self,
        model: str,
        record_id: Union[int, List[int]],
        fields: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Get a cached model record.

        Args:
            model: Odoo model name
            record_id: Record ID or list of IDs
            fields: Fields included in data

        Returns:
            Cached record data or None
        """
        key = make_model_cache_key(model, record_id, fields)
        return await self.get(key)
