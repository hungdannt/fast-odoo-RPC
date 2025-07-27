# Retry Mechanisms

Zenoo RPC provides sophisticated retry mechanisms with exponential backoff, circuit breaker patterns, and intelligent failure handling to ensure reliable operations in unstable network conditions.

## Overview

The retry system includes:

- **Exponential Backoff**: Intelligent delay between retry attempts
- **Circuit Breaker**: Prevent cascading failures by temporarily stopping requests
- **Jitter**: Add randomness to prevent thundering herd problems
- **Conditional Retries**: Retry only on specific error types
- **Custom Strategies**: Implement your own retry logic

## Basic Retry Configuration

### Client-Level Retry Setup

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy
from zenoo_rpc.retry.policies import DefaultRetryPolicy

async with ZenooClient("localhost", port=8069) as client:
    # Setup retry mechanism with strategy
    retry_strategy = ExponentialBackoffStrategy(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        multiplier=2.0,
        jitter=True
    )

    # Create retry policy
    retry_policy = DefaultRetryPolicy()
    retry_policy.strategy = retry_strategy

    await client.login("my_database", "admin", "admin")
```

### Operation-Level Retries

```python
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.retry.decorators import async_retry
from zenoo_rpc.retry.policies import DefaultRetryPolicy

# Retry specific operations
@async_retry(policy=DefaultRetryPolicy())
async def create_partner_with_retry():
    return await client.create(
        "res.partner",
        {
            "name": "Test Partner",
            "email": "test@example.com"
        }
    )

# Use the retry decorator
partner_id = await create_partner_with_retry()
```

## Retry Strategies

### Exponential Backoff

```python
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy

# Configure exponential backoff
strategy = ExponentialBackoffStrategy(
    max_attempts=5,        # Maximum retry attempts
    base_delay=1.0,        # Initial delay in seconds
    max_delay=60.0,        # Maximum delay between attempts
    multiplier=2.0,        # Exponential multiplier
    jitter=True           # Add random jitter
)

# Use with retry policy
from zenoo_rpc.retry.policies import RetryPolicy
policy = RetryPolicy(strategy=strategy)
```

### Linear Backoff

```python
from zenoo_rpc.retry.strategies import LinearBackoffStrategy

# Configure linear backoff
strategy = LinearBackoffStrategy(
    max_attempts=3,
    base_delay=2.0,
    increment=1.0,  # Increase delay by 1 second each attempt
    jitter=False
)
```

### Fixed Delay

```python
from zenoo_rpc.retry.strategies import FixedDelayStrategy

# Configure fixed delay
strategy = FixedDelayStrategy(
    max_attempts=4,
    delay=5.0,  # Always wait 5 seconds between attempts
    jitter=True
)
```

### Custom Retry Strategy

```python
from zenoo_rpc.retry import RetryStrategy
import random

class CustomRetryStrategy(RetryStrategy):
    def __init__(self, max_attempts=3):
        self.max_attempts = max_attempts
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry based on attempt and exception"""
        if attempt >= self.max_attempts:
            return False
        
        # Only retry on specific exceptions
        from zenoo_rpc.exceptions import NetworkError, TimeoutError
        return isinstance(exception, (NetworkError, TimeoutError))
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt"""
        # Custom delay logic: fibonacci-like sequence
        if attempt <= 1:
            return 1.0
        return self.get_delay(attempt - 1) + self.get_delay(attempt - 2)

# Use custom strategy
await client.setup_retry_manager(strategy=CustomRetryStrategy(max_attempts=5))
```

## Circuit Breaker Pattern

### Basic Circuit Breaker

```python
from zenoo_rpc.retry import CircuitBreaker

# Configure circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,    # Open after 5 failures
    recovery_timeout=30.0,  # Try to recover after 30 seconds
    expected_exception=Exception
)

# Setup with client
await client.setup_retry_manager(
    strategy=ExponentialBackoff(),
    circuit_breaker=circuit_breaker
)
```

### Advanced Circuit Breaker

```python
from zenoo_rpc.retry import AdvancedCircuitBreaker
from zenoo_rpc.exceptions import NetworkError, ServerError

# Configure advanced circuit breaker
circuit_breaker = AdvancedCircuitBreaker(
    failure_threshold=10,
    recovery_timeout=60.0,
    half_open_max_calls=3,  # Test with 3 calls in half-open state
    expected_exceptions=[NetworkError, ServerError],  # Only break on these
    success_threshold=2     # Need 2 successes to close circuit
)

