# Transaction Context API Reference

Advanced transaction context management with decorators, context managers, savepoints, and metadata handling for complex transaction workflows.

## Overview

Transaction context provides:

- **Context Managers**: Convenient transaction handling with automatic cleanup
- **Decorators**: Function-level transaction management (@atomic)
- **Savepoints**: Nested transaction support with rollback points
- **Metadata**: Context data storage and retrieval
- **Manual Control**: Explicit transaction lifecycle management

## Context Managers

### `transaction()`

Standalone async context manager for transaction handling.

```python
async def transaction(
    client: Any,
    transaction_id: Optional[str] = None,
    auto_commit: bool = True,
    auto_rollback: bool = True,
) -> Transaction:
    """Async context manager for transaction handling."""
```

**Parameters:**

- `client` (Any): Zenoo RPC client instance
- `transaction_id` (Optional[str]): Optional transaction identifier
- `auto_commit` (bool): Whether to auto-commit on success (default: True)
- `auto_rollback` (bool): Whether to auto-rollback on exception (default: True)

**Returns:** `Transaction` - Transaction instance

**Example:**

```python
from zenoo_rpc.transaction.context import transaction

async def create_partner_with_contacts():
    async with transaction(client) as tx:
        # Create company
        company = await client.create("res.partner", {
            "name": "ACME Corp",
            "is_company": True
        })
        
        # Create contacts
        contact1 = await client.create("res.partner", {
            "name": "John Doe",
            "parent_id": company["id"],
            "email": "john@acme.com"
        })
        
        contact2 = await client.create("res.partner", {
            "name": "Jane Smith", 
            "parent_id": company["id"],
            "email": "jane@acme.com"
        })
        
        # Auto-commit on success
        return company, [contact1, contact2]

# Usage
company, contacts = await create_partner_with_contacts()
```

### Transaction with Manual Control

```python
async def manual_transaction_control():
    async with transaction(client, auto_commit=False) as tx:
        try:
            # Create records
            partner = await client.create("res.partner", {"name": "Test"})
            
            # Validate business logic
            if not validate_partner(partner):
                await tx.rollback()
                return None
            
            # Manual commit
            await tx.commit()
            return partner
            
        except Exception as e:
            # Manual rollback on error
            await tx.rollback()
            raise
```

## Decorators

### `@atomic`

Decorator for atomic transaction execution, similar to Django's @transaction.atomic.

```python
def atomic(
    client: Optional[Any] = None, 
    auto_commit: bool = True, 
    auto_rollback: bool = True
) -> Union[Callable[[F], F], Any]:
    """Decorator for atomic transaction execution."""
```

**Parameters:**

- `client` (Optional[Any]): Client instance (can be passed at decoration or runtime)
- `auto_commit` (bool): Whether to auto-commit on success (default: True)
- `auto_rollback` (bool): Whether to auto-rollback on exception (default: True)

**Returns:** Decorated function or decorator

### Basic @atomic Usage

```python
from zenoo_rpc.transaction.context import atomic

@atomic
async def create_partner_with_contacts(client, company_data, contacts_data):
    """Create company with contacts atomically."""
    # This entire function runs in a transaction
    company = await client.create("res.partner", {
        **company_data,
        "is_company": True
    })
    
    # Create all contacts
    contacts = []
    for contact_data in contacts_data:
        contact = await client.create("res.partner", {
            **contact_data,
            "parent_id": company["id"]
        })
        contacts.append(contact)
    
    return company, contacts

# Usage - client is automatically detected from first argument
company, contacts = await create_partner_with_contacts(
    client,
    {"name": "ACME Corp", "email": "info@acme.com"},
    [
        {"name": "John Doe", "email": "john@acme.com"},
        {"name": "Jane Smith", "email": "jane@acme.com"}
    ]
)
```

### @atomic with Explicit Client

```python
# Pre-configure client at decoration time
@atomic(client=client, auto_commit=True)
async def update_partner_hierarchy(parent_id, updates):
    """Update partner hierarchy atomically."""
    # Update parent
    await client.write("res.partner", [parent_id], updates["parent"])
    
    # Update all children
    children = await client.search("res.partner", [("parent_id", "=", parent_id)])
    for child_id in children:
        await client.write("res.partner", [child_id], updates["children"])

# Usage - no need to pass client
await update_partner_hierarchy(123, {
    "parent": {"phone": "+1-555-0100"},
    "children": {"mobile": "+1-555-0101"}
})
```

