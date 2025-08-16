"""
Cache-specific exceptions for OdooFlow.
"""

from ..exceptions.base import ZenooError


class CacheError(ZenooError):
    """Base exception for cache-related errors."""

    pass


class CacheBackendError(CacheError):
    """Exception raised when cache backend operations fail."""

    def __init__(self, message: str, backend: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.backend = backend


class CacheKeyError(CacheError):
    """Exception raised for invalid cache keys."""

    pass


class CacheSerializationError(CacheError):
    """Exception raised when cache serialization/deserialization fails."""

    def __init__(self, message: str, data_type: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.data_type = data_type


class CacheConnectionError(CacheBackendError):
    """Exception raised when cache backend connection fails."""

    pass


class CacheTimeoutError(CacheBackendError):
    """Exception raised when cache operations timeout."""

    pass
