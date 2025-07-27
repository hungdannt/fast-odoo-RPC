import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from src.zenoo_rpc.transport.httpx_transport import AsyncTransport
from src.zenoo_rpc.exceptions import ConnectionError, MethodNotFoundError


@pytest.fixture
def transport():
    """Create an AsyncTransport instance."""
    return AsyncTransport(base_url="http://test.odoo.com", timeout=30.0)


@pytest.mark.asyncio
async def test_transport_initialization(transport):
    """Test AsyncTransport initialization."""
    assert transport.base_url == "http://test.odoo.com"
    assert transport.timeout == 30.0
    assert transport.verify_ssl is True
    assert transport._client is not None


@pytest.mark.asyncio
async def test_transport_json_rpc_call_success():
    """Test successful JSON-RPC call."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"success": True},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        transport = AsyncTransport("http://test.com")
        result = await transport.json_rpc_call("common", "version", {})

        assert result == {"jsonrpc": "2.0", "id": 1, "result": {"success": True}}
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_transport_json_rpc_call_error():
    """Test JSON-RPC call with error response."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock error response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        transport = AsyncTransport("http://test.com")

        with pytest.raises(MethodNotFoundError):
            await transport.json_rpc_call("object", "invalid_method", {})


@pytest.mark.asyncio
async def test_transport_call():
    """Test the call method (XML-RPC style)."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [1, 2, 3],
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        transport = AsyncTransport("http://test.com")
        result = await transport.call(
            "/xmlrpc/2/object",
            "execute_kw",
            "db",
            1,
            "pass",
            "res.partner",
            "search",
            [[]],
        )

        assert result == [1, 2, 3]


@pytest.mark.asyncio
async def test_transport_health_check_success():
    """Test successful health check."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        transport = AsyncTransport("http://test.com")
        result = await transport.health_check()

        assert result is True
        mock_client.get.assert_called_once_with("/web/health")


@pytest.mark.asyncio
async def test_transport_health_check_failure():
    """Test failed health check."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock connection error
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        transport = AsyncTransport("http://test.com")
        result = await transport.health_check()

        assert result is False


@pytest.mark.asyncio
async def test_transport_close():
    """Test closing the transport."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        transport = AsyncTransport("http://test.com")
        await transport.close()

        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_transport_connection_error():
    """Test handling connection errors."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock connection error
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        transport = AsyncTransport("http://test.com")

        with pytest.raises(ConnectionError):
            await transport.json_rpc_call("common", "version", {})


@pytest.mark.asyncio
async def test_transport_timeout():
    """Test request timeout handling."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock timeout error
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")

        transport = AsyncTransport("http://test.com", timeout=1.0)

        with pytest.raises(ConnectionError):
            await transport.json_rpc_call("common", "version", {})


@pytest.mark.asyncio
async def test_transport_context_manager():
    """Test transport as context manager."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncTransport("http://test.com") as transport:
            assert transport._client is not None

        # Should close when exiting context
        mock_client.aclose.assert_called_once()


def test_transport_prepare_json_rpc_payload():
    """Test JSON-RPC payload preparation."""
    transport = AsyncTransport("http://test.com")

    # Note: This is testing internal behavior if the method exists
    # Otherwise, we can test it indirectly through json_rpc_call
    pass  # Placeholder for internal method testing if needed
