"""
Batch operation definitions for OdooFlow.

This module defines different types of batch operations
with validation and execution logic.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field

from .exceptions import BatchValidationError


class OperationType(Enum):
    """Batch operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UNLINK = "unlink"  # Alias for delete


class OperationStatus(Enum):
    """Batch operation status."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchOperation(ABC):
    """Abstract base class for batch operations.

    This class defines the interface for all batch operations
    with common properties and validation logic.
    """

    model: str
    data: Union[List[Dict[str, Any]], List[int], Dict[str, Any]]
    operation_type: OperationType = field(default=OperationType.CREATE)
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OperationStatus = OperationStatus.PENDING
    priority: int = 0
    context: Optional[Dict[str, Any]] = None

    # Execution metadata
    created_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Any] = None

    def __post_init__(self):
        """Post-initialization validation."""
        self.validate()

    @abstractmethod
    def validate(self) -> None:
        """Validate operation data."""
        pass

    @abstractmethod
    def get_batch_size(self) -> int:
        """Get the number of records in this operation."""
        pass

    @abstractmethod
    def split(self, chunk_size: int) -> List["BatchOperation"]:
        """Split operation into smaller chunks."""
        pass

    def is_completed(self) -> bool:
        """Check if operation is completed."""
        return self.status in (OperationStatus.COMPLETED, OperationStatus.FAILED)

    def is_successful(self) -> bool:
        """Check if operation completed successfully."""
        return self.status == OperationStatus.COMPLETED

    def get_duration(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class CreateOperation(BatchOperation):
    """Batch create operation.

    Creates multiple records in a single batch operation
    with optimized performance and error handling.

    Example:
        >>> operation = CreateOperation(
        ...     model="res.partner",
        ...     data=[
        ...         {"name": "Company A", "is_company": True},
        ...         {"name": "Company B", "is_company": True}
        ...     ]
        ... )
    """

    return_ids: bool = True
    operation_type: OperationType = field(default=OperationType.CREATE, init=False)

    def validate(self) -> None:
        """Validate create operation data."""
        if not self.model:
            raise BatchValidationError("Model is required for create operation")

        if not isinstance(self.data, list):
            raise BatchValidationError(
                "Create operation data must be a list of dictionaries"
            )

        if not self.data:
            raise BatchValidationError("Create operation data cannot be empty")

        # Validate each record
        for i, record in enumerate(self.data):
            if not isinstance(record, dict):
                raise BatchValidationError(f"Record {i} must be a dictionary")

            if not record:
                raise BatchValidationError(f"Record {i} cannot be empty")

    def get_batch_size(self) -> int:
        """Get the number of records to create."""
        return len(self.data)

    def split(self, chunk_size: int) -> List["CreateOperation"]:
        """Split create operation into smaller chunks."""
        if chunk_size >= len(self.data):
            return [self]

        chunks = []
        for i in range(0, len(self.data), chunk_size):
            chunk_data = self.data[i : i + chunk_size]
            chunk = CreateOperation(
                model=self.model,
                data=chunk_data,
                return_ids=self.return_ids,
                context=self.context,
                priority=self.priority,
            )
            chunks.append(chunk)

        return chunks


@dataclass
class UpdateOperation(BatchOperation):
    """Batch update operation.

    Updates multiple records with the same or different values
    in a single batch operation.

    Example:
        >>> # Update multiple records with same values
        >>> operation = UpdateOperation(
        ...     model="res.partner",
        ...     data={"active": False},
        ...     record_ids=[1, 2, 3]
        ... )
        >>>
        >>> # Update multiple records with different values
        >>> operation = UpdateOperation(
        ...     model="res.partner",
        ...     data=[
        ...         {"id": 1, "name": "Updated Name 1"},
        ...         {"id": 2, "name": "Updated Name 2"}
        ...     ]
        ... )
    """

    record_ids: Optional[List[int]] = None
    operation_type: OperationType = field(default=OperationType.UPDATE, init=False)

    def validate(self) -> None:
        """Validate update operation data."""
        if not self.model:
            raise BatchValidationError("Model is required for update operation")

        if isinstance(self.data, dict):
            # Single update data for multiple records
            if not self.record_ids:
                raise BatchValidationError("Record IDs are required for bulk update")

            if not self.record_ids:
                raise BatchValidationError("Record IDs list cannot be empty")

            if not self.data:
                raise BatchValidationError("Update data cannot be empty")

        elif isinstance(self.data, list):
            # Individual update data for each record
            if not self.data:
                raise BatchValidationError("Update operation data cannot be empty")

            for i, record in enumerate(self.data):
                if not isinstance(record, dict):
                    raise BatchValidationError(f"Record {i} must be a dictionary")

                if "id" not in record:
                    raise BatchValidationError(f"Record {i} must contain 'id' field")

                if len(record) < 2:  # id + at least one field to update
                    raise BatchValidationError(
                        f"Record {i} must contain fields to update"
                    )

        else:
            raise BatchValidationError(
                "Update data must be a dictionary or list of dictionaries"
            )

    def get_batch_size(self) -> int:
        """Get the number of records to update."""
        if isinstance(self.data, dict):
            return len(self.record_ids) if self.record_ids else 0
        else:
            return len(self.data)

    def is_bulk_operation(self) -> bool:
        """Check if this is a bulk update operation.

        Returns:
            True if updating multiple records with the same data, False otherwise.
        """
        return isinstance(self.data, dict) and self.record_ids is not None

    def split(self, chunk_size: int) -> List["UpdateOperation"]:
        """Split update operation into smaller chunks."""
        if isinstance(self.data, dict):
            # Bulk update with same data
            if chunk_size >= len(self.record_ids):
                return [self]

            chunks = []
            for i in range(0, len(self.record_ids), chunk_size):
                chunk_ids = self.record_ids[i : i + chunk_size]
                chunk = UpdateOperation(
                    model=self.model,
                    data=self.data,
                    record_ids=chunk_ids,
                    context=self.context,
                    priority=self.priority,
                )
                chunks.append(chunk)

            return chunks

        else:
            # Individual updates
            if chunk_size >= len(self.data):
                return [self]

            chunks = []
            for i in range(0, len(self.data), chunk_size):
                chunk_data = self.data[i : i + chunk_size]
                chunk = UpdateOperation(
                    model=self.model,
                    data=chunk_data,
                    context=self.context,
                    priority=self.priority,
                )
                chunks.append(chunk)

            return chunks


@dataclass
class DeleteOperation(BatchOperation):
    """Batch delete operation.

    Deletes multiple records in a single batch operation
    with optimized performance.

    Example:
        >>> operation = DeleteOperation(
        ...     model="res.partner",
        ...     data=[1, 2, 3, 4, 5]  # Record IDs to delete
        ... )
    """

    operation_type: OperationType = field(default=OperationType.DELETE, init=False)

    def validate(self) -> None:
        """Validate delete operation data."""
        if not self.model:
            raise BatchValidationError("Model is required for delete operation")

        if not isinstance(self.data, list):
            raise BatchValidationError(
                "Delete operation data must be a list of record IDs"
            )

        if not self.data:
            raise BatchValidationError("Delete operation data cannot be empty")

        # Validate record IDs
        for i, record_id in enumerate(self.data):
            if not isinstance(record_id, int) or record_id <= 0:
                raise BatchValidationError(f"Record ID {i} must be a positive integer")

    def get_batch_size(self) -> int:
        """Get the number of records to delete."""
        return len(self.data)

    def split(self, chunk_size: int) -> List["DeleteOperation"]:
        """Split delete operation into smaller chunks."""
        if chunk_size >= len(self.data):
            return [self]

        chunks = []
        for i in range(0, len(self.data), chunk_size):
            chunk_data = self.data[i : i + chunk_size]
            chunk = DeleteOperation(
                model=self.model,
                data=chunk_data,
                context=self.context,
                priority=self.priority,
            )
            chunks.append(chunk)

        return chunks


def create_batch_operation(
    operation_type: str, model: str, data: Any, **kwargs
) -> BatchOperation:
    """Factory function to create batch operations.

    Args:
        operation_type: Type of operation ("create", "update", "delete")
        model: Odoo model name
        data: Operation data
        **kwargs: Additional operation parameters

    Returns:
        BatchOperation instance

    Raises:
        BatchValidationError: If operation type is invalid
    """
    operation_type = operation_type.lower()

    if operation_type == "create":
        return CreateOperation(model=model, data=data, **kwargs)
    elif operation_type == "update":
        return UpdateOperation(model=model, data=data, **kwargs)
    elif operation_type in ("delete", "unlink"):
        return DeleteOperation(model=model, data=data, **kwargs)
    else:
        raise BatchValidationError(f"Unknown operation type: {operation_type}")


def validate_batch_operations(operations: List[BatchOperation]) -> None:
    """Validate a list of batch operations.

    Args:
        operations: List of batch operations to validate

    Raises:
        BatchValidationError: If validation fails
    """
    if not operations:
        raise BatchValidationError("Operations list cannot be empty")

    for i, operation in enumerate(operations):
        try:
            operation.validate()
        except BatchValidationError as e:
            raise BatchValidationError(f"Operation {i} validation failed: {e}")

    # Check for conflicting operations
    _check_operation_conflicts(operations)


def _check_operation_conflicts(operations: List[BatchOperation]) -> None:
    """Check for conflicting operations in the batch.

    Args:
        operations: List of batch operations

    Raises:
        BatchValidationError: If conflicts are found
    """
    # Group operations by model
    model_operations = {}
    for operation in operations:
        if operation.model not in model_operations:
            model_operations[operation.model] = []
        model_operations[operation.model].append(operation)

    # Check for conflicts within each model
    for model, ops in model_operations.items():
        # Check for delete operations followed by updates
        delete_ops = [op for op in ops if op.operation_type == OperationType.DELETE]
        update_ops = [op for op in ops if op.operation_type == OperationType.UPDATE]

        if delete_ops and update_ops:
            # This could be valid in some cases, just warn
            pass  # Could add warning logic here
