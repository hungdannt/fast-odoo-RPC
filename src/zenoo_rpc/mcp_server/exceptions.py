"""
MCP Server exceptions for Zenoo RPC.

This module defines custom exceptions for MCP server operations,
providing clear error handling and security boundaries.
"""

from typing import Optional, Any, Dict


class MCPServerError(Exception):
    """Base exception for all MCP server errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class MCPAuthenticationError(MCPServerError):
    """Raised when MCP client authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        auth_method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "AUTH_FAILED", details)
        self.auth_method = auth_method


class MCPAuthorizationError(MCPServerError):
    """Raised when MCP client lacks required permissions."""
    
    def __init__(
        self,
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "ACCESS_DENIED", details)
        self.required_permission = required_permission
        self.resource = resource


class MCPValidationError(MCPServerError):
    """Raised when MCP request validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class MCPToolError(MCPServerError):
    """Raised when MCP tool execution fails."""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "TOOL_ERROR", details)
        self.tool_name = tool_name
        self.arguments = arguments


class MCPResourceError(MCPServerError):
    """Raised when MCP resource access fails."""
    
    def __init__(
        self,
        message: str,
        resource_uri: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "RESOURCE_ERROR", details)
        self.resource_uri = resource_uri


class MCPPromptError(MCPServerError):
    """Raised when MCP prompt operation fails."""
    
    def __init__(
        self,
        message: str,
        prompt_name: Optional[str] = None,
        arguments: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "PROMPT_ERROR", details)
        self.prompt_name = prompt_name
        self.arguments = arguments


class MCPConfigurationError(MCPServerError):
    """Raised when MCP server configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key
        self.config_value = config_value


class MCPConnectionError(MCPServerError):
    """Raised when MCP server connection fails."""
    
    def __init__(
        self,
        message: str,
        connection_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "CONNECTION_ERROR", details)
        self.connection_type = connection_type
