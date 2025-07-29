# Batch API Reference

The batch module provides efficient bulk operations for creating, updating, and deleting multiple records with performance optimization, chunking, and concurrency control.

## Overview

The batch system consists of:

- **BatchManager**: Main interface for batch operations
- **Batch Operations**: CreateOperation, UpdateOperation, DeleteOperation
- **BatchExecutor**: Handles execution with performance optimization
- **Context Managers**: Convenient batch contexts
- **Chunking**: Automatic operation splitting for large datasets

## BatchManager

Main batch management interface coordinating bulk operations.

### Constructor

```python
class BatchManager:
    """Main batch operations manager for Zenoo RPC.

    This class provides a high-level interface for creating and executing
    batch operations with automatic optimization and error handling.

    Features:
    - Fluent interface for batch building
    - Automatic operation optimization
    - Progress tracking and monitoring
    - Error handling and recovery
    - Performance statistics
    """

    def __init__(
        self,
        client: Any,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[int] = None,
    ):
        """Initialize batch manager.

        Args:
            client: Zenoo RPC client instance
            max_chunk_size: Maximum records per chunk
            max_concurrency: Maximum concurrent operations
            timeout: Operation timeout in seconds
        """
        self.client = client
        self.max_chunk_size = max_chunk_size
        self.max_concurrency = max_concurrency
        self.timeout = timeout

        # Active batches
        self.active_batches = {}

        # Statistics
        self.stats = {
            "total_batches": 0,
            "completed_batches": 0,
            "failed_batches": 0,
            "total_operations": 0,
            "total_records": 0,
        }
```

**Parameters:**

- `client` (ZenooClient): Zenoo RPC client instance
- `max_chunk_size` (int): Maximum records per chunk (default: 100)
- `max_concurrency` (int): Maximum concurrent operations (default: 5)
- `timeout` (int, optional): Operation timeout in seconds (default: None)

**Example:**

```python
from zenoo_rpc.batch.manager import BatchManager

# Basic setup
batch_manager = BatchManager(client=client)

# Custom configuration
batch_manager = BatchManager(
    client=client,
    max_chunk_size=200,
    max_concurrency=10,
    timeout=600
)

# Attach to client
client.batch_manager = BatchManager(client=client)
```

### Batch Context

#### `async batch()`

Create a batch context for collecting and executing operations.

**Returns:** `AsyncContextManager[BatchContext]` - Batch context

**Example:**

```python
# Basic batch context
async with batch_manager.batch() as batch_context:
    # Operations are collected and executed automatically on context exit
    await batch_context.create(
        model="res.partner",
        data=[
            {"name": "Company A", "email": "a@company.com"},
            {"name": "Company B", "email": "b@company.com"}
        ]
    )

    # Update operations
    await batch_context.update(
        model="res.partner",
        record_ids=[1, 2],
        data={"active": True}
    )

    # Delete operations
    await batch_context.delete(
        model="res.partner",
        record_ids=[3, 4, 5]
    )
```

### Bulk Operations

#### `async bulk_create(model, records, chunk_size=None, context=None)`

Create multiple records efficiently.

**Parameters:**

- `model` (str): Odoo model name
- `records` (List[Dict[str, Any]]): List of record data
- `chunk_size` (int, optional): Override default chunk size
- `context` (Dict[str, Any], optional): Execution context

**Returns:** `List[int]` - List of created record IDs

**Example:**

```python
# Basic bulk create
partners_data = [
    {"name": "ACME Corp", "email": "contact@acme.com", "is_company": True},
    {"name": "Global Inc", "email": "info@global.com", "is_company": True},
    {"name": "Tech Solutions", "email": "hello@tech.com", "is_company": True}
]

created_ids = await batch_manager.bulk_create(
    model="res.partner",
    records=partners_data,
    chunk_size=50
)

print(f"Created {len(created_ids)} partners")
for i, partner_id in enumerate(created_ids):
    print(f"Partner {i+1}: ID {partner_id}")
```

