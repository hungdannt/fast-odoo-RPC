# Basic CRUD Operations Tutorial

This tutorial covers the fundamental Create, Read, Update, and Delete operations using Zenoo RPC. You'll learn how to perform these operations efficiently with type safety and modern Python patterns.

## Prerequisites

- Zenoo RPC installed (`pip install zenoo-rpc`)
- Access to an Odoo server
- Basic understanding of async/await in Python

## Setup

First, let's set up our basic client connection:

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import ValidationError, AccessError

async def main():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Your CRUD operations here
        await crud_examples(client)

async def crud_examples(client: ZenooClient):
    """Examples of CRUD operations"""
    pass  # We'll fill this in

if __name__ == "__main__":
    asyncio.run(main())
```

## Create Operations

### Creating Single Records

```python
async def create_single_record(client: ZenooClient):
    """Create a single partner record"""
    
    # Create a new company
    new_company = await client.model(ResPartner).create({
        "name": "Acme Corporation",
        "is_company": True,
        "email": "contact@acme.com",
        "phone": "+1-555-0123",
        "website": "https://acme.com",
        "street": "123 Business Ave",
        "city": "Business City",
        "zip": "12345",
        "comment": "Created via Zenoo RPC"
    })
    
    print(f"Created company: {new_company.name} (ID: {new_company.id})")
    return new_company

# Usage
company = await create_single_record(client)
```

### Creating Multiple Records (Bulk Create)

```python
async def create_multiple_records(client: ZenooClient):
    """Create multiple records efficiently"""
    
    companies_data = [
        {
            "name": "Tech Solutions Inc",
            "is_company": True,
            "email": "info@techsolutions.com",
            "phone": "+1-555-0124"
        },
        {
            "name": "Global Services Ltd",
            "is_company": True,
            "email": "contact@globalservices.com",
            "phone": "+1-555-0125"
        },
        {
            "name": "Innovation Corp",
            "is_company": True,
            "email": "hello@innovation.com",
            "phone": "+1-555-0126"
        }
    ]
    
    # Bulk create - much more efficient than individual creates
    companies = await client.model(ResPartner).bulk_create(companies_data)
    
    print(f"Created {len(companies)} companies:")
    for company in companies:
        print(f"  - {company.name} (ID: {company.id})")
    
    return companies

# Usage
companies = await create_multiple_records(client)
```

### Creating with Relationships

```python
async def create_with_relationships(client: ZenooClient):
    """Create records with relationship fields"""
    
    # First, get a country for the address
    usa = await client.model(ResCountry).filter(code="US").first()
    
    if usa:
        # Create company with country relationship
        company = await client.model(ResPartner).create({
            "name": "American Tech Co",
            "is_company": True,
            "email": "info@americantech.com",
            "country_id": usa.id,  # Many2One relationship
            "street": "456 Tech Street",
            "city": "Silicon Valley",
            "zip": "94000"
        })
        
        # Create a contact for this company
        contact = await client.model(ResPartner).create({
            "name": "John Smith",
            "is_company": False,
            "email": "john.smith@americantech.com",
            "phone": "+1-555-0127",
            "parent_id": company.id,  # Link to parent company
            "function": "CEO"
        })
        
        print(f"Created company: {company.name}")
        print(f"Created contact: {contact.name}")
        
        return company, contact
    
    return None, None

# Usage
company, contact = await create_with_relationships(client)
```

## Read Operations

### Reading Single Records

```python
async def read_single_record(client: ZenooClient):
    """Read a single record by ID"""
    
    # Get specific partner by ID
    partner = await client.model(ResPartner).get(1)
    
    if partner:
        print(f"Partner: {partner.name}")
        print(f"Email: {partner.email}")
        print(f"Is Company: {partner.is_company}")
        print(f"Active: {partner.active}")
    
    return partner

# Usage
partner = await read_single_record(client)
```

### Reading Multiple Records with Filtering

```python
async def read_with_filtering(client: ZenooClient):
    """Read records with various filters"""
    
    # Get all companies
    companies = await client.model(ResPartner).filter(
        is_company=True
    ).all()
    
    print(f"Found {len(companies)} companies")
    
    # Get companies with email
    companies_with_email = await client.model(ResPartner).filter(
        is_company=True,
        email__isnull=False
    ).all()
    
    print(f"Found {len(companies_with_email)} companies with email")
    
    # Get companies by name pattern
    acme_companies = await client.model(ResPartner).filter(
        is_company=True,
        name__ilike="acme%"
    ).all()
    
    print(f"Found {len(acme_companies)} companies with 'acme' in name")
    
    return companies, companies_with_email, acme_companies

