# Retry API Reference

The retry module provides advanced retry logic with exponential backoff, jitter, circuit breaker integration, and comprehensive error handling for resilient operations.

## Overview

The retry system consists of:

- **Retry Strategies**: ExponentialBackoffStrategy, LinearBackoffStrategy, FixedDelayStrategy, AdaptiveStrategy
- **Retry Policies**: DefaultRetryPolicy, NetworkRetryPolicy, DatabaseRetryPolicy
- **Decorators**: @async_retry, @retry for function-level retry logic
- **Circuit Breakers**: Fault tolerance patterns for external dependencies
- **Error Classification**: Automatic retryable vs non-retryable error detection

## Retry Strategies

### ExponentialBackoffStrategy

Exponential backoff with configurable multiplier and jitter.

```python
class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff retry strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize exponential backoff strategy."""
```

**Parameters:**

- `max_attempts` (int): Maximum retry attempts (default: 3)
- `base_delay` (float): Initial delay in seconds (default: 1.0)
- `multiplier` (float): Exponential multiplier (default: 2.0)
- `max_delay` (float): Maximum delay between attempts (default: 60.0)
- `jitter` (bool): Add random jitter to delays (default: True)
- `jitter_type` (str): Jitter algorithm ("full", "equal", "decorr") (default: "full")

**Example:**

```python
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy

# Basic exponential backoff
strategy = ExponentialBackoffStrategy(
    max_attempts=5,
    base_delay=1.0,
    multiplier=2.0,
    max_delay=60.0,
    jitter=True
)

# Delays: ~1s, ~2s, ~4s, ~8s, ~16s (with jitter)
```

### LinearBackoffStrategy

Linear backoff with fixed increment.

```python
class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """Initialize linear backoff strategy."""
```

**Example:**

```python
from zenoo_rpc.retry.strategies import LinearBackoffStrategy

strategy = LinearBackoffStrategy(
    max_attempts=5,
    base_delay=2.0,
    increment=3.0,
    max_delay=30.0
)

# Delays: 2s, 5s, 8s, 11s, 14s
```

### FixedDelayStrategy

Fixed delay between retry attempts.

```python
class FixedDelayStrategy(RetryStrategy):
    """Fixed delay retry strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        jitter: bool = False
    ):
        """Initialize fixed delay strategy."""
```

**Example:**

```python
from zenoo_rpc.retry.strategies import FixedDelayStrategy

# Good for rate-limited APIs
strategy = FixedDelayStrategy(
    max_attempts=3,
    delay=60.0,  # Wait 1 minute between attempts
    jitter=False
)
```

### AdaptiveStrategy

Adaptive strategy that adjusts based on success rate.

```python
class AdaptiveStrategy(RetryStrategy):
    """Adaptive retry strategy based on success rate."""
    
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        success_threshold: float = 0.8,
        adaptation_window: int = 100,
        min_samples: int = 10
    ):
        """Initialize adaptive strategy."""
```

**Features:**

- Adjusts delay based on recent success rate
- Conservative backoff with insufficient data
- Aggressive backoff when success rate is low
- Minimal backoff when success rate is high

**Example:**

```python
from zenoo_rpc.retry.strategies import AdaptiveStrategy

strategy = AdaptiveStrategy(
    max_attempts=5,
    base_delay=1.0,
    success_threshold=0.8,  # Adapt when success rate < 80%
    adaptation_window=100,  # Consider last 100 attempts
    min_samples=10         # Need 10 samples before adapting
)
```

## Retry Policies

### DefaultRetryPolicy

General-purpose retry policy for common scenarios.

```python
class DefaultRetryPolicy(RetryPolicy):
    """Default retry policy for common scenarios."""
    
    def __init__(self):
        # Retryable: ConnectionError, TimeoutError, OSError
        # Non-retryable: ValueError, TypeError, AttributeError
        # Strategy: ExponentialBackoff (3 attempts, 1s base, 2x multiplier)
        # Timeout: 60 seconds
```

**Example:**