### @atomic with Transaction Access

```python
@atomic
async def complex_business_operation(client, data):
    """Complex operation with transaction access."""
    # Access transaction through _transaction parameter
    def inner_function(_transaction=None):
        if _transaction:
            # Set transaction context
            _transaction.set_context("operation_type", "complex_business")
            _transaction.set_context("user_id", data.get("user_id"))
    
    # Transaction is automatically injected
    inner_function(_transaction=kwargs.get("_transaction"))
    
    # Perform operations
    result = await client.create("res.partner", data)
    return result
```

## TransactionContext Class

Manual transaction control with explicit lifecycle management.

### Constructor

```python
class TransactionContext:
    """Context manager for manual transaction control."""
    
    def __init__(self, client: Any):
        """Initialize transaction context."""
        self.client = client
        self.transaction: Optional[Transaction] = None
```

**Parameters:**

- `client` (Any): Zenoo RPC client instance

### Methods

#### `async begin(transaction_id=None, auto_commit=False)`

Begin a new transaction with manual control.

**Parameters:**

- `transaction_id` (Optional[str]): Optional transaction identifier
- `auto_commit` (bool): Whether to auto-commit (default: False for manual control)

**Returns:** `Transaction` - Transaction instance

**Example:**

```python
from zenoo_rpc.transaction.context import TransactionContext

async def manual_transaction_example():
    ctx = TransactionContext(client)
    
    async with ctx.begin() as tx:
        # Manual transaction control
        partner = await client.create("res.partner", {"name": "Test"})
        
        # Set transaction context
        tx.set_context("created_by", "api_user")
        tx.set_context("operation_id", "12345")
        
        # Conditional logic
        if validate_partner_data(partner):
            await tx.commit()
            print("Partner created successfully")
        else:
            await tx.rollback()
            print("Partner creation rolled back")
        
        return partner
```

#### `get_current_transaction()`

Get the current active transaction.

**Returns:** `Optional[Transaction]` - Current transaction or None

**Example:**

```python
ctx = TransactionContext(client)

async with ctx.begin() as tx:
    # Get current transaction
    current_tx = ctx.get_current_transaction()
    assert current_tx == tx
    
    # Use transaction
    await current_tx.create("res.partner", {"name": "Test"})
```

## SavepointContext Class

Context manager for savepoint handling within transactions.

### Constructor

```python
class SavepointContext:
    """Context manager for savepoint handling."""
    
    def __init__(self, transaction: Transaction, savepoint_name: Optional[str] = None):
        """Initialize savepoint context."""
        self.transaction = transaction
        self.savepoint_name = savepoint_name
```

**Parameters:**

- `transaction` (Transaction): Transaction instance
- `savepoint_name` (Optional[str]): Optional savepoint name

### Usage Examples

#### Basic Savepoint Usage

```python
from zenoo_rpc.transaction.context import transaction, SavepointContext

async def create_with_savepoints():
    async with transaction(client) as tx:
        # Create main company
        company = await client.create("res.partner", {
            "name": "ACME Corp",
            "is_company": True
        })
        
        # Create contacts with savepoint protection
        async with SavepointContext(tx, "contacts") as sp:
            try:
                contact1 = await client.create("res.partner", {
                    "name": "John Doe",
                    "parent_id": company["id"],
                    "email": "john@acme.com"
                })
                
                contact2 = await client.create("res.partner", {
                    "name": "Jane Smith",
                    "parent_id": company["id"],
                    "email": "jane@acme.com"
                })
                
                # Validate contacts
                if not validate_contacts([contact1, contact2]):
                    await sp.rollback()  # Only rollback contacts
                    print("Contacts rolled back, company preserved")
                
            except Exception as e:
                # Automatic rollback to savepoint on exception
                print(f"Error creating contacts: {e}")
                # Company creation is still valid
        
        return company
```

#### Nested Savepoints

