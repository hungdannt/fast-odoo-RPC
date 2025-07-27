# Error Handling

Zenoo RPC provides a comprehensive exception hierarchy and robust error handling mechanisms to help you build resilient applications with clear error reporting and recovery strategies.

## Exception Hierarchy

Zenoo RPC organizes exceptions in a logical hierarchy for precise error handling:

```
ZenooError (base)
├── ConnectionError
├── RequestTimeoutError (TimeoutError)
├── AuthenticationError
├── ValidationError
├── AccessError
├── MethodNotFoundError
├── InternalError
├── TransactionError (from transaction module)
├── BatchError (from batch module)
├── CacheError (from cache module)
└── RetryError (from retry module)
    ├── MaxRetriesExceededError
    └── RetryTimeoutError
```

## Basic Error Handling

### Catching Specific Exceptions

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import (
    AuthenticationError,
    ValidationError,
    AccessError,
    ConnectionError,
    RequestTimeoutError
)

async with ZenooClient("localhost", port=8069) as client:
    try:
        await client.login("my_database", "admin", "wrong_password")
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Server message: {e.server_message}")
        
    try:
        partner = await client.model(ResPartner).get(99999)
        
    except NotFoundError as e:
        print(f"Partner not found: {e}")
        print(f"Searched ID: {e.searched_id}")
        
    try:
        partner = await client.model(ResPartner).create({
            "name": "",  # Invalid: empty name
            "email": "invalid-email"  # Invalid: bad email format
        })
        
    except ValidationError as e:
        print(f"Validation failed: {e}")
        print(f"Field errors: {e.field_errors}")
        for field, error in e.field_errors.items():
            print(f"  {field}: {error}")
```

### Generic Error Handling

```python
from zenoo_rpc.exceptions import ZenooError

try:
    # Any Zenoo RPC operation
    partners = await client.search("res.partner", [("is_company", "=", True)])

except ZenooError as e:
    # Catch all Zenoo RPC exceptions
    print(f"Zenoo RPC error: {e}")
    print(f"Error type: {type(e).__name__}")
    print(f"Error context: {e.context}")

except Exception as e:
    # Catch any other unexpected errors
    print(f"Unexpected error: {e}")
```

## Connection and Network Errors

### Network Error Handling

```python
from zenoo_rpc.exceptions import ConnectionError, RequestTimeoutError

async def robust_connection():
    try:
        async with ZenooClient("unreliable-server.com", port=8069) as client:
            await client.login("database", "user", "password")
            return await client.search("res.partner", [])

    except ConnectionError as e:
        print(f"Connection failed: {e}")
        print(f"Context: {e.context}")
        return []

    except RequestTimeoutError as e:
        print(f"Operation timed out: {e}")
        print(f"Context: {e.context}")
        return []
```

### Connection Recovery

```python
import asyncio
from zenoo_rpc.exceptions import ConnectionError

async def connect_with_retry(max_attempts=3):
    """Connect with automatic retry on connection failures"""
    
    for attempt in range(max_attempts):
        try:
            client = ZenooClient("localhost", port=8069)
            await client.connect()
            await client.login("my_database", "admin", "admin")
            return client
            
        except ConnectionError as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_attempts - 1:
                delay = 2 ** attempt  # Exponential backoff
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                print("All connection attempts failed")
                raise
```

## Server and Database Errors

### Server Error Handling

```python
from zenoo_rpc.exceptions import InternalError, AccessError, MethodNotFoundError

try:
    # Operation that might trigger server errors
    result = await client.call(
        "res.partner",
        "complex_server_method",
        [complex_params]
    )

except InternalError as e:
    print(f"Internal server error: {e}")
    print(f"Server traceback: {e.server_traceback}")
    print(f"Context: {e.context}")

except AccessError as e:
    print(f"Access denied: {e}")
    print(f"Server traceback: {e.server_traceback}")
    print(f"Context: {e.context}")

except MethodNotFoundError as e:
    print(f"Method not found: {e}")
    print(f"Context: {e.context}")
```

### Database Connection Issues

```python
async def handle_database_issues():
    try:
        await client.login("nonexistent_db", "admin", "admin")
        
    except DatabaseError as e:
        if "database does not exist" in str(e).lower():
            print("Database does not exist")
            # Maybe create database or use different one
            
        elif "too many connections" in str(e).lower():
            print("Database connection pool exhausted")
            # Wait and retry, or use connection pooling
            
        else:
            print(f"Other database error: {e}")
```

## Validation and Data Errors

### Field Validation Errors

```python
from zenoo_rpc.exceptions import ValidationError

