"""
Circuit breaker tests for the enhanced connection pool.

This module tests the circuit breaker functionality including state transitions
from CLOSED -> OPEN -> HALF_OPEN and recovery after timeout.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import pytest
import httpx

from zenoo_rpc.transport.pool import (
    CircuitBreaker,
    CircuitBreakerState,
    EnhancedConnectionPool,
    PooledConnection,
    ConnectionState,
)
from zenoo_rpc.exceptions import ZenooError


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state(self):
        """Test circuit breaker initializes in CLOSED state."""
        cb = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60.0, success_threshold=3
        )

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.should_allow_request() is True

    def test_failure_threshold_transition_to_open(self):
        """Test transition from CLOSED to OPEN state after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures up to threshold
        for i in range(3):
            assert cb.state == CircuitBreakerState.CLOSED
            cb.record_failure()

        # Should now be OPEN
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.should_allow_request() is False

    def test_recovery_timeout_transition_to_half_open(self):
        """Test transition from OPEN to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        # Trip the circuit breaker
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Time hasn't passed yet
        assert cb.should_allow_request() is False

        # Simulate time passing by mocking time.time()
        with patch("time.time") as mock_time:
            # Set initial time
            mock_time.return_value = cb.last_failure_time + 11.0

            # Should transition to HALF_OPEN
            assert cb.should_allow_request() is True
            assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_to_closed_after_success_threshold(self):
        """Test transition from HALF_OPEN to CLOSED after success threshold."""
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=10.0, success_threshold=3
        )

        # Trip to OPEN
        cb.record_failure()

        # Move to HALF_OPEN
        with patch("time.time") as mock_time:
            mock_time.return_value = cb.last_failure_time + 11.0
            cb.should_allow_request()
            assert cb.state == CircuitBreakerState.HALF_OPEN

            # Record successes
            for i in range(3):
                cb.record_success()

            # Should be back to CLOSED
            assert cb.state == CircuitBreakerState.CLOSED
            assert cb.failure_count == 0

    def test_half_open_to_open_on_failure(self):
        """Test transition from HALF_OPEN back to OPEN on failure."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        # Trip to OPEN
        cb.record_failure()

        # Move to HALF_OPEN
        with patch("time.time") as mock_time:
            mock_time.return_value = cb.last_failure_time + 11.0
            cb.should_allow_request()
            assert cb.state == CircuitBreakerState.HALF_OPEN

            # Record failure in HALF_OPEN
            cb.record_failure()

            # Should be back to OPEN
            assert cb.state == CircuitBreakerState.OPEN
            assert cb.success_count == 0

    def test_success_resets_failure_count_in_closed(self):
        """Test that success resets failure count in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        # Success should reset
        cb.record_success()
        assert cb.failure_count == 0

    def test_half_open_state_allows_request(self):
        """Test that HALF_OPEN state allows requests (covers lines 63-65)."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)

        # Trip to OPEN
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Manually set to HALF_OPEN
        cb.state = CircuitBreakerState.HALF_OPEN

        # Should allow request in HALF_OPEN state
        assert cb.should_allow_request() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN


