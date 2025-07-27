"""
Retry-related exceptions for OdooFlow.
"""

from ..exceptions import ZenooError


class RetryError(ZenooError):
    """Base exception for retry-related errors."""

    pass


class MaxRetriesExceededError(RetryError):
    """Raised when maximum retry attempts are exceeded."""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Maximum retry attempts ({attempts}) exceeded. "
            f"Last error: {last_exception}"
        )


class RetryTimeoutError(RetryError):
    """Raised when retry timeout is exceeded."""

    def __init__(self, timeout: float, attempts: int):
        self.timeout = timeout
        self.attempts = attempts
        super().__init__(
            f"Retry timeout ({timeout}s) exceeded after {attempts} attempts"
        )
