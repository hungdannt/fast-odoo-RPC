#!/usr/bin/env python3
"""
Zenoo-RPC Phase 2 Demo - Pydantic Models and Query Builder

This demo showcases the new features in Phase 2:
- Type-safe Pydantic models
- Fluent query builder with method chaining
- Django-like Q objects and field lookups
- Lazy loading and relationship handling
"""

import asyncio
from typing import List

from zenoo_rpc import ZenooClient, Q, Field
from zenoo_rpc.models.common import ResPartner, ResCountry, ProductProduct
from zenoo_rpc.exceptions import Zenoo-RPCError


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


async def demo_type_safe_models():
    """Demo type-safe Pydantic models."""
    print_section("Type-Safe Pydantic Models")
    
    print("1. Creating model instances with type safety...")
    
    # Create a partner with type safety
    partner = ResPartner(
        id=1,
        name="ACME Corporation",
        is_company=True,
        email="contact@acme.com",
        phone="+1-555-0123",
        customer_rank=1,
        supplier_rank=0
    )
    
    print(f"   Partner: {partner}")
    print(f"   Name: {partner.name} (type: {type(partner.name).__name__})")
    print(f"   Is Company: {partner.is_company} (type: {type(partner.is_company).__name__})")
    print(f"   Email: {partner.email} (type: {type(partner.email).__name__})")
    
    # Demonstrate computed properties
    print(f"\n2. Computed properties...")
    print(f"   Is Customer: {partner.is_customer}")
    print(f"   Is Vendor: {partner.is_vendor}")
    
    # Create address and test full_address property
    partner.street = "123 Business Ave"
    partner.street2 = "Suite 100"
    partner.city = "Tech City"
    partner.zip = "12345"
    
    print(f"   Full Address: {partner.full_address}")
    
    # Demonstrate field validation
    print(f"\n3. Field validation...")
    try:
        # This would raise a validation error in real usage
        print("   ✅ Pydantic validates field types automatically")
        print("   ✅ IDE provides autocompletion and type checking")
    except Exception as e:
        print(f"   ❌ Validation error: {e}")
    
    # Show model metadata
    print(f"\n4. Model metadata...")
    print(f"   Odoo model name: {partner.get_odoo_name()}")
    print(f"   Loaded fields: {partner.get_loaded_fields()}")
    print(f"   Field loaded (name): {partner.is_field_loaded('name')}")
    print(f"   Field loaded (description): {partner.is_field_loaded('description')}")


async def demo_fluent_query_builder():
    """Demo fluent query builder interface."""
    print_section("Fluent Query Builder")
    
    print("🔗 Zenoo-RPC vs odoorpc Query Comparison:")
    print()
    
    # Show the old way (odoorpc)
    print("📜 Old way (odoorpc):")
    print("   Partner = odoo.env['res.partner']")
    print("   partner_ids = Partner.search([")
    print("       ('is_company', '=', True),")
    print("       ('name', 'ilike', 'acme%'),")
    print("       ('customer_rank', '>', 0)")
    print("   ], limit=10, order='name')")
    print("   partners = Partner.browse(partner_ids)  # Second RPC call!")
    
    print("\n✨ New way (Zenoo-RPC):")
    print("   # Type-safe, fluent interface")
    print("   partners = await client.model(ResPartner).filter(")
    print("       is_company=True,")
    print("       name__ilike='acme%',")
    print("       customer_rank__gt=0")
    print("   ).order_by('name').limit(10).all()  # Single RPC call!")
    
    print("\n🎯 Query Builder Features:")
    
    # Simulate query building (without actual client)
    print("\n1. Method chaining...")
    print("   query = client.model(ResPartner)")
    print("   query = query.filter(is_company=True)")
    print("   query = query.filter(name__ilike='acme%')")
    print("   query = query.order_by('name')")
    print("   query = query.limit(10)")
    print("   # Query is built but not executed yet (lazy evaluation)")
    
    print("\n2. Django-style field lookups...")
    lookups = [
        "name__ilike='company%'",
        "create_date__gte='2024-01-01'",
        "email__contains='@acme.com'",
        "phone__startswith='+1'",
        "customer_rank__in=[1, 2, 3]",
        "description__isnull=True"
    ]
    
    for lookup in lookups:
        print(f"   ✅ {lookup}")
    
    print("\n3. Q objects for complex queries...")
    print("   # Complex OR/AND logic")
    print("   q = (Q(name__ilike='acme%') | Q(name__ilike='corp%')) & Q(is_company=True)")
    print("   partners = await client.model(ResPartner).filter(q).all()")
    
    print("\n4. Field expressions...")
    print("   # Type-safe field references")
    print("   name_field = Field('name')")
    print("   age_field = Field('age')")
    print("   query = name_field.ilike('john%') & (age_field > 18)")


