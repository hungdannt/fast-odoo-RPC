# Batch Executor

The batch executor is responsible for executing batch operations efficiently.

## Overview

The `BatchExecutor` class manages the execution of batched operations, providing:
- Efficient bulk operations
- Error handling and rollback
- Performance optimization
- Progress tracking

## Class Reference

### BatchExecutor

```python
class BatchExecutor:
    """Executes batch operations with optimization and error handling."""
    
    def __init__(self, client: ZenooClient, batch_size: int = 100):
        """Initialize batch executor.
        
        Args:
            client: Zenoo RPC client instance
            batch_size: Maximum operations per batch
        """
        self.client = client
        self.batch_size = batch_size
        self.operations = []
        self.results = []
    
    async def execute(self) -> List[Any]:
        """Execute all batched operations.
        
        Returns:
            List of operation results
            
        Raises:
            BatchExecutionError: If batch execution fails
        """
        pass
    
    def add_operation(self, operation: BatchOperation):
        """Add operation to batch.
        
        Args:
            operation: Operation to add to batch
        """
        pass
    
    async def execute_with_progress(self, callback: Callable = None) -> List[Any]:
        """Execute batch with progress tracking.
        
        Args:
            callback: Progress callback function
            
        Returns:
            List of operation results
        """
        pass
```

## Usage Examples

### Basic Batch Execution

```python
async def basic_batch_execution():
    """Demonstrate basic batch execution."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        executor = BatchExecutor(client, batch_size=50)
        
        # Add operations
        for i in range(100):
            executor.add_operation(CreateOperation(
                "res.partner",
                {"name": f"Partner {i}", "email": f"partner{i}@example.com"}
            ))
        
        # Execute batch
        results = await executor.execute()
        print(f"Created {len(results)} partners")

async def batch_with_progress():
    """Demonstrate batch execution with progress tracking."""
    
    def progress_callback(completed: int, total: int):
        print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        executor = BatchExecutor(client)
        
        # Add operations
        for i in range(200):
            executor.add_operation(CreateOperation(
                "product.product",
                {"name": f"Product {i}", "list_price": 10.0 + i}
            ))
        
        # Execute with progress
        results = await executor.execute_with_progress(progress_callback)
        print(f"Batch completed: {len(results)} products created")
```

### Error Handling

```python
async def batch_with_error_handling():
    """Demonstrate batch execution with error handling."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        executor = BatchExecutor(client)
        
        try:
            # Add operations (some may fail)
            executor.add_operation(CreateOperation("res.partner", {"name": "Valid Partner"}))
            executor.add_operation(CreateOperation("res.partner", {}))  # Missing required field
            executor.add_operation(CreateOperation("res.partner", {"name": "Another Valid Partner"}))
            
            results = await executor.execute()
            
        except BatchExecutionError as e:
            print(f"Batch execution failed: {e}")
            print(f"Successful operations: {e.successful_count}")
            print(f"Failed operations: {e.failed_count}")
            
            # Access partial results
            for result in e.partial_results:
                if result.success:
                    print(f"Success: {result.data}")
                else:
                    print(f"Error: {result.error}")
```

## Performance Optimization

### Batch Size Tuning

```python
class OptimizedBatchExecutor(BatchExecutor):
    """Batch executor with performance optimizations."""
    
    def __init__(self, client: ZenooClient, auto_tune: bool = True):
        super().__init__(client)
        self.auto_tune = auto_tune
        self.performance_history = []
    
    async def execute_optimized(self) -> List[Any]:
        """Execute batch with automatic performance tuning."""
        
        if self.auto_tune:
            optimal_batch_size = await self._determine_optimal_batch_size()
            self.batch_size = optimal_batch_size
        
        return await self.execute()
    
    async def _determine_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on performance history."""
        
        if not self.performance_history:
            return self.batch_size
        
        # Analyze performance history and adjust batch size
        avg_time_per_operation = sum(h['time_per_op'] for h in self.performance_history[-5:]) / 5
        
        if avg_time_per_operation < 0.1:  # Fast operations
            return min(self.batch_size * 2, 500)
        elif avg_time_per_operation > 1.0:  # Slow operations
            return max(self.batch_size // 2, 10)
        else:
            return self.batch_size
```

## Advanced Features

### Parallel Batch Execution

```python
import asyncio
from typing import List

class ParallelBatchExecutor:
    """Execute multiple batches in parallel."""
    
    def __init__(self, client: ZenooClient, max_concurrent_batches: int = 3):
        self.client = client
        self.max_concurrent_batches = max_concurrent_batches
    
    async def execute_parallel_batches(self, operation_groups: List[List[BatchOperation]]) -> List[List[Any]]:
        """Execute multiple batches in parallel.
        
        Args:
            operation_groups: List of operation groups to execute in parallel
            
        Returns:
            List of results for each batch
        """
        
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        
        async def execute_single_batch(operations: List[BatchOperation]) -> List[Any]:
            async with semaphore:
                executor = BatchExecutor(self.client)
                for operation in operations:
                    executor.add_operation(operation)
                return await executor.execute()
        
        # Execute batches in parallel
        tasks = [execute_single_batch(ops) for ops in operation_groups]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Batch failed: {result}")
                final_results.append([])
            else:
                final_results.append(result)
        
        return final_results

# Usage
async def parallel_batch_example():
    """Demonstrate parallel batch execution."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        parallel_executor = ParallelBatchExecutor(client, max_concurrent_batches=3)
        
        # Create operation groups
        partner_operations = [
            CreateOperation("res.partner", {"name": f"Partner {i}"})
            for i in range(50)
        ]
        
        product_operations = [
            CreateOperation("product.product", {"name": f"Product {i}"})
            for i in range(50)
        ]
        
        order_operations = [
            CreateOperation("sale.order", {"partner_id": 1})
            for i in range(30)
        ]
        
        # Execute in parallel
        results = await parallel_executor.execute_parallel_batches([
            partner_operations,
            product_operations,
            order_operations
        ])
        
        print(f"Partners created: {len(results[0])}")
        print(f"Products created: {len(results[1])}")
        print(f"Orders created: {len(results[2])}")
```

## Best Practices

1. **Batch Size**: Start with 100 operations per batch and tune based on performance
2. **Error Handling**: Always handle partial failures in batch operations
3. **Progress Tracking**: Use progress callbacks for long-running batches
4. **Memory Management**: Process large datasets in chunks to avoid memory issues
5. **Parallel Execution**: Use parallel batches for independent operations

## Related

- [Batch Operations](operations.md) - Operation types and usage
- [Batch Context](context.md) - Context management
- [Performance Guide](performance.md) - Performance optimization
