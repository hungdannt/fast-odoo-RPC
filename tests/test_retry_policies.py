"""
Comprehensive tests for retry/policies.py.

This module tests all retry policy classes and functionality with focus on:
- RetryContext class behavior and timing
- RetryPolicy enhanced decision making
- Circuit breaker integration and state management
- Idempotency checks and graceful degradation
- Specialized policies (Network, Database, etc.)
- Factory functions and policy customization
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.zenoo_rpc.retry.policies import (
    RetryDecision,
    RetryContext,
    RetryPolicy,
    DefaultRetryPolicy,
    NetworkRetryPolicy,
    DatabaseRetryPolicy,
    QuickRetryPolicy,
    AggressiveRetryPolicy,
    CircuitBreakerRetryPolicy,
    IdempotentRetryPolicy,
    GracefulDegradationRetryPolicy,
    create_network_policy,
    create_database_policy,
    create_circuit_breaker_policy,
)
from src.zenoo_rpc.retry.strategies import (
    RetryAttempt,
    ExponentialBackoffStrategy,
)


class TestRetryContext:
    """Test RetryContext class."""

    def test_basic_creation(self):
        """Test basic RetryContext creation."""
        exception = ValueError("test error")
        start_time = time.time()
        
        context = RetryContext(
            attempt_number=2,
            exception=exception,
            start_time=start_time
        )
        
        assert context.attempt_number == 2
        assert context.exception == exception
        assert context.start_time == start_time
        assert context.last_attempt_time is None
        assert context.total_delay == 0.0
        assert len(context.attempts_history) == 0
        assert isinstance(context.metadata, dict)

    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        start_time = time.time() - 5.0  # 5 seconds ago
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=start_time
        )
        
        elapsed = context.elapsed_time
        assert 4.5 <= elapsed <= 5.5  # Allow some tolerance

    def test_time_since_last_attempt(self):
        """Test time since last attempt calculation."""
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        # Initially None
        assert context.time_since_last_attempt is None
        
        # Set last attempt time
        context.last_attempt_time = time.time() - 2.0
        time_since = context.time_since_last_attempt
        assert 1.5 <= time_since <= 2.5

    def test_add_attempt(self):
        """Test adding attempts to history."""
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        # Add first attempt
        attempt1 = RetryAttempt(attempt_number=1, delay=1.0)
        context.add_attempt(attempt1)
        
        assert len(context.attempts_history) == 1
        assert context.attempts_history[0] == attempt1
        assert context.total_delay == 1.0
        assert context.last_attempt_time is not None
        
        # Add second attempt
        attempt2 = RetryAttempt(attempt_number=2, delay=2.0)
        context.add_attempt(attempt2)
        
        assert len(context.attempts_history) == 2
        assert context.total_delay == 3.0

    def test_metadata_usage(self):
        """Test metadata functionality."""
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time(),
            metadata={"operation": "test", "user_id": 123}
        )
        
        assert context.metadata["operation"] == "test"
        assert context.metadata["user_id"] == 123
        
        # Add more metadata
        context.metadata["retry_reason"] = "network_error"
        assert context.metadata["retry_reason"] == "network_error"


class TestRetryPolicy:
    """Test RetryPolicy class."""

    def test_basic_creation(self):
        """Test basic RetryPolicy creation."""
        policy = RetryPolicy()
        
        assert isinstance(policy.strategy, ExponentialBackoffStrategy)
        assert len(policy.retryable_exceptions) == 0
        assert len(policy.non_retryable_exceptions) == 0
        assert policy.timeout is None
        assert policy.retry_condition is None

    def test_custom_configuration(self):
        """Test RetryPolicy with custom configuration."""
        strategy = ExponentialBackoffStrategy(max_attempts=5)
        retryable_exceptions = {ConnectionError, TimeoutError}
        non_retryable_exceptions = {ValueError, TypeError}
        
        def custom_condition(exc):
            return isinstance(exc, OSError)
        
        policy = RetryPolicy(
            strategy=strategy,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            timeout=60.0,
            retry_condition=custom_condition,
            max_total_delay=120.0,
            backoff_multiplier_on_failure=1.5
        )
        
        assert policy.strategy == strategy
        assert policy.retryable_exceptions == retryable_exceptions
        assert policy.non_retryable_exceptions == non_retryable_exceptions
        assert policy.timeout == 60.0
        assert policy.retry_condition == custom_condition
        assert policy.max_total_delay == 120.0
        assert policy.backoff_multiplier_on_failure == 1.5

    def test_legacy_should_retry_interface(self):
        """Test legacy should_retry interface."""
        policy = RetryPolicy(timeout=5.0)
        
        # Should retry within timeout
        start_time = time.time()
        assert policy.should_retry(1, Exception(), start_time) is True
        
        # Should not retry after timeout
        old_start_time = time.time() - 10.0
        assert policy.should_retry(1, Exception(), old_start_time) is False

    def test_make_retry_decision_timeout(self):
        """Test retry decision with timeout."""
        policy = RetryPolicy(timeout=5.0)
        
        # Within timeout
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.RETRY
        
        # Exceeded timeout
        old_context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time() - 10.0
        )
        decision = policy.make_retry_decision(old_context)
        assert decision == RetryDecision.TIMEOUT

    def test_make_retry_decision_max_total_delay(self):
        """Test retry decision with max total delay."""
        policy = RetryPolicy(max_total_delay=10.0)
        
        context = RetryContext(
            attempt_number=2,
            exception=Exception(),
            start_time=time.time(),
            total_delay=15.0  # Exceeds max_total_delay
        )
        
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.TIMEOUT

    def test_make_retry_decision_strategy_limit(self):
        """Test retry decision with strategy limit."""
        strategy = ExponentialBackoffStrategy(max_attempts=2)
        policy = RetryPolicy(strategy=strategy)
        
        context = RetryContext(
            attempt_number=3,  # Exceeds max_attempts
            exception=Exception(),
            start_time=time.time()
        )
        
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.STOP

    def test_make_retry_decision_non_retryable_exception(self):
        """Test retry decision with non-retryable exception."""
        policy = RetryPolicy(
            non_retryable_exceptions={ValueError, TypeError}
        )
        
        context = RetryContext(
            attempt_number=1,
            exception=ValueError("test"),
            start_time=time.time()
        )
        
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.NON_RETRYABLE

    def test_make_retry_decision_retryable_exceptions(self):
        """Test retry decision with retryable exceptions list."""
        policy = RetryPolicy(
            retryable_exceptions={ConnectionError, TimeoutError}
        )
        
        # Retryable exception
        retryable_context = RetryContext(
            attempt_number=1,
            exception=ConnectionError("test"),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(retryable_context)
        assert decision == RetryDecision.RETRY
        
        # Non-retryable exception
        non_retryable_context = RetryContext(
            attempt_number=1,
            exception=ValueError("test"),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(non_retryable_context)
        assert decision == RetryDecision.NON_RETRYABLE

    def test_make_retry_decision_custom_condition(self):
        """Test retry decision with custom condition."""
        def custom_condition(exc):
            return isinstance(exc, ConnectionError)
        
        policy = RetryPolicy(retry_condition=custom_condition)
        
        # Condition passes
        pass_context = RetryContext(
            attempt_number=1,
            exception=ConnectionError("test"),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(pass_context)
        assert decision == RetryDecision.RETRY
        
        # Condition fails
        fail_context = RetryContext(
            attempt_number=1,
            exception=ValueError("test"),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(fail_context)
        assert decision == RetryDecision.NON_RETRYABLE

    def test_circuit_breaker_hook(self):
        """Test circuit breaker hook integration."""
        circuit_breaker_mock = Mock(return_value=False)
        policy = RetryPolicy(circuit_breaker_hook=circuit_breaker_mock)
        
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.CIRCUIT_OPEN
        circuit_breaker_mock.assert_called_once_with(context)

    def test_idempotency_check(self):
        """Test idempotency check integration."""
        idempotency_mock = Mock(return_value=False)
        policy = RetryPolicy(idempotency_check=idempotency_mock)
        
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.NON_RETRYABLE
        idempotency_mock.assert_called_once_with(context)

    def test_get_delay_with_backoff_multiplier(self):
        """Test delay calculation with backoff multiplier."""
        policy = RetryPolicy(backoff_multiplier_on_failure=2.0)
        
        # Mock strategy to return fixed delay
        policy.strategy.get_delay = Mock(return_value=1.0)
        
        # First attempt: 1.0 * (2.0^0) = 1.0
        delay1 = policy.get_delay(1)
        assert delay1 == 1.0
        
        # Second attempt: 1.0 * (2.0^1) = 2.0
        delay2 = policy.get_delay(2)
        assert delay2 == 2.0
        
        # Third attempt: 1.0 * (2.0^2) = 4.0
        delay3 = policy.get_delay(3)
        assert delay3 == 4.0

    def test_success_callback(self):
        """Test success callback execution."""
        success_mock = Mock()
        policy = RetryPolicy(success_callback=success_mock)
        
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        policy.on_success(context)
        success_mock.assert_called_once_with(context)

    def test_failure_callback(self):
        """Test failure callback execution."""
        failure_mock = Mock()
        policy = RetryPolicy(failure_callback=failure_mock)
        
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        result = policy.on_failure(context)
        failure_mock.assert_called_once_with(context)
        assert result is None

    def test_graceful_degradation(self):
        """Test graceful degradation execution."""
        degradation_result = {"fallback": "data"}
        degradation_mock = Mock(return_value=degradation_result)
        policy = RetryPolicy(graceful_degradation=degradation_mock)
        
        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )
        
        result = policy.on_failure(context)
        degradation_mock.assert_called_once_with(context)
        assert result == degradation_result


class TestDefaultRetryPolicy:
    """Test DefaultRetryPolicy class."""

    def test_basic_configuration(self):
        """Test default policy configuration."""
        policy = DefaultRetryPolicy()

        assert policy.strategy.max_attempts == 3
        assert policy.strategy.base_delay == 1.0
        assert policy.strategy.multiplier == 2.0
        assert policy.timeout == 60.0

        # Check retryable exceptions
        assert ConnectionError in policy.retryable_exceptions
        assert TimeoutError in policy.retryable_exceptions
        assert OSError in policy.retryable_exceptions

        # Check non-retryable exceptions
        assert ValueError in policy.non_retryable_exceptions
        assert TypeError in policy.non_retryable_exceptions
        assert AttributeError in policy.non_retryable_exceptions

    def test_retryable_exception_handling(self):
        """Test handling of retryable exceptions."""
        policy = DefaultRetryPolicy()

        context = RetryContext(
            attempt_number=1,
            exception=ConnectionError("network error"),
            start_time=time.time()
        )

        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.RETRY

    def test_non_retryable_exception_handling(self):
        """Test handling of non-retryable exceptions."""
        policy = DefaultRetryPolicy()

        context = RetryContext(
            attempt_number=1,
            exception=ValueError("invalid value"),
            start_time=time.time()
        )

        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.NON_RETRYABLE


class TestNetworkRetryPolicy:
    """Test NetworkRetryPolicy class."""

    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx module."""
        with patch('src.zenoo_rpc.retry.policies.httpx') as mock:
            # Create mock exception classes
            mock.ConnectError = type('ConnectError', (Exception,), {})
            mock.TimeoutException = type('TimeoutException', (Exception,), {})
            mock.NetworkError = type('NetworkError', (Exception,), {})
            mock.PoolTimeout = type('PoolTimeout', (Exception,), {})
            mock.HTTPStatusError = type('HTTPStatusError', (Exception,), {})

            # Create mock response
            mock_response = Mock()
            mock_response.status_code = 500
            mock.HTTPStatusError.response = mock_response

            yield mock

    def test_basic_configuration(self, mock_httpx):
        """Test network policy configuration."""
        policy = NetworkRetryPolicy()

        assert policy.strategy.max_attempts == 5
        assert policy.strategy.base_delay == 0.5
        assert policy.strategy.multiplier == 1.5
        assert policy.timeout == 30.0

    def test_network_retry_condition_retryable_status(self, mock_httpx):
        """Test network retry condition with retryable status codes."""
        policy = NetworkRetryPolicy()

        # Create mock HTTP error with retryable status code
        mock_response = Mock()
        mock_response.status_code = 503  # Service Unavailable

        http_error = mock_httpx.HTTPStatusError()
        http_error.response = mock_response

        result = policy._network_retry_condition(http_error)
        assert result is True

    def test_network_retry_condition_non_retryable_status(self, mock_httpx):
        """Test network retry condition with non-retryable status codes."""
        policy = NetworkRetryPolicy()

        # Create mock HTTP error with non-retryable status code
        mock_response = Mock()
        mock_response.status_code = 404  # Not Found

        http_error = mock_httpx.HTTPStatusError()
        http_error.response = mock_response

        result = policy._network_retry_condition(http_error)
        assert result is False

    def test_network_retry_condition_non_http_error(self, mock_httpx):
        """Test network retry condition with non-HTTP errors."""
        policy = NetworkRetryPolicy()

        # Non-HTTP error should be retryable
        result = policy._network_retry_condition(ConnectionError())
        assert result is True