async def demo_q_objects():
    """Demo Q objects for complex queries."""
    print_section("Q Objects and Complex Queries")
    
    print("1. Basic Q objects...")
    
    # Create Q objects
    q1 = Q(name="ACME Corp")
    q2 = Q(is_company=True)
    
    print(f"   q1 = Q(name='ACME Corp')")
    print(f"   q2 = Q(is_company=True)")
    print(f"   q1 domain: {q1.to_domain()}")
    print(f"   q2 domain: {q2.to_domain()}")
    
    print("\n2. Combining Q objects...")
    
    # AND combination
    and_q = q1 & q2
    print(f"   AND: q1 & q2")
    print(f"   Domain: {and_q.to_domain()}")
    
    # OR combination
    q3 = Q(name="Tech Corp")
    or_q = q1 | q3
    print(f"   OR: Q(name='ACME Corp') | Q(name='Tech Corp')")
    print(f"   Domain: {or_q.to_domain()}")
    
    # NOT combination
    not_q = ~q1
    print(f"   NOT: ~Q(name='ACME Corp')")
    print(f"   Domain: {not_q.to_domain()}")
    
    print("\n3. Complex combinations...")
    
    # Complex query: (name contains 'acme' OR name contains 'corp') AND is_company=True
    complex_q = (Q(name__icontains='acme') | Q(name__icontains='corp')) & Q(is_company=True)
    print(f"   Complex: (name contains 'acme' OR 'corp') AND is_company=True")
    print(f"   Domain: {complex_q.to_domain()}")
    
    print("\n4. Field lookups in Q objects...")
    
    lookups_q = Q(
        name__ilike='company%',
        create_date__gte='2024-01-01',
        customer_rank__gt=0
    )
    print(f"   Multiple lookups in single Q:")
    print(f"   Domain: {lookups_q.to_domain()}")


async def demo_field_expressions():
    """Demo Field expressions for type-safe queries."""
    print_section("Field Expressions")
    
    print("1. Creating field references...")
    
    name_field = Field('name')
    email_field = Field('email')
    age_field = Field('age')
    
    print(f"   name_field = Field('name')")
    print(f"   email_field = Field('email')")
    print(f"   age_field = Field('age')")
    
    print("\n2. Comparison operations...")
    
    # Equality
    eq_expr = name_field == "John Doe"
    print(f"   name_field == 'John Doe'")
    print(f"   Domain: {eq_expr.to_domain()}")
    
    # Greater than
    gt_expr = age_field > 18
    print(f"   age_field > 18")
    print(f"   Domain: {gt_expr.to_domain()}")
    
    # Like operations
    like_expr = name_field.ilike("john%")
    print(f"   name_field.ilike('john%')")
    print(f"   Domain: {like_expr.to_domain()}")
    
    print("\n3. String operations...")
    
    # Contains
    contains_expr = email_field.contains("@acme.com")
    print(f"   email_field.contains('@acme.com')")
    print(f"   Domain: {contains_expr.to_domain()}")
    
    # Starts with
    starts_expr = name_field.startswith("Dr.")
    print(f"   name_field.startswith('Dr.')")
    print(f"   Domain: {starts_expr.to_domain()}")
    
    # Ends with
    ends_expr = email_field.endswith(".com")
    print(f"   email_field.endswith('.com')")
    print(f"   Domain: {ends_expr.to_domain()}")
    
    print("\n4. Combining field expressions...")
    
    # Complex combination
    complex_expr = (name_field.ilike("john%") & (age_field > 18)) | email_field.contains("@company.com")
    print(f"   Complex: (name like 'john%' AND age > 18) OR email contains '@company.com'")
    print(f"   Domain: {complex_expr.to_domain()}")


