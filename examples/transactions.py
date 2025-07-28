"""
Transaction management example for Zenoo-RPC.

This example demonstrates transaction capabilities including
ACID compliance, rollback scenarios, and batch operations.
"""

import asyncio
import logging
from typing import List

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import AuthenticationError, ValidationError, ZenooError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_transaction_example():
    """Demonstrate basic transaction usage."""
    print("=== Basic Transaction Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            print("✅ Authenticated successfully")
            
            # Setup transaction manager
            await client.setup_transaction_manager()
            print("✅ Transaction manager initialized")
            
            # Example 1: Successful transaction
            print("\n🔄 Example 1: Successful Transaction")
            async with client.transaction():
                # Create a test partner
                partner_data = {
                    "name": "Transaction Test Partner",
                    "email": "transaction@zenoo-rpc.com",
                    "is_company": False
                }
                
                partner_id = await client.create("res.partner", partner_data)
                print(f"  Created partner with ID: {partner_id}")
                
                # Update the partner in same transaction
                await client.write("res.partner", [partner_id], {
                    "phone": "+1234567890"
                })
                print("  Updated partner phone")
                
                # Read back to verify
                partner = await client.read("res.partner", [partner_id], 
                                          ["name", "email", "phone"])
                print(f"  Verified: {partner[0]['name']} - {partner[0]['phone']}")
                
                # Transaction will be committed automatically
            
            print("✅ Transaction committed successfully")
            
            # Cleanup - delete the test partner
            await client.unlink("res.partner", [partner_id])
            print("🧹 Cleaned up test partner")
            
    except Exception as e:
        logger.error(f"Error in basic transaction: {e}")
        print(f"❌ Error: {e}")


async def rollback_transaction_example():
    """Demonstrate transaction rollback."""
    print("\n=== Transaction Rollback Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            await client.setup_transaction_manager()
            
            # Count partners before transaction
            initial_count = await client.search_count("res.partner", [])
            print(f"Initial partner count: {initial_count}")
            
            try:
                async with client.transaction():
                    # Create a partner
                    partner_data = {
                        "name": "Rollback Test Partner",
                        "email": "rollback@zenoo-rpc.com"
                    }
                    
                    partner_id = await client.create("res.partner", partner_data)
                    print(f"  Created partner with ID: {partner_id}")
                    
                    # Simulate an error that causes rollback
                    # This will cause the transaction to rollback
                    raise ValidationError("Simulated validation error")
                    
            except ValidationError as e:
                print(f"  Expected error occurred: {e}")
                print("  Transaction should be rolled back")
            
            # Verify rollback - count should be the same
            final_count = await client.search_count("res.partner", [])
            print(f"Final partner count: {final_count}")
            
            if initial_count == final_count:
                print("✅ Transaction rollback successful - no data was committed")
            else:
                print("❌ Transaction rollback failed - data was committed")
                
    except Exception as e:
        logger.error(f"Error in rollback example: {e}")
        print(f"❌ Error: {e}")


async def nested_transaction_example():
    """Demonstrate nested transaction behavior."""
    print("\n=== Nested Transaction Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            await client.setup_transaction_manager()
            
            partner_ids = []
            
            try:
                # Outer transaction
                async with client.transaction():
                    print("  Started outer transaction")
                    
                    # Create first partner
                    partner1_data = {
                        "name": "Nested Transaction Partner 1",
                        "email": "nested1@zenoo-rpc.com"
                    }
                    partner1_id = await client.create("res.partner", partner1_data)
                    partner_ids.append(partner1_id)
                    print(f"    Created partner 1: {partner1_id}")
                    
                    # Inner transaction (savepoint)
                    try:
                        async with client.transaction():
                            print("    Started inner transaction")
                            
                            # Create second partner
                            partner2_data = {
                                "name": "Nested Transaction Partner 2",
                                "email": "nested2@zenoo-rpc.com"
                            }
                            partner2_id = await client.create("res.partner", partner2_data)
                            partner_ids.append(partner2_id)
                            print(f"      Created partner 2: {partner2_id}")
                            
                            # Simulate error in inner transaction
                            raise ValidationError("Inner transaction error")
                            
                    except ValidationError as e:
                        print(f"    Inner transaction error: {e}")
                        print("    Inner transaction rolled back")
                    
                    print("  Outer transaction continues...")
                    
                    # Create third partner in outer transaction
                    partner3_data = {
                        "name": "Nested Transaction Partner 3",
                        "email": "nested3@zenoo-rpc.com"
                    }
                    partner3_id = await client.create("res.partner", partner3_data)
                    partner_ids.append(partner3_id)
                    print(f"    Created partner 3: {partner3_id}")
                
                print("✅ Outer transaction committed")
                
                # Verify which partners exist
                for partner_id in partner_ids:
                    try:
                        partner = await client.read("res.partner", [partner_id], ["name"])
                        print(f"  ✅ Partner {partner_id} exists: {partner[0]['name']}")
                    except Exception:
                        print(f"  ❌ Partner {partner_id} does not exist (rolled back)")
                
                # Cleanup existing partners
                existing_partners = []
                for partner_id in partner_ids:
                    try:
                        await client.read("res.partner", [partner_id], ["id"])
                        existing_partners.append(partner_id)
                    except Exception:
                        pass
                
                if existing_partners:
                    await client.unlink("res.partner", existing_partners)
                    print(f"🧹 Cleaned up {len(existing_partners)} test partners")
                
            except Exception as e:
                print(f"  Outer transaction error: {e}")
                
    except Exception as e:
        logger.error(f"Error in nested transaction example: {e}")
        print(f"❌ Error: {e}")


async def main():
    """Run all transaction examples."""
    print("🚀 Zenoo RPC Transaction Management Examples")
    print("=" * 60)
    
    await basic_transaction_example()
    await rollback_transaction_example()
    await nested_transaction_example()
    
    print("\n✨ Transaction examples completed!")
    print("\n📚 Key takeaways:")
    print("  - ACID compliance with automatic commit/rollback")
    print("  - Exception handling triggers rollback")
    print("  - Nested transactions with savepoints")
    print("  - Context manager ensures proper cleanup")
    print("  - Transaction manager setup required")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")
        print(f"❌ Failed to run examples: {e}")
