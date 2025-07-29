# Batch Operations API Reference

Comprehensive batch operation types with chunking, validation, error handling, and performance optimization for efficient bulk data processing in Zenoo RPC.

## Overview

Batch operations provide:

- **Operation Types**: CreateOperation, UpdateOperation, DeleteOperation
- **Chunking**: Automatic splitting for large datasets
- **Validation**: Data validation and error prevention
- **Status Tracking**: Operation lifecycle monitoring
- **Performance**: Optimized execution with concurrency control

## BatchOperation Base Class

Abstract base class for all batch operations with common functionality.

### Constructor

```python
@dataclass
class BatchOperation(ABC):
    """Abstract base class for batch operations."""
    
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
```

**Parameters:**

- `model` (str): Odoo model name (e.g., "res.partner")
- `data` (Union[List[Dict], List[int], Dict]): Operation data
- `operation_type` (OperationType): Type of operation (CREATE, UPDATE, DELETE)
- `operation_id` (str): Unique operation identifier (auto-generated)
- `status` (OperationStatus): Current operation status
- `priority` (int): Operation priority (higher = more priority)
- `context` (Optional[Dict]): Odoo context for operation

### Abstract Methods

#### `validate()`

Validate operation data before execution.

**Raises:** `BatchValidationError` - If validation fails

#### `get_batch_size()`

Get the number of records in this operation.

**Returns:** `int` - Number of records

#### `split(chunk_size)`

Split operation into smaller chunks.

**Parameters:**

- `chunk_size` (int): Maximum size per chunk

**Returns:** `List[BatchOperation]` - List of chunked operations

### Common Methods

#### `get_duration()`

Get operation execution duration.

**Returns:** `Optional[float]` - Duration in seconds or None if not completed

**Example:**

```python
operation = CreateOperation(
    model="res.partner",
    data=[{"name": "Company A"}, {"name": "Company B"}]
)

# Check duration after execution
if operation.completed_at and operation.started_at:
    duration = operation.completed_at - operation.started_at
    print(f"Operation took {duration:.2f} seconds")
```

## CreateOperation

Batch create operation for multiple record creation with optimized performance.

### Constructor

```python
@dataclass
class CreateOperation(BatchOperation):
    """Batch create operation."""
    
    return_ids: bool = True
    operation_type: OperationType = field(default=OperationType.CREATE, init=False)
```

**Additional Parameters:**

- `return_ids` (bool): Whether to return created record IDs (default: True)

**Features:**

- Bulk record creation
- Automatic ID return
- Data validation
- Chunking support

### Usage Examples

#### Basic Create Operation

```python
from zenoo_rpc.batch.operations import CreateOperation

# Create multiple partners
operation = CreateOperation(
    model="res.partner",
    data=[
        {"name": "ACME Corp", "is_company": True, "email": "info@acme.com"},
        {"name": "Global Tech", "is_company": True, "email": "contact@global.com"},
        {"name": "Local Business", "is_company": True, "phone": "+1-555-0100"}
    ],
    context={"active_test": False},
    priority=1
)

# Validate before execution
operation.validate()

print(f"Will create {operation.get_batch_size()} records")
print(f"Operation ID: {operation.operation_id}")
```

#### Large Dataset with Chunking

```python
# Large dataset - will be automatically chunked
large_dataset = [
    {"name": f"Company {i}", "is_company": True}
    for i in range(1000)
]

operation = CreateOperation(
    model="res.partner",
    data=large_dataset
)

# Split into chunks of 100
chunks = operation.split(chunk_size=100)
print(f"Split into {len(chunks)} chunks")

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {chunk.get_batch_size()} records")
```

#### Create with Context

```python
# Create with specific context
operation = CreateOperation(
    model="res.partner",
    data=[
        {"name": "Test Company", "country_id": 1},
        {"name": "Demo Company", "country_id": 2}
    ],
    context={
        "lang": "en_US",
        "tz": "UTC",
        "active_test": False,
        "tracking_disable": True  # Disable mail tracking
    }
)
```

### Validation Rules

