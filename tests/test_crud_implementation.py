"""Test CRUD implementation in ZenooClient."""

import pytest
from unittest.mock import AsyncMock, patch, call
from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.exceptions import AuthenticationError


@pytest.fixture
async def authenticated_client():
    """Create an authenticated client for testing."""
    client = ZenooClient("http://localhost:8069")

    # Mock the authentication by setting internal attributes
    client._session._database = "test_db"
    client._session._uid = 1
    client._session._username = "admin"
    client._session._password = "admin"

    # Mock execute_kw to avoid actual RPC calls
    client.execute_kw = AsyncMock()

    return client


@pytest.fixture
async def unauthenticated_client():
    """Create an unauthenticated client for testing."""
    client = ZenooClient("http://localhost:8069")
    client.execute_kw = AsyncMock()
    return client


class TestCRUDMethods:
    """Test CRUD methods implementation."""

    async def test_create_method_success(self, authenticated_client):
        """Test successful create operation."""
        # Setup - Mock both the validation call and the create call
        authenticated_client.execute_kw.side_effect = [
            {"name": {"required": False}},  # get_model_fields response
            123  # create response
        ]

        # Execute
        result = await authenticated_client.create(
            "res.partner",
            {"name": "Test Partner", "email": "test@example.com"}
        )

        # Verify
        assert result == 123
        # Enhanced create method makes 2 calls: fields_get + create
        assert authenticated_client.execute_kw.call_count == 2

        # Verify the calls were made in correct order
        calls = authenticated_client.execute_kw.call_args_list
        # First call: get_model_fields (fields_get)
        assert calls[0][0] == ("res.partner", "fields_get", [])
        # Second call: actual create
        assert calls[1][0] == ("res.partner", "create", [{"name": "Test Partner", "email": "test@example.com"}])
        assert calls[1][1] == {"context": None}

    async def test_create_method_with_context(self, authenticated_client):
        """Test create operation with context."""
        # Setup - Mock both validation and create calls
        authenticated_client.execute_kw.side_effect = [
            {"name": {"required": False}},  # get_model_fields response
            124  # create response
        ]
        context = {"lang": "en_US", "tz": "UTC"}

        # Execute
        result = await authenticated_client.create(
            "res.partner",
            {"name": "Test Partner 2"},
            context=context
        )

        # Verify
        assert result == 124
        assert authenticated_client.execute_kw.call_count == 2

        # Verify the calls
        calls = authenticated_client.execute_kw.call_args_list
        # First call: get_model_fields
        assert calls[0][0] == ("res.partner", "fields_get", [])
        # Second call: create with context
        assert calls[1][0] == ("res.partner", "create", [{"name": "Test Partner 2"}])
        assert calls[1][1] == {"context": context}

    async def test_create_method_without_validation(self, authenticated_client):
        """Test create operation with validation disabled."""
        # Setup
        authenticated_client.execute_kw.return_value = 125

        # Execute with validation disabled
        result = await authenticated_client.create(
            "res.partner",
            {"name": "Test Partner"},
            validate_required=False
        )

        # Verify - should only make one call (no validation)
        assert result == 125
        authenticated_client.execute_kw.assert_called_once_with(
            "res.partner",
            "create",
            [{"name": "Test Partner"}],
            context=None
        )

    async def test_create_method_unauthenticated(self, unauthenticated_client):
        """Test create operation when not authenticated."""
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            await unauthenticated_client.create(
                "res.partner",
                {"name": "Test Partner"}
            )

    async def test_write_method_success(self, authenticated_client):
        """Test successful write operation with access checking."""
        # Setup - Mock access check and write calls
        authenticated_client.execute_kw.side_effect = [
            [{"id": 1}, {"id": 2}, {"id": 3}],  # search_read for access check
            True  # write response
        ]

        # Execute
        result = await authenticated_client.write(
            "res.partner",
            [1, 2, 3],
            {"active": False}
        )

        # Verify
        assert result is True
        assert authenticated_client.execute_kw.call_count == 2

        # Verify the calls using call objects
        expected_calls = [
            call("res.partner", "search_read", [[("id", "in", [1, 2, 3])]], {"fields": ["id"], "limit": 3}),
            call("res.partner", "write", [[1, 2, 3], {"active": False}], context=None)
        ]
        authenticated_client.execute_kw.assert_has_calls(expected_calls)

    async def test_write_method_without_access_check(self, authenticated_client):
        """Test write operation with access checking disabled."""
        # Setup
        authenticated_client.execute_kw.return_value = True

        # Execute with access checking disabled
        result = await authenticated_client.write(
            "res.partner",
            [5],
            {"name": "Updated Name"},
            check_access=False
        )

        # Verify - should only make one call (no access check)
        assert result is True
        authenticated_client.execute_kw.assert_called_once_with(
            "res.partner",
            "write",
            [[5], {"name": "Updated Name"}],
            context=None
        )

    async def test_write_method_with_context(self, authenticated_client):
        """Test write operation with context and access checking."""
        # Setup - Mock access check and write calls
        authenticated_client.execute_kw.side_effect = [
            [{"id": 5}],  # search_read for access check
            True  # write response
        ]
        context = {"check_company": True}

        # Execute
        result = await authenticated_client.write(
            "res.partner",
            [5],
            {"name": "Updated Name"},
            context=context
        )

        # Verify
        assert result is True
        assert authenticated_client.execute_kw.call_count == 2

        # Verify the calls using call objects
        expected_calls = [
            call("res.partner", "search_read", [[("id", "in", [5])]], {"fields": ["id"], "limit": 1}),
            call("res.partner", "write", [[5], {"name": "Updated Name"}], context=context)
        ]
        authenticated_client.execute_kw.assert_has_calls(expected_calls)

    async def test_write_method_unauthenticated(self, unauthenticated_client):
        """Test write operation when not authenticated."""
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            await unauthenticated_client.write(
                "res.partner",
                [1],
                {"name": "Test"}
            )

    async def test_unlink_method_success(self, authenticated_client):
        """Test successful unlink operation with access checking."""
        # Setup - Mock access check and unlink calls
        authenticated_client.execute_kw.side_effect = [
            [{"id": 1}, {"id": 2}, {"id": 3}],  # search_read for access check
            True  # unlink response
        ]

        # Execute
        result = await authenticated_client.unlink("res.partner", [1, 2, 3])

        # Verify
        assert result is True
        assert authenticated_client.execute_kw.call_count == 2

        # Verify the calls using call objects
        expected_calls = [
            call("res.partner", "search_read", [[("id", "in", [1, 2, 3])]], {"fields": ["id"], "limit": 3}),
            call("res.partner", "unlink", [[1, 2, 3]], context=None)
        ]
        authenticated_client.execute_kw.assert_has_calls(expected_calls)

    async def test_unlink_method_with_context(self, authenticated_client):
        """Test unlink operation with context and access checking."""
        # Setup - Mock access check and unlink calls
        authenticated_client.execute_kw.side_effect = [
            [{"id": 10}],  # search_read for access check
            True  # unlink response
        ]
        context = {"force_delete": True}

        # Execute
        result = await authenticated_client.unlink(
            "res.partner",
            [10],
            context=context
        )

        # Verify
        assert result is True
        assert authenticated_client.execute_kw.call_count == 2

        # Verify the calls using call objects
        expected_calls = [
            call("res.partner", "search_read", [[("id", "in", [10])]], {"fields": ["id"], "limit": 1}),
            call("res.partner", "unlink", [[10]], context=context)
        ]
        authenticated_client.execute_kw.assert_has_calls(expected_calls)

    async def test_unlink_method_unauthenticated(self, unauthenticated_client):
        """Test unlink operation when not authenticated."""
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            await unauthenticated_client.unlink("res.partner", [1])


