"""
Enhanced connection pooling for OdooFlow.

This module provides advanced connection pooling with HTTP/2 support,
connection health monitoring, and performance optimization.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager

import httpx

from ..exceptions import ZenooError

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""

    IDLE = "idle"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


class CircuitBreakerState(Enum):
    """Circuit breaker state enumeration."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for connection failure handling."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3

    # Internal state
    state: CircuitBreakerState = field(default=CircuitBreakerState.CLOSED)
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0

    def should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record a successful request."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0


@dataclass
class ConnectionStats:
    """Connection statistics."""

    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    request_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0

    @property
    def average_response_time(self) -> float:
        """Get average response time."""
        if self.request_count == 0:
            return 0.0
        return self.total_response_time / self.request_count

    @property
    def error_rate(self) -> float:
        """Get error rate as percentage."""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100


@dataclass
class PooledConnection:
    """Represents a pooled HTTP connection."""

    client: httpx.AsyncClient
    state: ConnectionState = ConnectionState.IDLE
    stats: ConnectionStats = field(default_factory=ConnectionStats)
    health_check_at: float = field(default_factory=time.time)

    def mark_used(self) -> None:
        """Mark connection as recently used."""
        self.stats.last_used = time.time()
        self.state = ConnectionState.ACTIVE

    def mark_idle(self) -> None:
        """Mark connection as idle."""
        self.state = ConnectionState.IDLE

    def mark_unhealthy(self) -> None:
        """Mark connection as unhealthy."""
        self.state = ConnectionState.UNHEALTHY

    def record_request(self, response_time: float, success: bool = True) -> None:
        """Record request statistics."""
        self.stats.request_count += 1
        self.stats.total_response_time += response_time

        if not success:
            self.stats.error_count += 1

    def is_healthy(self, max_error_rate: float = 10.0) -> bool:
        """Check if connection is healthy."""
        if self.state == ConnectionState.UNHEALTHY:
            return False

        # Check error rate
        if self.stats.error_rate > max_error_rate:
            return False

        return True

    def should_health_check(self, interval: float = 30.0) -> bool:
        """Check if connection needs health check."""
        return time.time() - self.health_check_at > interval


