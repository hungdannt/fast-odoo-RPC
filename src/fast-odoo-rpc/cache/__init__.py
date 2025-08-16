"""
Intelligent caching system for OdooFlow.

This module provides TTL and LRU caching strategies with both
in-memory and Redis backend support for high-performance data caching.
"""

from .manager import CacheManager
from .backends import MemoryCache, RedisCache
from .strategies import TTLCache, LRUCache, LFUCache
from .decorators import cached, cache_result, invalidate_cache
from .keys import CacheKey, make_cache_key
from .exceptions import CacheError, CacheBackendError, CacheKeyError

__all__ = [
    # Core caching
    "CacheManager",
    # Backends
    "MemoryCache",
    "RedisCache",
    # Strategies
    "TTLCache",
    "LRUCache",
    "LFUCache",
    # Decorators
    "cached",
    "cache_result",
    "invalidate_cache",
    # Key management
    "CacheKey",
    "make_cache_key",
    # Exceptions
    "CacheError",
    "CacheBackendError",
    "CacheKeyError",
]