```python
# CreateOperation validation checks:
# 1. Model is required and non-empty
# 2. Data must be a list of dictionaries
# 3. Data cannot be empty
# 4. Each record must be a non-empty dictionary

try:
    operation = CreateOperation(
        model="res.partner",
        data=[
            {"name": "Valid Company"},
            {},  # Invalid: empty dictionary
            {"name": "Another Company"}
        ]
    )
    operation.validate()
except BatchValidationError as e:
    print(f"Validation failed: {e}")
```

## UpdateOperation

Batch update operation supporting both uniform and individual record updates.

### Constructor

```python
@dataclass
class UpdateOperation(BatchOperation):
    """Batch update operation."""
    
    record_ids: Optional[List[int]] = None
    operation_type: OperationType = field(default=OperationType.UPDATE, init=False)
```

**Additional Parameters:**

- `record_ids` (Optional[List[int]]): Record IDs for uniform updates

**Features:**

- Uniform updates (same data for multiple records)
- Individual updates (different data per record)
- Flexible data formats
- Efficient chunking

### Usage Examples

#### Uniform Update (Same Data for Multiple Records)

```python
from zenoo_rpc.batch.operations import UpdateOperation

# Update multiple records with same data
operation = UpdateOperation(
    model="res.partner",
    data={"active": False, "customer_rank": 0},
    record_ids=[1, 2, 3, 4, 5],
    context={"active_test": False}
)

print(f"Will update {len(operation.record_ids)} records")
```

#### Individual Updates (Different Data per Record)

```python
# Update each record with different data
operation = UpdateOperation(
    model="res.partner",
    data=[
        {"id": 1, "name": "Updated Company 1", "email": "new1@example.com"},
        {"id": 2, "name": "Updated Company 2", "email": "new2@example.com"},
        {"id": 3, "name": "Updated Company 3", "phone": "+1-555-0200"}
    ]
)

print(f"Will update {operation.get_batch_size()} records individually")
```

#### Bulk Status Update

```python
# Bulk activate partners
activate_operation = UpdateOperation(
    model="res.partner",
    data={"active": True},
    record_ids=list(range(100, 200)),  # IDs 100-199
    priority=2
)

# Bulk deactivate with context
deactivate_operation = UpdateOperation(
    model="res.partner", 
    data={"active": False, "customer_rank": 0},
    record_ids=[201, 202, 203],
    context={"mail_notrack": True}  # Disable mail notifications
)
```

### Chunking Strategies

```python
# Large uniform update
large_update = UpdateOperation(
    model="res.partner",
    data={"category_id": [(6, 0, [1, 2])]},  # Add categories
    record_ids=list(range(1, 1001))  # 1000 records
)

# Split into chunks of 50
chunks = large_update.split(chunk_size=50)
print(f"Uniform update split into {len(chunks)} chunks")

# Large individual updates
individual_updates = UpdateOperation(
    model="res.partner",
    data=[
        {"id": i, "ref": f"REF-{i:04d}"}
        for i in range(1, 501)  # 500 individual updates
    ]
)

# Split into chunks of 25
chunks = individual_updates.split(chunk_size=25)
print(f"Individual updates split into {len(chunks)} chunks")
```

### Validation Rules

```python
# UpdateOperation validation checks:
# 1. Model is required
# 2. For uniform updates: data must be dict, record_ids required
# 3. For individual updates: data must be list of dicts with 'id' field
# 4. Cannot have both record_ids and list data

try:
    # Invalid: missing 'id' in individual update
    operation = UpdateOperation(
        model="res.partner",
        data=[
            {"name": "Missing ID"}  # Invalid: no 'id' field
        ]
    )
    operation.validate()
except BatchValidationError as e:
    print(f"Validation failed: {e}")
```

## DeleteOperation

Batch delete operation for efficient multiple record deletion.

### Constructor

```python
@dataclass
class DeleteOperation(BatchOperation):
    """Batch delete operation."""
    
    operation_type: OperationType = field(default=OperationType.DELETE, init=False)
```

**Features:**

- Bulk record deletion
- ID validation
- Safe chunking
- Error handling

### Usage Examples

