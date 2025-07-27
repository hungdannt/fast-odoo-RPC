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
    """Manages batch operations for a Zenoo RPC client."""
    
    def __init__(
        self,
        client: ZenooClient,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[float] = 300
    ):
        """Initialize batch manager."""
        self.client = client
        self.max_chunk_size = max_chunk_size
        self.max_concurrency = max_concurrency
        self.timeout = timeout
```

**Parameters:**

- `client` (ZenooClient): Zenoo RPC client instance
- `max_chunk_size` (int): Maximum records per chunk (default: 100)
- `max_concurrency` (int): Maximum concurrent operations (default: 5)
- `timeout` (float, optional): Operation timeout in seconds (default: 300)

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
    # Operations are collected and executed automatically
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=[
            {"name": "Company A", "email": "a@company.com"},
            {"name": "Company B", "email": "b@company.com"}
        ]
    )
    
    # Update operations
    await batch_manager.bulk_write(
        model="res.partner",
        updates=[
            {"id": created_ids[0], "data": {"phone": "+1-555-0001"}},
            {"id": created_ids[1], "data": {"phone": "+1-555-0002"}}
        ]
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

async with batch_manager.batch() as batch_context:
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=partners_data,
        chunk_size=50
    )
    
    print(f"Created {len(created_ids)} partners")
    for i, partner_id in enumerate(created_ids):
        print(f"Partner {i+1}: ID {partner_id}")
```

#### `async bulk_write(model, updates, chunk_size=None, context=None)`

Update multiple records efficiently.

**Parameters:**

- `model` (str): Odoo model name
- `updates` (List[Dict[str, Any]]): List of update operations
  - Format: `[{"id": record_id, "data": update_data}, ...]`
  - Or: `[{"ids": [id1, id2], "data": update_data}, ...]`
- `chunk_size` (int, optional): Override default chunk size
- `context` (Dict[str, Any], optional): Execution context

**Returns:** `bool` - True if all updates successful

**Example:**

```python
# Individual record updates
updates = [
    {"id": 1, "data": {"active": True, "customer_rank": 1}},
    {"id": 2, "data": {"active": True, "customer_rank": 2}},
    {"id": 3, "data": {"active": False, "customer_rank": 0}}
]

async with batch_manager.batch() as batch_context:
    success = await batch_manager.bulk_write(
        model="res.partner",
        updates=updates
    )

# Bulk update with same data
bulk_updates = [
    {
        "ids": [1, 2, 3, 4, 5],
        "data": {"active": True, "customer_rank": 1}
    }
]

async with batch_manager.batch() as batch_context:
    success = await batch_manager.bulk_write(
        model="res.partner",
        updates=bulk_updates
    )
```

#### `async bulk_unlink(model, record_ids, chunk_size=None, context=None)`

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

async with batch_manager.batch() as batch_context:
    success = await batch_manager.bulk_unlink(
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

batch.delete("res.partner", [4, 5, 6])

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
def progress_callback(completed, total, operation):
    print(f"Progress: {completed}/{total} - {operation.model}")

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
    context: Optional[Dict[str, Any]] = None
    priority: int = 0
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
print(f"Can split: {operation.can_split()}")        # True

# Split into chunks
chunks = operation.split(chunk_size=1)
print(f"Split into {len(chunks)} chunks")
```

### UpdateOperation

Batch update operation for multiple record updates.

```python
@dataclass
class UpdateOperation(BatchOperation):
    """Batch update operation."""
    
    model: str
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    record_ids: Optional[List[int]] = None
    context: Optional[Dict[str, Any]] = None
    priority: int = 0
```

**Example:**

```python
from zenoo_rpc.batch.operations import UpdateOperation

# Same data for multiple records
operation1 = UpdateOperation(
    model="res.partner",
    data={"active": True},
    record_ids=[1, 2, 3, 4, 5]
)

# Different data for each record
operation2 = UpdateOperation(
    model="res.partner",
    data=[
        {"id": 1, "name": "Updated Name 1"},
        {"id": 2, "name": "Updated Name 2"}
    ]
)
```

### DeleteOperation

Batch delete operation for multiple record deletion.

```python
@dataclass
class DeleteOperation(BatchOperation):
    """Batch delete operation."""
    
    model: str
    data: List[int]  # Record IDs to delete
    context: Optional[Dict[str, Any]] = None
    priority: int = 0
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
        client: ZenooClient,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[float] = None
    ):
        """Initialize batch executor."""
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

