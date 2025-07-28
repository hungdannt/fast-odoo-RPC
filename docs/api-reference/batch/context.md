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
    """Context manager for batch operations."""
    
    def __init__(self, client: ZenooClient, auto_execute: bool = True):
        """Initialize batch context.
        
        Args:
            client: Zenoo RPC client instance
            auto_execute: Whether to auto-execute on context exit
        """
        self.client = client
        self.auto_execute = auto_execute
        self.operations = []
        self.results = []
    
    async def __aenter__(self):
        """Enter batch context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit batch context and execute operations."""
        if self.auto_execute and not exc_type:
            await self.execute()
    
    def create(self, model: str, data: Dict[str, Any]):
        """Add create operation to batch."""
        pass
    
    def update(self, model: str, data: Dict[str, Any], ids: List[int]):
        """Add update operation to batch."""
        pass
    
    def delete(self, model: str, ids: List[int]):
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
        
        # Operations are automatically executed on context exit
        async with client.batch() as batch:
            # Add operations
            batch.create("res.partner", {"name": "Partner 1", "email": "p1@example.com"})
            batch.create("res.partner", {"name": "Partner 2", "email": "p2@example.com"})
            batch.create("product.product", {"name": "Product 1", "list_price": 10.0})
        
        # Operations are executed here automatically
        print("Batch operations completed")

async def manual_batch_execution():
    """Demonstrate manual batch execution."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Disable auto-execution
        async with BatchContext(client, auto_execute=False) as batch:
            batch.create("res.partner", {"name": "Manual Partner"})
            batch.create("product.product", {"name": "Manual Product"})
            
            # Execute manually
            results = await batch.execute()
            print(f"Created {len(results)} records manually")
```

### Error Handling

```python
async def batch_with_error_handling():
    """Demonstrate error handling in batch context."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.batch() as batch:
                batch.create("res.partner", {"name": "Valid Partner"})
                batch.create("res.partner", {})  # Invalid - missing name
                batch.create("res.partner", {"name": "Another Partner"})
                
                # If an error occurs, the context will handle it
                
        except BatchExecutionError as e:
            print(f"Batch failed: {e}")
            print(f"Successful operations: {e.successful_count}")
            
            # Handle partial results
            for i, result in enumerate(e.partial_results):
                if result.success:
                    print(f"Operation {i}: Success - ID {result.data.id}")
                else:
                    print(f"Operation {i}: Failed - {result.error}")