class TestPoolCircuitBreaker:
    """Test circuit breaker integration with connection pool."""

    @pytest.fixture
    async def pool(self):
        """Create a test connection pool."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com", pool_size=2, max_connections=5
        )
        yield pool
        if pool.initialized:
            await pool.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_requests_when_open(self, pool):
        """Test that circuit breaker blocks requests when OPEN."""
        # Manually trip the circuit breaker
        pool.circuit_breaker.state = CircuitBreakerState.OPEN

        # Should raise error with the state value in the message
        with pytest.raises(ZenooError, match="Circuit breaker is open"):
            pool.get_connection()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failures(self, pool):
        """Test that connection failures are recorded in circuit breaker."""
        await pool.initialize()

        # Create mock connections that will be used
        mock_connections = []
        for _ in range(pool.circuit_breaker.failure_threshold):
            mock_client = AsyncMock()
            mock_connection = PooledConnection(client=mock_client)
            mock_connections.append(mock_connection)

        # Mock _acquire_connection to return connections
        acquire_call_count = 0

        def acquire_side_effect():
            nonlocal acquire_call_count
            if acquire_call_count < len(mock_connections):
                conn = mock_connections[acquire_call_count]
                acquire_call_count += 1
                return conn
            raise ZenooError("No more connections")

        with patch.object(pool, "_acquire_connection", side_effect=acquire_side_effect):
            # Try multiple times - the context manager will record failures
            for i in range(pool.circuit_breaker.failure_threshold):
                try:
                    async with pool.get_connection() as conn:
                        # Simulate failure during connection usage
                        raise ZenooError("Connection failed during usage")
                except ZenooError:
                    pass

            # Circuit breaker should be open
            assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self, pool):
        """Test that successful connections are recorded."""
        await pool.initialize()

        # Create a mock connection
        mock_client = AsyncMock()
        mock_connection = PooledConnection(client=mock_client)

        with patch.object(pool, "_acquire_connection", return_value=mock_connection):
            async with pool.get_connection() as conn:
                pass

            # Should record success
            assert pool.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_flow(self, pool):
        """Test complete circuit breaker recovery flow."""
        await pool.initialize()

        # Set up circuit breaker with short timeouts for testing
        pool.circuit_breaker.failure_threshold = 2
        pool.circuit_breaker.recovery_timeout = 1.0
        pool.circuit_breaker.success_threshold = 2

        # Phase 1: Trip circuit breaker (CLOSED -> OPEN)
        with patch.object(pool, "_acquire_connection") as mock_acquire:
            mock_acquire.side_effect = ZenooError("Connection failed")

            for i in range(2):
                try:
                    async with pool.get_connection() as conn:
                        pass
                except ZenooError:
                    pass

            assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

        # Phase 2: Wait for recovery timeout (OPEN -> HALF_OPEN)
        await asyncio.sleep(1.1)

        # Create successful mock connection
        mock_client = AsyncMock()
        mock_connection = PooledConnection(client=mock_client)

        with patch.object(pool, "_acquire_connection", return_value=mock_connection):
            # Phase 3: Successful requests in HALF_OPEN state
            for i in range(2):
                async with pool.get_connection() as conn:
                    pass

            # Should be back to CLOSED
            assert pool.circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure_returns_to_open(self, pool):
        """Test that failure in HALF_OPEN state returns to OPEN."""
        await pool.initialize()

        # Set up circuit breaker
        pool.circuit_breaker.failure_threshold = 1
        pool.circuit_breaker.recovery_timeout = 0.1

        # Trip to OPEN
        with patch.object(
            pool, "_acquire_connection", side_effect=ZenooError("Failed")
        ):
            try:
                async with pool.get_connection() as conn:
                    pass
            except ZenooError:
                pass

        assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Next request should be allowed (HALF_OPEN)
        with patch.object(
            pool, "_acquire_connection", side_effect=ZenooError("Failed again")
        ):
            try:
                async with pool.get_connection() as conn:
                    pass
            except ZenooError:
                pass

        # Should be back to OPEN
        assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_real_connection_errors(self, pool):
        """Test circuit breaker with realistic connection error scenarios."""
        await pool.initialize()

        # Configure circuit breaker
        pool.circuit_breaker.failure_threshold = 3

        # Simulate various connection errors
        error_scenarios = [
            httpx.ConnectTimeout("Connection timeout"),
            httpx.NetworkError("Network unreachable"),
            httpx.RemoteProtocolError("Connection reset"),
        ]

        with patch.object(pool, "_create_connection") as mock_create:
            for error in error_scenarios:
                mock_client = AsyncMock()
                mock_client.aclose = AsyncMock()
                mock_connection = PooledConnection(client=mock_client)
                mock_create.return_value = mock_connection

                # Make connection unhealthy
                mock_connection.mark_unhealthy()

                try:
                    async with pool.get_connection() as conn:
                        # Simulate the error during usage
                        raise error
                except Exception:
                    pass

        # Circuit breaker should be tripped
        assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_pool_exhaustion_at_max_capacity(self, pool):
        """Test pool exhaustion when at maximum capacity (covers lines 348-358)."""
        await pool.initialize()

        # Acquire all connections to exhaust the pool
        acquired_connections = []

        # First, acquire all available connections
        for _ in range(pool.pool_size):
            conn = await pool._acquire_connection()
            acquired_connections.append(conn)

        # Now acquire more connections up to max_connections
        for _ in range(pool.max_connections - pool.pool_size):
            conn = await pool._acquire_connection()
            acquired_connections.append(conn)

        # At this point, we're at max capacity
        assert len(pool.connections) == pool.max_connections

        # Mock the available_connections.get to timeout
        with patch.object(
            pool.available_connections, "get", side_effect=asyncio.TimeoutError()
        ):
            # Trying to acquire another connection should raise error
            with pytest.raises(
                ZenooError, match="Connection pool exhausted and at maximum capacity"
            ):
                await pool._acquire_connection()
