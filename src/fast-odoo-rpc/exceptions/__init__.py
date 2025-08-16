"""
Exception hierarchy for Zenoo-RPC.

This module provides a structured exception hierarchy that maps JSON-RPC errors
to meaningful Python exceptions with proper context and debugging information.
"""

from .base import (
    ZenooError,
    ConnectionError,
    AuthenticationError,
    ValidationError,
    AccessError,
    RequestTimeoutError,
    MethodNotFoundError,
    InternalError,
)

from .mapping import map_jsonrpc_error

# Keep TimeoutError as alias for backward compatibility
TimeoutError = RequestTimeoutError

__all__ = [
    "ZenooError",
    "ConnectionError",
    "AuthenticationError",
    "ValidationError",
    "AccessError",
    "TimeoutError",
    "MethodNotFoundError",
    "InternalError",
    "map_jsonrpc_error",
]
