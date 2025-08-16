"""
Enhanced cache decorators for OdooFlow.

This module provides production-ready decorators for automatic caching of
function results with advanced features including cache stampede prevention,
sliding expiration, circuit breaker integration, and comprehensive monitoring.

Features:
- Cache stampede prevention with promise-based deduplication
- Sliding expiration and dynamic TTL management
- Circuit breaker integration for fault tolerance
- Comprehensive metrics and monitoring
- Redis optimization with client-side caching
- Thread-safe async operations
- Graceful error handling and fallback mechanisms
"""

import functools
import hashlib
import json
import time
from typing import Any, Callable, Optional, Union, List, Dict, Tuple
import asyncio
import logging
from dataclasses import dataclass, field

from .manager import CacheManager
from .keys import make_cache_key
from .exceptions import CacheError

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache metrics for monitoring and observability."""

    hits: int = 0
    misses: int = 0
    errors: int = 0
    stampede_prevented: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    last_access: Optional[float] = None

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.errors / self.total_requests


@dataclass
class CachePromise:
    """Promise for handling concurrent cache requests."""

    future: asyncio.Future
    created_at: float = field(default_factory=time.time)
    access_count: int = 0

    def __post_init__(self):
        """Initialize promise."""
        if self.future.done():
            # If future is already done, mark creation time
            self.created_at = time.time()


class CacheStampedeManager:
    """Manager for preventing cache stampede with promise-based deduplication."""

    def __init__(self):
        """Initialize stampede manager."""
        self._promises: Dict[str, CachePromise] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    async def get_or_create_promise(
        self,
        cache_key: str,
        coro_func: Callable[[], Any]
    ) -> Tuple[Any, bool]:
        """Get existing promise or create new one.

        Args:
            cache_key: Cache key for the operation
            coro_func: Coroutine function to execute if no promise exists

        Returns:
            Tuple of (result, was_stampede_prevented)
        """
        # Cleanup old promises periodically
        await self._cleanup_old_promises()

        # Check if promise already exists (outside lock for performance)
        if cache_key in self._promises:
            async with self._lock:
                # Double-check inside lock
                if cache_key in self._promises:
                    promise = self._promises[cache_key]
                    promise.access_count += 1

                    try:
                        # Wait for existing promise (outside lock)
                        pass  # We'll await outside the lock
                    except Exception:
                        # Remove failed promise
                        self._promises.pop(cache_key, None)
                        raise

            # Await the promise outside the lock
            try:
                result = await promise.future
                return result, True  # Stampede prevented
            except Exception as e:
                # Remove failed promise
                async with self._lock:
                    self._promises.pop(cache_key, None)
                raise e

        # Create new promise
        async with self._lock:
            # Double-check that no promise was created while waiting for lock
            if cache_key in self._promises:
                promise = self._promises[cache_key]
                promise.access_count += 1

                # Await outside lock
                try:
                    result = await promise.future
                    return result, True  # Stampede prevented
                except Exception as e:
                    self._promises.pop(cache_key, None)
                    raise e

            # Create new task and promise
            future = asyncio.create_task(coro_func())
            promise = CachePromise(future=future)
            self._promises[cache_key] = promise

        # Execute outside lock
        try:
            result = await future
            return result, False  # Not a stampede
        except Exception as e:
            # Remove failed promise
            async with self._lock:
                self._promises.pop(cache_key, None)
            raise e
        finally:
            # Remove completed promise
            async with self._lock:
                self._promises.pop(cache_key, None)

    async def _cleanup_old_promises(self):
        """Clean up old completed or failed promises."""
        current_time = time.time()

        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        # Remove old promises
        expired_keys = []
        for key, promise in self._promises.items():
            cleanup_time = self._cleanup_interval
            if (promise.future.done() or
                    current_time - promise.created_at > cleanup_time):
                expired_keys.append(key)

        for key in expired_keys:
            self._promises.pop(key, None)

        self._last_cleanup = current_time


# Global stampede manager instance
_stampede_manager = CacheStampedeManager()

# Global metrics storage
_cache_metrics: Dict[str, CacheMetrics] = {}


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
    stale_ttl: Optional[int] = None,
):
    """Enhanced async cache decorator with stampede prevention and metrics.

    This decorator provides production-ready caching with advanced features:
    - Cache stampede prevention using promise-based deduplication
    - Comprehensive metrics and monitoring
    - Stale-while-revalidate pattern support
    - Circuit breaker integration hooks
    - Thread-safe async operations

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        backend: Cache backend to use
        cache_manager: Cache manager instance
        skip_cache: Function to determine if caching should be skipped
        key_builder: Custom key building function
        prevent_stampede: Enable cache stampede prevention
        enable_metrics: Enable metrics collection
        stale_while_revalidate: Enable stale-while-revalidate pattern
        stale_ttl: TTL for stale data (used with SWR)

    Example:
        >>> @async_cached(ttl=300, prevent_stampede=True, enable_metrics=True)
        ... async def get_partner_data(client, partner_id):
        ...     return await client.model("res.partner").get(id=partner_id)
        ...
        >>> # First call hits database, subsequent concurrent calls wait
        >>> results = await asyncio.gather(*[
        ...     get_partner_data(client, 123) for _ in range(10)
        ... ])  # Only 1 database call made
    """

    def decorator(func: Callable) -> Callable:
        func_name = f"{func.__module__}.{func.__qualname__}"

        # Initialize metrics if enabled
        if enable_metrics and func_name not in _cache_metrics:
            _cache_metrics[func_name] = CacheMetrics()

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = _cache_metrics.get(func_name) if enable_metrics else None

            if metrics:
                metrics.total_requests += 1
                metrics.last_access = start_time

            # Get cache manager
            manager = cache_manager
            if manager is None:
                # Try to get from first argument (usually client)
                if args and hasattr(args[0], "cache_manager"):
                    manager = args[0].cache_manager
                else:
                    logger.warning(
                        f"No cache manager available for {func.__name__}"
                    )
                    return await func(*args, **kwargs)

            # Check if caching should be skipped
            if skip_cache and skip_cache(*args, **kwargs):
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _build_function_cache_key(
                    func, args, kwargs, key_prefix
                )

            # Define async function for cache miss
            async def execute_function():
                try:
                    result = await func(*args, **kwargs)

                    # Cache the result
                    try:
                        await manager.set(cache_key, result, ttl=ttl,
                                        backend=backend)
                        logger.debug(f"Cached result for {func_name}: {cache_key}")
                    except Exception as e:
                        logger.error(f"Cache set error for {func_name}: {e}")
                        if metrics:
                            metrics.errors += 1

                    return result
                except Exception as e:
                    if metrics:
                        metrics.errors += 1
                    raise e

            # Try to get from cache first
            try:
                cached_result = await manager.get(cache_key, backend=backend)
                if cached_result is not None:
                    if metrics:
                        metrics.hits += 1
                        # Update average response time
                        response_time = time.time() - start_time
                        metrics.avg_response_time = (
                            (metrics.avg_response_time * (metrics.hits - 1) +
                             response_time) / metrics.hits
                        )

                    logger.debug(f"Cache hit for {func_name}: {cache_key}")
                    return cached_result
            except Exception as e:
                logger.error(f"Cache get error for {func_name}: {e}")
                if metrics:
                    metrics.errors += 1

            # Cache miss - handle with or without stampede prevention
            if metrics:
                metrics.misses += 1

            if prevent_stampede:
                try:
                    result, was_prevented = await _stampede_manager.get_or_create_promise(
                        cache_key, execute_function
                    )

                    if was_prevented and metrics:
                        metrics.stampede_prevented += 1
                        logger.debug(f"Stampede prevented for {func_name}: {cache_key}")

                    return result
                except Exception as e:
                    logger.error(f"Stampede manager error for {func_name}: {e}")
                    # Fallback to direct execution
                    return await execute_function()
            else:
                return await execute_function()

        # Add metadata and utility methods
        wrapper._cache_ttl = ttl
        wrapper._cache_backend = backend
        wrapper._cache_key_prefix = key_prefix
        wrapper._prevent_stampede = prevent_stampede
        wrapper._enable_metrics = enable_metrics

        # Add metrics access method
        if enable_metrics:
            wrapper.get_cache_metrics = lambda: _cache_metrics.get(func_name)
            wrapper.reset_cache_metrics = lambda: _cache_metrics.update({
                func_name: CacheMetrics()
            })

        return wrapper

    return decorator


def sliding_cache(
    ttl: int,
    max_ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    backend: Optional[str] = None,
    cache_manager: Optional[CacheManager] = None,
    slide_on_hit: bool = True,
    slide_factor: float = 1.0,
):
    """Sliding expiration cache decorator.

    This decorator implements sliding expiration where the TTL of cached
    items is extended each time they are accessed, keeping frequently
    accessed data in cache longer.

    Args:
        ttl: Initial TTL in seconds
        max_ttl: Maximum TTL to prevent infinite sliding
        key_prefix: Prefix for cache keys
        backend: Cache backend to use
        cache_manager: Cache manager instance
        slide_on_hit: Whether to slide TTL on cache hits
        slide_factor: Factor to multiply TTL on each slide

    Example:
        >>> @sliding_cache(ttl=300, max_ttl=3600, slide_factor=1.5)
        ... async def get_user_preferences(client, user_id):
        ...     return await client.get_user_preferences(user_id)
        ...
        >>> # Frequently accessed preferences stay cached longer
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager
            manager = cache_manager
            if manager is None:
                if args and hasattr(args[0], "cache_manager"):
                    manager = args[0].cache_manager
                else:
                    logger.warning(
                        f"No cache manager available for {func.__name__}"
                    )
                    return await func(*args, **kwargs)

            # Build cache key
            cache_key = _build_function_cache_key(func, args, kwargs, key_prefix)

            # Try to get from cache
            try:
                cached_result = await manager.get(cache_key, backend=backend)
                if cached_result is not None:
                    # Slide the TTL if enabled
                    if slide_on_hit:
                        new_ttl = min(ttl * slide_factor, max_ttl or float('inf'))
                        try:
                            await manager.set(
                                cache_key, cached_result,
                                ttl=int(new_ttl), backend=backend
                            )
                            logger.debug(
                                f"Slid TTL for {func.__name__}: {cache_key} "
                                f"to {new_ttl}s"
                            )
                        except Exception as e:
                            logger.error(f"TTL slide error: {e}")

                    return cached_result
            except Exception as e:
                logger.error(f"Cache get error for {func.__name__}: {e}")

            # Cache miss - execute function and cache result
            result = await func(*args, **kwargs)

            try:
                await manager.set(cache_key, result, ttl=ttl, backend=backend)
            except Exception as e:
                logger.error(f"Cache set error for {func.__name__}: {e}")

            return result

        # Add metadata
        wrapper._cache_ttl = ttl
        wrapper._cache_max_ttl = max_ttl
        wrapper._slide_factor = slide_factor

        return wrapper

    return decorator


