# Batch Operations

Zenoo RPC's batch operations system allows you to perform multiple database operations efficiently in a single transaction. This dramatically improves performance for bulk data processing while maintaining data consistency.

## Overview

Batch operations provide:

- **High Performance**: Minimize RPC calls by batching operations
- **Transaction Safety**: All operations in a batch are atomic
- **Memory Efficiency**: Process large datasets without loading everything into memory
- **Progress Tracking**: Monitor batch operation progress
- **Error Handling**: Robust error handling with rollback capabilities

## Setting Up Batch Manager

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.batch.manager import BatchManager

async with ZenooClient("localhost", port=8069) as client:
    await client.login("my_database", "admin", "admin")

    # Setup batch manager with configuration
    batch_manager = BatchManager(
        client=client,
        max_chunk_size=100,        # Process 100 records per chunk
        max_concurrency=5,         # Process 5 chunks concurrently
        timeout=300                # Operation timeout in seconds
    )

    # Store batch manager in client for convenience
    client.batch_manager = batch_manager
```

## Basic Batch Operations

### Batch Context Manager

```python
from zenoo_rpc.models.common import ResPartner

# Use batch context for automatic transaction management
async with batch_manager.batch() as batch_context:
    # All operations within this context are batched
    partners_data = [
        {"name": "Company A", "email": "a@company.com", "is_company": True},
        {"name": "Company B", "email": "b@company.com", "is_company": True},
        {"name": "Company C", "email": "c@company.com", "is_company": True},
    ]

    # Create multiple records efficiently
    created_ids = await batch_manager.bulk_create(
        model="res.partner",
        records=partners_data,
        chunk_size=50
    )
    print(f"Created {len(created_ids)} partners")
```

### Batch Create Operations

```python
# Prepare data for batch creation
customers_data = []
for i in range(1000):
    customers_data.append({
        "name": f"Customer {i:04d}",
        "email": f"customer{i:04d}@example.com",
        "phone": f"+1-555-{i:04d}",
        "is_company": False
    })

# Batch create with progress tracking
created_customer_ids = await batch_manager.bulk_create(
    model="res.partner",
    records=customers_data,
    chunk_size=50,  # Override default chunk size
    context={"tracking_disable": True}  # Disable tracking for performance
)

print(f"Successfully created {len(created_customer_ids)} customers")
```

### Batch Update Operations

```python
# Update multiple records
async with client.batch() as batch:
    # Get partners to update
    partners = await client.model(ResPartner).filter(
        is_company=True,
        active=True
    ).all()
    
    # Prepare update data
    updates = []
    for partner in partners:
        updates.append({
            "id": partner.id,
            "data": {
                "category_id": [(4, 1)],  # Add category
                "comment": f"Updated on {datetime.now()}"
            }
        })
    
    # Batch update
    updated_count = await batch.update_many(ResPartner, updates)
    print(f"Updated {updated_count} partners")
```

### Batch Delete Operations

```python
# Batch delete with conditions
async with client.batch() as batch:
    # Delete inactive partners created more than a year ago
    deleted_count = await batch.delete_many(
        ResPartner,
        filters={
            "active": False,
            "create_date__lt": datetime.now() - timedelta(days=365)
        },
        chunk_size=25
    )
    
    print(f"Deleted {deleted_count} inactive partners")
```

## Advanced Batch Patterns

### Mixed Operations in Single Batch

```python
async with client.batch() as batch:
    # Create new partners
    new_partners = await batch.create_many(ResPartner, [
        {"name": "New Company 1", "is_company": True},
        {"name": "New Company 2", "is_company": True}
    ])
    
    # Update existing partners
    await batch.update_many(ResPartner, [
        {"id": 1, "data": {"active": True}},
        {"id": 2, "data": {"active": True}}
    ])
    
    # Delete old partners
    await batch.delete_many(ResPartner, filters={"active": False})
    
    print("Mixed batch operations completed")
