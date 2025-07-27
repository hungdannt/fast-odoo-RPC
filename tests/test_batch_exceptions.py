"""
Comprehensive tests for batch exceptions.

This module tests all batch-related exception classes with focus on:
- Exception hierarchy and inheritance
- Batch operation error handling
- Failed operations tracking
- Validation error collection
- Batch size and timeout handling
- Integration with base ZenooError
"""

from src.zenoo_rpc.batch.exceptions import (
    BatchError,
    BatchExecutionError,
    BatchValidationError,
    BatchSizeError,
    BatchTimeoutError,
)
from src.zenoo_rpc.exceptions import ZenooError


class TestBatchError:
    """Test BatchError base exception class."""

    def test_inheritance(self):
        """Test that BatchError inherits from ZenooError."""
        assert issubclass(BatchError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic BatchError instantiation."""
        error = BatchError("Batch operation failed")
        assert str(error) == "Batch operation failed"
        assert error.batch_id is None
        assert isinstance(error, ZenooError)

    def test_with_batch_id(self):
        """Test BatchError with batch ID."""
        error = BatchError("Batch failed", batch_id="batch_123")
        
        assert str(error) == "Batch failed"
        assert error.batch_id == "batch_123"

    def test_with_context_and_batch_id(self):
        """Test BatchError with context and batch ID."""
        context = {"operation_count": 50, "start_time": "2023-01-01T10:00:00"}
        error = BatchError(
            "Batch processing error",
            batch_id="batch_456",
            context=context
        )
        
        assert str(error) == "Batch processing error"
        assert error.batch_id == "batch_456"
        assert error.context == context

    def test_empty_message(self):
        """Test BatchError with empty message."""
        error = BatchError("", batch_id="empty_batch")
        assert str(error) == ""
        assert error.batch_id == "empty_batch"


class TestBatchExecutionError:
    """Test BatchExecutionError exception class."""

    def test_inheritance(self):
        """Test that BatchExecutionError inherits from BatchError."""
        assert issubclass(BatchExecutionError, BatchError)
        assert issubclass(BatchExecutionError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic BatchExecutionError instantiation."""
        error = BatchExecutionError("Execution failed")
        
        assert str(error) == "Execution failed"
        assert error.failed_operations == []
        assert error.partial_results == {}
        assert error.batch_id is None

    def test_with_failed_operations(self):
        """Test BatchExecutionError with failed operations."""
        failed_ops = [
            {"id": 1, "error": "Connection timeout"},
            {"id": 3, "error": "Invalid data"},
        ]
        error = BatchExecutionError(
            "Some operations failed",
            failed_operations=failed_ops
        )
        
        assert str(error) == "Some operations failed"
        assert error.failed_operations == failed_ops
        assert len(error.failed_operations) == 2

    def test_with_partial_results(self):
        """Test BatchExecutionError with partial results."""
        partial_results = {
            "successful": [1, 2, 4, 5],
            "failed": [3, 6],
            "total": 6
        }
        error = BatchExecutionError(
            "Partial execution failure",
            partial_results=partial_results
        )
        
        assert str(error) == "Partial execution failure"
        assert error.partial_results == partial_results
        assert error.partial_results["successful"] == [1, 2, 4, 5]

    def test_with_all_parameters(self):
        """Test BatchExecutionError with all parameters."""
        failed_ops = [{"id": 2, "error": "Validation failed"}]
        partial_results = {"completed": 3, "failed": 1}
        context = {"retry_count": 2}
        
        error = BatchExecutionError(
            "Batch execution partially failed",
            batch_id="batch_789",
            failed_operations=failed_ops,
            partial_results=partial_results,
            context=context
        )
        
        assert str(error) == "Batch execution partially failed"
        assert error.batch_id == "batch_789"
        assert error.failed_operations == failed_ops
        assert error.partial_results == partial_results
        assert error.context == context

    def test_none_parameters(self):
        """Test BatchExecutionError with None parameters."""
        error = BatchExecutionError(
            "Error message",
            failed_operations=None,
            partial_results=None
        )
        
        # Should default to empty list/dict
        assert error.failed_operations == []
        assert error.partial_results == {}


class TestBatchValidationError:
    """Test BatchValidationError exception class."""

    def test_inheritance(self):
        """Test that BatchValidationError inherits from BatchError."""
        assert issubclass(BatchValidationError, BatchError)
        assert issubclass(BatchValidationError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic BatchValidationError instantiation."""
        error = BatchValidationError("Validation failed")
        
        assert str(error) == "Validation failed"
        assert error.validation_errors == []
        assert error.batch_id is None

    def test_with_validation_errors(self):
        """Test BatchValidationError with validation errors."""
        validation_errors = [
            {"field": "name", "error": "Required field missing"},
            {"field": "email", "error": "Invalid email format"},
            {"field": "age", "error": "Must be positive integer"},
        ]
        error = BatchValidationError(
            "Multiple validation errors",
            validation_errors=validation_errors
        )
        
        assert str(error) == "Multiple validation errors"
        assert error.validation_errors == validation_errors
        assert len(error.validation_errors) == 3

    def test_with_batch_id_and_errors(self):
        """Test BatchValidationError with batch ID and errors."""
        validation_errors = [{"field": "status", "error": "Invalid status"}]
        error = BatchValidationError(
            "Batch validation failed",
            batch_id="validation_batch",
            validation_errors=validation_errors
        )
        
        assert str(error) == "Batch validation failed"
        assert error.batch_id == "validation_batch"
        assert error.validation_errors == validation_errors

    def test_none_validation_errors(self):
        """Test BatchValidationError with None validation errors."""
        error = BatchValidationError(
            "Error message",
            validation_errors=None
        )
        
        # Should default to empty list
        assert error.validation_errors == []

    def test_complex_validation_errors(self):
        """Test with complex validation error structures."""
        validation_errors = [
            {
                "operation_id": 1,
                "field_errors": {
                    "name": ["Required", "Too short"],
                    "email": ["Invalid format"]
                }
            },
            {
                "operation_id": 3,
                "field_errors": {
                    "age": ["Must be positive", "Must be integer"]
                }
            }
        ]
        error = BatchValidationError(
            "Complex validation failure",
            validation_errors=validation_errors
        )
        
        assert error.validation_errors == validation_errors
        assert len(error.validation_errors) == 2


class TestBatchSizeError:
    """Test BatchSizeError exception class."""

    def test_inheritance(self):
        """Test that BatchSizeError inherits from BatchError."""
        assert issubclass(BatchSizeError, BatchError)
        assert issubclass(BatchSizeError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic BatchSizeError instantiation."""
        error = BatchSizeError("Batch size too large")
        
        assert str(error) == "Batch size too large"
        assert error.batch_id is None

    def test_with_batch_id(self):
        """Test BatchSizeError with batch ID."""
        error = BatchSizeError("Exceeds maximum size", batch_id="large_batch")
        
        assert str(error) == "Exceeds maximum size"
        assert error.batch_id == "large_batch"

    def test_size_limit_scenarios(self):
        """Test various batch size error scenarios."""
        scenarios = [
            "Batch size exceeds maximum limit of 1000",
            "Empty batch not allowed",
            "Batch too small for processing",
            "Size limit reached: 500/500",
        ]
        
        for message in scenarios:
            error = BatchSizeError(message)
            assert str(error) == message

    def test_with_context(self):
        """Test BatchSizeError with size context."""
        context = {
            "current_size": 1500,
            "max_size": 1000,
            "operation_type": "bulk_create"
        }
        error = BatchSizeError(
            "Batch size limit exceeded",
            context=context
        )
        
        assert str(error) == "Batch size limit exceeded"
        assert error.context["current_size"] == 1500
        assert error.context["max_size"] == 1000


class TestBatchTimeoutError:
    """Test BatchTimeoutError exception class."""

    def test_inheritance(self):
        """Test that BatchTimeoutError inherits from BatchError."""
        assert issubclass(BatchTimeoutError, BatchError)
        assert issubclass(BatchTimeoutError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic BatchTimeoutError instantiation."""
        error = BatchTimeoutError("Batch operation timed out")
        
        assert str(error) == "Batch operation timed out"
        assert error.batch_id is None

    def test_with_batch_id(self):
        """Test BatchTimeoutError with batch ID."""
        error = BatchTimeoutError("Timeout after 30s", batch_id="slow_batch")
        
        assert str(error) == "Timeout after 30s"
        assert error.batch_id == "slow_batch"

    def test_timeout_scenarios(self):
        """Test various timeout error scenarios."""
        scenarios = [
            "Operation timeout after 60 seconds",
            "Network timeout during batch processing",
            "Database timeout on bulk insert",
            "Processing timeout exceeded",
        ]
        
        for message in scenarios:
            error = BatchTimeoutError(message)
            assert str(error) == message

    def test_with_timeout_context(self):
        """Test BatchTimeoutError with timeout context."""
        context = {
            "timeout_seconds": 30,
            "elapsed_seconds": 45,
            "operations_completed": 75,
            "operations_total": 100
        }
        error = BatchTimeoutError(
            "Batch processing timeout",
            batch_id="timeout_batch",
            context=context
        )
        
        assert str(error) == "Batch processing timeout"
        assert error.batch_id == "timeout_batch"
        assert error.context["timeout_seconds"] == 30
        assert error.context["elapsed_seconds"] == 45


class TestExceptionIntegration:
    """Test integration between different batch exceptions."""

    def test_exception_hierarchy(self):
        """Test that all exceptions maintain proper hierarchy."""
        # Create instances of all exception types
        batch_error = BatchError("Base error", batch_id="test")
        execution_error = BatchExecutionError("Execution error")
        validation_error = BatchValidationError("Validation error")
        size_error = BatchSizeError("Size error")
        timeout_error = BatchTimeoutError("Timeout error")
        
        # Test isinstance relationships
        exceptions = [execution_error, validation_error, size_error, timeout_error]
        
        for exc in exceptions:
            assert isinstance(exc, BatchError)
            assert isinstance(exc, ZenooError)
            assert isinstance(exc, Exception)

    def test_batch_id_inheritance(self):
        """Test that batch_id is inherited from BatchError."""
        exceptions_with_batch_id = [
            BatchError("Error", batch_id="test_batch"),
            BatchExecutionError("Exec error", batch_id="exec_batch"),
            BatchValidationError("Valid error", batch_id="valid_batch"),
            BatchSizeError("Size error", batch_id="size_batch"),
            BatchTimeoutError("Timeout error", batch_id="timeout_batch"),
        ]
        
        for exc in exceptions_with_batch_id:
            assert hasattr(exc, 'batch_id')
            assert exc.batch_id is not None

    def test_exception_chaining(self):
        """Test exception chaining with batch exceptions."""
        original_error = ConnectionError("Database connection lost")
        batch_error = BatchExecutionError("Batch failed due to connection")
        batch_error.__cause__ = original_error
        
        assert batch_error.__cause__ is original_error
        assert "Batch failed due to connection" in str(batch_error)

    def test_complex_error_scenario(self):
        """Test complex error scenario with multiple error types."""
        # Simulate a complex batch operation failure
        failed_operations = [
            {"id": 1, "error": "Validation failed"},
            {"id": 5, "error": "Timeout"},
        ]
        partial_results = {"successful": [2, 3, 4], "failed": [1, 5]}
        
        execution_error = BatchExecutionError(
            "Batch partially failed",
            batch_id="complex_batch",
            failed_operations=failed_operations,
            partial_results=partial_results
        )
        
        # Verify all data is preserved
        assert execution_error.batch_id == "complex_batch"
        assert len(execution_error.failed_operations) == 2
        assert execution_error.partial_results["successful"] == [2, 3, 4]
        assert execution_error.partial_results["failed"] == [1, 5]
