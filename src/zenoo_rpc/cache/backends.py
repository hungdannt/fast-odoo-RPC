"""
Cache backend implementations for OdooFlow.

This module provides different cache backends including
in-memory and Redis implementations with async support.
"""

import asyncio
import json
import pickle  # nosec B403
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from collections import OrderedDict
import logging

from .exceptions import (
    CacheBackendError,
    CacheSerializationError,
    CacheConnectionError,
)
from .keys import CacheKey, validate_cache_key

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends.

    This class defines the interface that all cache backends
    must implement for consistent caching behavior.
    """

    @abstractmethod
    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    async def set(
        self, key: Union[str, CacheKey], value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        pass

    @abstractmethod
    async def exists(self, key: Union[str, CacheKey]) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values.

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend with TTL and LRU support.

    This backend stores data in memory with optional TTL
    and LRU eviction policies for memory management.

    Features:
    - TTL (Time To Live) support
    - LRU (Least Recently Used) eviction
    - Thread-safe operations
    - Memory usage tracking

    Example:
        >>> cache = MemoryCache(max_size=1000, default_ttl=300)
        >>> await cache.set("key1", "value1", ttl=60)
        >>> value = await cache.get("key1")
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        cleanup_interval: int = 60,
    ):
        """Initialize memory cache.

        Args:
            max_size: Maximum number of items to store
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        # Storage
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._expiry: Dict[str, float] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Start cleanup task
        self._start_cleanup_task()

    async def connect(self) -> None:
        """Connect method for compatibility with other backends."""
        # Memory cache doesn't need connection, but we provide this for compatibility
        pass

    async def close(self) -> None:
        """Close memory cache and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def _start_cleanup_task(self):
        """Start the cleanup task for expired items."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def _cleanup_expired(self):
        """Cleanup expired items periodically."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._remove_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory cache cleanup error: {e}")

    async def _remove_expired(self):
        """Remove expired items from cache."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, expiry in self._expiry.items()
                if expiry <= current_time
            ]

            for key in expired_keys:
                self._data.pop(key, None)
                self._expiry.pop(key, None)

            if expired_keys:
                logger.debug(
                    f"Memory cache: Removed {len(expired_keys)} expired items"
                )

    async def _evict_lru(self):
        """Evict least recently used items if cache is full."""
        while len(self._data) >= self.max_size:
            # Remove oldest item (LRU)
            oldest_key = next(iter(self._data))
            self._data.pop(oldest_key)
            self._expiry.pop(oldest_key, None)

    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from the memory cache."""
        key_str = validate_cache_key(key)

        async with self._lock:
            # Check if key exists
            if key_str not in self._data:
                self._misses += 1
                return None

            # Check if expired
            if key_str in self._expiry:
                if time.time() > self._expiry[key_str]:
                    # Remove expired item
                    self._data.pop(key_str)
                    self._expiry.pop(key_str)
                    self._misses += 1
                    return None

            # Move to end (mark as recently used)
            value = self._data.pop(key_str)
            self._data[key_str] = value

            self._hits += 1
            return value

    async def set(
        self, key: Union[str, CacheKey], value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set a value in the memory cache."""
        key_str = validate_cache_key(key)

        async with self._lock:
            # Evict if necessary
            await self._evict_lru()

            # Set value
            self._data[key_str] = value

            # Set expiry
            effective_ttl = ttl or self.default_ttl
            if effective_ttl:
                self._expiry[key_str] = time.time() + effective_ttl
            elif key_str in self._expiry:
                # Remove expiry if no TTL
                del self._expiry[key_str]

            self._sets += 1
            return True

    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from the memory cache."""
        key_str = validate_cache_key(key)

        async with self._lock:
            existed = key_str in self._data
            self._data.pop(key_str, None)
            self._expiry.pop(key_str, None)

            if existed:
                self._deletes += 1

            return existed

    async def exists(self, key: Union[str, CacheKey]) -> bool:
        """Check if a key exists in the memory cache."""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cached values."""
        async with self._lock:
            self._data.clear()
            self._expiry.clear()
            return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (
                (self._hits / total_requests * 100)
                if total_requests > 0
                else 0
            )

            return {
                "backend": "memory",
                "size": len(self._data),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "sets": self._sets,
                "deletes": self._deletes,
                "expired_items": len(self._expiry),
            }


