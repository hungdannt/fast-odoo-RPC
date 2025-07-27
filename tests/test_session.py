import pytest
from unittest.mock import AsyncMock
from src.zenoo_rpc.transport.session import SessionManager
from src.zenoo_rpc.exceptions import AuthenticationError


@pytest.fixture
async def session_manager():
    return SessionManager()


@pytest.fixture
async def transport_mock():
    return AsyncMock()


async def test_initial_state(session_manager):
    assert session_manager.database is None
    assert session_manager.uid is None
    assert session_manager.username is None
    assert session_manager.password is None
    assert session_manager.context == {}
    assert session_manager.server_version is None
    assert not session_manager.is_authenticated


async def test_authenticate_success(session_manager, transport_mock):
    transport_mock.json_rpc_call.side_effect = [
        {"result": {"server_version": "14.0"}},  # Mock version response
        {"result": 1},  # Mock success authentication
        {"result": {"lang": "en_US", "tz": "UTC"}},  # Mock context response
    ]
    await session_manager.authenticate(transport_mock, "mydb", "admin", "password")
    assert session_manager.is_authenticated
    assert session_manager.database == "mydb"
    assert session_manager.uid == 1
    assert session_manager.username == "admin"
    assert session_manager.password == "password"
    assert session_manager.server_version == {"server_version": "14.0"}


async def test_authenticate_failure(session_manager, transport_mock):
    transport_mock.json_rpc_call.side_effect = [
        {"result": {"server_version": "14.0"}},  # Mock version response
        {"result": None},  # Mock failure authentication
    ]
    with pytest.raises(
        AuthenticationError, match="Authentication failed for user 'admin'"
    ):
        await session_manager.authenticate(transport_mock, "mydb", "admin", "password")


async def test_authenticate_exception_handling(session_manager, transport_mock):
    transport_mock.json_rpc_call.side_effect = Exception("Network error")
    with pytest.raises(
        AuthenticationError, match="Authentication failed: Network error"
    ):
        await session_manager.authenticate(transport_mock, "mydb", "admin", "password")


async def test_authenticate_with_api_key_success(session_manager, transport_mock):
    transport_mock.json_rpc_call.side_effect = [
        {"result": {"server_version": "14.0"}},  # Mock version response
        {"result": 1},  # Mock success authentication with API key
        {"result": {"lang": "en_US", "tz": "UTC"}},  # Mock context response
    ]
    await session_manager.authenticate_with_api_key(
        transport_mock, "mydb", "admin", "api_key"
    )
    assert session_manager.is_authenticated
    assert session_manager.database == "mydb"
    assert session_manager.uid == 1
    assert session_manager.username == "admin"


async def test_authenticate_with_api_key_failure(session_manager, transport_mock):
    transport_mock.json_rpc_call.side_effect = [
        {"result": {"server_version": "14.0"}},  # Mock version response
        {"result": None},  # Mock failure authentication
    ]
    with pytest.raises(
        AuthenticationError, match="API key authentication failed for user 'admin'"
    ):
        await session_manager.authenticate_with_api_key(
            transport_mock, "mydb", "admin", "api_key"
        )


async def test_authenticate_with_api_key_exception(session_manager, transport_mock):
    transport_mock.json_rpc_call.side_effect = Exception("Network error")
    with pytest.raises(
        AuthenticationError, match="API key authentication failed: Network error"
    ):
        await session_manager.authenticate_with_api_key(
            transport_mock, "mydb", "admin", "api_key"
        )


async def test_load_user_context_success(session_manager, transport_mock):
    # Set up authenticated state
    session_manager._database = "mydb"
    session_manager._uid = 1

    transport_mock.json_rpc_call.return_value = {
        "result": {"lang": "fr_FR", "tz": "Europe/Paris", "custom": "value"}
    }

    await session_manager._load_user_context(transport_mock)
    assert session_manager.context == {
        "lang": "fr_FR",
        "tz": "Europe/Paris",
        "custom": "value",
    }


async def test_load_user_context_not_authenticated(session_manager, transport_mock):
    # When not authenticated, should return without doing anything
    await session_manager._load_user_context(transport_mock)
    transport_mock.json_rpc_call.assert_not_called()


async def test_load_user_context_default_on_error(session_manager, transport_mock):
    # Set up authenticated state
    session_manager._database = "mydb"
    session_manager._uid = 1

    transport_mock.json_rpc_call.side_effect = Exception("Failed to load context")
    await session_manager._load_user_context(transport_mock)
    assert session_manager.context == {"lang": "en_US", "tz": "UTC", "uid": 1}


async def test_get_call_context_no_additional(session_manager):
    session_manager._context = {"lang": "en_US", "tz": "UTC"}
    context = session_manager.get_call_context()
    assert context == {"lang": "en_US", "tz": "UTC"}


async def test_get_call_context_with_additional(session_manager):
    session_manager._context = {"lang": "en_US", "tz": "UTC"}
    context = session_manager.get_call_context({"custom_key": "value", "lang": "fr_FR"})
    assert context == {"lang": "fr_FR", "tz": "UTC", "custom_key": "value"}


async def test_clear(session_manager, transport_mock):
    # First authenticate to set values
    transport_mock.json_rpc_call.side_effect = [
        {"result": {"server_version": "14.0"}},
        {"result": 1},
        {"result": {"lang": "en_US"}},
    ]
    await session_manager.authenticate(transport_mock, "mydb", "admin", "password")

    # Then clear
    session_manager.clear()
    assert not session_manager.is_authenticated
    assert session_manager.database is None
    assert session_manager.uid is None
    assert session_manager.username is None
    # Note: password is not cleared by the clear() method
    assert session_manager.context == {}
    assert session_manager.server_version is None
