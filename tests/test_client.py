"""
Tests for the main Zenoo-RPC client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import AuthenticationError, ConnectionError


class TestZenooClient:
    """Test cases for ZenooClient."""

    def test_client_initialization(self):
        """Test client initialization with default parameters."""
        client = ZenooClient("localhost")

        assert client.host == "localhost"
        assert client.port == 8069
        assert client.protocol == "http"
        assert not client.is_authenticated
        assert client.database is None
        assert client.uid is None

    def test_client_initialization_with_custom_params(self):
        """Test client initialization with custom parameters."""
        client = ZenooClient(
            host_or_url="example.com",
            port=8080,
            protocol="https",
            timeout=60.0,
            verify_ssl=False,
        )

        assert client.host == "example.com"
        assert client.port == 8080
        assert client.protocol == "https"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            async with ZenooClient("localhost") as client:
                assert isinstance(client, ZenooClient)

            # Verify close was called
            mock_transport_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            # Mock session manager
            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.username = "admin"

                client = ZenooClient("localhost")
                await client.login("test_db", "admin", "password")

                # Verify authenticate was called
                mock_session_instance.authenticate.assert_called_once_with(
                    mock_transport_instance, "test_db", "admin", "password"
                )

    @pytest.mark.asyncio
    async def test_login_failure(self):
        """Test login failure."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.authenticate.side_effect = AuthenticationError(
                    "Invalid credentials"
                )

                client = ZenooClient("localhost")

                with pytest.raises(AuthenticationError, match="Invalid credentials"):
                    await client.login("test_db", "admin", "wrong_password")

    @pytest.mark.asyncio
    async def test_execute_kw_not_authenticated(self):
        """Test execute_kw when not authenticated."""
        client = ZenooClient("localhost")

        with pytest.raises(AuthenticationError, match="Not authenticated"):
            await client.execute_kw("res.partner", "search", [[]])

    @pytest.mark.asyncio
    async def test_execute_kw_success(self):
        """Test successful execute_kw call."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": [1, 2, 3]}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {"lang": "en_US"}

                client = ZenooClient("localhost")
                result = await client.execute_kw("res.partner", "search", [[]])

                assert result == [1, 2, 3]
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_read(self):
        """Test search_read method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": [{"id": 1, "name": "Test Partner"}]
            }

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.search_read(
                    "res.partner",
                    [("is_company", "=", True)],
                    fields=["name", "email"],
                    limit=10,
                )

                assert result == [{"id": 1, "name": "Test Partner"}]

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.health_check.return_value = True

            client = ZenooClient("localhost")
            result = await client.health_check()

            assert result is True
            mock_transport_instance.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_server_version(self):
        """Test get server version method."""
        version_info = {
            "server_version": "16.0",
            "server_version_info": [16, 0, 0, "final", 0],
            "protocol_version": 1,
        }

        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": version_info
            }

            client = ZenooClient("localhost")
            result = await client.get_server_version()

            assert result == version_info

    @pytest.mark.asyncio
    async def test_list_databases(self):
        """Test list databases method."""
        databases = ["db1", "db2", "test_db"]

        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": databases}

            client = ZenooClient("localhost")
            result = await client.list_databases()

            assert result == databases