# Usage
all_companies, companies_with_email, acme_companies = await read_with_filtering(client)
```

### Reading with Pagination

```python
async def read_with_pagination(client: ZenooClient):
    """Read records with pagination"""
    
    page_size = 10
    page = 0
    all_partners = []
    
    while True:
        # Get a page of partners
        partners = await client.model(ResPartner).filter(
            active=True
        ).order_by("name").limit(page_size).offset(page * page_size).all()
        
        if not partners:
            break  # No more records
        
        print(f"Page {page + 1}: {len(partners)} partners")
        all_partners.extend(partners)
        page += 1
        
        # For demo, stop after 3 pages
        if page >= 3:
            break
    
    print(f"Total loaded: {len(all_partners)} partners")
    return all_partners

# Usage
partners = await read_with_pagination(client)
```

### Reading with Relationships

```python
async def read_with_relationships(client: ZenooClient):
    """Read records and access relationships"""
    
    # Get partners with country information
    partners = await client.model(ResPartner).filter(
        is_company=True,
        country_id__isnull=False
    ).limit(5).all()
    
    for partner in partners:
        print(f"Company: {partner.name}")
        
        # Access Many2One relationship (lazy loaded)
        if partner.country_id:
            country = await partner.country_id
            print(f"  Country: {country.name} ({country.code})")
        
        # Access One2Many relationship
        children = await partner.child_ids.limit(3).all()
        if children:
            print(f"  Contacts ({len(children)}):")
            for child in children:
                print(f"    - {child.name}")
        
        print()  # Empty line for readability

# Usage
await read_with_relationships(client)
```

## Update Operations

### Updating Single Records

```python
async def update_single_record(client: ZenooClient):
    """Update a single record"""
    
    # Find a partner to update
    partner = await client.model(ResPartner).filter(
        name__ilike="acme%"
    ).first()
    
    if partner:
        # Update the partner
        updated_partner = await client.model(ResPartner).update(
            partner.id,
            {
                "email": "newemail@acme.com",
                "phone": "+1-555-9999",
                "website": "https://newacme.com"
            }
        )
        
        print(f"Updated partner: {updated_partner.name}")
        print(f"New email: {updated_partner.email}")
        
        return updated_partner
    
    return None

# Usage
updated_partner = await update_single_record(client)
```

### Updating Multiple Records

```python
async def update_multiple_records(client: ZenooClient):
    """Update multiple records at once"""
    
    # Update all companies without email
    updated_count = await client.model(ResPartner).filter(
        is_company=True,
        email__isnull=True
    ).update({
        "email": "info@company.com",  # Default email
        "comment": "Email added via bulk update"
    })
    
    print(f"Updated {updated_count} companies")
    
    # Update specific records by ID
    partner_ids = [1, 2, 3]  # Replace with actual IDs
    updated_partners = await client.model(ResPartner).filter(
        id__in=partner_ids
    ).update({
        "active": True,
        "comment": "Reactivated via bulk update"
    })
    
    print(f"Updated {updated_partners} specific partners")

# Usage
await update_multiple_records(client)
```

### Conditional Updates

```python
async def conditional_updates(client: ZenooClient):
    """Perform updates based on conditions"""
    
    # Update companies based on size (example logic)
    large_companies = await client.model(ResPartner).filter(
        is_company=True,
        # Assuming you have a custom field for company size
        # employee_count__gte=100
    ).update({
        "comment": "Large company - priority customer"
    })
    
    # Update partners without phone numbers
    partners_without_phone = await client.model(ResPartner).filter(
        phone__isnull=True,
        mobile__isnull=True
    ).update({
        "comment": "Missing contact information"
    })
    
    print(f"Updated companies and partners based on conditions")

# Usage
await conditional_updates(client)
```

## Delete Operations

### Deleting Single Records

```python
async def delete_single_record(client: ZenooClient):
    """Delete a single record"""
    
    # Create a test record first
    test_partner = await client.model(ResPartner).create({
        "name": "Test Partner for Deletion",
        "email": "test@delete.com"
    })
    
    print(f"Created test partner: {test_partner.name} (ID: {test_partner.id})")
    
    # Delete the record
    success = await client.model(ResPartner).delete(test_partner.id)
    
    if success:
        print(f"Successfully deleted partner {test_partner.id}")
    else:
        print(f"Failed to delete partner {test_partner.id}")
    
    return success

# Usage
success = await delete_single_record(client)
```

### Deleting Multiple Records

```python
async def delete_multiple_records(client: ZenooClient):
    """Delete multiple records"""
    
    # Create test records first
    test_data = [
        {"name": "Test Company 1", "is_company": True},
        {"name": "Test Company 2", "is_company": True},
        {"name": "Test Company 3", "is_company": True}
    ]
    
    test_partners = await client.model(ResPartner).bulk_create(test_data)
    test_ids = [p.id for p in test_partners]
    
    print(f"Created {len(test_partners)} test partners")
    
    # Delete by IDs
    success = await client.model(ResPartner).delete(test_ids)
    
    if success:
        print(f"Successfully deleted {len(test_ids)} partners")
    else:
        print("Failed to delete some or all partners")
    
    return success