#### `async bulk_update(model, data, record_ids=None, chunk_size=None, context=None)`

Update multiple records efficiently.

**Parameters:**

- `model` (str): Odoo model name
- `data` (Union[Dict[str, Any], List[Dict[str, Any]]]): Update data
  - Dict: Same data for all records (requires record_ids)
  - List: Individual data per record (format: `[{"id": 1, "field": "value"}, ...]`)
- `record_ids` (List[int], optional): Record IDs (required if data is dict)
- `chunk_size` (int, optional): Override default chunk size
- `context` (Dict[str, Any], optional): Execution context

**Returns:** `bool` - True if all updates successful

**Example:**

```python
# Individual record updates
individual_updates = [
    {"id": 1, "active": True, "customer_rank": 1},
    {"id": 2, "active": True, "customer_rank": 2},
    {"id": 3, "active": False, "customer_rank": 0}
]

success = await batch_manager.bulk_update(
    model="res.partner",
    data=individual_updates
)

# Bulk update with same data for multiple records
success = await batch_manager.bulk_update(
    model="res.partner",
    data={"active": True, "customer_rank": 1},
    record_ids=[1, 2, 3, 4, 5]
)
```

#### `async bulk_delete(model, record_ids, chunk_size=None, context=None)`

Delete multiple records efficiently.

**Parameters:**

- `model` (str): Odoo model name
- `record_ids` (List[int]): List of record IDs to delete
- `chunk_size` (int, optional): Override default chunk size
- `context` (Dict[str, Any], optional): Execution context

**Returns:** `bool` - True if all deletions successful

**Example:**

```python
# Delete multiple records
record_ids_to_delete = [10, 11, 12, 13, 14]

success = await batch_manager.bulk_delete(
    model="res.partner",
    record_ids=record_ids_to_delete,
    chunk_size=25
)

if success:
    print(f"Successfully deleted {len(record_ids_to_delete)} records")
```

### Advanced Batch Operations

#### `create_batch(batch_id=None)`

Create a batch for manual operation building.

**Parameters:**

- `batch_id` (str, optional): Custom batch identifier

**Returns:** `Batch` - Batch instance for operation building

**Example:**

```python
# Manual batch building
batch = batch_manager.create_batch("custom-batch-001")

# Add operations
batch.create("res.partner", [
    {"name": "Company A", "is_company": True},
    {"name": "Company B", "is_company": True}
])

batch.update("res.partner", {"active": False}, record_ids=[1, 2, 3])

batch.unlink("res.partner", [4, 5, 6])

# Execute batch
results = await batch.execute()
```

#### `async execute_operations(operations, progress_callback=None)`

Execute a list of batch operations.

**Parameters:**

- `operations` (List[BatchOperation]): List of operations to execute
- `progress_callback` (Callable, optional): Progress callback function

**Returns:** `Dict[str, Any]` - Execution results and statistics

**Example:**

```python
from zenoo_rpc.batch.operations import CreateOperation, UpdateOperation

# Create operations manually
operations = [
    CreateOperation(
        model="res.partner",
        data=[{"name": "Test Company"}]
    ),
    UpdateOperation(
        model="res.partner",
        data={"active": True},
        record_ids=[1, 2, 3]
    )
]

# Progress callback
async def progress_callback(progress):
    print(f"Progress: {progress['completed']}/{progress['total']} "
          f"({progress['percentage']:.1f}%)")
    print(f"Stats: {progress['stats']}")

# Execute operations
results = await batch_manager.execute_operations(
    operations,
    progress_callback=progress_callback
)

print(f"Completed: {results['stats']['completed_operations']}")
print(f"Failed: {results['stats']['failed_operations']}")
```

## Batch Operations

### CreateOperation

Batch create operation for multiple record creation.

```python
@dataclass
class CreateOperation(BatchOperation):
    """Batch create operation."""

    model: str
    data: List[Dict[str, Any]]
    operation_type: OperationType = field(default=OperationType.CREATE, init=False)
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OperationStatus = OperationStatus.PENDING
    priority: int = 0
    context: Optional[Dict[str, Any]] = None
    return_ids: bool = True

    # Execution metadata
    created_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Any] = None
```

