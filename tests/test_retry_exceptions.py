"""
Comprehensive tests for retry exceptions.

This module tests all retry-related exception classes with focus on:
- Exception hierarchy and inheritance
- Error message formatting and attributes
- Exception chaining and context preservation
- Integration with base ZenooError
"""

from src.zenoo_rpc.retry.exceptions import (
    RetryError,
    MaxRetriesExceededError,
    RetryTimeoutError,
)
from src.zenoo_rpc.exceptions import ZenooError


class TestRetryError:
    """Test RetryError base exception class."""

    def test_inheritance(self):
        """Test that RetryError inherits from ZenooError."""
        assert issubclass(RetryError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic RetryError instantiation."""
        error = RetryError("Test retry error")
        assert str(error) == "Test retry error"
        assert isinstance(error, ZenooError)
        assert isinstance(error, Exception)

    def test_empty_instantiation(self):
        """Test RetryError with empty message."""
        error = RetryError("")
        assert str(error) == ""

    def test_exception_chaining(self):
        """Test exception chaining with RetryError."""
        original_error = ValueError("Original error")

        try:
            raise original_error
        except ValueError as e:
            retry_error = RetryError("Retry failed")
            retry_error.__cause__ = e

        assert retry_error.__cause__ is original_error
        assert "Retry failed" in str(retry_error)


class TestMaxRetriesExceededError:
    """Test MaxRetriesExceededError exception class."""

    def test_inheritance(self):
        """Test that MaxRetriesExceededError inherits from RetryError."""
        assert issubclass(MaxRetriesExceededError, RetryError)
        assert issubclass(MaxRetriesExceededError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic MaxRetriesExceededError instantiation."""
        last_exception = ConnectionError("Connection failed")
        error = MaxRetriesExceededError(attempts=3, last_exception=last_exception)
        
        assert error.attempts == 3
        assert error.last_exception is last_exception
        assert "Maximum retry attempts (3) exceeded" in str(error)
        assert "Connection failed" in str(error)

    def test_message_formatting(self):
        """Test error message formatting with different exception types."""
        # Test with different exception types
        test_cases = [
            (ValueError("Invalid value"), "Invalid value"),
            (ConnectionError("Network error"), "Network error"),
            (TimeoutError("Request timeout"), "Request timeout"),
            (Exception("Generic error"), "Generic error"),
        ]
        
        for last_exception, expected_text in test_cases:
            error = MaxRetriesExceededError(attempts=5, last_exception=last_exception)
            error_str = str(error)
            
            assert "Maximum retry attempts (5) exceeded" in error_str
            assert f"Last error: {last_exception}" in error_str
            assert expected_text in error_str

    def test_zero_attempts(self):
        """Test with zero attempts."""
        last_exception = RuntimeError("Runtime error")
        error = MaxRetriesExceededError(attempts=0, last_exception=last_exception)
        
        assert error.attempts == 0
        assert "Maximum retry attempts (0) exceeded" in str(error)

    def test_high_attempts(self):
        """Test with high number of attempts."""
        last_exception = OSError("OS error")
        error = MaxRetriesExceededError(attempts=1000, last_exception=last_exception)
        
        assert error.attempts == 1000
        assert "Maximum retry attempts (1000) exceeded" in str(error)

    def test_exception_with_no_message(self):
        """Test with exception that has no message."""
        last_exception = Exception()  # No message
        error = MaxRetriesExceededError(attempts=2, last_exception=last_exception)
        
        assert error.attempts == 2
        assert error.last_exception is last_exception
        assert "Maximum retry attempts (2) exceeded" in str(error)

    def test_nested_exception_chaining(self):
        """Test exception chaining with nested exceptions."""
        original_error = ValueError("Original")
        intermediate_error = ConnectionError("Intermediate")
        intermediate_error.__cause__ = original_error
        retry_error = MaxRetriesExceededError(attempts=3, last_exception=intermediate_error)

        assert retry_error.last_exception is intermediate_error
        assert retry_error.last_exception.__cause__ is original_error


class TestRetryTimeoutError:
    """Test RetryTimeoutError exception class."""

    def test_inheritance(self):
        """Test that RetryTimeoutError inherits from RetryError."""
        assert issubclass(RetryTimeoutError, RetryError)
        assert issubclass(RetryTimeoutError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic RetryTimeoutError instantiation."""
        error = RetryTimeoutError(timeout=30.0, attempts=5)
        
        assert error.timeout == 30.0
        assert error.attempts == 5
        assert "Retry timeout (30.0s) exceeded after 5 attempts" in str(error)

    def test_message_formatting(self):
        """Test error message formatting with different values."""
        test_cases = [
            (10.0, 1, "Retry timeout (10.0s) exceeded after 1 attempts"),
            (0.5, 0, "Retry timeout (0.5s) exceeded after 0 attempts"),
            (120.5, 10, "Retry timeout (120.5s) exceeded after 10 attempts"),
            (1.0, 100, "Retry timeout (1.0s) exceeded after 100 attempts"),
        ]
        
        for timeout, attempts, expected_message in test_cases:
            error = RetryTimeoutError(timeout=timeout, attempts=attempts)
            assert str(error) == expected_message

    def test_zero_timeout(self):
        """Test with zero timeout."""
        error = RetryTimeoutError(timeout=0.0, attempts=1)
        
        assert error.timeout == 0.0
        assert error.attempts == 1
        assert "Retry timeout (0.0s) exceeded after 1 attempts" in str(error)

    def test_fractional_timeout(self):
        """Test with fractional timeout values."""
        error = RetryTimeoutError(timeout=2.5, attempts=3)
        
        assert error.timeout == 2.5
        assert "Retry timeout (2.5s) exceeded" in str(error)

    def test_large_timeout(self):
        """Test with large timeout values."""
        error = RetryTimeoutError(timeout=3600.0, attempts=50)
        
        assert error.timeout == 3600.0
        assert "Retry timeout (3600.0s) exceeded after 50 attempts" in str(error)


class TestExceptionIntegration:
    """Test integration between different retry exceptions."""

    def test_exception_hierarchy_chain(self):
        """Test that all exceptions maintain proper hierarchy."""
        # Create a chain of exceptions
        original = ValueError("Original error")
        max_retries = MaxRetriesExceededError(attempts=3, last_exception=original)
        timeout_error = RetryTimeoutError(timeout=10.0, attempts=2)
        
        # Test isinstance relationships
        assert isinstance(max_retries, RetryError)
        assert isinstance(max_retries, ZenooError)
        assert isinstance(timeout_error, RetryError)
        assert isinstance(timeout_error, ZenooError)

    def test_exception_attributes_preservation(self):
        """Test that exception attributes are preserved correctly."""
        original_error = ConnectionError("Network failure")
        max_retries_error = MaxRetriesExceededError(
            attempts=5, 
            last_exception=original_error
        )
        
        # Verify attributes are accessible
        assert hasattr(max_retries_error, 'attempts')
        assert hasattr(max_retries_error, 'last_exception')
        assert max_retries_error.attempts == 5
        assert max_retries_error.last_exception is original_error
        
        timeout_error = RetryTimeoutError(timeout=15.5, attempts=3)
        assert hasattr(timeout_error, 'timeout')
        assert hasattr(timeout_error, 'attempts')
        assert timeout_error.timeout == 15.5
        assert timeout_error.attempts == 3

    def test_exception_serialization(self):
        """Test that exception attributes are properly accessible."""
        # Test MaxRetriesExceededError attributes
        original_error = ValueError("Test error")
        max_retries = MaxRetriesExceededError(attempts=3, last_exception=original_error)

        # Verify all attributes are accessible
        assert max_retries.attempts == 3
        assert max_retries.last_exception is original_error
        assert "Maximum retry attempts (3) exceeded" in str(max_retries)

        # Test RetryTimeoutError attributes
        timeout_error = RetryTimeoutError(timeout=10.0, attempts=2)

        assert timeout_error.timeout == 10.0
        assert timeout_error.attempts == 2
        assert "Retry timeout (10.0s) exceeded after 2 attempts" in str(timeout_error)

    def test_repr_methods(self):
        """Test string representation methods."""
        original_error = RuntimeError("Runtime issue")
        max_retries = MaxRetriesExceededError(attempts=2, last_exception=original_error)
        timeout_error = RetryTimeoutError(timeout=5.0, attempts=1)
        
        # Test that repr works without errors
        repr(max_retries)
        repr(timeout_error)
        
        # Test that str works correctly
        assert "Maximum retry attempts" in str(max_retries)
        assert "Retry timeout" in str(timeout_error)
