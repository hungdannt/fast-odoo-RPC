"""
MCP Server configuration for Zenoo RPC.

This module provides configuration management for the MCP server,
including security settings, performance tuning, and feature flags.
"""

import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class MCPTransportType(Enum):
    """Supported MCP server transport types."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class MCPAuthMethod(Enum):
    """Supported authentication methods."""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"


@dataclass
class MCPSecurityConfig:
    """Security configuration for MCP server."""
    
    # Authentication
    auth_method: MCPAuthMethod = MCPAuthMethod.API_KEY
    api_keys: List[str] = field(default_factory=list)
    oauth2_config: Optional[Dict[str, Any]] = None
    
    # Authorization
    enable_permissions: bool = True
    default_permissions: List[str] = field(default_factory=lambda: ["read"])
    permission_mapping: Dict[str, List[str]] = field(default_factory=dict)
    
    # Security features
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    enable_input_validation: bool = True
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    
    # CORS settings (for HTTP transport)
    enable_cors: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST"])


@dataclass
class MCPPerformanceConfig:
    """Performance configuration for MCP server."""
    
    # Caching
    enable_caching: bool = True
    cache_ttl: int = 300  # seconds
    cache_max_size: int = 1000
    
    # Connection pooling
    max_connections: int = 100
    connection_timeout: int = 30
    
    # Request handling
    max_concurrent_requests: int = 50
    request_timeout: int = 60
    
    # Resource limits
    max_records_per_request: int = 1000
    max_search_results: int = 500


@dataclass
class MCPFeatureConfig:
    """Feature flags for MCP server."""
    
    # Core features
    enable_tools: bool = True
    enable_resources: bool = True
    enable_prompts: bool = True
    
    # Advanced features
    enable_batch_operations: bool = True
    enable_transactions: bool = True
    enable_webhooks: bool = False
    
    # Odoo-specific features
    enable_model_introspection: bool = True
    enable_workflow_operations: bool = True
    enable_report_generation: bool = True
    
    # AI features
    enable_ai_suggestions: bool = False
    enable_natural_language_queries: bool = False


@dataclass
class MCPServerConfig:
    """Complete MCP server configuration."""
    
    # Basic settings
    name: str = "zenoo-mcp-server"
    version: str = "1.0.0"
    description: str = "Zenoo RPC MCP Server for Odoo Integration"
    
    # Transport settings
    transport_type: MCPTransportType = MCPTransportType.STDIO
    host: str = "localhost"
    port: int = 8000
    
    # Odoo connection
    odoo_url: str = "http://localhost:8069"
    odoo_database: str = "demo"
    odoo_username: str = "admin"
    odoo_password: str = "admin"
    
    # Component configurations
    security: MCPSecurityConfig = field(default_factory=MCPSecurityConfig)
    performance: MCPPerformanceConfig = field(default_factory=MCPPerformanceConfig)
    features: MCPFeatureConfig = field(default_factory=MCPFeatureConfig)
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Custom settings
    custom_tools: List[str] = field(default_factory=list)
    custom_resources: List[str] = field(default_factory=list)
    custom_prompts: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> "MCPServerConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        # Basic settings
        config.name = os.getenv("MCP_SERVER_NAME", config.name)
        config.transport_type = MCPTransportType(
            os.getenv("MCP_TRANSPORT_TYPE", config.transport_type.value)
        )
        config.host = os.getenv("MCP_HOST", config.host)
        config.port = int(os.getenv("MCP_PORT", str(config.port)))
        
        # Odoo connection
        config.odoo_url = os.getenv("ODOO_URL", config.odoo_url)
        config.odoo_database = os.getenv("ODOO_DATABASE", config.odoo_database)
        config.odoo_username = os.getenv("ODOO_USERNAME", config.odoo_username)
        config.odoo_password = os.getenv("ODOO_PASSWORD", config.odoo_password)
        
        # Security
        api_keys_env = os.getenv("MCP_API_KEYS")
        if api_keys_env:
            config.security.api_keys = api_keys_env.split(",")
        
        config.security.auth_method = MCPAuthMethod(
            os.getenv("MCP_AUTH_METHOD", config.security.auth_method.value)
        )
        
        # Performance
        config.performance.enable_caching = os.getenv("MCP_ENABLE_CACHING", "true").lower() == "true"
        config.performance.cache_ttl = int(os.getenv("MCP_CACHE_TTL", str(config.performance.cache_ttl)))
        config.performance.max_connections = int(os.getenv("MCP_MAX_CONNECTIONS", str(config.performance.max_connections)))
        
        # Features
        config.features.enable_tools = os.getenv("MCP_ENABLE_TOOLS", "true").lower() == "true"
        config.features.enable_resources = os.getenv("MCP_ENABLE_RESOURCES", "true").lower() == "true"
        config.features.enable_prompts = os.getenv("MCP_ENABLE_PROMPTS", "true").lower() == "true"
        
        # Logging
        config.log_level = os.getenv("MCP_LOG_LEVEL", config.log_level)
        
        return config
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerConfig":
        """Create configuration from dictionary."""
        config = cls()
        
        # Basic settings
        config.name = data.get("name", config.name)
        config.version = data.get("version", config.version)
        config.description = data.get("description", config.description)
        
        # Transport
        transport_type = data.get("transport_type", config.transport_type.value)
        config.transport_type = MCPTransportType(transport_type)
        config.host = data.get("host", config.host)
        config.port = data.get("port", config.port)
        
        # Odoo connection
        config.odoo_url = data.get("odoo_url", config.odoo_url)
        config.odoo_database = data.get("odoo_database", config.odoo_database)
        config.odoo_username = data.get("odoo_username", config.odoo_username)
        config.odoo_password = data.get("odoo_password", config.odoo_password)
        
        # Security
        if "security" in data:
            security_data = data["security"]
            config.security.auth_method = MCPAuthMethod(
                security_data.get("auth_method", config.security.auth_method.value)
            )
            config.security.api_keys = security_data.get("api_keys", config.security.api_keys)
            config.security.enable_permissions = security_data.get("enable_permissions", config.security.enable_permissions)
            config.security.enable_rate_limiting = security_data.get("enable_rate_limiting", config.security.enable_rate_limiting)
        
        # Performance
        if "performance" in data:
            perf_data = data["performance"]
            config.performance.enable_caching = perf_data.get("enable_caching", config.performance.enable_caching)
            config.performance.cache_ttl = perf_data.get("cache_ttl", config.performance.cache_ttl)
            config.performance.max_connections = perf_data.get("max_connections", config.performance.max_connections)
        
        # Features
        if "features" in data:
            feature_data = data["features"]
            config.features.enable_tools = feature_data.get("enable_tools", config.features.enable_tools)
            config.features.enable_resources = feature_data.get("enable_resources", config.features.enable_resources)
            config.features.enable_prompts = feature_data.get("enable_prompts", config.features.enable_prompts)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "transport_type": self.transport_type.value,
            "host": self.host,
            "port": self.port,
            "odoo_url": self.odoo_url,
            "odoo_database": self.odoo_database,
            "odoo_username": self.odoo_username,
            "odoo_password": "***",  # Hide password
            "security": {
                "auth_method": self.security.auth_method.value,
                "enable_permissions": self.security.enable_permissions,
                "enable_rate_limiting": self.security.enable_rate_limiting,
                "enable_input_validation": self.security.enable_input_validation,
            },
            "performance": {
                "enable_caching": self.performance.enable_caching,
                "cache_ttl": self.performance.cache_ttl,
                "max_connections": self.performance.max_connections,
                "max_concurrent_requests": self.performance.max_concurrent_requests,
            },
            "features": {
                "enable_tools": self.features.enable_tools,
                "enable_resources": self.features.enable_resources,
                "enable_prompts": self.features.enable_prompts,
                "enable_batch_operations": self.features.enable_batch_operations,
                "enable_transactions": self.features.enable_transactions,
            },
            "log_level": self.log_level,
        }
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.name:
            raise ValueError("Server name is required")
        
        if not self.odoo_url:
            raise ValueError("Odoo URL is required")
        
        if not self.odoo_database:
            raise ValueError("Odoo database is required")
        
        if not self.odoo_username:
            raise ValueError("Odoo username is required")
        
        if not self.odoo_password:
            raise ValueError("Odoo password is required")
        
        if self.security.auth_method == MCPAuthMethod.API_KEY and not self.security.api_keys:
            raise ValueError("API keys are required when using API key authentication")
        
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        if self.performance.cache_ttl < 0:
            raise ValueError("Cache TTL must be non-negative")
        
        if self.performance.max_connections < 1:
            raise ValueError("Max connections must be at least 1")