```python
from zenoo_rpc.retry.policies import DefaultRetryPolicy
from zenoo_rpc.models.common import ResPartner

policy = DefaultRetryPolicy()

# Use with decorator
from zenoo_rpc.retry.decorators import async_retry

@async_retry(policy=policy)
async def reliable_operation():
    return await client.model(ResPartner).all()
```

### NetworkRetryPolicy

Specialized policy for network operations.

```python
class NetworkRetryPolicy(RetryPolicy):
    """Network-specific retry policy."""
    
    def __init__(self):
        # Retryable: ConnectionError, TimeoutError, OSError, HTTPError (5xx)
        # Strategy: ExponentialBackoff (5 attempts, 2s base, 2x multiplier)
        # Timeout: 120 seconds
```

**Example:**

```python
from zenoo_rpc.retry.policies import NetworkRetryPolicy

@async_retry(policy=NetworkRetryPolicy())
async def network_operation():
    return await client.search("res.partner", [])
```

### DatabaseRetryPolicy

Specialized policy for database operations.

```python
class DatabaseRetryPolicy(RetryPolicy):
    """Database-specific retry policy."""
    
    def __init__(self):
        # Retryable: ConnectionError, TimeoutError, DatabaseError
        # Strategy: ExponentialBackoff (3 attempts, 2s base, 1.5x multiplier)
        # Timeout: 180 seconds
```

**Example:**

```python
from zenoo_rpc.retry.policies import DatabaseRetryPolicy

@async_retry(policy=DatabaseRetryPolicy())
async def database_operation():
    return await client.create("res.partner", partner_data)
```

### QuickRetryPolicy

Fast retry policy for quick operations.

```python
class QuickRetryPolicy(RetryPolicy):
    """Quick retry policy for fast operations."""
    
    def __init__(self):
        # Strategy: ExponentialBackoff (2 attempts, 0.1s base, 2x multiplier)
        # Max delay: 1 second
        # Timeout: 5 seconds
```

### AggressiveRetryPolicy

Aggressive retry policy for critical operations.

```python
class AggressiveRetryPolicy(RetryPolicy):
    """Aggressive retry policy for critical operations."""
    
    def __init__(self):
        # Strategy: ExponentialBackoff (10 attempts, 0.5s base, 1.2x multiplier)
        # Timeout: 300 seconds (5 minutes)
```

## Retry Decorators

### `@async_retry`

Comprehensive async retry decorator with advanced features.

```python
def async_retry(
    policy: Optional[RetryPolicy] = None,
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff_multiplier: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Optional[Union[Type[Exception], tuple]] = None,
    on_retry: Optional[Callable[[RetryAttempt], None]] = None,
    timeout: Optional[float] = None
) -> Callable:
    """Enhanced async retry decorator."""
```

**Parameters:**

- `policy` (RetryPolicy, optional): Retry policy to use
- `max_attempts` (int, optional): Override max attempts
- `delay` (float, optional): Override base delay
- `backoff_multiplier` (float, optional): Override multiplier
- `max_delay` (float, optional): Override max delay
- `exceptions` (Exception types, optional): Specific exceptions to retry
- `on_retry` (Callable, optional): Callback on each retry
- `timeout` (float, optional): Total operation timeout

**Example:**

```python
from zenoo_rpc.retry.decorators import async_retry
from zenoo_rpc.exceptions import ConnectionError, RequestTimeoutError

# Basic retry
@async_retry(max_attempts=3, delay=1.0)
async def basic_operation():
    return await client.model(ResPartner).all()

# Advanced retry with policy
@async_retry(
    policy=NetworkRetryPolicy(),
    exceptions=(ConnectionError, RequestTimeoutError),
    timeout=60.0
)
async def network_operation():
    return await client.search("res.partner", [])

# Retry with callback
def retry_callback(attempt):
    print(f"Retry attempt {attempt.number}/{attempt.max_attempts}")
    print(f"Last error: {attempt.last_exception}")
    print(f"Next delay: {attempt.next_delay}s")

@async_retry(
    max_attempts=5,
    delay=2.0,
    on_retry=retry_callback
)
async def monitored_operation():
    return await client.create("res.partner", data)
```

### Convenience Decorators

#### `@network_retry`

```python
from zenoo_rpc.retry.decorators import network_retry

@network_retry(max_attempts=5, base_delay=2.0)
async def api_call():
    return await client.model(ResPartner).all()
```

