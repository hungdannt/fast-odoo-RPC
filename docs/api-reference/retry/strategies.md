# Retry Strategies API Reference

Advanced retry strategies with exponential backoff, linear progression, adaptive algorithms, and sophisticated jitter implementations for resilient distributed systems.

## Overview

Retry strategies provide:

- **Backoff Algorithms**: Exponential, linear, fixed, Fibonacci, decorrelated jitter
- **Adaptive Behavior**: Success rate-based strategy adjustment
- **Jitter Implementation**: Full, equal, decorrelated jitter algorithms
- **Thread Safety**: Concurrent access support for adaptive strategies
- **Performance Optimization**: Efficient delay calculations with caching

## RetryStrategy Base Class

Abstract base class for all retry strategies with common functionality.

### Constructor

```python
class RetryStrategy(ABC):
    """Abstract base class for retry strategies."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize retry strategy."""
```

**Parameters:**

- `max_attempts` (int): Maximum number of retry attempts (default: 3)
- `max_delay` (float): Maximum delay between attempts in seconds (default: 60.0)
- `jitter` (bool): Whether to add random jitter to delays (default: True)
- `jitter_type` (str): Type of jitter algorithm ("full", "equal", "decorrelated")

### Abstract Methods

#### `calculate_delay(attempt)`

Calculate base delay for given attempt number.

**Parameters:**

- `attempt` (int): Attempt number (1-based)

**Returns:** `float` - Base delay in seconds

#### `get_delay(attempt)`

Get final delay with jitter applied.

**Parameters:**

- `attempt` (int): Attempt number (1-based)

**Returns:** `float` - Final delay in seconds with jitter

### Jitter Algorithms

#### Full Jitter

```python
# Full jitter: delay = random(0, base_delay)
def _apply_full_jitter(self, base_delay: float) -> float:
    return random.uniform(0, base_delay)
```

#### Equal Jitter

```python
# Equal jitter: delay = base_delay/2 + random(0, base_delay/2)
def _apply_equal_jitter(self, base_delay: float) -> float:
    half_delay = base_delay / 2
    return half_delay + random.uniform(0, half_delay)
```

#### Decorrelated Jitter

```python
# Decorrelated jitter: delay = random(base_delay, previous_delay * 3)
def _apply_decorrelated_jitter(self, base_delay: float) -> float:
    # Implementation varies by strategy
    pass
```

## ExponentialBackoffStrategy

Exponential backoff with configurable multiplier and advanced jitter support.

### Constructor

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

- `base_delay` (float): Initial delay in seconds (default: 1.0)
- `multiplier` (float): Exponential multiplier (default: 2.0)

**Algorithm:** `delay = base_delay * multiplier^(attempt-1)`

### Usage Examples

#### Basic Exponential Backoff

```python
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy

# Standard exponential backoff
strategy = ExponentialBackoffStrategy(
    max_attempts=5,
    base_delay=1.0,
    multiplier=2.0,
    max_delay=60.0,
    jitter=True
)

# Calculate delays
for attempt in range(1, 6):
    delay = strategy.get_delay(attempt)
    print(f"Attempt {attempt}: {delay:.2f}s")

# Output (with jitter):
# Attempt 1: 0.73s  (base: 1.0s)
# Attempt 2: 1.45s  (base: 2.0s)
# Attempt 3: 2.89s  (base: 4.0s)
# Attempt 4: 6.12s  (base: 8.0s)
# Attempt 5: 11.34s (base: 16.0s)
```

#### Conservative Exponential Backoff

```python
# Conservative backoff for critical operations
conservative_strategy = ExponentialBackoffStrategy(
    max_attempts=3,
    base_delay=2.0,
    multiplier=1.5,  # Slower growth
    max_delay=30.0,
    jitter=False     # Predictable delays
)

# Delays: 2.0s, 3.0s, 4.5s
```

#### Aggressive Exponential Backoff

```python
# Aggressive backoff for transient failures
aggressive_strategy = ExponentialBackoffStrategy(
    max_attempts=7,
    base_delay=0.5,
    multiplier=3.0,  # Rapid growth
    max_delay=120.0,
    jitter=True,
    jitter_type="equal"
)

# Base delays: 0.5s, 1.5s, 4.5s, 13.5s, 40.5s, 121.5s (capped), 121.5s (capped)
```

## LinearBackoffStrategy

Linear backoff with fixed increment per attempt.

### Constructor

```python
class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        """Initialize linear backoff strategy."""
```

**Parameters:**

- `base_delay` (float): Initial delay in seconds (default: 1.0)
- `increment` (float): Linear increment per attempt (default: 1.0)

**Algorithm:** `delay = base_delay + increment * (attempt-1)`

### Usage Examples

#### Basic Linear Backoff

```python
from zenoo_rpc.retry.strategies import LinearBackoffStrategy

# Standard linear backoff
strategy = LinearBackoffStrategy(
    max_attempts=5,
    base_delay=2.0,
    increment=3.0,
    max_delay=30.0,
    jitter=True
)

# Base delays: 2.0s, 5.0s, 8.0s, 11.0s, 14.0s
```

#### Rate-Limited API Backoff

