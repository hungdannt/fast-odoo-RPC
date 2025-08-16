"""
MCP Server security manager for Zenoo RPC.

This module provides comprehensive security features including
authentication, authorization, input validation, and rate limiting.
"""

import hashlib
import hmac
import time
import logging
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, deque
from dataclasses import dataclass

from .config import MCPServerConfig, MCPAuthMethod
from .exceptions import (
    MCPAuthenticationError,
    MCPAuthorizationError,
    MCPValidationError
)

logger = logging.getLogger(__name__)


@dataclass
class MCPSession:
    """Represents an authenticated MCP session."""
    
    session_id: str
    client_id: str
    authenticated: bool = False
    permissions: Set[str] = None
    created_at: float = None
    last_activity: float = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_activity is None:
            self.last_activity = time.time()
        if self.metadata is None:
            self.metadata = {}
    
    def is_expired(self, timeout: int = 3600) -> bool:
        """Check if session is expired."""
        return time.time() - self.last_activity > timeout
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def has_permission(self, permission: str) -> bool:
        """Check if session has specific permission."""
        return permission in self.permissions or "admin" in self.permissions


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        now = time.time()
        client_requests = self.clients[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) < self.max_requests:
            client_requests.append(now)
            return True
        
        return False
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        client_requests = self.clients[client_id]
        
        # Remove old requests
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        return max(0, self.max_requests - len(client_requests))


class InputValidator:
    """Input validation for MCP requests."""
    
    def __init__(self, max_request_size: int = 10 * 1024 * 1024):
        self.max_request_size = max_request_size
    
    def validate_request_size(self, data: Any) -> None:
        """Validate request size."""
        if isinstance(data, (str, bytes)):
            size = len(data)
        else:
            # Estimate size for other types
            size = len(str(data))
        
        if size > self.max_request_size:
            raise MCPValidationError(
                f"Request size {size} exceeds maximum {self.max_request_size}",
                field="request_size",
                value=size
            )
    
    def validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments."""
        if not isinstance(arguments, dict):
            raise MCPValidationError(
                "Tool arguments must be a dictionary",
                field="arguments",
                value=type(arguments).__name__
            )
        
        # Check for dangerous patterns
        dangerous_keys = ["__", "eval", "exec", "import", "open", "file"]
        for key in arguments:
            if any(dangerous in str(key).lower() for dangerous in dangerous_keys):
                raise MCPValidationError(
                    f"Potentially dangerous argument key: {key}",
                    field="arguments",
                    value=key
                )
        
        # Validate specific tool arguments
        self._validate_specific_tool(tool_name, arguments)
    
    def _validate_specific_tool(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate arguments for specific tools."""
        if tool_name == "search_records":
            if "model" not in arguments:
                raise MCPValidationError("Model is required for search_records")
            
            if "limit" in arguments:
                limit = arguments["limit"]
                if not isinstance(limit, int) or limit < 1 or limit > 1000:
                    raise MCPValidationError(
                        "Limit must be an integer between 1 and 1000",
                        field="limit",
                        value=limit
                    )
        
        elif tool_name == "create_record":
            if "model" not in arguments or "values" not in arguments:
                raise MCPValidationError("Model and values are required for create_record")
        
        elif tool_name == "update_record":
            if "model" not in arguments or "record_id" not in arguments or "values" not in arguments:
                raise MCPValidationError("Model, record_id, and values are required for update_record")
    
    def sanitize_domain(self, domain: List) -> List:
        """Sanitize search domain to prevent injection."""
        if not isinstance(domain, list):
            raise MCPValidationError("Domain must be a list")
        
        sanitized = []
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                field, operator, value = item
                
                # Validate field name
                if not isinstance(field, str) or not field.replace("_", "").replace(".", "").isalnum():
                    raise MCPValidationError(f"Invalid field name: {field}")
                
                # Validate operator
                allowed_operators = [
                    "=", "!=", "<", "<=", ">", ">=", "like", "ilike", 
                    "in", "not in", "child_of", "parent_of"
                ]
                if operator not in allowed_operators:
                    raise MCPValidationError(f"Invalid operator: {operator}")
                
                sanitized.append([field, operator, value])
            elif item in ["&", "|", "!"]:
                sanitized.append(item)
            else:
                raise MCPValidationError(f"Invalid domain item: {item}")
        
        return sanitized


