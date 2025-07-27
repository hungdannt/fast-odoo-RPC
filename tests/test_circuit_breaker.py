"""
Tests for circuit breaker pattern in connection pooling.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch

from src.zenoo_rpc.transport.pool import (
    CircuitBreaker,
    CircuitBreakerState,
    EnhancedConnectionPool,
)
from src.zenoo_rpc.exceptions import ZenooError


class TestCircuitBreaker:
    """Test cases for circuit breaker functionality."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        cb = CircuitBreaker()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.should_allow_request() is True

    def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures below threshold
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.should_allow_request() is True

        # Record failure that hits threshold
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.should_allow_request() is False

    def test_circuit_breaker_recovery_timeout(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.should_allow_request() is False

        # Wait for recovery timeout
        time.sleep(0.2)

        # Should transition to half-open
        assert cb.should_allow_request() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_breaker_half_open_success(self):
        """Test circuit breaker closes after successful requests in half-open."""
        cb = CircuitBreaker(
            failure_threshold=2, recovery_timeout=0.1, success_threshold=2
        )

        # Open the circuit breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.2)
        cb.should_allow_request()  # Transition to half-open

        # Record successful requests
        cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker opens again on failure in half-open."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.2)
        cb.should_allow_request()  # Transition to half-open

        # Record failure in half-open state
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.success_count == 0


class TestConnectionPoolCircuitBreaker:
    """Test cases for circuit breaker integration with connection pool."""

    @pytest.mark.asyncio
    async def test_connection_pool_circuit_breaker_integration(self):
        """Test circuit breaker integration with connection pool."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com", pool_size=2, max_connections=5
        )

        # Verify circuit breaker is initialized
        assert pool.circuit_breaker is not None
        assert pool.circuit_breaker.state == CircuitBreakerState.CLOSED

        # Should allow requests initially
        connection_context = pool.get_connection()
        assert connection_context is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_requests_when_open(self):
        """Test circuit breaker blocks requests when open."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com", pool_size=2, max_connections=5
        )

        # Manually open circuit breaker
        pool.circuit_breaker.state = CircuitBreakerState.OPEN
        pool.circuit_breaker.last_failure_time = time.time()  # Set recent failure time

        # Should raise error when circuit breaker is open
        with pytest.raises(ZenooError, match="Circuit breaker is open"):
            pool.get_connection()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success_and_failure(self):
        """Test circuit breaker records success and failure from connection context."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com", pool_size=1, max_connections=2
        )

        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Test successful request
            async with pool.get_connection() as client:
                # Simulate successful request
                pass

            # Circuit breaker should record success
            assert pool.circuit_breaker.failure_count == 0

            # Test failed request
            try:
                async with pool.get_connection() as client:
                    # Simulate failed request
                    raise Exception("Request failed")
            except Exception:
                pass

            # Circuit breaker should record failure
            assert pool.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after consecutive failures."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com", pool_size=1, max_connections=2
        )

        # Set low failure threshold for testing
        pool.circuit_breaker.failure_threshold = 2

        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Simulate multiple failed requests
            for i in range(2):
                try:
                    async with pool.get_connection() as client:
                        raise Exception(f"Request {i} failed")
                except Exception:
                    pass

            # Circuit breaker should be open
            assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

            # Should block subsequent requests
            with pytest.raises(ZenooError, match="Circuit breaker is open"):
                pool.get_connection()

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com", pool_size=1, max_connections=2
        )

        # Set low thresholds for testing
        pool.circuit_breaker.failure_threshold = 1
        pool.circuit_breaker.recovery_timeout = 0.1
        pool.circuit_breaker.success_threshold = 1

        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Open circuit breaker with failure
            try:
                async with pool.get_connection() as client:
                    raise Exception("Request failed")
            except Exception:
                pass

            assert pool.circuit_breaker.state == CircuitBreakerState.OPEN

            # Wait for recovery timeout
            await asyncio.sleep(0.2)

            # Should allow request (transition to half-open)
            connection_context = pool.get_connection()
            assert connection_context is not None

            # Successful request should close circuit breaker
            async with connection_context as client:
                pass  # Successful request

            assert pool.circuit_breaker.state == CircuitBreakerState.CLOSED