#### `@database_retry`

```python
from zenoo_rpc.retry.decorators import database_retry

@database_retry(max_attempts=3, base_delay=2.0, max_delay=60.0)
async def db_operation():
    return await client.create("res.partner", data)
```

#### `@quick_retry`

```python
from zenoo_rpc.retry.decorators import quick_retry

@quick_retry(max_attempts=2)
async def fast_operation():
    return await client.search_count("res.partner", [])
```

## Circuit Breaker Integration

### Basic Circuit Breaker

```python
from zenoo_rpc.retry.circuit_breaker import CircuitBreaker

# Configure circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,    # Open after 5 failures
    recovery_timeout=30.0,  # Try to recover after 30 seconds
    expected_exception=Exception
)

# Use with retry policy
policy = DefaultRetryPolicy()
policy.circuit_breaker = circuit_breaker

@async_retry(policy=policy)
async def protected_operation():
    return await client.model(ResPartner).all()
```

### Advanced Circuit Breaker

```python
from zenoo_rpc.retry.circuit_breaker import AdvancedCircuitBreaker
from zenoo_rpc.exceptions import ConnectionError, RequestTimeoutError

circuit_breaker = AdvancedCircuitBreaker(
    failure_threshold=10,
    recovery_timeout=60.0,
    half_open_max_calls=3,  # Test with 3 calls in half-open state
    expected_exceptions=[ConnectionError, RequestTimeoutError],
    success_threshold=2     # Need 2 successes to close circuit
)
```

## Error Classification

### Automatic Error Classification

```python
from zenoo_rpc.retry.policies import RetryPolicy

# Custom policy with error classification
class CustomRetryPolicy(RetryPolicy):
    def __init__(self):
        retryable_exceptions = {
            ConnectionError,
            RequestTimeoutError,
            # Add custom retryable exceptions
        }
        
        non_retryable_exceptions = {
            ValidationError,
            AuthenticationError,
            # Add custom non-retryable exceptions
        }
        
        super().__init__(
            strategy=ExponentialBackoffStrategy(),
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions
        )
```

### Custom Retry Conditions

```python
def custom_retry_condition(exception, attempt):
    """Custom retry condition function."""
    # Retry on specific HTTP status codes
    if hasattr(exception, 'status_code'):
        return exception.status_code in [429, 502, 503, 504]
    
    # Retry on connection issues
    if isinstance(exception, ConnectionError):
        return True
    
    # Don't retry on authentication errors
    if isinstance(exception, AuthenticationError):
        return False
    
    # Default behavior
    return attempt.number < 3

@async_retry(retry_condition=custom_retry_condition)
async def custom_operation():
    return await client.model(ResPartner).all()
```

## Advanced Patterns

### Retry with Fallback

```python
from zenoo_rpc.retry.decorators import async_retry
from zenoo_rpc.retry.exceptions import MaxRetriesExceededError

@async_retry(max_attempts=3)
async def get_partners_with_fallback():
    try:
        return await client.model(ResPartner).filter(is_company=True).all()
    except MaxRetriesExceededError:
        return []  # Return empty list if all retries fail

# Will return empty list if all retries fail
partners = await get_partners_with_fallback()
```

### Retry with Timeout

```python
import asyncio
from zenoo_rpc.retry.decorators import async_retry

@async_retry(max_attempts=5, delay=1.0)
async def time_limited_operation():
    return await client.model(ResPartner).all()

try:
    # Use asyncio.wait_for for timeout control
    partners = await asyncio.wait_for(time_limited_operation(), timeout=30.0)
except asyncio.TimeoutError:
    print("Operation timed out after 30 seconds")
```

### Bulk Operation Retries

```python
from zenoo_rpc.retry.bulk import BulkRetryManager

async def retry_bulk_operations():
    bulk_retry = BulkRetryManager(
        max_attempts=3,
        base_delay=2.0,
        partial_success_threshold=0.8  # Succeed if 80% of operations succeed
    )
    
    operations = [
        lambda: client.create("res.partner", {"name": f"Partner {i}"})
        for i in range(100)
    ]
    
    results = await bulk_retry.execute_bulk(operations)
    
    print(f"Successful: {len(results.successful)}")
    print(f"Failed: {len(results.failed)}")
    
    return results
```