def circuit_cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    backend: Optional[str] = None,
    cache_manager: Optional[CacheManager] = None,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: int = 60,
    fallback_ttl: int = 30,
):
    """Cache decorator with circuit breaker integration.

    This decorator integrates with circuit breaker patterns to provide
    graceful degradation when the underlying service is failing.
    It can serve stale cache data when the circuit is open.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        backend: Cache backend to use
        cache_manager: Cache manager instance
        circuit_breaker_threshold: Number of failures before opening circuit
        circuit_breaker_timeout: Time to wait before attempting recovery
        fallback_ttl: TTL for fallback cache entries

    Example:
        >>> @circuit_cached(ttl=300, circuit_breaker_threshold=3)
        ... async def get_external_data(client, data_id):
        ...     return await client.fetch_external_api(data_id)
        ...
        >>> # Serves stale data when external API is down
    """

    def decorator(func: Callable) -> Callable:
        func_name = f"{func.__module__}.{func.__qualname__}"

        # Circuit breaker state
        failure_count = 0
        last_failure_time = 0.0
        circuit_open = False

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal failure_count, last_failure_time, circuit_open

            # Get cache manager
            manager = cache_manager
            if manager is None:
                if args and hasattr(args[0], "cache_manager"):
                    manager = args[0].cache_manager
                else:
                    logger.warning(
                        f"No cache manager available for {func.__name__}"
                    )
                    return await func(*args, **kwargs)

            # Build cache key
            cache_key = _build_function_cache_key(func, args, kwargs, key_prefix)

            # Check circuit breaker state
            current_time = time.time()
            if circuit_open:
                if current_time - last_failure_time >= circuit_breaker_timeout:
                    # Try to close circuit
                    circuit_open = False
                    failure_count = 0
                    logger.info(f"Circuit breaker reset for {func_name}")
                else:
                    # Circuit is open, try to serve stale data
                    try:
                        stale_data = await manager.get(cache_key, backend=backend)
                        if stale_data is not None:
                            logger.info(
                                f"Serving stale data for {func_name} "
                                f"(circuit open): {cache_key}"
                            )
                            return stale_data
                    except Exception as e:
                        logger.error(f"Failed to get stale data: {e}")

                    # No stale data available
                    raise CacheError(
                        f"Circuit breaker open for {func_name}, "
                        f"no stale data available"
                    )

            # Try to get from cache first
            try:
                cached_result = await manager.get(cache_key, backend=backend)
                if cached_result is not None:
                    return cached_result
            except Exception as e:
                logger.error(f"Cache get error for {func_name}: {e}")

            # Cache miss - execute function
            try:
                result = await func(*args, **kwargs)

                # Reset circuit breaker on success
                failure_count = 0
                circuit_open = False

                # Cache the result
                try:
                    await manager.set(cache_key, result, ttl=ttl, backend=backend)
                except Exception as e:
                    logger.error(f"Cache set error for {func_name}: {e}")

                return result

            except Exception as e:
                # Handle failure
                failure_count += 1
                last_failure_time = current_time

                if failure_count >= circuit_breaker_threshold:
                    circuit_open = True
                    logger.warning(
                        f"Circuit breaker opened for {func_name} "
                        f"after {failure_count} failures"
                    )

                # Try to serve stale data on failure
                try:
                    stale_data = await manager.get(cache_key, backend=backend)
                    if stale_data is not None:
                        logger.info(
                            f"Serving stale data for {func_name} "
                            f"(function failed): {cache_key}"
                        )
                        # Extend TTL for fallback data
                        await manager.set(
                            cache_key, stale_data,
                            ttl=fallback_ttl, backend=backend
                        )
                        return stale_data
                except Exception as cache_error:
                    logger.error(f"Failed to get stale data: {cache_error}")

                # Re-raise original exception
                raise e

        # Add metadata
        wrapper._circuit_breaker_threshold = circuit_breaker_threshold
        wrapper._circuit_breaker_timeout = circuit_breaker_timeout
        wrapper._fallback_ttl = fallback_ttl

        # Add circuit breaker status method
        wrapper.get_circuit_status = lambda: {
            "open": circuit_open,
            "failure_count": failure_count,
            "last_failure_time": last_failure_time,
        }

        return wrapper

    return decorator