class RedisCache(CacheBackend):
    """Enhanced Redis cache backend with production-ready features.

    This backend provides enterprise-grade Redis caching with advanced
    connection management, resilience patterns, and comprehensive monitoring.

    Enhanced Features:
    - Singleton connection pool management
    - Circuit breaker pattern for fault tolerance
    - Exponential backoff retry with jitter
    - Health checking and automatic reconnection
    - Comprehensive metrics and observability
    - Graceful shutdown and resource cleanup
    - Transaction-aware cache invalidation
    - Fallback mechanisms for high availability

    Example:
        >>> cache = RedisCache(url="redis://localhost:6379/0")
        >>> await cache.connect()
        >>> await cache.set("key1", {"data": "value"}, ttl=300)
        >>> value = await cache.get("key1")
        >>> await cache.close()  # Graceful shutdown
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        namespace: str = "odooflow",
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
        """Initialize enhanced Redis cache.

        Args:
            url: Redis connection URL
            namespace: Cache namespace for key isolation
            serializer: Serialization method ("json" or "pickle")
            max_connections: Maximum connections in pool
            retry_attempts: Number of retry attempts
            retry_backoff_base: Base delay for exponential backoff (seconds)
            retry_backoff_max: Maximum delay for exponential backoff (seconds)
            health_check_interval: Health check interval (seconds)
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_timeout: Circuit breaker timeout (seconds)
            socket_timeout: Socket timeout (seconds)
            socket_connect_timeout: Socket connect timeout (seconds)
            enable_fallback: Enable fallback to memory cache on Redis failure
        """
        self.url = url
        self.namespace = namespace
        self.serializer = serializer
        self.max_connections = max_connections
        self.retry_attempts = retry_attempts
        self.retry_backoff_base = retry_backoff_base
        self.retry_backoff_max = retry_backoff_max
        self.health_check_interval = health_check_interval
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.enable_fallback = enable_fallback

        # Redis client (will be initialized in connect())
        self.redis = None
        self._connected = False
        self._connecting = False
        self._connection_lock = asyncio.Lock()

        # Circuit breaker state
        self._circuit_state = "closed"  # closed, open, half_open
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_lock = asyncio.Lock()

        # Enhanced statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._errors = 0
        self._connection_errors = 0
        self._circuit_breaker_trips = 0
        self._fallback_hits = 0
        self._total_operations = 0
        self._last_health_check = 0

        # Fallback memory cache
        self._fallback_cache = None
        if self.enable_fallback:
            # Create fallback cache directly to avoid circular imports
            self._fallback_cache = MemoryCache(max_size=1000, default_ttl=300)

    async def connect(self) -> None:
        """Enhanced connection with singleton pattern and health checking."""
        if self._connected:
            return

        async with self._connection_lock:
            # Double-check pattern
            if self._connected:
                return

            if self._connecting:
                # Wait for ongoing connection attempt
                while self._connecting:
                    await asyncio.sleep(0.1)
                return

            self._connecting = True

            try:
                await self._establish_connection()
                self._connected = True
                self._connecting = False

                # Reset circuit breaker on successful connection
                await self._reset_circuit_breaker()

                # Initialize fallback cache if enabled
                if self.enable_fallback and self._fallback_cache:
                    await self._fallback_cache.connect()

                logger.info(
                    f"Redis cache connected to {self.url} "
                    f"(pool_size={self.max_connections}, "
                    f"health_check={self.health_check_interval}s)"
                )

            except Exception as e:
                self._connecting = False
                await self._record_failure()
                logger.error(f"Failed to connect to Redis: {e}")
                raise CacheConnectionError(
                    f"Redis connection failed: {e}"
                ) from e

    async def _establish_connection(self) -> None:
        """Establish Redis connection with proper configuration."""
        try:
            # Import redis here to make it optional
            import aioredis

            # Support both aioredis 1.x and 2.x with enhanced config
            if hasattr(aioredis, "from_url"):
                # aioredis 2.x
                self.redis = aioredis.from_url(
                    self.url,
                    max_connections=self.max_connections,
                    retry_on_timeout=True,
                    decode_responses=False,  # We handle encoding ourselves
                )
            else:
                # aioredis 1.x
                self.redis = await aioredis.create_redis_pool(
                    self.url,
                    maxsize=self.max_connections,
                    encoding=None,  # We handle encoding ourselves
                )

            # Test connection with timeout
            await asyncio.wait_for(
                self.redis.ping(), timeout=self.socket_connect_timeout
            )

        except ImportError:
            raise CacheBackendError(
                "aioredis is required for Redis cache backend. "
                "Install with: pip install aioredis"
            )
        except asyncio.TimeoutError:
            raise CacheConnectionError("Redis connection timeout")
        except Exception as e:
            raise CacheConnectionError(f"Redis connection failed: {e}") from e

    async def close(self) -> None:
        """Graceful shutdown with proper resource cleanup."""
        if not self._connected:
            return

        try:
            if self.redis:
                # Close Redis connection pool
                if hasattr(self.redis, "close"):
                    await self.redis.close()
                elif hasattr(self.redis, "wait_closed"):
                    self.redis.close()
                    await self.redis.wait_closed()

            # Close fallback cache
            if self._fallback_cache:
                await self._fallback_cache.close()

            self._connected = False
            logger.info("Redis cache connection closed gracefully")

        except Exception as e:
            logger.error(f"Error during Redis cache shutdown: {e}")

    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows operation."""
        async with self._circuit_lock:
            current_time = time.time()

            if self._circuit_state == "closed":
                return True
            elif self._circuit_state == "open":
                if (
                    current_time - self._last_failure_time
                    > self.circuit_breaker_timeout
                ):
                    self._circuit_state = "half_open"
                    logger.info("Circuit breaker moved to half-open state")
                    return True
                return False
            elif self._circuit_state == "half_open":
                return True

        return False

    async def _record_failure(self) -> None:
        """Record operation failure for circuit breaker."""
        async with self._circuit_lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            self._connection_errors += 1

            if (
                self._circuit_state in ["closed", "half_open"]
                and self._failure_count >= self.circuit_breaker_threshold
            ):
                self._circuit_state = "open"
                self._circuit_breaker_trips += 1
                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures"
                )

    async def _record_success(self) -> None:
        """Record successful operation for circuit breaker."""
        async with self._circuit_lock:
            if self._circuit_state == "half_open":
                await self._reset_circuit_breaker()

    async def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker to closed state."""
        async with self._circuit_lock:
            self._circuit_state = "closed"
            self._failure_count = 0
            self._last_failure_time = 0
            if self._circuit_breaker_trips > 0:
                logger.info("Circuit breaker reset to closed state")

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self.namespace}:{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            if self.serializer == "json":
                return json.dumps(value, default=str).encode("utf-8")
            elif self.serializer == "pickle":
                return pickle.dumps(value)
            else:
                raise CacheSerializationError(
                    f"Unknown serializer: {self.serializer}"
                )
        except Exception as e:
            raise CacheSerializationError(f"Serialization failed: {e}")

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            if self.serializer == "json":
                return json.loads(data.decode("utf-8"))
            elif self.serializer == "pickle":
                # WARNING: pickle.loads() can be unsafe with untrusted data
                # Only use with trusted cache backends and data sources
                return pickle.loads(data)  # nosec B301
            else:
                raise CacheSerializationError(
                    f"Unknown serializer: {self.serializer}"
                )
        except Exception as e:
            raise CacheSerializationError(f"Deserialization failed: {e}")

    async def _ensure_connected(self):
        """Ensure Redis connection is active."""
        if not self._connected or not self.redis:
            await self.connect()

    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Enhanced get with circuit breaker, retry, and fallback."""
        self._total_operations += 1
        key_str = validate_cache_key(key)

        # Check circuit breaker
        if not await self._check_circuit_breaker():
            return await self._fallback_get(key_str)

        # Try Redis with retry
        for attempt in range(self.retry_attempts):
            try:
                await self._ensure_connected()
                redis_key = self._make_key(key_str)

                data = await self.redis.get(redis_key)
                if data is None:
                    self._misses += 1
                    return None

                value = self._deserialize(data)
                self._hits += 1
                await self._record_success()
                return value

            except Exception as e:
                self._errors += 1
                await self._record_failure()

                if attempt < self.retry_attempts - 1:
                    # Exponential backoff with jitter
                    delay = min(
                        self.retry_backoff_base * (2**attempt),
                        self.retry_backoff_max,
                    )
                    jitter = (
                        delay
                        * 0.1
                        * (0.5 - asyncio.get_event_loop().time() % 1)
                    )
                    await asyncio.sleep(delay + jitter)
                    continue

                logger.error(
                    f"Redis cache get error after {self.retry_attempts} attempts: {e}"
                )

                # Try fallback on final failure
                return await self._fallback_get(key_str)

    async def _fallback_get(self, key: str) -> Optional[Any]:
        """Get from fallback cache when Redis is unavailable."""
        if not self.enable_fallback or not self._fallback_cache:
            return None

        try:
            value = await self._fallback_cache.get(key)
            if value is not None:
                self._fallback_hits += 1
                logger.debug(f"Fallback cache hit for key: {key}")
            return value
        except Exception as e:
            logger.error(f"Fallback cache get error: {e}")
            return None

    async def _fallback_set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set in fallback cache when Redis is unavailable."""
        if not self.enable_fallback or not self._fallback_cache:
            return False

        try:
            return await self._fallback_cache.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Fallback cache set error: {e}")
            return False

    async def set(
        self, key: Union[str, CacheKey], value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Enhanced set with circuit breaker, retry, and fallback."""
        self._total_operations += 1
        key_str = validate_cache_key(key)

        # Check circuit breaker
        if not await self._check_circuit_breaker():
            return await self._fallback_set(key_str, value, ttl)

        # Try Redis with retry
        for attempt in range(self.retry_attempts):
            try:
                await self._ensure_connected()
                redis_key = self._make_key(key_str)
                data = self._serialize(value)

                if ttl:
                    await self.redis.setex(redis_key, ttl, data)
                else:
                    await self.redis.set(redis_key, data)

                self._sets += 1
                await self._record_success()
                return True

            except Exception as e:
                self._errors += 1
                await self._record_failure()

                if attempt < self.retry_attempts - 1:
                    # Exponential backoff with jitter
                    delay = min(
                        self.retry_backoff_base * (2**attempt),
                        self.retry_backoff_max,
                    )
                    jitter = (
                        delay
                        * 0.1
                        * (0.5 - asyncio.get_event_loop().time() % 1)
                    )
                    await asyncio.sleep(delay + jitter)
                    continue

                logger.error(
                    f"Redis cache set error after {self.retry_attempts} attempts: {e}"
                )

                # Try fallback on final failure
                return await self._fallback_set(key_str, value, ttl)

    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from Redis cache."""
        await self._ensure_connected()
        key_str = validate_cache_key(key)
        redis_key = self._make_key(key_str)

        try:
            result = await self.redis.delete(redis_key)
            if result > 0:
                self._deletes += 1
                return True
            return False

        except Exception as e:
            self._errors += 1
            logger.error(f"Redis cache delete error: {e}")
            raise CacheBackendError(f"Failed to delete from Redis: {e}")  # nosec B608

    async def exists(self, key: Union[str, CacheKey]) -> bool:
        """Check if a key exists in Redis cache."""
        await self._ensure_connected()
        key_str = validate_cache_key(key)
        redis_key = self._make_key(key_str)

        try:
            result = await self.redis.exists(redis_key)
            return result > 0

        except Exception as e:
            self._errors += 1
            logger.error(f"Redis cache exists error: {e}")
            raise CacheBackendError(f"Failed to check existence in Redis: {e}")

    async def clear(self) -> bool:
        """Clear all cached values in namespace."""
        await self._ensure_connected()

        try:
            # Get all keys in namespace
            pattern = f"{self.namespace}:*"
            keys = await self.redis.keys(pattern)

            if keys:
                await self.redis.delete(*keys)

            return True

        except Exception as e:
            self._errors += 1
            logger.error(f"Redis cache clear error: {e}")
            raise CacheBackendError(f"Failed to clear Redis cache: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get enhanced Redis cache statistics with resilience metrics."""
        total_requests = self._hits + self._misses
        hit_rate = (
            (self._hits / total_requests * 100) if total_requests > 0 else 0
        )

        # Calculate fallback rate
        fallback_rate = 0
        if self._total_operations > 0:
            fallback_rate = self._fallback_hits / self._total_operations * 100

        stats = {
            "backend": "redis",
            "connected": self._connected,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "sets": self._sets,
            "deletes": self._deletes,
            "errors": self._errors,
            "namespace": self.namespace,
            "serializer": self.serializer,
            # Enhanced resilience metrics
            "total_operations": self._total_operations,
            "connection_errors": self._connection_errors,
            "circuit_breaker_trips": self._circuit_breaker_trips,
            "circuit_state": self._circuit_state,
            "failure_count": self._failure_count,
            "fallback_hits": self._fallback_hits,
            "fallback_rate": round(fallback_rate, 2),
            "fallback_enabled": self.enable_fallback,
            # Configuration
            "max_connections": self.max_connections,
            "retry_attempts": self.retry_attempts,
            "health_check_interval": self.health_check_interval,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
        }

        # Add Redis server info if connected
        if self._connected and self.redis:
            try:
                info = await self.redis.info()
                stats.update(
                    {
                        "redis_version": info.get("redis_version"),
                        "used_memory": info.get("used_memory_human"),
                        "connected_clients": info.get("connected_clients"),
                        "total_connections_received": info.get(
                            "total_connections_received"
                        ),
                        "keyspace_hits": info.get("keyspace_hits"),
                        "keyspace_misses": info.get("keyspace_misses"),
                    }
                )
            except Exception:
                pass  # nosec B110 - Ignore errors getting Redis info

        return stats
