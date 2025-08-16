"""
Retry decorators for OdooFlow.

This module provides decorators for adding retry logic to functions and methods.
"""

import asyncio
import time
import logging
from functools import wraps
from typing import Any, Callable, Optional, Type, Union, TypeVar

from .policies import RetryPolicy, DefaultRetryPolicy
from .strategies import RetryAttempt
from .exceptions import MaxRetriesExceededError, RetryTimeoutError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    policy: Optional[RetryPolicy] = None,
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff_multiplier: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Optional[Union[Type[Exception], tuple]] = None,
    on_retry: Optional[Callable[[RetryAttempt], None]] = None,
) -> Callable[[F], F]:
    """Retry decorator for synchronous functions.

    Args:
        policy: Retry policy to use
        max_attempts: Maximum retry attempts (overrides policy)
        delay: Base delay in seconds (overrides policy)
        backoff_multiplier: Backoff multiplier (overrides policy)
        max_delay: Maximum delay (overrides policy)
        exceptions: Exception types to retry on
        on_retry: Callback called on each retry attempt

    Returns:
        Decorated function
    """
    if policy is None:
        policy = DefaultRetryPolicy()

    # Override policy settings if provided
    if max_attempts is not None:
        policy.strategy.max_attempts = max_attempts
    if delay is not None and hasattr(policy.strategy, "base_delay"):
        policy.strategy.base_delay = delay
    if backoff_multiplier is not None and hasattr(policy.strategy, "multiplier"):
        policy.strategy.multiplier = backoff_multiplier
    if max_delay is not None:
        policy.strategy.max_delay = max_delay
    if exceptions is not None:
        if isinstance(exceptions, type):
            exceptions = (exceptions,)
        policy.retryable_exceptions = set(exceptions)

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            last_exception = None

            for attempt in range(1, policy.strategy.max_attempts + 1):
                attempt_start = time.time()

                try:
                    result = func(*args, **kwargs)

                    # Success - record if strategy supports it
                    if hasattr(policy.strategy, "record_attempt"):
                        policy.strategy.record_attempt(success=True)

                    return result

                except Exception as e:
                    last_exception = e
                    attempt_end = time.time()

                    # Record failure if strategy supports it
                    if hasattr(policy.strategy, "record_attempt"):
                        policy.strategy.record_attempt(success=False)

                    # Create retry attempt info
                    retry_attempt = RetryAttempt(
                        attempt_number=attempt,
                        delay=0,  # Will be set below
                        exception=e,
                        start_time=attempt_start,
                        end_time=attempt_end,
                    )

                    # Check if should retry
                    if not policy.should_retry(attempt, e, start_time):
                        break

                    # Calculate delay
                    delay = policy.get_delay(attempt)
                    retry_attempt.delay = delay

                    # Call retry callback
                    if on_retry:
                        on_retry(retry_attempt)

                    logger.debug(
                        f"Retry attempt {attempt}/{policy.strategy.max_attempts} "
                        f"for {func.__name__} after {retry_attempt.duration:.2f}s, "
                        f"waiting {delay:.2f}s. Error: {e}"
                    )

                    # Wait before retry
                    if delay > 0:
                        time.sleep(delay)

            # Check if timeout exceeded
            if policy.timeout and (time.time() - start_time) >= policy.timeout:
                raise RetryTimeoutError(policy.timeout, attempt)

            # Max retries exceeded
            raise MaxRetriesExceededError(attempt, last_exception)

        return wrapper

    return decorator


