#!/usr/bin/env python3
"""
CLI tool for running Zenoo RPC MCP Server.

This script provides a command-line interface for starting and managing
the MCP server that exposes Odoo operations to AI tools.

Usage:
    python -m zenoo_rpc.mcp_server.cli [options]
    
    # Start with default settings
    python -m zenoo_rpc.mcp_server.cli
    
    # Start with custom config
    python -m zenoo_rpc.mcp_server.cli --config config.json
    
    # Start with environment variables
    MCP_SERVER_NAME="my-odoo-server" python -m zenoo_rpc.mcp_server.cli
    
    # Start with specific transport
    python -m zenoo_rpc.mcp_server.cli --transport http --port 8080
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .server import ZenooMCPServer
from .config import MCPServerConfig, MCPTransportType
from .exceptions import MCPServerError, MCPConfigurationError


def setup_logging(log_level: str = "INFO", log_format: str = None) -> None:
    """Setup logging configuration."""
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stderr),  # Important: use stderr for stdio transport
        ]
    )


def load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise MCPConfigurationError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise MCPConfigurationError(f"Invalid JSON in configuration file: {e}")


def create_config(args: argparse.Namespace) -> MCPServerConfig:
    """Create server configuration from CLI arguments."""
    # Start with environment-based config
    config = MCPServerConfig.from_env()
    
    # Load from config file if specified
    if args.config:
        config_data = load_config_file(args.config)
        config = MCPServerConfig.from_dict(config_data)
    
    # Override with CLI arguments
    if args.name:
        config.name = args.name
    
    if args.transport:
        config.transport_type = MCPTransportType(args.transport)
    
    if args.host:
        config.host = args.host
    
    if args.port:
        config.port = args.port
    
    if args.odoo_url:
        config.odoo_url = args.odoo_url
    
    if args.odoo_database:
        config.odoo_database = args.odoo_database
    
    if args.odoo_username:
        config.odoo_username = args.odoo_username
    
    if args.odoo_password:
        config.odoo_password = args.odoo_password
    
    if args.api_keys:
        config.security.api_keys = args.api_keys.split(',')
    
    if args.log_level:
        config.log_level = args.log_level
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        raise MCPConfigurationError(f"Configuration validation failed: {e}")
    
    return config


def print_server_info(config: MCPServerConfig) -> None:
    """Print server information."""
    print("🚀 Zenoo RPC MCP Server", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"Name: {config.name}", file=sys.stderr)
    print(f"Version: {config.version}", file=sys.stderr)
    print(f"Transport: {config.transport_type.value}", file=sys.stderr)
    
    if config.transport_type != MCPTransportType.STDIO:
        print(f"Host: {config.host}", file=sys.stderr)
        print(f"Port: {config.port}", file=sys.stderr)
    
    print(f"Odoo URL: {config.odoo_url}", file=sys.stderr)
    print(f"Odoo Database: {config.odoo_database}", file=sys.stderr)
    print(f"Auth Method: {config.security.auth_method.value}", file=sys.stderr)
    print(f"Log Level: {config.log_level}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)


async def run_server(config: MCPServerConfig) -> None:
    """Run the MCP server."""
    server = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received signal {signum}, shutting down...", file=sys.stderr)
        if server:
            asyncio.create_task(server.stop())
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and start server
        server = ZenooMCPServer(config)
        print("✅ Server initialized successfully", file=sys.stderr)
        
        print("🔌 Starting server...", file=sys.stderr)
        await server.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user", file=sys.stderr)
    except Exception as e:
        print(f"❌ Server error: {e}", file=sys.stderr)
        raise
    finally:
        if server:
            await server.stop()
        print("👋 Server stopped", file=sys.stderr)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Zenoo RPC MCP Server - Expose Odoo operations to AI tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings (stdio transport)
  python -m zenoo_rpc.mcp_server.cli
  
  # Start HTTP server on custom port
  python -m zenoo_rpc.mcp_server.cli --transport http --port 8080
  
  # Use custom Odoo connection
  python -m zenoo_rpc.mcp_server.cli --odoo-url http://odoo.example.com:8069
  
  # Load configuration from file
  python -m zenoo_rpc.mcp_server.cli --config server-config.json
  
  # Use environment variables
  export ODOO_URL=http://localhost:8069
  export ODOO_DATABASE=production
  export MCP_API_KEYS=key1,key2,key3
  python -m zenoo_rpc.mcp_server.cli

Environment Variables:
  MCP_SERVER_NAME       Server name
  MCP_TRANSPORT_TYPE    Transport type (stdio, http, sse)
  MCP_HOST             Host for HTTP transport
  MCP_PORT             Port for HTTP transport
  ODOO_URL             Odoo server URL
  ODOO_DATABASE        Odoo database name
  ODOO_USERNAME        Odoo username
  ODOO_PASSWORD        Odoo password
  MCP_API_KEYS         Comma-separated API keys
  MCP_LOG_LEVEL        Log level (DEBUG, INFO, WARNING, ERROR)
        """
    )
    
    # Server configuration
    parser.add_argument(
        "--name",
        help="Server name (default: zenoo-mcp-server)"
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Configuration file path (JSON format)"
    )
    
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "http", "sse"],
        help="Transport type (default: stdio)"
    )
    
    parser.add_argument(
        "--host",
        help="Host for HTTP transport (default: localhost)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        help="Port for HTTP transport (default: 8000)"
    )
    
    # Odoo connection
    parser.add_argument(
        "--odoo-url",
        help="Odoo server URL (default: http://localhost:8069)"
    )
    
    parser.add_argument(
        "--odoo-database",
        help="Odoo database name (default: demo)"
    )
    
    parser.add_argument(
        "--odoo-username",
        help="Odoo username (default: admin)"
    )
    
    parser.add_argument(
        "--odoo-password",
        help="Odoo password (default: admin)"
    )
    
    # Security
    parser.add_argument(
        "--api-keys",
        help="Comma-separated API keys for authentication"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Zenoo RPC MCP Server 1.0.0"
    )
    
    # Development options
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode (verbose logging, debug features)"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    args = parser.parse_args()
    
    try:
        # Create configuration
        config = create_config(args)
        
        # Setup logging
        log_level = config.log_level
        if args.dev:
            log_level = "DEBUG"
        
        setup_logging(log_level, config.log_format)
        
        # Validate config and exit if requested
        if args.validate_config:
            print("✅ Configuration is valid", file=sys.stderr)
            print(json.dumps(config.to_dict(), indent=2), file=sys.stderr)
            return
        
        # Print server info
        print_server_info(config)
        
        # Run server
        asyncio.run(run_server(config))
        
    except MCPConfigurationError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except MCPServerError as e:
        print(f"❌ Server error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.dev:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
