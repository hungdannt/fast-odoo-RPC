"""
Test MCP integration functionality.

This module tests the MCP client, manager, and integration components
to ensure they work correctly with the Zenoo RPC framework.
"""

import asyncio
import pytest
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from zenoo_rpc.mcp import (
    MCPClient,
    MCPManager,
    MCPServerConfig,
    MCPTransportType,
    MCPError,
    MCPConnectionError
)
from zenoo_rpc.mcp.integration import MCPIntegration


class TestMCPIntegration:
    """Test MCP integration functionality."""
    
    def test_mcp_server_config_creation(self):
        """Test MCP server configuration creation."""
        # Test stdio configuration
        stdio_config = MCPServerConfig(
            name="test_stdio",
            transport_type=MCPTransportType.STDIO,
            command="echo",
            args=["hello"]
        )
        
        assert stdio_config.name == "test_stdio"
        assert stdio_config.transport_type == MCPTransportType.STDIO
        assert stdio_config.command == "echo"
        assert stdio_config.args == ["hello"]
        
        # Test HTTP configuration
        http_config = MCPServerConfig(
            name="test_http",
            transport_type=MCPTransportType.HTTP,
            url="http://localhost:8000/mcp"
        )
        
        assert http_config.name == "test_http"
        assert http_config.transport_type == MCPTransportType.HTTP
        assert http_config.url == "http://localhost:8000/mcp"
    
    def test_mcp_server_config_validation(self):
        """Test MCP server configuration validation."""
        # Test invalid transport type
        with pytest.raises(Exception):  # MCPConfigurationError
            MCPServerConfig(
                name="invalid",
                transport_type="invalid_transport"
            )
        
        # Test missing command for stdio
        with pytest.raises(Exception):  # MCPConfigurationError
            MCPServerConfig(
                name="stdio_no_command",
                transport_type=MCPTransportType.STDIO
            )
        
        # Test missing URL for HTTP
        with pytest.raises(Exception):  # MCPConfigurationError
            MCPServerConfig(
                name="http_no_url",
                transport_type=MCPTransportType.HTTP
            )
    
    @pytest.mark.asyncio
    async def test_mcp_manager_basic_operations(self):
        """Test basic MCP manager operations."""
        manager = MCPManager()
        
        # Test empty manager
        assert manager.list_servers() == []
        assert manager.get_connected_servers() == []
        
        # Test adding server configuration
        config = MCPServerConfig(
            name="test_server",
            transport_type=MCPTransportType.STDIO,
            command="echo",
            args=["test"]
        )
        
        await manager.add_server(config)
        
        # Verify server was added
        assert "test_server" in manager.list_servers()
        
        # Test removing server
        removed = await manager.remove_server("test_server")
        assert removed is True
        assert manager.list_servers() == []
        
        # Test removing non-existent server
        removed = await manager.remove_server("non_existent")
        assert removed is False
    
    @pytest.mark.asyncio
    async def test_mcp_integration_mixin(self):
        """Test MCP integration mixin functionality."""
        
        class TestClient(MCPIntegration):
            """Test client with MCP integration."""
            
            def __init__(self):
                super().__init__()
        
        client = TestClient()
        
        # Test initial state
        assert not client.is_mcp_enabled()
        assert client.get_mcp_manager() is None
        
        # Test MCP operations without setup should fail
        with pytest.raises(MCPError):
            await client.mcp_list_servers()
        
        # Test setup with empty server list
        await client.setup_mcp_manager([], auto_connect=False, health_monitoring=False)
        
        # Verify MCP is now enabled
        assert client.is_mcp_enabled()
        assert client.get_mcp_manager() is not None
        
        # Test basic operations
        servers = await client.mcp_list_servers()
        assert servers == []
        
        connected_servers = await client.mcp_get_connected_servers()
        assert connected_servers == []
        
        # Test health check
        health_status = await client.mcp_health_check_all()
        assert health_status == {}
        
        # Cleanup
        await client._cleanup_mcp()
        assert not client.is_mcp_enabled()
    
    def test_mcp_error_hierarchy(self):
        """Test MCP error hierarchy."""
        # Test base MCP error
        base_error = MCPError("Base error", server_name="test_server")
        assert str(base_error) == "[test_server] Base error"
        assert base_error.server_name == "test_server"
        
        # Test connection error
        conn_error = MCPConnectionError(
            "Connection failed",
            server_name="test_server",
            transport_type="stdio"
        )
        assert "test_server" in str(conn_error)
        assert conn_error.transport_type == "stdio"
    
    @pytest.mark.asyncio
    async def test_mcp_manager_context_manager(self):
        """Test MCP manager as context manager."""
        async with MCPManager() as manager:
            # Test basic operations within context
            assert manager.list_servers() == []
            
            # Add a test server
            config = MCPServerConfig(
                name="context_test",
                transport_type=MCPTransportType.STDIO,
                command="echo",
                args=["context"]
            )
            
            await manager.add_server(config)
            assert "context_test" in manager.list_servers()
        
        # After context exit, manager should be cleaned up
        # (In real implementation, this would disconnect all servers)
    
    def test_mcp_transport_type_enum(self):
        """Test MCP transport type enumeration."""
        assert MCPTransportType.STDIO.value == "stdio"
        assert MCPTransportType.HTTP.value == "http"
        assert MCPTransportType.SSE.value == "sse"
        
        # Test enum conversion
        assert MCPTransportType("stdio") == MCPTransportType.STDIO
        assert MCPTransportType("http") == MCPTransportType.HTTP
        assert MCPTransportType("sse") == MCPTransportType.SSE