**Example:**

```python
from zenoo_rpc.batch.operations import CreateOperation

operation = CreateOperation(
    model="res.partner",
    data=[
        {"name": "Company A", "is_company": True},
        {"name": "Company B", "is_company": True}
    ],
    context={"active_test": False},
    priority=1
)

# Get operation info
print(f"Batch size: {operation.get_batch_size()}")  # 2
print(f"Operation ID: {operation.operation_id}")
print(f"Status: {operation.status}")

# Split into chunks
chunks = operation.split(chunk_size=1)
print(f"Split into {len(chunks)} chunks")

# Check completion status
print(f"Is completed: {operation.is_completed()}")
print(f"Is successful: {operation.is_successful()}")
```

### UpdateOperation

Batch update operation for multiple record updates.

```python
@dataclass
class UpdateOperation(BatchOperation):
    """Batch update operation."""

    model: str
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    operation_type: OperationType = field(default=OperationType.UPDATE, init=False)
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OperationStatus = OperationStatus.PENDING
    priority: int = 0
    context: Optional[Dict[str, Any]] = None
    record_ids: Optional[List[int]] = None

    # Execution metadata
    created_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Any] = None
```

**Example:**

```python
from zenoo_rpc.batch.operations import UpdateOperation

# Same data for multiple records (bulk update)
operation1 = UpdateOperation(
    model="res.partner",
    data={"active": True},
    record_ids=[1, 2, 3, 4, 5]
)

print(f"Is bulk operation: {operation1.is_bulk_operation()}")  # True
print(f"Batch size: {operation1.get_batch_size()}")  # 5

# Different data for each record (individual updates)
operation2 = UpdateOperation(
    model="res.partner",
    data=[
        {"id": 1, "name": "Updated Name 1"},
        {"id": 2, "name": "Updated Name 2"}
    ]
)

print(f"Is bulk operation: {operation2.is_bulk_operation()}")  # False
print(f"Batch size: {operation2.get_batch_size()}")  # 2
```

### DeleteOperation

Batch delete operation for multiple record deletion.

```python
@dataclass
class DeleteOperation(BatchOperation):
    """Batch delete operation."""

    model: str
    data: List[int]  # Record IDs to delete
    operation_type: OperationType = field(default=OperationType.DELETE, init=False)
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
```

**Example:**

```python
from zenoo_rpc.batch.operations import DeleteOperation

operation = DeleteOperation(
    model="res.partner",
    data=[1, 2, 3, 4, 5],  # Record IDs
    context={"active_test": False}
)

print(f"Will delete {operation.get_batch_size()} records")
```

## BatchExecutor

Handles execution of batch operations with performance optimization.

### Constructor

```python
class BatchExecutor:
    """Executes batch operations with optimization."""

    def __init__(
        self,
        client: Any,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[int] = None,
        retry_attempts: int = 3,
    ):
        """Initialize batch executor.

        Args:
            client: Zenoo RPC client instance
            max_chunk_size: Maximum records per chunk
            max_concurrency: Maximum concurrent operations
            timeout: Operation timeout in seconds
            retry_attempts: Number of retry attempts for failed operations
        """
```

**Features:**

- Automatic operation chunking
- Parallel execution with concurrency control
- Progress tracking and monitoring
- Error handling and partial results
- Performance optimization

## Context Managers

### `batch_context()`

Standalone batch context manager.

```python
from zenoo_rpc.batch.context import batch_context

async with batch_context(
    client,
    max_chunk_size=100,
    max_concurrency=5
) as batch:
    """Convenient batch context without manager."""
    batch.create("res.partner", [{"name": "Test"}])
    batch.update("res.partner", {"active": False}, record_ids=[1, 2])
    # Auto-execute on context exit
```

### `batch_operation()`

Context manager for single operation type accumulation.