class TestDatabaseRetryPolicy:
    """Test DatabaseRetryPolicy class."""

    def test_basic_configuration(self):
        """Test database policy configuration."""
        policy = DatabaseRetryPolicy()

        assert policy.strategy.max_attempts == 3
        assert policy.strategy.base_delay == 2.0
        assert policy.strategy.multiplier == 2.0
        assert policy.timeout == 120.0

        # Check basic retryable exceptions
        assert ConnectionError in policy.retryable_exceptions
        assert TimeoutError in policy.retryable_exceptions
        assert OSError in policy.retryable_exceptions

    def test_with_psycopg2_exceptions(self):
        """Test database policy with psycopg2 exceptions."""
        # Mock psycopg2 import in the module
        import sys

        # Create mock psycopg2 module
        mock_psycopg2 = MagicMock()
        mock_psycopg2.OperationalError = type(
            'OperationalError', (Exception,), {}
        )
        mock_psycopg2.InterfaceError = type('InterfaceError', (Exception,), {})

        # Add to sys.modules before importing policy
        sys.modules['psycopg2'] = mock_psycopg2

        try:
            # Import and create policy (will use mocked psycopg2)
            from src.zenoo_rpc.retry.policies import DatabaseRetryPolicy
            policy = DatabaseRetryPolicy()

            # Should include psycopg2 exceptions
            operational_error = mock_psycopg2.OperationalError
            interface_error = mock_psycopg2.InterfaceError
            assert operational_error in policy.retryable_exceptions
            assert interface_error in policy.retryable_exceptions
        finally:
            # Clean up
            if 'psycopg2' in sys.modules:
                del sys.modules['psycopg2']


