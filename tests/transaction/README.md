# Transaction System Tests

This directory contains comprehensive tests for the transaction management system in zenoo_rpc.

## Test Coverage

The transaction module has achieved **≥95% code coverage**:
- `transaction/__init__.py`: 100%
- `transaction/exceptions.py`: 100% 
- `transaction/manager.py`: 98%
- `transaction/context.py`: 93%

## Test Organization

### test_manager_happy_paths.py
Tests standard transaction workflows including:
- Simple commit/rollback sequences
- Nested savepoints
- Duration calculation
- Transaction stats aggregation
- Property-based testing with Hypothesis for random operation sequences

### test_manager_edge_cases.py
Tests error conditions and edge cases:
- Invalid savepoint names and special characters
- Rollback after commit / commit after rollback
- Commit failure recovery
- Rollback with compensating operation failures
- Utility methods (get_current_transaction, get_transaction, rollback_all)
- Large transactions with many operations

### test_concurrency.py
Tests concurrent transaction handling:
- 20 coroutines creating/rolling back transactions concurrently
- Verifies isolation and atomicity
- Tests with random number of concurrent transactions using Hypothesis

### test_transaction_context.py
Tests the transaction context API:
- `@atomic` decorator (with and without parentheses)
- Transaction context manager
- Exception propagation
- SavepointContext for nested transaction support
- Transaction contextvar propagation across async contexts

## Key Features Tested

1. **Transaction Lifecycle**: Creation, commit, rollback, state transitions
2. **Savepoints**: Creation, rollback to savepoint, nested savepoints
3. **Error Handling**: Commit failures, rollback failures, state violations
4. **Concurrency**: Multiple concurrent transactions with proper isolation
5. **Context Management**: Decorators and context managers for transaction control
6. **Edge Cases**: Empty operations, special characters, large transaction volumes

## Running the Tests

```bash
# Run all transaction tests
pytest tests/transaction/

# Run with coverage report
pytest tests/transaction/ --cov=src/zenoo_rpc/transaction --cov-report=term-missing

# Run specific test file
pytest tests/transaction/test_manager_happy_paths.py -v

# Run with hypothesis statistics
pytest tests/transaction/ --hypothesis-show-statistics
```

## Property-Based Testing

Several tests use Hypothesis for property-based testing:
- Random operation sequences
- Random savepoint operations  
- Concurrent transactions with random counts
- Random transaction IDs

Health check warnings for function-scoped fixtures are suppressed where needed.
