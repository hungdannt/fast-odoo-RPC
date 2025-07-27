# Transaction API Reference

The transaction module provides explicit transaction control with async context managers, supporting commit/rollback operations, nested transactions, and ACID compliance.

## Overview

The transaction system consists of:

- **TransactionManager**: Main interface for transaction management
- **Transaction**: Individual transaction with operation tracking
- **Context Managers**: Convenient transaction contexts
- **ACID Compliance**: Atomicity, Consistency, Isolation, Durability
- **Rollback Support**: Automatic rollback with operation reversal

## TransactionManager

Main transaction management interface coordinating transaction lifecycle.

### Constructor

```python
class TransactionManager:
    """Manages transactions for a Zenoo RPC client."""
    
    def __init__(self, client: ZenooClient):
        """Initialize the transaction manager."""
        self.client = client
        self.active_transactions: Dict[str, Transaction] = {}
        self.current_transaction: Optional[Transaction] = None
```

**Example:**

```python
from zenoo_rpc.transaction.manager import TransactionManager

# Setup transaction manager
transaction_manager = TransactionManager(client)

# Or attach to client
client.transaction_manager = TransactionManager(client)
```

### Transaction Context

#### `async transaction(transaction_id=None, auto_commit=True)`

Create a new transaction context with automatic management.

**Parameters:**

- `transaction_id` (str, optional): Unique transaction identifier
- `auto_commit` (bool): Whether to auto-commit on success (default: True)

**Returns:** `AsyncContextManager[Transaction]` - Transaction context

**Example:**

```python
# Basic transaction
async with transaction_manager.transaction() as tx:
    partner_id = await client.create("res.partner", {
        "name": "Test Company",
        "email": "test@company.com"
    })
    await client.write("res.partner", [partner_id], {
        "phone": "+1-555-0123"
    })
    # Auto-commit on success

# Custom transaction ID
async with transaction_manager.transaction(
    transaction_id="custom-tx-001"
) as tx:
    # Operations here
    pass

# Manual commit control
async with transaction_manager.transaction(auto_commit=False) as tx:
    # Operations here
    if some_condition:
        await tx.commit()
    else:
        await tx.rollback()
```

### Statistics

#### `successful_transactions`

Number of successfully committed transactions.

**Type:** `int`

#### `failed_transactions`

Number of failed/rolled back transactions.

**Type:** `int`

**Example:**

```python
print(f"Success rate: {transaction_manager.successful_transactions}")
print(f"Failed transactions: {transaction_manager.failed_transactions}")
```

## Transaction

Individual transaction with operation tracking and lifecycle management.

### Properties

#### `id`

Unique transaction identifier.

**Type:** `str`

#### `state`

Current transaction state.

**Type:** `TransactionState` (ACTIVE, COMMITTED, ROLLED_BACK)

#### `is_active`

Check if transaction is active.

**Type:** `bool`

#### `is_nested`

Check if this is a nested transaction.

**Type:** `bool`

#### `operations`

List of operations performed in this transaction.

**Type:** `List[OperationRecord]`

**Example:**

```python
async with transaction_manager.transaction() as tx:
    print(f"Transaction ID: {tx.id}")
    print(f"Is active: {tx.is_active}")
    
    await client.create("res.partner", {"name": "Test"})
    
    print(f"Operations count: {len(tx.operations)}")
    for op in tx.operations:
        print(f"Operation: {op.operation_type} on {op.model}")
```

### Operation Tracking

#### `add_operation(operation_type, model, record_ids=None, **kwargs)`

Track an operation for potential rollback.

**Parameters:**

- `operation_type` (str): Type of operation ("create", "write", "unlink")
- `model` (str): Odoo model name
- `record_ids` (List[int], optional): Affected record IDs
- `original_data` (Dict, optional): Original data before operation
- `created_ids` (List[int], optional): IDs of created records
- `data` (Dict, optional): Operation data
- `idempotency_key` (str, optional): Idempotency key
- `operation_context` (Dict, optional): Operation context
- `rollback_data` (Dict, optional): Specific rollback data

**Example:**

```python
# Usually called automatically by client operations
async with transaction_manager.transaction() as tx:
    # This automatically calls tx.add_operation()
    partner_id = await client.create("res.partner", {"name": "Test"})
    
    # Manual operation tracking (advanced usage)
    tx.add_operation(
        operation_type="custom",
        model="res.partner",
        record_ids=[partner_id],
        data={"custom_field": "value"}
    )
```

### Context Management

#### `set_context(key, value)`

Set context data for the transaction.

**Parameters:**

- `key` (str): Context key
- `value` (Any): Context value

#### `get_context(key=None, default=None)`

Get context data from the transaction.

**Parameters:**

- `key` (str, optional): Context key (returns all if None)
- `default` (Any): Default value if key not found

**Returns:** `Any` - Context value or all context

**Example:**

