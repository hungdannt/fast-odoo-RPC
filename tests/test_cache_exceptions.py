"""
Comprehensive tests for cache exceptions.

This module tests all cache-related exception classes with focus on:
- Exception hierarchy and inheritance
- Error message formatting and attributes
- Backend-specific error handling
- Serialization error context
- Integration with base ZenooError
"""

from src.zenoo_rpc.cache.exceptions import (
    CacheError,
    CacheBackendError,
    CacheKeyError,
    CacheSerializationError,
    CacheConnectionError,
    CacheTimeoutError,
)
from src.zenoo_rpc.exceptions import ZenooError


class TestCacheError:
    """Test CacheError base exception class."""

    def test_inheritance(self):
        """Test that CacheError inherits from ZenooError."""
        assert issubclass(CacheError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic CacheError instantiation."""
        error = CacheError("Test cache error")
        assert str(error) == "Test cache error"
        assert isinstance(error, ZenooError)
        assert isinstance(error, Exception)

    def test_empty_message(self):
        """Test CacheError with empty message."""
        error = CacheError("")
        assert str(error) == ""

    def test_with_context(self):
        """Test CacheError with context information."""
        context = {"operation": "get", "key": "test_key"}
        error = CacheError("Cache operation failed", context=context)
        
        assert str(error) == "Cache operation failed"
        assert error.context == context
        assert error.context["operation"] == "get"
        assert error.context["key"] == "test_key"


class TestCacheBackendError:
    """Test CacheBackendError exception class."""

    def test_inheritance(self):
        """Test that CacheBackendError inherits from CacheError."""
        assert issubclass(CacheBackendError, CacheError)
        assert issubclass(CacheBackendError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic CacheBackendError instantiation."""
        error = CacheBackendError("Backend operation failed")
        assert str(error) == "Backend operation failed"
        assert error.backend is None

    def test_with_backend_name(self):
        """Test CacheBackendError with backend specification."""
        error = CacheBackendError("Redis connection failed", backend="redis")
        
        assert str(error) == "Redis connection failed"
        assert error.backend == "redis"

    def test_with_context_and_backend(self):
        """Test CacheBackendError with both context and backend."""
        context = {"host": "localhost", "port": 6379}
        error = CacheBackendError(
            "Connection timeout", 
            backend="redis", 
            context=context
        )
        
        assert str(error) == "Connection timeout"
        assert error.backend == "redis"
        assert error.context == context

    def test_different_backends(self):
        """Test with different backend types."""
        backends = ["redis", "memcached", "memory", "file", "database"]
        
        for backend in backends:
            error = CacheBackendError(f"{backend} error", backend=backend)
            assert error.backend == backend
            assert f"{backend} error" in str(error)


class TestCacheKeyError:
    """Test CacheKeyError exception class."""

    def test_inheritance(self):
        """Test that CacheKeyError inherits from CacheError."""
        assert issubclass(CacheKeyError, CacheError)
        assert issubclass(CacheKeyError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic CacheKeyError instantiation."""
        error = CacheKeyError("Invalid cache key")
        assert str(error) == "Invalid cache key"

    def test_key_validation_errors(self):
        """Test various key validation error scenarios."""
        test_cases = [
            "Key too long",
            "Key contains invalid characters",
            "Empty key not allowed",
            "Key format invalid",
        ]
        
        for message in test_cases:
            error = CacheKeyError(message)
            assert str(error) == message

    def test_with_context(self):
        """Test CacheKeyError with key context."""
        context = {"key": "invalid:key:with:colons", "max_length": 250}
        error = CacheKeyError("Key validation failed", context=context)
        
        assert str(error) == "Key validation failed"
        assert error.context["key"] == "invalid:key:with:colons"
        assert error.context["max_length"] == 250


class TestCacheSerializationError:
    """Test CacheSerializationError exception class."""

    def test_inheritance(self):
        """Test that CacheSerializationError inherits from CacheError."""
        assert issubclass(CacheSerializationError, CacheError)
        assert issubclass(CacheSerializationError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic CacheSerializationError instantiation."""
        error = CacheSerializationError("Serialization failed")
        assert str(error) == "Serialization failed"
        assert error.data_type is None

    def test_with_data_type(self):
        """Test CacheSerializationError with data type specification."""
        error = CacheSerializationError(
            "Cannot serialize object", 
            data_type="datetime"
        )
        
        assert str(error) == "Cannot serialize object"
        assert error.data_type == "datetime"

    def test_different_data_types(self):
        """Test with different data types."""
        data_types = ["dict", "list", "set", "custom_class", "function"]
        
        for data_type in data_types:
            error = CacheSerializationError(
                f"Cannot serialize {data_type}", 
                data_type=data_type
            )
            assert error.data_type == data_type
            assert f"Cannot serialize {data_type}" in str(error)

    def test_with_context_and_data_type(self):
        """Test with both context and data type."""
        context = {"object_id": 12345, "size": "large"}
        error = CacheSerializationError(
            "Object too complex to serialize",
            data_type="custom_object",
            context=context
        )
        
        assert str(error) == "Object too complex to serialize"
        assert error.data_type == "custom_object"
        assert error.context == context


class TestCacheConnectionError:
    """Test CacheConnectionError exception class."""

    def test_inheritance(self):
        """Test that CacheConnectionError inherits from CacheBackendError."""
        assert issubclass(CacheConnectionError, CacheBackendError)
        assert issubclass(CacheConnectionError, CacheError)
        assert issubclass(CacheConnectionError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic CacheConnectionError instantiation."""
        error = CacheConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.backend is None

    def test_with_backend(self):
        """Test CacheConnectionError with backend specification."""
        error = CacheConnectionError("Redis connection lost", backend="redis")
        
        assert str(error) == "Redis connection lost"
        assert error.backend == "redis"

    def test_connection_scenarios(self):
        """Test various connection error scenarios."""
        scenarios = [
            ("Connection refused", "redis"),
            ("Network timeout", "memcached"),
            ("Authentication failed", "redis"),
            ("Host unreachable", "remote_cache"),
        ]
        
        for message, backend in scenarios:
            error = CacheConnectionError(message, backend=backend)
            assert str(error) == message
            assert error.backend == backend


class TestCacheTimeoutError:
    """Test CacheTimeoutError exception class."""

    def test_inheritance(self):
        """Test that CacheTimeoutError inherits from CacheBackendError."""
        assert issubclass(CacheTimeoutError, CacheBackendError)
        assert issubclass(CacheTimeoutError, CacheError)
        assert issubclass(CacheTimeoutError, ZenooError)

    def test_basic_instantiation(self):
        """Test basic CacheTimeoutError instantiation."""
        error = CacheTimeoutError("Operation timed out")
        assert str(error) == "Operation timed out"
        assert error.backend is None

    def test_with_backend(self):
        """Test CacheTimeoutError with backend specification."""
        error = CacheTimeoutError("Get operation timeout", backend="redis")
        
        assert str(error) == "Get operation timeout"
        assert error.backend == "redis"

    def test_timeout_scenarios(self):
        """Test various timeout error scenarios."""
        scenarios = [
            ("Read timeout after 5s", "redis"),
            ("Write timeout", "memcached"),
            ("Connection timeout", "file_cache"),
            ("Bulk operation timeout", "database"),
        ]
        
        for message, backend in scenarios:
            error = CacheTimeoutError(message, backend=backend)
            assert str(error) == message
            assert error.backend == backend


class TestExceptionIntegration:
    """Test integration between different cache exceptions."""

    def test_exception_hierarchy(self):
        """Test that all exceptions maintain proper hierarchy."""
        # Create instances of all exception types
        cache_error = CacheError("Base cache error")
        backend_error = CacheBackendError("Backend error", backend="redis")
        key_error = CacheKeyError("Key error")
        serialization_error = CacheSerializationError("Serialization error")
        connection_error = CacheConnectionError("Connection error")
        timeout_error = CacheTimeoutError("Timeout error")
        
        # Test isinstance relationships
        exceptions = [
            backend_error, key_error, serialization_error, 
            connection_error, timeout_error
        ]
        
        for exc in exceptions:
            assert isinstance(exc, CacheError)
            assert isinstance(exc, ZenooError)
            assert isinstance(exc, Exception)

    def test_backend_specific_exceptions(self):
        """Test backend-specific exception behavior."""
        # Connection and timeout errors should inherit backend attribute
        connection_error = CacheConnectionError("Failed", backend="redis")
        timeout_error = CacheTimeoutError("Timeout", backend="redis")
        
        assert hasattr(connection_error, 'backend')
        assert hasattr(timeout_error, 'backend')
        assert connection_error.backend == "redis"
        assert timeout_error.backend == "redis"

    def test_exception_chaining(self):
        """Test exception chaining with cache exceptions."""
        original_error = ConnectionError("Network error")
        cache_error = CacheConnectionError("Cache connection failed")
        cache_error.__cause__ = original_error
        
        assert cache_error.__cause__ is original_error
        assert "Cache connection failed" in str(cache_error)

    def test_context_preservation(self):
        """Test that context is preserved across exception types."""
        context = {"operation": "set", "key": "test", "value_size": 1024}
        
        # Test different exception types with same context
        exceptions = [
            CacheError("Error", context=context),
            CacheBackendError("Backend error", context=context),
            CacheSerializationError("Serialization error", context=context),
        ]
        
        for exc in exceptions:
            assert exc.context == context
            assert exc.context["operation"] == "set"
            assert exc.context["key"] == "test"
            assert exc.context["value_size"] == 1024
