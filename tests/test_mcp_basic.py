"""
Basic test for MCP integration without external dependencies.

This test verifies the MCP module structure and basic functionality
without requiring the actual MCP Python SDK.
"""

import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_mcp_module_structure():
    """Test that MCP module structure is correct."""
    print("🔍 Testing MCP Module Structure")
    print("=" * 40)
    
    try:
        # Test that the mcp package exists
        import zenoo_rpc.mcp
        print("✅ zenoo_rpc.mcp package imported")
        
        # Test transport module
        from zenoo_rpc.mcp.transport import MCPTransportType, MCPServerConfig
        print("✅ Transport components imported")
        
        # Test transport types
        assert MCPTransportType.STDIO.value == "stdio"
        assert MCPTransportType.HTTP.value == "http"
        assert MCPTransportType.SSE.value == "sse"
        print("✅ Transport types working")
        
        # Test server config creation
        config = MCPServerConfig(
            name="test",
            transport_type=MCPTransportType.STDIO,
            command="echo",
            args=["hello"]
        )
        assert config.name == "test"
        assert config.command == "echo"
        print("✅ Server config creation working")
        
        # Test exceptions
        from zenoo_rpc.mcp.exceptions import (
            MCPError,
            MCPConnectionError,
            MCPTimeoutError
        )
        
        # Test exception hierarchy
        assert issubclass(MCPConnectionError, MCPError)
        assert issubclass(MCPTimeoutError, MCPError)
        print("✅ Exception hierarchy working")
        
        # Test exception creation
        error = MCPError("Test error", server_name="test_server")
        assert error.server_name == "test_server"
        assert "test_server" in str(error)
        print("✅ Exception creation working")
        
        print("\n🎉 All MCP module structure tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_integration_structure():
    """Test MCP integration module structure."""
    print("\n🔍 Testing MCP Integration Structure")
    print("=" * 40)
    
    try:
        from zenoo_rpc.mcp.integration import MCPIntegration
        print("✅ MCPIntegration imported")
        
        # Test that integration class can be instantiated
        integration = MCPIntegration()
        print("✅ MCPIntegration instantiated")
        
        # Test initial state
        assert not integration.is_mcp_enabled()
        assert integration.get_mcp_manager() is None
        print("✅ Initial state correct")
        
        # Test that methods exist
        assert hasattr(integration, 'setup_mcp_manager')
        assert hasattr(integration, 'mcp_call_tool')
        assert hasattr(integration, 'mcp_read_resource')
        assert hasattr(integration, 'mcp_list_servers')
        print("✅ Required methods exist")
        
        print("\n🎉 MCP integration structure tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_configuration_validation():
    """Test MCP configuration validation."""
    print("\n🔍 Testing MCP Configuration Validation")
    print("=" * 40)
    
    try:
        from zenoo_rpc.mcp.transport import MCPServerConfig, MCPTransportType
        from zenoo_rpc.mcp.exceptions import MCPConfigurationError
        
        # Test valid stdio config
        stdio_config = MCPServerConfig(
            name="stdio_test",
            transport_type=MCPTransportType.STDIO,
            command="echo",
            args=["hello"]
        )
        assert stdio_config.transport_type == MCPTransportType.STDIO
        print("✅ Valid stdio config created")
        
        # Test valid HTTP config
        http_config = MCPServerConfig(
            name="http_test",
            transport_type=MCPTransportType.HTTP,
            url="http://localhost:8000/mcp"
        )
        assert http_config.transport_type == MCPTransportType.HTTP
        print("✅ Valid HTTP config created")
        
        # Test string transport type conversion
        string_config = MCPServerConfig(
            name="string_test",
            transport_type="stdio",
            command="echo",
            args=["test"]
        )
        assert string_config.transport_type == MCPTransportType.STDIO
        print("✅ String transport type conversion working")
        
        # Test invalid transport type
        try:
            invalid_config = MCPServerConfig(
                name="invalid",
                transport_type="invalid_transport",
                command="echo"
            )
            print("❌ Should have raised MCPConfigurationError")
            return False
        except MCPConfigurationError:
            print("✅ Invalid transport type properly rejected")
        
        # Test missing command for stdio
        try:
            no_command_config = MCPServerConfig(
                name="no_command",
                transport_type=MCPTransportType.STDIO
            )
            print("❌ Should have raised MCPConfigurationError for missing command")
            return False
        except MCPConfigurationError:
            print("✅ Missing command properly rejected")
        
        # Test missing URL for HTTP
        try:
            no_url_config = MCPServerConfig(
                name="no_url",
                transport_type=MCPTransportType.HTTP
            )
            print("❌ Should have raised MCPConfigurationError for missing URL")
            return False
        except MCPConfigurationError:
            print("✅ Missing URL properly rejected")
        
        print("\n🎉 MCP configuration validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_transport_manager():
    """Test MCP transport manager basic functionality."""
    print("\n🔍 Testing MCP Transport Manager")
    print("=" * 40)
    
    try:
        from zenoo_rpc.mcp.transport import MCPTransportManager, MCPServerConfig, MCPTransportType
        
        # Create transport manager
        manager = MCPTransportManager()
        print("✅ Transport manager created")
        
        # Test initial state
        assert manager.list_transports() == []
        print("✅ Initial state correct")
        
        # Add transport
        config = MCPServerConfig(
            name="test_transport",
            transport_type=MCPTransportType.STDIO,
            command="echo",
            args=["test"]
        )
        
        transport = manager.add_transport(config)
        assert transport is not None
        print("✅ Transport added successfully")
        
        # Test transport listing
        transports = manager.list_transports()
        assert "test_transport" in transports
        print("✅ Transport listing working")
        
        # Test transport retrieval
        retrieved_transport = manager.get_transport("test_transport")
        assert retrieved_transport is not None
        assert retrieved_transport.name == "test_transport"
        print("✅ Transport retrieval working")
        
        # Test transport removal
        removed = manager.remove_transport("test_transport")
        assert removed is True
        assert manager.list_transports() == []
        print("✅ Transport removal working")
        
        # Test removing non-existent transport
        removed = manager.remove_transport("non_existent")
        assert removed is False
        print("✅ Non-existent transport removal handled correctly")
        
        print("\n🎉 MCP transport manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all basic MCP tests."""
    print("🚀 Starting MCP Basic Tests")
    print("=" * 50)
    
    tests = [
        test_mcp_module_structure,
        test_mcp_integration_structure,
        test_mcp_configuration_validation,
        test_mcp_transport_manager,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All MCP basic tests passed successfully!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