class TestManagerSetup:
    """Test manager setup methods."""

    async def test_setup_transaction_manager(self, authenticated_client):
        """Test transaction manager setup."""
        with patch('src.zenoo_rpc.transaction.manager.TransactionManager') as MockTransactionManager:
            mock_manager = AsyncMock()
            MockTransactionManager.return_value = mock_manager
            
            # Execute
            result = await authenticated_client.setup_transaction_manager()
            
            # Verify
            assert result == mock_manager
            assert authenticated_client.transaction_manager == mock_manager
            MockTransactionManager.assert_called_once_with(authenticated_client)

    async def test_setup_cache_manager_memory(self, authenticated_client):
        """Test cache manager setup with memory backend."""
        with patch('src.zenoo_rpc.cache.manager.CacheManager') as MockCacheManager:
            mock_manager = AsyncMock()
            MockCacheManager.return_value = mock_manager
            
            # Execute
            result = await authenticated_client.setup_cache_manager(backend="memory")
            
            # Verify
            assert result == mock_manager
            assert authenticated_client.cache_manager == mock_manager
            mock_manager.setup_memory_cache.assert_called_once()

    async def test_setup_cache_manager_redis(self, authenticated_client):
        """Test cache manager setup with Redis backend."""
        with patch('src.zenoo_rpc.cache.manager.CacheManager') as MockCacheManager:
            mock_manager = AsyncMock()
            MockCacheManager.return_value = mock_manager
            
            # Execute
            result = await authenticated_client.setup_cache_manager(
                backend="redis",
                url="redis://localhost:6379"
            )
            
            # Verify
            assert result == mock_manager
            assert authenticated_client.cache_manager == mock_manager
            mock_manager.setup_redis_cache.assert_called_once_with(
                url="redis://localhost:6379"
            )
