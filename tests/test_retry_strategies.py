"""
Comprehensive tests for retry/strategies.py.

This module tests all retry strategy classes and functionality with focus on:
- RetryAttempt class behavior and timing
- Strategy delay calculations and jitter algorithms
- Async/await compatibility and sleep functions
- Thread-safe statistics tracking
- Adaptive strategy behavior and adaptation
- Advanced strategies (Fibonacci, Decorrelated Jitter)
- Factory functions and convenience methods
"""

import asyncio
import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from src.zenoo_rpc.retry.strategies import (
    RetryAttempt,
    RetryStrategy,
    ExponentialBackoffStrategy,
    LinearBackoffStrategy,
    FixedDelayStrategy,
    AdaptiveStrategy,
    DecorrelatedJitterStrategy,
    FibonacciBackoffStrategy,
    exponential_backoff,
    adaptive_strategy,
)


class TestRetryAttempt:
    """Test RetryAttempt class."""

    def test_basic_creation(self):
        """Test basic RetryAttempt creation."""
        attempt = RetryAttempt(attempt_number=1, delay=1.0)
        
        assert attempt.attempt_number == 1
        assert attempt.delay == 1.0
        assert attempt.exception is None
        assert attempt.outcome is None
        assert isinstance(attempt.start_time, float)
        assert attempt.end_time is None
        assert isinstance(attempt.retry_state, dict)

    def test_duration_calculation(self):
        """Test duration calculation."""
        attempt = RetryAttempt(attempt_number=1)
        
        # Duration should be calculated from start_time
        duration1 = attempt.duration
        time.sleep(0.01)  # Small delay
        duration2 = attempt.duration
        
        assert duration2 > duration1
        assert duration1 >= 0

    def test_duration_with_end_time(self):
        """Test duration calculation with end_time set."""
        start_time = time.time()
        end_time = start_time + 2.5
        
        attempt = RetryAttempt(
            attempt_number=1,
            start_time=start_time,
            end_time=end_time
        )
        
        assert attempt.duration == 2.5

    def test_success_properties(self):
        """Test succeeded and failed properties."""
        # Successful attempt
        success_attempt = RetryAttempt(attempt_number=1)
        assert success_attempt.succeeded is True
        assert success_attempt.failed is False
        
        # Failed attempt
        failed_attempt = RetryAttempt(
            attempt_number=1, 
            exception=ValueError("test error")
        )
        assert failed_attempt.succeeded is False
        assert failed_attempt.failed is True

    def test_mark_completed_success(self):
        """Test marking attempt as completed successfully."""
        attempt = RetryAttempt(attempt_number=1)
        outcome = {"result": "success"}
        
        attempt.mark_completed(outcome=outcome)
        
        assert attempt.end_time is not None
        assert attempt.outcome == outcome
        assert attempt.exception is None
        assert attempt.succeeded is True

    def test_mark_completed_failure(self):
        """Test marking attempt as completed with failure."""
        attempt = RetryAttempt(attempt_number=1)
        exception = ValueError("test error")
        
        attempt.mark_completed(exception=exception)
        
        assert attempt.end_time is not None
        assert attempt.outcome is None
        assert attempt.exception == exception
        assert attempt.failed is True

    def test_retry_state_default(self):
        """Test default retry state."""
        attempt = RetryAttempt(attempt_number=1)
        
        assert isinstance(attempt.retry_state, dict)
        assert len(attempt.retry_state) == 0

    def test_retry_state_custom(self):
        """Test custom retry state."""
        custom_state = {"strategy": "exponential", "multiplier": 2.0}
        attempt = RetryAttempt(attempt_number=1, retry_state=custom_state)
        
        assert attempt.retry_state == custom_state


