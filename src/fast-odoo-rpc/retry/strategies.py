"""
Retry strategies for OdooFlow.

This module provides different retry strategies with various backoff algorithms,
including exponential backoff with full jitter, adaptive strategies, and
async/await compatibility following industry best practices.
"""

import asyncio
import random
import time
import threading
from abc import ABC, abstractmethod
from typing import Optional, Any, Callable
from dataclasses import dataclass, field


@dataclass
class RetryAttempt:
    """Information about a retry attempt with comprehensive context.

    This class provides detailed information about each retry attempt,
    including timing, outcome, and context for debugging and monitoring.

    Attributes:
        attempt_number: Current attempt number (1-based)
        delay: Delay before this attempt (in seconds)
        exception: Exception that occurred (if any)
        start_time: When the attempt started
        end_time: When the attempt ended
        outcome: Result of the attempt (if successful)
        retry_state: Additional retry state information
    """

    attempt_number: int
    delay: float = 0.0
    exception: Optional[Exception] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    outcome: Optional[Any] = None
    retry_state: Optional[dict] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get attempt duration in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def succeeded(self) -> bool:
        """Check if attempt succeeded (no exception)."""
        return self.exception is None

    @property
    def failed(self) -> bool:
        """Check if attempt failed (has exception)."""
        return self.exception is not None

    def mark_completed(
        self,
        outcome: Optional[Any] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """Mark attempt as completed with outcome or exception."""
        self.end_time = time.time()
        self.outcome = outcome
        self.exception = exception


class RetryStrategy(ABC):
    """Base class for retry strategies with async support and full jitter.

    This class provides the foundation for all retry strategies, including
    support for async operations, configurable jitter algorithms, and
    comprehensive retry decision logic.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize retry strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            max_delay: Maximum delay between attempts
            jitter: Whether to add random jitter to delays
            jitter_type: Type of jitter ('full', 'equal', 'decorrelated')
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if max_delay < 0:
            raise ValueError("max_delay must be non-negative")

        self.max_attempts = max_attempts
        self.max_delay = max_delay
        self.jitter = jitter
        self.jitter_type = jitter_type

    @abstractmethod
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        pass

    def get_delay(self, attempt: int) -> float:
        """Get delay with optional jitter using specified algorithm.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds with jitter applied
        """
        base_delay = self.calculate_delay(attempt)

        # Apply maximum delay limit
        base_delay = min(base_delay, self.max_delay)

        # Apply jitter if enabled
        if not self.jitter or base_delay <= 0:
            return max(0, base_delay)

        return self._apply_jitter(base_delay)

    def _apply_jitter(self, delay: float) -> float:
        """Apply jitter to delay using specified algorithm.

        Args:
            delay: Base delay in seconds

        Returns:
            Delay with jitter applied
        """
        if self.jitter_type == "full":
            # Full jitter: random between 0 and delay
            return random.uniform(0, delay)  # nosec B311
        elif self.jitter_type == "equal":
            # Equal jitter: delay/2 + random(0, delay/2)
            half_delay = delay / 2
            return half_delay + random.uniform(0, half_delay)  # nosec B311
        elif self.jitter_type == "decorrelated":
            # Decorrelated jitter: random between base/3 and delay
            return random.uniform(delay / 3, delay)  # nosec B311
        else:
            # Default: ±25% jitter (legacy behavior)
            jitter_range = delay * 0.25
            jittered = delay + random.uniform(-jitter_range, jitter_range)  # nosec B311
            return max(0, jittered)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Check if should retry based on attempt and exception.

        Args:
            attempt: Current attempt number (1-based)
            exception: Exception that occurred

        Returns:
            True if should retry
        """
        return attempt < self.max_attempts

    async def async_sleep(self, delay: float) -> None:
        """Async sleep for the specified delay.

        Args:
            delay: Delay in seconds
        """
        if delay > 0:
            await asyncio.sleep(delay)

    def sync_sleep(self, delay: float) -> None:
        """Synchronous sleep for the specified delay.

        Args:
            delay: Delay in seconds
        """
        if delay > 0:
            time.sleep(delay)

    def create_attempt(
        self, attempt_number: int, delay: float = 0.0
    ) -> RetryAttempt:
        """Create a new RetryAttempt instance.

        Args:
            attempt_number: Current attempt number
            delay: Delay before this attempt

        Returns:
            New RetryAttempt instance
        """
        return RetryAttempt(
            attempt_number=attempt_number,
            delay=delay,
            retry_state={"strategy": self.__class__.__name__}
        )


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff retry strategy with configurable parameters.

    This strategy implements exponential backoff with optional jitter,
    following industry best practices for distributed systems.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize exponential backoff strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            multiplier: Exponential multiplier (typically 2.0)
            max_delay: Maximum delay between attempts
            jitter: Whether to add random jitter to delays
            jitter_type: Type of jitter algorithm to use
        """
        super().__init__(max_attempts, max_delay, jitter, jitter_type)

        if base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if multiplier <= 0:
            raise ValueError("multiplier must be positive")

        self.base_delay = base_delay
        self.multiplier = multiplier

    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Calculated delay in seconds
        """
        if attempt < 1:
            return 0.0

        # Calculate exponential delay: base_delay * multiplier^(attempt-1)
        delay = self.base_delay * (self.multiplier ** (attempt - 1))

        # Prevent overflow for very large attempts
        return min(delay, self.max_delay)


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        """Initialize linear backoff strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            increment: Linear increment per attempt
            max_delay: Maximum delay between attempts
            jitter: Whether to add random jitter to delays
        """
        super().__init__(max_attempts, max_delay, jitter)
        self.base_delay = base_delay
        self.increment = increment

    def calculate_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay."""
        return self.base_delay + (self.increment * (attempt - 1))


class FixedDelayStrategy(RetryStrategy):
    """Fixed delay retry strategy."""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize fixed delay strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            delay: Fixed delay in seconds
            jitter: Whether to add random jitter to delays
            jitter_type: Type of jitter algorithm to use
        """
        super().__init__(max_attempts, delay, jitter, jitter_type)
        self.delay = delay

    def calculate_delay(self, attempt: int) -> float:
        """Calculate fixed delay."""
        return self.delay


class AdaptiveStrategy(RetryStrategy):
    """Adaptive retry strategy that adjusts based on success rate.

    This strategy monitors success rates and adapts its backoff behavior
    accordingly. It uses thread-safe statistics tracking and implements
    sophisticated adaptation algorithms.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full",
        success_threshold: float = 0.8,
        adaptation_window: int = 100,
        min_samples: int = 10
    ):
        """Initialize adaptive strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay between attempts
            jitter: Whether to add random jitter to delays
            jitter_type: Type of jitter algorithm to use
            success_threshold: Success rate threshold for adaptation
            adaptation_window: Window size for success rate calculation
            min_samples: Minimum samples before adaptation kicks in
        """
        super().__init__(max_attempts, max_delay, jitter, jitter_type)

        if not 0 <= success_threshold <= 1:
            raise ValueError("success_threshold must be between 0 and 1")
        if adaptation_window < 1:
            raise ValueError("adaptation_window must be positive")
        if min_samples < 1:
            raise ValueError("min_samples must be positive")

        self.base_delay = base_delay
        self.success_threshold = success_threshold
        self.adaptation_window = adaptation_window
        self.min_samples = min_samples

        # Thread-safe statistics tracking
        self._lock = threading.Lock()
        self._attempts_history = []
        self._total_attempts = 0
        self._successful_attempts = 0

    def calculate_delay(self, attempt: int) -> float:
        """Calculate adaptive delay based on current success rate.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Calculated delay in seconds
        """
        success_rate = self.get_success_rate()

        # If we don't have enough samples, use conservative exponential backoff
        if self._total_attempts < self.min_samples:
            multiplier = 2.0 ** (attempt - 1)
        elif success_rate < self.success_threshold:
            # Poor success rate: aggressive exponential backoff
            multiplier = 3.0 ** (attempt - 1)
        elif success_rate > 0.95:
            # Excellent success rate: minimal backoff
            multiplier = 1.0 + (attempt - 1) * 0.5
        else:
            # Good success rate: moderate exponential backoff
            multiplier = 1.5 ** (attempt - 1)

        return self.base_delay * multiplier

    def get_success_rate(self) -> float:
        """Get current success rate in a thread-safe manner.

        Returns:
            Success rate between 0.0 and 1.0
        """
        with self._lock:
            if self._total_attempts == 0:
                return 1.0
            return self._successful_attempts / self._total_attempts

    def record_attempt(self, success: bool) -> None:
        """Record attempt result for adaptation in a thread-safe manner.

        Args:
            success: Whether the attempt was successful
        """
        with self._lock:
            # Add to history
            self._attempts_history.append(success)

            # Maintain sliding window
            if len(self._attempts_history) > self.adaptation_window:
                removed = self._attempts_history.pop(0)
                if removed:
                    self._successful_attempts -= 1
                self._total_attempts -= 1

            # Update counters
            self._total_attempts += 1
            if success:
                self._successful_attempts += 1

    def get_statistics(self) -> dict:
        """Get current statistics in a thread-safe manner.

        Returns:
            Dictionary with current statistics
        """
        with self._lock:
            # Calculate success rate directly to avoid deadlock
            if self._total_attempts == 0:
                success_rate = 1.0
            else:
                success_rate = self._successful_attempts / self._total_attempts
            return {
                "total_attempts": self._total_attempts,
                "successful_attempts": self._successful_attempts,
                "success_rate": success_rate,
                "window_size": len(self._attempts_history),
                "adaptation_active": self._total_attempts >= self.min_samples
            }

    def reset_statistics(self) -> None:
        """Reset all statistics in a thread-safe manner."""
        with self._lock:
            self._attempts_history.clear()
            self._total_attempts = 0
            self._successful_attempts = 0


class DecorrelatedJitterStrategy(RetryStrategy):
    """Decorrelated jitter strategy for optimal backoff distribution.

    This strategy implements the decorrelated jitter algorithm which provides
    better distribution of retry attempts across time, reducing thundering herd
    effects in distributed systems.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        cap: float = 20.0
    ):
        """Initialize decorrelated jitter strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay between attempts
            cap: Cap for decorrelated jitter calculation
        """
        super().__init__(
            max_attempts, max_delay, jitter=True, jitter_type="decorrelated"
        )
        self.base_delay = base_delay
        self.cap = cap
        self._previous_delay = base_delay

    def calculate_delay(self, attempt: int) -> float:
        """Calculate decorrelated jitter delay.

        The decorrelated jitter algorithm uses the formula:
        delay = random_between(base_delay, previous_delay * 3)

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Calculated delay in seconds
        """
        if attempt == 1:
            self._previous_delay = self.base_delay
            return self.base_delay

        # Decorrelated jitter: random between base and 3x previous delay
        min_delay = self.base_delay
        max_delay = min(self._previous_delay * 3, self.cap)

        delay = random.uniform(min_delay, max_delay)  # nosec B311
        self._previous_delay = delay

        return delay


