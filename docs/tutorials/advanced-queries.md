# Advanced Queries

This tutorial covers advanced querying techniques in Zenoo RPC, including complex filters, aggregations, subqueries, and performance optimization strategies.

## Prerequisites

- Basic understanding of [Query Builder](../user-guide/queries.md)
- Familiarity with [Relationships](../user-guide/relationships.md)
- Knowledge of Odoo domain syntax

## Complex Filtering

### Using Q Objects for Complex Logic

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.query.filters import Q

async def complex_filtering_example():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Complex OR conditions
        partners = await partner_builder.filter(
            Q(name__ilike="acme%") | Q(name__ilike="corp%") | Q(name__ilike="inc%")
        ).all()
        
        # Nested AND/OR logic
        complex_partners = await partner_builder.filter(
            (Q(is_company=True) & Q(customer_rank__gt=0)) |
            (Q(is_company=False) & Q(parent_id__isnull=False))
        ).all()
        
        # NOT conditions
        non_draft_partners = await partner_builder.filter(
            ~Q(state="draft")
        ).all()
        
        print(f"Found {len(partners)} partners with specific names")
        print(f"Found {len(complex_partners)} partners with complex criteria")
        print(f"Found {len(non_draft_partners)} non-draft partners")

# Run the example
asyncio.run(complex_filtering_example())
```

### Advanced Field Lookups

```python
from datetime import datetime, timedelta

async def advanced_field_lookups():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Date range queries
        recent_partners = await partner_builder.filter(
            create_date__gte=datetime.now() - timedelta(days=30),
            create_date__lt=datetime.now()
        ).all()
        
        # String pattern matching
        email_partners = await partner_builder.filter(
            email__regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            name__istartswith="a",
            phone__contains="+1"
        ).all()
        
        # Numeric comparisons
        valued_customers = await partner_builder.filter(
            customer_rank__gte=5,
            credit_limit__gt=10000.0,
            payment_term_id__isnull=False
        ).all()
        
        # List operations
        specific_countries = await partner_builder.filter(
            country_id__in=[233, 75, 56],  # US, France, Belgium
            state_id__not_in=[1, 2, 3]    # Exclude specific states
        ).all()
        
        print(f"Recent partners: {len(recent_partners)}")
        print(f"Email partners: {len(email_partners)}")
        print(f"Valued customers: {len(valued_customers)}")
        print(f"Specific countries: {len(specific_countries)}")

asyncio.run(advanced_field_lookups())
```

## Relationship Queries

### Deep Relationship Filtering

```python
async def relationship_queries():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Filter by related field values
        us_partners = await partner_builder.filter(
            country_id__name="United States",
            state_id__name__ilike="california%"
        ).all()
        
        # Filter by reverse relationships
        partners_with_orders = await partner_builder.filter(
            sale_order_ids__state__in=["sale", "done"],
            sale_order_ids__amount_total__gte=1000.0
        ).all()
        
        # Multiple relationship levels
        partners_with_invoiced_orders = await partner_builder.filter(
            sale_order_ids__invoice_ids__state="posted",
            sale_order_ids__invoice_ids__amount_total__gt=500.0
        ).all()
        
        print(f"US partners in California: {len(us_partners)}")
        print(f"Partners with significant orders: {len(partners_with_orders)}")
        print(f"Partners with invoiced orders: {len(partners_with_invoiced_orders)}")

asyncio.run(relationship_queries())
```

### Prefetching for Performance

```python
async def optimized_relationship_queries():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Prefetch related data to avoid N+1 queries
        partners = await partner_builder.filter(
            is_company=True
        ).prefetch_related(
            "country_id",
            "state_id", 
            "category_id",
            "child_ids",
            "sale_order_ids"
        ).limit(50).all()
        
        # Now accessing relationships doesn't trigger additional queries
        for partner in partners:
            country = await partner.country_id
            if country:
                print(f"{partner.name} is from {country.name}")
            
            # Access child companies
            children = await partner.child_ids.all()
            if children:
                print(f"  Has {len(children)} subsidiaries")
            
            # Access orders
            orders = await partner.sale_order_ids.filter(
                state__in=["sale", "done"]
            ).all()
            if orders:
                total_amount = sum(order.amount_total for order in orders)
                print(f"  Total orders: ${total_amount:,.2f}")

