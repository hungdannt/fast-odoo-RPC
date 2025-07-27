"""
Transaction manager implementation for OdooFlow.

This module provides the core transaction management functionality,
including transaction lifecycle, savepoints, and rollback handling.
"""

import asyncio
import uuid
import time
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging

from .exceptions import (
    TransactionError,
    TransactionRollbackError,
    TransactionCommitError,
    TransactionStateError,
)

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction state enumeration."""

    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class OperationRecord:
    """Record of an operation for rollback purposes.

    Enhanced with proper rollback support and compensating operations.
    Based on SQLAlchemy transaction patterns and Saga pattern best practices.
    """

    operation_type: str  # 'create', 'update', 'delete'
    model: str
    record_ids: List[int]
    original_data: Optional[Dict[str, Any]] = None
    created_ids: Optional[List[int]] = None
    timestamp: float = field(default_factory=time.time)

    # Enhanced rollback support
    rollback_data: Optional[Dict[str, Any]] = None
    compensating_operation: Optional[Dict[str, Any]] = None
    rollback_status: str = "pending"  # pending, success, failed, skipped
    rollback_error: Optional[str] = None
    rollback_timestamp: Optional[float] = None

    # Operation context for better rollback
    operation_context: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None

    def get_compensating_operation(self) -> Dict[str, Any]:
        """Get the compensating operation to undo this operation.

        Returns a detailed compensating operation with all necessary context
        for proper rollback execution.
        """
        if self.compensating_operation:
            return self.compensating_operation

        if self.operation_type == "create":
            # Compensate CREATE with DELETE
            compensating_op = {
                "type": "delete",
                "model": self.model,
                "ids": self.created_ids or self.record_ids,
                "context": self.operation_context or {},
                "idempotency_key": (
                    f"rollback_{self.idempotency_key}"
                    if self.idempotency_key
                    else None
                ),
            }
        elif self.operation_type == "update":
            # Compensate UPDATE with restore original values
            compensating_op = {
                "type": "update",
                "model": self.model,
                "ids": self.record_ids,
                "values": self.original_data or {},
                "context": self.operation_context or {},
                "idempotency_key": (
                    f"rollback_{self.idempotency_key}"
                    if self.idempotency_key
                    else None
                ),
            }
        elif self.operation_type == "delete":
            # Compensate DELETE with CREATE (if data available)
            compensating_op = {
                "type": "create",
                "model": self.model,
                "values": self.rollback_data or self.original_data or {},
                "context": self.operation_context or {},
                "idempotency_key": (
                    f"rollback_{self.idempotency_key}"
                    if self.idempotency_key
                    else None
                ),
                "original_ids": self.record_ids,  # Store original IDs
            }
        else:
            raise ValueError(f"Unknown operation type: {self.operation_type}")

        # Cache the compensating operation
        self.compensating_operation = compensating_op
        return compensating_op

    def mark_rollback_success(self) -> None:
        """Mark this operation as successfully rolled back."""
        self.rollback_status = "success"
        self.rollback_timestamp = time.time()
        self.rollback_error = None

    def mark_rollback_failed(self, error: str) -> None:
        """Mark this operation as failed to rollback."""
        self.rollback_status = "failed"
        self.rollback_timestamp = time.time()
        self.rollback_error = error

    def mark_rollback_skipped(self, reason: str) -> None:
        """Mark this operation as skipped during rollback."""
        self.rollback_status = "skipped"
        self.rollback_timestamp = time.time()
        self.rollback_error = reason

    def is_rollback_complete(self) -> bool:
        """Check if rollback is complete (success or skipped)."""
        return self.rollback_status in ("success", "skipped")

    def can_rollback(self) -> bool:
        """Check if this operation can be rolled back."""
        if self.rollback_status != "pending":
            return False

        if self.operation_type == "create":
            return bool(self.created_ids or self.record_ids)
        elif self.operation_type == "update":
            return bool(self.record_ids and self.original_data)
        elif self.operation_type == "delete":
            return bool(self.rollback_data or self.original_data)

        return False


@dataclass
class Savepoint:
    """Represents a transaction savepoint for nested transaction support.

    Enhanced with rollback tracking, context management, and performance monitoring
    based on SQLAlchemy savepoint patterns.

    Features:
    - Operation index tracking for partial rollback
    - Context preservation for nested transactions
    - Performance monitoring and statistics
    - Rollback status tracking
    """

    name: str
    savepoint_id: str
    operation_index: int
    timestamp: float = field(default_factory=time.time)

    # Enhanced savepoint features
    context: Dict[str, Any] = field(default_factory=dict)
    parent_savepoint_id: Optional[str] = None
    is_released: bool = False
    rollback_count: int = 0

    # Performance tracking
    created_at: float = field(default_factory=time.time)
    released_at: Optional[float] = None
    last_rollback_at: Optional[float] = None

    def release(self) -> None:
        """Release this savepoint (mark as no longer needed)."""
        self.is_released = True
        self.released_at = time.time()

    def record_rollback(self) -> None:
        """Record a rollback to this savepoint."""
        self.rollback_count += 1
        self.last_rollback_at = time.time()

    def get_duration(self) -> Optional[float]:
        """Get savepoint lifetime duration."""
        if self.timestamp is None:
            return None

        end_time = self.released_at or time.time()
        return end_time - self.timestamp

    def is_active(self) -> bool:
        """Check if savepoint is still active (not released)."""
        return not self.is_released


class Transaction:
    """Represents a single transaction with Odoo.

    This class manages the lifecycle of a transaction, including
    operations tracking, commit/rollback, and savepoint management.

    Features:
    - Operation tracking for rollback
    - Savepoint support for nested transactions
    - Automatic cleanup on context exit
    - Performance monitoring

    Example:
        >>> async with client.transaction() as tx:
        ...     partner = await tx.create(ResPartner, name="Test")
        ...     await tx.update(partner, email="test@example.com")
        ...     # Automatic commit on success
    """

    def __init__(
        self,
        client: Any,
        transaction_id: Optional[str] = None,
        parent: Optional["Transaction"] = None,
    ):
        """Initialize a transaction.

        Args:
            client: OdooFlow client instance
            transaction_id: Unique transaction identifier
            parent: Parent transaction for nested transactions
        """
        self.id = transaction_id or str(uuid.uuid4())
        self.client = client
        self.parent = parent
        self.state = TransactionState.ACTIVE

        # Operation tracking for rollback
        self.operations: List[OperationRecord] = []
        self.savepoints: List[Savepoint] = []

        # Nested transactions
        self.children: Set["Transaction"] = set()
        if parent:
            parent.children.add(self)

        # Performance tracking
        self.start_time: Optional[float] = time.time()
        self.end_time: Optional[float] = None
        self.committed_at: Optional[float] = None
        self.rolled_back_at: Optional[float] = None

        # Context tracking
        self._context: Dict[str, Any] = {}

        # Cache invalidation tracking
        self._cache_invalidation_keys: set = set()
        self._cache_invalidation_patterns: set = set()
        self._cache_invalidation_models: set = set()

        logger.debug(f"Transaction {self.id} created")

    @property
    def context(self) -> Dict[str, Any]:
        """Get transaction context."""
        return self._context

    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self.state == TransactionState.ACTIVE

    @property
    def is_nested(self) -> bool:
        """Check if this is a nested transaction."""
        return self.parent is not None

    @property
    def duration(self) -> Optional[float]:
        """Get transaction duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def add_operation(
        self,
        operation_type: str,
        model: str,
        record_ids: Optional[List[int]] = None,
        original_data: Optional[Dict[str, Any]] = None,
        created_ids: Optional[List[int]] = None,
        data: Optional[Dict[str, Any]] = None,
        record_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        operation_context: Optional[Dict[str, Any]] = None,
        rollback_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an operation to the transaction log.

        Enhanced with idempotency support and operation context tracking.

        Args:
            operation_type: Type of operation (create, update, delete)
            model: Odoo model name
            record_ids: List of record IDs affected
            original_data: Original data before operation (for rollback)
            created_ids: IDs of created records (for create operations)
            data: Operation data (for create/update operations)
            record_id: Single record ID (converted to record_ids list)
            idempotency_key: Optional idempotency key for operation
            operation_context: Optional context for operation
            rollback_data: Optional specific data for rollback (for delete operations)
        """
        if not self.is_active:
            raise TransactionStateError(
                f"Cannot add operation to {self.state.value} transaction"
            )

        # Handle backward compatibility - use data as original_data if provided
        if data and not original_data:
            original_data = data

        # Handle record_id parameter (convert to record_ids list)
        if record_id is not None:
            record_ids = [record_id]
        elif record_ids is None:
            record_ids = []

        operation = OperationRecord(
            operation_type=operation_type,
            model=model,
            record_ids=record_ids,
            original_data=original_data,
            created_ids=created_ids,
            rollback_data=rollback_data,
            operation_context=operation_context or {},
            idempotency_key=idempotency_key,
        )

        self.operations.append(operation)

        # Track cache invalidation for this operation
        self._track_cache_invalidation(operation_type, model, record_ids)

        logger.debug(
            f"Transaction {self.id}: Added {operation_type} operation on {model}"
        )

    def set_context(self, key: str, value: Any) -> None:
        """Set context data for the transaction.

        Args:
            key: Context key
            value: Context value
        """
        self._context[key] = value

    def get_context(self, key: str = None, default: Any = None) -> Any:
        """Get context data from the transaction.

        Args:
            key: Context key (if None, returns all context)
            default: Default value if key not found

        Returns:
            Context value, all context, or default
        """
        if key is None:
            return self._context
        return self._context.get(key, default)

    def get_duration(self) -> Optional[float]:
        """Get transaction duration in seconds.

        Returns:
            Duration in seconds or None if not completed
        """
        if self.start_time is None:
            return None

        end_time = self.end_time or self.rolled_back_at or self.committed_at
        if end_time is None:
            # Transaction still active, return current duration
            import asyncio

            try:
                return asyncio.get_event_loop().time() - self.start_time
            except RuntimeError:
                # No event loop, use time.time()
                import time

                return time.time() - self.start_time

        return end_time - self.start_time

    async def create_savepoint(
        self,
        name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a savepoint for nested transaction support.

        Enhanced implementation with context preservation and proper
        savepoint hierarchy management.

        Args:
            name: Optional savepoint name
            context: Optional context to preserve with savepoint

        Returns:
            Savepoint identifier

        Raises:
            TransactionStateError: If transaction is not active
        """
        if not self.is_active:
            raise TransactionStateError(
                f"Cannot create savepoint in {self.state.value} transaction"
            )

        savepoint_name = name or f"sp_{len(self.savepoints)}"
        savepoint_id = str(uuid.uuid4())

        # Get parent savepoint ID if exists
        parent_savepoint_id = None
        if self.savepoints:
            # Find the most recent active savepoint
            for sp in reversed(self.savepoints):
                if sp.is_active():
                    parent_savepoint_id = sp.savepoint_id
                    break

        # Preserve current context and merge with provided context
        savepoint_context = {}
        # Always start with current transaction context
        savepoint_context.update(self.context)
        # Override with provided context if any
        if context:
            savepoint_context.update(context)

        savepoint = Savepoint(
            name=savepoint_name,
            savepoint_id=savepoint_id,
            operation_index=len(self.operations),
            context=savepoint_context,
            parent_savepoint_id=parent_savepoint_id,
        )

        self.savepoints.append(savepoint)

        logger.info(
            f"Transaction {self.id}: Created savepoint {savepoint_name} "
            f"at operation index {len(self.operations)} "
            f"(parent: {parent_savepoint_id})"
        )

        return savepoint_id

    async def release_savepoint(self, savepoint_id: str) -> None:
        """Release a savepoint (mark as no longer needed).

        Args:
            savepoint_id: Savepoint identifier to release

        Raises:
            TransactionError: If savepoint not found
        """
        savepoint = None
        for sp in self.savepoints:
            if sp.savepoint_id == savepoint_id:
                savepoint = sp
                break

        if savepoint is None:
            raise TransactionError(
                f"Savepoint {savepoint_id} not found in transaction {self.id}"
            )

        if savepoint.is_released:
            logger.warning(f"Savepoint {savepoint_id} is already released")
            return

        savepoint.release()

        logger.debug(
            f"Transaction {self.id}: Released savepoint {savepoint.name}"
        )

    def get_active_savepoints(self) -> List[Savepoint]:
        """Get list of active (not released) savepoints.

        Returns:
            List of active savepoints
        """
        return [sp for sp in self.savepoints if sp.is_active()]

    def get_savepoint_by_name(self, name: str) -> Optional[Savepoint]:
        """Get savepoint by name.

        Args:
            name: Savepoint name

        Returns:
            Savepoint if found, None otherwise
        """
        for sp in self.savepoints:
            if sp.name == name and sp.is_active():
                return sp
        return None

    def _track_cache_invalidation(
        self,
        operation_type: str,
        model: str,
        record_ids: Optional[List[int]] = None,
    ) -> None:
        """Track cache keys that need invalidation for this operation.

        Args:
            operation_type: Type of operation (create, update, delete)
            model: Odoo model name
            record_ids: List of record IDs affected
        """
        # Track model-level invalidation
        self._cache_invalidation_models.add(model)

        # Track specific record invalidation patterns
        if record_ids:
            for record_id in record_ids:
                # Individual record cache keys
                self._cache_invalidation_keys.add(f"{model}:{record_id}")
                self._cache_invalidation_keys.add(
                    f"record:{model}:{record_id}"
                )

        # Track query-level invalidation patterns
        self._cache_invalidation_patterns.add(f"{model}:*")
        self._cache_invalidation_patterns.add(f"query:{model}:*")

        # Track list/search cache patterns
        self._cache_invalidation_patterns.add(f"search:{model}:*")
        self._cache_invalidation_patterns.add(f"list:{model}:*")

    def add_cache_invalidation_key(self, key: str) -> None:
        """Add a specific cache key for invalidation.

        Args:
            key: Cache key to invalidate
        """
        self._cache_invalidation_keys.add(key)

    def add_cache_invalidation_pattern(self, pattern: str) -> None:
        """Add a cache pattern for invalidation.

        Args:
            pattern: Cache pattern to invalidate (supports wildcards)
        """
        self._cache_invalidation_patterns.add(pattern)

    def get_cache_invalidation_data(self) -> Dict[str, Any]:
        """Get cache invalidation data for this transaction.

        Returns:
            Dictionary with cache invalidation information
        """
        return {
            "keys": list(self._cache_invalidation_keys),
            "patterns": list(self._cache_invalidation_patterns),
            "models": list(self._cache_invalidation_models),
        }

    async def rollback_to_savepoint(self, savepoint_id: str) -> None:
        """Rollback to a specific savepoint.

        Enhanced implementation with proper savepoint tracking,
        context restoration, and performance monitoring.

        Args:
            savepoint_id: Savepoint identifier to rollback to

        Raises:
            TransactionStateError: If transaction is not active
            TransactionError: If savepoint not found or already released
            TransactionRollbackError: If rollback operations fail
        """
        if not self.is_active:
            raise TransactionStateError(
                f"Cannot rollback in {self.state.value} transaction"
            )

        # Find the savepoint
        savepoint = None
        savepoint_index = -1
        for i, sp in enumerate(self.savepoints):
            if sp.savepoint_id == savepoint_id:
                savepoint = sp
                savepoint_index = i
                break

        if savepoint is None:
            raise TransactionError(
                f"Savepoint {savepoint_id} not found in transaction {self.id}"
            )

        if savepoint.is_released:
            raise TransactionError(
                f"Savepoint {savepoint_id} has already been released"
            )

        # Check if savepoint is still valid (not superseded by later savepoints)
        if not savepoint.is_active():
            raise TransactionError(
                f"Savepoint {savepoint_id} is no longer active"
            )

        logger.info(
            f"Transaction {self.id}: Rolling back to savepoint {savepoint.name} "
            f"(created at operation index {savepoint.operation_index})"
        )

        # Get operations to rollback (after the savepoint)
        operations_to_rollback = self.operations[savepoint.operation_index :]

        if not operations_to_rollback:
            logger.info(
                f"Transaction {self.id}: No operations to rollback for savepoint {savepoint.name}"
            )
            return

        try:
            # Execute rollback operations
            await self._execute_rollback_operations(operations_to_rollback)

            # Remove operations after savepoint
            self.operations = self.operations[: savepoint.operation_index]

            # Release savepoints after this one
            for sp in self.savepoints[savepoint_index + 1 :]:
                sp.release()

            # Keep only savepoints up to and including the target savepoint
            self.savepoints = self.savepoints[: savepoint_index + 1]

            # Record rollback in savepoint
            savepoint.record_rollback()

            # Restore context if available
            if savepoint.context:
                for key, value in savepoint.context.items():
                    self.context[key] = value

            logger.info(
                f"Transaction {self.id}: Successfully rolled back to savepoint {savepoint.name} "
                f"(rolled back {len(operations_to_rollback)} operations)"
            )

        except Exception as e:
            logger.error(
                f"Transaction {self.id}: Failed to rollback to savepoint {savepoint.name}: {e}"
            )
            raise TransactionRollbackError(
                f"Failed to rollback to savepoint {savepoint.name}: {e}",
                transaction_id=self.id,
            ) from e

    async def _execute_rollback_operations(
        self, operations: List[OperationRecord]
    ) -> None:
        """Execute compensating operations to rollback changes.

        Enhanced implementation with proper error handling, operation tracking,
        and partial rollback support based on SQLAlchemy patterns.

        Args:
            operations: List of operations to rollback (in reverse order)

        Raises:
            TransactionRollbackError: If critical operations fail to rollback
        """
        failed_operations = []
        skipped_operations = []
        successful_operations = []

        logger.info(
            f"Transaction {self.id}: Starting rollback of {len(operations)} operations"
        )

        # Process operations in reverse order (LIFO - Last In, First Out)
        for operation in reversed(operations):
            try:
                # Check if operation can be rolled back
                if not operation.can_rollback():
                    operation.mark_rollback_skipped(
                        "Operation cannot be rolled back - missing required data"
                    )
                    skipped_operations.append(operation)
                    logger.warning(
                        f"Skipping rollback of {operation.operation_type} "
                        f"on {operation.model}: insufficient data"
                    )
                    continue

                # Get compensating operation
                compensating_op = operation.get_compensating_operation()

                # Execute the compensating operation
                await self._execute_compensating_operation(
                    compensating_op, operation
                )

                # Mark as successful
                operation.mark_rollback_success()
                successful_operations.append(operation)

                logger.debug(
                    f"Successfully rolled back {operation.operation_type} "
                    f"on {operation.model} (IDs: {operation.record_ids})"
                )

            except Exception as e:
                # Mark as failed and continue with other operations
                operation.mark_rollback_failed(str(e))
                failed_operations.append((operation, e))

                logger.error(
                    f"Failed to rollback {operation.operation_type} "
                    f"on {operation.model} (IDs: {operation.record_ids}): {e}"
                )

                # Continue with other operations for partial rollback
                continue

        # Log rollback summary
        logger.info(
            f"Transaction {self.id}: Rollback completed - "
            f"Success: {len(successful_operations)}, "
            f"Failed: {len(failed_operations)}, "
            f"Skipped: {len(skipped_operations)}"
        )

        # Raise error if any critical operations failed
        if failed_operations:
            error_msg = (
                f"Failed to rollback {len(failed_operations)} operations. "
                f"Successfully rolled back {len(successful_operations)} operations. "
                f"Skipped {len(skipped_operations)} operations."
            )

            # Create enhanced error with context
            raise TransactionRollbackError(
                error_msg,
                transaction_id=self.id,
                failed_operations=failed_operations,
                partial_rollback=len(successful_operations) > 0,
            )

    async def _execute_compensating_operation(
        self, operation: Dict[str, Any], operation_record: OperationRecord
    ) -> None:
        """Execute a single compensating operation.

        Enhanced implementation with proper error handling, idempotency,
        and detailed logging based on best practices.

        Args:
            operation: Compensating operation to execute
            operation_record: Original operation record for context

        Raises:
            Exception: If the compensating operation fails
        """
        op_type = operation["type"]
        model = operation["model"]
        context = operation.get("context", {})
        idempotency_key = operation.get("idempotency_key")

        logger.debug(
            f"Executing compensating operation: {op_type} on {model} "
            f"(idempotency_key: {idempotency_key})"
        )

        try:
            if op_type == "delete":
                # Compensate CREATE by deleting created records
                await self._rollback_create_operation(
                    operation, operation_record
                )

            elif op_type == "update":
                # Compensate UPDATE by restoring original values
                await self._rollback_update_operation(
                    operation, operation_record
                )

            elif op_type == "create":
                # Compensate DELETE by recreating records (complex)
                await self._rollback_delete_operation(
                    operation, operation_record
                )

            else:
                raise ValueError(
                    f"Unknown compensating operation type: {op_type}"
                )

        except Exception as e:
            logger.error(
                f"Compensating operation failed: {op_type} on {model} - {e}"
            )
            raise

    async def _rollback_create_operation(
        self, operation: Dict[str, Any], operation_record: OperationRecord
    ) -> None:
        """Rollback CREATE operation by deleting created records.

        Args:
            operation: Compensating delete operation
            operation_record: Original create operation record
        """
        ids = operation["ids"]
        model = operation["model"]

        if not ids:
            logger.warning(
                f"No IDs to delete for rollback of create on {model}"
            )
            return

        try:
            # Use client's unlink method to delete records
            result = await self.client.unlink(model, ids)

            logger.info(
                f"Rollback CREATE: Successfully deleted {len(ids)} records "
                f"from {model} (result: {result})"
            )

        except Exception as e:
            # Check if records were already deleted (idempotency)
            if (
                "does not exist" in str(e).lower()
                or "not found" in str(e).lower()
            ):
                logger.warning(
                    f"Records already deleted during rollback of {model}: {ids}"
                )
                return  # Consider this successful (idempotent)

            raise Exception(
                f"Failed to delete records {ids} from {model} during rollback: {e}"
            ) from e

    async def _rollback_update_operation(
        self, operation: Dict[str, Any], operation_record: OperationRecord
    ) -> None:
        """Rollback UPDATE operation by restoring original values.

        Args:
            operation: Compensating update operation
            operation_record: Original update operation record
        """
        ids = operation["ids"]
        values = operation["values"]
        model = operation["model"]

        if not ids:
            logger.warning(f"No IDs to update for rollback on {model}")
            return

        if not values:
            logger.warning(
                f"No original values to restore for rollback on {model}: {ids}"
            )
            return

        try:
            # Use client's write method to restore original values
            result = await self.client.write(model, ids, values)

            logger.info(
                f"Rollback UPDATE: Successfully restored {len(ids)} records "
                f"in {model} with {len(values)} fields (result: {result})"
            )

        except Exception as e:
            raise Exception(
                f"Failed to restore values for records {ids} in {model} "
                f"during rollback: {e}"
            ) from e

    async def _rollback_delete_operation(
        self, operation: Dict[str, Any], operation_record: OperationRecord
    ) -> None:
        """Rollback DELETE operation by recreating records.

        This is the most complex rollback operation as it requires
        recreating deleted records with all their relationships.

        Args:
            operation: Compensating create operation
            operation_record: Original delete operation record
        """
        values = operation["values"]
        model = operation["model"]
        original_ids = operation.get("original_ids", [])

        if not values:
            logger.error(
                f"Cannot rollback DELETE on {model}: no data available to recreate records"
            )
            raise Exception(
                f"Cannot rollback DELETE on {model}: missing rollback data"
            )

        try:
            # This is complex because:
            # 1. We need to handle relationships properly
            # 2. IDs will be different after recreation
            # 3. Some fields might not be recreatable

            logger.warning(
                f"Attempting to rollback DELETE on {model} - "
                f"this may result in data inconsistencies"
            )

            # For now, we'll attempt basic recreation
            # In a production system, this would need more sophisticated handling
            if isinstance(values, dict):
                # Single record
                result = await self.client.create(model, values)
                logger.info(
                    f"Rollback DELETE: Recreated record in {model} "
                    f"(original ID: {original_ids}, new ID: {result})"
                )
            elif isinstance(values, list):
                # Multiple records
                results = []
                for record_values in values:
                    result = await self.client.create(model, record_values)
                    results.append(result)

                logger.info(
                    f"Rollback DELETE: Recreated {len(results)} records in {model} "
                    f"(original IDs: {original_ids}, new IDs: {results})"
                )
            else:
                raise ValueError(
                    f"Invalid values format for recreation: {type(values)}"
                )

        except Exception as e:
            raise Exception(
                f"Failed to recreate deleted records in {model} during rollback: {e}"
            ) from e

    async def commit(self) -> None:
        """Commit the transaction.

        This method commits all operations in the transaction.
        For nested transactions, this only marks the transaction as committed;
        the actual commit happens when the root transaction commits.
        """
        if not self.is_active:
            raise TransactionStateError(
                f"Cannot commit {self.state.value} transaction"
            )

        try:
            # For nested transactions, just mark as committed
            if self.is_nested:
                self.state = TransactionState.COMMITTED
                logger.debug(
                    f"Nested transaction {self.id} marked as committed"
                )
                return

            # Commit all child transactions first
            for child in self.children:
                if child.is_active:
                    await child.commit()

            # Perform actual commit operations
            await self._perform_commit()

            # Invalidate cache after successful commit
            await self._invalidate_cache_on_commit()

            self.state = TransactionState.COMMITTED
            self.end_time = asyncio.get_event_loop().time()
            self.committed_at = self.end_time

            logger.info(
                f"Transaction {self.id} committed successfully with {len(self.operations)} operations"
            )

        except Exception as e:
            self.state = TransactionState.FAILED
            logger.error(f"Transaction {self.id} commit failed: {e}")
            raise TransactionCommitError(
                f"Failed to commit transaction {self.id}",
                original_error=e,
                transaction_id=self.id,
            )

    async def rollback(self) -> None:
        """Rollback the transaction.

        This method undoes all operations in the transaction.
        """
        if self.state in (
            TransactionState.COMMITTED,
            TransactionState.ROLLED_BACK,
        ):
            logger.warning(f"Transaction {self.id} already {self.state.value}")
            return

        try:
            # Rollback all child transactions first
            for child in self.children:
                if child.is_active:
                    await child.rollback()

            # Rollback operations using compensating operations
            await self._execute_rollback_operations(self.operations)

            # Clear operations after successful rollback
            self.operations.clear()
            self.savepoints.clear()

            self.state = TransactionState.ROLLED_BACK
            self.end_time = asyncio.get_event_loop().time()
            self.rolled_back_at = self.end_time

            logger.info(f"Transaction {self.id} rolled back successfully")

        except TransactionRollbackError as e:
            # This is already a properly formatted rollback error with context
            # Just update transaction state and re-raise
            self.state = TransactionState.FAILED
            self.end_time = asyncio.get_event_loop().time()
            self.rolled_back_at = self.end_time

            logger.error(f"Transaction {self.id} rollback failed: {e}")
            raise  # Re-raise the original TransactionRollbackError with context

        except Exception as e:
            # Unexpected error during rollback
            self.state = TransactionState.FAILED
            self.end_time = asyncio.get_event_loop().time()
            self.rolled_back_at = self.end_time

            logger.error(f"Transaction {self.id} rollback failed: {e}")
            raise TransactionRollbackError(
                f"Failed to rollback transaction {self.id}",
                original_error=e,
                transaction_id=self.id,
            )

    async def _perform_commit(self) -> None:
        """Perform the actual commit operations."""
        # In a real implementation, this would batch operations
        # and send them to Odoo in an optimized way

        # For now, we just log the operations that would be committed
        logger.debug(
            f"Transaction {self.id}: Committing {len(self.operations)} operations"
        )

        # Group operations by type for batch processing
        creates = [
            op for op in self.operations if op.operation_type == "create"
        ]
        updates = [
            op for op in self.operations if op.operation_type == "update"
        ]
        deletes = [
            op for op in self.operations if op.operation_type == "delete"
        ]

        # Process in order: creates, updates, deletes
        if creates:
            logger.debug(
                f"Transaction {self.id}: Processing {len(creates)} create operations"
            )
            # For now, just log the operations - actual implementation would execute them
            for op in creates:
                logger.debug(
                    f"Create operation: {op.model} with {len(op.record_ids)} records"
                )

        if updates:
            logger.debug(
                f"Transaction {self.id}: Processing {len(updates)} update operations"
            )
            for op in updates:
                logger.debug(
                    f"Update operation: {op.model} with {len(op.record_ids)} records"
                )

        if deletes:
            logger.debug(
                f"Transaction {self.id}: Processing {len(deletes)} delete operations"
            )
            for op in deletes:
                logger.debug(
                    f"Delete operation: {op.model} with {len(op.record_ids)} records"
                )

    async def _invalidate_cache_on_commit(self) -> None:
        """Invalidate cache entries after successful transaction commit."""
        try:
            # Get cache manager from client if available
            cache_manager = getattr(self.client, "cache_manager", None)
            if not cache_manager:
                logger.debug("No cache manager available for invalidation")
                return

            invalidation_data = self.get_cache_invalidation_data()
            total_invalidated = 0

            # Invalidate specific cache keys
            for key in invalidation_data["keys"]:
                try:
                    await cache_manager.delete(key)
                    total_invalidated += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to invalidate cache key {key}: {e}"
                    )

            # Invalidate cache patterns
            for pattern in invalidation_data["patterns"]:
                try:
                    count = await cache_manager.invalidate_pattern(pattern)
                    total_invalidated += count
                except Exception as e:
                    logger.warning(
                        f"Failed to invalidate cache pattern {pattern}: {e}"
                    )

            # Invalidate model-level caches
            for model in invalidation_data["models"]:
                try:
                    count = await cache_manager.invalidate_model(model)
                    total_invalidated += count
                except Exception as e:
                    logger.warning(
                        f"Failed to invalidate model cache {model}: {e}"
                    )

            if total_invalidated > 0:
                logger.info(
                    f"Transaction {self.id}: Invalidated {total_invalidated} cache entries"
                )

        except Exception as e:
            # Cache invalidation failure should not fail the transaction
            logger.error(
                f"Cache invalidation failed for transaction {self.id}: {e}"
            )


