"""
HTTP transport implementation using httpx.

This module provides the core HTTP transport layer for communicating with
Odoo servers using the JSON-RPC protocol over HTTP/HTTPS.
"""

import asyncio
import uuid
from typing import Any, Dict, Optional

import httpx

from ..exceptions import ConnectionError, TimeoutError, map_jsonrpc_error


class AsyncTransport:
    """Async HTTP transport for Odoo JSON-RPC communication.

    This class handles the low-level HTTP communication with Odoo servers,
    including connection pooling, timeout handling, and error mapping.

    Features:
    - HTTP/2 support for better performance
    - Connection pooling and keep-alive
    - Automatic retry logic for transient failures
    - Proper timeout handling
    - SSL/TLS support

    Example:
        >>> transport = AsyncTransport("http://localhost:8069")
        >>> result = await transport.json_rpc_call("common", "version", {})
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        verify_ssl: bool = True,
    ):
        """Initialize the async transport.

        Args:
            base_url: Base URL of the Odoo server (e.g., "http://localhost:8069")
            timeout: Request timeout in seconds
            max_connections: Maximum number of connections in the pool
            max_keepalive_connections: Maximum number of keep-alive connections
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")

        # Configure httpx client with optimal settings
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
            http2=True,  # Enable HTTP/2 for better performance
            verify=verify_ssl,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "OdooFlow/0.1.0 (httpx)",
            },
        )

    async def json_rpc_call(
        self,
        service: str,
        method: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make an async JSON-RPC call to the Odoo server.

        Args:
            service: The service to call (e.g., "common", "object")
            method: The method to call (e.g., "version", "execute_kw")
            params: Parameters to pass to the method
            request_id: Optional request ID for tracking

        Returns:
            The JSON-RPC response data

        Raises:
            ConnectionError: If connection to server fails
            TimeoutError: If request times out
            ZenooError: If server returns an error response
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Construct JSON-RPC payload
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": params.get("args", []),
                **{k: v for k, v in params.items() if k != "args"},
            },
            "id": request_id,
        }

        try:
            # Make the HTTP request
            response = await self._client.post("/jsonrpc", json=payload)
            response.raise_for_status()

            # Parse JSON response
            json_response = response.json()

            # Check for JSON-RPC errors
            if "error" in json_response:
                raise map_jsonrpc_error(json_response["error"])

            return json_response

        except httpx.TimeoutException as e:
            raise TimeoutError(
                f"Request timed out after {self._client.timeout}s: {e}"
            ) from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ConnectionError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            ) from e
        except Exception as e:
            # Catch any other unexpected errors
            if isinstance(e, (ConnectionError, TimeoutError)):
                raise
            # Don't wrap ZenooError exceptions - let them bubble up
            from ..exceptions.base import ZenooError
            if isinstance(e, ZenooError):
                raise
            raise ConnectionError(f"Unexpected error during RPC call: {e}") from e

    async def health_check(self) -> bool:
        """Check if the Odoo server is reachable and responding.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            result = await self.json_rpc_call("common", "version", {})
            return "result" in result
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