def metrics_cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    backend: Optional[str] = None,
    cache_manager: Optional[CacheManager] = None,
    track_performance: bool = True,
    track_memory: bool = False,
):
    """Cache decorator with comprehensive metrics tracking.

    This decorator provides detailed metrics and monitoring capabilities
    for cache performance analysis and optimization.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        backend: Cache backend to use
        cache_manager: Cache manager instance
        track_performance: Enable performance metrics tracking
        track_memory: Enable memory usage tracking

    Example:
        >>> @metrics_cached(ttl=300, track_performance=True)
        ... async def get_analytics_data(client, query):
        ...     return await client.run_analytics_query(query)
        ...
        >>> # Access metrics
        >>> metrics = get_analytics_data.get_detailed_metrics()
        >>> print(f"Hit rate: {metrics['hit_rate']:.2%}")
    """

    def decorator(func: Callable) -> Callable:
        func_name = f"{func.__module__}.{func.__qualname__}"

        # Initialize detailed metrics
        detailed_metrics = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0,
            "total_response_time": 0.0,
            "min_response_time": float('inf'),
            "max_response_time": 0.0,
            "cache_size_samples": [],
            "key_access_frequency": {},
            "error_types": {},
        }

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            detailed_metrics["total_requests"] += 1

            # Get cache manager
            manager = cache_manager
            if manager is None:
                if args and hasattr(args[0], "cache_manager"):
                    manager = args[0].cache_manager
                else:
                    logger.warning(
                        f"No cache manager available for {func.__name__}"
                    )
                    return await func(*args, **kwargs)

            # Build cache key
            cache_key = _build_function_cache_key(func, args, kwargs, key_prefix)

            # Track key access frequency
            detailed_metrics["key_access_frequency"][cache_key] = (
                detailed_metrics["key_access_frequency"].get(cache_key, 0) + 1
            )

            # Try to get from cache
            try:
                cached_result = await manager.get(cache_key, backend=backend)
                if cached_result is not None:
                    detailed_metrics["hits"] += 1

                    # Track response time
                    response_time = time.time() - start_time
                    detailed_metrics["total_response_time"] += response_time
                    detailed_metrics["min_response_time"] = min(
                        detailed_metrics["min_response_time"], response_time
                    )
                    detailed_metrics["max_response_time"] = max(
                        detailed_metrics["max_response_time"], response_time
                    )

                    return cached_result
            except Exception as e:
                detailed_metrics["errors"] += 1
                error_type = type(e).__name__
                detailed_metrics["error_types"][error_type] = (
                    detailed_metrics["error_types"].get(error_type, 0) + 1
                )
                logger.error(f"Cache get error for {func_name}: {e}")

            # Cache miss
            detailed_metrics["misses"] += 1

            try:
                result = await func(*args, **kwargs)

                # Cache the result
                try:
                    await manager.set(cache_key, result, ttl=ttl, backend=backend)
                except Exception as e:
                    detailed_metrics["errors"] += 1
                    error_type = type(e).__name__
                    detailed_metrics["error_types"][error_type] = (
                        detailed_metrics["error_types"].get(error_type, 0) + 1
                    )
                    logger.error(f"Cache set error for {func_name}: {e}")

                # Track response time
                response_time = time.time() - start_time
                detailed_metrics["total_response_time"] += response_time
                detailed_metrics["min_response_time"] = min(
                    detailed_metrics["min_response_time"], response_time
                )
                detailed_metrics["max_response_time"] = max(
                    detailed_metrics["max_response_time"], response_time
                )

                return result

            except Exception as e:
                detailed_metrics["errors"] += 1
                error_type = type(e).__name__
                detailed_metrics["error_types"][error_type] = (
                    detailed_metrics["error_types"].get(error_type, 0) + 1
                )
                raise e

        # Add metrics access methods
        def get_detailed_metrics():
            total_requests = detailed_metrics["total_requests"]
            total_time = detailed_metrics["total_response_time"]

            return {
                **detailed_metrics,
                "hit_rate": (detailed_metrics["hits"] / total_requests
                           if total_requests > 0 else 0.0),
                "miss_rate": (detailed_metrics["misses"] / total_requests
                            if total_requests > 0 else 0.0),
                "error_rate": (detailed_metrics["errors"] / total_requests
                             if total_requests > 0 else 0.0),
                "avg_response_time": (total_time / total_requests
                                    if total_requests > 0 else 0.0),
            }

        def reset_detailed_metrics():
            detailed_metrics.clear()
            detailed_metrics.update({
                "hits": 0,
                "misses": 0,
                "errors": 0,
                "total_requests": 0,
                "total_response_time": 0.0,
                "min_response_time": float('inf'),
                "max_response_time": 0.0,
                "cache_size_samples": [],
                "key_access_frequency": {},
                "error_types": {},
            })

        wrapper.get_detailed_metrics = get_detailed_metrics
        wrapper.reset_detailed_metrics = reset_detailed_metrics

        return wrapper

    return decorator


