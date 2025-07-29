"""
MCP-specific exceptions for Zenoo RPC.

This module defines custom exceptions for MCP client operations,
providing clear error handling and debugging information.
"""

from typing import Optional, Any, Dict
from ..exceptions.base import ZenooError


class MCPError(ZenooError):
    """Base exception for all MCP-related errors."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.server_name = server_name
        self.details = details or {}
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.server_name:
            base_msg = f"[{self.server_name}] {base_msg}"
        return base_msg


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        transport_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.transport_type = transport_type


class MCPTimeoutError(MCPError):
    """Raised when MCP operation times out."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.timeout_duration = timeout_duration
        self.operation = operation


class MCPProtocolError(MCPError):
    """Raised when MCP protocol error occurs."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.error_code = error_code


class MCPToolError(MCPError):
    """Raised when MCP tool execution fails."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.tool_name = tool_name
        self.arguments = arguments


class MCPResourceError(MCPError):
    """Raised when MCP resource access fails."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        resource_uri: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.resource_uri = resource_uri


class MCPPromptError(MCPError):
    """Raised when MCP prompt operation fails."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        prompt_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.prompt_name = prompt_name
        self.arguments = arguments


class MCPServerNotFoundError(MCPError):
    """Raised when specified MCP server is not found."""
    
    def __init__(
        self,
        server_name: str,
        available_servers: Optional[list] = None
    ):
        message = f"MCP server '{server_name}' not found"
        if available_servers:
            message += f". Available servers: {', '.join(available_servers)}"
        super().__init__(message, server_name)
        self.available_servers = available_servers or []


class MCPConfigurationError(MCPError):
    """Raised when MCP configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details=details)
        self.config_key = config_key
        self.config_value = config_value


class MCPAuthenticationError(MCPError):
    """Raised when MCP server authentication fails."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        auth_method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.auth_method = auth_method


class MCPCapabilityError(MCPError):
    """Raised when MCP server doesn't support required capability."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        capability: Optional[str] = None,
        available_capabilities: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, server_name, details)
        self.capability = capability
        self.available_capabilities = available_capabilities or []
