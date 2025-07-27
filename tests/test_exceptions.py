"""
Tests for Zenoo-RPC exception handling.
"""

import pytest

from zenoo_rpc.exceptions import (
    AccessError,
    AuthenticationError,
    InternalError,
    MethodNotFoundError,
    ZenooError,
    ValidationError,
    map_jsonrpc_error,
)


class TestExceptions:
    """Test cases for Zenoo-RPC exceptions."""

    def test_base_exception(self):
        """Test base ZenooError exception."""
        context = {"code": -32000, "details": "test"}
        error = ZenooError("Test error", context=context)

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context == context

    def test_validation_error_with_field(self):
        """Test ValidationError with field information."""
        error = ValidationError("Invalid value", field="name")

        assert str(error) == "Invalid value"
        assert error.field == "name"

    def test_access_error_with_traceback(self):
        """Test AccessError with server traceback."""
        traceback = "Traceback (most recent call last):\n  File..."
        error = AccessError("Access denied", server_traceback=traceback)

        assert str(error) == "Access denied"
        assert error.server_traceback == traceback

    def test_internal_error_with_traceback(self):
        """Test InternalError with server traceback."""
        traceback = "Traceback (most recent call last):\n  File..."
        error = InternalError("Internal server error", server_traceback=traceback)

        assert str(error) == "Internal server error"
        assert error.server_traceback == traceback


class TestErrorMapping:
    """Test cases for JSON-RPC error mapping."""

    def test_map_parse_error(self):
        """Test mapping of JSON-RPC parse error."""
        error_data = {"code": -32700, "message": "Parse error", "data": {}}

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ValidationError)
        assert "Parse error" in str(exception)
        assert exception.context["code"] == -32700

    def test_map_invalid_request(self):
        """Test mapping of invalid request error."""
        error_data = {"code": -32600, "message": "Invalid Request", "data": {}}

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ValidationError)
        assert "Invalid request" in str(exception)

    def test_map_method_not_found(self):
        """Test mapping of method not found error."""
        error_data = {"code": -32601, "message": "Method not found", "data": {}}

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, MethodNotFoundError)
        assert "Method not found" in str(exception)

    def test_map_invalid_params(self):
        """Test mapping of invalid params error."""
        error_data = {"code": -32602, "message": "Invalid params", "data": {}}

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ValidationError)
        assert "Invalid params" in str(exception)

    def test_map_internal_error(self):
        """Test mapping of internal error."""
        error_data = {
            "code": -32603,
            "message": "Internal error",
            "data": {"debug": "Traceback..."},
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, InternalError)
        assert "Internal error" in str(exception)
        assert exception.server_traceback == "Traceback..."

    def test_map_odoo_access_error(self):
        """Test mapping of Odoo AccessError."""
        error_data = {
            "code": -32000,
            "message": "Access Denied",
            "data": {
                "name": "odoo.exceptions.AccessError",
                "debug": "Access denied for user...",
            },
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, AccessError)
        assert str(exception) == "Access Denied"
        assert exception.server_traceback == "Access denied for user..."

    def test_map_odoo_validation_error(self):
        """Test mapping of Odoo ValidationError."""
        error_data = {
            "code": -32000,
            "message": "Validation failed",
            "data": {
                "name": "odoo.exceptions.ValidationError",
                "debug": "Field validation failed...",
            },
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ValidationError)
        assert str(exception) == "Validation failed"

    def test_map_odoo_user_error(self):
        """Test mapping of Odoo UserError."""
        error_data = {
            "code": -32000,
            "message": "User error occurred",
            "data": {
                "name": "odoo.exceptions.UserError",
                "debug": "User error details...",
            },
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ValidationError)
        assert str(exception) == "User error occurred"

    def test_map_odoo_authentication_error(self):
        """Test mapping of Odoo AuthenticationError."""
        error_data = {
            "code": -32000,
            "message": "Authentication failed",
            "data": {
                "name": "odoo.exceptions.AuthenticationError",
                "debug": "Invalid credentials...",
            },
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, AuthenticationError)
        assert str(exception) == "Authentication failed"

    def test_map_odoo_missing_error(self):
        """Test mapping of Odoo MissingError."""
        error_data = {
            "code": -32000,
            "message": "Record does not exist",
            "data": {
                "name": "odoo.exceptions.MissingError",
                "debug": "Record not found...",
            },
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ValidationError)
        assert "Record not found" in str(exception)

    def test_map_unknown_error(self):
        """Test mapping of unknown error type."""
        error_data = {
            "code": -32000,
            "message": "Unknown error",
            "data": {"name": "some.unknown.Error", "debug": "Unknown error details..."},
        }

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ZenooError)
        assert "Server error: Unknown error" in str(exception)

    def test_map_error_without_message(self):
        """Test mapping error without message."""
        error_data = {"code": -32000, "data": {}}

        exception = map_jsonrpc_error(error_data)

        assert isinstance(exception, ZenooError)
        assert "Unknown error" in str(exception)