async def demo_lazy_loading():
    """Demo lazy loading concepts."""
    print_section("Lazy Loading and Relationships")
    
    print("1. Lazy evaluation concept...")
    print("   # Query is built but not executed")
    print("   partners_query = client.model(ResPartner).filter(is_company=True)")
    print("   print(partners_query)  # Shows <QuerySet [unevaluated ResPartner query]>")
    print()
    print("   # Execution happens when data is needed")
    print("   partners = await partners_query.all()  # NOW the RPC call is made")
    print("   print(partners_query)  # Shows <QuerySet [X ResPartner objects]>")
    
    print("\n2. Relationship lazy loading...")
    print("   # Partner with country relationship")
    print("   partner = await client.model(ResPartner).get(id=1)")
    print("   # Country is not loaded yet - it's a LazyRelationship")
    print("   country = await partner.country_id  # Loads on demand")
    print("   print(country.name)  # Now we have the country data")
    
    print("\n3. Collection lazy loading...")
    print("   # Company with child contacts")
    print("   company = await client.model(ResPartner).get(id=1)")
    print("   # Child contacts are lazy-loaded")
    print("   async for contact in company.child_ids:")
    print("       print(contact.name)  # Loads contacts on iteration")
    
    print("\n4. Prefetching optimization...")
    print("   # Efficient prefetching to avoid N+1 queries")
    print("   partners = await client.model(ResPartner).filter(")
    print("       is_company=True")
    print("   ).prefetch_related('country_id', 'child_ids').all()")
    print("   # All relationships loaded in batch queries")


async def demo_performance_comparison():
    """Demo performance improvements."""
    print_section("Performance Improvements")
    
    print("🚀 Zenoo-RPC Performance Benefits:")
    print()
    
    print("1. Single RPC calls...")
    print("   odoorpc: search() + browse() = 2 RPC calls")
    print("   Zenoo-RPC: search_read() = 1 RPC call")
    print("   ✅ 50% fewer RPC calls for basic queries")
    
    print("\n2. Efficient relationship loading...")
    print("   odoorpc: N+1 queries for relationships")
    print("   Zenoo-RPC: Batch loading with prefetch_related()")
    print("   ✅ Dramatically reduced query count")
    
    print("\n3. Connection pooling...")
    print("   odoorpc: Basic HTTP connections")
    print("   Zenoo-RPC: HTTP/2 + connection pooling")
    print("   ✅ Better network utilization")
    
    print("\n4. Lazy evaluation...")
    print("   odoorpc: Immediate execution")
    print("   Zenoo-RPC: Build complex queries, execute once")
    print("   ✅ Optimized query execution")
    
    print("\n5. Type safety benefits...")
    print("   odoorpc: Runtime errors, no IDE support")
    print("   Zenoo-RPC: Compile-time checks, full IDE support")
    print("   ✅ Fewer bugs, better developer experience")


async def main():
    """Run all Phase 2 demos."""
    print_header("🚀 Zenoo-RPC Phase 2 Demo - Pydantic Models & Query Builder")
    
    print("Welcome to Zenoo-RPC Phase 2! This demo showcases the new features:")
    print("✨ Type-safe Pydantic models with field validation")
    print("🔗 Fluent query builder with method chaining")
    print("🎯 Django-like Q objects and field lookups")
    print("⚡ Lazy loading and performance optimizations")
    print()
    print("📋 Demo Agenda:")
    print("   1. Type-Safe Pydantic Models")
    print("   2. Fluent Query Builder")
    print("   3. Q Objects and Complex Queries")
    print("   4. Field Expressions")
    print("   5. Lazy Loading Concepts")
    print("   6. Performance Improvements")
    
    # Run all demos
    await demo_type_safe_models()
    await demo_fluent_query_builder()
    await demo_q_objects()
    await demo_field_expressions()
    await demo_lazy_loading()
    await demo_performance_comparison()
    
    print_header("🎉 Phase 2 Demo Complete!")
    print()
    print("🔗 What's Next:")
    print("   📖 Check out the updated documentation")
    print("   🧪 Run the comprehensive test suite")
    print("   🚀 Try building your own queries with type safety")
    print("   ⭐ Phase 3 coming soon: Transactions, Caching & Batch Operations!")
    print()
    print("Thank you for exploring Zenoo-RPC Phase 2! 🐍✨")


if __name__ == "__main__":
    asyncio.run(main())