try:
    partner = await client.model(ResPartner).create({
        "name": "",  # Required field
        "email": "not-an-email",  # Invalid format
        "phone": "123",  # Too short
        "vat": "INVALID_VAT"  # Invalid VAT number
    })
    
except ValidationError as e:
    print("Validation errors occurred:")
    
    # Access field-specific errors
    for field_name, error_message in e.field_errors.items():
        print(f"  {field_name}: {error_message}")
    
    # Access constraint violations
    for constraint in e.constraint_violations:
        print(f"  Constraint '{constraint.name}': {constraint.message}")
    
    # Get suggested fixes
    if e.suggestions:
        print("Suggestions:")
        for suggestion in e.suggestions:
            print(f"  - {suggestion}")
```

### Data Integrity Errors

```python
from zenoo_rpc.exceptions import IntegrityError

try:
    # Try to delete a partner that has related records
    await client.model(ResPartner).filter(id=1).delete()
    
except IntegrityError as e:
    print(f"Cannot delete due to related records: {e}")
    print(f"Related models: {e.related_models}")
    print(f"Related records count: {e.related_count}")
    
    # Handle by updating related records first
    if e.can_cascade:
        print("Attempting cascade delete...")
        await client.model(ResPartner).filter(id=1).delete(cascade=True)
```

## Operation-Specific Errors

### Transaction Errors

```python
from zenoo_rpc.exceptions import TransactionError, RollbackError

try:
    async with client.transaction() as tx:
        # Multiple operations in transaction
        partner = await client.model(ResPartner).create({
            "name": "Test Partner"
        })
        
        # This might fail and cause rollback
        await client.model(ResPartner).create({
            "name": partner.name  # Duplicate name might not be allowed
        })
        
except TransactionError as e:
    print(f"Transaction failed: {e}")
    print(f"Failed operation: {e.failed_operation}")
    print(f"Rollback successful: {e.rollback_successful}")
    
except RollbackError as e:
    print(f"Rollback failed: {e}")
    print(f"Database may be in inconsistent state")
    # This is serious - might need manual intervention
```

### Batch Operation Errors

```python
from zenoo_rpc.exceptions import BatchOperationError

try:
    async with client.batch() as batch:
        # Batch operations that might partially fail
        partners_data = [
            {"name": "Valid Partner 1", "email": "valid1@example.com"},
            {"name": "", "email": "invalid"},  # This will fail
            {"name": "Valid Partner 2", "email": "valid2@example.com"}
        ]
        
        partners = await batch.create_many(ResPartner, partners_data)
        
except BatchOperationError as e:
    print(f"Batch operation partially failed: {e}")
    print(f"Successful operations: {e.successful_count}")
    print(f"Failed operations: {e.failed_count}")
    
    # Process successful results
    for success in e.successful_results:
        print(f"Created partner: {success.name}")
    
    # Handle individual failures
    for failure in e.failed_operations:
        print(f"Failed to create partner at index {failure.index}: {failure.error}")
```

### Cache Errors

```python
from zenoo_rpc.exceptions import CacheError, CacheConnectionError

try:
    # Cache operation that might fail
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).cache(ttl=300).all()
    
except CacheConnectionError as e:
    print(f"Cache server unavailable: {e}")
    print("Falling back to direct database query...")
    
    # Fallback to non-cached query
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).all()
    
except CacheError as e:
    print(f"Cache operation failed: {e}")
    # Continue without caching
```

## Advanced Error Handling Patterns

### Error Context and Debugging

```python
from zenoo_rpc.exceptions import ZenooRPCError

def log_error_context(error: ZenooRPCError):
    """Log comprehensive error context for debugging"""
    
    print(f"Error: {error}")
    print(f"Type: {type(error).__name__}")
    print(f"Time: {error.timestamp}")
    
    # Request context
    if hasattr(error, 'request_context'):
        ctx = error.request_context
        print(f"Request ID: {ctx.request_id}")
        print(f"Method: {ctx.method}")
        print(f"Model: {ctx.model}")
        print(f"User: {ctx.user_id}")
    
    # Server context
    if hasattr(error, 'server_context'):
        ctx = error.server_context
        print(f"Server: {ctx.server_version}")
        print(f"Database: {ctx.database}")
        print(f"Session: {ctx.session_id}")
    
    # Stack trace
    if hasattr(error, 'client_traceback'):
        print(f"Client traceback: {error.client_traceback}")
    
    if hasattr(error, 'server_traceback'):
        print(f"Server traceback: {error.server_traceback}")

# Usage
try:
    await some_operation()
except ZenooRPCError as e:
    log_error_context(e)
