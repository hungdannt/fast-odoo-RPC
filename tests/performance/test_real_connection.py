"""
Test real connection to Odoo server for performance benchmarking.

This script tests both zenoo_rpc and odoorpc connections to ensure
they work properly before running comprehensive benchmarks.
"""

import asyncio
import time
from typing import Dict, Any

# zenoo_rpc imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.zenoo_rpc import ZenooClient

# odoorpc imports
try:
    import odoorpc
    ODOORPC_AVAILABLE = True
except ImportError:
    ODOORPC_AVAILABLE = False
    print("Warning: odoorpc not available. Install with: pip install odoorpc")

# Configuration
ODOO_URL = "https://85588445-18-0-all.runbot157.odoo.com"
ODOO_DATABASE = "85588445-18-0-all"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "admin"


async def test_zenoo_rpc_connection():
    """Test zenoo_rpc connection and basic operations."""
    print("\n🔧 Testing zenoo_rpc connection...")
    
    try:
        # Create client
        client = ZenooClient(ODOO_URL)
        
        # Test authentication
        start_time = time.time()
        await client.login(ODOO_DATABASE, ODOO_USERNAME, ODOO_PASSWORD)
        auth_time = time.time() - start_time
        print(f"✅ Authentication successful in {auth_time:.2f}s")
        
        # Test basic read operation
        start_time = time.time()
        partners = await client.search_read(
            "res.partner",
            domain=[],
            fields=["name", "email", "is_company"],
            limit=5
        )
        read_time = time.time() - start_time
        print(f"✅ Read {len(partners)} partners in {read_time:.2f}s")
        
        # Display sample data
        for partner in partners[:3]:
            print(f"   - {partner.get('name', 'N/A')} ({partner.get('email', 'no email')})")
        
        # Test create operation
        start_time = time.time()
        partner_id = await client.execute_kw(
            "res.partner",
            "create",
            [{
                "name": f"Benchmark Test Partner {int(time.time())}",
                "email": f"benchmark{int(time.time())}@test.com",
                "is_company": False
            }]
        )
        create_time = time.time() - start_time
        print(f"✅ Created partner ID {partner_id} in {create_time:.2f}s")
        
        # Test update operation
        start_time = time.time()
        await client.execute_kw(
            "res.partner",
            "write",
            [[partner_id], {"name": f"Updated Benchmark Partner {int(time.time())}"}]
        )
        update_time = time.time() - start_time
        print(f"✅ Updated partner in {update_time:.2f}s")
        
        # Test delete operation
        start_time = time.time()
        await client.execute_kw(
            "res.partner",
            "unlink",
            [[partner_id]]
        )
        delete_time = time.time() - start_time
        print(f"✅ Deleted partner in {delete_time:.2f}s")
        
        # Close connection
        await client.close()
        
        return {
            "auth_time": auth_time,
            "read_time": read_time,
            "create_time": create_time,
            "update_time": update_time,
            "delete_time": delete_time,
            "total_records": len(partners)
        }
        
    except Exception as e:
        print(f"❌ zenoo_rpc test failed: {e}")
        return None


def test_odoorpc_connection():
    """Test odoorpc connection and basic operations."""
    print("\n🔧 Testing odoorpc connection...")
    
    if not ODOORPC_AVAILABLE:
        print("❌ odoorpc not available. Install with: pip install odoorpc")
        return None
    
    try:
        # Parse URL for odoorpc
        from urllib.parse import urlparse
        parsed = urlparse(ODOO_URL)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        # Create client
        start_time = time.time()
        client = odoorpc.ODOO(host, port=port, protocol=parsed.scheme)
        client.login(ODOO_DATABASE, ODOO_USERNAME, ODOO_PASSWORD)
        auth_time = time.time() - start_time
        print(f"✅ Authentication successful in {auth_time:.2f}s")
        
        # Test basic read operation
        start_time = time.time()
        Partner = client.env['res.partner']
        partners = Partner.search_read(
            [],
            ['name', 'email', 'is_company'],
            limit=5
        )
        read_time = time.time() - start_time
        print(f"✅ Read {len(partners)} partners in {read_time:.2f}s")
        
        # Display sample data
        for partner in partners[:3]:
            print(f"   - {partner.get('name', 'N/A')} ({partner.get('email', 'no email')})")
        
        # Test create operation
        start_time = time.time()
        partner_id = Partner.create({
            "name": f"Benchmark Test Partner {int(time.time())}",
            "email": f"benchmark{int(time.time())}@test.com",
            "is_company": False
        })
        create_time = time.time() - start_time
        print(f"✅ Created partner ID {partner_id} in {create_time:.2f}s")
        
        # Test update operation
        start_time = time.time()
        partner = Partner.browse(partner_id)
        partner.write({"name": f"Updated Benchmark Partner {int(time.time())}"})
        update_time = time.time() - start_time
        print(f"✅ Updated partner in {update_time:.2f}s")
        
        # Test delete operation
        start_time = time.time()
        partner.unlink()
        delete_time = time.time() - start_time
        print(f"✅ Deleted partner in {delete_time:.2f}s")
        
        # Close connection
        client.logout()
        
        return {
            "auth_time": auth_time,
            "read_time": read_time,
            "create_time": create_time,
            "update_time": update_time,
            "delete_time": delete_time,
            "total_records": len(partners)
        }
        
    except Exception as e:
        print(f"❌ odoorpc test failed: {e}")
        return None


async def main():
    """Run connection tests and compare basic performance."""
    print("🚀 ZENOO-RPC vs ODOORPC CONNECTION TEST")
    print("=" * 60)
    
    # Test zenoo_rpc
    zenoo_results = await test_zenoo_rpc_connection()
    
    # Test odoorpc
    odoorpc_results = test_odoorpc_connection()
    
    # Compare results
    print("\n📊 PERFORMANCE COMPARISON")
    print("-" * 60)
    
    if zenoo_results and odoorpc_results:
        operations = ["auth_time", "read_time", "create_time", "update_time", "delete_time"]
        
        for op in operations:
            zenoo_time = zenoo_results[op]
            odoorpc_time = odoorpc_results[op]
            improvement = ((odoorpc_time - zenoo_time) / odoorpc_time * 100) if odoorpc_time > 0 else 0
            
            print(f"{op.replace('_', ' ').title()}:")
            print(f"  zenoo_rpc: {zenoo_time:.3f}s")
            print(f"  odoorpc:   {odoorpc_time:.3f}s")
            print(f"  Improvement: {improvement:+.1f}%")
            print()
        
        print(f"Total records found: {zenoo_results['total_records']}")
        
    elif zenoo_results:
        print("✅ zenoo_rpc connection successful")
        print("❌ odoorpc connection failed")
        
    elif odoorpc_results:
        print("❌ zenoo_rpc connection failed")
        print("✅ odoorpc connection successful")
        
    else:
        print("❌ Both connections failed")
    
    print("\n" + "=" * 60)
    print("CONNECTION TEST COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
