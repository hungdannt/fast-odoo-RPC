# Retry Policies API Reference

Comprehensive retry policies with circuit breakers, timeout management, exception filtering, and graceful degradation for production-ready resilience patterns.

## Overview

Retry policies provide:

- **Exception Classification**: Automatic retryable vs non-retryable detection
- **Timeout Management**: Total operation timeout with circuit breaker integration
- **Circuit Breaker Support**: Fault tolerance patterns for external dependencies
- **Graceful Degradation**: Fallback mechanisms when retries are exhausted
- **Custom Conditions**: Flexible retry decision logic

## RetryPolicy Base Class

Comprehensive retry policy configuration with advanced features.

### Constructor

```python
@dataclass
class RetryPolicy:
    """Enhanced retry policy configuration."""
    
    strategy: RetryStrategy = field(default_factory=lambda: ExponentialBackoffStrategy())
    retryable_exceptions: Set[Type[Exception]] = field(default_factory=set)
    non_retryable_exceptions: Set[Type[Exception]] = field(default_factory=set)
    timeout: Optional[float] = None
    retry_condition: Optional[Callable[[Exception], bool]] = None
    
    # Enhanced features
    circuit_breaker_hook: Optional[Callable[[RetryContext], bool]] = None
    idempotency_check: Optional[Callable[[RetryContext], bool]] = None
    graceful_degradation: Optional[Callable[[RetryContext], Any]] = None
    max_total_delay: Optional[float] = None
    backoff_multiplier_on_failure: float = 1.0
    success_callback: Optional[Callable[[RetryContext], None]] = None
    failure_callback: Optional[Callable[[RetryContext], None]] = None
```

**Parameters:**

- `strategy` (RetryStrategy): Retry strategy to use
- `retryable_exceptions` (Set[Type[Exception]]): Exceptions that should trigger retry
- `non_retryable_exceptions` (Set[Type[Exception]]): Exceptions that should not retry
- `timeout` (Optional[float]): Total operation timeout in seconds
- `retry_condition` (Optional[Callable]): Custom retry condition function
- `circuit_breaker_hook` (Optional[Callable]): Circuit breaker integration
- `graceful_degradation` (Optional[Callable]): Fallback function when retries exhausted

### Decision Making

#### `make_retry_decision(context)`

Make comprehensive retry decision with enhanced context.

**Parameters:**

- `context` (RetryContext): Retry context with comprehensive information

**Returns:** `RetryDecision` - Decision indicating what action to take

**Example:**

```python
from zenoo_rpc.retry.policies import RetryPolicy, RetryContext, RetryDecision

policy = RetryPolicy()

# Create retry context
context = RetryContext(
    attempt_number=2,
    exception=ConnectionError("Network error"),
    start_time=time.time()
)

# Make decision
decision = policy.make_retry_decision(context)

if decision == RetryDecision.RETRY:
    print("Should retry")
elif decision == RetryDecision.STOP:
    print("Should stop retrying")
elif decision == RetryDecision.CIRCUIT_OPEN:
    print("Circuit breaker is open")
```

## Built-in Policies

### DefaultRetryPolicy

General-purpose retry policy for common scenarios.

```python
class DefaultRetryPolicy(RetryPolicy):
    """Default retry policy for common scenarios."""
    
    def __init__(self):
        # Retryable: ConnectionError, TimeoutError, OSError
        # Non-retryable: ValueError, TypeError, AttributeError, KeyError, IndexError
        # Strategy: ExponentialBackoff (3 attempts, 1s base, 2x multiplier, 30s max)
        # Timeout: 60 seconds
        super().__init__(
            strategy=ExponentialBackoffStrategy(max_attempts=3),
            timeout=60.0
        )
```

**Configuration:**

- **Max Attempts**: 3
- **Base Delay**: 1.0 seconds
- **Multiplier**: 2.0
- **Max Delay**: 30.0 seconds
- **Timeout**: 60 seconds
- **Jitter**: Enabled

**Example:**

```python
from zenoo_rpc.retry.policies import DefaultRetryPolicy
from zenoo_rpc.retry.decorators import async_retry
from zenoo_rpc.models.common import ResPartner

# Use default policy
@async_retry(policy=DefaultRetryPolicy())
async def reliable_operation():
    return await client.model(ResPartner).all()

# Delays: ~1s, ~2s, ~4s (with jitter)
```

### NetworkRetryPolicy

Specialized policy for network operations with HTTP-specific handling.