def test_mcp_imports():
    """Test that all MCP components can be imported correctly."""
    try:
        from zenoo_rpc.mcp import (
            MCPClient,
            MCPManager,
            MCPServerConfig,
            MCPTransportType,
            MCPError,
            MCPConnectionError,
            MCPTimeoutError
        )
        
        # Test that classes exist and are callable
        assert callable(MCPClient)
        assert callable(MCPManager)
        assert callable(MCPServerConfig)
        
        # Test that enums work
        assert hasattr(MCPTransportType, 'STDIO')
        assert hasattr(MCPTransportType, 'HTTP')
        assert hasattr(MCPTransportType, 'SSE')
        
        # Test that exceptions are proper exception classes
        assert issubclass(MCPError, Exception)
        assert issubclass(MCPConnectionError, MCPError)
        assert issubclass(MCPTimeoutError, MCPError)
        
        print("✅ All MCP imports successful")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        raise


async def test_mcp_integration_demo():
    """Demo test showing MCP integration usage."""
    print("\n🎯 MCP Integration Demo")
    print("=" * 50)
    
    try:
        # Create integration instance
        class DemoClient(MCPIntegration):
            def __init__(self):
                super().__init__()
        
        client = DemoClient()
        
        print("✅ 1. Created MCP integration client")
        
        # Setup MCP manager (with empty config for demo)
        await client.setup_mcp_manager(
            servers=[],
            auto_connect=False,
            health_monitoring=False
        )
        
        print("✅ 2. Setup MCP manager successfully")
        
        # Test basic operations
        servers = await client.mcp_list_servers()
        print(f"✅ 3. Listed servers: {servers}")
        
        connected = await client.mcp_get_connected_servers()
        print(f"✅ 4. Connected servers: {connected}")
        
        health = await client.mcp_health_check_all()
        print(f"✅ 5. Health check results: {health}")
        
        # Cleanup
        await client._cleanup_mcp()
        print("✅ 6. Cleaned up MCP integration")
        
        print("\n🎉 MCP Integration Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    print("🔍 Testing MCP Integration")
    print("=" * 50)
    
    # Test imports
    test_mcp_imports()
    
    # Run async demo
    asyncio.run(test_mcp_integration_demo())
    
    print("\n✅ All MCP integration tests completed!")
