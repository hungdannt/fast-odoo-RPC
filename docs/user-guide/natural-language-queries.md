# 🗣️ Natural Language Queries Guide

Transform plain English into powerful Odoo queries with AI assistance!

## 🎯 Overview

Zenoo RPC's Natural Language Query feature allows you to:
- Write queries in plain English instead of complex domain filters
- Get intelligent model and field suggestions
- Automatically generate optimized Odoo domains
- Understand query logic with AI explanations

## 🚀 Basic Usage

### Simple Queries

```python
import asyncio
from zenoo_rpc import ZenooClient

async def basic_queries():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        # Find all companies
        companies = await client.ai.query("Find all companies")
        
        # Get active users
        users = await client.ai.query("Show me all active users")
        
        # Find customers
        customers = await client.ai.query("Get all customers")
        
        print(f"Found {len(companies)} companies")
        print(f"Found {len(users)} users")
        print(f"Found {len(customers)} customers")

asyncio.run(basic_queries())
```

### Query with Filters

```python
async def filtered_queries():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        # Date-based queries
        recent_partners = await client.ai.query(
            "Find partners created in the last 30 days"
        )
        
        # Location-based queries
        vietnam_companies = await client.ai.query(
            "Find all companies in Vietnam"
        )
        
        # Status-based queries
        active_employees = await client.ai.query(
            "Show me active employees with email addresses"
        )
        
        # Complex conditions
        large_customers = await client.ai.query(
            "Find customers with more than 10 orders and total sales > $10000"
        )
```

## 🎨 Query Patterns

### 1. Entity Queries

```python
# Basic entity finding
await client.ai.query("Find all products")
await client.ai.query("Get all invoices")
await client.ai.query("Show me sales orders")

# With status filters
await client.ai.query("Find active products")
await client.ai.query("Get draft invoices")
await client.ai.query("Show confirmed sales orders")
```

### 2. Relationship Queries

```python
# Related data
await client.ai.query("Find customers with pending invoices")
await client.ai.query("Get products without stock")
await client.ai.query("Show employees in Sales department")

# Complex relationships
await client.ai.query("Find partners who are both customers and suppliers")
await client.ai.query("Get products sold in the last quarter")
```

### 3. Date and Time Queries

```python
# Recent data
await client.ai.query("Find orders created today")
await client.ai.query("Get invoices from this month")
await client.ai.query("Show activities from last week")

# Date ranges
await client.ai.query("Find sales between January and March 2024")
await client.ai.query("Get payments from Q1 2024")
```

### 4. Numerical Queries

```python
# Comparisons
await client.ai.query("Find products with price > $100")
await client.ai.query("Get invoices with amount < $500")
await client.ai.query("Show orders with quantity >= 10")

# Ranges
await client.ai.query("Find products priced between $50 and $200")
await client.ai.query("Get customers with credit limit > $5000")
```

## 🔍 Advanced Features

### Query Explanation

Understand how your natural language gets converted:

```python
async def explain_queries():
    # Get detailed explanation
    explanation = await client.ai.explain_query(
        "Find all companies in Vietnam with revenue > 1M USD"
    )
    
    print(f"Model: {explanation['model']}")
    print(f"Domain: {explanation['domain']}")
    print(f"Fields: {explanation['fields']}")
    print(f"Explanation: {explanation['explanation']}")
    
    # Example output:
    # Model: res.partner
    # Domain: [['is_company', '=', True], ['country_id.name', 'ilike', 'Vietnam']]
    # Fields: ['name', 'email', 'phone', 'country_id']
    # Explanation: The query targets companies (is_company=True) located in Vietnam...
```

### Model Hints

Guide the AI to specific models:

```python
# Without hint - AI chooses best model
users = await client.ai.query("Find all active users")

# With hint - Force specific model
users = await client.ai.query(
    "Find all active users",
    model_hint="res.users"
)

# Multiple model options
partners = await client.ai.query(
    "Find contacts with email",
    model_hint="res.partner"  # Instead of res.users
)
```

### Limiting Results

```python
# Limit number of results
top_customers = await client.ai.query(
    "Find top customers by sales",
    limit=10
)

# Large datasets
all_products = await client.ai.query(
    "Get all products",
    limit=1000  # Prevent memory issues
)
```

## 📊 Query Examples by Domain

### CRM & Sales

