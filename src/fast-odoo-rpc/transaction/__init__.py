"""
Transaction management for OdooFlow.

This module provides explicit transaction control with async context managers,
supporting commit/rollback operations and nested transactions.
"""

from .manager import TransactionManager, Transaction
from .context import transaction, atomic
from .exceptions import TransactionError, TransactionRollbackError

__all__ = [
    # Core transaction management
    "TransactionManager",
    "Transaction",
    # Context managers
    "transaction",
    "atomic",
    # Exceptions
    "TransactionError",
    "TransactionRollbackError",
]
