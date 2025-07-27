# Transaction Management Guide

Zenoo RPC provides comprehensive transaction management to ensure data consistency and integrity in your Odoo operations. This guide covers everything from basic transactions to advanced patterns like savepoints and distributed transactions.

## Overview

Transaction management in Zenoo RPC provides:

- **ACID Compliance** - Atomicity, Consistency, Isolation, Durability
- **Automatic Rollback** - Rollback on exceptions
- **Savepoints** - Nested transaction support
- **Context Managers** - Clean, Pythonic transaction handling
- **Deadlock Detection** - Automatic deadlock resolution
- **Performance Optimization** - Batch operations within transactions

## Basic Transaction Usage

### Simple Transactions

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def basic_transaction_example():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Setup transaction manager first
        from zenoo_rpc.transaction.manager import TransactionManager
        transaction_manager = TransactionManager(client)

        # Basic transaction with automatic commit/rollback
        async with transaction_manager.transaction() as tx:
            # Create a company
            company_id = await client.create(
                "res.partner",
                {
                    "name": "Acme Corporation",
                    "is_company": True,
                    "email": "contact@acme.com"
                }
            )

            # Create a contact for the company
            contact_id = await client.create(
                "res.partner",
                {
                    "name": "John Doe",
                    "parent_id": company_id,
                    "email": "john@acme.com",
                    "function": "CEO"
                }
            )

            # Both records are created atomically
            # Automatic commit on successful exit
            print(f"Created company ID: {company_id}")
            print(f"Created contact ID: {contact_id}")

asyncio.run(basic_transaction_example())
```

### Transaction with Error Handling

```python
async def transaction_with_error_handling():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction() as tx:
                # Create company
                company = await client.model(ResPartner).create({
                    "name": "Test Company",
                    "is_company": True
                })
                
                # This might fail due to validation
                contact = await client.model(ResPartner).create({
                    "name": "",  # Empty name will cause validation error
                    "parent_id": company.id
                })
                
        except ValidationError as e:
            print(f"Transaction rolled back due to validation error: {e}")
            # Company creation is automatically rolled back
        
        except Exception as e:
            print(f"Transaction rolled back due to error: {e}")
```

## Advanced Transaction Patterns

### Manual Transaction Control

```python
async def manual_transaction_control():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Start transaction manually
        tx = await client.begin_transaction()
        
        try:
            # Perform operations
            partner = await client.model(ResPartner).create({
                "name": "Manual Transaction Partner",
                "is_company": True
            })
            
            # Manual commit
            await tx.commit()
            print("Transaction committed successfully")
            
        except Exception as e:
            # Manual rollback
            await tx.rollback()
            print(f"Transaction rolled back: {e}")
```

### Savepoints (Nested Transactions)

```python
async def savepoint_example():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Main transaction operations
            company = await client.model(ResPartner).create({
                "name": "Main Company",
                "is_company": True
            })
            
            # Create savepoint for risky operations
            savepoint = await tx.savepoint("contact_creation")
            
            try:
                # Risky operation that might fail
                contact = await client.model(ResPartner).create({
                    "name": "Risky Contact",
                    "parent_id": company.id,
                    "email": "invalid-email"  # This might fail validation
                })
                
                # Release savepoint if successful
                await savepoint.release()
                print("Contact created successfully")
                
            except ValidationError as e:
                # Rollback to savepoint, keep main transaction
                await savepoint.rollback()
                print(f"Contact creation failed, rolled back to savepoint: {e}")
                
                # Create a valid contact instead
                contact = await client.model(ResPartner).create({
                    "name": "Valid Contact",
                    "parent_id": company.id,
                    "email": "valid@email.com"
                })
            
            # Main transaction continues and commits
            print(f"Company {company.name} created with contact")
