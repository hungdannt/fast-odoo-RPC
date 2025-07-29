# Exceptions API Reference

Zenoo RPC provides a comprehensive exception hierarchy that maps JSON-RPC errors to meaningful Python exceptions with proper context and debugging information.

## Exception Hierarchy

```
ZenooError (Base)
├── ConnectionError
├── AuthenticationError
├── ValidationError
├── RequestTimeoutError
├── MethodNotFoundError
├── InternalError
├── TimeoutError
├── TransactionError (from zenoo_rpc.transaction.exceptions)
│   ├── TransactionRollbackError
│   ├── TransactionCommitError
│   ├── NestedTransactionError
│   └── TransactionStateError
├── CacheError (from zenoo_rpc.cache.exceptions)
│   ├── CacheBackendError
│   ├── CacheKeyError
│   ├── CacheConnectionError
│   ├── CacheSerializationError
│   └── CacheTimeoutError
├── BatchError (from zenoo_rpc.batch.exceptions)
│   ├── BatchExecutionError
│   ├── BatchValidationError
│   ├── BatchSizeError
│   └── BatchTimeoutError
└── RetryError (from zenoo_rpc.retry.exceptions)
    ├── MaxRetriesExceededError
    └── RetryTimeoutError
```

## Base Exception

### `ZenooError`

Base exception for all Zenoo RPC errors.

```python
class ZenooError(Exception):
    """Base exception for all Zenoo RPC errors."""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}
        
        # Additional context
        for key, value in kwargs.items():
            setattr(self, key, value)
```

**Attributes:**

- `message` (str): Error message
- `code` (int, optional): Error code from Odoo
- `data` (dict): Additional error data
- Custom attributes from kwargs

**Usage:**

```python
from zenoo_rpc.exceptions import ZenooError

try:
    await client.create("res.partner", invalid_data)
except ZenooError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.code}")
    print(f"Data: {e.data}")
```

## Connection Exceptions

### `ConnectionError`

Raised when connection to Odoo server fails.

```python
class ConnectionError(ZenooError):
    """Connection to Odoo server failed."""
    
    def __init__(
        self, 
        message: str, 
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.host = host
        self.port = port
```

**Common Causes:**

- Server is down or unreachable
- Network connectivity issues
- Firewall blocking connection
- Invalid host/port configuration

**Example:**

```python
from zenoo_rpc.exceptions import ConnectionError

try:
    client = ZenooClient("unreachable-server.com")
    await client.login("db", "user", "pass")
except ConnectionError as e:
    print(f"Cannot connect to {e.host}:{e.port}")
    print(f"Error: {e.message}")
```

### `RequestTimeoutError`

Raised when request times out.

```python
class RequestTimeoutError(ZenooError):
    """Request timed out."""
    
    def __init__(
        self, 
        message: str, 
        timeout: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout = timeout
```

**Example:**

```python
from zenoo_rpc.exceptions import RequestTimeoutError

try:
    # Long-running operation
    result = await client.search("res.partner", [])
except RequestTimeoutError as e:
    print(f"Request timed out after {e.timeout} seconds")
```

## Authentication Exceptions

### `AuthenticationError`

Raised when authentication fails.

```python
class AuthenticationError(ZenooError):
    """Authentication failed."""
    
    def __init__(
        self, 
        message: str, 
        database: Optional[str] = None,
        username: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.database = database
        self.username = username
```

**Common Causes:**

- Invalid username/password
- Database doesn't exist
- User account disabled
- Session expired

**Example:**

```python
from zenoo_rpc.exceptions import AuthenticationError

try:
    await client.login("demo", "admin", "wrong_password")
except AuthenticationError as e:
    print(f"Login failed for {e.username} on {e.database}")
    print(f"Error: {e.message}")
```

## Validation Exceptions

### `ValidationError`

Raised when data validation fails.

```python
class ValidationError(ZenooError):
    """Data validation failed."""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.model = model
```

**Common Causes:**

- Required field missing
- Invalid field value
- Constraint violation
- Format validation failure

**Example:**

```python
from zenoo_rpc.exceptions import ValidationError

try:
    await client.create("res.partner", {
        "name": "",  # Required field empty
        "email": "invalid-email"  # Invalid format
    })
except ValidationError as e:
    print(f"Validation failed for {e.model}.{e.field}")
    print(f"Value: {e.value}")
    print(f"Error: {e.message}")
```