def async_retry(
    policy: Optional[RetryPolicy] = None,
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff_multiplier: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Optional[Union[Type[Exception], tuple]] = None,
    on_retry: Optional[Callable[[RetryAttempt], None]] = None,
) -> Callable[[F], F]:
    """Retry decorator for asynchronous functions.

    Args:
        policy: Retry policy to use
        max_attempts: Maximum retry attempts (overrides policy)
        delay: Base delay in seconds (overrides policy)
        backoff_multiplier: Backoff multiplier (overrides policy)
        max_delay: Maximum delay (overrides policy)
        exceptions: Exception types to retry on
        on_retry: Callback called on each retry attempt

    Returns:
        Decorated async function
    """
    if policy is None:
        policy = DefaultRetryPolicy()

    # Override policy settings if provided
    if max_attempts is not None:
        policy.strategy.max_attempts = max_attempts
    if delay is not None and hasattr(policy.strategy, "base_delay"):
        policy.strategy.base_delay = delay
    if backoff_multiplier is not None and hasattr(policy.strategy, "multiplier"):
        policy.strategy.multiplier = backoff_multiplier
    if max_delay is not None:
        policy.strategy.max_delay = max_delay
    if exceptions is not None:
        if isinstance(exceptions, type):
            exceptions = (exceptions,)
        policy.retryable_exceptions = set(exceptions)

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            last_exception = None

            for attempt in range(1, policy.strategy.max_attempts + 1):
                attempt_start = time.time()

                try:
                    result = await func(*args, **kwargs)

                    # Success - record if strategy supports it
                    if hasattr(policy.strategy, "record_attempt"):
                        policy.strategy.record_attempt(success=True)

                    return result

                except Exception as e:
                    last_exception = e
                    attempt_end = time.time()

                    # Record failure if strategy supports it
                    if hasattr(policy.strategy, "record_attempt"):
                        policy.strategy.record_attempt(success=False)

                    # Create retry attempt info
                    retry_attempt = RetryAttempt(
                        attempt_number=attempt,
                        delay=0,  # Will be set below
                        exception=e,
                        start_time=attempt_start,
                        end_time=attempt_end,
                    )

                    # Check if should retry
                    if not policy.should_retry(attempt, e, start_time):
                        break

                    # Calculate delay
                    delay = policy.get_delay(attempt)
                    retry_attempt.delay = delay

                    # Call retry callback
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(retry_attempt)
                        else:
                            on_retry(retry_attempt)

                    logger.debug(
                        f"Async retry attempt {attempt}/{policy.strategy.max_attempts} "
                        f"for {func.__name__} after {retry_attempt.duration:.2f}s, "
                        f"waiting {delay:.2f}s. Error: {e}"
                    )

                    # Wait before retry
                    if delay > 0:
                        await asyncio.sleep(delay)

            # Check if timeout exceeded
            if policy.timeout and (time.time() - start_time) >= policy.timeout:
                raise RetryTimeoutError(policy.timeout, attempt)

            # Max retries exceeded
            raise MaxRetriesExceededError(attempt, last_exception)

        return wrapper

    return decorator


# Convenience decorators for common scenarios
def network_retry(
    max_attempts: int = 5, base_delay: float = 0.5, max_delay: float = 10.0
):
    """Convenience decorator for network operations."""
    from .policies import NetworkRetryPolicy

    policy = NetworkRetryPolicy()
    policy.strategy.max_attempts = max_attempts
    if hasattr(policy.strategy, "base_delay"):
        policy.strategy.base_delay = base_delay
    policy.strategy.max_delay = max_delay

    return async_retry(policy=policy)


def database_retry(
    max_attempts: int = 3, base_delay: float = 2.0, max_delay: float = 60.0
):
    """Convenience decorator for database operations."""
    from .policies import DatabaseRetryPolicy

    policy = DatabaseRetryPolicy()
    policy.strategy.max_attempts = max_attempts
    if hasattr(policy.strategy, "base_delay"):
        policy.strategy.base_delay = base_delay
    policy.strategy.max_delay = max_delay

    return async_retry(policy=policy)


def quick_retry(max_attempts: int = 2):
    """Convenience decorator for quick retry operations."""
    from .policies import QuickRetryPolicy

    policy = QuickRetryPolicy()
    policy.strategy.max_attempts = max_attempts

    return async_retry(policy=policy)