```python
async with transaction_manager.transaction() as tx:
    # Set context
    tx.set_context("user_id", 123)
    tx.set_context("operation_source", "api")
    
    # Get context
    user_id = tx.get_context("user_id")
    all_context = tx.get_context()
    
    print(f"User ID: {user_id}")
    print(f"All context: {all_context}")
```

### Transaction Control

#### `async commit()`

Commit the transaction and all its operations.

**Returns:** `None`

**Raises:**
- `TransactionCommitError`: If commit fails
- `TransactionStateError`: If transaction not in valid state

**Example:**

```python
async with transaction_manager.transaction(auto_commit=False) as tx:
    partner_id = await client.create("res.partner", {"name": "Test"})
    
    # Manual commit
    try:
        await tx.commit()
        print("Transaction committed successfully")
    except TransactionCommitError as e:
        print(f"Commit failed: {e}")
```

#### `async rollback()`

Rollback the transaction and reverse all operations.

**Returns:** `None`

**Raises:**
- `TransactionRollbackError`: If rollback fails

**Example:**

```python
async with transaction_manager.transaction(auto_commit=False) as tx:
    try:
        partner_id = await client.create("res.partner", {"name": "Test"})
        
        # Some condition that requires rollback
        if some_error_condition:
            await tx.rollback()
            return
        
        await tx.commit()
        
    except Exception as e:
        # Automatic rollback on exception
        await tx.rollback()
        raise
```

### Savepoints

#### `async create_savepoint(name=None)`

Create a savepoint for partial rollback.

**Parameters:**

- `name` (str, optional): Savepoint name (auto-generated if None)

**Returns:** `Savepoint` - Savepoint object

#### `async rollback_to_savepoint(savepoint)`

Rollback to a specific savepoint.

**Parameters:**

- `savepoint` (Savepoint): Savepoint to rollback to

**Example:**

```python
async with transaction_manager.transaction() as tx:
    # Create initial data
    partner_id = await client.create("res.partner", {"name": "Test"})
    
    # Create savepoint
    sp1 = await tx.create_savepoint("after_partner_creation")
    
    try:
        # Risky operations
        await client.write("res.partner", [partner_id], {"email": "invalid"})
        
    except ValidationError:
        # Rollback to savepoint
        await tx.rollback_to_savepoint(sp1)
        print("Rolled back to savepoint")
    
    # Continue with transaction
    await client.write("res.partner", [partner_id], {"phone": "+1-555-0123"})
```

## Context Managers

### `transaction()`

Standalone transaction context manager.

```python
from zenoo_rpc.transaction.context import transaction

async with transaction(client) as tx:
    """Convenient transaction context without manager."""
    partner_id = await client.create("res.partner", {"name": "Test"})
    # Auto-commit on success
```

### `atomic()`

Decorator for atomic operations.

```python
from zenoo_rpc.transaction.context import atomic

@atomic(client)
async def create_partner_with_contacts(partner_data, contacts_data):
    """Atomic operation decorator."""
    partner_id = await client.create("res.partner", partner_data)
    
    for contact_data in contacts_data:
        contact_data["parent_id"] = partner_id
        await client.create("res.partner", contact_data)
    
    return partner_id

# Usage
partner_id = await create_partner_with_contacts(
    {"name": "ACME Corp", "is_company": True},
    [
        {"name": "John Doe", "email": "john@acme.com"},
        {"name": "Jane Smith", "email": "jane@acme.com"}
    ]
)
```

## Nested Transactions

### Nested Transaction Support

```python
async with transaction_manager.transaction() as outer_tx:
    # Outer transaction
    company_id = await client.create("res.partner", {
        "name": "Parent Company",
        "is_company": True
    })
    
    # Nested transaction
    async with transaction_manager.transaction() as inner_tx:
        contact_id = await client.create("res.partner", {
            "name": "Contact Person",
            "parent_id": company_id,
            "is_company": False
        })
        
        # Inner transaction can be rolled back independently
        if some_condition:
            await inner_tx.rollback()
        # Otherwise commits with outer transaction
    
    # Outer transaction continues
    await client.write("res.partner", [company_id], {
        "website": "https://company.com"
    })
```

## ACID Compliance

### Atomicity

All operations in a transaction are committed or rolled back together.

```python
async with transaction_manager.transaction() as tx:
    try:
        # Multiple operations - all or nothing
        partner_id = await client.create("res.partner", partner_data)
        order_id = await client.create("sale.order", order_data)
        line_id = await client.create("sale.order.line", line_data)
        
        # All operations committed together
        
    except Exception:
        # All operations rolled back together
        raise
```

### Consistency

Transaction ensures data consistency through validation.

```python
async with transaction_manager.transaction() as tx:
    # Validation ensures consistency
    partner_id = await client.create("res.partner", {
        "name": "Test Company",
        "email": "test@company.com",  # Must be valid email
        "is_company": True
    })
    
    # Related data maintains consistency
    order_id = await client.create("sale.order", {
        "partner_id": partner_id,  # Must reference existing partner
        "state": "draft"
    })
```

