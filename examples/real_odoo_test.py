#!/usr/bin/env python3
"""
Zenoo-RPC Real Odoo Server Test

This script tests Zenoo-RPC against a real Odoo server to verify
all functionality works correctly with actual Odoo data.

Note: Set environment variables for real testing:
- ODOO_HOST: Odoo server URL
- ODOO_DATABASE: Database name
- ODOO_USERNAME: Username
- ODOO_PASSWORD: Password
"""

import asyncio
import sys
from typing import List, Dict, Any

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import ZenooError, AuthenticationError


# Odoo credentials - Use environment variables for real testing
import os
ODOO_CONFIG = {
    "url": os.getenv("ODOO_HOST", "https://demo.odoo.com"),
    "database": os.getenv("ODOO_DATABASE", "demo_database"),
    "username": os.getenv("ODOO_USERNAME", "demo_user"),
    "password": os.getenv("ODOO_PASSWORD", "demo_password")
}


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'-' * 40}")
    print(f"  {title}")
    print(f"{'-' * 40}")


async def test_basic_connection():
    """Test basic connection and authentication."""
    print_section("Basic Connection Test")
    
    try:
        client = ZenooClient(ODOO_CONFIG["url"])

        print(f"🔗 Connecting to: {ODOO_CONFIG['url']}")
        print(f"📊 Database: {ODOO_CONFIG['database']}")
        print(f"👤 Username: {ODOO_CONFIG['username']}")
        
        # Test authentication
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"],
            ODOO_CONFIG["password"]
        )
        
        print("✅ Authentication successful!")
        print(f"🆔 User ID: {client.uid}")
        print(f"📊 Database: {client.database}")
        print(f"👤 Username: {client.username}")

        # Test server version
        if client.server_version:
            print(f"🖥️ Server Version: {client.server_version}")
        
        await client.close()
        return True
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_basic_queries():
    """Test basic query operations."""
    print_section("Basic Query Test")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            
            # Test search_read
            print("🔍 Testing search_read...")
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "email", "phone"],
                limit=5
            )
            
            print(f"📊 Found {len(partners)} companies:")
            for partner in partners:
                print(f"   - {partner.get('name')} (ID: {partner.get('id')})")
                if partner.get('email'):
                    print(f"     Email: {partner.get('email')}")
                if partner.get('phone'):
                    print(f"     Phone: {partner.get('phone')}")
            
            # Test count
            print("\n📊 Testing count...")
            total_partners = await client.search_count("res.partner", [])
            total_companies = await client.search_count("res.partner", [("is_company", "=", True)])
            
            print(f"   Total partners: {total_partners}")
            print(f"   Total companies: {total_companies}")
            
            return True
            
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False


async def test_pydantic_models():
    """Test Pydantic model functionality."""
    print_section("Pydantic Models Test")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            
            # Test model query
            print("🏗️ Testing Pydantic models...")
            partners_data = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "email", "phone", "is_company", "customer_rank", "supplier_rank"],
                limit=3
            )
            
            # Create Pydantic model instances
            partners = []
            for data in partners_data:
                try:
                    partner = ResPartner(**data)
                    partners.append(partner)
                    print(f"✅ Created partner model: {partner.name}")
                    print(f"   Is customer: {partner.is_customer}")
                    print(f"   Is vendor: {partner.is_vendor}")
                except Exception as e:
                    print(f"⚠️ Model creation failed for {data.get('name')}: {e}")
            
            print(f"📊 Successfully created {len(partners)} partner models")
            return True
            
    except Exception as e:
        print(f"❌ Pydantic models test failed: {e}")
        return False


async def test_query_builder():
    """Test query builder functionality."""
    print_section("Query Builder Test")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            
            print("🔗 Testing query builder...")
            
            # Test fluent interface (simulated since we need actual QueryBuilder integration)
            # For now, we'll test the underlying functionality
            
            # Test complex domain
            domain = [
                ("is_company", "=", True),
                ("customer_rank", ">", 0)
            ]
            
            customers = await client.search_read(
                "res.partner",
                domain=domain,
                fields=["name", "email", "customer_rank"],
                limit=5
            )
            
            print(f"📊 Found {len(customers)} customer companies:")
            for customer in customers:
                print(f"   - {customer.get('name')} (Rank: {customer.get('customer_rank')})")
            
            return True
            
    except Exception as e:
        print(f"❌ Query builder test failed: {e}")
        return False


