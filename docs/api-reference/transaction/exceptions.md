# Transaction Exceptions

Exception classes for transaction management in Zenoo RPC.

## Overview

Transaction exceptions provide detailed error information for transaction-related failures:
- Transaction state errors
- Rollback failures
- Savepoint management errors
- Deadlock detection

## Exception Hierarchy

```python
class TransactionError(ZenooError):
    """Base exception for transaction-related errors."""
    pass

class TransactionStateError(TransactionError):
    """Raised when transaction is in invalid state."""
    pass

class RollbackError(TransactionError):
    """Raised when transaction rollback fails."""
    pass

class SavepointError(TransactionError):
    """Raised when savepoint operation fails."""
    pass

class DeadlockError(TransactionError):
    """Raised when deadlock is detected."""
    pass
```

## Exception Classes

### TransactionError

Base exception for all transaction-related errors.

```python
class TransactionError(ZenooError):
    """Base exception for transaction-related errors.
    
    Attributes:
        transaction_id: ID of the failed transaction
        operation: Operation that caused the error
        context: Additional error context
    """
    
    def __init__(self, message: str, transaction_id: str = None, operation: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.transaction_id = transaction_id
        self.operation = operation
        self.context = context or {}
```

### TransactionStateError

Raised when attempting operations on transactions in invalid states.

```python
class TransactionStateError(TransactionError):
    """Raised when transaction is in invalid state.
    
    Common scenarios:
    - Attempting to commit already committed transaction
    - Rolling back inactive transaction
    - Creating savepoint in rolled back transaction
    """
    
    def __init__(self, message: str, current_state: str, expected_state: str, **kwargs):
        super().__init__(message, **kwargs)
        self.current_state = current_state
        self.expected_state = expected_state
```

### RollbackError

Raised when transaction rollback operations fail.

```python
class RollbackError(TransactionError):
    """Raised when transaction rollback fails.
    
    Attributes:
        partial_rollback: Whether partial rollback occurred
        failed_operations: List of operations that failed to rollback
    """
    
    def __init__(self, message: str, partial_rollback: bool = False, failed_operations: List[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.partial_rollback = partial_rollback
        self.failed_operations = failed_operations or []
```

### SavepointError

Raised when savepoint operations fail.

```python
class SavepointError(TransactionError):
    """Raised when savepoint operation fails.
    
    Attributes:
        savepoint_name: Name of the failed savepoint
        savepoint_operation: Operation that failed (create, rollback, release)
    """
    
    def __init__(self, message: str, savepoint_name: str = None, savepoint_operation: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.savepoint_name = savepoint_name
        self.savepoint_operation = savepoint_operation
```

### DeadlockError

Raised when database deadlock is detected.

```python
class DeadlockError(TransactionError):
    """Raised when deadlock is detected.
    
    Attributes:
        involved_transactions: List of transaction IDs involved in deadlock
        retry_suggested: Whether retry is suggested
    """
    
    def __init__(self, message: str, involved_transactions: List[str] = None, retry_suggested: bool = True, **kwargs):
        super().__init__(message, **kwargs)
        self.involved_transactions = involved_transactions or []
        self.retry_suggested = retry_suggested
```

## Usage Examples

### Basic Exception Handling

```python
from zenoo_rpc.transaction.exceptions import TransactionError, TransactionStateError

async def handle_transaction_errors():
    """Demonstrate basic transaction error handling."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction() as tx:
                # Perform operations
                partner = await client.model("res.partner").create({
                    "name": "Test Partner"
                })
                
                # Simulate error condition
                if partner.id > 1000:
                    raise ValueError("Simulated error")
                
        except TransactionError as e:
            print(f"Transaction error: {e}")
            print(f"Transaction ID: {e.transaction_id}")
            print(f"Operation: {e.operation}")
            print(f"Context: {e.context}")
            
        except TransactionStateError as e:
            print(f"Transaction state error: {e}")
            print(f"Current state: {e.current_state}")
            print(f"Expected state: {e.expected_state}")
```

### Savepoint Error Handling

```python
from zenoo_rpc.transaction.exceptions import SavepointError

async def handle_savepoint_errors():
    """Demonstrate savepoint error handling."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction() as tx:
                # Create savepoint
                savepoint = await tx.create_savepoint("before_risky_operation")
                
                try:
                    # Risky operation
                    await client.model("res.partner").create({})  # Missing required fields
                    
                except Exception:
                    # Rollback to savepoint
                    await tx.rollback_to_savepoint(savepoint)
                    
        except SavepointError as e:
            print(f"Savepoint error: {e}")
            print(f"Savepoint name: {e.savepoint_name}")
            print(f"Operation: {e.savepoint_operation}")
```

### Deadlock Handling with Retry