class TestRetryStrategyBase:
    """Test RetryStrategy base class."""

    def test_abstract_instantiation_error(self):
        """Test that RetryStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RetryStrategy()

    def test_validation_max_attempts(self):
        """Test validation of max_attempts parameter."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        # Valid max_attempts
        strategy = TestStrategy(max_attempts=3)
        assert strategy.max_attempts == 3
        
        # Invalid max_attempts
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            TestStrategy(max_attempts=0)

    def test_validation_max_delay(self):
        """Test validation of max_delay parameter."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        # Valid max_delay
        strategy = TestStrategy(max_delay=60.0)
        assert strategy.max_delay == 60.0
        
        # Invalid max_delay
        with pytest.raises(ValueError, match="max_delay must be non-negative"):
            TestStrategy(max_delay=-1.0)

    def test_jitter_types(self):
        """Test different jitter types."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 10.0
        
        # Test all jitter types
        jitter_types = ["full", "equal", "decorrelated", "legacy"]
        
        for jitter_type in jitter_types:
            strategy = TestStrategy(jitter=True, jitter_type=jitter_type)
            delay = strategy.get_delay(1)
            assert delay >= 0

    def test_full_jitter(self):
        """Test full jitter algorithm."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 10.0
        
        strategy = TestStrategy(jitter=True, jitter_type="full")
        
        # Test multiple delays to ensure randomness
        delays = [strategy.get_delay(1) for _ in range(100)]
        
        # All delays should be between 0 and 10
        assert all(0 <= delay <= 10 for delay in delays)
        # Should have some variation
        assert len(set(delays)) > 10

    def test_equal_jitter(self):
        """Test equal jitter algorithm."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 10.0
        
        strategy = TestStrategy(jitter=True, jitter_type="equal")
        
        # Test multiple delays
        delays = [strategy.get_delay(1) for _ in range(100)]
        
        # All delays should be between 5 and 10 (half + random half)
        assert all(5 <= delay <= 10 for delay in delays)

    def test_decorrelated_jitter(self):
        """Test decorrelated jitter algorithm."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 9.0
        
        strategy = TestStrategy(jitter=True, jitter_type="decorrelated")
        
        # Test multiple delays
        delays = [strategy.get_delay(1) for _ in range(100)]
        
        # All delays should be between 3 and 9 (delay/3 to delay)
        assert all(3 <= delay <= 9 for delay in delays)

    def test_no_jitter(self):
        """Test strategy without jitter."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 5.0
        
        strategy = TestStrategy(jitter=False)
        
        # All delays should be exactly 5.0
        for _ in range(10):
            assert strategy.get_delay(1) == 5.0

    def test_max_delay_enforcement(self):
        """Test that max_delay is enforced."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 100.0  # Exceeds max_delay
        
        strategy = TestStrategy(max_delay=60.0, jitter=False)
        delay = strategy.get_delay(1)
        
        assert delay == 60.0

    def test_should_retry_default(self):
        """Test default should_retry behavior."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        strategy = TestStrategy(max_attempts=3)
        
        assert strategy.should_retry(1, Exception()) is True
        assert strategy.should_retry(2, Exception()) is True
        assert strategy.should_retry(3, Exception()) is False
        assert strategy.should_retry(4, Exception()) is False

    @pytest.mark.asyncio
    async def test_async_sleep(self):
        """Test async sleep functionality."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        strategy = TestStrategy()
        
        start_time = time.time()
        await strategy.async_sleep(0.1)
        end_time = time.time()
        
        # Should have slept for approximately 0.1 seconds
        assert 0.05 <= (end_time - start_time) <= 0.2

    @pytest.mark.asyncio
    async def test_async_sleep_zero_delay(self):
        """Test async sleep with zero delay."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        strategy = TestStrategy()
        
        start_time = time.time()
        await strategy.async_sleep(0.0)
        end_time = time.time()
        
        # Should return immediately
        assert (end_time - start_time) < 0.01

    def test_sync_sleep(self):
        """Test synchronous sleep functionality."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        strategy = TestStrategy()
        
        start_time = time.time()
        strategy.sync_sleep(0.1)
        end_time = time.time()
        
        # Should have slept for approximately 0.1 seconds
        assert 0.05 <= (end_time - start_time) <= 0.2

    def test_create_attempt(self):
        """Test create_attempt method."""
        class TestStrategy(RetryStrategy):
            def calculate_delay(self, attempt: int) -> float:
                return 1.0
        
        strategy = TestStrategy()
        attempt = strategy.create_attempt(attempt_number=2, delay=1.5)
        
        assert attempt.attempt_number == 2
        assert attempt.delay == 1.5
        assert attempt.retry_state["strategy"] == "TestStrategy"


class TestExponentialBackoffStrategy:
    """Test ExponentialBackoffStrategy class."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = ExponentialBackoffStrategy()

        assert strategy.max_attempts == 3
        assert strategy.base_delay == 1.0
        assert strategy.multiplier == 2.0
        assert strategy.max_delay == 60.0
        assert strategy.jitter is True

    def test_custom_parameters(self):
        """Test strategy with custom parameters."""
        strategy = ExponentialBackoffStrategy(
            max_attempts=5,
            base_delay=2.0,
            multiplier=3.0,
            max_delay=120.0,
            jitter=False
        )

        assert strategy.max_attempts == 5
        assert strategy.base_delay == 2.0
        assert strategy.multiplier == 3.0
        assert strategy.max_delay == 120.0
        assert strategy.jitter is False

    def test_parameter_validation(self):
        """Test parameter validation."""
        # Valid parameters
        ExponentialBackoffStrategy(base_delay=0.0, multiplier=1.0)

        # Invalid base_delay
        with pytest.raises(
            ValueError, match="base_delay must be non-negative"
        ):
            ExponentialBackoffStrategy(base_delay=-1.0)

        # Invalid multiplier
        with pytest.raises(ValueError, match="multiplier must be positive"):
            ExponentialBackoffStrategy(multiplier=0.0)

    def test_delay_calculation(self):
        """Test exponential delay calculation."""
        strategy = ExponentialBackoffStrategy(
            base_delay=1.0,
            multiplier=2.0,
            jitter=False
        )

        # Test exponential progression: 1, 2, 4, 8, 16...
        assert strategy.calculate_delay(1) == 1.0
        assert strategy.calculate_delay(2) == 2.0
        assert strategy.calculate_delay(3) == 4.0
        assert strategy.calculate_delay(4) == 8.0
        assert strategy.calculate_delay(5) == 16.0

    def test_delay_with_custom_multiplier(self):
        """Test delay calculation with custom multiplier."""
        strategy = ExponentialBackoffStrategy(
            base_delay=2.0,
            multiplier=3.0,
            jitter=False
        )

        # Test progression: 2, 6, 18, 54...
        assert strategy.calculate_delay(1) == 2.0
        assert strategy.calculate_delay(2) == 6.0
        assert strategy.calculate_delay(3) == 18.0
        assert strategy.calculate_delay(4) == 54.0

    def test_delay_overflow_protection(self):
        """Test protection against delay overflow."""
        strategy = ExponentialBackoffStrategy(
            base_delay=1.0,
            multiplier=2.0,
            max_delay=60.0,
            jitter=False
        )

        # Very large attempt should not cause overflow
        delay = strategy.calculate_delay(100)
        assert delay <= strategy.max_delay * 10

    def test_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        strategy = ExponentialBackoffStrategy(
            base_delay=10.0,
            multiplier=2.0,
            jitter=True,
            jitter_type="full"
        )

        # Test multiple delays to ensure randomness
        delays = [strategy.get_delay(2) for _ in range(100)]

        # Base delay for attempt 2 should be 20.0
        # With full jitter, should be between 0 and 20
        assert all(0 <= delay <= 20 for delay in delays)
        # Should have variation
        assert len(set(delays)) > 10

    def test_zero_attempt_handling(self):
        """Test handling of zero or negative attempts."""
        strategy = ExponentialBackoffStrategy()

        assert strategy.calculate_delay(0) == 0.0
        assert strategy.calculate_delay(-1) == 0.0