```python
from zenoo_rpc.batch.context import batch_operation

async with batch_operation(
    client,
    model="res.partner",
    operation_type="create",
    chunk_size=50
) as collector:
    """Accumulate operations of single type."""
    collector.add({"name": "Test Company 1"})
    collector.add({"name": "Test Company 2"})
    # Records are automatically created when context exits
```

## Performance Optimization

### Chunking Strategy

```python
# Automatic chunking for large datasets
large_dataset = [{"name": f"Company {i}"} for i in range(1000)]

# Automatically split into chunks of 100
created_ids = await batch_manager.bulk_create(
    model="res.partner",
    records=large_dataset,
    chunk_size=100
)

print(f"Created {len(created_ids)} records in chunks")
```

### Concurrency Control

```python
# Configure optimal concurrency
batch_manager = BatchManager(
    client=client,
    max_chunk_size=50,     # Smaller chunks for better parallelism
    max_concurrency=10,    # Higher concurrency for speed
    timeout=120            # Longer timeout for large operations
)

# Execute with progress tracking
async def progress_callback(progress):
    print(f"Progress: {progress['percentage']:.1f}%")

results = await batch_manager.execute_operations(
    operations,
    progress_callback=progress_callback
)
```

## Summary

The Batch API provides comprehensive tools for efficient bulk operations:

### Key Components

- **BatchManager**: Main interface for batch operations
- **Batch Operations**: CreateOperation, UpdateOperation, DeleteOperation
- **BatchExecutor**: Performance-optimized execution engine
- **Context Managers**: Convenient batch contexts for different use cases

### Usage Patterns

1. **Bulk Operations**: Use `bulk_create()`, `bulk_update()`, `bulk_delete()` for simple bulk operations
2. **Batch Context**: Use `batch_manager.batch()` for collecting multiple operations
3. **Manual Batches**: Use `create_batch()` for fine-grained control
4. **Standalone Context**: Use `batch_context()` for independent batch operations

### Best Practices

- Configure appropriate chunk sizes for your data volume
- Use concurrency control to balance speed and resource usage
- Implement progress tracking for long-running operations
- Handle errors gracefully with proper exception handling
- Monitor performance and adjust settings as needed

The Batch API makes it easy to perform efficient bulk operations while maintaining excellent performance and reliability.

## Performance Optimization

### Chunking Strategy

```python
# Automatic chunking for large datasets
large_dataset = [{"name": f"Company {i}"} for i in range(1000)]

# Automatically split into chunks of 100
created_ids = await batch_manager.bulk_create(
    model="res.partner",
    records=large_dataset,
    chunk_size=100
)

print(f"Created {len(created_ids)} records in chunks")
```

### Concurrency Control

```python
# High-performance batch manager
batch_manager = BatchManager(
    client=client,
    max_chunk_size=200,    # Larger chunks
    max_concurrency=20,    # More concurrent operations
    timeout=600           # Longer timeout
)

# Use bulk operations for high-performance processing
created_ids = await batch_manager.bulk_create(
    model="res.partner",
    records=very_large_dataset,
    chunk_size=200
)

print(f"Created {len(created_ids)} records with high concurrency")
```

### Progress Monitoring

```python
async def progress_callback(progress):
    """Progress callback for monitoring."""
    print(f"Progress: {progress['percentage']:.1f}% "
          f"({progress['completed']}/{progress['total']})")
    print(f"Stats: {progress['stats']['completed_operations']} completed, "
          f"{progress['stats']['failed_operations']} failed")

# Use with progress monitoring
results = await batch_manager.execute_operations(
    operations,
    progress_callback=progress_callback
)
```

## Error Handling

### Batch Exceptions

```python
from zenoo_rpc.batch.exceptions import (
    BatchError,
    BatchExecutionError,
    BatchValidationError
)

try:
    # Use batch context correctly
    async with batch_manager.batch() as batch_context:
        await batch_context.create("res.partner", invalid_data)

except BatchExecutionError as e:
    print(f"Batch execution failed: {e}")
    # Handle batch execution errors

except BatchValidationError as e:
    print(f"Batch validation failed: {e}")
    # Handle validation errors

except BatchError as e:
    print(f"General batch error: {e}")
    # Handle general batch errors
```