```

### Batch with Relationships

```python
from zenoo_rpc.models.common import ResPartner, ResPartnerCategory

async with client.batch() as batch:
    # Create categories first
    categories = await batch.create_many(ResPartnerCategory, [
        {"name": "VIP Customer", "color": 1},
        {"name": "Premium Partner", "color": 2}
    ])
    
    # Create partners with relationships
    partners_data = []
    for i in range(100):
        partners_data.append({
            "name": f"Partner {i:03d}",
            "email": f"partner{i:03d}@example.com",
            "category_id": [(6, 0, [cat.id for cat in categories])],  # Link categories
            "is_company": True
        })
    
    partners = await batch.create_many(ResPartner, partners_data)
    print(f"Created {len(partners)} partners with categories")
```

### Conditional Batch Operations

```python
async with client.batch() as batch:
    # Get partners that need updates
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).all()
    
    create_data = []
    update_data = []
    
    for partner in partners:
        if not partner.email:
            # Update partners without email
            update_data.append({
                "id": partner.id,
                "data": {"email": f"noreply@{partner.name.lower().replace(' ', '')}.com"}
            })
        
        if partner.is_company and not partner.website:
            # Create website records for companies
            create_data.append({
                "name": f"{partner.name} Website",
                "url": f"https://{partner.name.lower().replace(' ', '')}.com",
                "partner_id": partner.id
            })
    
    # Execute conditional operations
    if update_data:
        await batch.update_many(ResPartner, update_data)
    
    if create_data:
        from zenoo_rpc.models.common import Website
        await batch.create_many(Website, create_data)
```

## Progress Tracking

### Basic Progress Tracking

```python
# Enable progress tracking
async with client.batch(show_progress=True) as batch:
    large_dataset = [{"name": f"Record {i}"} for i in range(10000)]
    
    # Progress will be displayed automatically
    records = await batch.create_many(ResPartner, large_dataset)
```

### Custom Progress Callbacks

```python
def progress_callback(current: int, total: int, operation: str):
    percentage = (current / total) * 100
    print(f"{operation}: {current}/{total} ({percentage:.1f}%)")

async with client.batch() as batch:
    # Set custom progress callback
    batch.set_progress_callback(progress_callback)
    
    large_dataset = [{"name": f"Record {i}"} for i in range(5000)]
    records = await batch.create_many(ResPartner, large_dataset)
```

### Progress with Async Iteration

```python
async def process_large_dataset():
    dataset = [{"name": f"Record {i}"} for i in range(50000)]
    
    async with client.batch() as batch:
        # Process in chunks with progress
        async for chunk_result in batch.create_many_iter(
            ResPartner, 
            dataset, 
            chunk_size=100
        ):
            print(f"Processed chunk: {len(chunk_result.records)} records")
            if chunk_result.errors:
                print(f"Errors in chunk: {len(chunk_result.errors)}")
```

## Error Handling

### Basic Error Handling

```python
from zenoo_rpc.exceptions import BatchOperationError, ValidationError

try:
    async with client.batch() as batch:
        # Some operations might fail
        partners_data = [
            {"name": "Valid Partner", "email": "valid@example.com"},
            {"name": "", "email": "invalid"},  # Invalid data
            {"name": "Another Valid", "email": "valid2@example.com"}
        ]
        
        partners = await batch.create_many(ResPartner, partners_data)
        
except BatchOperationError as e:
    print(f"Batch operation failed: {e}")
    print(f"Successful operations: {e.successful_count}")
    print(f"Failed operations: {e.failed_count}")
    
    # Access individual errors
    for error in e.errors:
        print(f"Error on record {error.record_index}: {error.message}")
