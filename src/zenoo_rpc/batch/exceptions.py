"""
Batch operation exceptions for OdooFlow.
"""

from ..exceptions import ZenooError


class BatchError(ZenooError):
    """Base exception for batch operation errors."""

    def __init__(self, message: str, batch_id: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.batch_id = batch_id


class BatchExecutionError(BatchError):
    """Exception raised when batch execution fails."""

    def __init__(
        self,
        message: str,
        failed_operations: list = None,
        partial_results: dict = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.failed_operations = failed_operations or []
        self.partial_results = partial_results or {}


class BatchValidationError(BatchError):
    """Exception raised when batch validation fails."""

    def __init__(self, message: str, validation_errors: list = None, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []


class BatchSizeError(BatchError):
    """Exception raised when batch size exceeds limits."""

    pass


class BatchTimeoutError(BatchError):
    """Exception raised when batch operation times out."""

    pass