asyncio.run(optimized_relationship_queries())
```

## Aggregation and Grouping

### Basic Aggregations

```python
from zenoo_rpc.query.aggregates import Count, Sum, Avg, Max, Min

async def aggregation_queries():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Count queries
        total_partners = await partner_builder.count()
        company_count = await partner_builder.filter(is_company=True).count()
        
        # Aggregation with grouping (using raw execute_kw for complex aggregations)
        country_stats = await client.execute_kw(
            "res.partner",
            "read_group",
            [],
            {
                "domain": [("is_company", "=", True)],
                "fields": ["country_id", "customer_rank"],
                "groupby": ["country_id"],
                "lazy": False
            }
        )
        
        print(f"Total partners: {total_partners}")
        print(f"Companies: {company_count}")
        print(f"Country statistics: {len(country_stats)} countries")
        
        for stat in country_stats[:5]:  # Show first 5
            country_name = stat.get("country_id", ["Unknown"])[1] if stat.get("country_id") else "Unknown"
            count = stat.get("country_id_count", 0)
            print(f"  {country_name}: {count} companies")

asyncio.run(aggregation_queries())
```

### Custom Aggregations

```python
async def custom_aggregations():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Sales analysis using raw queries
        sales_stats = await client.execute_kw(
            "sale.order",
            "read_group",
            [],
            {
                "domain": [("state", "in", ["sale", "done"])],
                "fields": ["partner_id", "amount_total", "date_order"],
                "groupby": ["partner_id"],
                "lazy": False
            }
        )
        
        # Process results
        top_customers = []
        for stat in sales_stats:
            if stat.get("partner_id"):
                partner_name = stat["partner_id"][1]
                total_amount = stat.get("amount_total", 0)
                order_count = stat.get("partner_id_count", 0)
                
                top_customers.append({
                    "name": partner_name,
                    "total_amount": total_amount,
                    "order_count": order_count,
                    "avg_order": total_amount / order_count if order_count > 0 else 0
                })
        
        # Sort by total amount
        top_customers.sort(key=lambda x: x["total_amount"], reverse=True)
        
        print("Top 10 Customers by Sales:")
        for i, customer in enumerate(top_customers[:10], 1):
            print(f"{i:2d}. {customer['name']}")
            print(f"    Total: ${customer['total_amount']:,.2f}")
            print(f"    Orders: {customer['order_count']}")
            print(f"    Avg: ${customer['avg_order']:,.2f}")

asyncio.run(custom_aggregations())
```

## Subqueries and Exists

### Subquery Patterns

```python
async def subquery_examples():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Partners with recent orders (subquery pattern)
        recent_order_partner_ids = await client.search(
            "sale.order",
            [("create_date", ">=", datetime.now() - timedelta(days=30))],
            fields=["partner_id"]
        )
        
        # Extract unique partner IDs
        partner_ids = list(set(
            order["partner_id"][0] for order in recent_order_partner_ids 
            if order.get("partner_id")
        ))
        
        # Get partners with recent orders
        partners_with_recent_orders = await partner_builder.filter(
            id__in=partner_ids
        ).all()
        
        # Partners without any orders (NOT EXISTS pattern)
        all_partner_ids = await client.search("res.partner", [], fields=["id"])
        all_ids = [p["id"] for p in all_partner_ids]
        
        partners_with_orders_ids = await client.search(
            "sale.order", [], fields=["partner_id"]
        )
        order_partner_ids = list(set(
            order["partner_id"][0] for order in partners_with_orders_ids
            if order.get("partner_id")
        ))
        
        partners_without_orders_ids = list(set(all_ids) - set(order_partner_ids))
        
        partners_without_orders = await partner_builder.filter(
            id__in=partners_without_orders_ids
        ).all()
        
        print(f"Partners with recent orders: {len(partners_with_recent_orders)}")
        print(f"Partners without any orders: {len(partners_without_orders)}")

