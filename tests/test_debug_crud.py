"""Debug CRUD implementation tests."""

import pytest
from unittest.mock import AsyncMock
from src.zenoo_rpc.client import ZenooClient


@pytest.fixture
async def debug_client():
    """Create an authenticated client for debugging."""
    client = ZenooClient("http://localhost:8069")

    # Mock the authentication by setting internal attributes
    client._session._database = "test_db"
    client._session._uid = 1
    client._session._username = "admin"
    client._session._password = "admin"

    # Mock execute_kw to avoid actual RPC calls
    client.execute_kw = AsyncMock()

    return client


class TestDebugCRUD:
    """Debug CRUD methods implementation."""

    async def test_debug_write_method(self, debug_client):
        """Debug write method call patterns."""
        # Setup - Mock access check and write calls
        debug_client.execute_kw.side_effect = [
            [{"id": 1}, {"id": 2}, {"id": 3}],  # search_read for access check
            True  # write response
        ]
        
        # Execute
        result = await debug_client.write(
            "res.partner",
            [1, 2, 3],
            {"active": False}
        )
        
        # Debug: Print all calls
        print(f"Call count: {debug_client.execute_kw.call_count}")
        print(f"All calls: {debug_client.execute_kw.call_args_list}")
        
        for i, call in enumerate(debug_client.execute_kw.call_args_list):
            print(f"Call {i}: args={call[0]}, kwargs={call[1]}")
        
        # Verify
        assert result is True
        assert debug_client.execute_kw.call_count == 2

    async def test_debug_write_without_access_check(self, debug_client):
        """Debug write method without access checking."""
        # Setup
        debug_client.execute_kw.return_value = True
        
        # Execute with access checking disabled
        result = await debug_client.write(
            "res.partner",
            [1, 2, 3],
            {"active": False},
            check_access=False
        )
        
        # Debug: Print all calls
        print(f"Call count: {debug_client.execute_kw.call_count}")
        print(f"All calls: {debug_client.execute_kw.call_args_list}")
        
        # Verify - should only make one call (no access check)
        assert result is True
        assert debug_client.execute_kw.call_count == 1
        
        # Verify the single call
        call = debug_client.execute_kw.call_args_list[0]
        print(f"Single call: args={call[0]}, kwargs={call[1]}")
        assert call[0] == ("res.partner", "write", [[1, 2, 3], {"active": False}])
        assert call[1] == {"context": None}
