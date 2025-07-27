"""
Retry policies for OdooFlow.

This module provides retry policies that determine when and how to retry
operations, including circuit breaker integration, timeout management, and
custom retry conditions following industry best practices for distributed
systems.
"""

import time
import logging
from typing import Type, Callable, Optional, Set, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .strategies import RetryStrategy, ExponentialBackoffStrategy, RetryAttempt


logger = logging.getLogger(__name__)


class RetryDecision(Enum):
    """Retry decision enumeration."""
    RETRY = "retry"
    STOP = "stop"
    CIRCUIT_OPEN = "circuit_open"
    TIMEOUT = "timeout"
    NON_RETRYABLE = "non_retryable"


@dataclass
class RetryContext:
    """Context information for retry decisions.

    This class provides comprehensive context for making retry decisions,
    including timing information, attempt history, and custom metadata.
    """

    attempt_number: int
    exception: Exception
    start_time: float
    last_attempt_time: Optional[float] = None
    total_delay: float = 0.0
    attempts_history: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_time(self) -> float:
        """Get total elapsed time since first attempt."""
        return time.time() - self.start_time

    @property
    def time_since_last_attempt(self) -> Optional[float]:
        """Get time since last attempt."""
        if self.last_attempt_time is None:
            return None
        return time.time() - self.last_attempt_time

    def add_attempt(self, attempt: RetryAttempt) -> None:
        """Add attempt to history."""
        self.attempts_history.append(attempt)
        self.last_attempt_time = time.time()
        if attempt.delay > 0:
            self.total_delay += attempt.delay