```python
import asyncio
import random
from zenoo_rpc.transaction.exceptions import DeadlockError

async def handle_deadlock_with_retry():
    """Demonstrate deadlock handling with retry logic."""
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with ZenooClient("localhost", port=8069) as client:
                await client.login("demo", "admin", "admin")
                
                async with client.transaction() as tx:
                    # Operations that might cause deadlock
                    partner1 = await client.model("res.partner").filter(id=1).first()
                    partner2 = await client.model("res.partner").filter(id=2).first()
                    
                    # Update in potentially conflicting order
                    await partner1.update({"name": f"Updated {random.randint(1, 1000)}"})
                    await partner2.update({"name": f"Updated {random.randint(1, 1000)}"})
                
                # Success - break retry loop
                break
                
        except DeadlockError as e:
            retry_count += 1
            
            if e.retry_suggested and retry_count < max_retries:
                # Exponential backoff
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                print(f"Deadlock detected, retrying in {wait_time:.2f}s (attempt {retry_count}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                print(f"Deadlock error after {retry_count} retries: {e}")
                print(f"Involved transactions: {e.involved_transactions}")
                raise
```

### Custom Exception Handler

```python
class TransactionExceptionHandler:
    """Custom handler for transaction exceptions."""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts = defaultdict(int)
    
    async def handle_exception(self, exception: TransactionError, context: Dict[str, Any] = None):
        """Handle transaction exception with logging and metrics."""
        
        # Update error counts
        self.error_counts[type(exception).__name__] += 1
        
        # Log error details
        self.logger.error(
            f"Transaction error: {exception}",
            extra={
                "transaction_id": exception.transaction_id,
                "operation": exception.operation,
                "error_type": type(exception).__name__,
                "context": exception.context,
                "additional_context": context
            }
        )
        
        # Handle specific exception types
        if isinstance(exception, DeadlockError):
            await self._handle_deadlock(exception)
        elif isinstance(exception, RollbackError):
            await self._handle_rollback_error(exception)
        elif isinstance(exception, SavepointError):
            await self._handle_savepoint_error(exception)
    
    async def _handle_deadlock(self, error: DeadlockError):
        """Handle deadlock-specific logic."""
        
        self.logger.warning(
            f"Deadlock detected involving transactions: {error.involved_transactions}"
        )
        
        # Could implement deadlock resolution logic here
        # e.g., notify monitoring system, adjust retry policies, etc.
    
    async def _handle_rollback_error(self, error: RollbackError):
        """Handle rollback error-specific logic."""
        
        if error.partial_rollback:
            self.logger.critical(
                f"Partial rollback occurred. Failed operations: {error.failed_operations}"
            )
            # Could trigger data consistency checks
    
    async def _handle_savepoint_error(self, error: SavepointError):
        """Handle savepoint error-specific logic."""
        
        self.logger.error(
            f"Savepoint '{error.savepoint_name}' operation '{error.savepoint_operation}' failed"
        )
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get error statistics."""
        return dict(self.error_counts)

# Usage with custom handler
async def use_custom_exception_handler():
    """Demonstrate custom exception handler usage."""
    
    handler = TransactionExceptionHandler()
    
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            async with client.transaction() as tx:
                # Operations that might fail
                pass
                
    except TransactionError as e:
        await handler.handle_exception(e, context={"user_id": 123, "operation": "bulk_update"})
        
        # Get error statistics
        stats = handler.get_error_statistics()
        print(f"Error statistics: {stats}")
```

## Error Recovery Patterns

### Automatic Retry with Backoff

```python
import asyncio
import random
from typing import Callable, Any

async def retry_on_transaction_error(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
) -> Any:
    """Retry operation on transaction errors with exponential backoff."""
    
    for attempt in range(max_retries + 1):
        try:
            return await operation()
            
        except (DeadlockError, TransactionStateError) as e:
            if attempt == max_retries:
                raise
            
            # Calculate delay with jitter
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # 10% jitter
            total_delay = delay + jitter
            
            print(f"Transaction error on attempt {attempt + 1}, retrying in {total_delay:.2f}s: {e}")
            await asyncio.sleep(total_delay)
        
        except TransactionError as e:
            # Don't retry other transaction errors
            print(f"Non-retryable transaction error: {e}")
            raise

# Usage
async def example_with_retry():
    """Example using retry pattern."""
    
    async def risky_transaction():
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            async with client.transaction() as tx:
                # Potentially conflicting operations
                return await client.model("res.partner").create({
                    "name": "Retry Test Partner"
                })
    
    try:
        result = await retry_on_transaction_error(risky_transaction)
        print(f"Operation succeeded: {result}")
    except TransactionError as e:
        print(f"Operation failed after retries: {e}")
```

## Best Practices

1. **Specific Handling**: Handle specific exception types differently
2. **Retry Logic**: Implement retry logic for transient errors like deadlocks
3. **Logging**: Log transaction errors with sufficient context
4. **Monitoring**: Monitor transaction error rates and patterns
5. **Recovery**: Implement appropriate recovery strategies for each error type

## Related

- [Transaction Manager](manager.md) - Transaction management
- [Transaction Context](context.md) - Context usage
- [Error Handling Guide](../../user-guide/error-handling.md) - General error handling