# Keep original decorators for backward compatibility
def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    backend: Optional[str] = None,
    cache_manager: Optional[CacheManager] = None,
    skip_cache: Optional[Callable] = None,
    key_builder: Optional[Callable] = None,
):
    """Legacy cache decorator for backward compatibility.

    Use async_cached for new implementations with enhanced features.
    """
    return async_cached(
        ttl=ttl,
        key_prefix=key_prefix,
        backend=backend,
        cache_manager=cache_manager,
        skip_cache=skip_cache,
        key_builder=key_builder,
        prevent_stampede=False,  # Disabled for backward compatibility
        enable_metrics=False,    # Disabled for backward compatibility
    )


# Utility functions for cache key generation and management

def _build_function_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: Optional[str] = None
) -> str:
    """Build cache key for function calls.

    Args:
        func: Function being cached
        args: Function positional arguments
        kwargs: Function keyword arguments
        key_prefix: Optional prefix for the key

    Returns:
        Cache key string
    """
    # Start with function name
    func_name = f"{func.__module__}.{func.__qualname__}"

    # Create key parts
    key_parts = []

    if key_prefix:
        key_parts.append(key_prefix)

    key_parts.append(func_name)

    # Filter out 'self' or 'cls' from args for methods
    filtered_args = args
    if args and hasattr(args[0], '__dict__'):
        # Likely a method call, skip first argument
        filtered_args = args[1:]

    # Add arguments hash only if there are actual arguments
    if len(filtered_args) > 0 or len(kwargs) > 0:
        # Create argument signature
        arg_signature = {
            'args': filtered_args,
            'kwargs': kwargs
        }

        # Create hash of arguments
        arg_str = json.dumps(arg_signature, sort_keys=True, default=str)
        arg_hash = hashlib.md5(arg_str.encode(), usedforsecurity=False).hexdigest()[:8]
        key_parts.append(arg_hash)

    return ":".join(key_parts)