# Usage
success = await delete_multiple_records(client)
```

### Conditional Deletion

```python
async def conditional_deletion(client: ZenooClient):
    """Delete records based on conditions"""
    
    # Delete inactive test partners
    deleted_count = await client.model(ResPartner).filter(
        name__ilike="test%",
        active=False
    ).delete()
    
    print(f"Deleted {deleted_count} inactive test partners")
    
    # Delete partners without any contact information
    deleted_count = await client.model(ResPartner).filter(
        email__isnull=True,
        phone__isnull=True,
        mobile__isnull=True,
        name__ilike="test%"  # Safety filter
    ).delete()
    
    print(f"Deleted {deleted_count} partners without contact info")

# Usage
await conditional_deletion(client)
```

## Error Handling in CRUD Operations

```python
async def crud_with_error_handling(client: ZenooClient):
    """CRUD operations with proper error handling"""
    
    try:
        # Create with validation
        partner = await client.model(ResPartner).create({
            "name": "Test Partner",
            "email": "invalid-email"  # This might cause validation error
        })
        
    except ValidationError as e:
        print(f"Validation error during create: {e}")
        
        # Create with valid data
        partner = await client.model(ResPartner).create({
            "name": "Test Partner",
            "email": "valid@email.com"
        })
    
    try:
        # Update with potential access error
        await client.model(ResPartner).update(partner.id, {
            "name": "Updated Name"
        })
        
    except AccessError as e:
        print(f"Access denied during update: {e}")
    
    try:
        # Delete with error handling
        await client.model(ResPartner).delete(partner.id)
        
    except Exception as e:
        print(f"Error during delete: {e}")

# Usage
await crud_with_error_handling(client)
```

## Complete CRUD Example

Here's a complete example that demonstrates all CRUD operations:

```python
async def complete_crud_example(client: ZenooClient):
    """Complete CRUD lifecycle example"""
    
    print("=== CRUD Operations Demo ===\n")
    
    # CREATE
    print("1. Creating records...")
    company = await client.model(ResPartner).create({
        "name": "Demo Company",
        "is_company": True,
        "email": "demo@company.com",
        "phone": "+1-555-DEMO"
    })
    print(f"Created: {company.name} (ID: {company.id})")
    
    # READ
    print("\n2. Reading records...")
    companies = await client.model(ResPartner).filter(
        name__ilike="demo%"
    ).all()
    print(f"Found {len(companies)} companies with 'demo' in name")
    
    # UPDATE
    print("\n3. Updating records...")
    updated_company = await client.model(ResPartner).update(
        company.id,
        {"website": "https://democompany.com"}
    )
    print(f"Updated: {updated_company.name} - Website: {updated_company.website}")
    
    # DELETE
    print("\n4. Deleting records...")
    success = await client.model(ResPartner).delete(company.id)
    print(f"Deleted: {'Success' if success else 'Failed'}")
    
    print("\n=== CRUD Demo Complete ===")

# Run the complete example
async def main():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        await complete_crud_example(client)

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

### 1. Use Transactions for Related Operations

```python
async def transactional_crud(client: ZenooClient):
    """Use transactions for data consistency"""
    
    async with client.transaction() as tx:
        # Create company
        company = await client.model(ResPartner).create({
            "name": "Transactional Company",
            "is_company": True
        })
        
        # Create contact
        contact = await client.model(ResPartner).create({
            "name": "John Doe",
            "parent_id": company.id,
            "email": "john@company.com"
        })
        
        # Both records created atomically
        # Automatic rollback if any operation fails
```

### 2. Use Bulk Operations for Performance

```python
# ✅ Good - Bulk operations
data = [{"name": f"Company {i}"} for i in range(100)]
companies = await client.model(ResPartner).bulk_create(data)

# ❌ Bad - Individual operations
companies = []
for i in range(100):
    company = await client.model(ResPartner).create({"name": f"Company {i}"})
    companies.append(company)
```

### 3. Handle Errors Gracefully

```python
async def safe_crud_operation(client: ZenooClient, data: dict):
    """Safely perform CRUD with error handling"""
    try:
        return await client.model(ResPartner).create(data)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return None
    except AccessError as e:
        logger.error(f"Access denied: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

## Next Steps

- [Advanced Queries](advanced-queries.md) - Learn complex filtering and joins
- [Performance Optimization](performance-optimization.md) - Speed up your operations
- [Testing Strategies](testing.md) - Test your CRUD operations
- [Transactions Guide](../user-guide/transactions.md) - Ensure data consistency