await client.setup_retry_manager(circuit_breaker=circuit_breaker)
```

### Circuit Breaker States

```python
# Check circuit breaker state
if client.retry_manager.circuit_breaker.is_open:
    print("Circuit breaker is open - requests will fail fast")
elif client.retry_manager.circuit_breaker.is_half_open:
    print("Circuit breaker is half-open - testing recovery")
else:
    print("Circuit breaker is closed - normal operation")

# Manual circuit breaker control
await client.retry_manager.circuit_breaker.open()   # Force open
await client.retry_manager.circuit_breaker.close()  # Force close
await client.retry_manager.circuit_breaker.reset()  # Reset to closed
```

## Conditional Retries

### Retry on Specific Exceptions

```python
from zenoo_rpc.retry import retry_on_exceptions
from zenoo_rpc.exceptions import NetworkError, TimeoutError, ServerError

@retry_on_exceptions(
    exceptions=[NetworkError, TimeoutError],  # Only retry these
    max_attempts=3,
    base_delay=2.0
)
async def network_sensitive_operation():
    return await client.model(ResPartner).filter(is_company=True).all()

# ServerError won't be retried, but NetworkError will
try:
    partners = await network_sensitive_operation()
except ServerError:
    print("Server error - no retry attempted")
```

### Conditional Retry Logic

```python
from zenoo_rpc.retry import ConditionalRetry

def should_retry_condition(exception: Exception, attempt: int) -> bool:
    """Custom condition for retrying"""
    # Don't retry validation errors
    if isinstance(exception, ValidationError):
        return False
    
    # Don't retry after 3 attempts on weekends
    if datetime.now().weekday() >= 5 and attempt >= 3:
        return False
    
    # Retry network issues
    return isinstance(exception, (NetworkError, TimeoutError))

@ConditionalRetry(
    condition=should_retry_condition,
    max_attempts=5,
    base_delay=1.0
)
async def conditional_operation():
    return await client.model(ResPartner).create({
        "name": "Test Partner",
        "email": "test@example.com"
    })
```

## Retry with Context

### Retry Context Information

```python
from zenoo_rpc.retry import RetryContext

@retry_on_failure(max_attempts=3)
async def operation_with_context():
    # Access retry context within the operation
    context = RetryContext.current()
    
    if context:
        print(f"Attempt {context.attempt} of {context.max_attempts}")
        print(f"Previous exception: {context.last_exception}")
        print(f"Total elapsed time: {context.elapsed_time}")
    
    return await client.model(ResPartner).search([])

# The context is automatically available during retries
partners = await operation_with_context()
```

### Retry with State

```python
class StatefulRetry:
    def __init__(self):
        self.attempt_count = 0
        self.start_time = None
    
    @retry_on_failure(max_attempts=5, base_delay=1.0)
    async def operation_with_state(self):
        self.attempt_count += 1
        if self.start_time is None:
            self.start_time = datetime.now()
        
        print(f"Attempt {self.attempt_count}, elapsed: {datetime.now() - self.start_time}")
        
        # Your actual operation
        return await client.model(ResPartner).create({
            "name": f"Partner {self.attempt_count}",
            "email": f"partner{self.attempt_count}@example.com"
        })

# Usage
retry_handler = StatefulRetry()
partner = await retry_handler.operation_with_state()
```

## Monitoring and Metrics

### Retry Metrics Collection

```python
from zenoo_rpc.retry import RetryMetrics

# Enable metrics collection
await client.setup_retry_manager(
    strategy=ExponentialBackoff(),
    collect_metrics=True
)

# Access metrics after operations
metrics = client.retry_manager.get_metrics()
print(f"Total retry attempts: {metrics.total_attempts}")
print(f"Successful retries: {metrics.successful_retries}")
print(f"Failed retries: {metrics.failed_retries}")
print(f"Average retry delay: {metrics.average_delay}")
print(f"Circuit breaker opens: {metrics.circuit_breaker_opens}")
```

### Custom Metrics Callback

```python
def retry_metrics_callback(event: str, context: dict):
    """Custom callback for retry events"""
    if event == "retry_attempt":
        print(f"Retry attempt {context['attempt']} for {context['operation']}")
    elif event == "retry_success":
        print(f"Retry succeeded after {context['attempts']} attempts")
    elif event == "retry_failed":
        print(f"Retry failed after {context['attempts']} attempts")
    elif event == "circuit_breaker_opened":
        print("Circuit breaker opened due to failures")