class MCPSecurityManager:
    """Comprehensive security manager for MCP server."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.sessions: Dict[str, MCPSession] = {}
        
        # Initialize components
        if config.security.enable_rate_limiting:
            self.rate_limiter = RateLimiter(
                config.security.rate_limit_requests,
                config.security.rate_limit_window
            )
        else:
            self.rate_limiter = None
        
        if config.security.enable_input_validation:
            self.input_validator = InputValidator(config.security.max_request_size)
        else:
            self.input_validator = None
        
        # Permission definitions
        self.default_permissions = set(config.security.default_permissions)
        self.permission_mapping = config.security.permission_mapping
        
        logger.info(f"Security manager initialized with auth method: {config.security.auth_method.value}")
    
    def authenticate(self, credentials: Dict[str, Any]) -> MCPSession:
        """Authenticate client and create session."""
        auth_method = self.config.security.auth_method
        
        if auth_method == MCPAuthMethod.NONE:
            return self._create_session("anonymous", permissions=self.default_permissions)
        
        elif auth_method == MCPAuthMethod.API_KEY:
            return self._authenticate_api_key(credentials)
        
        elif auth_method == MCPAuthMethod.BASIC:
            return self._authenticate_basic(credentials)
        
        elif auth_method == MCPAuthMethod.OAUTH2:
            return self._authenticate_oauth2(credentials)
        
        else:
            raise MCPAuthenticationError(f"Unsupported auth method: {auth_method}")
    
    def _authenticate_api_key(self, credentials: Dict[str, Any]) -> MCPSession:
        """Authenticate using API key."""
        api_key = credentials.get("api_key")
        if not api_key:
            raise MCPAuthenticationError("API key is required")
        
        if api_key not in self.config.security.api_keys:
            raise MCPAuthenticationError("Invalid API key")
        
        # Get permissions for this API key
        permissions = self.permission_mapping.get(api_key, list(self.default_permissions))

        return self._create_session(f"api_key_{api_key[:8]}", permissions=set(permissions))
    
    def _authenticate_basic(self, credentials: Dict[str, Any]) -> MCPSession:
        """Authenticate using basic auth."""
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise MCPAuthenticationError("Username and password are required")
        
        # In a real implementation, verify against user database
        # For now, use simple validation
        if username == "admin" and password == "admin":
            return self._create_session(username, permissions={"admin"})
        
        raise MCPAuthenticationError("Invalid username or password")
    
    def _authenticate_oauth2(self, credentials: Dict[str, Any]) -> MCPSession:
        """Authenticate using OAuth2."""
        token = credentials.get("access_token")
        if not token:
            raise MCPAuthenticationError("Access token is required")
        
        # In a real implementation, validate token with OAuth2 provider
        # For now, simple validation
        if token.startswith("valid_"):
            return self._create_session("oauth2_user", permissions=self.default_permissions)
        
        raise MCPAuthenticationError("Invalid access token")
    
    def _create_session(self, client_id: str, permissions: Set[str]) -> MCPSession:
        """Create new authenticated session."""
        session_id = hashlib.sha256(f"{client_id}_{time.time()}".encode()).hexdigest()
        
        session = MCPSession(
            session_id=session_id,
            client_id=client_id,
            authenticated=True,
            permissions=permissions
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created session {session_id} for client {client_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """Get session by ID."""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            del self.sessions[session_id]
            return None
        return session
    
    def check_permission(self, session: MCPSession, permission: str, resource: str = None) -> None:
        """Check if session has required permission."""
        if not self.config.security.enable_permissions:
            return
        
        if not session.has_permission(permission):
            raise MCPAuthorizationError(
                f"Permission '{permission}' required",
                required_permission=permission,
                resource=resource
            )
    
    def check_rate_limit(self, client_id: str) -> None:
        """Check rate limit for client."""
        if not self.rate_limiter:
            return
        
        if not self.rate_limiter.is_allowed(client_id):
            remaining = self.rate_limiter.get_remaining(client_id)
            raise MCPAuthorizationError(
                f"Rate limit exceeded. {remaining} requests remaining",
                details={"remaining_requests": remaining}
            )
    
    def validate_request(self, data: Any) -> None:
        """Validate incoming request."""
        if not self.input_validator:
            return
        
        self.input_validator.validate_request_size(data)
    
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate tool call arguments."""
        if not self.input_validator:
            return
        
        self.input_validator.validate_tool_arguments(tool_name, arguments)
    
    def sanitize_domain(self, domain: List) -> List:
        """Sanitize search domain."""
        if not self.input_validator:
            return domain
        
        return self.input_validator.sanitize_domain(domain)
    
    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session {session_id}")
    
    def get_security_info(self) -> Dict[str, Any]:
        """Get security information for monitoring."""
        return {
            "auth_method": self.config.security.auth_method.value,
            "active_sessions": len(self.sessions),
            "rate_limiting_enabled": self.rate_limiter is not None,
            "input_validation_enabled": self.input_validator is not None,
            "permissions_enabled": self.config.security.enable_permissions,
        }