```python
async def nested_savepoints_example():
    async with transaction(client) as tx:
        # Level 0: Main transaction
        company = await client.create("res.partner", {
            "name": "ACME Corp",
            "is_company": True
        })
        
        # Level 1: Contacts savepoint
        async with SavepointContext(tx, "contacts") as contacts_sp:
            contact1 = await client.create("res.partner", {
                "name": "John Doe",
                "parent_id": company["id"]
            })
            
            # Level 2: Contact details savepoint
            async with SavepointContext(tx, "contact_details") as details_sp:
                try:
                    # Add email
                    await client.write("res.partner", [contact1["id"]], {
                        "email": "john@acme.com"
                    })
                    
                    # Add phone (might fail validation)
                    await client.write("res.partner", [contact1["id"]], {
                        "phone": "invalid-phone"
                    })
                    
                except Exception:
                    # Rollback only contact details
                    await details_sp.rollback()
                    print("Contact details rolled back")
            
            # Contact still exists, just without details
            contact2 = await client.create("res.partner", {
                "name": "Jane Smith",
                "parent_id": company["id"]
            })
        
        return company
```

#### Manual Savepoint Control

```python
async def manual_savepoint_control():
    async with transaction(client) as tx:
        company = await client.create("res.partner", {"name": "ACME Corp"})
        
        async with SavepointContext(tx, "batch_operations") as sp:
            success_count = 0
            
            for i in range(10):
                try:
                    contact = await client.create("res.partner", {
                        "name": f"Contact {i}",
                        "parent_id": company["id"]
                    })
                    success_count += 1
                    
                except Exception as e:
                    print(f"Failed to create contact {i}: {e}")
                    
                    if success_count < 5:
                        # If less than 5 successful, rollback all
                        await sp.rollback()
                        print("Rolled back all contacts due to low success rate")
                        break
            
            print(f"Created {success_count} contacts successfully")
```

## Context Data Management

### Setting and Getting Context

```python
async def context_management_example():
    async with transaction(client) as tx:
        # Set context data
        tx.set_context("user_id", 123)
        tx.set_context("operation_source", "api")
        tx.set_context("request_id", "req-12345")
        tx.set_context("metadata", {
            "ip_address": "192.168.1.100",
            "user_agent": "ZenooRPC/1.0"
        })
        
        # Get specific context
        user_id = tx.get_context("user_id")
        source = tx.get_context("operation_source")
        
        # Get context with default
        priority = tx.get_context("priority", "normal")
        
        # Get all context
        all_context = tx.get_context()
        
        print(f"User ID: {user_id}")
        print(f"Source: {source}")
        print(f"Priority: {priority}")
        print(f"All context: {all_context}")
        
        # Use context in operations
        partner = await client.create("res.partner", {
            "name": f"Partner created by user {user_id}",
            "ref": f"API-{tx.get_context('request_id')}"
        })
```

### Context Inheritance

```python
async def context_inheritance_example():
    async with transaction(client) as parent_tx:
        # Set parent context
        parent_tx.set_context("company_id", 1)
        parent_tx.set_context("department", "sales")
        
        # Nested transaction inherits context
        async with SavepointContext(parent_tx, "nested") as sp:
            # Access parent context
            company_id = parent_tx.get_context("company_id")
            department = parent_tx.get_context("department")
            
            # Add nested context
            parent_tx.set_context("operation", "bulk_create")
            
            # Create records with inherited context
            for i in range(5):
                await client.create("res.partner", {
                    "name": f"Partner {i}",
                    "company_id": company_id,
                    "category_id": [(6, 0, [1])]  # Sales category
                })
```

## Advanced Patterns

### Transaction Middleware

```python
class TransactionMiddleware:
    """Middleware for transaction processing."""
    
    def __init__(self, client):
        self.client = client
    
    @atomic
    async def process_with_audit(self, operation_func, audit_data):
        """Process operation with audit trail."""
        # Set audit context
        tx = kwargs.get("_transaction")
        if tx:
            tx.set_context("audit_user", audit_data["user_id"])
            tx.set_context("audit_timestamp", time.time())
            tx.set_context("audit_operation", audit_data["operation"])
        
        try:
            # Execute operation
            result = await operation_func()
            
            # Log success
            await self.client.create("audit.log", {
                "operation": audit_data["operation"],
                "user_id": audit_data["user_id"],
                "status": "success",
                "details": str(result)
            })
            
            return result
            
        except Exception as e:
            # Log failure
            await self.client.create("audit.log", {
                "operation": audit_data["operation"],
                "user_id": audit_data["user_id"],
                "status": "error",
                "error_message": str(e)
            })
            raise

# Usage
middleware = TransactionMiddleware(client)

async def create_partner():
    return await client.create("res.partner", {"name": "Test"})

result = await middleware.process_with_audit(
    create_partner,
    {"user_id": 123, "operation": "create_partner"}
)
```

