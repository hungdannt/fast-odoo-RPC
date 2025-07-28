"""
Advanced ORM usage example for Zenoo-RPC.

This example demonstrates the advanced ORM capabilities of Zenoo-RPC,
including type-safe queries, method chaining, and relationship handling.
"""

import asyncio
import logging
from typing import Optional

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import AuthenticationError, ZenooError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def advanced_orm_example():
    """Demonstrate advanced ORM capabilities."""
    print("=== Advanced ORM Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            # Authenticate
            await client.login("your_database", "your_username", "your_password")
            print(f"✅ Authenticated as {client.username}")
            
            # Example 1: Type-safe queries with method chaining
            print("\n🔍 Example 1: Type-safe Queries")
            companies = await client.model(ResPartner).filter(
                is_company=True,
                customer_rank__gt=0  # Companies that are customers
            ).order_by("name").limit(5).all()
            
            print(f"Found {len(companies)} customer companies:")
            for company in companies:
                print(f"  - {company.name} (ID: {company.id})")
                if company.email:
                    print(f"    Email: {company.email}")
            
            # Example 2: Single record retrieval
            print("\n🎯 Example 2: Single Record Retrieval")
            if companies:
                first_company = await client.model(ResPartner).filter(
                    id=companies[0].id
                ).first()
                
                if first_company:
                    print(f"Retrieved: {first_company.name}")
                    print(f"  Type: {'Company' if first_company.is_company else 'Individual'}")
                    print(f"  Customer rank: {first_company.customer_rank}")
            
            # Example 3: Complex filtering
            print("\n🔧 Example 3: Complex Filtering")
            contacts = await client.model(ResPartner).filter(
                is_company=False,  # Individuals only
                email__isnull=False,  # Must have email
                customer_rank__gt=0  # Must be customers
            ).limit(3).all()
            
            print(f"Found {len(contacts)} individual customers with email:")
            for contact in contacts:
                print(f"  - {contact.name}: {contact.email}")
            
            # Example 4: Counting records
            print("\n📊 Example 4: Counting Records")
            total_partners = await client.model(ResPartner).count()
            total_companies = await client.model(ResPartner).filter(
                is_company=True
            ).count()
            total_customers = await client.model(ResPartner).filter(
                customer_rank__gt=0
            ).count()
            
            print(f"Total partners: {total_partners}")
            print(f"Total companies: {total_companies}")
            print(f"Total customers: {total_customers}")
            
            # Example 5: Field selection (optimization)
            print("\n⚡ Example 5: Field Selection for Performance")
            lightweight_partners = await client.model(ResPartner).filter(
                is_company=True
            ).only("name", "email", "phone").limit(3).all()
            
            print("Lightweight partner data (only selected fields):")
            for partner in lightweight_partners:
                print(f"  - {partner.name}")
                print(f"    Email: {partner.email or 'N/A'}")
                print(f"    Phone: {getattr(partner, 'phone', 'N/A')}")
            
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        print("❌ Please check your credentials and try again.")
    except ZenooError as e:
        logger.error(f"Zenoo RPC error: {e}")
        print(f"❌ Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")


async def relationship_example():
    """Demonstrate relationship handling."""
    print("\n=== Relationship Handling Example ===")
    
    try:
        async with ZenooClient("https://your-odoo-server.com") as client:
            await client.login("your_database", "your_username", "your_password")
            
            # Find a company with contacts
            company = await client.model(ResPartner).filter(
                is_company=True,
                child_ids__isnull=False  # Has child contacts
            ).first()
            
            if company:
                print(f"Company: {company.name}")
                
                # Get child contacts (lazy loading)
                contacts = await client.model(ResPartner).filter(
                    parent_id=company.id
                ).all()
                
                print(f"  Contacts ({len(contacts)}):")
                for contact in contacts:
                    print(f"    - {contact.name}")
                    if contact.email:
                        print(f"      Email: {contact.email}")
            else:
                print("No company with contacts found")
                
    except Exception as e:
        logger.error(f"Error in relationship example: {e}")
        print(f"❌ Error: {e}")


async def main():
    """Run all advanced ORM examples."""
    print("🚀 Zenoo RPC Advanced ORM Examples")
    print("=" * 50)
    
    await advanced_orm_example()
    await relationship_example()
    
    print("\n✨ Advanced ORM examples completed!")
    print("\n📚 Key takeaways:")
    print("  - Type-safe queries with IDE support")
    print("  - Method chaining for fluent API")
    print("  - Complex filtering with field lookups")
    print("  - Performance optimization with field selection")
    print("  - Relationship handling with lazy loading")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")
        print(f"❌ Failed to run examples: {e}")