```python
class NetworkRetryPolicy(RetryPolicy):
    """Network-specific retry policy."""
    
    def __init__(self):
        # Retryable: ConnectionError, TimeoutError, OSError, httpx errors
        # Strategy: ExponentialBackoff (5 attempts, 0.5s base, 1.5x multiplier, 10s max)
        # Timeout: 30 seconds
        # Custom condition: HTTP 5xx errors are retryable
        super().__init__(
            strategy=ExponentialBackoffStrategy(max_attempts=5),
            timeout=30.0
        )
```

**Configuration:**

- **Max Attempts**: 5
- **Base Delay**: 0.5 seconds
- **Multiplier**: 1.5
- **Max Delay**: 10.0 seconds
- **Timeout**: 30 seconds
- **HTTP Handling**: 5xx errors are retryable, 4xx are not

**Example:**

```python
from zenoo_rpc.retry.policies import NetworkRetryPolicy

@async_retry(policy=NetworkRetryPolicy())
async def api_call():
    return await client.search("res.partner", [])

# Optimized for network operations
# Handles HTTP errors appropriately
```

### DatabaseRetryPolicy

Specialized policy for database operations with database-specific error handling.

```python
class DatabaseRetryPolicy(RetryPolicy):
    """Database-specific retry policy."""
    
    def __init__(self):
        # Retryable: ConnectionError, TimeoutError, OSError, psycopg2 errors
        # Strategy: ExponentialBackoff (3 attempts, 2s base, 2x multiplier, 60s max)
        # Timeout: 120 seconds
```

**Configuration:**

- **Max Attempts**: 3
- **Base Delay**: 2.0 seconds
- **Multiplier**: 2.0
- **Max Delay**: 60.0 seconds
- **Timeout**: 120 seconds
- **Database Errors**: Handles psycopg2 OperationalError, InterfaceError

**Example:**

```python
from zenoo_rpc.retry.policies import DatabaseRetryPolicy

@async_retry(policy=DatabaseRetryPolicy())
async def database_operation():
    return await client.create("res.partner", partner_data)

# Longer delays suitable for database recovery
# Handles database-specific exceptions
```

### QuickRetryPolicy

Fast retry policy for quick operations with minimal delay.

```python
class QuickRetryPolicy(RetryPolicy):
    """Quick retry policy for fast operations."""
    
    def __init__(self):
        # Strategy: ExponentialBackoff (2 attempts, 0.1s base, 2x multiplier, 1s max)
        # Timeout: 5 seconds
        # Jitter: Disabled for predictable timing
        super().__init__(
            strategy=ExponentialBackoffStrategy(max_attempts=2),
            timeout=5.0
        )
```

**Configuration:**

- **Max Attempts**: 2
- **Base Delay**: 0.1 seconds
- **Multiplier**: 2.0
- **Max Delay**: 1.0 seconds
- **Timeout**: 5 seconds
- **Jitter**: Disabled

**Example:**

```python
from zenoo_rpc.retry.policies import QuickRetryPolicy

@async_retry(policy=QuickRetryPolicy())
async def fast_operation():
    return await client.search_count("res.partner", [])

# Delays: 0.1s, 0.2s
# Total time: ~0.3s + operation time
```

### AggressiveRetryPolicy

Aggressive retry policy for critical operations with many attempts.

```python
class AggressiveRetryPolicy(RetryPolicy):
    """Aggressive retry policy for critical operations."""
    
    def __init__(self):
        # Strategy: ExponentialBackoff (10 attempts, 0.5s base, 1.2x multiplier, 30s max)
        # Timeout: 300 seconds (5 minutes)
```

**Configuration:**

- **Max Attempts**: 10
- **Base Delay**: 0.5 seconds
- **Multiplier**: 1.2 (slower growth)
- **Max Delay**: 30.0 seconds
- **Timeout**: 300 seconds (5 minutes)

**Example:**

```python
from zenoo_rpc.retry.policies import AggressiveRetryPolicy

@async_retry(policy=AggressiveRetryPolicy())
async def critical_operation():
    return await client.create("res.partner", critical_data)

# Many attempts with gradual backoff
# Suitable for critical business operations
```

## Advanced Policies

### CircuitBreakerRetryPolicy

Retry policy with integrated circuit breaker for fault tolerance.

```python
class CircuitBreakerRetryPolicy(RetryPolicy):
    """Retry policy with circuit breaker integration."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """Initialize circuit breaker retry policy."""
```

**Parameters:**

- `failure_threshold` (int): Failures before circuit opens (default: 5)
- `recovery_timeout` (float): Time before testing recovery (default: 60.0)
- `half_open_max_calls` (int): Max calls in half-open state (default: 3)