#### Basic Delete Operation

```python
from zenoo_rpc.batch.operations import DeleteOperation

# Delete multiple records
operation = DeleteOperation(
    model="res.partner",
    data=[1, 2, 3, 4, 5],  # Record IDs to delete
    context={"active_test": False}
)

print(f"Will delete {operation.get_batch_size()} records")
```

#### Large Scale Deletion

```python
# Delete many records (will be chunked automatically)
large_deletion = DeleteOperation(
    model="res.partner",
    data=list(range(1000, 2000)),  # Delete IDs 1000-1999
    priority=3
)

# Split into safe chunks
chunks = large_deletion.split(chunk_size=50)
print(f"Large deletion split into {len(chunks)} chunks")

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: Delete {chunk.get_batch_size()} records")
```

#### Conditional Deletion with Context

```python
# Delete with specific context
operation = DeleteOperation(
    model="res.partner",
    data=[101, 102, 103],
    context={
        "active_test": False,  # Include inactive records
        "force_delete": True   # Force deletion even with dependencies
    }
)
```

### Validation Rules

```python
# DeleteOperation validation checks:
# 1. Model is required
# 2. Data must be a list of integers (record IDs)
# 3. Data cannot be empty
# 4. All IDs must be positive integers

try:
    operation = DeleteOperation(
        model="res.partner",
        data=[1, 2, "invalid", 4]  # Invalid: string in ID list
    )
    operation.validate()
except BatchValidationError as e:
    print(f"Validation failed: {e}")
```

## Operation Factory

Factory function for creating batch operations dynamically.

### `create_batch_operation()`

```python
def create_batch_operation(
    operation_type: str, 
    model: str, 
    data: Any, 
    **kwargs
) -> BatchOperation:
    """Factory function to create batch operations."""
```

**Parameters:**

- `operation_type` (str): Type of operation ("create", "update", "delete")
- `model` (str): Odoo model name
- `data` (Any): Operation data
- `**kwargs`: Additional operation parameters

**Returns:** `BatchOperation` - Appropriate operation instance

**Example:**

```python
from zenoo_rpc.batch.operations import create_batch_operation

# Create operations dynamically
operations = []

# Create operation
create_op = create_batch_operation(
    "create",
    "res.partner",
    [{"name": "Dynamic Company"}],
    priority=1
)
operations.append(create_op)

# Update operation
update_op = create_batch_operation(
    "update",
    "res.partner",
    {"active": True},
    record_ids=[1, 2, 3]
)
operations.append(update_op)

# Delete operation
delete_op = create_batch_operation(
    "delete",
    "res.partner",
    [4, 5, 6]
)
operations.append(delete_op)

print(f"Created {len(operations)} operations")
```

## Operation Status and Lifecycle

### OperationStatus Enum

```python
class OperationStatus(Enum):
    """Batch operation status."""
    
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Status Tracking

```python
# Track operation lifecycle
operation = CreateOperation(
    model="res.partner",
    data=[{"name": "Test Company"}]
)

print(f"Initial status: {operation.status}")  # PENDING

# During execution (handled by BatchExecutor)
operation.status = OperationStatus.EXECUTING
operation.started_at = time.time()

# After completion
operation.status = OperationStatus.COMPLETED
operation.completed_at = time.time()
operation.result = [123]  # Created record ID

# Check results
if operation.status == OperationStatus.COMPLETED:
    if operation.completed_at and operation.started_at:
        duration = operation.completed_at - operation.started_at
        print(f"Operation completed in {duration:.2f} seconds")
    print(f"Created record ID: {operation.result[0]}")
```

## Advanced Patterns

### Priority-Based Operations

```python
# Create operations with different priorities
high_priority = CreateOperation(
    model="res.partner",
    data=[{"name": "Critical Customer"}],
    priority=10  # High priority
)

normal_priority = CreateOperation(
    model="res.partner",
    data=[{"name": "Regular Customer"}],
    priority=5   # Normal priority
)

low_priority = CreateOperation(
    model="res.partner",
    data=[{"name": "Bulk Import"}],
    priority=1   # Low priority
)