class TransactionManager:
    """Manages transactions for an OdooFlow client.

    This class provides transaction management capabilities,
    including nested transactions, savepoints, and batch operations.
    """

    def __init__(self, client: Any):
        """Initialize the transaction manager.

        Args:
            client: OdooFlow client instance
        """
        self.client = client
        self.active_transactions: Dict[str, Transaction] = {}
        self.current_transaction: Optional[Transaction] = None

        # Statistics tracking
        self.successful_transactions = 0
        self.failed_transactions = 0

    @asynccontextmanager
    async def transaction(
        self, transaction_id: Optional[str] = None, auto_commit: bool = True
    ):
        """Create a new transaction context.

        Args:
            transaction_id: Optional transaction identifier
            auto_commit: Whether to auto-commit on success

        Yields:
            Transaction instance

        Example:
            >>> async with client.transaction_manager.transaction() as tx:
            ...     await tx.create(ResPartner, name="Test")
            ...     # Auto-commit on success
        """
        # Create transaction
        parent = self.current_transaction
        transaction = Transaction(
            client=self.client, transaction_id=transaction_id, parent=parent
        )

        # Set as current transaction
        previous_transaction = self.current_transaction
        self.current_transaction = transaction
        self.active_transactions[transaction.id] = transaction

        # Start timing
        transaction.start_time = asyncio.get_event_loop().time()

        try:
            logger.info(f"Starting transaction {transaction.id}")
            yield transaction

            # Auto-commit if enabled and no exceptions
            if auto_commit and transaction.is_active:
                await transaction.commit()

        except Exception as e:
            # Auto-rollback on exception
            if transaction.is_active:
                logger.warning(
                    f"Transaction {transaction.id} failed, rolling back: {e}"
                )
                await transaction.rollback()
            raise

        finally:
            # Track transaction outcome
            if transaction.state == TransactionState.COMMITTED:
                self.successful_transactions += 1
            elif transaction.state in [
                TransactionState.ROLLED_BACK,
                TransactionState.FAILED,
            ]:
                self.failed_transactions += 1

            # Cleanup
            self.current_transaction = previous_transaction
            if transaction.id in self.active_transactions:
                del self.active_transactions[transaction.id]

            logger.debug(f"Transaction {transaction.id} context exited")

    def get_current_transaction(self) -> Optional[Transaction]:
        """Get the current active transaction.

        Returns:
            Current transaction or None
        """
        return self.current_transaction

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID.

        Args:
            transaction_id: Transaction identifier

        Returns:
            Transaction instance or None
        """
        return self.active_transactions.get(transaction_id)

    async def rollback_all(self) -> None:
        """Rollback all active transactions."""
        for transaction in list(self.active_transactions.values()):
            if transaction.is_active:
                await transaction.rollback()

    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get statistics about active transactions.

        Returns:
            Dictionary with transaction statistics
        """
        active_count = len(
            [tx for tx in self.active_transactions.values() if tx.is_active]
        )
        total_operations = sum(
            len(tx.operations) for tx in self.active_transactions.values()
        )

        return {
            "active_transactions": active_count,
            "total_transactions": len(self.active_transactions),
            "total_operations": total_operations,
            "current_transaction_id": (
                self.current_transaction.id
                if self.current_transaction
                else None
            ),
            "successful_transactions": self.successful_transactions,
            "failed_transactions": self.failed_transactions,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about active transactions (alias for get_transaction_stats).

        Returns:
            Dictionary with transaction statistics
        """
        return self.get_transaction_stats()
