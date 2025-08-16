"""
MCP transport layer abstraction for Zenoo RPC.

This module provides transport layer abstractions for different
MCP connection types (stdio, HTTP, SSE) with unified interface.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

try:
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    # Mock classes for when MCP is not available
    class StdioServerParameters:
        def __init__(self, command, args=None, env=None, cwd=None):
            self.command = command
            self.args = args or []
            self.env = env or {}
            self.cwd = cwd

    def stdio_client(params):
        class MockStdioClient:
            async def __aenter__(self):
                return "mock_read", "mock_write"

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockStdioClient()

    def streamablehttp_client(url, auth=None):
        class MockHttpClient:
            async def __aenter__(self):
                return "mock_read", "mock_write", "mock_extra"

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockHttpClient()

    MCP_AVAILABLE = False

from .exceptions import MCPConfigurationError, MCPConnectionError

logger = logging.getLogger(__name__)


class MCPTransportType(Enum):
    """Supported MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass
class MCPServerConfig:
    """Configuration for MCP server connection."""
    
    name: str
    transport_type: Union[MCPTransportType, str]
    
    # stdio transport options
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    
    # HTTP/SSE transport options
    url: Optional[str] = None
    auth: Optional[Any] = None
    headers: Optional[Dict[str, str]] = None
    
    # Common options
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Health check options
    health_check_interval: float = 60.0
    health_check_timeout: float = 5.0
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if isinstance(self.transport_type, str):
            try:
                self.transport_type = MCPTransportType(self.transport_type)
            except ValueError:
                raise MCPConfigurationError(
                    f"Invalid transport type: {self.transport_type}. "
                    f"Must be one of: {[t.value for t in MCPTransportType]}"
                )
        
        # Validate transport-specific requirements
        if self.transport_type == MCPTransportType.STDIO:
            if not self.command:
                raise MCPConfigurationError(
                    "stdio transport requires 'command' parameter"
                )
        elif self.transport_type in (MCPTransportType.HTTP, MCPTransportType.SSE):
            if not self.url:
                raise MCPConfigurationError(
                    f"{self.transport_type.value} transport requires 'url' parameter"
                )
    
    def to_stdio_params(self) -> StdioServerParameters:
        """Convert to MCP StdioServerParameters."""
        if self.transport_type != MCPTransportType.STDIO:
            raise MCPConfigurationError(
                f"Cannot convert {self.transport_type.value} config to stdio params"
            )
        
        return StdioServerParameters(
            command=self.command,
            args=self.args or [],
            env=self.env or {},
            cwd=self.cwd
        )


