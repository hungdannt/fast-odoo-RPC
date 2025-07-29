"""
Comprehensive tests for ZenooClient to improve coverage.

This test file focuses on testing scenarios and methods that are not covered
in the basic test_client.py file to increase overall coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from urllib.parse import urlparse

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import (
    AuthenticationError, 
    ConnectionError, 
    ValidationError,
    AccessError,
    TimeoutError,
    ZenooError
)


class TestZenooClientComprehensive:
    """Comprehensive test cases for ZenooClient to improve coverage."""

    def test_parse_host_or_url_full_url(self):
        """Test URL parsing with full URLs."""
        client = ZenooClient("https://demo.odoo.com:8080")
        
        assert client.host == "demo.odoo.com"
        assert client.port == 8080
        assert client.protocol == "https"

    def test_parse_host_or_url_http_url(self):
        """Test URL parsing with HTTP URL."""
        client = ZenooClient("http://localhost:8069")
        
        assert client.host == "localhost"
        assert client.port == 8069
        assert client.protocol == "http"

    def test_parse_host_or_url_host_only(self):
        """Test URL parsing with host only."""
        client = ZenooClient("example.com")
        
        assert client.host == "example.com"
        assert client.port == 8069  # Default port
        assert client.protocol == "http"  # Default protocol

    def test_parse_host_or_url_with_overrides(self):
        """Test URL parsing with parameter overrides."""
        client = ZenooClient("example.com", port=9000, protocol="https")
        
        assert client.host == "example.com"
        assert client.port == 9000
        assert client.protocol == "https"

    def test_parse_host_or_url_https_default_port(self):
        """Test HTTPS URL with default port."""
        client = ZenooClient("https://secure.odoo.com")
        
        assert client.host == "secure.odoo.com"
        assert client.port == 443  # HTTPS default
        assert client.protocol == "https"

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
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.username = "admin"

                client = ZenooClient("localhost")
                await client.login_with_api_key("test_db", "admin", "api_key_123")

                mock_session_instance.authenticate_with_api_key.assert_called_once_with(
                    mock_transport_instance, "test_db", "admin", "api_key_123"
                )

    @pytest.mark.asyncio
    async def test_login_with_api_key_failure(self):
        """Test login with API key failure."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.authenticate_with_api_key.side_effect = AuthenticationError(
                    "Invalid API key"
                )

                client = ZenooClient("localhost")

                with pytest.raises(AuthenticationError, match="Invalid API key"):
                    await client.login_with_api_key("test_db", "admin", "invalid_key")

    def test_session_properties_not_authenticated(self):
        """Test session properties when not authenticated."""
        client = ZenooClient("localhost")
        
        assert not client.is_authenticated
        assert client.database is None
        assert client.uid is None
        assert client.username is None

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

    @pytest.mark.asyncio
    async def test_create_method(self):
        """Test create method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": 123}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.create("res.partner", {"name": "Test Partner"})

                assert result == 123
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_method(self):
        """Test write method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": True}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.write("res.partner", [1, 2], {"name": "Updated"})

                assert result is True
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlink_method(self):
        """Test unlink method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": True}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.unlink("res.partner", [1, 2])

                assert result is True
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_method(self):
        """Test search method."""
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
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.search(
                    "res.partner", 
                    [("is_company", "=", True)], 
                    limit=10, 
                    offset=5
                )

                assert result == [1, 2, 3]
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_method(self):
        """Test read method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": [{"id": 1, "name": "Test"}]
            }

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.read("res.partner", [1], fields=["name"])

                assert result == [{"id": 1, "name": "Test"}]
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_count_method(self):
        """Test search_count method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": 42}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.search_count("res.partner", [("is_company", "=", True)])

                assert result == 42
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_method_not_authenticated(self):
        """Test model method when not authenticated."""
        from zenoo_rpc.models.common import ResPartner
        
        client = ZenooClient("localhost")
        
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            client.model(ResPartner)

    @pytest.mark.asyncio
    async def test_model_method_authenticated(self):
        """Test model method when authenticated."""
        from zenoo_rpc.models.common import ResPartner
        
        with patch("zenoo_rpc.client.SessionManager") as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.is_authenticated = True

            client = ZenooClient("localhost")
            
            with patch("zenoo_rpc.query.builder.QueryBuilder") as mock_query_builder:
                mock_builder_instance = MagicMock()
                mock_query_builder.return_value = mock_builder_instance
                
                result = client.model(ResPartner)
                
                assert result == mock_builder_instance
                mock_query_builder.assert_called_once_with(ResPartner, client)

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
    async def test_context_manager_with_exception(self):
        """Test context manager behavior when exception occurs."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            try:
                async with ZenooClient("localhost") as client:
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Verify close was still called
            mock_transport_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_cache_manager(self):
        """Test setup_cache_manager method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.cache.manager.CacheManager") as mock_cache_mgr:
                mock_cache_instance = MagicMock()
                mock_cache_mgr.return_value = mock_cache_instance

                client = ZenooClient("localhost")
                await client.setup_cache_manager(
                    backend="memory", max_size=1000, ttl=300
                )

                assert hasattr(client, '_cache_manager')
                mock_cache_mgr.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_transaction_manager(self):
        """Test setup_transaction_manager method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch(
                "zenoo_rpc.transaction.manager.TransactionManager"
            ) as mock_tx_mgr:
                mock_tx_instance = MagicMock()
                mock_tx_mgr.return_value = mock_tx_instance

                client = ZenooClient("localhost")
                await client.setup_transaction_manager()

                assert hasattr(client, '_transaction_manager')
                mock_tx_mgr.assert_called_once_with(client=client)

    @pytest.mark.asyncio
    async def test_setup_batch_manager(self):
        """Test setup_batch_manager method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.batch.manager.BatchManager") as mock_batch_mgr:
                mock_batch_instance = MagicMock()
                mock_batch_mgr.return_value = mock_batch_instance

                client = ZenooClient("localhost")
                await client.setup_batch_manager(
                    max_chunk_size=50, max_concurrent_batches=5
                )

                assert hasattr(client, '_batch_manager')
                mock_batch_mgr.assert_called_once()

    def test_transaction_context_not_initialized(self):
        """Test transaction context when manager not initialized."""
        client = ZenooClient("localhost")

        with pytest.raises(RuntimeError, match="Transaction manager not initialized"):
            client.transaction()

    def test_transaction_context_initialized(self):
        """Test transaction context when manager is initialized."""
        with patch("zenoo_rpc.transaction.manager.TransactionManager") as mock_tx_manager:
            mock_tx_instance = MagicMock()
            mock_tx_manager.return_value = mock_tx_instance
            mock_context = MagicMock()
            mock_tx_instance.transaction.return_value = mock_context

            client = ZenooClient("localhost")
            client._transaction_manager = mock_tx_instance

            result = client.transaction()

            assert result == mock_context
            mock_tx_instance.transaction.assert_called_once()

    def test_batch_context_not_initialized(self):
        """Test batch context when manager not initialized."""
        client = ZenooClient("localhost")

        with pytest.raises(RuntimeError, match="Batch manager not initialized"):
            client.batch()

    def test_batch_context_initialized(self):
        """Test batch context when manager is initialized."""
        with patch("zenoo_rpc.batch.manager.BatchManager") as mock_batch_manager:
            mock_batch_instance = MagicMock()
            mock_batch_manager.return_value = mock_batch_instance
            mock_context = MagicMock()
            mock_batch_instance.batch.return_value = mock_context

            client = ZenooClient("localhost")
            client._batch_manager = mock_batch_instance

            result = client.batch()

            assert result == mock_context
            mock_batch_instance.batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_kw_with_context(self):
        """Test execute_kw with custom context."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": "success"}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {"lang": "en_US"}

                client = ZenooClient("localhost")
                result = await client.execute_kw(
                    "res.partner",
                    "search",
                    [[]],
                    context={"active_test": False}
                )

                assert result == "success"
                # Verify the call was made with merged context
                call_args = mock_transport_instance.json_rpc_call.call_args
                assert "active_test" in str(call_args)

    @pytest.mark.asyncio
    async def test_execute_kw_connection_error(self):
        """Test execute_kw with connection error."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.side_effect = ConnectionError("Connection failed")

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")

                with pytest.raises(ConnectionError, match="Connection failed"):
                    await client.execute_kw("res.partner", "search", [[]])

    @pytest.mark.asyncio
    async def test_search_read_with_all_params(self):
        """Test search_read with all parameters."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "result": [{"id": 1, "name": "Test", "email": "test@example.com"}]
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
                    offset=5,
                    order="name ASC",
                    context={"lang": "fr_FR"}
                )

                assert result == [{"id": 1, "name": "Test", "email": "test@example.com"}]
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_context(self):
        """Test create method with context."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {"result": 456}

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")
                result = await client.create(
                    "res.partner",
                    {"name": "Test Partner"},
                    context={"tracking_disable": True}
                )

                assert result == 456
                mock_transport_instance.json_rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_execute_kw(self):
        """Test error handling in execute_kw method."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "error": {
                    "code": 200,
                    "message": "Odoo Server Error",
                    "data": {"name": "odoo.exceptions.ValidationError"}
                }
            }

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")

                # Mock the error mapping
                with patch("zenoo_rpc.client.map_odoo_error") as mock_map_error:
                    mock_map_error.side_effect = ValidationError("Validation failed")

                    with pytest.raises(ValidationError, match="Validation failed"):
                        await client.execute_kw("res.partner", "create", [{}])
