"""
Base exception classes for Zenoo-RPC.

This module defines the core exception hierarchy that provides structured
error handling with proper context and debugging information.
"""

from typing import Any, Dict, Optional


class ZenooError(Exception):
    """Base exception for all Zenoo-RPC errors.

    This is the root exception that all other Zenoo-RPC exceptions inherit from.
    It allows users to catch all library-specific errors with a single except clause.
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ConnectionError(ZenooError):
    """Raised when connection to Odoo server fails.

    This includes network timeouts, connection refused, DNS resolution failures,
    and other transport-level errors.
    """

    pass


class RequestTimeoutError(ZenooError):
    """Raised when a request times out.

    This is raised when an operation takes longer than the configured timeout.
    """

    pass


# Keep TimeoutError as alias for backward compatibility
TimeoutError = RequestTimeoutError


class AuthenticationError(ZenooError):
    """Raised when authentication fails.

    This includes invalid credentials, expired sessions, and permission denied
    during the authentication process.
    """

    pass


class ValidationError(ZenooError):
    """Raised when data validation fails.

    This can occur during Pydantic model validation or when the server
    rejects data due to validation constraints.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.field = field


class AccessError(ZenooError):
    """Raised when access is denied by the Odoo server.

    This includes insufficient permissions, record-level security violations,
    and other access control failures.
    """

    def __init__(
        self,
        message: str,
        server_traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.server_traceback = server_traceback


class MethodNotFoundError(ZenooError):
    """Raised when a requested method does not exist.

    This occurs when trying to call a method that doesn't exist on the
    specified Odoo model or service.
    """

    pass


class InternalError(ZenooError):
    """Raised when an internal server error occurs.

    This represents errors that occur within the Odoo server itself,
    such as database errors, Python exceptions in server code, etc.
    """

    def __init__(
        self,
        message: str,
        server_traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.server_traceback = server_traceback
