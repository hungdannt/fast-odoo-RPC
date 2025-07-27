import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.exceptions import AuthenticationError


def test_client_initialization_full_url():
    """Test client initialization with full URL."""
    with patch("src.zenoo_rpc.client.AsyncTransport") as mock_transport:
        client = ZenooClient("http://test.com:8080")

        assert client.host == "test.com"
        assert client.port == 8080
        assert client.protocol == "http"


def test_client_initialization_host_only():
    """Test client initialization with host only."""
    with patch("src.zenoo_rpc.client.AsyncTransport") as mock_transport:
        client = ZenooClient("test.com")

        assert client.host == "test.com"
        assert client.port == 8069  # Default port
        assert client.protocol == "http"  # Default protocol


def test_client_initialization_with_params():
    """Test client initialization with separate parameters."""
    with patch("src.zenoo_rpc.client.AsyncTransport") as mock_transport:
        client = ZenooClient("test.com", port=8070, protocol="https")

        assert client.host == "test.com"
        assert client.port == 8070
        assert client.protocol == "https"


@pytest.mark.asyncio
async def test_client_login(mocker):
    """Test client login method."""
    mock_transport = AsyncMock()
    mock_session = AsyncMock()

    with patch("src.zenoo_rpc.client.AsyncTransport", return_value=mock_transport):
        with patch("src.zenoo_rpc.client.SessionManager", return_value=mock_session):
            client = ZenooClient("http://test.com")

            await client.login("test_db", "admin", "password")

            mock_session.authenticate.assert_called_once_with(
                mock_transport, "test_db", "admin", "password"
            )


@pytest.mark.asyncio
async def test_client_execute_kw_not_authenticated():
    """Test execute_kw raises error when not authenticated."""
    with patch("src.zenoo_rpc.client.AsyncTransport") as mock_transport:
        client = ZenooClient("http://test.com")

        with pytest.raises(AuthenticationError, match="Not authenticated"):
            await client.execute_kw("res.partner", "search", [[]])


@pytest.mark.asyncio
async def test_client_search_read(mocker):
    """Test search_read method."""
    mock_transport = AsyncMock()
    mock_session = MagicMock()
    mock_session.is_authenticated = True
    mock_session.database = "test_db"
    mock_session.uid = 123
    mock_session.password = "password"
    mock_session.get_call_context.return_value = None

    mock_transport.json_rpc_call.return_value = {"result": [{"id": 1, "name": "Test"}]}

    with patch("src.zenoo_rpc.client.AsyncTransport", return_value=mock_transport):
        with patch("src.zenoo_rpc.client.SessionManager", return_value=mock_session):
            client = ZenooClient("http://test.com")

            result = await client.search_read(
                "res.partner", [("is_company", "=", True)]
            )

            assert result == [{"id": 1, "name": "Test"}]
            mock_transport.json_rpc_call.assert_called_once()


@pytest.mark.asyncio
async def test_client_close():
    """Test client close method."""
    mock_transport = AsyncMock()
    mock_session = MagicMock()

    with patch("src.zenoo_rpc.client.AsyncTransport", return_value=mock_transport):
        with patch("src.zenoo_rpc.client.SessionManager", return_value=mock_session):
            client = ZenooClient("http://test.com")

            await client.close()

            mock_transport.close.assert_called_once()
            mock_session.clear.assert_called_once()


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client as async context manager."""
    mock_transport = AsyncMock()

    with patch("src.zenoo_rpc.client.AsyncTransport", return_value=mock_transport):
        async with ZenooClient("http://test.com") as client:
            assert client is not None

        # Close should have been called
        mock_transport.close.assert_called_once()


@pytest.mark.asyncio
async def test_client_get_server_version():
    """Test get_server_version method."""
    mock_transport = AsyncMock()
    mock_transport.json_rpc_call.return_value = {
        "result": {
            "server_version": "14.0",
            "server_serie": "14.0",
            "protocol_version": 1,
        }
    }

    with patch("src.zenoo_rpc.client.AsyncTransport", return_value=mock_transport):
        client = ZenooClient("http://test.com")

        version = await client.get_server_version()

        assert version["server_version"] == "14.0"
        mock_transport.json_rpc_call.assert_called_once_with("common", "version", {})


@pytest.mark.asyncio
async def test_client_model_requires_authentication():
    """Test model method requires authentication."""
    with patch("src.zenoo_rpc.client.AsyncTransport"):
        client = ZenooClient("http://test.com")

        with pytest.raises(AuthenticationError, match="Not authenticated"):
            from src.zenoo_rpc.models.common import ResPartner

            client.model(ResPartner)
