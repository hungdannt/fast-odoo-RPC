# Batch Context

The batch context provides a convenient way to manage batch operations with automatic execution and cleanup.

## Overview

The `BatchContext` class offers:
- Automatic batch execution on context exit
- Transaction-like behavior
- Error handling and rollback
- Resource management

## Class Reference

### BatchContext

```python
class BatchContext:
    """Context for collecting batch operations."""

    def __init__(self, manager: BatchManager):
        """Initialize batch context.

        Args:
            manager: Batch manager instance
        """
        self.manager = manager
        self.operations = []
        self._stats = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
        }

    async def create(
        self,
        model: str,
        data: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ):
        """Add create operation to batch.

        Args:
            model: Odoo model name
            data: List of record data
            context: Optional context
        """
        pass

    async def write_many(
        self,
        model: str,
        updates: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ):
        """Add write operations to batch.

        Args:
            model: Odoo model name
            updates: List of update operations
            context: Optional context
        """
        pass

    async def unlink(
        self,
        model: str,
        record_ids: List[int],
        context: Optional[Dict[str, Any]] = None,
    ):
        """Add unlink operation to batch.

        Args:
            model: Odoo model name
            record_ids: List of record IDs to delete
            context: Optional context
        """
        """Add delete operation to batch."""
        pass
    
    async def execute(self) -> List[Any]:
        """Execute all batched operations."""
        pass
```

## Usage Examples

### Basic Batch Context

```python
async def basic_batch_context():
    """Demonstrate basic batch context usage."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup batch manager
        await client.setup_batch_manager()

        # Operations are automatically executed on context exit
        async with client.batch() as batch:
            # Add operations (note: create expects list of records)
            await batch.create("res.partner", [
                {"name": "Partner 1", "email": "p1@example.com"},
                {"name": "Partner 2", "email": "p2@example.com"}
            ])
            await batch.create("product.product", [
                {"name": "Product 1", "list_price": 10.0}
            ])

        # Operations are executed here automatically
        print("Batch operations completed")

async def standalone_batch_context():
    """Demonstrate standalone batch context usage."""

    from zenoo_rpc.batch.context import batch_context

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Use standalone batch context
        async with batch_context(client, max_chunk_size=100) as batch:
            batch.create("res.partner", [
                {"name": "Standalone Partner 1"},
                {"name": "Standalone Partner 2"}
            ])
            batch.update("res.partner", {"active": False}, record_ids=[1, 2, 3])

            # Batch is automatically executed when context exits

        print("Standalone batch operations completed")
```

### Error Handling

```python
async def batch_with_error_handling():
    """Demonstrate error handling in batch context."""

    from zenoo_rpc.batch.exceptions import BatchError

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        await client.setup_batch_manager()

        try:
            async with client.batch() as batch:
                # Valid operations
                await batch.create("res.partner", [
                    {"name": "Valid Partner 1"},
                    {"name": "Valid Partner 2"}
                ])

                # This might fail due to validation
                await batch.create("res.partner", [
                    {"name": ""},  # Invalid - empty name
                ])

        except BatchError as e:
            print(f"Batch failed: {e}")
            # Handle batch execution errors

        except Exception as e:
            print(f"Unexpected error: {e}")

async def batch_with_transaction():
    """Demonstrate batch with transaction support."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup both transaction and batch managers
        await client.setup_transaction_manager()
        await client.setup_batch_manager()

        try:
            # Use transaction for rollback capability
            async with client.transaction() as tx:
                async with client.batch() as batch:
                    await batch.create("res.partner", [
                        {"name": "Transactional Partner 1"},
                        {"name": "Transactional Partner 2"}
                    ])

                    # If any operation fails, transaction will rollback
                    await batch.write_many("res.partner", [
                        {"id": 1, "values": {"active": False}},
                        {"id": 2, "values": {"active": False}}
                    ])

                # Transaction commits automatically if no errors
                print("Batch operations committed successfully")

        except Exception as e:
            print(f"Transaction rolled back due to error: {e}")
```

### Advanced Context Features

```python
async def batch_with_progress_tracking():
    """Demonstrate batch operations with progress tracking."""

    from zenoo_rpc.batch.context import batch_context

    async def progress_callback(progress):
        """Progress callback function."""
        print(f"Progress: {progress['percentage']:.1f}% "
              f"({progress['completed']}/{progress['total']})")

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Use batch context with progress tracking
        async with batch_context(
            client,
            max_chunk_size=50,
            max_concurrency=3,
            progress_callback=progress_callback
        ) as batch:

            # Add many operations
            partners_data = [
                {"name": f"Bulk Partner {i}", "email": f"partner{i}@example.com"}
                for i in range(200)
            ]
            batch.create("res.partner", partners_data)

            # Update operations
            batch.update("res.partner", {"active": True}, record_ids=list(range(1, 51)))

            # Operations will be executed with progress reporting

async def batch_with_chunking():
    """Demonstrate batch operations with custom chunking."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup batch manager with custom settings
        batch_manager = await client.setup_batch_manager(
            max_chunk_size=25,  # Smaller chunks
            max_concurrency=2,  # Limited concurrency
            timeout=60
        )

        # Large dataset
        large_dataset = [
            {"name": f"Product {i}", "list_price": 10.0 + i}
            for i in range(500)
        ]

        # Use bulk operations with chunking
        created_ids = await batch_manager.bulk_create(
            model="product.product",
            records=large_dataset,
            chunk_size=25
        )

        print(f"Created {len(created_ids)} products in chunks")
```