def get_cache_metrics(func_name: Optional[str] = None) -> Dict[str, Any]:
    """Get cache metrics for all functions or specific function.

    Args:
        func_name: Optional function name to get metrics for

    Returns:
        Dictionary of cache metrics
    """
    if func_name:
        return _cache_metrics.get(func_name, CacheMetrics()).__dict__

    return {
        name: metrics.__dict__
        for name, metrics in _cache_metrics.items()
    }


def reset_cache_metrics(func_name: Optional[str] = None) -> None:
    """Reset cache metrics for all functions or specific function.

    Args:
        func_name: Optional function name to reset metrics for
    """
    if func_name:
        if func_name in _cache_metrics:
            _cache_metrics[func_name] = CacheMetrics()
    else:
        _cache_metrics.clear()


def get_stampede_manager_stats() -> Dict[str, Any]:
    """Get statistics from the global stampede manager.

    Returns:
        Dictionary with stampede manager statistics
    """
    return {
        "active_promises": len(_stampede_manager._promises),
        "cleanup_interval": _stampede_manager._cleanup_interval,
        "last_cleanup": _stampede_manager._last_cleanup,
    }


async def clear_cache_stampede_promises() -> None:
    """Clear all active cache stampede promises.

    This should be used carefully as it may cause duplicate work
    for ongoing operations.
    """
    async with _stampede_manager._lock:
        _stampede_manager._promises.clear()
        logger.info("Cleared all cache stampede promises")