```

### Partial Success Handling

```python
# Configure batch to continue on errors
async with client.batch(continue_on_error=True) as batch:
    mixed_data = [
        {"name": "Good Record 1", "email": "good1@example.com"},
        {"name": "", "email": "bad"},  # This will fail
        {"name": "Good Record 2", "email": "good2@example.com"},
    ]
    
    result = await batch.create_many(ResPartner, mixed_data)
    
    print(f"Created: {len(result.successful)}")
    print(f"Failed: {len(result.failed)}")
    
    # Process successful records
    for record in result.successful:
        print(f"Created: {record.name}")
    
    # Handle failed records
    for error in result.failed:
        print(f"Failed to create record {error.index}: {error.message}")
```

### Retry Failed Operations

```python
async def batch_with_retry():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with client.batch() as batch:
                # Your batch operations here
                result = await batch.create_many(ResPartner, data)
                return result
                
        except BatchOperationError as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            
            print(f"Batch failed, retrying ({retry_count}/{max_retries})")
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
```

## Performance Optimization

### Optimal Chunk Sizing

```python
# Configure chunk size based on data complexity
async with client.batch() as batch:
    # Small chunks for complex data with relationships
    complex_data = [...]  # Data with many relationships
    await batch.create_many(
        ResPartner, 
        complex_data, 
        chunk_size=25  # Smaller chunks
    )
    
    # Larger chunks for simple data
    simple_data = [...]  # Simple data without relationships
    await batch.create_many(
        ResPartner, 
        simple_data, 
        chunk_size=200  # Larger chunks
    )
```

### Concurrent Processing

```python
# Configure concurrent chunk processing
async with client.batch() as batch:
    # Set concurrency level
    batch.set_max_concurrent_chunks(10)
    
    large_dataset = [{"name": f"Record {i}"} for i in range(100000)]
    
    # Process with high concurrency
    records = await batch.create_many(ResPartner, large_dataset)
```

### Memory-Efficient Processing

```python
async def process_huge_dataset():
    """Process dataset too large to fit in memory"""
    
    async def data_generator():
        # Generate data on-the-fly instead of loading all at once
        for i in range(1000000):  # 1 million records
            yield {
                "name": f"Generated Record {i}",
                "email": f"record{i}@generated.com"
            }
    
    async with client.batch() as batch:
        # Process generator with streaming
        total_created = 0
        
        async for chunk_result in batch.create_many_stream(
            ResPartner,
            data_generator(),
            chunk_size=500
        ):
            total_created += len(chunk_result.records)
            print(f"Total created so far: {total_created}")
```

## Best Practices

### 1. Use Appropriate Chunk Sizes

```python
# Good: Adjust chunk size based on data complexity
async with client.batch() as batch:
    # Simple data - larger chunks
    simple_records = await batch.create_many(
        ResPartner, simple_data, chunk_size=200
    )
    
    # Complex data with relationships - smaller chunks
    complex_records = await batch.create_many(
        ResPartner, complex_data, chunk_size=50
    )
```

### 2. Handle Errors Gracefully

```python
# Good: Plan for partial failures
async with client.batch(continue_on_error=True) as batch:
    result = await batch.create_many(ResPartner, data)
    
    # Process successful records
    for record in result.successful:
        await process_successful_record(record)
    
    # Handle failed records
    for error in result.failed:
        await handle_failed_record(error)
```

### 3. Use Progress Tracking for Long Operations

```python
# Good: Show progress for long-running operations
async with client.batch(show_progress=True) as batch:
    large_dataset = generate_large_dataset()
    records = await batch.create_many(ResPartner, large_dataset)
```

### 4. Optimize for Your Use Case

```python
# Good: Configure based on your specific needs
async with client.batch() as batch:
    if is_high_priority_operation:
        batch.set_max_concurrent_chunks(1)  # Sequential for reliability
    else:
        batch.set_max_concurrent_chunks(10)  # Concurrent for speed
    
    records = await batch.create_many(ResPartner, data)
```

## Next Steps

- Learn about [Transactions](transactions.md) for advanced transaction management
- Explore [Retry Mechanisms](retry-mechanisms.md) for handling batch operation failures
- Check [Performance Optimization](../tutorials/performance-optimization.md) for more performance tips
