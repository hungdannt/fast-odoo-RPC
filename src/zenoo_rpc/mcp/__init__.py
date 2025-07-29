"""
MCP (Model Context Protocol) client integration for Zenoo RPC.

This module provides MCP client capabilities to connect to MCP servers
and expose their tools, resources, and prompts through the Zenoo RPC interface.
"""

from .client import MCPClient
from .manager import MCPManager
from .transport import MCPTransport, MCPServerConfig, MCPTransportType, MCPTransportManager
from .exceptions import (
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
    MCPResourceError,
    MCPPromptError,
    MCPServerNotFoundError,
    MCPConfigurationError,
    MCPAuthenticationError,
    MCPCapabilityError
)

__all__ = [
    # Core classes
    "MCPClient",
    "MCPManager",

    # Transport layer
    "MCPTransport",
    "MCPServerConfig",
    "MCPTransportType",
    "MCPTransportManager",

    # Exceptions
    "MCPError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPToolError",
    "MCPResourceError",
    "MCPPromptError",
    "MCPServerNotFoundError",
    "MCPConfigurationError",
    "MCPAuthenticationError",
    "MCPCapabilityError",
]