### Partial Results

```python
async def safe_batch_operation():
    """Handle partial results in batch operations."""
    try:
        # Use bulk operations directly for better error handling
        results = await batch_manager.bulk_create(
            model="res.partner",
            records=mixed_valid_invalid_data
        )

        return results

    except BatchExecutionError as e:
        print(f"Batch execution failed: {e}")
        # Handle batch execution errors
        # Check if any operations succeeded before the failure

        raise

async def safe_batch_with_validation():
    """Pre-validate data before batch operations."""
    valid_records = []
    invalid_records = []

    for record in mixed_data:
        if record.get('name'):  # Basic validation
            valid_records.append(record)
        else:
            invalid_records.append(record)

    if invalid_records:
        print(f"Skipping {len(invalid_records)} invalid records")

    if valid_records:
        results = await batch_manager.bulk_create(
            model="res.partner",
            records=valid_records
        )
        return results

    return []
```

## Integration with Transactions

### Transactional Batch Operations

```python
from zenoo_rpc.transaction.manager import TransactionManager

# Setup both managers
await client.setup_transaction_manager()
await client.setup_batch_manager()

# Use transaction with batch operations
async with client.transaction() as tx:
    # Create records
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=partner_data
    )

    # Update records
    await batch_manager.bulk_update(
        model="res.partner",
        data={"active": True},
        record_ids=created_ids
    )

    # All operations commit together if no errors
    # Transaction automatically rolls back on any exception
```

## Best Practices

### 1. Use Appropriate Chunk Sizes

```python
# ✅ Good: Appropriate chunk size for data volume
small_dataset = [...]  # < 50 records
await batch_manager.bulk_create("res.partner", small_dataset, chunk_size=25)

large_dataset = [...]  # > 1000 records  
await batch_manager.bulk_create("res.partner", large_dataset, chunk_size=200)
```

### 2. Handle Large Datasets

```python
# ✅ Good: Process very large datasets in batches
async def process_large_dataset(data, batch_size=1000):
    """Process large dataset in manageable batches."""
    for i in range(0, len(data), batch_size):
        batch_data = data[i:i + batch_size]

        # Use bulk operations directly for large datasets
        created_ids = await batch_manager.bulk_create(
            model="res.partner",
            records=batch_data,
            chunk_size=100  # Internal chunking
        )

        print(f"Processed batch {i//batch_size + 1}: {len(created_ids)} records")
```

### 3. Use Progress Monitoring

```python
# ✅ Good: Monitor progress for long-running operations
def create_progress_callback(description):
    async def callback(progress):
        print(f"{description}: {progress['percentage']:.1f}% complete "
              f"({progress['completed']}/{progress['total']})")
    return callback

results = await batch_manager.execute_operations(
    operations,
    progress_callback=create_progress_callback("Creating partners")
)
```

### 4. Validate Data Before Batch Operations

```python
# ✅ Good: Validate data before batch processing
def validate_partner_data(records):
    """Validate partner data before batch creation."""
    valid_records = []
    invalid_records = []
    
    for record in records:
        if not record.get("name"):
            invalid_records.append(record)
        elif not record.get("email") or "@" not in record["email"]:
            invalid_records.append(record)
        else:
            valid_records.append(record)
    
    return valid_records, invalid_records

# Usage
valid_data, invalid_data = validate_partner_data(raw_data)

if invalid_data:
    print(f"Skipping {len(invalid_data)} invalid records")

if valid_data:
    # Use bulk operations for validated data
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=valid_data
    )
```

## Next Steps

- Learn about [Batch Operations](operations.md) in detail
- Explore [Batch Executor](executor.md) optimization
- Check [Batch Context](context.md) management
- Understand [Performance Tuning](performance.md) strategies