async def batch_with_rollback():
    """Demonstrate batch rollback on error."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        class RollbackBatchContext(BatchContext):
            """Batch context with rollback capability."""
            
            def __init__(self, client: ZenooClient):
                super().__init__(client, auto_execute=False)
                self.created_ids = []
            
            async def execute_with_rollback(self):
                """Execute with automatic rollback on failure."""
                try:
                    results = await self.execute()
                    
                    # Track created records for potential rollback
                    for result in results:
                        if hasattr(result, 'id'):
                            self.created_ids.append((result._model_name, result.id))
                    
                    return results
                    
                except Exception as e:
                    # Rollback created records
                    await self.rollback()
                    raise
            
            async def rollback(self):
                """Rollback created records."""
                for model_name, record_id in reversed(self.created_ids):
                    try:
                        await self.client.model(model_name).filter(id=record_id).delete()
                        print(f"Rolled back {model_name} ID {record_id}")
                    except Exception as rollback_error:
                        print(f"Rollback failed for {model_name} ID {record_id}: {rollback_error}")
        
        async with RollbackBatchContext(client) as batch:
            batch.create("res.partner", {"name": "Partner 1"})
            batch.create("res.partner", {"name": "Partner 2"})
            
            try:
                await batch.execute_with_rollback()
                print("Batch completed successfully")
            except Exception as e:
                print(f"Batch failed and rolled back: {e}")
```

### Advanced Context Features

```python
class AdvancedBatchContext(BatchContext):
    """Advanced batch context with additional features."""
    
    def __init__(self, client: ZenooClient, batch_size: int = 100, parallel: bool = False):
        super().__init__(client)
        self.batch_size = batch_size
        self.parallel = parallel
        self.operation_groups = []
    
    async def execute_in_chunks(self) -> List[Any]:
        """Execute operations in chunks."""
        
        all_results = []
        
        # Split operations into chunks
        for i in range(0, len(self.operations), self.batch_size):
            chunk = self.operations[i:i + self.batch_size]
            
            if self.parallel:
                # Execute chunks in parallel
                chunk_results = await self._execute_parallel_chunk(chunk)
            else:
                # Execute chunks sequentially
                chunk_results = await self._execute_sequential_chunk(chunk)
            
            all_results.extend(chunk_results)
        
        return all_results
    
    async def _execute_parallel_chunk(self, operations: List[BatchOperation]) -> List[Any]:
        """Execute chunk operations in parallel."""
        
        # Group operations by type for parallel execution
        create_ops = [op for op in operations if isinstance(op, CreateOperation)]
        update_ops = [op for op in operations if isinstance(op, UpdateOperation)]
        delete_ops = [op for op in operations if isinstance(op, DeleteOperation)]
        
        tasks = []
        if create_ops:
            tasks.append(self._execute_create_operations(create_ops))
        if update_ops:
            tasks.append(self._execute_update_operations(update_ops))
        if delete_ops:
            tasks.append(self._execute_delete_operations(delete_ops))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Flatten results
            flattened_results = []
            for result in results:
                if isinstance(result, list):
                    flattened_results.extend(result)
                elif not isinstance(result, Exception):
                    flattened_results.append(result)
            return flattened_results
        
        return []
    
    async def _execute_sequential_chunk(self, operations: List[BatchOperation]) -> List[Any]:
        """Execute chunk operations sequentially."""
        
        results = []
        for operation in operations:
            try:
                result = await operation.execute(self.client)
                results.append(result)
            except Exception as e:
                # Handle individual operation errors
                results.append(BatchOperationResult(success=False, error=str(e)))
        
        return results

# Usage of advanced context
async def advanced_batch_example():
    """Demonstrate advanced batch context features."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Large batch with chunking and parallel execution
        async with AdvancedBatchContext(client, batch_size=50, parallel=True) as batch:
            
            # Add many operations
            for i in range(500):
                batch.create("res.partner", {
                    "name": f"Bulk Partner {i}",
                    "email": f"bulk{i}@example.com"
                })
            
            for i in range(200):
                batch.create("product.product", {
                    "name": f"Bulk Product {i}",
                    "list_price": 10.0 + (i * 0.5)
                })
            
            # Operations will be executed in chunks with parallel processing
            results = await batch.execute_in_chunks()
            print(f"Bulk operations completed: {len(results)} records created")
```

### Context with Validation

```python
class ValidatedBatchContext(BatchContext):
    """Batch context with operation validation."""
    
    def __init__(self, client: ZenooClient, validate_before_execute: bool = True):
        super().__init__(client)
        self.validate_before_execute = validate_before_execute
        self.validation_errors = []
    
    def create(self, model: str, data: Dict[str, Any]):
        """Add create operation with validation."""
        
        if self.validate_before_execute:
            validation_error = self._validate_create_data(model, data)
            if validation_error:
                self.validation_errors.append(validation_error)
                return
        
        super().create(model, data)
    
    def _validate_create_data(self, model: str, data: Dict[str, Any]) -> Optional[str]:
        """Validate create operation data."""
        
        # Basic validation rules
        if model == "res.partner":
            if not data.get("name"):
                return "Partner name is required"
            if data.get("email") and "@" not in data["email"]:
                return "Invalid email format"
        
        elif model == "product.product":
            if not data.get("name"):
                return "Product name is required"
            if data.get("list_price") and data["list_price"] < 0:
                return "Product price cannot be negative"
        
        return None
    
    async def execute(self) -> List[Any]:
        """Execute with pre-validation check."""
        
        if self.validation_errors:
            raise ValidationError(f"Validation failed: {self.validation_errors}")
        
        return await super().execute()

# Usage with validation
async def validated_batch_example():
    """Demonstrate batch context with validation."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with ValidatedBatchContext(client) as batch:
                batch.create("res.partner", {"name": "Valid Partner", "email": "valid@example.com"})
                batch.create("res.partner", {"email": "invalid-email"})  # Missing name
                batch.create("product.product", {"name": "Valid Product", "list_price": 10.0})
                batch.create("product.product", {"list_price": -5.0})  # Missing name, negative price
                
        except ValidationError as e:
            print(f"Validation failed: {e}")
            print("Please fix validation errors and try again")
```

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