## Access Exceptions

### `AccessError`

Raised when user lacks required permissions.

```python
class AccessError(ZenooError):
    """Access denied - insufficient permissions."""
    
    def __init__(
        self, 
        message: str, 
        model: Optional[str] = None,
        operation: Optional[str] = None,
        record_ids: Optional[List[int]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.model = model
        self.operation = operation
        self.record_ids = record_ids
```

**Common Causes:**

- User lacks read/write/create/delete permissions
- Record-level security rules
- Field-level access restrictions
- Group membership requirements

**Example:**

```python
from zenoo_rpc.exceptions import AccessError

try:
    await client.unlink("res.users", [1])  # Delete admin user
except AccessError as e:
    print(f"Access denied for {e.operation} on {e.model}")
    print(f"Record IDs: {e.record_ids}")
    print(f"Error: {e.message}")
```

## Transaction Exceptions

### `TransactionError`

Base exception for transaction-related errors.

```python
class TransactionError(ZenooError):
    """Base exception for transaction-related errors."""
    
    def __init__(
        self, 
        message: str, 
        transaction_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.transaction_id = transaction_id
```

### `TransactionRollbackError`

Raised when transaction rollback fails.

```python
class TransactionRollbackError(TransactionError):
    """Transaction rollback failed."""
    
    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        original_error: Optional[Exception] = None,
        failed_operations: Optional[List[Tuple[Any, Exception]]] = None,
        partial_rollback: bool = False,
        **kwargs,
    ):
        super().__init__(message, transaction_id=transaction_id, **kwargs)
        self.original_error = original_error
        self.failed_operations = failed_operations or []
        self.partial_rollback = partial_rollback
```

**Example:**

```python
from zenoo_rpc.transaction.exceptions import TransactionRollbackError
from zenoo_rpc.transaction.manager import TransactionManager

try:
    async with TransactionManager(client).transaction() as tx:
        await client.create("res.partner", data)
        raise Exception("Force rollback")
except TransactionRollbackError as e:
    print(f"Rollback failed for transaction {e.transaction_id}")
    print(f"Original error: {e.original_error}")
    print(f"Partial rollback: {e.partial_rollback}")
```

## Cache Exceptions

### `CacheError`

Base exception for cache-related errors.

```python
class CacheError(ZenooError):
    """Base exception for cache-related errors."""
```

### `CacheBackendError`

Raised when cache backend operation fails.

```python
class CacheBackendError(CacheError):
    """Cache backend operation failed."""
    
    def __init__(
        self, 
        message: str, 
        backend: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.backend = backend
        self.operation = operation
```

**Example:**

```python
from zenoo_rpc.cache.exceptions import CacheBackendError

try:
    await client.cache_manager.setup_redis_cache(
        url="redis://invalid-host:6379"
    )
except CacheBackendError as e:
    print(f"Cache backend '{e.backend}' failed: {e.message}")
    print(f"Operation: {e.operation}")
```

## Batch Exceptions

### `BatchError`

Base exception for batch operation errors.

```python
class BatchError(ZenooError):
    """Base exception for batch operation errors."""
```

### `BatchExecutionError`

Raised when batch execution fails.

```python
class BatchExecutionError(BatchError):
    """Batch execution failed."""
    
    def __init__(
        self, 
        message: str, 
        batch_id: Optional[str] = None,
        failed_operations: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.batch_id = batch_id
        self.failed_operations = failed_operations or []
```

**Example:**

```python
from zenoo_rpc.batch.exceptions import BatchExecutionError
from zenoo_rpc.batch.manager import BatchManager

try:
    batch_manager = BatchManager(client)
    # Use bulk operations directly (correct API)
    await batch_manager.bulk_create("res.partner", invalid_data)
except BatchExecutionError as e:
    print(f"Batch {e.batch_id} failed: {e.message}")
    for failed_op in e.failed_operations:
        print(f"Failed operation: {failed_op}")
```

## Retry Exceptions

### `RetryError`

Base exception for retry mechanism errors.

```python
class RetryError(ZenooError):
    """Base exception for retry mechanism errors."""
```

### `MaxRetriesExceededError`

Raised when maximum retry attempts exceeded.

```python
class MaxRetriesExceededError(RetryError):
    """Maximum retry attempts exceeded."""
    
    def __init__(
        self, 
        message: str, 
        max_attempts: Optional[int] = None,
        last_exception: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.max_attempts = max_attempts
        self.last_exception = last_exception
```

