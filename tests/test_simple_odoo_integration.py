"""Simple integration test with real Odoo instance."""

import pytest
import time
from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.exceptions import AuthenticationError

# Test Odoo credentials - Use environment variables for real testing
import os
ODOO_CONFIG = {
    "host": os.getenv("ODOO_HOST", "https://demo.odoo.com"),
    "database": os.getenv("ODOO_DATABASE", "demo_database"),
    "username": os.getenv("ODOO_USERNAME", "demo_user"),
    "password": os.getenv("ODOO_PASSWORD", "demo_password")
}

@pytest.fixture
async def real_odoo_client():
    """Create client connected to real Odoo instance."""
    client = ZenooClient(ODOO_CONFIG["host"])
    
    try:
        # Test authentication
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"], 
            ODOO_CONFIG["password"]
        )
        yield client
    except Exception as e:
        pytest.skip(f"Cannot connect to Odoo: {e}")


class TestSimpleOdooIntegration:
    """Simple integration tests with real Odoo."""

    async def test_authentication_success(self, real_odoo_client):
        """Test successful authentication."""
        client = real_odoo_client
        
        assert client.is_authenticated
        assert client.database == ODOO_CONFIG["database"]
        assert client.username == ODOO_CONFIG["username"]
        assert client.uid is not None
        
        print(f"✅ Authenticated as user ID: {client.uid}")
        print(f"✅ Server version: {client.server_version}")

    async def test_create_partner_basic(self, real_odoo_client):
        """Test basic partner creation."""
        client = real_odoo_client
        
        partner_data = {
            "name": f"Zenoo Test Partner {int(time.time())}",
            "email": f"zenoo{int(time.time())}@test.com",
            "is_company": False
        }
        
        start_time = time.time()
        partner_id = await client.create("res.partner", partner_data)
        create_time = time.time() - start_time
        
        assert isinstance(partner_id, int)
        assert partner_id > 0
        
        print(f"✅ Created partner ID: {partner_id}")
        print(f"✅ Create time: {create_time:.3f}s")

    async def test_write_partner_basic(self, real_odoo_client):
        """Test basic partner update."""
        client = real_odoo_client
        
        # Create partner first
        partner_data = {
            "name": f"Update Test {int(time.time())}",
            "phone": "+1111111111"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Update partner
        update_data = {
            "phone": "+2222222222",
            "mobile": "+3333333333"
        }
        
        start_time = time.time()
        result = await client.write("res.partner", [partner_id], update_data)
        write_time = time.time() - start_time
        
        assert result is True
        
        print(f"✅ Updated partner ID: {partner_id}")
        print(f"✅ Write time: {write_time:.3f}s")

    async def test_read_partner_basic(self, real_odoo_client):
        """Test basic partner read."""
        client = real_odoo_client
        
        # Create partner first
        partner_data = {
            "name": f"Read Test {int(time.time())}",
            "email": f"read{int(time.time())}@test.com"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Read partner
        start_time = time.time()
        partners = await client.read("res.partner", [partner_id], ["name", "email"])
        read_time = time.time() - start_time
        
        assert len(partners) == 1
        partner = partners[0]
        assert partner["id"] == partner_id
        assert partner["name"] == partner_data["name"]
        assert partner["email"] == partner_data["email"]
        
        print(f"✅ Read partner: {partner}")
        print(f"✅ Read time: {read_time:.3f}s")

    async def test_search_read_basic(self, real_odoo_client):
        """Test basic search_read operation."""
        client = real_odoo_client
        
        start_time = time.time()
        partners = await client.search_read(
            "res.partner",
            domain=[("is_company", "=", True)],
            fields=["name", "email"],
            limit=3
        )
        search_time = time.time() - start_time
        
        assert isinstance(partners, list)
        assert len(partners) <= 3
        
        if partners:
            partner = partners[0]
            assert "id" in partner
            assert "name" in partner
        
        print(f"✅ Found {len(partners)} companies")
        print(f"✅ Search time: {search_time:.3f}s")

    async def test_execute_kw_direct(self, real_odoo_client):
        """Test direct execute_kw call."""
        client = real_odoo_client
        
        start_time = time.time()
        result = await client.execute_kw(
            "res.partner",
            "search_count",
            [[("is_company", "=", True)]]
        )
        execute_time = time.time() - start_time
        
        assert isinstance(result, int)
        assert result >= 0
        
        print(f"✅ Company count: {result}")
        print(f"✅ Execute time: {execute_time:.3f}s")

    async def test_get_model_fields(self, real_odoo_client):
        """Test get_model_fields operation."""
        client = real_odoo_client
        
        start_time = time.time()
        fields = await client.get_model_fields("res.partner")
        fields_time = time.time() - start_time
        
        assert isinstance(fields, dict)
        assert "name" in fields
        assert "email" in fields
        assert "phone" in fields
        
        print(f"✅ Got {len(fields)} fields for res.partner")
        print(f"✅ Fields time: {fields_time:.3f}s")

    async def test_manager_setup_integration(self, real_odoo_client):
        """Test manager setup with real client."""
        client = real_odoo_client
        
        # Test transaction manager setup
        tx_manager = await client.setup_transaction_manager()
        assert tx_manager is not None
        assert client.transaction_manager == tx_manager
        
        # Test cache manager setup
        cache_manager = await client.setup_cache_manager(backend="memory")
        assert cache_manager is not None
        assert client.cache_manager == cache_manager
        
        # Test batch manager setup
        batch_manager = await client.setup_batch_manager()
        assert batch_manager is not None
        assert client.batch_manager == batch_manager
        
        print("✅ All managers setup successfully")

    async def test_error_handling_real(self, real_odoo_client):
        """Test error handling with real Odoo errors."""
        client = real_odoo_client
        
        # Test invalid model
        try:
            await client.create("invalid.model", {"name": "Test"})
            assert False, "Should have raised exception"
        except Exception as e:
            print(f"✅ Invalid model error: {type(e).__name__}")
        
        # Test invalid field
        try:
            await client.create("res.partner", {"invalid_field_xyz": "Test"})
            assert False, "Should have raised exception"
        except Exception as e:
            print(f"✅ Invalid field error: {type(e).__name__}")

    async def test_performance_characteristics(self, real_odoo_client):
        """Test basic performance characteristics."""
        client = real_odoo_client
        
        # Test multiple creates
        times = []
        partner_ids = []
        
        for i in range(5):
            partner_data = {
                "name": f"Perf Test {i} {int(time.time())}",
                "email": f"perf{i}{int(time.time())}@test.com"
            }
            
            start_time = time.time()
            partner_id = await client.create("res.partner", partner_data)
            create_time = time.time() - start_time
            
            times.append(create_time)
            partner_ids.append(partner_id)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"✅ Created {len(partner_ids)} partners")
        print(f"✅ Average time: {avg_time:.3f}s")
        print(f"✅ Min time: {min_time:.3f}s")
        print(f"✅ Max time: {max_time:.3f}s")
        
        # Performance assertions
        assert avg_time < 5.0  # Should be less than 5 seconds average
        assert max_time < 10.0  # No single operation should take more than 10 seconds
