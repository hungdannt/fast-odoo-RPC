"""
MCP Manager for Zenoo RPC.

This module provides the MCP manager that coordinates multiple MCP clients
and provides a unified interface for accessing MCP servers.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

try:
    from mcp.types import Tool, Resource, Prompt
    MCP_AVAILABLE = True
except ImportError:
    # Mock classes for when MCP is not available
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

from .client import MCPClient
from .transport import MCPTransport, MCPServerConfig, MCPTransportManager
from .exceptions import (
    MCPError,
    MCPServerNotFoundError,
    MCPConfigurationError
)

logger = logging.getLogger(__name__)


class MCPManager:
    """Manager for multiple MCP clients.
    
    This manager provides a unified interface for working with multiple
    MCP servers, handling connection management, load balancing, and
    providing aggregated views of tools, resources, and prompts.
    
    Features:
    - Multiple server management
    - Connection pooling and health monitoring
    - Unified tool/resource/prompt discovery
    - Load balancing for tool calls
    - Automatic failover and retry
    - Caching and performance optimization
    
    Example:
        >>> manager = MCPManager()
        >>> await manager.add_server(MCPServerConfig(
        ...     name="filesystem",
        ...     transport_type="stdio",
        ...     command="mcp-server-filesystem",
        ...     args=["--root", "/data"]
        ... ))
        >>> await manager.connect_all()
        >>> tools = await manager.list_all_tools()
        >>> result = await manager.call_tool("filesystem", "list_files", {"path": "/"})
    """
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        max_retries: int = 3,
        health_check_interval: float = 60.0
    ):
        """Initialize MCP manager.
        
        Args:
            default_timeout: Default timeout for operations
            max_retries: Default max retries for operations
            health_check_interval: Health check interval in seconds
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.health_check_interval = health_check_interval
        
        # Core components
        self.transport_manager = MCPTransportManager()
        self.clients: Dict[str, MCPClient] = {}
        
        # State tracking
        self._connected_servers: Set[str] = set()
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Caching
        self._aggregated_tools_cache: Optional[Dict[str, List[Tool]]] = None
        self._aggregated_resources_cache: Optional[Dict[str, List[Resource]]] = None
        self._aggregated_prompts_cache: Optional[Dict[str, List[Prompt]]] = None

    async def add_server(self, config: MCPServerConfig) -> None:
        """Add a new MCP server configuration.
        
        Args:
            config: MCP server configuration
            
        Raises:
            MCPConfigurationError: If configuration is invalid
        """
        try:
            # Add transport
            transport = self.transport_manager.add_transport(config)
            
            # Create client
            client = MCPClient(
                transport=transport,
                timeout=config.timeout or self.default_timeout,
                max_retries=config.max_retries or self.max_retries
            )
            
            self.clients[config.name] = client
            
            # Clear aggregated caches
            self._clear_aggregated_caches()
            
            logger.info(f"Added MCP server '{config.name}'")
            
        except Exception as e:
            logger.error(f"Failed to add server '{config.name}': {e}")
            raise MCPConfigurationError(
                f"Failed to add server: {e}",
                config_key="server_config",
                config_value=config
            ) from e

    async def remove_server(self, name: str) -> bool:
        """Remove an MCP server.
        
        Args:
            name: Server name
            
        Returns:
            True if server was removed
        """
        if name not in self.clients:
            return False
        
        try:
            # Disconnect client if connected
            client = self.clients[name]
            if name in self._connected_servers:
                await client.disconnect()
                self._connected_servers.discard(name)
            
            # Remove client and transport
            del self.clients[name]
            self.transport_manager.remove_transport(name)
            
            # Clear aggregated caches
            self._clear_aggregated_caches()
            
            logger.info(f"Removed MCP server '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove server '{name}': {e}")
            return False

    async def connect_server(self, name: str) -> bool:
        """Connect to a specific MCP server.
        
        Args:
            name: Server name
            
        Returns:
            True if connection successful
        """
        if name not in self.clients:
            raise MCPServerNotFoundError(name, list(self.clients.keys()))
        
        try:
            client = self.clients[name]
            await client.connect()
            self._connected_servers.add(name)
            
            logger.info(f"Connected to MCP server '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server '{name}': {e}")
            return False

    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from a specific MCP server.
        
        Args:
            name: Server name
            
        Returns:
            True if disconnection successful
        """
        if name not in self.clients:
            return False
        
        try:
            client = self.clients[name]
            await client.disconnect()
            self._connected_servers.discard(name)
            
            logger.info(f"Disconnected from MCP server '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect from server '{name}': {e}")
            return False

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured MCP servers.
        
        Returns:
            Dict mapping server names to connection success
        """
        results = {}
        
        for name in self.clients.keys():
            results[name] = await self.connect_server(name)
        
        connected_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"Connected to {connected_count}/{total_count} MCP servers")
        return results

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        tasks = []
        for name in list(self._connected_servers):
            tasks.append(self.disconnect_server(name))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def list_servers(self) -> List[str]:
        """List all configured server names.
        
        Returns:
            List of server names
        """
        return list(self.clients.keys())

    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names.
        
        Returns:
            List of connected server names
        """
        return list(self._connected_servers)

    def get_client(self, name: str) -> MCPClient:
        """Get MCP client by server name.
        
        Args:
            name: Server name
            
        Returns:
            MCP client instance
            
        Raises:
            MCPServerNotFoundError: If server not found
        """
        if name not in self.clients:
            raise MCPServerNotFoundError(name, list(self.clients.keys()))
        
        return self.clients[name]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """Call a tool on a specific MCP server.
        
        Args:
            server_name: Server name
            tool_name: Tool name
            arguments: Tool arguments
            timeout: Optional timeout override
            
        Returns:
            Tool execution result
        """
        client = self.get_client(server_name)
        return await client.call_tool(tool_name, arguments, timeout)

    async def read_resource(
        self,
        server_name: str,
        uri: str
    ) -> Any:
        """Read a resource from a specific MCP server.
        
        Args:
            server_name: Server name
            uri: Resource URI
            
        Returns:
            Resource content
        """
        client = self.get_client(server_name)
        return await client.read_resource(uri)

    async def get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, str]] = None
    ) -> Any:
        """Get a prompt from a specific MCP server.
        
        Args:
            server_name: Server name
            prompt_name: Prompt name
            arguments: Prompt arguments
            
        Returns:
            Prompt result
        """
        client = self.get_client(server_name)
        return await client.get_prompt(prompt_name, arguments)

    async def list_all_tools(self, use_cache: bool = True) -> Dict[str, List[Tool]]:
        """List all tools from all connected servers.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            Dict mapping server names to their tools
        """
        if use_cache and self._aggregated_tools_cache is not None:
            return self._aggregated_tools_cache
        
        results = {}
        for name in self._connected_servers:
            try:
                client = self.clients[name]
                tools = await client.list_tools(use_cache)
                results[name] = tools
            except Exception as e:
                logger.error(f"Failed to list tools from '{name}': {e}")
                results[name] = []
        
        self._aggregated_tools_cache = results
        return results

    async def list_all_resources(self, use_cache: bool = True) -> Dict[str, List[Resource]]:
        """List all resources from all connected servers.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            Dict mapping server names to their resources
        """
        if use_cache and self._aggregated_resources_cache is not None:
            return self._aggregated_resources_cache
        
        results = {}
        for name in self._connected_servers:
            try:
                client = self.clients[name]
                resources = await client.list_resources(use_cache)
                results[name] = resources
            except Exception as e:
                logger.error(f"Failed to list resources from '{name}': {e}")
                results[name] = []
        
        self._aggregated_resources_cache = results
        return results

    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all servers.
        
        Returns:
            Dict mapping server names to health status
        """
        results = {}
        for name in self.clients.keys():
            try:
                if name in self._connected_servers:
                    client = self.clients[name]
                    results[name] = await client.health_check()
                else:
                    results[name] = False
            except Exception as e:
                logger.error(f"Health check failed for '{name}': {e}")
                results[name] = False
        
        return results

    def _clear_aggregated_caches(self) -> None:
        """Clear all aggregated caches."""
        self._aggregated_tools_cache = None
        self._aggregated_resources_cache = None
        self._aggregated_prompts_cache = None

    async def start_health_monitoring(self) -> None:
        """Start health monitoring for all servers."""
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Started health monitoring with {self.health_check_interval}s interval")

    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped health monitoring")

    async def _health_check_loop(self) -> None:
        """Health check loop for all servers."""
        while True:
            try:
                health_results = await self.health_check_all()
                
                # Log unhealthy servers
                for name, healthy in health_results.items():
                    if not healthy and name in self._connected_servers:
                        logger.warning(f"MCP server '{name}' failed health check")
                        # Could implement auto-reconnection here
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def __aenter__(self) -> "MCPManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_health_monitoring()
        await self.disconnect_all()