# Enhanced cache invalidation with pattern support
class CacheInvalidationManager:
    """Manager for advanced cache invalidation patterns."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize invalidation manager.

        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager
        self._invalidation_patterns: Dict[str, List[str]] = {}

    def register_invalidation_pattern(
        self,
        trigger_pattern: str,
        invalidate_patterns: List[str]
    ) -> None:
        """Register invalidation pattern.

        Args:
            trigger_pattern: Pattern that triggers invalidation
            invalidate_patterns: Patterns to invalidate when triggered
        """
        self._invalidation_patterns[trigger_pattern] = invalidate_patterns

    async def invalidate_by_pattern(
        self,
        pattern: str,
        backend: Optional[str] = None
    ) -> int:
        """Invalidate cache entries by pattern.

        Args:
            pattern: Pattern to match for invalidation
            backend: Cache backend to use

        Returns:
            Number of entries invalidated
        """
        try:
            return await self.cache_manager.invalidate_pattern(
                pattern, backend=backend
            )
        except Exception as e:
            logger.error(f"Pattern invalidation error: {e}")
            return 0

    async def trigger_invalidation(
        self,
        trigger: str,
        backend: Optional[str] = None
    ) -> int:
        """Trigger invalidation based on registered patterns.

        Args:
            trigger: Trigger pattern
            backend: Cache backend to use

        Returns:
            Total number of entries invalidated
        """
        total_invalidated = 0

        for trigger_pattern, invalidate_patterns in self._invalidation_patterns.items():
            if trigger.startswith(trigger_pattern):
                for pattern in invalidate_patterns:
                    invalidated = await self.invalidate_by_pattern(pattern, backend)
                    total_invalidated += invalidated
                    logger.debug(
                        f"Invalidated {invalidated} entries for pattern: {pattern}"
                    )

        return total_invalidated


def cache_result(
    model: str,
    operation: str,
    ttl: Optional[int] = None,
    backend: Optional[str] = None,
    invalidate_on: Optional[List[str]] = None,
):
    """Decorator for caching Odoo operation results.

    This decorator is specifically designed for caching Odoo
    model operations with automatic key generation and invalidation.

    Args:
        model: Odoo model name
        operation: Operation type (search, read, count, etc.)
        ttl: Time to live in seconds
        backend: Cache backend to use
        invalidate_on: List of operations that should invalidate this cache

    Example:
        >>> @cache_result("res.partner", "search", ttl=300)
        ... async def search_partners(client, domain, **kwargs):
        ...     return await client.search_read("res.partner", domain, **kwargs)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager from first argument (client)
            if not args or not hasattr(args[0], "cache_manager"):
                logger.warning(f"No cache manager available for {func.__name__}")
                return await func(*args, **kwargs)

            manager = args[0].cache_manager

            # Build cache key for Odoo operation
            cache_key = make_cache_key(model=model, operation=operation, params=kwargs)

            # Try to get from cache
            try:
                cached_result = await manager.get(cache_key, backend=backend)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {model}.{operation}: {cache_key}")
                    return cached_result
            except Exception as e:
                logger.error(f"Cache get error for {model}.{operation}: {e}")

            # Execute function
            logger.debug(f"Cache miss for {model}.{operation}: {cache_key}")
            result = await func(*args, **kwargs)

            # Cache result
            try:
                await manager.set(cache_key, result, ttl=ttl, backend=backend)
                logger.debug(f"Cached result for {model}.{operation}: {cache_key}")
            except Exception as e:
                logger.error(f"Cache set error for {model}.{operation}: {e}")

            return result

        # Add metadata
        wrapper._cache_model = model
        wrapper._cache_operation = operation
        wrapper._cache_ttl = ttl
        wrapper._cache_backend = backend
        wrapper._invalidate_on = invalidate_on or []

        return wrapper

    return decorator