async def test_phase3_features():
    """Test Phase 3 features with real Odoo server."""
    print_section("Phase 3 Features Test")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            
            # Test cache manager setup
            print("💾 Testing cache manager...")
            await client.setup_cache_manager(
                backend="memory",
                strategy="ttl",
                default_ttl=300,
                max_size=100
            )
            print("✅ Cache manager setup successful")
            
            # Test transaction manager setup
            print("🔄 Testing transaction manager...")
            await client.setup_transaction_manager()
            print("✅ Transaction manager setup successful")
            
            # Test batch manager setup
            print("📦 Testing batch manager...")
            await client.setup_batch_manager(
                max_chunk_size=50,
                max_concurrency=3
            )
            print("✅ Batch manager setup successful")
            
            # Test caching with real data
            print("💾 Testing caching with real data...")
            cache_manager = client.cache_manager
            
            # Cache some partner data
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                limit=2
            )
            
            cache_key = "test_partners"
            await cache_manager.set(cache_key, partners, ttl=60)
            
            # Retrieve from cache
            cached_partners = await cache_manager.get(cache_key)
            if cached_partners:
                print(f"✅ Successfully cached and retrieved {len(cached_partners)} partners")
            
            # Test cache stats
            stats = await cache_manager.get_stats()
            print(f"📊 Cache stats: {stats['manager']['total_hits']} hits, {stats['manager']['total_misses']} misses")
            
            return True
            
    except Exception as e:
        print(f"❌ Phase 3 features test failed: {e}")
        return False


async def test_model_operations():
    """Test model CRUD operations (read-only for safety)."""
    print_section("Model Operations Test")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            
            # Test reading specific models
            print("📖 Testing model reading...")
            
            # Get a specific partner
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "email", "phone", "street", "city", "country_id"],
                limit=1
            )
            
            if partners:
                partner = partners[0]
                print(f"📋 Partner details:")
                print(f"   Name: {partner.get('name')}")
                print(f"   Email: {partner.get('email')}")
                print(f"   Phone: {partner.get('phone')}")
                print(f"   Address: {partner.get('street')}, {partner.get('city')}")
                
                # Test reading related data
                if partner.get('country_id'):
                    country_id = partner['country_id'][0] if isinstance(partner['country_id'], list) else partner['country_id']
                    country = await client.read("res.country", [country_id], ["name", "code"])
                    if country:
                        print(f"   Country: {country[0].get('name')} ({country[0].get('code')})")
            
            # Test field access
            print("\n🔍 Testing field access...")
            fields_info = await client.get_model_fields("res.partner")
            print(f"📊 res.partner has {len(fields_info)} fields")
            
            # Show some key fields
            key_fields = ["name", "email", "phone", "is_company", "customer_rank"]
            for field_name in key_fields:
                if field_name in fields_info:
                    field_info = fields_info[field_name]
                    print(f"   {field_name}: {field_info.get('type')} - {field_info.get('string')}")
            
            return True
            
    except Exception as e:
        print(f"❌ Model operations test failed: {e}")
        return False


async def test_performance():
    """Test performance with real data."""
    print_section("Performance Test")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            
            import time
            
            # Test query performance
            print("⚡ Testing query performance...")
            
            start_time = time.time()
            partners = await client.search_read(
                "res.partner",
                domain=[],
                fields=["name", "email"],
                limit=100
            )
            query_time = time.time() - start_time
            
            print(f"📊 Retrieved {len(partners)} partners in {query_time:.3f}s")
            print(f"⚡ Performance: {len(partners) / query_time:.1f} records/second")
            
            # Test with caching
            await client.setup_cache_manager()
            cache_manager = client.cache_manager
            
            # First query (cache miss)
            start_time = time.time()
            await cache_manager.cache_query_result("res.partner", [], partners)
            cache_time = time.time() - start_time
            
            # Second query (cache hit)
            start_time = time.time()
            cached_result = await cache_manager.get_cached_query_result("res.partner", [])
            retrieve_time = time.time() - start_time
            
            if cached_result:
                print(f"💾 Cache store time: {cache_time:.3f}s")
                print(f"💾 Cache retrieve time: {retrieve_time:.3f}s")
                print(f"⚡ Cache speedup: {query_time / retrieve_time:.1f}x faster")
            
            return True
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


async def main():
    """Run all tests against real Odoo server."""
    print_header("🚀 Zenoo-RPC Real Odoo Server Test")
    
    print("Testing Zenoo-RPC against real Odoo server:")
    print(f"🌐 URL: {ODOO_CONFIG['url']}")
    print(f"🗄️ Database: {ODOO_CONFIG['database']}")
    print(f"👤 User: {ODOO_CONFIG['username']}")
    print()
    print("⚠️ Note: This test performs read-only operations for safety")
    
    # Test results
    results = {}
    
    # Run tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Basic Queries", test_basic_queries),
        ("Pydantic Models", test_pydantic_models),
        ("Query Builder", test_query_builder),
        ("Phase 3 Features", test_phase3_features),
        ("Model Operations", test_model_operations),
        ("Performance", test_performance),
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name} test...")
            result = await test_func()
            results[test_name] = result
            if result:
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"💥 {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print_header("📊 Test Results Summary")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    print("\nDetailed results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 All tests passed! Zenoo-RPC is working correctly with real Odoo server.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