```python
# For APIs with rate limiting
rate_limit_strategy = LinearBackoffStrategy(
    max_attempts=4,
    base_delay=60.0,    # Start with 1 minute
    increment=30.0,     # Add 30 seconds each attempt
    max_delay=300.0,    # Cap at 5 minutes
    jitter=False        # Predictable for rate limits
)

# Delays: 60s, 90s, 120s, 150s
```

## FixedDelayStrategy

Fixed delay between all retry attempts.

### Constructor

```python
class FixedDelayStrategy(RetryStrategy):
    """Fixed delay retry strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize fixed delay strategy."""
```

**Parameters:**

- `delay` (float): Fixed delay in seconds (default: 1.0)

**Algorithm:** `delay = fixed_delay`

### Usage Examples

#### Basic Fixed Delay

```python
from zenoo_rpc.retry.strategies import FixedDelayStrategy

# Fixed 5-second delays
strategy = FixedDelayStrategy(
    max_attempts=4,
    delay=5.0,
    jitter=True
)

# All delays: ~5.0s (with jitter variation)
```

#### Database Connection Retry

```python
# Database connection with fixed intervals
db_strategy = FixedDelayStrategy(
    max_attempts=3,
    delay=10.0,     # Wait 10 seconds between attempts
    jitter=False    # Consistent timing
)
```

## AdaptiveStrategy

Adaptive strategy that adjusts behavior based on success rate with thread-safe statistics.

### Constructor

```python
class AdaptiveStrategy(RetryStrategy):
    """Adaptive retry strategy based on success rate."""
    
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full",
        success_threshold: float = 0.8,
        adaptation_window: int = 100,
        min_samples: int = 10
    ):
        """Initialize adaptive strategy."""
```

**Parameters:**

- `success_threshold` (float): Success rate threshold for adaptation (default: 0.8)
- `adaptation_window` (int): Window size for success rate calculation (default: 100)
- `min_samples` (int): Minimum samples before adaptation (default: 10)

**Features:**

- Thread-safe statistics tracking
- Sliding window success rate calculation
- Dynamic backoff adjustment
- Conservative behavior with insufficient data

### Usage Examples

#### Basic Adaptive Strategy

```python
from zenoo_rpc.retry.strategies import AdaptiveStrategy

# Adaptive strategy with monitoring
strategy = AdaptiveStrategy(
    max_attempts=5,
    base_delay=1.0,
    success_threshold=0.8,  # Adapt when success rate < 80%
    adaptation_window=100,  # Consider last 100 attempts
    min_samples=10         # Need 10 samples before adapting
)

# Record attempt results
strategy.record_attempt(success=True)
strategy.record_attempt(success=False)
strategy.record_attempt(success=True)

# Get current success rate
success_rate = strategy.get_success_rate()
print(f"Current success rate: {success_rate:.2%}")
```

#### Adaptive Behavior Patterns

```python
# Different backoff based on success rate:

# High success rate (>95%): Minimal backoff
# delay = base_delay * (1.0 + (attempt-1) * 0.5)
# Delays: 1.0s, 1.5s, 2.0s, 2.5s, 3.0s

# Good success rate (80-95%): Moderate exponential backoff
# delay = base_delay * (1.5 ^ (attempt-1))
# Delays: 1.0s, 1.5s, 2.25s, 3.38s, 5.06s

# Poor success rate (<80%): Aggressive exponential backoff
# delay = base_delay * (3.0 ^ (attempt-1))
# Delays: 1.0s, 3.0s, 9.0s, 27.0s, 60.0s (capped)

# Insufficient data (<10 samples): Conservative exponential backoff
# delay = base_delay * (2.0 ^ (attempt-1))
# Delays: 1.0s, 2.0s, 4.0s, 8.0s, 16.0s
```

#### Production Monitoring

```python
# Production adaptive strategy with monitoring
production_strategy = AdaptiveStrategy(
    max_attempts=7,
    base_delay=0.5,
    success_threshold=0.85,
    adaptation_window=200,  # Larger window for stability
    min_samples=20         # More samples for reliability
)

# Monitor strategy performance
def monitor_strategy():
    stats = {
        "success_rate": production_strategy.get_success_rate(),
        "total_attempts": production_strategy._total_attempts,
        "successful_attempts": production_strategy._successful_attempts,
        "window_size": len(production_strategy._attempts_history)
    }
    return stats
```

## Advanced Strategies

### DecorrelatedJitterStrategy

Decorrelated jitter strategy to avoid thundering herd problems.

```python
class DecorrelatedJitterStrategy(RetryStrategy):
    """Decorrelated jitter strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        cap: float = 60.0
    ):
        """Initialize decorrelated jitter strategy."""
```

**Algorithm:** `delay = random(base_delay, min(previous_delay * 3, cap))`

**Example:**

```python
from zenoo_rpc.retry.strategies import DecorrelatedJitterStrategy

strategy = DecorrelatedJitterStrategy(
    max_attempts=5,
    base_delay=1.0,
    cap=60.0
)

# Delays are decorrelated and avoid synchronized retries
```

### FibonacciBackoffStrategy

Fibonacci sequence backoff for balanced growth.

