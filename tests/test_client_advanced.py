"""
Advanced tests for ZenooClient to improve coverage.

This test file focuses on testing advanced scenarios and edge cases
to increase overall coverage for the client module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import (
    AuthenticationError,
    ConnectionError,
    ValidationError,
    AccessError,
    TimeoutError,
    ZenooError
)


class TestZenooClientAdvanced:
    """Advanced test cases for ZenooClient."""

    @pytest.mark.asyncio
    async def test_setup_managers_integration(self):
        """Test setting up all managers together."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.cache.manager.CacheManager"), \
                 patch("zenoo_rpc.transaction.manager.TransactionManager"), \
                 patch("zenoo_rpc.batch.manager.BatchManager"):

                client = ZenooClient("localhost")
                
                # Setup all managers
                await client.setup_cache_manager(backend="memory")
                await client.setup_transaction_manager()
                await client.setup_batch_manager()

                # Verify all managers are set
                assert hasattr(client, '_cache_manager')
                assert hasattr(client, '_transaction_manager')
                assert hasattr(client, '_batch_manager')

    @pytest.mark.asyncio
    async def test_transaction_context_manager_flow(self):
        """Test transaction context manager flow."""
        with patch("zenoo_rpc.transaction.manager.TransactionManager") as mock_tx:
            mock_tx_instance = MagicMock()
            mock_tx.return_value = mock_tx_instance
            mock_context = MagicMock()
            mock_tx_instance.transaction.return_value = mock_context

            client = ZenooClient("localhost")
            client._transaction_manager = mock_tx_instance

            result = client.transaction()
            assert result == mock_context
            mock_tx_instance.transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_context_manager_flow(self):
        """Test batch context manager flow."""
        with patch("zenoo_rpc.batch.manager.BatchManager") as mock_batch:
            mock_batch_instance = MagicMock()
            mock_batch.return_value = mock_batch_instance
            mock_context = MagicMock()
            mock_batch_instance.batch.return_value = mock_context

            client = ZenooClient("localhost")
            client._batch_manager = mock_batch_instance

            result = client.batch()
            assert result == mock_context
            mock_batch_instance.batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_kw_error_mapping(self):
        """Test error mapping in execute_kw."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance
            mock_transport_instance.json_rpc_call.return_value = {
                "error": {
                    "code": 200,
                    "message": "Validation Error",
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

                with patch("zenoo_rpc.client.map_odoo_error") as mock_map:
                    mock_map.side_effect = ValidationError("Validation failed")

                    with pytest.raises(ValidationError):
                        await client.execute_kw("res.partner", "create", [{}])

    @pytest.mark.asyncio
    async def test_crud_operations_comprehensive(self):
        """Test comprehensive CRUD operations."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")

                # Test create
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": 123
                }
                result = await client.create("res.partner", {"name": "Test"})
                assert result == 123

                # Test read
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": [{"id": 123, "name": "Test"}]
                }
                result = await client.read("res.partner", [123])
                assert result == [{"id": 123, "name": "Test"}]

                # Test write
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": True
                }
                result = await client.write("res.partner", [123], {"name": "Updated"})
                assert result is True

                # Test unlink
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": True
                }
                result = await client.unlink("res.partner", [123])
                assert result is True

    @pytest.mark.asyncio
    async def test_search_operations_comprehensive(self):
        """Test comprehensive search operations."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            with patch("zenoo_rpc.client.SessionManager") as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.is_authenticated = True
                mock_session_instance.database = "test_db"
                mock_session_instance.uid = 1
                mock_session_instance.get_call_context.return_value = {}

                client = ZenooClient("localhost")

                # Test search
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": [1, 2, 3]
                }
                result = await client.search("res.partner", [])
                assert result == [1, 2, 3]

                # Test search_count
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": 42
                }
                result = await client.search_count("res.partner", [])
                assert result == 42

                # Test search_read
                mock_transport_instance.json_rpc_call.return_value = {
                    "result": [{"id": 1, "name": "Test"}]
                }
                result = await client.search_read("res.partner", [])
                assert result == [{"id": 1, "name": "Test"}]

    @pytest.mark.asyncio
    async def test_context_merging(self):
        """Test context merging in operations."""
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
                mock_session_instance.get_call_context.return_value = {
                    "lang": "en_US",
                    "tz": "UTC"
                }

                client = ZenooClient("localhost")

                # Test context merging
                await client.execute_kw(
                    "res.partner",
                    "create",
                    [{"name": "Test"}],
                    context={"active_test": False}
                )

                # Verify the call was made
                call_args = mock_transport_instance.json_rpc_call.call_args
                assert call_args is not None

    @pytest.mark.asyncio
    async def test_model_query_builder_integration(self):
        """Test model method integration with query builder."""
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

    @pytest.mark.asyncio
    async def test_authentication_state_properties(self):
        """Test authentication state properties."""
        with patch("zenoo_rpc.client.SessionManager") as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance

            client = ZenooClient("localhost")

            # Test not authenticated
            mock_session_instance.is_authenticated = False
            mock_session_instance.database = None
            mock_session_instance.uid = None
            mock_session_instance.username = None

            assert not client.is_authenticated
            assert client.database is None
            assert client.uid is None
            assert client.username is None

            # Test authenticated
            mock_session_instance.is_authenticated = True
            mock_session_instance.database = "test_db"
            mock_session_instance.uid = 42
            mock_session_instance.username = "test_user"

            assert client.is_authenticated
            assert client.database == "test_db"
            assert client.uid == 42
            assert client.username == "test_user"

    @pytest.mark.asyncio
    async def test_server_info_methods(self):
        """Test server information methods."""
        with patch("zenoo_rpc.client.AsyncTransport") as mock_transport:
            mock_transport_instance = AsyncMock()
            mock_transport.return_value = mock_transport_instance

            client = ZenooClient("localhost")

            # Test get_server_version
            version_info = {"server_version": "16.0"}
            mock_transport_instance.json_rpc_call.return_value = {
                "result": version_info
            }
            result = await client.get_server_version()
            assert result == version_info

            # Test list_databases
            databases = ["db1", "db2"]
            mock_transport_instance.json_rpc_call.return_value = {
                "result": databases
            }
            result = await client.list_databases()
            assert result == databases

    @pytest.mark.asyncio
    async def test_error_scenarios(self):
        """Test various error scenarios."""
        client = ZenooClient("localhost")

        # Test not authenticated errors
        with pytest.raises(AuthenticationError):
            await client.execute_kw("res.partner", "search", [[]])

        with pytest.raises(AuthenticationError):
            client.model(type("TestModel", (), {}))

        # Test manager not initialized errors
        with pytest.raises(RuntimeError):
            client.transaction()

        with pytest.raises(RuntimeError):
            client.batch()