class MCPTransport:
    """Abstract transport layer for MCP connections."""
    
    def __init__(self, config: MCPServerConfig):
        """Initialize transport with configuration.
        
        Args:
            config: MCP server configuration
        """
        self.config = config
        self.name = config.name
        self.transport_type = config.transport_type
        self._connection_context = None
        self._read_stream = None
        self._write_stream = None
        self._connected = False
    
    async def connect(self) -> tuple[Any, Any]:
        """Establish connection and return read/write streams.
        
        Returns:
            Tuple of (read_stream, write_stream)
            
        Raises:
            MCPConnectionError: If connection fails
        """
        if self._connected:
            return self._read_stream, self._write_stream
        
        try:
            if self.transport_type == MCPTransportType.STDIO:
                await self._connect_stdio()
            elif self.transport_type == MCPTransportType.HTTP:
                await self._connect_http()
            elif self.transport_type == MCPTransportType.SSE:
                await self._connect_sse()
            else:
                raise MCPConnectionError(
                    f"Unsupported transport type: {self.transport_type}",
                    server_name=self.name,
                    transport_type=self.transport_type.value
                )
            
            self._connected = True
            logger.info(
                f"Connected to MCP server '{self.name}' via {self.transport_type.value}"
            )
            
            return self._read_stream, self._write_stream
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.name}': {e}")
            raise MCPConnectionError(
                f"Connection failed: {e}",
                server_name=self.name,
                transport_type=self.transport_type.value
            ) from e
    
    async def _connect_stdio(self) -> None:
        """Connect using stdio transport."""
        stdio_params = self.config.to_stdio_params()
        self._connection_context = stdio_client(stdio_params)
        
        # Enter the context manager
        streams = await self._connection_context.__aenter__()
        self._read_stream, self._write_stream = streams
    
    async def _connect_http(self) -> None:
        """Connect using HTTP transport."""
        self._connection_context = streamablehttp_client(
            self.config.url,
            auth=self.config.auth
        )
        
        # Enter the context manager
        streams = await self._connection_context.__aenter__()
        self._read_stream, self._write_stream, _ = streams
    
    async def _connect_sse(self) -> None:
        """Connect using SSE transport."""
        # SSE transport implementation would go here
        # For now, fall back to HTTP
        await self._connect_http()
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if not self._connected:
            return
        
        try:
            if self._connection_context:
                await self._connection_context.__aexit__(None, None, None)
                self._connection_context = None
            
            self._read_stream = None
            self._write_stream = None
            self._connected = False
            
            logger.info(f"Disconnected from MCP server '{self.name}'")
            
        except Exception as e:
            logger.error(f"Error during disconnect from '{self.name}': {e}")
    
    async def health_check(self) -> bool:
        """Check if transport connection is healthy.
        
        Returns:
            True if connection is healthy
        """
        try:
            if not self._connected:
                return False
            
            # Simple health check - try to establish connection if not connected
            # In a real implementation, this might send a ping or status request
            await asyncio.wait_for(
                self._perform_health_check(),
                timeout=self.config.health_check_timeout
            )
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed for '{self.name}': {e}")
            return False
    
    async def _perform_health_check(self) -> None:
        """Perform transport-specific health check."""
        # This is a placeholder - real implementation would depend on transport type
        # For stdio: check if process is still running
        # For HTTP: send a health check request
        # For SSE: check if connection is still open
        pass
    
    def is_connected(self) -> bool:
        """Check if transport is currently connected."""
        return self._connected
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging."""
        return {
            "name": self.name,
            "transport_type": self.transport_type.value,
            "connected": self._connected,
            "config": {
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "retry_delay": self.config.retry_delay,
            }
        }
    
    async def __aenter__(self) -> "MCPTransport":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


class MCPTransportManager:
    """Manager for multiple MCP transport connections."""
    
    def __init__(self):
        """Initialize transport manager."""
        self.transports: Dict[str, MCPTransport] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 60.0
    
    def add_transport(self, config: MCPServerConfig) -> MCPTransport:
        """Add a new transport configuration.
        
        Args:
            config: MCP server configuration
            
        Returns:
            Created transport instance
        """
        if config.name in self.transports:
            logger.warning(f"Transport '{config.name}' already exists, replacing")
        
        transport = MCPTransport(config)
        self.transports[config.name] = transport
        
        logger.info(f"Added MCP transport '{config.name}' ({config.transport_type.value})")
        return transport
    
    def get_transport(self, name: str) -> Optional[MCPTransport]:
        """Get transport by name.
        
        Args:
            name: Transport name
            
        Returns:
            Transport instance or None if not found
        """
        return self.transports.get(name)
    
    def remove_transport(self, name: str) -> bool:
        """Remove transport by name.
        
        Args:
            name: Transport name
            
        Returns:
            True if transport was removed
        """
        if name in self.transports:
            transport = self.transports.pop(name)
            # Disconnect if connected
            if transport.is_connected():
                asyncio.create_task(transport.disconnect())
            logger.info(f"Removed MCP transport '{name}'")
            return True
        return False
    
    def list_transports(self) -> List[str]:
        """List all transport names.
        
        Returns:
            List of transport names
        """
        return list(self.transports.keys())
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect all transports.
        
        Returns:
            Dict mapping transport names to connection success
        """
        results = {}
        for name, transport in self.transports.items():
            try:
                await transport.connect()
                results[name] = True
            except Exception as e:
                logger.error(f"Failed to connect transport '{name}': {e}")
                results[name] = False
        
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect all transports."""
        tasks = []
        for transport in self.transports.values():
            if transport.is_connected():
                tasks.append(transport.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start_health_monitoring(self, interval: float = 60.0) -> None:
        """Start health monitoring for all transports.
        
        Args:
            interval: Health check interval in seconds
        """
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._health_check_interval = interval
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Started health monitoring with {interval}s interval")
    
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
        """Health check loop for all transports."""
        while True:
            try:
                for name, transport in self.transports.items():
                    if transport.is_connected():
                        healthy = await transport.health_check()
                        if not healthy:
                            logger.warning(f"Transport '{name}' failed health check")
                            # Could implement auto-reconnection here
                
                await asyncio.sleep(self._health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self._health_check_interval)
    
    async def __aenter__(self) -> "MCPTransportManager":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_health_monitoring()
        await self.disconnect_all()
