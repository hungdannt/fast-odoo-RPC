import pytest
from src.zenoo_rpc.exceptions.mapping import map_jsonrpc_error, extract_server_traceback
from src.zenoo_rpc.exceptions import ZenooError, ValidationError, AccessError


def test_map_jsonrpc_error_validation():
    """Test mapping validation errors."""
    error_data = {
        "code": 200,
        "message": "Validation Error",
        "data": {
            "name": "odoo.exceptions.ValidationError",
            "debug": "Field validation failed",
        },
    }

    mapped_error = map_jsonrpc_error(error_data)
    assert isinstance(mapped_error, ValidationError)
    assert "Validation Error" in str(mapped_error)


def test_map_jsonrpc_error_access():
    """Test mapping access errors."""
    error_data = {
        "code": 403,
        "message": "Access Denied",
        "data": {
            "name": "odoo.exceptions.AccessError",
            "debug": "You don't have access to this resource",
        },
    }

    mapped_error = map_jsonrpc_error(error_data)
    assert isinstance(mapped_error, AccessError)
    assert "Access Denied" in str(mapped_error)


def test_map_jsonrpc_error_generic():
    """Test mapping generic errors."""
    error_data = {
        "code": 500,
        "message": "Internal Server Error",
        "data": {"name": "UnknownError", "debug": "Something went wrong"},
    }

    mapped_error = map_jsonrpc_error(error_data)
    assert isinstance(mapped_error, ZenooError)
    assert "Internal Server Error" in str(mapped_error)


def test_map_jsonrpc_error_missing_data():
    """Test mapping errors with missing data."""
    error_data = {"code": 400, "message": "Bad Request"}

    mapped_error = map_jsonrpc_error(error_data)
    assert isinstance(mapped_error, ZenooError)
    assert "Bad Request" in str(mapped_error)


def test_map_jsonrpc_error_standard_codes():
    """Test mapping standard JSON-RPC error codes."""
    # Parse error
    error = map_jsonrpc_error({"code": -32700, "message": "Parse error"})
    assert isinstance(error, ValidationError)
    assert "Parse error" in str(error)

    # Method not found
    from src.zenoo_rpc.exceptions import MethodNotFoundError

    error = map_jsonrpc_error({"code": -32601, "message": "Method not found"})
    assert isinstance(error, MethodNotFoundError)

    # Internal error
    from src.zenoo_rpc.exceptions import InternalError

    error = map_jsonrpc_error({"code": -32603, "message": "Internal error"})
    assert isinstance(error, InternalError)


def test_extract_server_traceback():
    """Test extracting server traceback."""
    error_data = {
        "code": 500,
        "message": "Error",
        "data": {"debug": "Traceback (most recent call last):\n  File..."},
    }

    traceback = extract_server_traceback(error_data)
    assert "Traceback" in traceback

    # Test with missing debug
    error_data_no_debug = {"code": 500, "message": "Error"}
    traceback = extract_server_traceback(error_data_no_debug)
    assert traceback == ""
