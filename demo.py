#!/usr/bin/env python3
"""
OdooFlow Demo Script

This script demonstrates the key features and improvements of OdooFlow
compared to the traditional odoorpc library.
"""

import asyncio
import time
from typing import List, Dict, Any

# Import OdooFlow
from odooflow import OdooFlowClient
from odooflow.exceptions import (
    OdooFlowError,
    ConnectionError,
    AuthenticationError,
    ValidationError,
    AccessError,
)


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


async def demo_connection_and_health():
    """Demo connection and health check features."""
    print_section("Connection and Health Check")
    
    # Demo 1: Health check without authentication
    print("1. Testing server health check...")
    try:
        async with OdooFlowClient("localhost", port=8069) as client:
            is_healthy = await client.health_check()
            print(f"   Server health: {'✅ OK' if is_healthy else '❌ FAILED'}")
            
            if is_healthy:
                # Get server version
                version_info = await client.get_server_version()
                server_version = version_info.get('server_version', 'Unknown')
                print(f"   Server version: {server_version}")
                
                # List databases
                databases = await client.list_databases()
                print(f"   Available databases: {databases}")
            else:
                print("   ⚠️  Server is not reachable")
                
    except ConnectionError as e:
        print(f"   ❌ Connection failed: {e}")
        print("   💡 Make sure Odoo server is running on localhost:8069")


async def demo_error_handling():
    """Demo structured error handling."""
    print_section("Structured Error Handling")
    
    # Demo 1: Connection error
    print("1. Testing connection error handling...")
    try:
        async with OdooFlowClient("nonexistent-server.local", port=8069) as client:
            await client.health_check()
    except ConnectionError as e:
        print(f"   ✅ Caught ConnectionError: {type(e).__name__}")
        print(f"   📝 Message: {e.message}")
    
    # Demo 2: Authentication error
    print("\n2. Testing authentication error handling...")
    try:
        async with OdooFlowClient("localhost", port=8069) as client:
            await client.login("fake_db", "fake_user", "fake_password")
    except AuthenticationError as e:
        print(f"   ✅ Caught AuthenticationError: {type(e).__name__}")
        print(f"   📝 Message: {e.message}")
    except ConnectionError as e:
        print(f"   ⚠️  Server not available: {e.message}")
    
    # Demo 3: Generic error handling
    print("\n3. Generic OdooFlow error handling...")
    try:
        # This will cause a connection error
        async with OdooFlowClient("localhost", port=9999) as client:
            await client.health_check()
    except OdooFlowError as e:
        print(f"   ✅ Caught OdooFlowError: {type(e).__name__}")
        print(f"   📝 Message: {e.message}")
        if hasattr(e, 'context') and e.context:
            print(f"   🔍 Context: {e.context}")


async def demo_async_features():
    """Demo async features and performance."""
    print_section("Async Features and Performance")
    
    print("1. Demonstrating async context manager...")
    start_time = time.time()
    
    try:
        async with OdooFlowClient("localhost", port=8069) as client:
            print("   ✅ Client created with async context manager")
            
            # Multiple concurrent health checks
            print("\n2. Testing concurrent operations...")
            tasks = []
            for i in range(3):
                task = asyncio.create_task(client.health_check())
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"   Task {i+1}: ❌ {type(result).__name__}")
                else:
                    print(f"   Task {i+1}: {'✅ Healthy' if result else '❌ Unhealthy'}")
        
        elapsed = time.time() - start_time
        print(f"\n   ⏱️  Total time: {elapsed:.2f} seconds")
        print("   ✅ Resources cleaned up automatically")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def demo_api_comparison():
    """Demo API improvements over odoorpc."""
    print_section("API Improvements over odoorpc")
    
    print("🔄 OdooFlow vs odoorpc API Comparison:")
    print()
    
    # Show the old way (odoorpc)
    print("📜 Old way (odoorpc):")
    print("   import odoorpc")
    print("   odoo = odoorpc.ODOO('localhost', port=8069)")
    print("   odoo.login('db_name', 'admin', 'password')")
    print("   Partner = odoo.env['res.partner']")
    print("   partner_ids = Partner.search([('is_company', '=', True)], limit=10)")
    print("   partners = Partner.browse(partner_ids)  # Second RPC call!")
    print("   for partner in partners:")
    print("       print(partner.name)  # Potential N+1 queries")
    
    print("\n✨ New way (OdooFlow):")
    print("   from odooflow import OdooFlowClient")
    print("   async with OdooFlowClient('localhost', port=8069) as client:")
    print("       await client.login('db_name', 'admin', 'password')")
    print("       # Single RPC call with type safety!")
    print("       partners = await client.search_read(")
    print("           'res.partner',")
    print("           domain=[('is_company', '=', True)],")
    print("           fields=['name', 'email'],")
    print("           limit=10")
    print("       )")
    print("       for partner in partners:")
    print("           print(partner['name'])  # No additional queries")
    
    print("\n🎯 Key Improvements:")
    print("   ✅ Async/await support for modern Python")
    print("   ✅ Single RPC call instead of search + browse")
    print("   ✅ Structured exception handling")
    print("   ✅ Type safety with Pydantic (coming in Phase 2)")
    print("   ✅ Intelligent caching (coming in Phase 3)")
    print("   ✅ Transaction management (coming in Phase 3)")


