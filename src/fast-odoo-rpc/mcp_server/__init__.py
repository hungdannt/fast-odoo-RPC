"""
MCP Server implementation for Zenoo RPC.

This module provides MCP (Model Context Protocol) server functionality,
allowing AI tools to connect to and interact with Odoo through Zenoo RPC.

The server exposes Odoo operations as MCP tools, data as resources,
and query templates as prompts.
"""

from .server import ZenooMCPServer
from .security import MCPSecurityManager
from .config import MCPServerConfig
from .exceptions import (
    MCPServerError,
    MCPAuthenticationError,
    MCPAuthorizationError,
    MCPValidationError
)

__all__ = [
    # Core server
    "ZenooMCPServer",

    # Components
    "MCPSecurityManager",

    # Configuration
    "MCPServerConfig",

    # Exceptions
    "MCPServerError",
    "MCPAuthenticationError",
    "MCPAuthorizationError",
    "MCPValidationError",
]