class ConnectionPool:
    """Connection pool with HTTP/2 support and health monitoring.

    This class provides advanced connection pooling capabilities including:
    - HTTP/2 support with multiplexing
    - Connection health monitoring
    - Automatic connection recovery
    - Load balancing across connections
    - Performance statistics and monitoring

    Features:
    - Configurable pool size and timeouts
    - Connection health checks
    - Automatic retry and failover
    - Performance metrics
    - Connection lifecycle management

    Example:
        >>> pool = ConnectionPool(
        ...     base_url="https://demo.odoo.com",
        ...     pool_size=10,
        ...     http2=True
        ... )
        >>> await pool.initialize()
        >>>
        >>> async with pool.get_connection() as client:
        ...     response = await client.post("/jsonrpc", json=data)
    """

    def __init__(
        self,
        base_url: str,
        pool_size: int = 10,
        max_connections: int = 20,
        http2: bool = True,
        timeout: float = 30.0,
        health_check_interval: float = 30.0,
        max_error_rate: float = 10.0,
        connection_ttl: float = 300.0,
    ):
        """Initialize enhanced connection pool.

        Args:
            base_url: Base URL for connections
            pool_size: Target pool size
            max_connections: Maximum connections
            http2: Enable HTTP/2 support
            timeout: Request timeout
            health_check_interval: Health check interval in seconds
            max_error_rate: Maximum error rate percentage
            connection_ttl: Connection time-to-live in seconds
        """
        self.base_url = base_url
        self.pool_size = pool_size
        self.max_connections = max_connections
        self.http2 = http2
        self.timeout = timeout
        self.health_check_interval = health_check_interval
        self.max_error_rate = max_error_rate
        self.connection_ttl = connection_ttl

        # Connection pool
        self.connections: List[PooledConnection] = []
        self.available_connections: asyncio.Queue = asyncio.Queue()
        self.active_connections: Dict[str, PooledConnection] = {}

        # Pool state
        self.initialized = False
        self.closed = False

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "connections_created": 0,
            "connections_closed": 0,
            "health_checks": 0,
            "pool_hits": 0,
            "pool_misses": 0,
        }

        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60.0, success_threshold=3
        )

        # Synchronization
        self.lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self.initialized:
            return

        async with self.lock:
            if self.initialized:
                return

            logger.info(
                f"Initializing connection pool: {self.pool_size} connections to {self.base_url}"
            )

            # Create initial connections
            for _ in range(self.pool_size):
                connection = await self._create_connection()
                self.connections.append(connection)
                await self.available_connections.put(connection)

            # Start background tasks
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

            self.initialized = True
            logger.info(
                f"Connection pool initialized with {len(self.connections)} connections"
            )

    async def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection."""
        # Configure httpx client
        limits = httpx.Limits(
            max_keepalive_connections=5, max_connections=10, keepalive_expiry=30.0
        )

        timeout = httpx.Timeout(connect=10.0, read=self.timeout, write=10.0, pool=5.0)

        client = httpx.AsyncClient(
            base_url=self.base_url,
            http2=self.http2,
            limits=limits,
            timeout=timeout,
            headers={
                "User-Agent": "OdooFlow/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        connection = PooledConnection(client=client)
        self.stats["connections_created"] += 1

        logger.debug(f"Created new connection (total: {len(self.connections) + 1})")
        return connection

    def get_connection(self) -> "ConnectionContext":
        """Get a connection from the pool.

        Returns:
            Connection context manager
        """
        if self.closed:
            raise ZenooError("Connection pool is closed")

        # Check circuit breaker
        if not self.circuit_breaker.should_allow_request():
            raise ZenooError(f"Circuit breaker is {self.circuit_breaker.state.value}")

        return ConnectionContext(self)

    async def _acquire_connection(self) -> PooledConnection:
        """Acquire a connection from the pool."""
        try:
            # Try to get available connection with timeout
            connection = await asyncio.wait_for(
                self.available_connections.get(), timeout=5.0
            )

            # Check if connection is healthy
            if not connection.is_healthy(self.max_error_rate):
                logger.warning("Acquired unhealthy connection, creating new one")
                await self._close_connection(connection)
                connection = await self._create_connection()

            connection.mark_used()
            self.stats["pool_hits"] += 1

            return connection

        except asyncio.TimeoutError:
            # No available connections, try to create new one
            if len(self.connections) < self.max_connections:
                logger.debug("Creating new connection due to pool exhaustion")
                connection = await self._create_connection()
                self.connections.append(connection)
                connection.mark_used()
                self.stats["pool_misses"] += 1
                return connection
            else:
                raise ZenooError("Connection pool exhausted and at maximum capacity")

    async def _release_connection(self, connection: PooledConnection) -> None:
        """Release a connection back to the pool."""
        if connection.state == ConnectionState.UNHEALTHY or self.closed:
            await self._close_connection(connection)
            return

        # Check if connection is too old
        if time.time() - connection.stats.created_at > self.connection_ttl:
            logger.debug("Closing old connection")
            await self._close_connection(connection)

            # Create replacement if needed
            if len(self.connections) < self.pool_size:
                new_connection = await self._create_connection()
                self.connections.append(new_connection)
                await self.available_connections.put(new_connection)

            return

        connection.mark_idle()
        await self.available_connections.put(connection)

    async def _close_connection(self, connection: PooledConnection) -> None:
        """Close a connection and remove from pool."""
        try:
            # Add timeout to prevent hanging on close
            await asyncio.wait_for(connection.client.aclose(), timeout=5.0)
            connection.state = ConnectionState.CLOSED

            if connection in self.connections:
                self.connections.remove(connection)

            self.stats["connections_closed"] += 1
            logger.debug(f"Closed connection (remaining: {len(self.connections)})")

        except asyncio.TimeoutError:
            logger.warning(f"Connection close timed out, forcing closure")
            connection.state = ConnectionState.CLOSED
            if connection in self.connections:
                self.connections.remove(connection)
            self.stats["connections_closed"] += 1
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            # Still mark as closed and remove from pool
            connection.state = ConnectionState.CLOSED
            if connection in self.connections:
                self.connections.remove(connection)

    async def _health_check_loop(self) -> None:
        """Background task for connection health checks."""
        while not self.closed:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _perform_health_checks(self) -> None:
        """Perform health checks on connections."""
        unhealthy_connections = []

        for connection in self.connections:
            if connection.should_health_check(self.health_check_interval):
                try:
                    # Simple health check - ping the server with timeout
                    start_time = time.time()
                    response = await asyncio.wait_for(
                        connection.client.get("/web/database/selector"),
                        timeout=5.0
                    )
                    response_time = time.time() - start_time

                    if response.status_code < 500:
                        connection.record_request(response_time, success=True)
                        connection.health_check_at = time.time()
                    else:
                        connection.record_request(response_time, success=False)
                        connection.mark_unhealthy()
                        unhealthy_connections.append(connection)

                    self.stats["health_checks"] += 1

                except asyncio.TimeoutError:
                    logger.warning("Health check timed out for connection")
                    connection.mark_unhealthy()
                    unhealthy_connections.append(connection)
                except Exception as e:
                    logger.warning(f"Health check failed for connection: {e}")
                    connection.mark_unhealthy()
                    unhealthy_connections.append(connection)

        # Close unhealthy connections
        for connection in unhealthy_connections:
            await self._close_connection(connection)

    async def _cleanup_loop(self) -> None:
        """Background task for connection cleanup."""
        while not self.closed:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _cleanup_connections(self) -> None:
        """Clean up old and unused connections."""
        current_time = time.time()
        connections_to_close = []

        for connection in self.connections:
            # Close connections that haven't been used recently
            if (
                connection.state == ConnectionState.IDLE
                and current_time - connection.stats.last_used > self.connection_ttl
            ):
                connections_to_close.append(connection)

        # Don't close too many connections at once
        if len(connections_to_close) > len(self.connections) // 2:
            connections_to_close = connections_to_close[: len(self.connections) // 2]

        for connection in connections_to_close:
            await self._close_connection(connection)

        # Ensure minimum pool size
        while len(self.connections) < self.pool_size:
            new_connection = await self._create_connection()
            self.connections.append(new_connection)
            await self.available_connections.put(new_connection)

    async def close(self) -> None:
        """Close the connection pool."""
        if self.closed:
            return

        logger.info("Closing connection pool")
        self.closed = True

        # Cancel background tasks
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()

        # Close all connections
        for connection in self.connections:
            await self._close_connection(connection)

        self.connections.clear()

        # Clear queue
        while not self.available_connections.empty():
            try:
                self.available_connections.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("Connection pool closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        stats = self.stats.copy()

        # Add current state
        stats.update(
            {
                "pool_size": len(self.connections),
                "available_connections": self.available_connections.qsize(),
                "active_connections": len(self.active_connections),
                "initialized": self.initialized,
                "closed": self.closed,
            }
        )

        # Add connection statistics
        if self.connections:
            total_requests = sum(conn.stats.request_count for conn in self.connections)
            total_errors = sum(conn.stats.error_count for conn in self.connections)
            avg_response_time = sum(
                conn.stats.average_response_time for conn in self.connections
            ) / len(self.connections)

            stats.update(
                {
                    "total_connection_requests": total_requests,
                    "total_connection_errors": total_errors,
                    "average_response_time": avg_response_time,
                    "overall_error_rate": (
                        (total_errors / total_requests * 100)
                        if total_requests > 0
                        else 0
                    ),
                }
            )

        return stats


class ConnectionContext:
    """Context manager for pooled connections."""

    def __init__(self, pool: ConnectionPool):
        """Initialize connection context.

        Args:
            pool: Connection pool instance
        """
        self.pool = pool
        self.connection: Optional[PooledConnection] = None

    async def __aenter__(self) -> httpx.AsyncClient:
        """Acquire connection from pool."""
        if not self.pool.initialized:
            await self.pool.initialize()

        self.connection = await self.pool._acquire_connection()
        return self.connection.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release connection back to pool."""
        if self.connection:
            if exc_type is not None:
                # Mark connection as potentially unhealthy on exception
                self.connection.record_request(0, success=False)
                # Record failure in circuit breaker
                self.pool.circuit_breaker.record_failure()
            else:
                # Record success in circuit breaker
                self.pool.circuit_breaker.record_success()

            await self.pool._release_connection(self.connection)