async def demo_real_world_usage():
    """Demo real-world usage patterns."""
    print_section("Real-world Usage Patterns")
    
    print("🏢 Example: Customer Data Export")
    print()
    
    # Show a realistic example
    example_code = '''
async def export_customer_data():
    """Export customer data with error handling and performance optimization."""
    async with OdooFlowClient("localhost", port=8069) as client:
        try:
            # Authenticate
            await client.login("production_db", "api_user", "secure_password")
            
            # Efficient single-call data retrieval
            customers = await client.search_read(
                "res.partner",
                domain=[
                    ("is_company", "=", True),
                    ("customer_rank", ">", 0),
                    ("active", "=", True)
                ],
                fields=["name", "email", "phone", "country_id", "create_date"],
                order="create_date desc",
                limit=1000
            )
            
            # Process data
            processed_data = []
            for customer in customers:
                processed_data.append({
                    "name": customer["name"],
                    "email": customer.get("email", ""),
                    "phone": customer.get("phone", ""),
                    "country": customer["country_id"][1] if customer.get("country_id") else "",
                    "created": customer["create_date"]
                })
            
            return processed_data
            
        except AuthenticationError:
            logger.error("Authentication failed - check credentials")
            raise
        except ValidationError as e:
            logger.error(f"Data validation error: {e.message}")
            raise
        except OdooFlowError as e:
            logger.error(f"Odoo operation failed: {e.message}")
            raise
'''
    
    print(example_code)
    
    print("🎯 Benefits of this approach:")
    print("   ✅ Single RPC call for all data")
    print("   ✅ Structured error handling")
    print("   ✅ Automatic resource cleanup")
    print("   ✅ Type-safe operations")
    print("   ✅ Clear, readable code")


async def main():
    """Run all demos."""
    print_header("🚀 OdooFlow Demo - Modern Odoo RPC for Python")
    
    print("Welcome to OdooFlow! This demo showcases the key features and")
    print("improvements over the traditional odoorpc library.")
    print()
    print("📋 Demo Agenda:")
    print("   1. Connection and Health Check")
    print("   2. Structured Error Handling")
    print("   3. Async Features and Performance")
    print("   4. API Improvements over odoorpc")
    print("   5. Real-world Usage Patterns")
    
    # Run all demos
    await demo_connection_and_health()
    await demo_error_handling()
    await demo_async_features()
    await demo_api_comparison()
    await demo_real_world_usage()
    
    print_header("🎉 Demo Complete!")
    print()
    print("🔗 Next Steps:")
    print("   📖 Read the documentation: docs/")
    print("   🧪 Run the examples: python examples/basic_usage.py")
    print("   🤝 Contribute: See CONTRIBUTING.md")
    print("   ⭐ Star the project on GitHub!")
    print()
    print("Thank you for trying OdooFlow! 🐍✨")


if __name__ == "__main__":
    asyncio.run(main())
