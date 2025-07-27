"""
Tests for the HTTP transport layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from zenoo_rpc.transport import AsyncTransport
from zenoo_rpc.exceptions import ConnectionError, TimeoutError


class TestAsyncTransport:
    """Test cases for AsyncTransport."""

    def test_transport_initialization(self):
        """Test transport initialization."""
        transport = AsyncTransport("http://localhost:8069")

        assert transport.base_url == "http://localhost:8069"
        assert isinstance(transport._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test transport as async context manager."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            async with AsyncTransport("http://localhost:8069") as transport:
                assert isinstance(transport, AsyncTransport)

            mock_client_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_json_rpc_call_success(self):
        """Test successful JSON-RPC call."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            # Mock successful response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {"version": "16.0"},
            }
            # Make sure raise_for_status doesn't raise
            mock_response.raise_for_status.return_value = None
            mock_client_instance.post.return_value = mock_response

            transport = AsyncTransport("http://localhost:8069")
            result = await transport.json_rpc_call("common", "version", {}, "test-id")

            assert result["result"] == {"version": "16.0"}
            mock_client_instance.post.assert_called_once_with(
                "/jsonrpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {"service": "common", "method": "version", "args": []},
                    "id": "test-id",
                },
            )

    @pytest.mark.asyncio
    async def test_json_rpc_call_with_args(self):
        """Test JSON-RPC call with arguments."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": [1, 2, 3],
            }
            mock_response.raise_for_status.return_value = None
            mock_client_instance.post.return_value = mock_response

            transport = AsyncTransport("http://localhost:8069")
            result = await transport.json_rpc_call(
                "object",
                "execute_kw",
                {
                    "args": ["db", 1, "password", "res.partner", "search", [[]]],
                    "context": {"lang": "en_US"},
                },
            )

            assert result["result"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_json_rpc_call_server_error(self):
        """Test JSON-RPC call with server error response."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test-id",
                "error": {"code": -32601, "message": "Method not found", "data": {}},
            }
            mock_client_instance.post.return_value = mock_response

            transport = AsyncTransport("http://localhost:8069")

            with pytest.raises(Exception):  # Should be mapped to MethodNotFoundError
                await transport.json_rpc_call("common", "invalid_method", {})

    @pytest.mark.asyncio
    async def test_json_rpc_call_timeout(self):
        """Test JSON-RPC call timeout."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.post.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

            transport = AsyncTransport("http://localhost:8069")

            with pytest.raises(TimeoutError, match="Request timed out"):
                await transport.json_rpc_call("common", "version", {})

    @pytest.mark.asyncio
    async def test_json_rpc_call_connection_error(self):
        """Test JSON-RPC call connection error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.post.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            transport = AsyncTransport("http://localhost:8069")

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await transport.json_rpc_call("common", "version", {})

    @pytest.mark.asyncio
    async def test_json_rpc_call_http_error(self):
        """Test JSON-RPC call HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            # Create a mock response with 500 status
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            http_error = httpx.HTTPStatusError(
                "Server error", request=AsyncMock(), response=mock_response
            )
            mock_client_instance.post.side_effect = http_error

            transport = AsyncTransport("http://localhost:8069")

            with pytest.raises(ConnectionError, match="HTTP error 500"):
                await transport.json_rpc_call("common", "version", {})

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "result": {"version": "16.0"},
            }
            mock_response.raise_for_status.return_value = None
            mock_client_instance.post.return_value = mock_response

            transport = AsyncTransport("http://localhost:8069")
            result = await transport.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.post.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            transport = AsyncTransport("http://localhost:8069")
            result = await transport.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_close(self):
        """Test transport close method."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance

            transport = AsyncTransport("http://localhost:8069")
            await transport.close()

            mock_client_instance.aclose.assert_called_once()