```

### Multiple Savepoints

```python
async def multiple_savepoints():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Create base company
            company = await client.model(ResPartner).create({
                "name": "Multi-Savepoint Company",
                "is_company": True
            })
            
            # Savepoint 1: Create contacts
            sp1 = await tx.savepoint("contacts")
            
            try:
                contacts = []
                for i in range(3):
                    contact = await client.model(ResPartner).create({
                        "name": f"Contact {i+1}",
                        "parent_id": company.id,
                        "email": f"contact{i+1}@company.com"
                    })
                    contacts.append(contact)
                
                await sp1.release()
                print("All contacts created successfully")
                
            except Exception as e:
                await sp1.rollback()
                print(f"Contact creation failed: {e}")
            
            # Savepoint 2: Create addresses
            sp2 = await tx.savepoint("addresses")
            
            try:
                # Create additional address
                address = await client.model(ResPartner).create({
                    "name": "Shipping Address",
                    "parent_id": company.id,
                    "type": "delivery",
                    "street": "123 Shipping St"
                })
                
                await sp2.release()
                print("Address created successfully")
                
            except Exception as e:
                await sp2.rollback()
                print(f"Address creation failed: {e}")
            
            # Main transaction commits with whatever succeeded
```

## Transaction Isolation Levels

### Setting Isolation Levels

```python
async def isolation_levels():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Read Committed (default)
        async with client.transaction(isolation="read_committed") as tx:
            # Standard isolation level
            partners = await client.model(ResPartner).all()
        
        # Repeatable Read
        async with client.transaction(isolation="repeatable_read") as tx:
            # Consistent reads within transaction
            partners1 = await client.model(ResPartner).all()
            # ... other operations ...
            partners2 = await client.model(ResPartner).all()
            # partners1 and partners2 will be identical
        
        # Serializable (highest isolation)
        async with client.transaction(isolation="serializable") as tx:
            # Full transaction isolation
            # May cause more deadlocks but ensures consistency
            critical_operation = await perform_critical_operation(client)
```

## Batch Operations in Transactions

### Efficient Bulk Operations

```python
async def batch_operations_in_transaction():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Prepare bulk data
            companies_data = []
            for i in range(100):
                companies_data.append({
                    "name": f"Bulk Company {i:03d}",
                    "is_company": True,
                    "email": f"company{i:03d}@example.com"
                })
            
            # Bulk create within transaction
            companies = await client.model(ResPartner).bulk_create(companies_data)
            
            # Create contacts for each company
            contacts_data = []
            for company in companies:
                contacts_data.append({
                    "name": f"Contact for {company.name}",
                    "parent_id": company.id,
                    "email": f"contact@{company.name.lower().replace(' ', '')}.com"
                })
            
            contacts = await client.model(ResPartner).bulk_create(contacts_data)
            
            print(f"Created {len(companies)} companies and {len(contacts)} contacts")
            # All operations committed atomically
```

### Conditional Batch Operations

```python
async def conditional_batch_operations():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Get existing partners
            existing_partners = await client.model(ResPartner).filter(
                email__isnull=False
            ).all()
            
            # Prepare updates based on conditions
            updates = []
            for partner in existing_partners:
                if "@gmail.com" in partner.email:
                    updates.append({
                        "id": partner.id,
                        "category_id": [(4, gmail_category_id)]  # Add category
                    })
                elif "@company.com" in partner.email:
                    updates.append({
                        "id": partner.id,
                        "is_company": True
                    })
            
            # Bulk update within transaction
            if updates:
                updated_partners = await client.model(ResPartner).bulk_update(updates)
                print(f"Updated {len(updated_partners)} partners")
```

## Transaction Performance Optimization

### Connection Pooling in Transactions

```python
async def optimized_transaction_performance():
    async with ZenooClient("localhost", port=8069) as client:
        # Configure for high-performance transactions
        await client.configure_transaction_pool(
            max_connections=20,      # Maximum concurrent transactions
            timeout=300,             # Transaction timeout (5 minutes)
            retry_attempts=3,        # Retry on deadlock
            deadlock_timeout=30      # Deadlock detection timeout
        )
        
        await client.login("demo", "admin", "admin")
        
        # Use optimized transaction
        async with client.transaction(
            timeout=60,              # Custom timeout for this transaction
            retry_on_deadlock=True   # Automatic retry on deadlock
        ) as tx:
            # High-performance operations
            result = await perform_complex_operations(client)