**Example:**

```python
from zenoo_rpc.retry.exceptions import MaxRetriesExceededError
from zenoo_rpc.retry.decorators import async_retry

@async_retry(max_attempts=3)
async def unreliable_operation():
    # Operation that might fail
    await client.search_read("res.partner", [])

try:
    await unreliable_operation()
except MaxRetriesExceededError as e:
    print(f"Failed after {e.max_attempts} attempts")
    print(f"Last error: {e.last_exception}")
```

## Error Mapping

### `map_jsonrpc_error()`

Maps JSON-RPC errors to appropriate Zenoo exceptions.

```python
def map_jsonrpc_error(error_data: Dict[str, Any]) -> ZenooError:
    """Map JSON-RPC error to appropriate Zenoo exception."""
    
    code = error_data.get("code", 0)
    message = error_data.get("message", "Unknown error")
    data = error_data.get("data", {})
    
    # Map based on error code and message
    if code == -32602:  # Invalid params
        return ValidationError(message, **data)
    elif "access" in message.lower():
        return AccessError(message, **data)
    elif "authentication" in message.lower():
        return AuthenticationError(message, **data)
    else:
        return ZenooError(message, code=code, data=data)
```

## Exception Handling Patterns

### Basic Error Handling

```python
from zenoo_rpc.exceptions import (
    ZenooError, 
    AuthenticationError, 
    ValidationError,
    AccessError
)

try:
    await client.login("demo", "admin", "admin")
    partner_id = await client.create("res.partner", data)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ValidationError as e:
    print(f"Data validation failed: {e}")
except AccessError as e:
    print(f"Access denied: {e}")
except ZenooError as e:
    print(f"Zenoo RPC error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Specific Error Handling

```python
from zenoo_rpc.exceptions import ValidationError

try:
    await client.create("res.partner", {
        "name": "Test Partner",
        "email": "invalid-email"
    })
except ValidationError as e:
    if e.field == "email":
        print("Please provide a valid email address")
    elif e.field == "name":
        print("Partner name is required")
    else:
        print(f"Validation error in {e.field}: {e.message}")
```

### Retry on Specific Errors

```python
from zenoo_rpc.exceptions import ConnectionError, RequestTimeoutError
import asyncio

async def robust_operation():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await client.search("res.partner", [])
        except (ConnectionError, RequestTimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Context-Aware Error Handling

```python
async def safe_partner_creation(partner_data):
    try:
        return await client.create("res.partner", partner_data)
    except ValidationError as e:
        # Handle validation errors gracefully
        if e.field == "email" and "duplicate" in e.message.lower():
            # Find existing partner with same email
            existing = await client.model(ResPartner).filter(
                email=partner_data["email"]
            ).first()
            return existing.id if existing else None
        else:
            # Re-raise other validation errors
            raise
    except AccessError:
        # Log access error but don't fail
        logger.warning(f"Access denied creating partner: {partner_data}")
        return None
```

## Custom Exceptions

### Creating Custom Exceptions

```python
class CustomBusinessError(ZenooError):
    """Custom business logic error."""
    
    def __init__(
        self, 
        message: str, 
        business_rule: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.business_rule = business_rule

# Usage
def validate_business_rules(partner_data):
    if partner_data.get("is_company") and not partner_data.get("vat"):
        raise CustomBusinessError(
            "Companies must have VAT number",
            business_rule="company_vat_required"
        )
```

## Debugging Tips

### Exception Context

```python
import traceback
from zenoo_rpc.exceptions import ZenooError

try:
    await client.create("res.partner", data)
except ZenooError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.code}")
    print(f"Data: {e.data}")
    print(f"Traceback: {traceback.format_exc()}")
```

### Logging Exceptions

```python
import logging
from zenoo_rpc.exceptions import ZenooError

logger = logging.getLogger(__name__)

try:
    await client.create("res.partner", data)
except ZenooError as e:
    logger.error(
        "Partner creation failed",
        extra={
            "error_code": e.code,
            "error_data": e.data,
            "partner_data": data
        },
        exc_info=True
    )
```

## Next Steps

- Learn about [Error Handling Patterns](../user-guide/error-handling.md)
- Explore [Retry Mechanisms](retry/index.md) for resilience
- Check [Logging and Debugging](../troubleshooting/debugging.md) guide
