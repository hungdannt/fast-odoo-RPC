"""
Tests for retry mechanism.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from src.zenoo_rpc.retry import (
    ExponentialBackoffStrategy,
    LinearBackoffStrategy,
    FixedDelayStrategy,
    AdaptiveStrategy,
    RetryPolicy,
    DefaultRetryPolicy,
    NetworkRetryPolicy,
    retry,
    async_retry,
    MaxRetriesExceededError,
    RetryTimeoutError,
)


class TestRetryStrategies:
    """Test cases for retry strategies."""

    def test_exponential_backoff_strategy(self):
        """Test exponential backoff strategy."""
        strategy = ExponentialBackoffStrategy(
            max_attempts=4, base_delay=1.0, multiplier=2.0, jitter=False
        )

        # Test delay calculation
        assert strategy.calculate_delay(1) == 1.0
        assert strategy.calculate_delay(2) == 2.0
        assert strategy.calculate_delay(3) == 4.0
        assert strategy.calculate_delay(4) == 8.0

        # Test should_retry
        assert strategy.should_retry(1, Exception()) is True
        assert strategy.should_retry(3, Exception()) is True
        assert strategy.should_retry(4, Exception()) is False

    def test_linear_backoff_strategy(self):
        """Test linear backoff strategy."""
        strategy = LinearBackoffStrategy(
            max_attempts=3, base_delay=1.0, increment=0.5, jitter=False
        )

        # Test delay calculation
        assert strategy.calculate_delay(1) == 1.0
        assert strategy.calculate_delay(2) == 1.5
        assert strategy.calculate_delay(3) == 2.0

    def test_fixed_delay_strategy(self):
        """Test fixed delay strategy."""
        strategy = FixedDelayStrategy(max_attempts=3, delay=2.0, jitter=False)

        # Test delay calculation
        assert strategy.calculate_delay(1) == 2.0
        assert strategy.calculate_delay(2) == 2.0
        assert strategy.calculate_delay(3) == 2.0

    def test_adaptive_strategy(self):
        """Test adaptive strategy."""
        strategy = AdaptiveStrategy(
            max_attempts=3, base_delay=1.0, success_threshold=0.8, jitter=False
        )

        # Initially should use linear backoff (high success rate)
        initial_delay = strategy.calculate_delay(2)

        # Record some failures to lower success rate
        strategy.record_attempt(False)
        strategy.record_attempt(False)
        strategy.record_attempt(False)

        # Should now use exponential backoff (low success rate)
        low_success_delay = strategy.calculate_delay(3)  # Use higher attempt number
        assert low_success_delay > initial_delay

    def test_strategy_max_delay_limit(self):
        """Test strategy respects max delay limit."""
        strategy = ExponentialBackoffStrategy(
            max_attempts=10, base_delay=1.0, multiplier=2.0, max_delay=5.0, jitter=False
        )

        # Large attempt should be capped at max_delay
        delay = strategy.get_delay(10)
        assert delay <= 5.0

    def test_strategy_jitter(self):
        """Test strategy adds jitter."""
        strategy = ExponentialBackoffStrategy(
            max_attempts=3, base_delay=2.0, multiplier=2.0, jitter=True
        )

        # With jitter, delays should vary
        delays = [strategy.get_delay(2) for _ in range(10)]

        # Should have some variation (not all identical)
        assert len(set(delays)) > 1

        # All delays should be positive
        assert all(d >= 0 for d in delays)


class TestRetryPolicies:
    """Test cases for retry policies."""

    def test_default_retry_policy(self):
        """Test default retry policy."""
        policy = DefaultRetryPolicy()

        # Should retry on connection errors
        assert policy.should_retry(1, ConnectionError(), time.time()) is True

        # Should not retry on value errors
        assert policy.should_retry(1, ValueError(), time.time()) is False

        # Should respect timeout
        start_time = time.time() - 70  # 70 seconds ago
        assert policy.should_retry(1, ConnectionError(), start_time) is False

    def test_network_retry_policy(self):
        """Test network retry policy."""
        policy = NetworkRetryPolicy()

        # Should retry on connection errors
        assert policy.should_retry(1, ConnectionError(), time.time()) is True

        # Should have custom retry condition for HTTP errors
        assert policy.retry_condition is not None

    def test_retry_policy_custom_condition(self):
        """Test retry policy with custom condition."""

        def custom_condition(exc):
            return "retry" in str(exc).lower()

        policy = RetryPolicy(retry_condition=custom_condition)

        # Should retry based on custom condition
        assert policy.should_retry(1, Exception("Please retry"), time.time()) is True
        assert policy.should_retry(1, Exception("Fatal error"), time.time()) is False


class TestRetryDecorators:
    """Test cases for retry decorators."""

    def test_sync_retry_decorator_success(self):
        """Test sync retry decorator with successful function."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 1

    def test_sync_retry_decorator_with_retries(self):
        """Test sync retry decorator with retries."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 3

    def test_sync_retry_decorator_max_retries_exceeded(self):
        """Test sync retry decorator when max retries exceeded."""
        call_count = 0

        @retry(max_attempts=2, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")

        with pytest.raises(MaxRetriesExceededError):
            test_function()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_decorator_success(self):
        """Test async retry decorator with successful function."""
        call_count = 0

        @async_retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_decorator_with_retries(self):
        """Test async retry decorator with retries."""
        call_count = 0

        @async_retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_decorator_max_retries_exceeded(self):
        """Test async retry decorator when max retries exceeded."""
        call_count = 0

        @async_retry(max_attempts=2, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")

        with pytest.raises(MaxRetriesExceededError):
            await test_function()

        assert call_count == 2

    def test_retry_decorator_with_callback(self):
        """Test retry decorator with callback."""
        retry_attempts = []

        def on_retry(attempt):
            retry_attempts.append(attempt)

        @retry(max_attempts=3, delay=0.01, on_retry=on_retry)
        def test_function():
            if len(retry_attempts) < 2:
                raise ConnectionError("Network error")
            return "success"

        result = test_function()
        assert result == "success"
        assert len(retry_attempts) == 2

        # Check retry attempt info
        for attempt in retry_attempts:
            assert attempt.attempt_number > 0
            assert attempt.exception is not None
            assert attempt.delay >= 0

    def test_retry_decorator_with_specific_exceptions(self):
        """Test retry decorator with specific exception types."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01, exceptions=(ConnectionError,))
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")  # Should retry
            elif call_count == 2:
                raise ValueError("Value error")  # Should not retry
            return "success"

        # Should get MaxRetriesExceededError wrapping ValueError
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            test_function()

        # The last exception should be ValueError
        assert isinstance(exc_info.value.last_exception, ValueError)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_timeout(self):
        """Test retry timeout functionality."""
        call_count = 0

        policy = RetryPolicy(timeout=0.1)  # Very short timeout

        @async_retry(policy=policy, delay=0.05)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")

        with pytest.raises((MaxRetriesExceededError, RetryTimeoutError)):
            await test_function()

        # Should have made at least one attempt
        assert call_count >= 1