### Isolation

Transactions are isolated from concurrent operations.

```python
# Transaction A
async with transaction_manager.transaction() as tx_a:
    partner = await client.read("res.partner", [1], ["name"])[0]
    # Other transactions don't see uncommitted changes
    await client.write("res.partner", [1], {"name": "Updated Name"})

# Transaction B (concurrent)
async with transaction_manager.transaction() as tx_b:
    # Sees original data until tx_a commits
    partner = await client.read("res.partner", [1], ["name"])[0]
```

### Durability

Committed transactions are permanently stored.

```python
async with transaction_manager.transaction() as tx:
    partner_id = await client.create("res.partner", partner_data)
    # Once committed, data is durable
    
# Data persists across client restarts
```

## Error Handling

### Transaction Exceptions

```python
from zenoo_rpc.transaction.exceptions import (
    TransactionError,
    TransactionRollbackError,
    TransactionCommitError,
    TransactionStateError
)

try:
    async with transaction_manager.transaction() as tx:
        # Operations that might fail
        await client.create("res.partner", invalid_data)
        
except TransactionRollbackError as e:
    print(f"Rollback failed: {e}")
    print(f"Failed operations: {e.get_failed_operation_summary()}")
    
except TransactionCommitError as e:
    print(f"Commit failed: {e}")
    
except TransactionStateError as e:
    print(f"Invalid transaction state: {e}")
```

### Graceful Error Handling

```python
async def safe_transaction_operation():
    """Safe transaction with comprehensive error handling."""
    try:
        async with transaction_manager.transaction() as tx:
            # Set context for debugging
            tx.set_context("operation", "partner_creation")
            tx.set_context("user_id", current_user_id)
            
            # Perform operations
            partner_id = await client.create("res.partner", partner_data)
            
            # Validate result
            if not partner_id:
                raise ValueError("Partner creation failed")
            
            return partner_id
            
    except ValidationError as e:
        logger.error(f"Validation error in transaction: {e}")
        raise
        
    except TransactionError as e:
        logger.error(f"Transaction error: {e}")
        # Could implement retry logic here
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in transaction: {e}")
        raise
```

## Performance Considerations

### Transaction Scope

Keep transactions as small as possible for better performance.

```python
# ✅ Good: Small transaction scope
async with transaction_manager.transaction() as tx:
    partner_id = await client.create("res.partner", partner_data)
    await client.write("res.partner", [partner_id], updates)

# ❌ Avoid: Large transaction scope
async with transaction_manager.transaction() as tx:
    # Too many operations in single transaction
    for i in range(1000):
        await client.create("res.partner", data[i])
```

### Batch Operations in Transactions

```python
# ✅ Good: Use batch operations within transactions
async with transaction_manager.transaction() as tx:
    from zenoo_rpc.batch.manager import BatchManager
    
    batch_manager = BatchManager(client)
    async with batch_manager.batch():
        created_ids = await batch_manager.bulk_create(
            model="res.partner",
            records=partner_data_list
        )
```

### Cache Integration

Transactions automatically handle cache invalidation.

```python
async with transaction_manager.transaction() as tx:
    # Cache is automatically invalidated on commit
    partner_id = await client.create("res.partner", partner_data)
    
    # Cached queries are invalidated
    partners = await client.model(ResPartner).cache(ttl=300).all()
```

## Best Practices

### 1. Use Context Managers

Always use context managers for automatic cleanup.

```python
# ✅ Good
async with transaction_manager.transaction() as tx:
    # Operations here

# ❌ Avoid manual management
tx = Transaction(client)
try:
    # Operations
    await tx.commit()
except:
    await tx.rollback()
```

### 2. Handle Specific Exceptions

Handle specific transaction exceptions appropriately.

```python
try:
    async with transaction_manager.transaction() as tx:
        # Operations
        pass
except TransactionRollbackError as e:
    # Handle rollback failure
    logger.error(f"Rollback failed: {e}")
except ValidationError as e:
    # Handle validation errors
    logger.warning(f"Validation failed: {e}")
```

### 3. Use Savepoints for Complex Logic

Use savepoints for partial rollback in complex operations.

```python
async with transaction_manager.transaction() as tx:
    # Safe operations
    partner_id = await client.create("res.partner", partner_data)
    
    sp = await tx.create_savepoint("before_risky_operation")
    
    try:
        # Risky operations
        await risky_operation()
    except Exception:
        await tx.rollback_to_savepoint(sp)
        # Continue with safe fallback
```

## Next Steps

- Learn about [Transaction Context](context.md) managers
- Explore [Transaction Exceptions](exceptions.md) handling
- Check [ACID Compliance](acid.md) implementation details
- Understand [Nested Transactions](nested.md) patterns
