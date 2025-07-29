"""
Simple tests for ZenooClient to improve coverage.

This test file focuses on testing basic functionality that is missing
from the current test coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import AuthenticationError


class TestZenooClientSimple:
    """Simple test cases for ZenooClient."""

    def test_client_initialization_with_url(self):
        """Test client initialization with different URL formats."""
        # Test with full URL
        client = ZenooClient("https://demo.odoo.com:8080")
        assert client.host == "demo.odoo.com"
        assert client.port == 8080
        assert client.protocol == "https"

        # Test with HTTP URL
        client = ZenooClient("http://localhost:8069")
        assert client.host == "localhost"
        assert client.port == 8069
        assert client.protocol == "http"

        # Test with host only
        client = ZenooClient("example.com")
        assert client.host == "example.com"
        assert client.port == 8069  # Default
        assert client.protocol == "http"  # Default

    def test_client_initialization_with_params(self):
        """Test client initialization with explicit parameters."""
        client = ZenooClient(
            "example.com", 
            port=9000, 
            protocol="https",
            timeout=60
        )
        assert client.host == "example.com"
        assert client.port == 9000
        assert client.protocol == "https"

    def test_session_properties_not_authenticated(self):
        """Test session properties when not authenticated."""
        client = ZenooClient("localhost")
        
        assert not client.is_authenticated
        assert client.database is None
        assert client.uid is None
        assert client.username is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager functionality."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            async with ZenooClient("localhost") as client:
                assert client is not None

            # Verify close was called
            mock_transport_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test close method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance

                client = ZenooClient("localhost")
                await client.close()

                mock_transport_instance.close.assert_called_once()
                mock_session_instance.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_kw_not_authenticated(self):
        """Test execute_kw when not authenticated."""
        client = ZenooClient("localhost")
        
        with pytest.raises(AuthenticationError):
            await client.execute_kw("res.partner", "search", [[]])

    @pytest.mark.asyncio
    async def test_model_not_authenticated(self):
        """Test model method when not authenticated."""
        from zenoo_rpc.models.common import ResPartner
        
        client = ZenooClient("localhost")
        
        with pytest.raises(AuthenticationError):
            client.model(ResPartner)

    def test_transaction_not_initialized(self):
        """Test transaction when manager not initialized."""
        client = ZenooClient("localhost")
        
        with pytest.raises(RuntimeError):
            client.transaction()

    def test_batch_not_initialized(self):
        """Test batch when manager not initialized."""
        client = ZenooClient("localhost")
        
        with pytest.raises(RuntimeError):
            client.batch()

    @pytest.mark.asyncio
    async def test_get_server_version(self):
        """Test get_server_version method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": {"server_version": "16.0"}
            }

            client = ZenooClient("localhost")
            result = await client.get_server_version()
            
            assert result == {"server_version": "16.0"}
            mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_databases(self):
        """Test list_databases method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": ["db1", "db2", "db3"]
            }

            client = ZenooClient("localhost")
            result = await client.list_databases()
            
            assert result == ["db1", "db2", "db3"]
            mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_with_api_key_success(self):
        """Test successful login with API key."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True

                client = ZenooClient("localhost")
                await client.login_with_api_key("test_db", "admin", "api_key")

                mock_session_instance.authenticate_with_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_with_api_key_failure(self):
        """Test login with API key failure."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.authenticate_with_api_key.side_effect = (
                    AuthenticationError("Invalid API key")
                )

                client = ZenooClient("localhost")

                with pytest.raises(AuthenticationError):
                    await client.login_with_api_key("test_db", "admin", "bad_key")

    @pytest.mark.asyncio
    async def test_execute_kw_basic_flow(self):
        """Test basic execute_kw flow when authenticated."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": [1, 2, 3]
            }

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.execute_kw(
                    "res.partner", 
                    "search", 
                    [[]]
                )

                assert result == [1, 2, 3]
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_method_authenticated(self):
        """Test model method when authenticated."""
        from zenoo_rpc.models.common import ResPartner

        with patch("zenoo_rpc.client.SessionManager") as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.is_authenticated = True

            client = ZenooClient("localhost")

            with patch("zenoo_rpc.query.builder.QueryBuilder") as mock_qb:
                mock_builder = MagicMock()
                mock_qb.return_value = mock_builder

                result = client.model(ResPartner)

                assert result == mock_builder
                mock_qb.assert_called_once_with(ResPartner, client)

    def test_session_properties_authenticated(self):
        """Test session properties when authenticated."""
        with patch("zenoo_rpc.client.SessionManager") as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.is_authenticated = True
            mock_session_instance.database = "test_db"
            mock_session_instance.uid = 42
            mock_session_instance.username = "test_user"

            client = ZenooClient("localhost")

            assert client.is_authenticated
            assert client.database == "test_db"
            assert client.uid == 42
            assert client.username == "test_user"