@dataclass
class RetryPolicy:
    """Enhanced retry policy configuration with circuit breaker support.

    This class provides comprehensive retry policy configuration including
    timeout management, exception filtering, custom retry conditions, and
    circuit breaker integration hooks.
    """

    strategy: RetryStrategy = field(
        default_factory=lambda: ExponentialBackoffStrategy()
    )
    retryable_exceptions: Set[Type[Exception]] = field(default_factory=set)
    non_retryable_exceptions: Set[Type[Exception]] = field(default_factory=set)
    timeout: Optional[float] = None
    retry_condition: Optional[Callable[[Exception], bool]] = None

    # Enhanced features
    circuit_breaker_hook: Optional[Callable[[RetryContext], bool]] = None
    idempotency_check: Optional[Callable[[RetryContext], bool]] = None
    graceful_degradation: Optional[Callable[[RetryContext], Any]] = None
    max_total_delay: Optional[float] = None
    backoff_multiplier_on_failure: float = 1.0
    success_callback: Optional[Callable[[RetryContext], None]] = None
    failure_callback: Optional[Callable[[RetryContext], None]] = None

    def should_retry(
        self, attempt: int, exception: Exception, start_time: float
    ) -> bool:
        """Check if operation should be retried (legacy interface).

        Args:
            attempt: Current attempt number (1-based)
            exception: Exception that occurred
            start_time: Start time of first attempt

        Returns:
            True if should retry
        """
        context = RetryContext(
            attempt_number=attempt,
            exception=exception,
            start_time=start_time
        )
        decision = self.make_retry_decision(context)
        return decision == RetryDecision.RETRY

    def make_retry_decision(self, context: RetryContext) -> RetryDecision:
        """Make comprehensive retry decision with enhanced context.

        Args:
            context: Retry context with comprehensive information

        Returns:
            RetryDecision indicating what action to take
        """
        # Check circuit breaker first
        if self.circuit_breaker_hook:
            try:
                if not self.circuit_breaker_hook(context):
                    logger.debug(
                        f"Circuit breaker open, stopping retry for attempt "
                        f"{context.attempt_number}"
                    )
                    return RetryDecision.CIRCUIT_OPEN
            except Exception as e:
                logger.warning(f"Circuit breaker hook failed: {e}")

        # Check timeout
        if self.timeout and context.elapsed_time >= self.timeout:
            logger.debug(
                f"Timeout reached ({self.timeout}s), stopping retry for "
                f"attempt {context.attempt_number}"
            )
            return RetryDecision.TIMEOUT

        # Check max total delay
        if (self.max_total_delay and
                context.total_delay >= self.max_total_delay):
            logger.debug(
                f"Max total delay reached ({self.max_total_delay}s), "
                f"stopping retry"
            )
            return RetryDecision.TIMEOUT

        # Check strategy limits
        if not self.strategy.should_retry(
            context.attempt_number, context.exception
        ):
            logger.debug(
                f"Strategy limit reached, stopping retry for attempt "
                f"{context.attempt_number}"
            )
            return RetryDecision.STOP

        # Check non-retryable exceptions
        if self._is_non_retryable_exception(context.exception):
            logger.debug(
                f"Non-retryable exception {type(context.exception).__name__}, "
                f"stopping retry"
            )
            return RetryDecision.NON_RETRYABLE

        # Check retryable exceptions
        if not self._is_retryable_exception(context.exception):
            logger.debug(
                f"Exception {type(context.exception).__name__} not in "
                f"retryable list, stopping retry"
            )
            return RetryDecision.NON_RETRYABLE

        # Check custom retry condition
        if self.retry_condition:
            try:
                if not self.retry_condition(context.exception):
                    logger.debug(
                        "Custom retry condition failed, stopping retry"
                    )
                    return RetryDecision.NON_RETRYABLE
            except Exception as e:
                logger.warning(f"Retry condition check failed: {e}")
                return RetryDecision.NON_RETRYABLE

        # Check idempotency if configured
        if self.idempotency_check:
            try:
                if not self.idempotency_check(context):
                    logger.debug(
                        "Idempotency check failed, stopping retry"
                    )
                    return RetryDecision.NON_RETRYABLE
            except Exception as e:
                logger.warning(f"Idempotency check failed: {e}")
                return RetryDecision.NON_RETRYABLE

        logger.debug(f"Retry approved for attempt {context.attempt_number}")
        return RetryDecision.RETRY

    def _is_non_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is explicitly non-retryable."""
        if not self.non_retryable_exceptions:
            return False

        return any(
            isinstance(exception, exc_type)
            for exc_type in self.non_retryable_exceptions
        )

    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        if not self.retryable_exceptions:
            return True  # If no specific list, assume retryable

        return any(
            isinstance(exception, exc_type)
            for exc_type in self.retryable_exceptions
        )

    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        base_delay = self.strategy.get_delay(attempt)

        # Apply backoff multiplier if configured
        if self.backoff_multiplier_on_failure != 1.0:
            base_delay *= (self.backoff_multiplier_on_failure ** (attempt - 1))

        return base_delay

    def on_success(self, context: RetryContext) -> None:
        """Handle successful operation completion.

        Args:
            context: Retry context
        """
        if self.success_callback:
            try:
                self.success_callback(context)
            except Exception as e:
                logger.warning(f"Success callback failed: {e}")

    def on_failure(self, context: RetryContext) -> Any:
        """Handle final failure after all retries exhausted.

        Args:
            context: Retry context

        Returns:
            Optional graceful degradation result
        """
        if self.failure_callback:
            try:
                self.failure_callback(context)
            except Exception as e:
                logger.warning(f"Failure callback failed: {e}")

        # Attempt graceful degradation
        if self.graceful_degradation:
            try:
                return self.graceful_degradation(context)
            except Exception as e:
                logger.warning(f"Graceful degradation failed: {e}")

        return None


class DefaultRetryPolicy(RetryPolicy):
    """Default retry policy for common scenarios."""

    def __init__(self):
        # Common retryable exceptions
        retryable_exceptions = {
            ConnectionError,
            TimeoutError,
            OSError,
        }

        # Common non-retryable exceptions
        non_retryable_exceptions = {
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
            IndexError,
        }

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=3,
                base_delay=1.0,
                multiplier=2.0,
                max_delay=30.0,
                jitter=True,
            ),
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            timeout=60.0,
        )


class NetworkRetryPolicy(RetryPolicy):
    """Retry policy optimized for network operations."""

    def __init__(self):
        import httpx

        # Network-specific retryable exceptions
        retryable_exceptions = {
            ConnectionError,
            TimeoutError,
            OSError,
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.PoolTimeout,
        }

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=5,
                base_delay=0.5,
                multiplier=1.5,
                max_delay=10.0,
                jitter=True,
            ),
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=set(),  # Use custom condition instead
            timeout=30.0,
            retry_condition=self._network_retry_condition,
        )

    def _network_retry_condition(self, exception: Exception) -> bool:
        """Custom retry condition for network errors."""
        import httpx

        # Retry on specific HTTP status codes
        if isinstance(exception, httpx.HTTPStatusError):
            # Retry on server errors and rate limiting
            retryable_status_codes = {429, 500, 502, 503, 504}
            return exception.response.status_code in retryable_status_codes

        return True


class DatabaseRetryPolicy(RetryPolicy):
    """Retry policy optimized for database operations."""

    def __init__(self):
        # Database-specific retryable exceptions
        retryable_exceptions = {
            ConnectionError,
            TimeoutError,
            OSError,
        }

        # Add database-specific exceptions if available
        try:
            import psycopg2

            retryable_exceptions.update(
                {
                    psycopg2.OperationalError,
                    psycopg2.InterfaceError,
                }
            )
        except ImportError:
            pass

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=3,
                base_delay=2.0,
                multiplier=2.0,
                max_delay=60.0,
                jitter=True,
            ),
            retryable_exceptions=retryable_exceptions,
            timeout=120.0,
        )


class QuickRetryPolicy(RetryPolicy):
    """Quick retry policy for fast operations."""

    def __init__(self):
        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=2,
                base_delay=0.1,
                multiplier=2.0,
                max_delay=1.0,
                jitter=False,
            ),
            timeout=5.0,
        )


class AggressiveRetryPolicy(RetryPolicy):
    """Aggressive retry policy for critical operations."""

    def __init__(self):
        retryable_exceptions = {
            ConnectionError,
            TimeoutError,
            OSError,
        }

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=10,
                base_delay=0.5,
                multiplier=1.2,
                max_delay=30.0,
                jitter=True,
            ),
            retryable_exceptions=retryable_exceptions,
            timeout=300.0,  # 5 minutes
        )


class CircuitBreakerRetryPolicy(RetryPolicy):
    """Retry policy with circuit breaker integration.

    This policy integrates with circuit breaker patterns to prevent
    cascading failures in distributed systems.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """Initialize circuit breaker retry policy.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed, open, half_open
        self._half_open_calls = 0

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=3,
                base_delay=1.0,
                multiplier=2.0,
                max_delay=30.0,
                jitter=True,
            ),
            circuit_breaker_hook=self._circuit_breaker_check,
            success_callback=self._on_success,
            failure_callback=self._on_failure,
            timeout=60.0,
        )

    def _circuit_breaker_check(self, context: RetryContext) -> bool:
        """Check circuit breaker state."""
        current_time = time.time()

        if self._state == "open":
            # Check if recovery timeout has passed
            if current_time - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
                self._half_open_calls = 0
                logger.info("Circuit breaker transitioning to half-open")
            else:
                return False  # Circuit is open, don't retry

        if self._state == "half_open":
            if self._half_open_calls >= self.half_open_max_calls:
                return False  # Too many calls in half-open state

        return True  # Allow retry

    def _on_success(self, context: RetryContext) -> None:
        """Handle successful operation."""
        if self._state == "half_open":
            self._state = "closed"
            self._failure_count = 0
            logger.info("Circuit breaker closed after successful recovery")
        elif self._state == "closed":
            self._failure_count = max(0, self._failure_count - 1)

    def _on_failure(self, context: RetryContext) -> None:
        """Handle operation failure."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == "half_open":
            self._state = "open"
            logger.warning("Circuit breaker opened from half-open state")
        elif (self._state == "closed" and
              self._failure_count >= self.failure_threshold):
            self._state = "open"
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )

        if self._state == "half_open":
            self._half_open_calls += 1