# Set callback
await client.setup_retry_manager(
    strategy=ExponentialBackoff(),
    metrics_callback=retry_metrics_callback
)
```

## Advanced Patterns

### Retry with Fallback

```python
from zenoo_rpc.retry import retry_with_fallback

@retry_with_fallback(
    max_attempts=3,
    fallback_value=[]  # Return empty list if all retries fail
)
async def get_partners_with_fallback():
    return await client.model(ResPartner).filter(is_company=True).all()

# Will return empty list if all retries fail
partners = await get_partners_with_fallback()
```

### Retry with Timeout

```python
import asyncio
from zenoo_rpc.retry import retry_with_timeout

@retry_with_timeout(
    max_attempts=5,
    base_delay=1.0,
    total_timeout=30.0  # Give up after 30 seconds total
)
async def time_limited_operation():
    return await client.model(ResPartner).search([])

try:
    partners = await time_limited_operation()
except asyncio.TimeoutError:
    print("Operation timed out after 30 seconds")
```

### Bulk Operation Retries

```python
from zenoo_rpc.retry import BulkRetryManager

async def retry_bulk_operations():
    bulk_retry = BulkRetryManager(
        max_attempts=3,
        base_delay=2.0,
        partial_success_threshold=0.8  # Succeed if 80% of operations succeed
    )
    
    operations = [
        lambda: client.model(ResPartner).create({"name": f"Partner {i}"})
        for i in range(100)
    ]
    
    results = await bulk_retry.execute_bulk(operations)
    
    print(f"Successful: {len(results.successful)}")
    print(f"Failed: {len(results.failed)}")
    
    return results
```

## Error Handling

### Retry Exception Handling

```python
from zenoo_rpc.exceptions import RetryExhaustedError, CircuitBreakerOpenError

try:
    partner = await client.model(ResPartner).create({
        "name": "Test Partner",
        "email": "test@example.com"
    })
    
except RetryExhaustedError as e:
    print(f"All retry attempts failed: {e}")
    print(f"Last exception: {e.last_exception}")
    print(f"Total attempts: {e.attempts}")
    
except CircuitBreakerOpenError:
    print("Circuit breaker is open - operation not attempted")
```

### Graceful Degradation

```python
async def resilient_partner_lookup(partner_id: int):
    """Lookup partner with graceful degradation"""
    try:
        # Try with retries
        return await client.model(ResPartner).get(partner_id)
        
    except RetryExhaustedError:
        # Fall back to cached data
        cached_partner = await client.cache_manager.get(f"partner_{partner_id}")
        if cached_partner:
            return cached_partner
        
        # Final fallback - return minimal partner object
        return ResPartner(id=partner_id, name="Unknown Partner")
```

## Best Practices

### 1. Choose Appropriate Retry Strategies

```python
# Good: Use exponential backoff for network operations
await client.setup_retry_manager(
    strategy=ExponentialBackoff(max_attempts=5, jitter=True)
)

# Good: Use fixed delay for rate-limited APIs
await client.setup_retry_manager(
    strategy=FixedDelay(max_attempts=3, delay=60.0)  # Wait 1 minute
)
```

### 2. Implement Circuit Breakers for External Dependencies

```python
# Good: Use circuit breaker for external service calls
await client.setup_retry_manager(
    strategy=ExponentialBackoff(),
    circuit_breaker=CircuitBreaker(failure_threshold=5)
)
```

### 3. Don't Retry Everything

```python
# Good: Only retry transient failures
@retry_on_exceptions(
    exceptions=[NetworkError, TimeoutError],  # Transient errors
    max_attempts=3
)
async def network_operation():
    return await client.model(ResPartner).search([])

# Avoid: Retrying validation errors
# ValidationError should not be retried as it won't succeed
```

### 4. Monitor Retry Behavior

```python
# Good: Collect and monitor retry metrics
await client.setup_retry_manager(
    strategy=ExponentialBackoff(),
    collect_metrics=True,
    metrics_callback=log_retry_metrics
)
```

### 5. Set Reasonable Timeouts

```python
# Good: Set total timeout to prevent infinite retries
@retry_with_timeout(
    max_attempts=5,
    total_timeout=60.0  # Don't retry for more than 1 minute
)
async def time_bounded_operation():
    return await client.model(ResPartner).search([])
```

## Next Steps

- Learn about [Error Handling](error-handling.md) for comprehensive exception management
- Explore [Transactions](transactions.md) for retry behavior within transactions
- Check [Performance Optimization](../tutorials/performance-optimization.md) for retry performance tuning