```

### Error Recovery Strategies

```python
async def resilient_partner_operation(partner_data):
    """Demonstrate various error recovery strategies"""
    
    # Strategy 1: Retry with backoff
    for attempt in range(3):
        try:
            return await client.model(ResPartner).create(partner_data)
            
        except NetworkError:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
    
    # Strategy 2: Fallback to different approach
    try:
        return await client.model(ResPartner).create(partner_data)
        
    except ValidationError as e:
        # Try to fix validation errors automatically
        fixed_data = await auto_fix_validation_errors(partner_data, e)
        return await client.model(ResPartner).create(fixed_data)
    
    # Strategy 3: Graceful degradation
    try:
        return await client.model(ResPartner).create(partner_data)
        
    except PermissionError:
        # Create with minimal permissions
        minimal_data = {k: v for k, v in partner_data.items() 
                      if k in ['name', 'email']}
        return await client.model(ResPartner).create(minimal_data)

async def auto_fix_validation_errors(data, error):
    """Automatically fix common validation errors"""
    fixed_data = data.copy()
    
    for field, message in error.field_errors.items():
        if "required" in message.lower() and not fixed_data.get(field):
            # Provide default values for required fields
            if field == "name":
                fixed_data[field] = "Unknown"
            elif field == "email":
                fixed_data[field] = "noreply@example.com"
        
        elif "invalid email" in message.lower():
            # Fix email format
            fixed_data[field] = f"{fixed_data[field]}@example.com"
    
    return fixed_data
```

### Error Aggregation

```python
from zenoo_rpc.exceptions import ErrorAggregator

async def bulk_operation_with_error_aggregation():
    """Collect and handle multiple errors from bulk operations"""
    
    aggregator = ErrorAggregator()
    successful_results = []
    
    partner_data_list = [...]  # Large list of partner data
    
    for i, partner_data in enumerate(partner_data_list):
        try:
            partner = await client.model(ResPartner).create(partner_data)
            successful_results.append(partner)
            
        except ZenooRPCError as e:
            aggregator.add_error(e, context={"index": i, "data": partner_data})
    
    # Process aggregated errors
    if aggregator.has_errors():
        print(f"Operation completed with {len(aggregator.errors)} errors")
        
        # Group errors by type
        error_groups = aggregator.group_by_type()
        for error_type, errors in error_groups.items():
            print(f"{error_type}: {len(errors)} occurrences")
        
        # Get most common errors
        common_errors = aggregator.get_most_common(limit=5)
        for error, count in common_errors:
            print(f"Common error: {error} ({count} times)")
    
    return successful_results
```

## Best Practices

### 1. Use Specific Exception Types

```python
# Good: Catch specific exceptions
try:
    partner = await client.model(ResPartner).get(partner_id)
except NotFoundError:
    # Handle missing partner specifically
    partner = await create_default_partner()
except ValidationError as e:
    # Handle validation errors specifically
    partner = await fix_and_retry(partner_data, e)

# Avoid: Catching generic exceptions
try:
    partner = await client.model(ResPartner).get(partner_id)
except Exception:
    # Too broad - might catch unexpected errors
    pass
```

### 2. Provide Meaningful Error Messages

```python
# Good: Contextual error handling
try:
    await client.model(ResPartner).create(partner_data)
except ValidationError as e:
    raise ValidationError(
        f"Failed to create partner '{partner_data.get('name', 'Unknown')}': {e}"
    ) from e

# Avoid: Swallowing errors silently
try:
    await client.model(ResPartner).create(partner_data)
except ValidationError:
    pass  # Silent failure - hard to debug
```

### 3. Log Errors Appropriately

```python
import logging

logger = logging.getLogger(__name__)

# Good: Log with appropriate levels and context
try:
    partner = await client.model(ResPartner).create(partner_data)
except ValidationError as e:
    logger.warning(f"Validation error creating partner: {e}", extra={
        "partner_data": partner_data,
        "field_errors": e.field_errors
    })
except NetworkError as e:
    logger.error(f"Network error creating partner: {e}", extra={
        "partner_data": partner_data,
        "retry_after": getattr(e, 'retry_after', None)
    })
```

### 4. Implement Circuit Breakers for External Dependencies

```python
# Good: Use circuit breaker for unreliable operations
from zenoo_rpc.retry import CircuitBreaker

@CircuitBreaker(failure_threshold=5, recovery_timeout=30)
async def external_api_call():
    # This will stop calling after 5 failures
    return await client.model(ResPartner).search([])
```

## Next Steps

- Learn about [Retry Mechanisms](retry-mechanisms.md) for automatic error recovery
- Explore [Transactions](transactions.md) for error handling in transactions
- Check [Troubleshooting Guide](../troubleshooting/debugging.md) for debugging techniques
