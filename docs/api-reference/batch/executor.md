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
    """Executes batch operations with performance optimization.

    This class handles the actual execution of batch operations,
    including chunking, parallel execution, and error handling.

    Features:
    - Automatic operation chunking
    - Parallel execution with concurrency control
    - Progress tracking and monitoring
    - Error handling and partial results
    - Performance optimization
    """

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
        self.client = client
        self.max_chunk_size = max_chunk_size
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.stats = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
            "total_records": 0,
            "processed_records": 0,
        }

    async def execute_operations(
        self,
        operations: List[BatchOperation],
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute a list of batch operations.

        Args:
            operations: List of batch operations to execute
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with execution results and statistics

        Raises:
            BatchExecutionError: If execution fails
        """
        pass
    
```

## Usage Examples

### Basic Batch Execution

```python
from zenoo_rpc.batch.executor import BatchExecutor
from zenoo_rpc.batch.operations import CreateOperation, UpdateOperation

async def basic_batch_execution():
    """Demonstrate basic batch execution."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Create executor with configuration
        executor = BatchExecutor(
            client=client,
            max_chunk_size=50,
            max_concurrency=3,
            timeout=60
        )

        # Create operations
        operations = []
        for i in range(100):
            operations.append(CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}", "email": f"partner{i}@example.com"}]
            ))

        # Execute operations
        result = await executor.execute_operations(operations)

        print(f"Execution completed:")
        print(f"- Total operations: {result['stats']['total_operations']}")
        print(f"- Completed: {result['stats']['completed_operations']}")
        print(f"- Failed: {result['stats']['failed_operations']}")
        print(f"- Duration: {result['duration']:.2f}s")

### Batch Execution with Progress Tracking

```python
async def batch_with_progress():
    """Demonstrate batch execution with progress tracking."""

    async def progress_callback(progress):
        """Progress callback function."""
        print(f"Progress: {progress['completed']}/{progress['total']} "
              f"({progress['percentage']:.1f}%)")
        print(f"Stats: {progress['stats']['completed_operations']} completed, "
              f"{progress['stats']['failed_operations']} failed")

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        executor = BatchExecutor(
            client=client,
            max_chunk_size=25,
            max_concurrency=2
        )

        # Create operations
        operations = []
        for i in range(200):
            operations.append(CreateOperation(
                model="product.product",
                data=[{"name": f"Product {i}", "list_price": 10.0 + i}]
            ))

        # Execute with progress tracking
        result = await executor.execute_operations(operations, progress_callback)
        print(f"Batch completed: {result['stats']['completed_operations']} products created")
```

### Error Handling

```python
from zenoo_rpc.batch.exceptions import BatchExecutionError

async def batch_with_error_handling():
    """Demonstrate batch execution with error handling."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        executor = BatchExecutor(
            client=client,
            max_chunk_size=50,
            retry_attempts=2
        )

        try:
            # Create operations (some may fail)
            operations = [
                CreateOperation("res.partner", [{"name": "Valid Partner 1"}]),
                CreateOperation("res.partner", [{}]),  # Missing required field
                CreateOperation("res.partner", [{"name": "Valid Partner 2"}]),
                UpdateOperation("res.partner", {"active": False}, record_ids=[999999])  # Non-existent ID
            ]

            result = await executor.execute_operations(operations)

            # Check results
            print(f"Execution completed:")
            print(f"- Successful: {result['stats']['completed_operations']}")
            print(f"- Failed: {result['stats']['failed_operations']}")

            # Process individual results
            for i, operation_result in enumerate(result['results']):
                if operation_result['success']:
                    print(f"Operation {i}: Success - {operation_result['result']}")
                else:
                    print(f"Operation {i}: Failed - {operation_result['error']}")

        except BatchExecutionError as e:
            print(f"Batch execution failed: {e}")
            # Handle critical failure
```

## Performance Optimization

### Optimal Configuration