```python
# Leads and opportunities
await client.ai.query("Find hot leads from this month")
await client.ai.query("Get opportunities with high probability")
await client.ai.query("Show lost opportunities with reasons")

# Customer management
await client.ai.query("Find VIP customers")
await client.ai.query("Get customers without recent orders")
await client.ai.query("Show customers with overdue payments")
```

### Inventory & Products

```python
# Stock management
await client.ai.query("Find products with low stock")
await client.ai.query("Get products without stock moves")
await client.ai.query("Show products with negative stock")

# Product analysis
await client.ai.query("Find best-selling products")
await client.ai.query("Get products with no sales")
await client.ai.query("Show seasonal products")
```

### Accounting & Finance

```python
# Invoice management
await client.ai.query("Find overdue invoices")
await client.ai.query("Get paid invoices from this quarter")
await client.ai.query("Show draft invoices older than 30 days")

# Payment tracking
await client.ai.query("Find pending payments")
await client.ai.query("Get payments by bank transfer")
await client.ai.query("Show refunded payments")
```

### Human Resources

```python
# Employee management
await client.ai.query("Find employees in IT department")
await client.ai.query("Get employees hired this year")
await client.ai.query("Show employees with pending leave requests")

# Payroll and attendance
await client.ai.query("Find employees with overtime")
await client.ai.query("Get attendance records for today")
await client.ai.query("Show employees with sick leave")
```

## 🎯 Best Practices

### 1. Be Specific

```python
# ❌ Vague
await client.ai.query("Find stuff")

# ✅ Specific
await client.ai.query("Find active products with stock quantity > 0")
```

### 2. Use Business Terms

```python
# ✅ Business language
await client.ai.query("Find customers with overdue invoices")
await client.ai.query("Get products with low stock alerts")
await client.ai.query("Show employees on vacation")
```

### 3. Include Context

```python
# ✅ With context
await client.ai.query("Find sales orders from European customers")
await client.ai.query("Get products sold in retail stores")
await client.ai.query("Show invoices for subscription services")
```

### 4. Handle Edge Cases

```python
async def robust_queries():
    try:
        results = await client.ai.query("Find unicorn customers")
        
        if not results:
            print("No results found - try a different query")
            
    except Exception as e:
        # Get AI help with the error
        diagnosis = await client.ai.diagnose(e)
        print(f"Query failed: {diagnosis['problem']}")
        print(f"Try: {diagnosis['solution']}")
```

## 🔧 Configuration & Tuning

### Confidence Levels

```python
# Check query confidence
explanation = await client.ai.explain_query("Find weird stuff")

if explanation['confidence'] < 0.7:
    print("⚠️ Low confidence query - results may be inaccurate")
    print(f"Confidence: {explanation['confidence']}")
    print("Consider rephrasing your query")
```

### Custom Field Mappings

The AI understands common business terms:

- **"customers"** → `customer_rank > 0`
- **"suppliers"** → `supplier_rank > 0`
- **"companies"** → `is_company = True`
- **"active"** → `active = True`
- **"recent"** → date-based filters
- **"overdue"** → date comparisons

## 🚨 Troubleshooting

### Common Issues

1. **No Results Found**
   ```python
   # Check if query makes sense
   explanation = await client.ai.explain_query("your query")
   print(f"AI interpreted as: {explanation['domain']}")
   ```

2. **Wrong Model Selected**
   ```python
   # Use model hint
   results = await client.ai.query(
       "your query",
       model_hint="correct.model.name"
   )
   ```

3. **Complex Queries Fail**
   ```python
   # Break into simpler parts
   part1 = await client.ai.query("Find all customers")
   part2 = await client.ai.query("Find recent orders")
   # Combine results in Python
   ```

### Performance Tips

```python
# Use limits for large datasets
results = await client.ai.query("Find all records", limit=100)

# Cache frequent queries
from functools import lru_cache

@lru_cache(maxsize=128)
async def cached_query(query_text):
    return await client.ai.query(query_text)
```

## 🎯 Next Steps

- **[Error Diagnosis Guide](./error-diagnosis.md)** - Handle query errors intelligently
- **[Model Generation Guide](./model-generation.md)** - Generate typed models
- **[Performance Optimization](./performance-optimization.md)** - Optimize query performance
- **[Advanced AI Features](./advanced-ai-features.md)** - Explore advanced capabilities

---

**💡 Pro Tip**: Start with simple queries and gradually add complexity. The AI learns from context and becomes more accurate with specific business terminology!