class TestLinearBackoffStrategy:
    """Test LinearBackoffStrategy class."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = LinearBackoffStrategy()

        assert strategy.max_attempts == 3
        assert strategy.base_delay == 1.0
        assert strategy.increment == 1.0

    def test_delay_calculation(self):
        """Test linear delay calculation."""
        strategy = LinearBackoffStrategy(
            base_delay=2.0,
            increment=3.0,
            jitter=False
        )

        # Test linear progression: 2, 5, 8, 11...
        assert strategy.calculate_delay(1) == 2.0
        assert strategy.calculate_delay(2) == 5.0
        assert strategy.calculate_delay(3) == 8.0
        assert strategy.calculate_delay(4) == 11.0

    def test_zero_increment(self):
        """Test linear strategy with zero increment."""
        strategy = LinearBackoffStrategy(
            base_delay=5.0,
            increment=0.0,
            jitter=False
        )

        # Should always return base_delay
        assert strategy.calculate_delay(1) == 5.0
        assert strategy.calculate_delay(2) == 5.0
        assert strategy.calculate_delay(3) == 5.0


class TestFixedDelayStrategy:
    """Test FixedDelayStrategy class."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = FixedDelayStrategy()

        assert strategy.max_attempts == 3
        assert strategy.delay == 1.0

    def test_delay_calculation(self):
        """Test fixed delay calculation."""
        strategy = FixedDelayStrategy(delay=5.0, jitter=False)

        # Should always return the same delay
        assert strategy.calculate_delay(1) == 5.0
        assert strategy.calculate_delay(2) == 5.0
        assert strategy.calculate_delay(3) == 5.0
        assert strategy.calculate_delay(10) == 5.0

    def test_delay_with_jitter(self):
        """Test fixed delay with jitter."""
        strategy = FixedDelayStrategy(
            delay=10.0, jitter=True, jitter_type="full"
        )

        # Test multiple delays
        delays = [strategy.get_delay(1) for _ in range(100)]

        # With full jitter, should be between 0 and 10
        assert all(0 <= delay <= 10 for delay in delays)


