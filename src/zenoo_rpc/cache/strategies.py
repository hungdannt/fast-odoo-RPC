"""
Cache strategies for OdooFlow.

This module provides different caching strategies including
TTL (Time To Live), LRU (Least Recently Used), and LFU (Least Frequently Used).
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from collections import OrderedDict, defaultdict

from .backends import CacheBackend
from .keys import CacheKey, validate_cache_key
from .exceptions import CacheError


class CacheStrategy(ABC):
    """Abstract base class for cache strategies.

    Cache strategies define how cached data is managed,
    including eviction policies and expiration handling.
    """

    def __init__(self, backend: CacheBackend):
        """Initialize cache strategy.

        Args:
            backend: Cache backend to use
        """
        self.backend = backend

    @abstractmethod
    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from cache with strategy-specific logic."""
        pass

    @abstractmethod
    async def set(self, key: Union[str, CacheKey], value: Any, **kwargs) -> bool:
        """Set a value in cache with strategy-specific logic."""
        pass

    @abstractmethod
    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class TTLCache(CacheStrategy):
    """Time To Live (TTL) cache strategy.

    This strategy automatically expires cached items after
    a specified time period. Items are removed when they
    expire or when explicitly accessed after expiration.

    Features:
    - Automatic expiration based on TTL
    - Configurable default TTL
    - Per-item TTL override
    - Lazy expiration on access

    Example:
        >>> cache = TTLCache(backend, default_ttl=300)  # 5 minutes
        >>> await cache.set("key1", "value1", ttl=60)   # 1 minute override
        >>> value = await cache.get("key1")
    """

    def __init__(
        self, backend: CacheBackend, default_ttl: int = 300, cleanup_interval: int = 60
    ):
        """Initialize TTL cache strategy.

        Args:
            backend: Cache backend
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        super().__init__(backend)
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        # Track expiration times (for backends that don't support TTL natively)
        self._expiry_times: Dict[str, float] = {}
        self._last_cleanup = time.time()

    async def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key not in self._expiry_times:
            return False

        return time.time() > self._expiry_times[key]

    async def _cleanup_expired(self):
        """Clean up expired items if needed."""
        current_time = time.time()

        # Only cleanup if interval has passed
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        expired_keys = [
            key for key, expiry in self._expiry_times.items() if expiry <= current_time
        ]

        for key in expired_keys:
            await self.backend.delete(key)
            del self._expiry_times[key]

        self._last_cleanup = current_time

    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from TTL cache."""
        try:
            key_str = validate_cache_key(key)

            # Check if expired
            if await self._is_expired(key_str):
                await self.delete(key)
                return None

            # Trigger cleanup if needed
            await self._cleanup_expired()

            return await self.backend.get(key)
        except Exception as e:
            from .exceptions import CacheBackendError

            raise CacheBackendError(
                f"Error getting value from TTL cache for key '{key}': {e}"
            ) from e

    async def set(
        self, key: Union[str, CacheKey], value: Any, ttl: Optional[int] = None, **kwargs
    ) -> bool:
        """Set a value in TTL cache."""
        key_str = validate_cache_key(key)
        effective_ttl = ttl or self.default_ttl

        # Set expiration time
        if effective_ttl:
            self._expiry_times[key_str] = time.time() + effective_ttl

        # Use backend's TTL if supported, otherwise track manually
        return await self.backend.set(key, value, ttl=effective_ttl)

    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from TTL cache."""
        key_str = validate_cache_key(key)

        # Remove from expiry tracking
        self._expiry_times.pop(key_str, None)

        return await self.backend.delete(key)

    async def clear(self) -> bool:
        """Clear all cached values."""
        self._expiry_times.clear()
        return await self.backend.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get TTL cache statistics."""
        backend_stats = await self.backend.get_stats()

        # Add TTL-specific stats
        current_time = time.time()
        expired_count = sum(
            1 for expiry in self._expiry_times.values() if expiry <= current_time
        )

        backend_stats.update(
            {
                "strategy": "ttl",
                "default_ttl": self.default_ttl,
                "tracked_expiries": len(self._expiry_times),
                "expired_items": expired_count,
            }
        )

        return backend_stats