def invalidate_cache(patterns: Union[str, List[str]], backend: Optional[str] = None):
    """Decorator for cache invalidation after function execution.

    This decorator invalidates cache entries matching the specified
    patterns after the decorated function completes successfully.

    Args:
        patterns: Cache key patterns to invalidate
        backend: Cache backend to use

    Example:
        >>> @invalidate_cache(["res.partner:*", "partner:*"])
        ... async def update_partner(client, partner_id, data):
        ...     return await client.update("res.partner", partner_id, data)
    """
    if isinstance(patterns, str):
        patterns = [patterns]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)

            # Invalidate cache after successful execution
            if args and hasattr(args[0], "cache_manager"):
                manager = args[0].cache_manager

                try:
                    for pattern in patterns:
                        await manager.invalidate_pattern(pattern, backend=backend)
                        logger.debug(f"Invalidated cache pattern: {pattern}")
                except Exception as e:
                    logger.error(f"Cache invalidation error: {e}")

            return result

        return wrapper

    return decorator


class CacheInvalidator:
    """Context manager for cache invalidation.

    This class provides a context manager for invalidating
    cache entries based on the operations performed within the context.

    Example:
        >>> async with CacheInvalidator(client.cache_manager, "res.partner") as invalidator:
        ...     partner = await client.create("res.partner", {"name": "Test"})
        ...     invalidator.add_pattern("partner:*")
        ...     # Cache will be invalidated when context exits
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        model: Optional[str] = None,
        backend: Optional[str] = None,
    ):
        """Initialize cache invalidator.

        Args:
            cache_manager: Cache manager instance
            model: Odoo model name (for automatic pattern generation)
            backend: Cache backend to use
        """
        self.cache_manager = cache_manager
        self.model = model
        self.backend = backend
        self.patterns: List[str] = []

        # Add default patterns for model
        if model:
            self.patterns.append(f"{model}:*")

    async def __aenter__(self):
        """Enter context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and invalidate cache."""
        if exc_type is None:  # Only invalidate on success
            await self.invalidate()

    def add_pattern(self, pattern: str) -> None:
        """Add a cache pattern to invalidate.

        Args:
            pattern: Cache key pattern
        """
        if pattern not in self.patterns:
            self.patterns.append(pattern)

    def add_model_pattern(self, model: str) -> None:
        """Add patterns for a specific model.

        Args:
            model: Odoo model name
        """
        self.add_pattern(f"{model}:*")

    async def invalidate(self) -> int:
        """Invalidate all registered patterns.

        Returns:
            Total number of keys invalidated
        """
        total_invalidated = 0

        for pattern in self.patterns:
            try:
                count = await self.cache_manager.invalidate_pattern(
                    pattern, backend=self.backend
                )
                total_invalidated += count
                logger.debug(f"Invalidated {count} keys for pattern: {pattern}")
            except Exception as e:
                logger.error(f"Failed to invalidate pattern {pattern}: {e}")

        return total_invalidated