class IdempotentRetryPolicy(RetryPolicy):
    """Retry policy for idempotent operations.

    This policy includes idempotency checks to ensure operations
    can be safely retried without side effects.
    """

    def __init__(
        self,
        idempotency_key_generator: Optional[Callable[[], str]] = None,
        idempotency_store: Optional[Dict[str, Any]] = None
    ):
        """Initialize idempotent retry policy.

        Args:
            idempotency_key_generator: Function to generate idempotency keys
            idempotency_store: Store for tracking idempotent operations
        """
        self.idempotency_key_generator = idempotency_key_generator
        self.idempotency_store = idempotency_store or {}

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=5,
                base_delay=1.0,
                multiplier=2.0,
                max_delay=60.0,
                jitter=True,
            ),
            idempotency_check=self._check_idempotency,
            timeout=120.0,
        )

    def _check_idempotency(self, context: RetryContext) -> bool:
        """Check if operation is safe to retry."""
        if not self.idempotency_key_generator:
            return True  # Assume safe if no generator provided

        try:
            key = self.idempotency_key_generator()

            # Check if operation was already completed successfully
            if key in self.idempotency_store:
                stored_result = self.idempotency_store[key]
                if stored_result.get("status") == "success":
                    logger.info(
                        f"Operation {key} already completed successfully"
                    )
                    return False  # Don't retry, operation already succeeded

            return True  # Safe to retry
        except Exception as e:
            logger.warning(f"Idempotency check failed: {e}")
            return False  # Conservative approach


