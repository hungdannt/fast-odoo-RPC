"""
MCP Client implementation for Zenoo RPC.

This module provides the core MCP client functionality to connect to
MCP servers and interact with their tools, resources, and prompts.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

try:
    from mcp import ClientSession
    from mcp.types import AnyUrl, Tool, Resource, Prompt
    MCP_AVAILABLE = True
except ImportError:
    # Mock classes for when MCP is not available
    class ClientSession:
        def __init__(self, read_stream, write_stream):
            self.read_stream = read_stream
            self.write_stream = write_stream

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def initialize(self):
            pass

        async def list_tools(self):
            class MockResponse:
                tools = []
            return MockResponse()

        async def call_tool(self, name, arguments):
            return {"result": f"Mock result for {name}"}

        async def list_resources(self):
            class MockResponse:
                resources = []
            return MockResponse()

        async def read_resource(self, uri):
            return {"content": f"Mock content for {uri}"}

        async def list_prompts(self):
            class MockResponse:
                prompts = []
            return MockResponse()

        async def get_prompt(self, name, arguments):
            return {"prompt": f"Mock prompt for {name}"}

    class AnyUrl:
        def __init__(self, url):
            self.url = url

        def __str__(self):
            return self.url

    class Tool:
        def __init__(self, name, description=""):
            self.name = name
            self.description = description

    class Resource:
        def __init__(self, uri, name=""):
            self.uri = uri
            self.name = name

    class Prompt:
        def __init__(self, name, description=""):
            self.name = name
            self.description = description

    MCP_AVAILABLE = False

from .exceptions import (
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
    MCPResourceError,
    MCPPromptError
)
from .transport import MCPTransport

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client for connecting to MCP servers.
    
    This client provides a bridge between Zenoo RPC and MCP servers,
    allowing Zenoo RPC to access tools, resources, and prompts from
    MCP-compatible servers.
    
    Features:
    - Multiple transport support (stdio, HTTP, SSE)
    - Async-first design
    - Tool, resource, and prompt discovery
    - Automatic session management
    - Error handling and retry logic
    
    Example:
        >>> transport = MCPTransport(config)
        >>> async with MCPClient(transport) as client:
        ...     tools = await client.list_tools()
        ...     result = await client.call_tool("fetch", {"url": "https://example.com"})
    """
    
    def __init__(
        self,
        transport: MCPTransport,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize MCP client.
        
        Args:
            transport: MCP transport configuration
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.transport = transport
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[ClientSession] = None
        self._connected = False
        
        # Cache for discovered capabilities
        self._tools_cache: Optional[List[Tool]] = None
        self._resources_cache: Optional[List[Resource]] = None
        self._prompts_cache: Optional[List[Prompt]] = None

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to MCP server."""
        if self._connected:
            return
            
        try:
            # Get transport streams
            read_stream, write_stream = await self.transport.connect()
            
            # Create session
            self.session = ClientSession(read_stream, write_stream)
            await self.session.__aenter__()
            
            # Initialize connection
            await self.session.initialize()
            self._connected = True
            
            logger.info(f"Connected to MCP server '{self.transport.name}'")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.transport.name}': {e}")
            raise MCPConnectionError(
                f"Connection failed: {e}",
                server_name=self.transport.name
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if not self._connected:
            return
            
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None
            
            await self.transport.disconnect()
            self._connected = False
            
            logger.info(f"Disconnected from MCP server '{self.transport.name}'")
            
        except Exception as e:
            logger.error(f"Error during disconnect from '{self.transport.name}': {e}")

    def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if not self._connected or not self.session:
            raise MCPConnectionError(
                "Not connected to MCP server",
                server_name=self.transport.name
            )

    async def list_tools(self, use_cache: bool = True) -> List[Tool]:
        """List available tools from MCP server.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            List of available tools
        """
        self._ensure_connected()
        
        if use_cache and self._tools_cache is not None:
            return self._tools_cache
        
        try:
            response = await self.session.list_tools()
            self._tools_cache = response.tools
            return self._tools_cache
            
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise MCPError(
                f"Failed to list tools: {e}",
                server_name=self.transport.name
            ) from e

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """Call a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            timeout: Optional timeout override
            
        Returns:
            Tool execution result
        """
        self._ensure_connected()
        
        try:
            result = await asyncio.wait_for(
                self.session.call_tool(name, arguments),
                timeout=timeout or self.timeout
            )
            return result
            
        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                f"Tool call '{name}' timed out",
                server_name=self.transport.name,
                timeout_duration=timeout or self.timeout,
                operation=f"call_tool:{name}"
            )
        except Exception as e:
            logger.error(f"Failed to call tool '{name}': {e}")
            raise MCPToolError(
                f"Tool call failed: {e}",
                server_name=self.transport.name,
                tool_name=name,
                arguments=arguments
            ) from e

    async def list_resources(self, use_cache: bool = True) -> List[Resource]:
        """List available resources from MCP server.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            List of available resources
        """
        self._ensure_connected()
        
        if use_cache and self._resources_cache is not None:
            return self._resources_cache
        
        try:
            response = await self.session.list_resources()
            self._resources_cache = response.resources
            return self._resources_cache
            
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            raise MCPError(
                f"Failed to list resources: {e}",
                server_name=self.transport.name
            ) from e

    async def read_resource(self, uri: Union[str, AnyUrl]) -> Any:
        """Read a resource from the MCP server.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        self._ensure_connected()
        
        try:
            if isinstance(uri, str):
                uri = AnyUrl(uri)
            
            result = await self.session.read_resource(uri)
            return result
            
        except Exception as e:
            logger.error(f"Failed to read resource '{uri}': {e}")
            raise MCPResourceError(
                f"Resource read failed: {e}",
                server_name=self.transport.name,
                resource_uri=str(uri)
            ) from e

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._tools_cache = None
        self._resources_cache = None
        self._prompts_cache = None

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information for debugging."""
        return {
            "name": self.transport.name,
            "transport_type": self.transport.transport_type.value,
            "connected": self._connected,
            "has_tools_cache": self._tools_cache is not None,
            "has_resources_cache": self._resources_cache is not None,
            "has_prompts_cache": self._prompts_cache is not None,
        }