### Batch Operation Context

```python
async def batch_operation_context_example():
    """Demonstrate batch operation context for single operations."""

    from zenoo_rpc.batch.context import batch_operation

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Use batch operation context for accumulating create operations
        async with batch_operation(
            client,
            model="res.partner",
            operation_type="create",
            chunk_size=50
        ) as collector:

            # Add records one by one
            for i in range(100):
                collector.add({
                    "name": f"Batch Partner {i}",
                    "email": f"batch{i}@example.com",
                    "is_company": i % 10 == 0  # Every 10th is a company
                })

            # Records are automatically created when context exits

        print("Batch operation context completed")

async def mixed_batch_operations():
    """Demonstrate mixed batch operations."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        await client.setup_batch_manager(max_chunk_size=50, max_concurrency=3)

        async with client.batch() as batch:
            # Create new partners
            await batch.create("res.partner", [
                {"name": "Batch Company A", "is_company": True},
                {"name": "Batch Company B", "is_company": True},
                {"name": "Batch Company C", "is_company": True}
            ])

            # Update existing partners
            await batch.write_many("res.partner", [
                {"id": 1, "values": {"phone": "+1-555-0001"}},
                {"id": 2, "values": {"phone": "+1-555-0002"}},
                {"id": 3, "values": {"phone": "+1-555-0003"}}
            ])

            # Delete inactive partners (if any exist)
            inactive_ids = await client.search("res.partner", [("active", "=", False)])
            if inactive_ids:
                await batch.unlink("res.partner", inactive_ids[:10])  # Limit to 10

        print("Mixed batch operations completed")
```

## Best Practices

### Performance Optimization

```python
async def optimized_batch_operations():
    """Demonstrate performance-optimized batch operations."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Configure batch manager for optimal performance
        batch_manager = await client.setup_batch_manager(
            max_chunk_size=100,    # Larger chunks for better throughput
            max_concurrency=5,     # Balanced concurrency
            timeout=120            # Longer timeout for large operations
        )

        # Use bulk operations for large datasets
        large_dataset = [
            {
                "name": f"Optimized Partner {i}",
                "email": f"opt{i}@example.com",
                "is_company": i % 20 == 0,
                "phone": f"+1-555-{i:04d}"
            }
            for i in range(1000)
        ]

        # Bulk create with optimal chunk size
        created_ids = await batch_manager.bulk_create(
            model="res.partner",
            records=large_dataset,
            chunk_size=100
        )

        print(f"Created {len(created_ids)} partners efficiently")

### Error Recovery

```python
async def batch_with_error_recovery():
    """Demonstrate batch operations with error recovery."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        await client.setup_batch_manager()

        # Prepare data with some intentionally invalid records
        mixed_data = [
            {"name": "Valid Partner 1", "email": "valid1@example.com"},
            {"name": "", "email": "invalid@example.com"},  # Invalid: empty name
            {"name": "Valid Partner 2", "email": "valid2@example.com"},
            {"name": "Valid Partner 3", "email": "invalid-email"},  # Invalid: bad email
            {"name": "Valid Partner 4", "email": "valid4@example.com"}
        ]

        # Filter valid records before batch operation
        valid_records = []
        for record in mixed_data:
            if record.get("name") and "@" in record.get("email", ""):
                valid_records.append(record)
            else:
                print(f"Skipping invalid record: {record}")

        # Process only valid records
        if valid_records:
            async with client.batch() as batch:
                await batch.create("res.partner", valid_records)

            print(f"Successfully processed {len(valid_records)} valid records")
```

## Summary

The batch context provides powerful capabilities for managing bulk operations in Zenoo RPC:

### Key Features

- **Automatic Execution**: Operations are executed when the context exits
- **Transaction Support**: Integration with transaction manager for rollback capability
- **Progress Tracking**: Monitor progress of large batch operations
- **Error Handling**: Robust error handling with partial results
- **Performance Optimization**: Chunking and concurrency control

### Usage Patterns

1. **Simple Batching**: Use `client.batch()` for basic batch operations
2. **Standalone Context**: Use `batch_context()` for more control
3. **Single Operations**: Use `batch_operation()` for accumulating single operation types
4. **Bulk Operations**: Use `BatchManager.bulk_*()` methods for large datasets

### Best Practices

- Configure appropriate chunk sizes for your data volume
- Use transaction contexts for operations requiring rollback capability
- Implement progress tracking for long-running operations
- Validate data before batch operations to avoid partial failures
- Monitor performance and adjust concurrency settings as needed

The batch context makes it easy to perform efficient bulk operations while maintaining data consistency and providing excellent error handling capabilities.

## Best Practices

1. **Auto-execution**: Use auto-execution for simple batch operations
2. **Error Handling**: Always handle batch execution errors appropriately
3. **Chunking**: Use chunking for large batches to avoid memory issues
4. **Validation**: Validate data before adding to batch when possible
5. **Resource Cleanup**: Use context managers for proper resource cleanup

## Related

- [Batch Operations](operations.md) - Operation types and usage
- [Batch Executor](executor.md) - Execution engine
- [Performance Guide](performance.md) - Performance optimization