### Conditional Transaction Handling

```python
async def conditional_transaction_example(use_transaction: bool = True):
    """Example of conditional transaction usage."""
    
    if use_transaction:
        async with transaction(client) as tx:
            return await _perform_operations(tx)
    else:
        # Direct operations without transaction
        return await _perform_operations(None)

async def _perform_operations(tx=None):
    """Perform operations with optional transaction context."""
    if tx:
        # Set transaction context
        tx.set_context("batch_mode", True)
    
    # Create records
    partners = []
    for i in range(5):
        partner = await client.create("res.partner", {
            "name": f"Partner {i}",
            "ref": f"BATCH-{i}"
        })
        partners.append(partner)
    
    return partners

# Usage
# With transaction (atomic)
partners_atomic = await conditional_transaction_example(use_transaction=True)

# Without transaction (individual commits)
partners_individual = await conditional_transaction_example(use_transaction=False)
```

## Error Handling

### Transaction Error Recovery

```python
from zenoo_rpc.transaction.exceptions import TransactionError

async def error_recovery_example():
    """Example of transaction error recovery."""
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with transaction(client) as tx:
                # Set retry context
                tx.set_context("retry_attempt", retry_count + 1)
                
                # Perform operations
                result = await risky_operation()
                
                # Success - break retry loop
                return result
                
        except TransactionError as e:
            retry_count += 1
            print(f"Transaction failed (attempt {retry_count}): {e}")
            
            if retry_count >= max_retries:
                print("Max retries exceeded")
                raise
            
            # Wait before retry
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
    
    raise TransactionError("Failed after all retries")

async def risky_operation():
    """Simulate a risky operation that might fail."""
    import random
    
    if random.random() < 0.7:  # 70% chance of failure
        raise TransactionError("Simulated operation failure")
    
    return await client.create("res.partner", {"name": "Success"})
```

### Savepoint Error Handling

```python
async def savepoint_error_handling():
    """Example of savepoint error handling."""
    
    async with transaction(client) as tx:
        company = await client.create("res.partner", {"name": "ACME Corp"})
        
        # Try to create contacts with error recovery
        contacts_created = 0
        
        for i in range(10):
            async with SavepointContext(tx, f"contact_{i}") as sp:
                try:
                    contact = await client.create("res.partner", {
                        "name": f"Contact {i}",
                        "parent_id": company["id"],
                        "email": f"contact{i}@acme.com"
                    })
                    contacts_created += 1
                    
                except Exception as e:
                    print(f"Failed to create contact {i}: {e}")
                    # Automatic rollback to savepoint
                    # Continue with next contact
        
        print(f"Successfully created {contacts_created}/10 contacts")
        return company
```

## Best Practices

### 1. Use Appropriate Context Managers

```python
# ✅ Good: Use @atomic for simple functions
@atomic
async def simple_operation(client, data):
    return await client.create("res.partner", data)

# ✅ Good: Use transaction() for complex logic
async def complex_operation():
    async with transaction(client) as tx:
        # Complex logic with conditional commits
        if condition:
            await tx.commit()
        else:
            await tx.rollback()

# ✅ Good: Use TransactionContext for manual control
async def manual_operation():
    ctx = TransactionContext(client)
    async with ctx.begin(auto_commit=False) as tx:
        # Full manual control
        await tx.commit()
```

### 2. Use Savepoints for Partial Rollbacks

```python
# ✅ Good: Use savepoints for independent operations
async with transaction(client) as tx:
    main_record = await client.create("res.partner", main_data)
    
    async with SavepointContext(tx, "optional_data") as sp:
        try:
            await client.create("res.partner.category", optional_data)
        except Exception:
            # Only optional data is rolled back
            pass
```

### 3. Set Meaningful Context

```python
# ✅ Good: Set meaningful context data
async with transaction(client) as tx:
    tx.set_context("user_id", current_user.id)
    tx.set_context("operation_type", "bulk_import")
    tx.set_context("source_file", filename)
    
    # Context can be used for auditing, debugging, etc.
```

## Next Steps

- Learn about [Transaction Manager](../manager.md) for advanced transaction management
- Explore [Transaction Performance](../../performance/transactions.md) for optimization
- Check [Error Handling](../../troubleshooting/transactions.md) for common issues