asyncio.run(subquery_examples())
```

## Performance Optimization

### Query Optimization Strategies

```python
async def query_optimization():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # 1. Use specific field selection
        lightweight_partners = await partner_builder.filter(
            is_company=True
        ).only("id", "name", "email").all()
        
        # 2. Use appropriate limits
        paginated_partners = await partner_builder.filter(
            is_company=True
        ).limit(100).offset(0).all()
        
        # 3. Use search_read for simple queries
        simple_data = await client.search_read(
            "res.partner",
            domain=[("is_company", "=", True)],
            fields=["name", "email"],
            limit=50
        )
        
        # 4. Batch related data access
        partners = await partner_builder.filter(
            is_company=True
        ).prefetch_related("country_id", "category_id").limit(20).all()
        
        # Access all related data efficiently
        countries = {}
        categories = {}
        
        for partner in partners:
            country = await partner.country_id
            if country and country.id not in countries:
                countries[country.id] = country.name
            
            partner_categories = await partner.category_id.all()
            for category in partner_categories:
                if category.id not in categories:
                    categories[category.id] = category.name
        
        print(f"Lightweight partners: {len(lightweight_partners)}")
        print(f"Paginated partners: {len(paginated_partners)}")
        print(f"Simple data: {len(simple_data)}")
        print(f"Unique countries: {len(countries)}")
        print(f"Unique categories: {len(categories)}")

asyncio.run(query_optimization())
```

### Caching Strategies

```python
async def caching_strategies():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Setup cache manager
        await client.cache_manager.setup_memory_cache(
            name="query_cache",
            max_size=1000,
            default_ttl=300
        )
        
        partner_builder = client.model(ResPartner)
        
        # Cache frequently accessed data
        countries = await partner_builder.filter(
            country_id__isnull=False
        ).only("country_id").cache(
            key="partner_countries",
            ttl=3600  # Cache for 1 hour
        ).all()
        
        # Cache expensive aggregations
        company_count = await partner_builder.filter(
            is_company=True
        ).cache(
            key="company_count",
            ttl=1800  # Cache for 30 minutes
        ).count()
        
        print(f"Cached countries query: {len(countries)} results")
        print(f"Cached company count: {company_count}")

asyncio.run(caching_strategies())
```

## Advanced Patterns

### Dynamic Query Building

```python
async def dynamic_query_building():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partner_builder = client.model(ResPartner)
        
        # Build query dynamically based on conditions
        filters = {}
        
        # Simulate user input
        search_name = "acme"
        search_country = "United States"
        is_company_filter = True
        min_customer_rank = 3
        
        if search_name:
            filters["name__ilike"] = f"%{search_name}%"
        
        if search_country:
            filters["country_id__name"] = search_country
        
        if is_company_filter is not None:
            filters["is_company"] = is_company_filter
        
        if min_customer_rank:
            filters["customer_rank__gte"] = min_customer_rank
        
        # Apply filters dynamically
        query = partner_builder.filter(**filters)
        
        # Add complex conditions if needed
        if search_name and len(search_name) > 3:
            query = query.filter(
                Q(name__ilike=f"%{search_name}%") | 
                Q(email__ilike=f"%{search_name}%")
            )
        
        results = await query.all()
        print(f"Dynamic query results: {len(results)} partners")

asyncio.run(dynamic_query_building())
```

## Best Practices

### 1. Use Appropriate Query Methods

```python
# ✅ Good: Use count() for counting
count = await partner_builder.filter(is_company=True).count()

# ❌ Avoid: Loading all records just to count
partners = await partner_builder.filter(is_company=True).all()
count = len(partners)  # Inefficient
```

### 2. Optimize Field Selection

```python
# ✅ Good: Select only needed fields
partners = await partner_builder.only("id", "name", "email").all()

# ❌ Avoid: Loading all fields when not needed
partners = await partner_builder.all()  # Loads all fields
```

### 3. Use Prefetching for Relationships

```python
# ✅ Good: Prefetch related data
partners = await partner_builder.prefetch_related("country_id").all()
for partner in partners:
    country = await partner.country_id  # No additional query

# ❌ Avoid: N+1 queries
partners = await partner_builder.all()
for partner in partners:
    country = await partner.country_id  # N additional queries
```

### 4. Cache Expensive Queries

```python
# ✅ Good: Cache stable data
countries = await partner_builder.filter(
    country_id__isnull=False
).cache(ttl=3600).all()

# ❌ Avoid: Caching frequently changing data
recent_orders = await order_builder.filter(
    create_date__gte=datetime.now() - timedelta(hours=1)
).cache(ttl=3600).all()  # Data changes too frequently
```

## Next Steps

- Learn about [Performance Optimization](performance-optimization.md) for more performance tips
- Explore [Caching System](../user-guide/caching.md) for advanced caching strategies
- Check [Batch Operations](../user-guide/batch-operations.md) for bulk query processing