## Monitoring and Observability

### Retry Metrics

```python
from zenoo_rpc.retry.metrics import RetryMetrics

# Enable retry metrics
metrics = RetryMetrics()

@async_retry(
    max_attempts=3,
    metrics=metrics
)
async def monitored_operation():
    return await client.model(ResPartner).search([])

# Get metrics
stats = metrics.get_stats()
print(f"Total attempts: {stats['total_attempts']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average retries: {stats['average_retries']:.1f}")
```

### Retry Events

```python
from zenoo_rpc.retry.events import RetryEventHandler

class CustomRetryEventHandler(RetryEventHandler):
    def on_retry_start(self, attempt):
        print(f"Starting retry attempt {attempt.number}")
    
    def on_retry_success(self, attempt):
        print(f"Retry succeeded after {attempt.number} attempts")
    
    def on_retry_failure(self, attempt):
        print(f"Retry failed: {attempt.last_exception}")
    
    def on_max_retries_exceeded(self, attempt):
        print(f"Max retries exceeded after {attempt.number} attempts")

# Use event handler
event_handler = CustomRetryEventHandler()

@async_retry(
    max_attempts=3,
    event_handler=event_handler
)
async def event_monitored_operation():
    return await client.model(ResPartner).all()
```

## Error Handling

### Retry Exceptions

```python
from zenoo_rpc.retry.exceptions import (
    RetryError,
    MaxRetriesExceededError,
    RetryTimeoutError
)

try:
    @async_retry(max_attempts=3, timeout=30.0)
    async def failing_operation():
        raise ConnectionError("Network error")
    
    result = await failing_operation()
    
except MaxRetriesExceededError as e:
    print(f"Failed after {e.max_attempts} attempts")
    print(f"Last error: {e.last_exception}")
    
except RetryTimeoutError as e:
    print(f"Operation timed out after {e.timeout} seconds")
    
except RetryError as e:
    print(f"Retry error: {e}")
```

## Best Practices

### 1. Choose Appropriate Strategies

```python
# ✅ Good: Exponential backoff for transient failures
@async_retry(
    strategy=ExponentialBackoffStrategy(max_attempts=5, base_delay=1.0),
    exceptions=(ConnectionError, RequestTimeoutError)
)
async def network_operation():
    return await client.search("res.partner", [])

# ✅ Good: Fixed delay for rate-limited APIs
@async_retry(
    strategy=FixedDelayStrategy(max_attempts=3, delay=60.0),
    exceptions=(RateLimitError,)
)
async def rate_limited_operation():
    return await client.api_call()
```

### 2. Use Circuit Breakers for External Dependencies

```python
# ✅ Good: Circuit breaker for external services
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

@async_retry(
    policy=NetworkRetryPolicy(),
    circuit_breaker=circuit_breaker
)
async def external_service_call():
    return await client.external_api()
```

### 3. Don't Retry Everything

```python
# ✅ Good: Only retry transient failures
@async_retry(
    exceptions=(ConnectionError, RequestTimeoutError),  # Transient errors
    max_attempts=3
)
async def selective_retry():
    return await client.model(ResPartner).all()

# ❌ Avoid: Retrying non-transient errors
@async_retry(max_attempts=3)  # Will retry ValidationError, etc.
async def bad_retry():
    return await client.create("res.partner", invalid_data)
```

### 4. Monitor Retry Behavior

```python
# ✅ Good: Monitor retry patterns
def log_retry_attempt(attempt):
    logger.warning(
        f"Retry {attempt.number}/{attempt.max_attempts}: {attempt.last_exception}"
    )

@async_retry(
    max_attempts=3,
    on_retry=log_retry_attempt
)
async def monitored_operation():
    return await client.model(ResPartner).all()
```

## Next Steps

- Learn about [Retry Strategies](strategies.md) in detail
- Explore [Retry Policies](policies.md) configuration
- Check [Circuit Breakers](circuit-breakers.md) patterns
- Understand [Error Classification](error-classification.md) logic
