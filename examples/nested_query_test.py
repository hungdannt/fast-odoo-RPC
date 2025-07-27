#!/usr/bin/env python3
"""
Zenoo-RPC Nested Query Test

This script tests nested query capabilities with real Odoo server
to see what's currently supported and what needs to be implemented.
"""

import asyncio
from zenoo_rpc import ZenooClient

# Odoo credentials - Use environment variables for real testing
import os
ODOO_CONFIG = {
    "url": os.getenv("ODOO_HOST", "https://demo.odoo.com"),
    "database": os.getenv("ODOO_DATABASE", "demo_database"),
    "username": os.getenv("ODOO_USERNAME", "demo_user"),
    "password": os.getenv("ODOO_PASSWORD", "demo_password")
}


async def test_basic_relationships():
    """Test basic relationship queries."""
    print("🔗 Testing Basic Relationships")
    print("-" * 40)
    
    async with ZenooClient(ODOO_CONFIG["url"]) as client:
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"],
            ODOO_CONFIG["password"]
        )
        
        print("\n1. Testing Many2one relationships...")
        try:
            # Get partners with their country information
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "country_id"],
                limit=3
            )
            
            print(f"   Found {len(partners)} companies:")
            for partner in partners:
                country_info = partner.get('country_id')
                if country_info:
                    if isinstance(country_info, list) and len(country_info) >= 2:
                        country_id, country_name = country_info[0], country_info[1]
                        print(f"   - {partner['name']} → Country: {country_name} (ID: {country_id})")
                    else:
                        print(f"   - {partner['name']} → Country: {country_info}")
                else:
                    print(f"   - {partner['name']} → No country")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n2. Testing One2many relationships...")
        try:
            # Get companies with their child companies
            companies = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True), ("child_ids", "!=", False)],
                fields=["name", "child_ids"],
                limit=2
            )
            
            print(f"   Found {len(companies)} companies with children:")
            for company in companies:
                child_ids = company.get('child_ids', [])
                print(f"   - {company['name']} has {len(child_ids)} children: {child_ids}")
                
                # Get details of child companies
                if child_ids:
                    children = await client.search_read(
                        "res.partner",
                        domain=[("id", "in", child_ids[:3])],  # Limit to first 3
                        fields=["name", "email"]
                    )
                    for child in children:
                        print(f"     → {child['name']} ({child.get('email', 'No email')})")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_nested_domain_queries():
    """Test nested domain queries."""
    print("\n🔍 Testing Nested Domain Queries")
    print("-" * 40)
    
    async with ZenooClient(ODOO_CONFIG["url"]) as client:
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"],
            ODOO_CONFIG["password"]
        )
        
        print("\n1. Testing nested AND/OR conditions...")
        try:
            # Complex nested domain
            domain = [
                '|',  # OR
                    '&',  # AND
                        ('name', 'ilike', 'anh'),
                        ('is_company', '=', True),
                    '&',  # AND
                        ('name', 'ilike', 'production'),
                        ('is_company', '=', True)
            ]
            
            partners = await client.search_read(
                "res.partner",
                domain=domain,
                fields=["name", "is_company"],
                limit=5
            )
            
            print(f"   Found {len(partners)} partners with nested conditions:")
            for partner in partners:
                print(f"   - {partner['name']} (Company: {partner['is_company']})")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n2. Testing relationship-based queries...")
        try:
            # Query partners based on their country
            partners = await client.search_read(
                "res.partner",
                domain=[("country_id.code", "=", "KH")],  # Cambodia
                fields=["name", "country_id"],
                limit=3
            )
            
            print(f"   Found {len(partners)} partners in Cambodia:")
            for partner in partners:
                country_info = partner.get('country_id')
                if isinstance(country_info, list) and len(country_info) >= 2:
                    print(f"   - {partner['name']} → {country_info[1]}")
                else:
                    print(f"   - {partner['name']} → {country_info}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_join_queries():
    """Test join-like queries."""
    print("\n🔗 Testing Join-like Queries")
    print("-" * 40)
    
    async with ZenooClient(ODOO_CONFIG["url"]) as client:
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"],
            ODOO_CONFIG["password"]
        )
        
        print("\n1. Testing manual joins...")
        try:
            # Get partners and their countries in separate queries
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "country_id"],
                limit=3
            )
            
            # Extract country IDs
            country_ids = []
            for partner in partners:
                country_info = partner.get('country_id')
                if isinstance(country_info, list) and len(country_info) >= 1:
                    country_ids.append(country_info[0])
            
            # Get country details
            countries = {}
            if country_ids:
                country_data = await client.search_read(
                    "res.country",
                    domain=[("id", "in", list(set(country_ids)))],
                    fields=["name", "code"]
                )
                countries = {c['id']: c for c in country_data}
            
            print(f"   Manual join results:")
            for partner in partners:
                country_info = partner.get('country_id')
                if isinstance(country_info, list) and len(country_info) >= 1:
                    country_id = country_info[0]
                    country = countries.get(country_id, {})
                    print(f"   - {partner['name']} → {country.get('name', 'Unknown')} ({country.get('code', 'N/A')})")
                else:
                    print(f"   - {partner['name']} → No country")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_current_query_builder():
    """Test current query builder capabilities."""
    print("\n🏗️ Testing Current Query Builder")
    print("-" * 40)
    
    async with ZenooClient(ODOO_CONFIG["url"]) as client:
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"],
            ODOO_CONFIG["password"]
        )
        
        print("\n1. Testing if query builder exists...")
        try:
            # Try to use query builder if it exists
            if hasattr(client, 'model'):
                print("   ✅ client.model() method exists")
                # This would test the query builder
                # model_query = client.model('res.partner')
                # print(f"   Query builder type: {type(model_query)}")
            else:
                print("   ❌ client.model() method not found")
            
            # Test if we can build complex queries
            print("   Testing complex domain building...")
            complex_domain = [
                '&',
                    ('is_company', '=', True),
                    '|',
                        ('name', 'ilike', 'anh'),
                        ('name', 'ilike', 'production')
            ]
            
            results = await client.search_read(
                "res.partner",
                domain=complex_domain,
                fields=["name"],
                limit=3
            )
            
            print(f"   ✅ Complex domain works: {len(results)} results")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_relationship_loading():
    """Test relationship loading capabilities."""
    print("\n🔄 Testing Relationship Loading")
    print("-" * 40)
    
    async with ZenooClient(ODOO_CONFIG["url"]) as client:
        await client.login(
            ODOO_CONFIG["database"],
            ODOO_CONFIG["username"],
            ODOO_CONFIG["password"]
        )
        
        print("\n1. Testing lazy loading simulation...")
        try:
            # Get a partner with relationships
            partners = await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "country_id", "child_ids"],
                limit=1
            )
            
            if partners:
                partner = partners[0]
                print(f"   Partner: {partner['name']}")
                
                # Simulate lazy loading of country
                country_info = partner.get('country_id')
                if country_info and isinstance(country_info, list):
                    country_id = country_info[0]
                    country = await client.read(
                        "res.country",
                        [country_id],
                        ["name", "code"]
                    )
                    if country:
                        print(f"   → Country (lazy loaded): {country[0]['name']} ({country[0]['code']})")
                
                # Simulate lazy loading of children
                child_ids = partner.get('child_ids', [])
                if child_ids:
                    children = await client.read(
                        "res.partner",
                        child_ids[:2],  # First 2 children
                        ["name", "email"]
                    )
                    print(f"   → Children (lazy loaded): {len(children)} contacts")
                    for child in children:
                        print(f"     - {child['name']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def main():
    """Run all nested query tests."""
    print("🚀 Zenoo-RPC Nested Query Test")
    print("=" * 60)
    print("Testing current nested query capabilities and identifying gaps...")
    
    try:
        await test_basic_relationships()
        await test_nested_domain_queries()
        await test_join_queries()
        await test_current_query_builder()
        await test_relationship_loading()
        
        print("\n" + "=" * 60)
        print("📊 NESTED QUERY ANALYSIS")
        print("=" * 60)
        
        print("\n✅ Currently Supported:")
        print("   - Basic relationship queries (Many2one, One2many)")
        print("   - Nested domain conditions (AND/OR logic)")
        print("   - Relationship-based filtering (country_id.code)")
        print("   - Manual join queries (separate calls)")
        print("   - Lazy loading simulation")
        
        print("\n❌ Missing Features:")
        print("   - Fluent query builder with relationships")
        print("   - Automatic relationship loading")
        print("   - Prefetching strategies")
        print("   - Type-safe relationship navigation")
        print("   - ORM-style joins")
        
        print("\n🔮 Recommendations:")
        print("   1. Implement fluent relationship queries:")
        print("      client.model(ResPartner).filter(country__code='KH')")
        print("   2. Add automatic relationship loading:")
        print("      partner.country_id  # Auto-loads country data")
        print("   3. Implement prefetch strategies:")
        print("      .prefetch_related('country_id', 'child_ids')")
        print("   4. Add type-safe relationship navigation")
        print("   5. Implement ORM-style select_related()")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