Decorator for batch operations.

```python
from zenoo_rpc.batch.context import batch_operation

@batch_operation(client, auto_execute=True)
async def create_test_data(batch):
    """Batch operation decorator."""
    batch.create("res.partner", [
        {"name": "Test Company 1"},
        {"name": "Test Company 2"}
    ])
    
    batch.create("res.users", [
        {"name": "Test User", "login": "test@user.com"}
    ])

# Usage
await create_test_data()
```

## Performance Optimization

### Chunking Strategy

```python
# Automatic chunking for large datasets
large_dataset = [{"name": f"Company {i}"} for i in range(1000)]

async with batch_manager.batch() as batch_context:
    # Automatically split into chunks of 100
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=large_dataset,
        chunk_size=100  # Process in chunks of 100
    )
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

async with batch_manager.batch() as batch_context:
    # Operations execute with controlled concurrency
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=very_large_dataset
    )
```

### Progress Monitoring

```python
def progress_callback(completed, total, current_operation):
    """Progress callback for monitoring."""
    percentage = (completed / total) * 100
    print(f"Progress: {percentage:.1f}% ({completed}/{total})")
    print(f"Current: {current_operation.operation_type.value} on {current_operation.model}")

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
    async with batch_manager.batch() as batch_context:
        await batch_manager.bulk_create("res.partner", invalid_data)
        
except BatchExecutionError as e:
    print(f"Batch execution failed: {e}")
    print(f"Failed operations: {len(e.failed_operations)}")
    
    for failed_op in e.failed_operations:
        print(f"Failed: {failed_op}")
        
except BatchValidationError as e:
    print(f"Batch validation failed: {e}")
```

### Partial Results

```python
async def safe_batch_operation():
    """Handle partial results in batch operations."""
    try:
        async with batch_manager.batch() as batch_context:
            results = await batch_manager.bulk_create(
                model="res.partner",
                records=mixed_valid_invalid_data
            )
            
            return results
            
    except BatchExecutionError as e:
        # Some operations may have succeeded
        if e.partial_results:
            print(f"Partial success: {len(e.partial_results)} operations completed")
            return e.partial_results
        
        raise
```

## Integration with Transactions

### Transactional Batch Operations

```python
from zenoo_rpc.transaction.manager import TransactionManager

transaction_manager = TransactionManager(client)

async with transaction_manager.transaction() as tx:
    async with batch_manager.batch() as batch_context:
        # All batch operations are transactional
        created_ids = await batch_manager.bulk_create(
            model="res.partner",
            records=partner_data
        )
        
        await batch_manager.bulk_write(
            model="res.partner",
            updates=[
                {"id": created_ids[0], "data": {"active": True}}
            ]
        )
        
        # All operations commit together
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
        
        async with batch_manager.batch() as batch_context:
            created_ids = await batch_manager.bulk_create(
                model="res.partner",
                records=batch_data
            )
            
        print(f"Processed batch {i//batch_size + 1}: {len(created_ids)} records")
```

### 3. Use Progress Monitoring

```python
# ✅ Good: Monitor progress for long-running operations
def create_progress_callback(description):
    def callback(completed, total, operation):
        percentage = (completed / total) * 100
        print(f"{description}: {percentage:.1f}% complete")
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
    async with batch_manager.batch() as batch_context:
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