```python
async def performance_optimized_execution():
    """Demonstrate performance-optimized batch execution."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Configure executor for optimal performance
        executor = BatchExecutor(
            client=client,
            max_chunk_size=100,    # Larger chunks for better throughput
            max_concurrency=5,     # Balanced concurrency
            timeout=120,           # Longer timeout for large operations
            retry_attempts=2       # Limited retries for faster failure handling
        )

        # Create large dataset
        operations = []
        for i in range(1000):
            operations.append(CreateOperation(
                model="res.partner",
                data=[{
                    "name": f"Bulk Partner {i}",
                    "email": f"bulk{i}@example.com",
                    "is_company": i % 20 == 0
                }]
            ))

        # Execute with performance monitoring
        import time
        start_time = time.time()

        result = await executor.execute_operations(operations)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Performance Results:")
        print(f"- Total operations: {result['stats']['total_operations']}")
        print(f"- Execution time: {duration:.2f}s")
        print(f"- Operations per second: {result['stats']['total_operations']/duration:.1f}")
        print(f"- Records per second: {result['stats']['total_records']/duration:.1f}")

### Batch Size Optimization

```python
async def find_optimal_batch_size():
    """Find optimal batch size for your environment."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Test different batch sizes
        batch_sizes = [25, 50, 100, 200]
        results = {}

        for batch_size in batch_sizes:
            executor = BatchExecutor(
                client=client,
                max_chunk_size=batch_size,
                max_concurrency=3
            )

            # Create test operations
            operations = []
            for i in range(500):
                operations.append(CreateOperation(
                    model="res.partner",
                    data=[{"name": f"Test Partner {i}"}]
                ))

            # Measure execution time
            import time
            start_time = time.time()

            result = await executor.execute_operations(operations)

            duration = time.time() - start_time
            ops_per_second = len(operations) / duration

            results[batch_size] = {
                "duration": duration,
                "ops_per_second": ops_per_second,
                "success_rate": result['stats']['completed_operations'] / result['stats']['total_operations']
            }

            print(f"Batch size {batch_size}: {ops_per_second:.1f} ops/sec, "
                  f"{results[batch_size]['success_rate']:.1%} success rate")

        # Find optimal batch size
        optimal_size = max(results.keys(), key=lambda k: results[k]['ops_per_second'])
        print(f"Optimal batch size: {optimal_size}")
```

## Advanced Features

### Multiple Model Operations

```python
async def multi_model_batch_execution():
    """Execute operations across multiple models efficiently."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        executor = BatchExecutor(
            client=client,
            max_chunk_size=50,
            max_concurrency=4
        )

        # Create operations for different models
        operations = []

        # Partner operations
        for i in range(100):
            operations.append(CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}", "is_company": i % 10 == 0}]
            ))

        # Product operations
        for i in range(50):
            operations.append(CreateOperation(
                model="product.product",
                data=[{"name": f"Product {i}", "list_price": 10.0 + i}]
            ))

        # Country operations
        for i in range(20):
            operations.append(CreateOperation(
                model="res.country",
                data=[{"name": f"Country {i}", "code": f"C{i:02d}"}]
            ))

        # Execute all operations together
        result = await executor.execute_operations(operations)

        print(f"Multi-model execution completed:")
        print(f"- Total operations: {result['stats']['total_operations']}")
        print(f"- Duration: {result['duration']:.2f}s")

        # Group results by model
        model_results = {}
        for op_result in result['results']:
            model = op_result['model']
            if model not in model_results:
                model_results[model] = {'success': 0, 'failed': 0}

            if op_result['success']:
                model_results[model]['success'] += 1
            else:
                model_results[model]['failed'] += 1

        for model, stats in model_results.items():
            print(f"- {model}: {stats['success']} success, {stats['failed']} failed")
```

### Retry and Timeout Configuration

```python
async def robust_batch_execution():
    """Demonstrate robust batch execution with retries and timeouts."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Configure executor for robustness
        executor = BatchExecutor(
            client=client,
            max_chunk_size=25,     # Smaller chunks for reliability
            max_concurrency=2,     # Conservative concurrency
            timeout=30,            # 30-second timeout per operation
            retry_attempts=3       # Retry failed operations
        )

        # Create operations that might fail
        operations = []
        for i in range(100):
            operations.append(CreateOperation(
                model="res.partner",
                data=[{
                    "name": f"Robust Partner {i}",
                    "email": f"robust{i}@example.com",
                    # Some records might have validation issues
                    "phone": f"+1-555-{i:04d}" if i % 10 != 0 else ""
                }]
            ))

        # Execute with robust error handling
        try:
            result = await executor.execute_operations(operations)

            print(f"Robust execution completed:")
            print(f"- Success rate: {result['stats']['completed_operations']/result['stats']['total_operations']:.1%}")
            print(f"- Failed operations: {result['stats']['failed_operations']}")
            print(f"- Total duration: {result['duration']:.2f}s")

        except Exception as e:
            print(f"Batch execution failed: {e}")

```

## Summary

The BatchExecutor provides powerful capabilities for executing batch operations efficiently:

### Key Features

- **Performance Optimization**: Automatic chunking and parallel execution
- **Error Handling**: Robust error handling with partial results
- **Progress Tracking**: Real-time progress monitoring
- **Retry Logic**: Configurable retry attempts for failed operations
- **Timeout Control**: Operation-level timeout configuration

### Best Practices

1. **Optimize Chunk Size**: Test different chunk sizes to find optimal performance
2. **Control Concurrency**: Balance concurrency with system resources
3. **Monitor Progress**: Use progress callbacks for long-running operations
4. **Handle Errors**: Implement proper error handling for partial failures
5. **Configure Timeouts**: Set appropriate timeouts for your operations

### Usage Patterns

- **Basic Execution**: Use `execute_operations()` for straightforward batch processing
- **Progress Tracking**: Add progress callbacks for user feedback
- **Error Recovery**: Handle partial failures gracefully
- **Performance Tuning**: Adjust configuration based on your environment

The BatchExecutor is the core engine that powers efficient bulk operations in Zenoo RPC, providing the foundation for high-performance data processing.

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
