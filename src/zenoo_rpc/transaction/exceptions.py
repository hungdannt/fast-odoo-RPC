"""
Transaction-specific exceptions for Zenoo-RPC.

Enhanced with detailed error context and rollback information
for better debugging and error handling.
"""

from typing import List, Tuple, Any, Optional
from ..exceptions import ZenooError


class TransactionError(ZenooError):
    """Base exception for transaction-related errors."""

    def __init__(self, message: str, transaction_id: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.transaction_id = transaction_id


class TransactionRollbackError(TransactionError):
    """Exception raised when a transaction rollback fails.

    Enhanced with detailed context about failed operations,
    partial rollback status, and recovery information.
    """

    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        original_error: Optional[Exception] = None,
        failed_operations: Optional[List[Tuple[Any, Exception]]] = None,
        partial_rollback: bool = False,
        **kwargs,
    ):
        super().__init__(message, transaction_id=transaction_id, **kwargs)
        self.original_error = original_error
        self.failed_operations = failed_operations or []
        self.partial_rollback = partial_rollback

    def get_failed_operation_summary(self) -> str:
        """Get a summary of failed operations for debugging."""
        if not self.failed_operations:
            return "No failed operations"

        summary = []
        for operation, error in self.failed_operations:
            op_type = getattr(operation, "operation_type", "unknown")
            model = getattr(operation, "model", "unknown")
            summary.append(f"{op_type} on {model}: {error}")

        return "; ".join(summary)

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.failed_operations:
            failed_summary = self.get_failed_operation_summary()
            return f"{base_msg}\nFailed operations: {failed_summary}"
        return base_msg


class TransactionCommitError(TransactionError):
    """Exception raised when a transaction commit fails."""

    def __init__(self, message: str, original_error: Exception = None, **kwargs):
        super().__init__(message, **kwargs)
        self.original_error = original_error


class NestedTransactionError(TransactionError):
    """Exception raised for nested transaction violations."""

    pass


class TransactionStateError(TransactionError):
    """Exception raised when transaction is in invalid state."""

    pass
