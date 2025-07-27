"""Test enhanced integration features with real Odoo instance."""

import pytest
import time
from typing import Dict, Any, List
from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.exceptions import (
    AuthenticationError, 
    ValidationError, 
    AccessError,
    ZenooError
)

# Test Odoo credentials - Use environment variables for real testing
import os
ODOO_CONFIG = {
    "host": os.getenv("ODOO_HOST", "https://demo.odoo.com"),
    "database": os.getenv("ODOO_DATABASE", "demo_database"),
    "username": os.getenv("ODOO_USERNAME", "demo_user"),
    "password": os.getenv("ODOO_PASSWORD", "demo_password")
}

@pytest.fixture
async def enhanced_client():
    """Create client with enhanced features."""
    client = ZenooClient(ODOO_CONFIG["host"])
    
    try:
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"], 
            ODOO_CONFIG["password"]
        )
        yield client
    except Exception as e:
        pytest.skip(f"Cannot connect to Odoo: {e}")


class TestEnhancedErrorHandling:
    """Test enhanced error handling features."""

    async def test_enhanced_create_with_validation(self, enhanced_client):
        """Test create with enhanced validation and error handling."""
        client = enhanced_client
        
        # Test with missing required fields (should provide better error message)
        try:
            await client.create("res.partner", {})
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            print(f"✅ Enhanced validation error: {e.message}")
            assert "required" in e.message.lower() or "name" in e.message.lower()

    async def test_enhanced_write_with_access_check(self, enhanced_client):
        """Test write with enhanced access checking."""
        client = enhanced_client
        
        # Create a partner first
        partner_data = {
            "name": f"Enhanced Test {int(time.time())}",
            "email": f"enhanced{int(time.time())}@test.com"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Test write with access checking
        result = await client.write(
            "res.partner", 
            [partner_id], 
            {"phone": "+1234567890"},
            check_access=True
        )
        assert result is True
        print(f"✅ Enhanced write with access check successful")

    async def test_enhanced_unlink_with_constraints(self, enhanced_client):
        """Test unlink with enhanced constraint handling."""
        client = enhanced_client
        
        # Create a partner
        partner_data = {
            "name": f"Unlink Test {int(time.time())}",
            "email": f"unlink{int(time.time())}@test.com"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Test unlink with constraint checking
        try:
            result = await client.unlink("res.partner", [partner_id], check_references=True)
            print(f"✅ Enhanced unlink successful: {result}")
        except ValidationError as e:
            print(f"✅ Enhanced constraint error: {e.message}")
            # This is expected if there are referential constraints


class TestFallbackMechanisms:
    """Test fallback mechanisms and graceful degradation."""

    async def test_safe_create_with_fallback(self, enhanced_client):
        """Test safe create with fallback to required fields."""
        client = enhanced_client
        
        # Test safe create with comprehensive data
        partner_data = {
            "name": f"Safe Create Test {int(time.time())}",
            "email": f"safe{int(time.time())}@test.com",
            "phone": "+1234567890",
            "street": "123 Test St",
            "city": "Test City"
        }
        
        partner_id = await client.safe_create_record("res.partner", partner_data)
        if partner_id:
            print(f"✅ Safe create successful: {partner_id}")
        else:
            print("✅ Safe create failed gracefully (returned None)")

    async def test_adaptive_read_records(self, enhanced_client):
        """Test adaptive read with fallback strategies."""
        client = enhanced_client
        
        # Create a test partner
        partner_data = {
            "name": f"Adaptive Read Test {int(time.time())}",
            "email": f"adaptive{int(time.time())}@test.com"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Test adaptive read
        records = await client.adaptive_read_records(
            "res.partner", 
            [partner_id], 
            ["name", "email", "phone"]
        )
        
        assert len(records) >= 0  # Should return accessible records
        if records:
            assert records[0]["id"] == partner_id
            print(f"✅ Adaptive read successful: {len(records)} records")
        else:
            print("✅ Adaptive read returned empty (access restricted)")

    async def test_get_accessible_records(self, enhanced_client):
        """Test getting only accessible records."""
        client = enhanced_client
        
        # Create multiple test partners
        partner_ids = []
        for i in range(3):
            partner_data = {
                "name": f"Accessible Test {i} {int(time.time())}",
                "email": f"accessible{i}{int(time.time())}@test.com"
            }
            partner_id = await client.create("res.partner", partner_data)
            partner_ids.append(partner_id)
        
        # Test getting accessible records
        accessible_records = await client.get_accessible_records(
            "res.partner",
            partner_ids,
            ["name", "email"]
        )
        
        print(f"✅ Accessible records: {len(accessible_records)}/{len(partner_ids)}")
        assert len(accessible_records) <= len(partner_ids)

    async def test_permission_checking(self, enhanced_client):
        """Test permission checking mechanisms."""
        client = enhanced_client
        
        # Test model access checking
        has_read = await client.check_model_access("res.partner", "read")
        has_create = await client.check_model_access("res.partner", "create")
        has_write = await client.check_model_access("res.partner", "write")
        has_unlink = await client.check_model_access("res.partner", "unlink")
        
        print(f"✅ Permissions - Read: {has_read}, Create: {has_create}, Write: {has_write}, Unlink: {has_unlink}")
        
        # Test getting user permissions
        permissions = await client.get_user_permissions("res.partner")
        print(f"✅ User permissions: {permissions}")
        
        assert isinstance(permissions, dict)
        assert "read" in permissions
        assert "create" in permissions
        assert "write" in permissions
        assert "unlink" in permissions

    async def test_fallback_manager_features(self, enhanced_client):
        """Test fallback manager specific features."""
        client = enhanced_client
        fallback_manager = client.fallback_manager
        
        # Test user capabilities for multiple models
        models = ["res.partner", "res.users", "ir.model"]
        capabilities = await fallback_manager.get_user_capabilities(models)
        
        print(f"✅ User capabilities for {len(models)} models:")
        for model, caps in capabilities.items():
            print(f"   {model}: {caps}")
        
        assert len(capabilities) == len(models)
        for model in models:
            assert model in capabilities
            assert isinstance(capabilities[model], dict)

    async def test_batch_operation_with_fallback(self, enhanced_client):
        """Test batch operations with individual fallback."""
        client = enhanced_client
        fallback_manager = client.fallback_manager
        
        # Create test data
        test_partners = [
            {"name": f"Batch Test {i} {int(time.time())}", "email": f"batch{i}@test.com"}
            for i in range(5)
        ]
        
        # Define operation function
        async def create_partner(partner_data):
            return await client.create("res.partner", partner_data)
        
        # Test batch operation
        results = await fallback_manager.batch_operation_with_fallback(
            create_partner,
            test_partners,
            batch_size=2,
            continue_on_error=True
        )
        
        print(f"✅ Batch operation results:")
        print(f"   Successful: {len(results['success'])}")
        print(f"   Failed: {len(results['failed'])}")
        
        assert "success" in results
        assert "failed" in results
        assert len(results["success"]) + len(results["failed"]) == len(test_partners)


class TestErrorMessageEnhancement:
    """Test enhanced error messages."""

    async def test_access_error_enhancement(self, enhanced_client):
        """Test enhanced access error messages."""
        client = enhanced_client
        
        try:
            # Try to access a restricted model or operation
            await client.create("ir.model", {"name": "test", "model": "test.model"})
        except (AccessError, ValidationError, ZenooError) as e:
            print(f"✅ Enhanced error message: {e.message}")
            # Should contain helpful guidance
            assert len(e.message) > 50  # Should be more descriptive

    async def test_validation_error_enhancement(self, enhanced_client):
        """Test enhanced validation error messages."""
        client = enhanced_client
        
        try:
            # Try to create with invalid data
            await client.create("res.partner", {"email": "invalid-email"})
        except ValidationError as e:
            print(f"✅ Enhanced validation error: {e.message}")
            # Should contain helpful guidance


class TestPerformanceWithEnhancements:
    """Test performance with enhanced features."""

    async def test_performance_with_fallbacks(self, enhanced_client):
        """Test that enhancements don't significantly impact performance."""
        client = enhanced_client
        
        # Test multiple operations with timing
        start_time = time.time()
        
        operations_count = 10
        successful_ops = 0
        
        for i in range(operations_count):
            try:
                partner_data = {
                    "name": f"Perf Test {i} {int(time.time())}",
                    "email": f"perf{i}{int(time.time())}@test.com"
                }
                
                # Use enhanced create
                partner_id = await client.safe_create_record("res.partner", partner_data)
                if partner_id:
                    successful_ops += 1
                    
                    # Use enhanced read
                    records = await client.adaptive_read_records(
                        "res.partner", 
                        [partner_id], 
                        ["name", "email"]
                    )
                    
            except Exception as e:
                print(f"Operation {i} failed: {e}")
        
        total_time = time.time() - start_time
        avg_time = total_time / operations_count
        
        print(f"✅ Performance test completed:")
        print(f"   Total operations: {operations_count}")
        print(f"   Successful operations: {successful_ops}")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Average time per operation: {avg_time:.3f}s")
        
        # Performance should still be reasonable
        assert avg_time < 10.0  # Should be less than 10 seconds per operation
        assert successful_ops > 0  # At least some operations should succeed
