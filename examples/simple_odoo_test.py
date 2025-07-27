#!/usr/bin/env python3
"""
Simple Zenoo-RPC test with real Odoo server.
"""

import asyncio
import sys
from zenoo_rpc import ZenooClient

# Odoo credentials - Use environment variables for real testing
import os
ODOO_CONFIG = {
    "url": os.getenv("ODOO_HOST", "https://demo.odoo.com"),
    "database": os.getenv("ODOO_DATABASE", "demo_database"),
    "username": os.getenv("ODOO_USERNAME", "demo_user"),
    "password": os.getenv("ODOO_PASSWORD", "demo_password")
}


async def main():
    """Simple test."""
    print("🚀 Simple Zenoo-RPC Test")
    print(f"🌐 URL: {ODOO_CONFIG['url']}")
    print(f"🗄️ Database: {ODOO_CONFIG['database']}")
    print(f"👤 User: {ODOO_CONFIG['username']}")
    
    try:
        async with ZenooClient(ODOO_CONFIG["url"]) as client:
            print("\n1. Testing authentication...")
            await client.login(
                ODOO_CONFIG["database"],
                ODOO_CONFIG["username"],
                ODOO_CONFIG["password"]
            )
            print(f"✅ Authentication successful! User ID: {client.uid}")
            
            print("\n2. Testing user access...")
            try:
                # Test user access first
                user_info = await client.execute_kw(
                    "res.users",
                    "read",
                    [[client.uid]],
                    {"fields": ["name", "login", "groups_id"]}
                )
                print(f"✅ User info: {user_info}")

            except Exception as e:
                print(f"❌ User access failed: {e}")
                import traceback
                traceback.print_exc()

            print("\n3. Testing basic RPC call...")
            try:
                # Test simple RPC call with res.users first (should have access)
                result = await client.execute_kw(
                    "res.users",
                    "search",
                    [[]],
                    {"limit": 1}
                )
                print(f"✅ Users search successful! Found IDs: {result}")

                # Now try res.partner
                result = await client.execute_kw(
                    "res.partner",
                    "search",
                    [[("is_company", "=", True)]],
                    {"limit": 1}
                )
                print(f"✅ Partner search successful! Found IDs: {result}")

                if result:
                    # Test read
                    partner_data = await client.execute_kw(
                        "res.partner",
                        "read",
                        [result],
                        {"fields": ["name", "email"]}
                    )
                    print(f"✅ Partner read successful! Data: {partner_data}")

            except Exception as e:
                print(f"❌ RPC call failed: {e}")
                print(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
            
            print("\n4. Testing search_read...")
            try:
                partners = await client.search_read(
                    "res.partner",
                    domain=[("is_company", "=", True)],
                    fields=["name", "email"],
                    limit=1
                )
                print(f"✅ search_read successful! Data: {partners}")

            except Exception as e:
                print(f"❌ search_read failed: {e}")
                print(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
            
            print("\n✅ Test completed!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


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
