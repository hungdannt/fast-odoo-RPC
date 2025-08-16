"""
JSON-RPC error mapping utilities.

This module provides functions to map JSON-RPC error responses from Odoo
to structured Zenoo-RPC exceptions with proper context and debugging information.
"""

from typing import Any, Dict

from .base import (
    AccessError,
    AuthenticationError,
    InternalError,
    MethodNotFoundError,
    ZenooError,
    ValidationError,
)


def map_jsonrpc_error(error_data: Dict[str, Any]) -> ZenooError:
    """Map JSON-RPC error response to appropriate Zenoo-RPC exception.

    Args:
        error_data: The error data from JSON-RPC response

    Returns:
        An appropriate ZenooError subclass instance

    Example:
        >>> error = {
        ...     "code": -32601,
        ...     "message": "Method not found",
        ...     "data": {"name": "odoo.exceptions.ValidationError"}
        ... }
        >>> exception = map_jsonrpc_error(error)
        >>> isinstance(exception, MethodNotFoundError)
        True
    """
    error_code = error_data.get("code")
    error_message = error_data.get("message", "Unknown error")
    error_data_dict = error_data.get("data", {})

    # Extract additional context
    context = {
        "code": error_code,
        "raw_error": error_data,
    }

    # Map standard JSON-RPC error codes
    if error_code == -32700:
        return ValidationError(f"Parse error: {error_message}", context=context)
    elif error_code == -32600:
        return ValidationError(f"Invalid request: {error_message}", context=context)
    elif error_code == -32601:
        return MethodNotFoundError(
            f"Method not found: {error_message}", context=context
        )
    elif error_code == -32602:
        return ValidationError(f"Invalid params: {error_message}", context=context)
    elif error_code == -32603:
        return InternalError(
            f"Internal error: {error_message}",
            server_traceback=error_data_dict.get("debug"),
            context=context,
        )

    # Map Odoo-specific errors based on exception type
    error_type = error_data_dict.get("name", "")
    server_traceback = error_data_dict.get("debug")

    # Enhanced error mapping for better user experience
    if "AccessError" in error_type or "AccessDenied" in error_type:
        return AccessError(
            _enhance_access_error_message(error_message),
            server_traceback=server_traceback,
            context=context
        )
    elif "ValidationError" in error_type or "UserError" in error_type:
        return ValidationError(
            _enhance_validation_error_message(error_message),
            context=context
        )
    elif "AuthenticationError" in error_type:
        return AuthenticationError(
            _enhance_auth_error_message(error_message),
            context=context
        )
    elif "MissingError" in error_type:
        return ValidationError(
            f"Record not found: {_enhance_missing_error_message(error_message)}",
            context=context
        )
    elif "IntegrityError" in error_type:
        return ValidationError(
            _enhance_integrity_error_message(error_message),
            context=context
        )
    elif "Warning" in error_type:  # Odoo's Warning exception
        return ValidationError(
            _enhance_warning_message(error_message),
            context=context
        )

    # Check for common error patterns in message
    error_lower = error_message.lower()

    if any(keyword in error_lower for keyword in ["permission", "access denied", "forbidden"]):
        return AccessError(
            _enhance_access_error_message(error_message),
            server_traceback=server_traceback,
            context=context
        )
    elif any(keyword in error_lower for keyword in ["required", "constraint", "invalid"]):
        return ValidationError(
            _enhance_validation_error_message(error_message),
            context=context
        )
    elif any(keyword in error_lower for keyword in ["foreign key", "referenced", "violates"]):
        return ValidationError(
            _enhance_integrity_error_message(error_message),
            context=context
        )

    # Default to generic ZenooError for unknown error types
    # But try to extract meaningful message from server traceback
    enhanced_message = _extract_meaningful_error_message(error_message, error_data_dict)
    return ZenooError(enhanced_message, context=context)


