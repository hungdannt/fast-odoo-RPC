"""
Basic usage example for Zenoo-RPC.

This example demonstrates the core functionality of Zenoo-RPC,
including connection, authentication, and basic operations.
"""

import asyncio
import logging
from typing import List, Dict, Any

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import AuthenticationError, ConnectionError, ZenooError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_connection_example():
    """Demonstrate basic connection and authentication."""
    print("=== Basic Connection Example ===")
    
    try:
        # Create client with context manager for automatic cleanup
        async with ZenooClient("https://your-odoo-server.com") as client:
            # Check server health
            is_healthy = await client.health_check()
            print(f"Server health: {'OK' if is_healthy else 'FAILED'}")
            
            if not is_healthy:
                print("Server is not reachable. Please check your Odoo installation.")
                return
            
            # Get server version
            version_info = await client.get_server_version()
            print(f"Server version: {version_info.get('server_version', 'Unknown')}")
            
            # List available databases
            databases = await client.list_databases()
            print(f"Available databases: {databases}")
            
            # Authenticate (replace with your credentials)
            try:
                await client.login("your_database", "your_username", "your_password")  # Replace with actual credentials
                print(f"Successfully authenticated as {client.username} on database {client.database}")
                print(f"User ID: {client.uid}")
                
            except AuthenticationError as e:
                print(f"Authentication failed: {e}")
                print("Please check your credentials and database name.")
                return
                
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        print("Please ensure Odoo server is running and accessible.")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def basic_operations_example():
    """Demonstrate basic CRUD operations."""
    print("\n=== Basic Operations Example ===")
    
    try:
        async with ZenooClient("localhost", port=8069) as client:
            # Authenticate
            await client.login("demo", "admin", "admin")  # Replace with actual credentials
            
            # Example 1: Search and read partners
            print("\n1. Searching for partners...")
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "email", "phone", "website"],
                limit=5
            )
            
            print(f"Found {len(partners)} companies:")
            for partner in partners:
                print(f"  - {partner['name']} (ID: {partner['id']})")
                if partner.get('email'):
                    print(f"    Email: {partner['email']}")
                if partner.get('website'):
                    print(f"    Website: {partner['website']}")
            
            # Example 2: Get specific record
            if partners:
                partner_id = partners[0]['id']
                print(f"\n2. Getting detailed info for partner ID {partner_id}...")
                
                partner_detail = await client.execute_kw(
                    "res.partner",
                    "read",
                    [[partner_id]],
                    {"fields": ["name", "email", "phone", "street", "city", "country_id"]}
                )
                
                if partner_detail:
                    partner = partner_detail[0]
                    print(f"Partner details:")
                    print(f"  Name: {partner.get('name')}")
                    print(f"  Email: {partner.get('email')}")
                    print(f"  Phone: {partner.get('phone')}")
                    print(f"  Address: {partner.get('street')}, {partner.get('city')}")
                    if partner.get('country_id'):
                        print(f"  Country: {partner['country_id'][1]}")  # [id, name] format
            
            # Example 3: Count records
            print("\n3. Counting records...")
            partner_count = await client.execute_kw(
                "res.partner",
                "search_count",
                [[("is_company", "=", True)]]
            )
            print(f"Total number of companies: {partner_count}")
            
            user_count = await client.execute_kw(
                "res.users",
                "search_count",
                [[]]
            )
            print(f"Total number of users: {user_count}")
            
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
    except ZenooError as e:
        print(f"Zenoo-RPC error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def advanced_search_example():
    """Demonstrate advanced search capabilities."""
    print("\n=== Advanced Search Example ===")
    
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")  # Replace with actual credentials
            
            # Complex domain search
            print("1. Complex search with multiple conditions...")
            domain = [
                "|",  # OR operator
                ("name", "ilike", "company"),
                ("name", "ilike", "corp"),
                ("is_company", "=", True),
                ("active", "=", True)
            ]
            
            partners = await client.search_read(
                "res.partner",
                domain=domain,
                fields=["name", "email", "is_company", "customer_rank", "supplier_rank"],
                order="name asc",
                limit=10
            )
            
            print(f"Found {len(partners)} partners matching complex criteria:")
            for partner in partners:
                partner_type = []
                if partner.get('customer_rank', 0) > 0:
                    partner_type.append("Customer")
                if partner.get('supplier_rank', 0) > 0:
                    partner_type.append("Vendor")
                if partner.get('is_company'):
                    partner_type.append("Company")
                
                type_str = ", ".join(partner_type) if partner_type else "Contact"
                print(f"  - {partner['name']} ({type_str})")
            
            # Search with pagination
            print("\n2. Paginated search...")
            page_size = 3
            for page in range(2):  # Get first 2 pages
                offset = page * page_size
                page_partners = await client.search_read(
                    "res.partner",
                    domain=[("is_company", "=", True)],
                    fields=["name"],
                    limit=page_size,
                    offset=offset,
                    order="name asc"
                )
                
                print(f"Page {page + 1}:")
                for partner in page_partners:
                    print(f"  - {partner['name']}")
                
                if len(page_partners) < page_size:
                    print("  (Last page)")
                    break
                    
    except Exception as e:
        print(f"Error in advanced search: {e}")


async def error_handling_example():
    """Demonstrate error handling."""
    print("\n=== Error Handling Example ===")
    
    # Example 1: Connection error
    print("1. Testing connection error...")
    try:
        async with ZenooClient("nonexistent-server.com", port=8069) as client:
            await client.health_check()
    except ConnectionError as e:
        print(f"Expected connection error: {e}")
    
    # Example 2: Authentication error
    print("\n2. Testing authentication error...")
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("nonexistent_db", "wrong_user", "wrong_password")
    except AuthenticationError as e:
        print(f"Expected authentication error: {e}")
    except ConnectionError as e:
        print(f"Connection error (server might not be running): {e}")
    
    # Example 3: Invalid method call
    print("\n3. Testing invalid method call...")
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")  # Replace with actual credentials
            
            # Try to call non-existent method
            await client.execute_kw("res.partner", "nonexistent_method", [])
            
    except ZenooError as e:
        print(f"Expected method error: {e}")
    except Exception as e:
        print(f"Other error: {e}")


async def main():
    """Run all examples."""
    print("Zenoo-RPC Basic Usage Examples")
    print("=" * 40)
    
    await basic_connection_example()
    await basic_operations_example()
    await advanced_search_example()
    await error_handling_example()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nNote: Make sure to update the connection parameters")
    print("(host, port, database, username, password) to match your Odoo setup.")


if __name__ == "__main__":
    asyncio.run(main())