class TestAdaptiveStrategy:
    """Test AdaptiveStrategy class."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = AdaptiveStrategy()

        assert strategy.max_attempts == 5
        assert strategy.base_delay == 1.0
        assert strategy.success_threshold == 0.8
        assert strategy.adaptation_window == 100
        assert strategy.min_samples == 10

    def test_parameter_validation(self):
        """Test parameter validation."""
        # Valid parameters
        AdaptiveStrategy(
            success_threshold=0.5, adaptation_window=50, min_samples=5
        )

        # Invalid success_threshold
        with pytest.raises(
            ValueError, match="success_threshold must be between 0 and 1"
        ):
            AdaptiveStrategy(success_threshold=1.5)

        with pytest.raises(
            ValueError, match="success_threshold must be between 0 and 1"
        ):
            AdaptiveStrategy(success_threshold=-0.1)

        # Invalid adaptation_window
        with pytest.raises(
            ValueError, match="adaptation_window must be positive"
        ):
            AdaptiveStrategy(adaptation_window=0)

        # Invalid min_samples
        with pytest.raises(ValueError, match="min_samples must be positive"):
            AdaptiveStrategy(min_samples=0)

    def test_initial_success_rate(self):
        """Test initial success rate."""
        strategy = AdaptiveStrategy()

        # Should start with 100% success rate
        assert strategy.get_success_rate() == 1.0

    def test_record_attempts(self):
        """Test recording attempts."""
        strategy = AdaptiveStrategy()

        # Record some attempts
        strategy.record_attempt(True)
        strategy.record_attempt(True)
        strategy.record_attempt(False)

        # Success rate should be 2/3
        assert abs(strategy.get_success_rate() - (2/3)) < 0.001

    def test_thread_safety(self):
        """Test thread-safe statistics tracking."""
        strategy = AdaptiveStrategy()

        def record_attempts():
            for _ in range(100):
                strategy.record_attempt(True)

        # Run multiple threads
        threads = [threading.Thread(target=record_attempts) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have recorded attempts up to sliding window size (100)
        # Due to sliding window, total_attempts will be capped at adaptation_window
        stats = strategy.get_statistics()
        assert stats["total_attempts"] == 100  # Sliding window size
        assert stats["successful_attempts"] == 100
        assert stats["success_rate"] == 1.0
        assert stats["window_size"] == 100

    def test_sliding_window(self):
        """Test sliding window behavior."""
        strategy = AdaptiveStrategy(adaptation_window=3)

        # Fill window
        strategy.record_attempt(True)   # [T]
        strategy.record_attempt(True)   # [T, T]
        strategy.record_attempt(False)  # [T, T, F]

        assert abs(strategy.get_success_rate() - (2/3)) < 0.001

        # Add one more (should remove first)
        strategy.record_attempt(True)   # [T, F, T]

        assert abs(strategy.get_success_rate() - (2/3)) < 0.001

    def test_adaptation_behavior(self):
        """Test adaptation behavior based on success rate."""
        strategy = AdaptiveStrategy(
            success_threshold=0.8,
            min_samples=5,
            jitter=False
        )

        # Record poor success rate
        for _ in range(3):
            strategy.record_attempt(True)
        for _ in range(7):
            strategy.record_attempt(False)

        # Success rate should be 30%, below threshold
        assert strategy.get_success_rate() == 0.3

        # Should use aggressive backoff
        delay1 = strategy.calculate_delay(1)
        delay2 = strategy.calculate_delay(2)

        # Should be exponential with multiplier 3.0
        assert delay2 > delay1 * 2.5

    def test_reset_statistics(self):
        """Test statistics reset."""
        strategy = AdaptiveStrategy()

        # Record some attempts
        strategy.record_attempt(True)
        strategy.record_attempt(False)

        assert strategy.get_success_rate() == 0.5

        # Reset
        strategy.reset_statistics()

        assert strategy.get_success_rate() == 1.0
        stats = strategy.get_statistics()
        assert stats["total_attempts"] == 0


class TestDecorrelatedJitterStrategy:
    """Test DecorrelatedJitterStrategy class."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = DecorrelatedJitterStrategy()

        assert strategy.max_attempts == 3
        assert strategy.base_delay == 1.0
        assert strategy.cap == 20.0

    def test_first_attempt_delay(self):
        """Test first attempt delay."""
        strategy = DecorrelatedJitterStrategy(base_delay=5.0)

        # First attempt should return base_delay
        delay = strategy.calculate_delay(1)
        assert delay == 5.0

    def test_decorrelated_progression(self):
        """Test decorrelated jitter progression."""
        strategy = DecorrelatedJitterStrategy(base_delay=1.0, cap=100.0)

        # Calculate multiple delays
        delays = []
        for attempt in range(1, 6):
            delay = strategy.calculate_delay(attempt)
            delays.append(delay)

        # First delay should be base_delay
        assert delays[0] == 1.0

        # Subsequent delays should be random but within bounds
        for i in range(1, len(delays)):
            assert delays[i] >= 1.0  # At least base_delay
            assert delays[i] <= strategy.cap  # At most cap

    def test_cap_enforcement(self):
        """Test that cap is enforced."""
        strategy = DecorrelatedJitterStrategy(base_delay=1.0, cap=10.0)

        # Run many attempts to test cap
        for attempt in range(1, 20):
            delay = strategy.calculate_delay(attempt)
            assert delay <= 10.0