```python
class FibonacciBackoffStrategy(RetryStrategy):
    """Fibonacci sequence backoff strategy."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_type: str = "full"
    ):
        """Initialize Fibonacci backoff strategy."""
```

**Algorithm:** `delay = base_delay * fibonacci(attempt)`

**Example:**

```python
from zenoo_rpc.retry.strategies import FibonacciBackoffStrategy

strategy = FibonacciBackoffStrategy(
    max_attempts=6,
    base_delay=1.0,
    jitter=True
)

# Fibonacci sequence: 1, 1, 2, 3, 5, 8
# Delays: 1.0s, 1.0s, 2.0s, 3.0s, 5.0s, 8.0s
```

## Factory Functions

Convenience functions for creating common strategy configurations.

### `exponential_backoff()`

```python
def exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> ExponentialBackoffStrategy:
    """Create exponential backoff strategy with common defaults."""
```

### `adaptive_strategy()`

```python
def adaptive_strategy(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    success_threshold: float = 0.8,
    adaptation_window: int = 100
) -> AdaptiveStrategy:
    """Create adaptive strategy with common defaults."""
```

**Example:**

```python
from zenoo_rpc.retry.strategies import exponential_backoff, adaptive_strategy

# Quick exponential backoff
exp_strategy = exponential_backoff(
    max_attempts=5,
    base_delay=0.5,
    multiplier=2.0
)

# Quick adaptive strategy
adapt_strategy = adaptive_strategy(
    max_attempts=7,
    success_threshold=0.85
)
```

## Strategy Comparison

### When to Use Each Strategy

| Strategy | Best For | Characteristics | Use Cases |
|----------|----------|-----------------|-----------|
| **Exponential** | Transient failures | Rapid backoff growth | Network errors, API rate limits |
| **Linear** | Predictable delays | Steady increase | Database locks, resource contention |
| **Fixed** | Rate-limited APIs | Consistent timing | External API quotas, batch processing |
| **Adaptive** | Variable conditions | Self-adjusting | Production systems, mixed workloads |
| **Decorrelated** | Distributed systems | Avoids thundering herd | Microservices, load balancing |
| **Fibonacci** | Balanced growth | Moderate progression | General purpose, moderate failures |

### Performance Characteristics

```python
# Strategy comparison for 5 attempts
strategies = {
    "Exponential (2x)": ExponentialBackoffStrategy(base_delay=1.0, multiplier=2.0),
    "Linear (+2s)": LinearBackoffStrategy(base_delay=1.0, increment=2.0),
    "Fixed (3s)": FixedDelayStrategy(delay=3.0),
    "Fibonacci": FibonacciBackoffStrategy(base_delay=1.0)
}

for name, strategy in strategies.items():
    delays = [strategy.calculate_delay(i) for i in range(1, 6)]
    total_time = sum(delays)
    print(f"{name}: {delays} (Total: {total_time}s)")

# Output:
# Exponential (2x): [1.0, 2.0, 4.0, 8.0, 16.0] (Total: 31.0s)
# Linear (+2s): [1.0, 3.0, 5.0, 7.0, 9.0] (Total: 25.0s)
# Fixed (3s): [3.0, 3.0, 3.0, 3.0, 3.0] (Total: 15.0s)
# Fibonacci: [1.0, 1.0, 2.0, 3.0, 5.0] (Total: 12.0s)
```

## Best Practices

### 1. Choose Strategy Based on Failure Type

```python
# ✅ Good: Match strategy to failure pattern
# Transient network errors
network_strategy = ExponentialBackoffStrategy(multiplier=2.0)

# Resource contention
resource_strategy = LinearBackoffStrategy(increment=1.0)

# Rate-limited APIs
rate_limit_strategy = FixedDelayStrategy(delay=60.0, jitter=False)

# Production systems
production_strategy = AdaptiveStrategy(success_threshold=0.85)
```

### 2. Configure Appropriate Limits

```python
# ✅ Good: Set reasonable limits
strategy = ExponentialBackoffStrategy(
    max_attempts=5,      # Don't retry forever
    base_delay=1.0,      # Start reasonable
    max_delay=60.0,      # Cap maximum delay
    jitter=True          # Avoid thundering herd
)
```

### 3. Use Jitter in Distributed Systems

```python
# ✅ Good: Always use jitter in distributed systems
distributed_strategy = ExponentialBackoffStrategy(
    jitter=True,
    jitter_type="full"  # Maximum jitter variation
)

# ❌ Avoid: No jitter in distributed systems
# Can cause thundering herd problems
```

### 4. Monitor Adaptive Strategies

```python
# ✅ Good: Monitor adaptive strategy performance
adaptive = AdaptiveStrategy()

# Regular monitoring
def log_strategy_stats():
    success_rate = adaptive.get_success_rate()
    if success_rate < 0.7:
        logger.warning(f"Low success rate: {success_rate:.2%}")
```

## Next Steps

- Learn about [Retry Policies](policies.md) for complete retry configuration
- Explore [Retry Decorators](../decorators.md) for function-level retry logic
- Check [Retry Performance](../../performance/retry.md) for optimization techniques