class GracefulDegradationRetryPolicy(RetryPolicy):
    """Retry policy with graceful degradation support.

    This policy provides fallback mechanisms when all retries are exhausted.
    """

    def __init__(
        self,
        fallback_function: Optional[Callable[[RetryContext], Any]] = None,
        degraded_service_timeout: float = 5.0
    ):
        """Initialize graceful degradation retry policy.

        Args:
            fallback_function: Function to call for graceful degradation
            degraded_service_timeout: Timeout for degraded service calls
        """
        self.fallback_function = fallback_function
        self.degraded_service_timeout = degraded_service_timeout

        super().__init__(
            strategy=ExponentialBackoffStrategy(
                max_attempts=3,
                base_delay=0.5,
                multiplier=2.0,
                max_delay=10.0,
                jitter=True,
            ),
            graceful_degradation=self._graceful_degradation,
            timeout=30.0,
        )

    def _graceful_degradation(self, context: RetryContext) -> Any:
        """Provide graceful degradation when retries are exhausted."""
        if not self.fallback_function:
            return None

        try:
            logger.info("Attempting graceful degradation")
            return self.fallback_function(context)
        except Exception as e:
            logger.error(f"Graceful degradation failed: {e}")
            return None


# Factory functions for common policy configurations
def create_network_policy(
    max_attempts: int = 5,
    base_delay: float = 0.5,
    timeout: float = 30.0
) -> NetworkRetryPolicy:
    """Create a network retry policy with custom parameters."""
    policy = NetworkRetryPolicy()
    policy.strategy.max_attempts = max_attempts
    policy.strategy.base_delay = base_delay
    policy.timeout = timeout
    return policy


def create_database_policy(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    timeout: float = 120.0
) -> DatabaseRetryPolicy:
    """Create a database retry policy with custom parameters."""
    policy = DatabaseRetryPolicy()
    policy.strategy.max_attempts = max_attempts
    policy.strategy.base_delay = base_delay
    policy.timeout = timeout
    return policy


def create_circuit_breaker_policy(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
) -> CircuitBreakerRetryPolicy:
    """Create a circuit breaker retry policy with custom parameters."""
    return CircuitBreakerRetryPolicy(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