def extract_server_traceback(error_data: Dict[str, Any]) -> str:
    """Extract server traceback from error data.

    Args:
        error_data: The error data from JSON-RPC response

    Returns:
        Server traceback string or empty string if not available
    """
    return error_data.get("data", {}).get("debug", "")


# Error message enhancement functions

def _enhance_access_error_message(message: str) -> str:
    """Enhance access error messages for better user experience."""
    if "access" in message.lower():
        return (
            f"{message}\n\n"
            "This error typically occurs when:\n"
            "• Your user account lacks the required permissions\n"
            "• The record is restricted by access rules\n"
            "• You're trying to access a field with group restrictions\n\n"
            "Please contact your system administrator to review your access rights."
        )
    return message


def _enhance_validation_error_message(message: str) -> str:
    """Enhance validation error messages for better user experience."""
    if "required" in message.lower():
        return (
            f"{message}\n\n"
            "This error occurs when required fields are missing or invalid. "
            "Please ensure all mandatory fields are provided with valid values."
        )
    elif "constraint" in message.lower():
        return (
            f"{message}\n\n"
            "This error occurs when data violates business rules or constraints. "
            "Please check your data and ensure it meets all requirements."
        )
    return message


def _enhance_auth_error_message(message: str) -> str:
    """Enhance authentication error messages for better user experience."""
    return (
        f"{message}\n\n"
        "Authentication failed. Please check:\n"
        "• Your username and password are correct\n"
        "• Your account is active and not locked\n"
        "• The database name is correct\n"
        "• Your session hasn't expired"
    )


def _enhance_missing_error_message(message: str) -> str:
    """Enhance missing record error messages for better user experience."""
    return (
        f"{message}\n\n"
        "The requested record(s) could not be found. This may happen when:\n"
        "• The record has been deleted\n"
        "• You don't have access to view the record\n"
        "• The record ID is incorrect"
    )


def _enhance_integrity_error_message(message: str) -> str:
    """Enhance integrity constraint error messages for better user experience."""
    if "foreign key" in message.lower():
        return (
            f"{message}\n\n"
            "This error occurs when trying to delete or modify a record that is "
            "referenced by other records. Please remove the references first or "
            "use appropriate cascade options."
        )
    elif "unique" in message.lower():
        return (
            f"{message}\n\n"
            "This error occurs when trying to create a duplicate record. "
            "Please ensure the values for unique fields are not already in use."
        )
    return message


def _enhance_warning_message(message: str) -> str:
    """Enhance Odoo Warning messages for better user experience."""
    return (
        f"{message}\n\n"
        "This is a business logic warning from Odoo. "
        "Please review your data and operation to resolve this issue."
    )


def _extract_meaningful_error_message(message: str, error_data: Dict[str, Any]) -> str:
    """Extract meaningful error message from Odoo server response.

    Args:
        message: Original error message
        error_data: Error data dictionary from server

    Returns:
        Enhanced error message with better context
    """
    # If we have a debug traceback, try to extract the actual error
    debug_info = error_data.get("debug", "")

    if debug_info:
        # Look for common error patterns in the traceback
        lines = debug_info.split('\n')

        # Find the last meaningful error line
        for line in reversed(lines):
            line = line.strip()

            # Skip empty lines and generic traceback lines
            if not line or line.startswith('File ') or line.startswith('  '):
                continue

            # Look for specific error patterns
            if any(pattern in line for pattern in [
                'ValueError:', 'UserError:', 'ValidationError:',
                'AccessDenied:', 'IntegrityError:', 'Warning:'
            ]):
                # Extract the actual error message
                if ':' in line:
                    actual_error = line.split(':', 1)[1].strip()
                    if actual_error and actual_error != message:
                        return f"{actual_error}\n\nOriginal: {message}"

    # Check if the message itself contains useful information
    if message and message != "Odoo Server Error":
        return message

    # Fallback to generic message with context
    error_type = error_data.get("name", "Unknown")
    return f"Server error ({error_type}): {message or 'No details available'}"