class FibonacciBackoffStrategy(RetryStrategy):
    """Fibonacci sequence backoff strategy.

    This strategy uses the Fibonacci sequence for delay calculation,
    providing a middle ground between linear and exponential backoff.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize Fibonacci backoff strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay multiplier in seconds
            max_delay: Maximum delay between attempts
            jitter: Whether to add random jitter to delays
            jitter_type: Type of jitter algorithm to use
        """
        super().__init__(max_attempts, max_delay, jitter, jitter_type)
        self.base_delay = base_delay
        self._fib_cache = {}

    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number with memoization.

        Args:
            n: Position in Fibonacci sequence

        Returns:
            Fibonacci number at position n
        """
        if n in self._fib_cache:
            return self._fib_cache[n]

        if n <= 1:
            result = n
        else:
            result = self._fibonacci(n - 1) + self._fibonacci(n - 2)

        self._fib_cache[n] = result
        return result

    def calculate_delay(self, attempt: int) -> float:
        """Calculate Fibonacci backoff delay.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Calculated delay in seconds
        """
        if attempt < 1:
            return 0.0

        # Use Fibonacci sequence for delay calculation
        fib_number = self._fibonacci(attempt)
        return self.base_delay * fib_number


# Convenience factory functions for common strategies
def exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> ExponentialBackoffStrategy:
    """Create an exponential backoff strategy with common defaults.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        multiplier: Exponential multiplier
        max_delay: Maximum delay between attempts
        jitter: Whether to add full jitter

    Returns:
        Configured ExponentialBackoffStrategy
    """
    return ExponentialBackoffStrategy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        multiplier=multiplier,
        max_delay=max_delay,
        jitter=jitter,
        jitter_type="full" if jitter else None
    )


def adaptive_strategy(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    success_threshold: float = 0.8,
    adaptation_window: int = 100
) -> AdaptiveStrategy:
    """Create an adaptive strategy with common defaults.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        success_threshold: Success rate threshold for adaptation
        adaptation_window: Window size for success rate calculation

    Returns:
        Configured AdaptiveStrategy
    """
    return AdaptiveStrategy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        success_threshold=success_threshold,
        adaptation_window=adaptation_window,
        jitter=True,
        jitter_type="full"
    )