```

### Concurrent Transactions

```python
async def concurrent_transactions():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async def create_company_with_contacts(company_name: str):
            async with client.transaction() as tx:
                company = await client.model(ResPartner).create({
                    "name": company_name,
                    "is_company": True
                })
                
                # Create contacts
                contacts = await client.model(ResPartner).bulk_create([
                    {
                        "name": f"Contact 1 for {company_name}",
                        "parent_id": company.id
                    },
                    {
                        "name": f"Contact 2 for {company_name}",
                        "parent_id": company.id
                    }
                ])
                
                return company, contacts
        
        # Run multiple transactions concurrently
        tasks = [
            create_company_with_contacts(f"Concurrent Company {i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        print(f"Created {len(results)} companies concurrently")
```

## Error Handling and Recovery

### Deadlock Handling

```python
async def deadlock_handling():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async def update_partner_with_retry(partner_id: int, data: dict):
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    async with client.transaction() as tx:
                        partner = await client.model(ResPartner).update(
                            partner_id, data
                        )
                        return partner
                        
                except DeadlockError as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise
                    
                    # Exponential backoff
                    wait_time = 2 ** retry_count
                    await asyncio.sleep(wait_time)
                    print(f"Deadlock detected, retrying in {wait_time}s...")
        
        # Usage
        partner = await update_partner_with_retry(1, {"name": "Updated Name"})
```

### Transaction Timeout Handling

```python
async def timeout_handling():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction(timeout=30) as tx:  # 30 second timeout
                # Long-running operation
                result = await perform_long_operation(client)
                
        except TransactionTimeoutError as e:
            print(f"Transaction timed out: {e}")
            # Handle timeout - maybe retry with smaller batch
            
        except Exception as e:
            print(f"Transaction failed: {e}")
```

## Monitoring and Debugging

### Transaction Monitoring

```python
async def transaction_monitoring():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Enable transaction monitoring
        await client.enable_transaction_monitoring()
        
        async with client.transaction() as tx:
            # Get transaction info
            tx_info = await tx.get_info()
            print(f"Transaction ID: {tx_info['id']}")
            print(f"Start time: {tx_info['start_time']}")
            print(f"Isolation level: {tx_info['isolation_level']}")
            
            # Perform operations
            partner = await client.model(ResPartner).create({
                "name": "Monitored Partner"
            })
            
            # Get transaction statistics
            stats = await tx.get_stats()
            print(f"Operations performed: {stats['operations']}")
            print(f"Records affected: {stats['records_affected']}")
            print(f"Duration: {stats['duration']:.3f}s")
```

### Transaction Logging

```python
import logging

async def transaction_logging():
    # Configure transaction logging
    logging.basicConfig(level=logging.INFO)
    tx_logger = logging.getLogger('zenoo_rpc.transaction')
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Enable detailed transaction logging
        await client.enable_transaction_logging(
            log_level=logging.DEBUG,
            log_operations=True,
            log_performance=True
        )
        
        async with client.transaction() as tx:
            # Operations will be logged automatically
            partner = await client.model(ResPartner).create({
                "name": "Logged Partner"
            })
```

## Best Practices

### Do's ✅

1. **Use context managers** for automatic cleanup
2. **Keep transactions short** to avoid locks
3. **Use savepoints** for complex operations
4. **Handle deadlocks** with retry logic
5. **Monitor transaction performance**
6. **Use appropriate isolation levels**
7. **Batch related operations** in single transactions

### Don'ts ❌

1. **Don't keep transactions open** for long periods
2. **Don't ignore transaction errors**
3. **Don't nest transactions** without savepoints
4. **Don't perform I/O operations** inside transactions
5. **Don't use transactions** for read-only operations
6. **Don't forget to handle timeouts**
7. **Don't mix transaction and non-transaction operations**

## Configuration Examples

### Development Configuration

```python
# Simple transaction configuration for development
async with client.transaction() as tx:
    # Basic operations
    pass
```

### Production Configuration

```python
# Production-ready transaction configuration
await client.configure_transaction_pool(
    max_connections=50,
    timeout=300,
    retry_attempts=3,
    deadlock_timeout=30,
    enable_monitoring=True
)

async with client.transaction(
    isolation="repeatable_read",
    timeout=60,
    retry_on_deadlock=True
) as tx:
    # Production operations
    pass
```

Transaction management is crucial for maintaining data integrity in your Odoo applications. Use these patterns and best practices to ensure your data operations are reliable and consistent.

## Next Steps

- [Batch Operations](batch-operations.md) - Optimize bulk operations
- [Error Handling](error-handling.md) - Handle errors gracefully
- [Performance Optimization](../tutorials/performance-optimization.md) - Optimize performance
- [Testing Strategies](../tutorials/testing.md) - Test your transactions
