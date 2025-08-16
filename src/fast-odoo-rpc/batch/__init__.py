"""
Batch operations for OdooFlow.

This module provides efficient bulk operations for creating,
updating, and deleting multiple records with performance optimization.
"""

from .manager import BatchManager
from .operations import (
    BatchOperation,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
)
from .executor import BatchExecutor
from .context import batch_context, batch_operation
from .exceptions import BatchError, BatchExecutionError, BatchValidationError

__all__ = [
    # Core batch management
    "BatchManager",
    "BatchExecutor",
    # Operations
    "BatchOperation",
    "CreateOperation",
    "UpdateOperation",
    "DeleteOperation",
    # Context managers
    "batch_context",
    "batch_operation",
    # Exceptions
    "BatchError",
    "BatchExecutionError",
    "BatchValidationError",
]