class LRUCache(CacheStrategy):
    """Least Recently Used (LRU) cache strategy.

    This strategy evicts the least recently used items when
    the cache reaches its maximum size. Access order is
    tracked to determine which items to evict.

    Features:
    - LRU eviction policy
    - Configurable maximum size
    - Access order tracking
    - Efficient O(1) operations

    Example:
        >>> cache = LRUCache(backend, max_size=1000)
        >>> await cache.set("key1", "value1")
        >>> value = await cache.get("key1")  # Marks as recently used
    """

    def __init__(self, backend: CacheBackend, max_size: int = 1000):
        """Initialize LRU cache strategy.

        Args:
            backend: Cache backend
            max_size: Maximum number of items
        """
        super().__init__(backend)
        self.max_size = max_size

        # Track access order
        self._access_order: OrderedDict[str, float] = OrderedDict()

    async def _update_access(self, key: str):
        """Update access time for a key."""
        current_time = time.time()

        # Remove and re-add to move to end
        self._access_order.pop(key, None)
        self._access_order[key] = current_time

    async def _evict_lru(self):
        """Evict least recently used items if over limit."""
        while len(self._access_order) > self.max_size:
            # Remove oldest (least recently used)
            lru_key = next(iter(self._access_order))
            await self.backend.delete(lru_key)
            del self._access_order[lru_key]

    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from LRU cache."""
        key_str = validate_cache_key(key)

        value = await self.backend.get(key)

        if value is not None:
            # Update access order
            await self._update_access(key_str)

        return value

    async def set(self, key: Union[str, CacheKey], value: Any, **kwargs) -> bool:
        """Set a value in LRU cache."""
        key_str = validate_cache_key(key)

        # Set in backend
        result = await self.backend.set(key, value, **kwargs)

        if result:
            # Update access order
            await self._update_access(key_str)

            # Evict if necessary
            await self._evict_lru()

        return result

    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from LRU cache."""
        key_str = validate_cache_key(key)

        # Remove from access tracking
        self._access_order.pop(key_str, None)

        return await self.backend.delete(key)

    async def clear(self) -> bool:
        """Clear all cached values."""
        self._access_order.clear()
        return await self.backend.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get LRU cache statistics."""
        backend_stats = await self.backend.get_stats()

        backend_stats.update(
            {
                "strategy": "lru",
                "max_size": self.max_size,
                "current_size": len(self._access_order),
                "utilization": round(len(self._access_order) / self.max_size * 100, 2),
            }
        )

        return backend_stats


class LFUCache(CacheStrategy):
    """Least Frequently Used (LFU) cache strategy.

    This strategy evicts the least frequently used items when
    the cache reaches its maximum size. Access frequency is
    tracked to determine which items to evict.

    Features:
    - LFU eviction policy
    - Configurable maximum size
    - Access frequency tracking
    - Aging mechanism to prevent stale popular items

    Example:
        >>> cache = LFUCache(backend, max_size=1000)
        >>> await cache.set("key1", "value1")
        >>> value = await cache.get("key1")  # Increments frequency
    """

    def __init__(
        self, backend: CacheBackend, max_size: int = 1000, aging_factor: float = 0.9
    ):
        """Initialize LFU cache strategy.

        Args:
            backend: Cache backend
            max_size: Maximum number of items
            aging_factor: Factor to age frequencies (0.0-1.0)
        """
        super().__init__(backend)
        self.max_size = max_size
        self.aging_factor = aging_factor

        # Track access frequency
        self._frequencies: Dict[str, int] = defaultdict(int)
        self._last_aging = time.time()
        self._aging_interval = 3600  # Age frequencies every hour

    async def _update_frequency(self, key: str):
        """Update access frequency for a key."""
        self._frequencies[key] += 1

        # Apply aging if needed
        await self._apply_aging()

    async def _apply_aging(self):
        """Apply aging to frequencies to prevent stale popular items."""
        current_time = time.time()

        if current_time - self._last_aging < self._aging_interval:
            return

        # Age all frequencies
        for key in self._frequencies:
            self._frequencies[key] = int(self._frequencies[key] * self.aging_factor)

        # Remove zero frequencies
        self._frequencies = {k: v for k, v in self._frequencies.items() if v > 0}

        self._last_aging = current_time

    async def _evict_lfu(self):
        """Evict least frequently used items if over limit."""
        while len(self._frequencies) > self.max_size:
            # Find least frequently used key
            lfu_key = min(self._frequencies.keys(), key=lambda k: self._frequencies[k])

            await self.backend.delete(lfu_key)
            del self._frequencies[lfu_key]

    async def get(self, key: Union[str, CacheKey]) -> Optional[Any]:
        """Get a value from LFU cache."""
        key_str = validate_cache_key(key)

        value = await self.backend.get(key)

        if value is not None:
            # Update frequency
            await self._update_frequency(key_str)

        return value

    async def set(self, key: Union[str, CacheKey], value: Any, **kwargs) -> bool:
        """Set a value in LFU cache."""
        key_str = validate_cache_key(key)

        # Set in backend
        result = await self.backend.set(key, value, **kwargs)

        if result:
            # Initialize frequency
            if key_str not in self._frequencies:
                self._frequencies[key_str] = 1

            # Evict if necessary
            await self._evict_lfu()

        return result

    async def delete(self, key: Union[str, CacheKey]) -> bool:
        """Delete a value from LFU cache."""
        key_str = validate_cache_key(key)

        # Remove from frequency tracking
        self._frequencies.pop(key_str, None)

        return await self.backend.delete(key)

    async def clear(self) -> bool:
        """Clear all cached values."""
        self._frequencies.clear()
        return await self.backend.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get LFU cache statistics."""
        backend_stats = await self.backend.get_stats()

        # Calculate frequency statistics
        frequencies = list(self._frequencies.values())
        avg_frequency = sum(frequencies) / len(frequencies) if frequencies else 0
        max_frequency = max(frequencies) if frequencies else 0
        min_frequency = min(frequencies) if frequencies else 0

        backend_stats.update(
            {
                "strategy": "lfu",
                "max_size": self.max_size,
                "current_size": len(self._frequencies),
                "utilization": round(len(self._frequencies) / self.max_size * 100, 2),
                "avg_frequency": round(avg_frequency, 2),
                "max_frequency": max_frequency,
                "min_frequency": min_frequency,
                "aging_factor": self.aging_factor,
            }
        )

        return backend_stats
