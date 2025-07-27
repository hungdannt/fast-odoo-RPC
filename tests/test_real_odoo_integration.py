"""Test CRUD methods with actual Odoo instance."""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.exceptions import (
    AuthenticationError, 
    ValidationError, 
    ZenooError,
    ConnectionError
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
    finally:
        # Cleanup if needed
        pass


@pytest.fixture
async def unauthenticated_client():
    """Create unauthenticated client for testing."""
    return ZenooClient(ODOO_CONFIG["host"])


class TestRealOdooAuthentication:
    """Test authentication flow with real Odoo."""

    async def test_successful_authentication(self, real_odoo_client):
        """Test successful authentication with real credentials."""
        client = real_odoo_client
        
        # Verify authentication status
        assert client.is_authenticated
        assert client.database == ODOO_CONFIG["database"]
        assert client.username == ODOO_CONFIG["username"]
        assert client.uid is not None
        assert client.uid > 0
        
        print(f"✅ Authenticated as user ID: {client.uid}")
        print(f"✅ Connected to database: {client.database}")

    async def test_invalid_credentials(self, unauthenticated_client):
        """Test authentication with invalid credentials."""
        client = unauthenticated_client
        
        with pytest.raises(AuthenticationError):
            await client.login(
                ODOO_CONFIG["database"],
                "invalid_user",
                "invalid_password"
            )

    async def test_invalid_database(self, unauthenticated_client):
        """Test authentication with invalid database."""
        client = unauthenticated_client
        
        with pytest.raises(AuthenticationError):
            await client.login(
                "invalid_database",
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )

    async def test_server_version_info(self, real_odoo_client):
        """Test server version information retrieval."""
        client = real_odoo_client
        
        version_info = client.server_version
        assert version_info is not None
        
        print(f"✅ Server version: {version_info}")


class TestRealOdooCRUDOperations:
    """Test CRUD operations with real Odoo."""

    async def test_create_partner_success(self, real_odoo_client):
        """Test creating a partner record."""
        client = real_odoo_client
        
        # Create test partner
        partner_data = {
            "name": f"Test Partner {int(time.time())}",
            "email": f"test{int(time.time())}@example.com",
            "phone": "+1234567890",
            "is_company": False,
            "comment": "Created by Zenoo-RPC integration test"
        }
        
        start_time = time.time()
        partner_id = await client.create("res.partner", partner_data)
        create_time = time.time() - start_time
        
        # Verify result
        assert isinstance(partner_id, int)
        assert partner_id > 0
        
        print(f"✅ Created partner ID: {partner_id}")
        print(f"✅ Create operation took: {create_time:.3f}s")
        
        # Store for cleanup
        return partner_id

    async def test_read_partner_success(self, real_odoo_client):
        """Test reading partner records."""
        client = real_odoo_client
        
        # First create a partner to read
        partner_data = {
            "name": f"Read Test Partner {int(time.time())}",
            "email": f"read{int(time.time())}@example.com"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Read the partner
        start_time = time.time()
        partners = await client.read("res.partner", [partner_id], ["name", "email", "phone"])
        read_time = time.time() - start_time
        
        # Verify result
        assert len(partners) == 1
        partner = partners[0]
        assert partner["id"] == partner_id
        assert partner["name"] == partner_data["name"]
        assert partner["email"] == partner_data["email"]
        
        print(f"✅ Read partner: {partner}")
        print(f"✅ Read operation took: {read_time:.3f}s")

    async def test_write_partner_success(self, real_odoo_client):
        """Test updating partner records."""
        client = real_odoo_client
        
        # Create partner to update
        partner_data = {
            "name": f"Update Test Partner {int(time.time())}",
            "phone": "+1111111111"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Update the partner
        update_data = {
            "phone": "+2222222222",
            "mobile": "+3333333333",
            "comment": "Updated by Zenoo-RPC test"
        }
        
        start_time = time.time()
        result = await client.write("res.partner", [partner_id], update_data)
        write_time = time.time() - start_time
        
        # Verify result
        assert result is True
        
        # Verify changes
        updated_partners = await client.read("res.partner", [partner_id], ["phone", "mobile", "comment"])
        updated_partner = updated_partners[0]
        
        assert updated_partner["phone"] == update_data["phone"]
        assert updated_partner["mobile"] == update_data["mobile"]
        # Comment field might be HTML encoded, so check if it contains our text
        assert update_data["comment"] in str(updated_partner["comment"])
        
        print(f"✅ Updated partner ID: {partner_id}")
        print(f"✅ Write operation took: {write_time:.3f}s")

    async def test_search_read_partners(self, real_odoo_client):
        """Test search_read operation."""
        client = real_odoo_client
        
        # Search for partners with email
        start_time = time.time()
        partners = await client.search_read(
            "res.partner",
            domain=[("email", "!=", False)],
            fields=["name", "email", "phone"],
            limit=5
        )
        search_time = time.time() - start_time
        
        # Verify result
        assert isinstance(partners, list)
        assert len(partners) <= 5
        
        if partners:
            partner = partners[0]
            assert "id" in partner
            assert "name" in partner
            assert "email" in partner
            
        print(f"✅ Found {len(partners)} partners with email")
        print(f"✅ Search operation took: {search_time:.3f}s")

    async def test_unlink_partner_success(self, real_odoo_client):
        """Test deleting partner records."""
        client = real_odoo_client
        
        # Create partner to delete
        partner_data = {
            "name": f"Delete Test Partner {int(time.time())}",
            "email": f"delete{int(time.time())}@example.com"
        }
        partner_id = await client.create("res.partner", partner_data)
        
        # Delete the partner
        start_time = time.time()
        result = await client.unlink("res.partner", [partner_id])
        unlink_time = time.time() - start_time
        
        # Verify result
        assert result is True
        
        # Verify deletion - should not find the record
        try:
            await client.read("res.partner", [partner_id], ["name"])
            assert False, "Partner should have been deleted"
        except Exception:
            pass  # Expected - record not found
        
        print(f"✅ Deleted partner ID: {partner_id}")
        print(f"✅ Unlink operation took: {unlink_time:.3f}s")


class TestRealOdooErrorHandling:
    """Test error handling with real Odoo errors."""

    async def test_create_invalid_model(self, real_odoo_client):
        """Test creating record in non-existent model."""
        client = real_odoo_client
        
        with pytest.raises(ZenooError):
            await client.create("invalid.model", {"name": "Test"})

    async def test_create_invalid_field(self, real_odoo_client):
        """Test creating record with invalid field."""
        client = real_odoo_client
        
        with pytest.raises(ZenooError):
            await client.create("res.partner", {"invalid_field": "Test"})

    async def test_write_nonexistent_record(self, real_odoo_client):
        """Test updating non-existent record."""
        client = real_odoo_client
        
        # Use a very high ID that shouldn't exist
        nonexistent_id = 999999999
        
        with pytest.raises(ZenooError):
            await client.write("res.partner", [nonexistent_id], {"name": "Test"})

    async def test_unlink_nonexistent_record(self, real_odoo_client):
        """Test deleting non-existent record."""
        client = real_odoo_client
        
        # Use a very high ID that shouldn't exist
        nonexistent_id = 999999999
        
        with pytest.raises(ZenooError):
            await client.unlink("res.partner", [nonexistent_id])

    async def test_unauthenticated_operations(self, unauthenticated_client):
        """Test operations without authentication."""
        client = unauthenticated_client
        
        with pytest.raises(AuthenticationError):
            await client.create("res.partner", {"name": "Test"})
        
        with pytest.raises(AuthenticationError):
            await client.write("res.partner", [1], {"name": "Test"})
        
        with pytest.raises(AuthenticationError):
            await client.unlink("res.partner", [1])


class TestRealOdooPerformance:
    """Test performance characteristics with real Odoo."""

    async def test_bulk_create_performance(self, real_odoo_client):
        """Test bulk create operations performance."""
        client = real_odoo_client
        
        # Create multiple partners
        num_records = 10
        start_time = time.time()
        
        partner_ids = []
        for i in range(num_records):
            partner_data = {
                "name": f"Bulk Test Partner {i} {int(time.time())}",
                "email": f"bulk{i}{int(time.time())}@example.com"
            }
            partner_id = await client.create("res.partner", partner_data)
            partner_ids.append(partner_id)
        
        total_time = time.time() - start_time
        avg_time = total_time / num_records
        
        print(f"✅ Created {num_records} partners in {total_time:.3f}s")
        print(f"✅ Average time per create: {avg_time:.3f}s")
        
        # Cleanup
        await client.unlink("res.partner", partner_ids)
        
        assert len(partner_ids) == num_records
        assert avg_time < 2.0  # Should be less than 2 seconds per record

    async def test_concurrent_operations(self, real_odoo_client):
        """Test concurrent operations performance."""
        client = real_odoo_client
        
        async def create_partner(index):
            partner_data = {
                "name": f"Concurrent Partner {index} {int(time.time())}",
                "email": f"concurrent{index}{int(time.time())}@example.com"
            }
            return await client.create("res.partner", partner_data)
        
        # Run concurrent creates
        num_concurrent = 5
        start_time = time.time()
        
        tasks = [create_partner(i) for i in range(num_concurrent)]
        partner_ids = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        print(f"✅ Created {num_concurrent} partners concurrently in {total_time:.3f}s")
        
        # Cleanup
        await client.unlink("res.partner", partner_ids)
        
        assert len(partner_ids) == num_concurrent
        assert total_time < 10.0  # Should complete within 10 seconds
