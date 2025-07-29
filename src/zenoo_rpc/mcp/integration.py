"""
MCP Integration for Zenoo RPC Client.

This module provides integration between the main ZenooClient and MCP functionality,
allowing seamless access to MCP servers alongside Odoo operations.
"""

import logging
from typing import Any, Dict, List, Optional

from .manager import MCPManager
from .transport import MCPServerConfig
from .exceptions import MCPError, MCPServerNotFoundError

logger = logging.getLogger(__name__)


class MCPIntegration:
    """MCP integration mixin for ZenooClient.
    
    This class provides MCP functionality that can be mixed into
    the main ZenooClient class, enabling MCP operations alongside
    Odoo RPC operations.
    
    Features:
    - MCP server management
    - Tool calling integration
    - Resource access
    - AI assistant integration
    - Unified error handling
    """
    
    def __init__(self):
        """Initialize MCP integration."""
        self._mcp_manager: Optional[MCPManager] = None
        self._mcp_enabled = False

    async def setup_mcp_manager(
        self,
        servers: List[MCPServerConfig],
        auto_connect: bool = True,
        health_monitoring: bool = True,
        **kwargs
    ) -> None:
        """Setup MCP manager with server configurations.
        
        Args:
            servers: List of MCP server configurations
            auto_connect: Whether to automatically connect to all servers
            health_monitoring: Whether to enable health monitoring
            **kwargs: Additional MCP manager options
            
        Example:
            >>> await client.setup_mcp_manager([
            ...     MCPServerConfig(
            ...         name="filesystem",
            ...         transport_type="stdio",
            ...         command="mcp-server-filesystem",
            ...         args=["--root", "/data"]
            ...     ),
            ...     MCPServerConfig(
            ...         name="database",
            ...         transport_type="http",
            ...         url="http://localhost:8000/mcp"
            ...     )
            ... ])
        """
        try:
            # Create MCP manager
            self._mcp_manager = MCPManager(**kwargs)
            
            # Add all servers
            for server_config in servers:
                await self._mcp_manager.add_server(server_config)
            
            # Auto-connect if requested
            if auto_connect:
                connection_results = await self._mcp_manager.connect_all()
                
                # Log connection results
                connected = sum(connection_results.values())
                total = len(connection_results)
                logger.info(f"MCP: Connected to {connected}/{total} servers")
                
                if connected == 0:
                    logger.warning("MCP: No servers connected successfully")
                elif connected < total:
                    failed_servers = [
                        name for name, success in connection_results.items() 
                        if not success
                    ]
                    logger.warning(f"MCP: Failed to connect to servers: {failed_servers}")
            
            # Start health monitoring if requested
            if health_monitoring:
                await self._mcp_manager.start_health_monitoring()
            
            self._mcp_enabled = True
            logger.info("MCP integration enabled successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup MCP manager: {e}")
            raise MCPError(f"MCP setup failed: {e}") from e

    async def mcp_call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """Call a tool on an MCP server.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Optional timeout override
            
        Returns:
            Tool execution result
            
        Example:
            >>> # List files using filesystem MCP server
            >>> files = await client.mcp_call_tool(
            ...     "filesystem",
            ...     "list_files", 
            ...     {"path": "/data/reports"}
            ... )
            
            >>> # Query database using database MCP server
            >>> results = await client.mcp_call_tool(
            ...     "database",
            ...     "execute_query",
            ...     {"sql": "SELECT * FROM customers LIMIT 10"}
            ... )
        """
        self._ensure_mcp_enabled()
        
        try:
            return await self._mcp_manager.call_tool(
                server_name, tool_name, arguments, timeout
            )
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            raise

    async def mcp_read_resource(
        self,
        server_name: str,
        uri: str
    ) -> Any:
        """Read a resource from an MCP server.
        
        Args:
            server_name: Name of the MCP server
            uri: Resource URI
            
        Returns:
            Resource content
            
        Example:
            >>> # Read a file using filesystem MCP server
            >>> content = await client.mcp_read_resource(
            ...     "filesystem",
            ...     "file:///data/reports/sales.csv"
            ... )
            
            >>> # Read configuration from config MCP server
            >>> config = await client.mcp_read_resource(
            ...     "config",
            ...     "config://database/connection"
            ... )
        """
        self._ensure_mcp_enabled()
        
        try:
            return await self._mcp_manager.read_resource(server_name, uri)
        except Exception as e:
            logger.error(f"MCP resource read failed: {e}")
            raise

    async def mcp_get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, str]] = None
    ) -> Any:
        """Get a prompt from an MCP server.
        
        Args:
            server_name: Name of the MCP server
            prompt_name: Name of the prompt
            arguments: Prompt arguments
            
        Returns:
            Prompt result
            
        Example:
            >>> # Get analysis prompt template
            >>> prompt = await client.mcp_get_prompt(
            ...     "templates",
            ...     "data_analysis",
            ...     {"dataset": "sales", "period": "monthly"}
            ... )
        """
        self._ensure_mcp_enabled()
        
        try:
            return await self._mcp_manager.get_prompt(
                server_name, prompt_name, arguments
            )
        except Exception as e:
            logger.error(f"MCP prompt get failed: {e}")
            raise

    async def mcp_list_servers(self) -> List[str]:
        """List all configured MCP servers.
        
        Returns:
            List of server names
        """
        self._ensure_mcp_enabled()
        return self._mcp_manager.list_servers()

    async def mcp_get_connected_servers(self) -> List[str]:
        """Get list of connected MCP servers.
        
        Returns:
            List of connected server names
        """
        self._ensure_mcp_enabled()
        return self._mcp_manager.get_connected_servers()

    async def mcp_list_all_tools(self, use_cache: bool = True) -> Dict[str, List]:
        """List all tools from all connected MCP servers.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            Dict mapping server names to their tools
        """
        self._ensure_mcp_enabled()
        return await self._mcp_manager.list_all_tools(use_cache)

    async def mcp_list_all_resources(self, use_cache: bool = True) -> Dict[str, List]:
        """List all resources from all connected MCP servers.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            Dict mapping server names to their resources
        """
        self._ensure_mcp_enabled()
        return await self._mcp_manager.list_all_resources(use_cache)

    async def mcp_health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all MCP servers.
        
        Returns:
            Dict mapping server names to health status
        """
        self._ensure_mcp_enabled()
        return await self._mcp_manager.health_check_all()

    async def mcp_connect_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server.
        
        Args:
            server_name: Name of the server to connect
            
        Returns:
            True if connection successful
        """
        self._ensure_mcp_enabled()
        return await self._mcp_manager.connect_server(server_name)

    async def mcp_disconnect_server(self, server_name: str) -> bool:
        """Disconnect from a specific MCP server.
        
        Args:
            server_name: Name of the server to disconnect
            
        Returns:
            True if disconnection successful
        """
        self._ensure_mcp_enabled()
        return await self._mcp_manager.disconnect_server(server_name)

    def is_mcp_enabled(self) -> bool:
        """Check if MCP integration is enabled.
        
        Returns:
            True if MCP is enabled
        """
        return self._mcp_enabled

    def get_mcp_manager(self) -> Optional[MCPManager]:
        """Get the MCP manager instance.
        
        Returns:
            MCP manager instance or None if not enabled
        """
        return self._mcp_manager

    def _ensure_mcp_enabled(self) -> None:
        """Ensure MCP integration is enabled.
        
        Raises:
            MCPError: If MCP is not enabled
        """
        if not self._mcp_enabled or not self._mcp_manager:
            raise MCPError(
                "MCP integration not enabled. Call setup_mcp_manager() first."
            )

    async def _cleanup_mcp(self) -> None:
        """Cleanup MCP resources during client shutdown."""
        if self._mcp_manager:
            try:
                await self._mcp_manager.stop_health_monitoring()
                await self._mcp_manager.disconnect_all()
                logger.info("MCP integration cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during MCP cleanup: {e}")
            finally:
                self._mcp_manager = None
                self._mcp_enabled = False