class TestQuickRetryPolicy:
    """Test QuickRetryPolicy class."""

    def test_basic_configuration(self):
        """Test quick policy configuration."""
        policy = QuickRetryPolicy()

        assert policy.strategy.max_attempts == 2
        assert policy.strategy.base_delay == 0.1
        assert policy.strategy.multiplier == 2.0
        assert policy.strategy.jitter is False
        assert policy.timeout == 5.0


class TestAggressiveRetryPolicy:
    """Test AggressiveRetryPolicy class."""

    def test_basic_configuration(self):
        """Test aggressive policy configuration."""
        policy = AggressiveRetryPolicy()

        assert policy.strategy.max_attempts == 10
        assert policy.strategy.base_delay == 0.5
        assert policy.strategy.multiplier == 1.2
        assert policy.timeout == 300.0

        # Check retryable exceptions
        assert ConnectionError in policy.retryable_exceptions
        assert TimeoutError in policy.retryable_exceptions
        assert OSError in policy.retryable_exceptions


class TestCircuitBreakerRetryPolicy:
    """Test CircuitBreakerRetryPolicy class."""

    def test_basic_configuration(self):
        """Test circuit breaker policy configuration."""
        policy = CircuitBreakerRetryPolicy(
            failure_threshold=3,
            recovery_timeout=30.0,
            half_open_max_calls=2
        )

        assert policy.failure_threshold == 3
        assert policy.recovery_timeout == 30.0
        assert policy.half_open_max_calls == 2
        assert policy._state == "closed"
        assert policy._failure_count == 0

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        policy = CircuitBreakerRetryPolicy()

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should allow retry in closed state
        result = policy._circuit_breaker_check(context)
        assert result is True

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        policy = CircuitBreakerRetryPolicy(failure_threshold=2)

        # Simulate failures to open circuit
        policy._failure_count = 2
        policy._state = "open"
        policy._last_failure_time = time.time()

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should not allow retry in open state
        result = policy._circuit_breaker_check(context)
        assert result is False

    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transition to half-open."""
        policy = CircuitBreakerRetryPolicy(recovery_timeout=0.1)

        # Set to open state
        policy._state = "open"
        policy._last_failure_time = time.time() - 0.2  # Past recovery timeout

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should transition to half-open and allow retry
        result = policy._circuit_breaker_check(context)
        assert result is True
        assert policy._state == "half_open"

    def test_circuit_breaker_half_open_limit(self):
        """Test circuit breaker half-open call limit."""
        policy = CircuitBreakerRetryPolicy(half_open_max_calls=2)

        # Set to half-open state with max calls reached
        policy._state = "half_open"
        policy._half_open_calls = 2

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should not allow retry when half-open limit reached
        result = policy._circuit_breaker_check(context)
        assert result is False

    def test_on_success_closed_state(self):
        """Test success handling in closed state."""
        policy = CircuitBreakerRetryPolicy()
        policy._failure_count = 2

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        policy._on_success(context)

        # Should reduce failure count
        assert policy._failure_count == 1

    def test_on_success_half_open_state(self):
        """Test success handling in half-open state."""
        policy = CircuitBreakerRetryPolicy()
        policy._state = "half_open"
        policy._failure_count = 3

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        policy._on_success(context)

        # Should close circuit and reset failure count
        assert policy._state == "closed"
        assert policy._failure_count == 0

    def test_on_failure_opens_circuit(self):
        """Test failure handling that opens circuit."""
        policy = CircuitBreakerRetryPolicy(failure_threshold=2)
        policy._failure_count = 1  # One failure away from threshold

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        policy._on_failure(context)

        # Should open circuit
        assert policy._state == "open"
        assert policy._failure_count == 2

    def test_on_failure_half_open_to_open(self):
        """Test failure in half-open state opens circuit."""
        policy = CircuitBreakerRetryPolicy()
        policy._state = "half_open"

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        policy._on_failure(context)

        # Should open circuit from half-open
        assert policy._state == "open"


class TestIdempotentRetryPolicy:
    """Test IdempotentRetryPolicy class."""

    def test_basic_configuration(self):
        """Test idempotent policy configuration."""
        policy = IdempotentRetryPolicy()

        assert policy.strategy.max_attempts == 5
        assert policy.timeout == 120.0
        assert policy.idempotency_store == {}

    def test_idempotency_check_no_generator(self):
        """Test idempotency check without key generator."""
        policy = IdempotentRetryPolicy()

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should return True if no generator provided
        result = policy._check_idempotency(context)
        assert result is True

    def test_idempotency_check_with_generator(self):
        """Test idempotency check with key generator."""
        key_generator = Mock(return_value="test_key_123")
        store = {}

        policy = IdempotentRetryPolicy(
            idempotency_key_generator=key_generator,
            idempotency_store=store
        )

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should return True for new operation
        result = policy._check_idempotency(context)
        assert result is True
        key_generator.assert_called_once()

    def test_idempotency_check_already_completed(self):
        """Test idempotency check for already completed operation."""
        key_generator = Mock(return_value="test_key_123")
        store = {
            "test_key_123": {"status": "success", "result": "completed"}
        }

        policy = IdempotentRetryPolicy(
            idempotency_key_generator=key_generator,
            idempotency_store=store
        )

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should return False for already completed operation
        result = policy._check_idempotency(context)
        assert result is False

    def test_idempotency_check_generator_failure(self):
        """Test idempotency check when generator fails."""
        key_generator = Mock(side_effect=Exception("generator failed"))

        policy = IdempotentRetryPolicy(
            idempotency_key_generator=key_generator
        )

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should return False on generator failure (conservative)
        result = policy._check_idempotency(context)
        assert result is False


class TestGracefulDegradationRetryPolicy:
    """Test GracefulDegradationRetryPolicy class."""

    def test_basic_configuration(self):
        """Test graceful degradation policy configuration."""
        policy = GracefulDegradationRetryPolicy()

        assert policy.strategy.max_attempts == 3
        assert policy.timeout == 30.0
        assert policy.fallback_function is None
        assert policy.degraded_service_timeout == 5.0

    def test_graceful_degradation_no_fallback(self):
        """Test graceful degradation without fallback function."""
        policy = GracefulDegradationRetryPolicy()

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        result = policy._graceful_degradation(context)
        assert result is None

    def test_graceful_degradation_with_fallback(self):
        """Test graceful degradation with fallback function."""
        fallback_result = {"fallback": "data", "degraded": True}
        fallback_function = Mock(return_value=fallback_result)

        policy = GracefulDegradationRetryPolicy(
            fallback_function=fallback_function
        )

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        result = policy._graceful_degradation(context)
        assert result == fallback_result
        fallback_function.assert_called_once_with(context)

    def test_graceful_degradation_fallback_failure(self):
        """Test graceful degradation when fallback fails."""
        fallback_function = Mock(side_effect=Exception("fallback failed"))

        policy = GracefulDegradationRetryPolicy(
            fallback_function=fallback_function
        )

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        result = policy._graceful_degradation(context)
        assert result is None


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_network_policy(self):
        """Test create_network_policy factory function."""
        policy = create_network_policy(
            max_attempts=7,
            base_delay=1.0,
            timeout=45.0
        )

        assert isinstance(policy, NetworkRetryPolicy)
        assert policy.strategy.max_attempts == 7
        assert policy.strategy.base_delay == 1.0
        assert policy.timeout == 45.0

    def test_create_database_policy(self):
        """Test create_database_policy factory function."""
        policy = create_database_policy(
            max_attempts=5,
            base_delay=3.0,
            timeout=180.0
        )

        assert isinstance(policy, DatabaseRetryPolicy)
        assert policy.strategy.max_attempts == 5
        assert policy.strategy.base_delay == 3.0
        assert policy.timeout == 180.0

    def test_create_circuit_breaker_policy(self):
        """Test create_circuit_breaker_policy factory function."""
        policy = create_circuit_breaker_policy(
            failure_threshold=10,
            recovery_timeout=120.0
        )

        assert isinstance(policy, CircuitBreakerRetryPolicy)
        assert policy.failure_threshold == 10
        assert policy.recovery_timeout == 120.0


class TestIntegration:
    """Test integration scenarios."""

    def test_policy_with_multiple_features(self):
        """Test policy with multiple enhanced features."""
        circuit_breaker_mock = Mock(return_value=True)
        idempotency_mock = Mock(return_value=True)
        success_mock = Mock()
        failure_mock = Mock()
        degradation_mock = Mock(return_value={"fallback": True})

        policy = RetryPolicy(
            timeout=10.0,
            max_total_delay=20.0,
            circuit_breaker_hook=circuit_breaker_mock,
            idempotency_check=idempotency_mock,
            success_callback=success_mock,
            failure_callback=failure_mock,
            graceful_degradation=degradation_mock,
            backoff_multiplier_on_failure=1.5
        )

        context = RetryContext(
            attempt_number=1,
            exception=ConnectionError("test"),
            start_time=time.time()
        )

        # Test retry decision
        decision = policy.make_retry_decision(context)
        assert decision == RetryDecision.RETRY

        # Verify all hooks were called
        circuit_breaker_mock.assert_called_once_with(context)
        idempotency_mock.assert_called_once_with(context)

        # Test success callback
        policy.on_success(context)
        success_mock.assert_called_once_with(context)

        # Test failure callback and degradation
        result = policy.on_failure(context)
        failure_mock.assert_called_once_with(context)
        degradation_mock.assert_called_once_with(context)
        assert result == {"fallback": True}

    def test_policy_decision_flow(self):
        """Test complete policy decision flow."""
        policy = RetryPolicy(
            retryable_exceptions={ConnectionError},
            non_retryable_exceptions={ValueError},
            timeout=5.0
        )

        # Test retryable exception
        retryable_context = RetryContext(
            attempt_number=1,
            exception=ConnectionError("network error"),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(retryable_context)
        assert decision == RetryDecision.RETRY

        # Test non-retryable exception
        non_retryable_context = RetryContext(
            attempt_number=1,
            exception=ValueError("invalid value"),
            start_time=time.time()
        )
        decision = policy.make_retry_decision(non_retryable_context)
        assert decision == RetryDecision.NON_RETRYABLE

        # Test timeout
        timeout_context = RetryContext(
            attempt_number=1,
            exception=ConnectionError("network error"),
            start_time=time.time() - 10.0  # 10 seconds ago
        )
        decision = policy.make_retry_decision(timeout_context)
        assert decision == RetryDecision.TIMEOUT

    def test_callback_error_handling(self):
        """Test error handling in callbacks."""
        failing_callback = Mock(side_effect=Exception("callback failed"))

        policy = RetryPolicy(
            success_callback=failing_callback,
            failure_callback=failing_callback,
            graceful_degradation=failing_callback
        )

        context = RetryContext(
            attempt_number=1,
            exception=Exception(),
            start_time=time.time()
        )

        # Should not raise exceptions even if callbacks fail
        policy.on_success(context)
        result = policy.on_failure(context)
        assert result is None