**Example:**

```python
from zenoo_rpc.retry.policies import CircuitBreakerRetryPolicy

# Circuit breaker for external service
circuit_policy = CircuitBreakerRetryPolicy(
    failure_threshold=3,
    recovery_timeout=30.0,
    half_open_max_calls=2
)

@async_retry(policy=circuit_policy)
async def external_service_call():
    return await client.external_api()

# Circuit states: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
```

### IdempotentRetryPolicy

Retry policy for idempotent operations with duplicate detection.

```python
class IdempotentRetryPolicy(RetryPolicy):
    """Retry policy for idempotent operations."""
    
    def __init__(
        self,
        idempotency_key_generator: Optional[Callable[[], str]] = None,
        idempotency_store: Optional[Dict[str, Any]] = None
    ):
        """Initialize idempotent retry policy."""
```

**Features:**

- Idempotency key generation
- Duplicate operation detection
- Safe retry for non-idempotent operations

**Example:**

```python
from zenoo_rpc.retry.policies import IdempotentRetryPolicy
import uuid

def generate_key():
    return str(uuid.uuid4())

idempotent_policy = IdempotentRetryPolicy(
    idempotency_key_generator=generate_key
)

@async_retry(policy=idempotent_policy)
async def idempotent_create():
    return await client.create("res.partner", data)

# Safe to retry without duplicates
```

### GracefulDegradationRetryPolicy

Retry policy with fallback mechanisms when retries are exhausted.

```python
class GracefulDegradationRetryPolicy(RetryPolicy):
    """Retry policy with graceful degradation."""
    
    def __init__(
        self,
        fallback_function: Optional[Callable[[RetryContext], Any]] = None,
        fallback_timeout: float = 10.0
    ):
        """Initialize graceful degradation retry policy."""
```

**Example:**

```python
from zenoo_rpc.retry.policies import GracefulDegradationRetryPolicy

def fallback_data(context):
    """Provide fallback data when retries fail."""
    return {"id": -1, "name": "Fallback Partner", "active": False}

fallback_policy = GracefulDegradationRetryPolicy(
    fallback_function=fallback_data
)

@async_retry(policy=fallback_policy)
async def get_partner_with_fallback():
    return await client.model(ResPartner).filter(id=123).first()

# Returns fallback data if all retries fail
```

## Custom Retry Conditions

### HTTP Status Code Handling

```python
def http_retry_condition(exception):
    """Custom retry condition for HTTP errors."""
    if hasattr(exception, 'response'):
        status_code = exception.response.status_code
        # Retry on 5xx server errors and 429 rate limit
        return status_code >= 500 or status_code == 429
    return True  # Retry other exceptions

policy = RetryPolicy(
    retry_condition=http_retry_condition,
    timeout=60.0
)
```

### Database Error Handling

```python
def database_retry_condition(exception):
    """Custom retry condition for database errors."""
    error_message = str(exception).lower()
    
    # Retry on connection issues
    if any(keyword in error_message for keyword in 
           ['connection', 'timeout', 'deadlock', 'lock']):
        return True
    
    # Don't retry on constraint violations
    if any(keyword in error_message for keyword in 
           ['unique', 'foreign key', 'check constraint']):
        return False
    
    return True  # Default to retry

db_policy = RetryPolicy(
    retry_condition=database_retry_condition,
    timeout=120.0
)
```

### Business Logic Conditions

```python
def business_retry_condition(exception):
    """Custom retry condition for business logic."""
    # Retry on temporary business errors
    if isinstance(exception, TemporaryBusinessError):
        return True
    
    # Don't retry on validation errors
    if isinstance(exception, ValidationError):
        return False
    
    # Don't retry on permission errors
    if isinstance(exception, PermissionError):
        return False
    
    return True

business_policy = RetryPolicy(
    retry_condition=business_retry_condition,
    timeout=30.0
)
```

## Policy Factory Functions

Convenience functions for creating common policy configurations.

### `create_network_policy()`

```python
def create_network_policy(
    max_attempts: int = 5,
    base_delay: float = 0.5,
    timeout: float = 30.0
) -> NetworkRetryPolicy:
    """Create a network retry policy with custom parameters."""
```

### `create_database_policy()`

```python
def create_database_policy(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    timeout: float = 120.0
) -> DatabaseRetryPolicy:
    """Create a database retry policy with custom parameters."""
```

### `create_circuit_breaker_policy()`

```python
def create_circuit_breaker_policy(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
) -> CircuitBreakerRetryPolicy:
    """Create a circuit breaker retry policy with custom parameters."""
```