class TestFibonacciBackoffStrategy:
    """Test FibonacciBackoffStrategy class."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = FibonacciBackoffStrategy()

        assert strategy.max_attempts == 3
        assert strategy.base_delay == 1.0

    def test_fibonacci_sequence(self):
        """Test Fibonacci sequence calculation."""
        strategy = FibonacciBackoffStrategy(base_delay=1.0, jitter=False)

        # Test Fibonacci progression: 1, 1, 2, 3, 5, 8, 13...
        expected_delays = [1.0, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0]

        for attempt, expected in enumerate(expected_delays, 1):
            delay = strategy.calculate_delay(attempt)
            assert delay == expected

    def test_fibonacci_with_multiplier(self):
        """Test Fibonacci with base delay multiplier."""
        strategy = FibonacciBackoffStrategy(base_delay=2.0, jitter=False)

        # Should multiply Fibonacci numbers by base_delay
        expected_delays = [2.0, 2.0, 4.0, 6.0, 10.0, 16.0, 26.0]

        for attempt, expected in enumerate(expected_delays, 1):
            delay = strategy.calculate_delay(attempt)
            assert delay == expected

    def test_fibonacci_memoization(self):
        """Test that Fibonacci calculation uses memoization."""
        strategy = FibonacciBackoffStrategy()

        # Calculate same Fibonacci number multiple times
        fib_10_1 = strategy._fibonacci(10)
        fib_10_2 = strategy._fibonacci(10)

        assert fib_10_1 == fib_10_2
        assert 10 in strategy._fib_cache

    def test_zero_attempt_handling(self):
        """Test handling of zero or negative attempts."""
        strategy = FibonacciBackoffStrategy()

        assert strategy.calculate_delay(0) == 0.0
        assert strategy.calculate_delay(-1) == 0.0


class TestFactoryFunctions:
    """Test factory functions."""

    def test_exponential_backoff_factory(self):
        """Test exponential_backoff factory function."""
        strategy = exponential_backoff(
            max_attempts=5,
            base_delay=2.0,
            multiplier=3.0,
            max_delay=120.0,
            jitter=True
        )

        assert isinstance(strategy, ExponentialBackoffStrategy)
        assert strategy.max_attempts == 5
        assert strategy.base_delay == 2.0
        assert strategy.multiplier == 3.0
        assert strategy.max_delay == 120.0
        assert strategy.jitter is True
        assert strategy.jitter_type == "full"

    def test_exponential_backoff_no_jitter(self):
        """Test exponential_backoff factory without jitter."""
        strategy = exponential_backoff(jitter=False)

        assert strategy.jitter is False
        assert strategy.jitter_type is None

    def test_adaptive_strategy_factory(self):
        """Test adaptive_strategy factory function."""
        strategy = adaptive_strategy(
            max_attempts=7,
            base_delay=3.0,
            success_threshold=0.9,
            adaptation_window=200
        )

        assert isinstance(strategy, AdaptiveStrategy)
        assert strategy.max_attempts == 7
        assert strategy.base_delay == 3.0
        assert strategy.success_threshold == 0.9
        assert strategy.adaptation_window == 200
        assert strategy.jitter is True
        assert strategy.jitter_type == "full"


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """Test complete async retry workflow."""
        strategy = ExponentialBackoffStrategy(
            max_attempts=3,
            base_delay=0.01,  # Small delay for testing
            jitter=False
        )

        attempts = []

        for attempt_num in range(1, 4):
            # Create attempt
            attempt = strategy.create_attempt(attempt_num)
            attempts.append(attempt)

            # Calculate delay
            delay = strategy.get_delay(attempt_num)

            # Async sleep
            start_time = time.time()
            await strategy.async_sleep(delay)
            end_time = time.time()

            # Mark completed
            attempt.mark_completed(outcome=f"result_{attempt_num}")

            # Verify timing
            actual_delay = end_time - start_time
            expected_delay = strategy.calculate_delay(attempt_num)
            assert abs(actual_delay - expected_delay) < 0.05

        # Verify all attempts
        assert len(attempts) == 3
        for i, attempt in enumerate(attempts, 1):
            assert attempt.attempt_number == i
            assert attempt.succeeded is True
            assert attempt.outcome == f"result_{i}"

    def test_strategy_comparison(self):
        """Test comparison between different strategies."""
        strategies = [
            ExponentialBackoffStrategy(jitter=False),
            LinearBackoffStrategy(jitter=False),
            FixedDelayStrategy(jitter=False),
            FibonacciBackoffStrategy(jitter=False)
        ]

        # Compare delays for first 5 attempts
        for attempt in range(1, 6):
            delays = [
                strategy.calculate_delay(attempt) for strategy in strategies
            ]

            # All should be positive
            assert all(delay >= 0 for delay in delays)

            # Exponential should grow fastest (after attempt 3)
            if attempt > 3:
                exp_delay = delays[0]  # ExponentialBackoffStrategy
                lin_delay = delays[1]  # LinearBackoffStrategy
                assert exp_delay > lin_delay