# Sort by priority for execution
operations = [normal_priority, high_priority, low_priority]
operations.sort(key=lambda op: op.priority, reverse=True)

print("Execution order:")
for i, op in enumerate(operations):
    print(f"{i+1}. Priority {op.priority}: {op.data[0]['name']}")
```

### Operation Chaining

```python
# Chain related operations
def create_company_with_contacts(company_data, contacts_data):
    """Create company and related contacts."""
    operations = []
    
    # 1. Create company (high priority)
    company_op = CreateOperation(
        model="res.partner",
        data=[{**company_data, "is_company": True}],
        priority=10
    )
    operations.append(company_op)
    
    # 2. Create contacts (normal priority, will get company_id after company creation)
    contacts_op = CreateOperation(
        model="res.partner",
        data=contacts_data,
        priority=5
    )
    operations.append(contacts_op)
    
    return operations

# Usage
company_data = {"name": "ACME Corp", "email": "info@acme.com"}
contacts_data = [
    {"name": "John Doe", "email": "john@acme.com"},
    {"name": "Jane Smith", "email": "jane@acme.com"}
]

operations = create_company_with_contacts(company_data, contacts_data)
```

### Error Recovery Operations

```python
# Create compensating operations for error recovery
def create_with_rollback(model, data):
    """Create operation with rollback capability."""
    
    create_op = CreateOperation(
        model=model,
        data=data,
        priority=5
    )
    
    # Prepare rollback operation (will be used if needed)
    rollback_op = DeleteOperation(
        model=model,
        data=[],  # Will be populated with created IDs
        priority=10  # High priority for cleanup
    )
    
    return create_op, rollback_op

# Usage
create_op, rollback_op = create_with_rollback(
    "res.partner",
    [{"name": "Test Company"}]
)

# After execution, if rollback needed:
if create_op.status == OperationStatus.COMPLETED and need_rollback:
    rollback_op.data = create_op.result  # Use created IDs
    # Execute rollback_op
```

## Best Practices

### 1. Choose Appropriate Chunk Sizes

```python
# ✅ Good: Reasonable chunk sizes based on data size
small_records = CreateOperation(
    model="res.partner.category",
    data=[{"name": f"Category {i}"} for i in range(1000)],
)
chunks = small_records.split(chunk_size=100)  # Small records, larger chunks

large_records = CreateOperation(
    model="res.partner",
    data=[{
        "name": f"Company {i}",
        "comment": "Large description " * 100  # Large data per record
    } for i in range(100)]
)
chunks = large_records.split(chunk_size=10)   # Large records, smaller chunks
```

### 2. Use Appropriate Operation Types

```python
# ✅ Good: Use uniform updates when possible
uniform_update = UpdateOperation(
    model="res.partner",
    data={"active": True},
    record_ids=[1, 2, 3, 4, 5]  # More efficient
)

# ❌ Avoid: Individual updates when uniform would work
individual_update = UpdateOperation(
    model="res.partner",
    data=[
        {"id": 1, "active": True},
        {"id": 2, "active": True},
        {"id": 3, "active": True}  # Less efficient for same data
    ]
)
```

### 3. Set Meaningful Priorities

```python
# ✅ Good: Logical priority assignment
critical_data = CreateOperation(
    model="res.partner",
    data=critical_customers,
    priority=10  # Critical business data
)

regular_data = CreateOperation(
    model="res.partner", 
    data=regular_customers,
    priority=5   # Normal priority
)

bulk_import = CreateOperation(
    model="res.partner",
    data=bulk_customers,
    priority=1   # Low priority background task
)
```

### 4. Validate Before Execution

```python
# ✅ Good: Always validate operations
operations = [create_op, update_op, delete_op]

for operation in operations:
    try:
        operation.validate()
    except BatchValidationError as e:
        print(f"Operation {operation.operation_id} validation failed: {e}")
        # Handle validation error
```

## Next Steps

- Learn about [Batch Manager](../manager.md) for operation execution
- Explore [Batch Executor](../executor.md) for performance optimization
- Check [Batch Performance](../../performance/batching.md) for tuning guidelines
