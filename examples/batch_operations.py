"""
Batch operations example for Zenoo-RPC.

This example demonstrates efficient bulk operations including
batch creation, updates, and performance optimization techniques.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import AuthenticationError, ZenooError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def batch_creation_example():
    """Demonstrate batch creation operations."""
    print("=== Batch Creation Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            print("✅ Authenticated successfully")
            
            # Setup batch manager
            await client.setup_batch_manager(max_chunk_size=50)
            print("✅ Batch manager initialized")
            
            # Prepare test data
            partners_data = []
            for i in range(10):
                partners_data.append({
                    "name": f"Batch Test Partner {i+1}",
                    "email": f"batch{i+1}@zenoo-rpc.com",
                    "is_company": i % 3 == 0,  # Every 3rd is a company
                    "phone": f"+123456789{i:02d}"
                })
            
            print(f"📦 Creating {len(partners_data)} partners in batch...")
            
            # Measure performance
            start_time = time.time()
            
            # Batch creation
            async with client.batch():
                partner_ids = []
                for partner_data in partners_data:
                    partner_id = await client.create("res.partner", partner_data)
                    partner_ids.append(partner_id)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Created {len(partner_ids)} partners in {duration:.2f} seconds")
            print(f"   Average: {duration/len(partner_ids):.3f} seconds per partner")
            print(f"   Partner IDs: {partner_ids[:3]}...{partner_ids[-3:] if len(partner_ids) > 6 else partner_ids[3:]}")
            
            # Verify creation
            created_partners = await client.search_read("res.partner", [
                ["id", "in", partner_ids]
            ], ["name", "email", "is_company"])
            
            print(f"✅ Verified {len(created_partners)} partners created:")
            for partner in created_partners[:3]:  # Show first 3
                partner_type = "Company" if partner['is_company'] else "Individual"
                print(f"   - {partner['name']} ({partner_type})")
            
            if len(created_partners) > 3:
                print(f"   ... and {len(created_partners) - 3} more")
            
            # Cleanup
            await client.unlink("res.partner", partner_ids)
            print(f"🧹 Cleaned up {len(partner_ids)} test partners")
            
    except Exception as e:
        logger.error(f"Error in batch creation: {e}")
        print(f"❌ Error: {e}")


async def batch_update_example():
    """Demonstrate batch update operations."""
    print("\n=== Batch Update Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            await client.setup_batch_manager()
            
            # First, create some test partners
            print("📦 Creating test partners for batch update...")
            partners_data = [
                {"name": f"Update Test Partner {i+1}", "email": f"update{i+1}@zenoo-rpc.com"}
                for i in range(5)
            ]
            
            partner_ids = []
            for partner_data in partners_data:
                partner_id = await client.create("res.partner", partner_data)
                partner_ids.append(partner_id)
            
            print(f"✅ Created {len(partner_ids)} test partners")
            
            # Batch update
            print("🔄 Performing batch updates...")
            start_time = time.time()
            
            async with client.batch():
                for i, partner_id in enumerate(partner_ids):
                    update_data = {
                        "phone": f"+987654321{i:02d}",
                        "website": f"https://partner{i+1}.example.com"
                    }
                    await client.write("res.partner", [partner_id], update_data)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Updated {len(partner_ids)} partners in {duration:.2f} seconds")
            
            # Verify updates
            updated_partners = await client.search_read("res.partner", [
                ["id", "in", partner_ids]
            ], ["name", "phone", "website"])
            
            print("✅ Verified updates:")
            for partner in updated_partners:
                print(f"   - {partner['name']}: {partner['phone']} | {partner['website']}")
            
            # Cleanup
            await client.unlink("res.partner", partner_ids)
            print(f"🧹 Cleaned up {len(partner_ids)} test partners")
            
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        print(f"❌ Error: {e}")


async def performance_comparison_example():
    """Compare batch vs individual operations performance."""
    print("\n=== Performance Comparison Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            
            # Test data
            test_data = [
                {"name": f"Perf Test Partner {i+1}", "email": f"perf{i+1}@zenoo-rpc.com"}
                for i in range(5)  # Small number for demo
            ]
            
            # Method 1: Individual operations
            print("🐌 Method 1: Individual Operations")
            start_time = time.time()
            
            individual_ids = []
            for partner_data in test_data:
                partner_id = await client.create("res.partner", partner_data)
                individual_ids.append(partner_id)
            
            individual_time = time.time() - start_time
            print(f"   Time: {individual_time:.3f} seconds")
            print(f"   Rate: {len(test_data)/individual_time:.1f} operations/second")
            
            # Method 2: Batch operations
            print("🚀 Method 2: Batch Operations")
            await client.setup_batch_manager()
            start_time = time.time()
            
            batch_ids = []
            async with client.batch():
                for partner_data in test_data:
                    partner_id = await client.create("res.partner", partner_data)
                    batch_ids.append(partner_id)
            
            batch_time = time.time() - start_time
            print(f"   Time: {batch_time:.3f} seconds")
            print(f"   Rate: {len(test_data)/batch_time:.1f} operations/second")
            
            # Performance improvement
            if batch_time > 0:
                improvement = (individual_time - batch_time) / individual_time * 100
                speedup = individual_time / batch_time
                print(f"\n📊 Performance Results:")
                print(f"   Improvement: {improvement:.1f}% faster")
                print(f"   Speedup: {speedup:.1f}x faster")
            
            # Cleanup
            all_ids = individual_ids + batch_ids
            if all_ids:
                await client.unlink("res.partner", all_ids)
                print(f"🧹 Cleaned up {len(all_ids)} test partners")
            
    except Exception as e:
        logger.error(f"Error in performance comparison: {e}")
        print(f"❌ Error: {e}")


async def main():
    """Run all batch operation examples."""
    print("🚀 Zenoo RPC Batch Operations Examples")
    print("=" * 50)
    
    await batch_creation_example()
    await batch_update_example()
    await performance_comparison_example()
    
    print("\n✨ Batch operation examples completed!")
    print("\n📚 Key takeaways:")
    print("  - Batch operations significantly improve performance")
    print("  - Automatic chunking for large datasets")
    print("  - Context manager ensures proper batch execution")
    print("  - Configurable batch size for optimization")
    print("  - Ideal for bulk data operations")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")
        print(f"❌ Failed to run examples: {e}")