**Example:**

```python
from zenoo_rpc.retry.policies import (
    create_network_policy,
    create_database_policy,
    create_circuit_breaker_policy
)

# Custom network policy
network_policy = create_network_policy(
    max_attempts=7,
    base_delay=1.0,
    timeout=45.0
)

# Custom database policy
db_policy = create_database_policy(
    max_attempts=5,
    base_delay=1.5,
    timeout=180.0
)

# Custom circuit breaker
circuit_policy = create_circuit_breaker_policy(
    failure_threshold=3,
    recovery_timeout=30.0
)
```

## Policy Composition

### Combining Policies

```python
class CompositeRetryPolicy(RetryPolicy):
    """Composite policy combining multiple policies."""
    
    def __init__(self, *policies: RetryPolicy):
        self.policies = policies
        # Use most restrictive settings
        super().__init__(
            timeout=min(p.timeout for p in policies if p.timeout),
            strategy=policies[0].strategy  # Use first strategy
        )
    
    def make_retry_decision(self, context):
        # All policies must agree to retry
        for policy in self.policies:
            decision = policy.make_retry_decision(context)
            if decision != RetryDecision.RETRY:
                return decision
        return RetryDecision.RETRY

# Combine network and circuit breaker policies
composite = CompositeRetryPolicy(
    NetworkRetryPolicy(),
    CircuitBreakerRetryPolicy()
)
```

### Conditional Policy Selection

```python
class ConditionalRetryPolicy(RetryPolicy):
    """Policy that selects strategy based on conditions."""
    
    def __init__(self):
        self.network_policy = NetworkRetryPolicy()
        self.database_policy = DatabaseRetryPolicy()
        self.default_policy = DefaultRetryPolicy()
    
    def make_retry_decision(self, context):
        # Select policy based on exception type
        if isinstance(context.exception, (ConnectionError, TimeoutError)):
            return self.network_policy.make_retry_decision(context)
        elif 'database' in str(context.exception).lower():
            return self.database_policy.make_retry_decision(context)
        else:
            return self.default_policy.make_retry_decision(context)

conditional_policy = ConditionalRetryPolicy()
```

## Best Practices

### 1. Choose Appropriate Policies

```python
# ✅ Good: Match policy to operation type
@async_retry(policy=NetworkRetryPolicy())
async def api_call():
    return await client.search("res.partner", [])

@async_retry(policy=DatabaseRetryPolicy())
async def database_write():
    return await client.create("res.partner", data)

@async_retry(policy=QuickRetryPolicy())
async def fast_check():
    return await client.search_count("res.partner", [])
```

### 2. Configure Timeouts Appropriately

```python
# ✅ Good: Set reasonable timeouts
quick_policy = QuickRetryPolicy()  # 5 seconds
network_policy = NetworkRetryPolicy()  # 30 seconds
database_policy = DatabaseRetryPolicy()  # 120 seconds
aggressive_policy = AggressiveRetryPolicy()  # 300 seconds

# ❌ Avoid: Infinite or very long timeouts without justification
```

### 3. Use Circuit Breakers for External Dependencies

```python
# ✅ Good: Circuit breaker for external services
external_policy = CircuitBreakerRetryPolicy(
    failure_threshold=5,
    recovery_timeout=60.0
)

@async_retry(policy=external_policy)
async def external_service():
    return await client.external_api()
```

### 4. Implement Graceful Degradation

```python
# ✅ Good: Provide fallback when retries fail
def fallback_function(context):
    logger.warning(f"Using fallback after {context.attempt_number} attempts")
    return default_data

graceful_policy = GracefulDegradationRetryPolicy(
    fallback_function=fallback_function
)
```

### 5. Monitor Policy Performance

```python
# ✅ Good: Monitor retry patterns
def success_callback(context):
    metrics.increment('retry.success', tags=[
        f'attempts:{context.attempt_number}',
        f'duration:{context.elapsed_time:.2f}'
    ])

def failure_callback(context):
    metrics.increment('retry.failure', tags=[
        f'attempts:{context.attempt_number}',
        f'exception:{type(context.exception).__name__}'
    ])

monitored_policy = RetryPolicy(
    success_callback=success_callback,
    failure_callback=failure_callback
)
```

## Next Steps

- Learn about [Retry Strategies](strategies.md) for backoff algorithms
- Explore [Retry Decorators](../decorators.md) for function-level retry logic
- Check [Circuit Breakers](../circuit-breakers.md) for fault tolerance patterns
