# Customer Management System

A comprehensive example demonstrating how to build a customer management system using Zenoo RPC with real-world patterns and best practices.

## Overview

This example shows how to implement a complete customer management system that handles:

- Customer creation and validation
- Bulk customer imports
- Customer search and filtering
- Relationship management (contacts, addresses)
- Transaction safety for data integrity
- Caching for performance optimization

## Complete Implementation

### Basic Customer Operations

```python
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, ResCountry
from zenoo_rpc.exceptions import ValidationError, AccessError
from zenoo_rpc.query.filters import Q

class CustomerManager:
    """Customer management service with business logic."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def create_customer(
        self, 
        name: str, 
        email: str, 
        phone: Optional[str] = None,
        is_company: bool = False,
        country_code: Optional[str] = None
    ) -> ResPartner:
        """Create a new customer with validation."""
        
        # Validate email uniqueness
        existing = await self.client.model(ResPartner).filter(
            email=email
        ).first()
        
        if existing:
            raise ValidationError(f"Customer with email {email} already exists")
        
        # Get country if provided
        country_id = None
        if country_code:
            country = await self.client.model(ResCountry).filter(
                code=country_code.upper()
            ).first()
            if country:
                country_id = country.id
        
        # Create customer data
        customer_data = {
            "name": name,
            "email": email,
            "is_company": is_company,
            "customer_rank": 1,  # Mark as customer
            "supplier_rank": 0,
        }
        
        if phone:
            customer_data["phone"] = phone
        if country_id:
            customer_data["country_id"] = country_id
        
        # Create customer with transaction safety
        async with self.client.transaction() as tx:
            customer = await self.client.model(ResPartner).create(customer_data)
            
            # Log customer creation
            await self._log_customer_activity(
                customer.id, 
                "created", 
                f"Customer {name} created"
            )
            
            return customer
    
    async def bulk_import_customers(
        self, 
        customer_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import multiple customers efficiently using batch operations."""
        
        results = {
            "successful": [],
            "failed": [],
            "duplicates": []
        }
        
        # Validate and prepare data
        validated_data = []
        for data in customer_data_list:
            try:
                # Check for required fields
                if not data.get("name") or not data.get("email"):
                    results["failed"].append({
                        "data": data,
                        "error": "Missing required fields: name or email"
                    })
                    continue
                
                # Check for duplicates
                existing = await self.client.model(ResPartner).filter(
                    email=data["email"]
                ).first()
                
                if existing:
                    results["duplicates"].append({
                        "data": data,
                        "existing_id": existing.id
                    })
                    continue
                
                # Prepare customer data
                customer_data = {
                    "name": data["name"],
                    "email": data["email"],
                    "phone": data.get("phone"),
                    "is_company": data.get("is_company", False),
                    "customer_rank": 1,
                    "supplier_rank": 0,
                }
                
                validated_data.append(customer_data)
                
            except Exception as e:
                results["failed"].append({
                    "data": data,
                    "error": str(e)
                })
        
        # Bulk create using batch operations
        if validated_data:
            try:
                async with self.client.batch() as batch:
                    for data in validated_data:
                        batch.create("res.partner", data)
                
                # Execute batch and get results
                batch_results = await batch.execute()
                results["successful"] = batch_results.get("created", [])
                
            except Exception as e:
                # If batch fails, try individual creates
                for data in validated_data:
                    try:
                        customer = await self.client.model(ResPartner).create(data)
                        results["successful"].append(customer.id)
                    except Exception as create_error:
                        results["failed"].append({
                            "data": data,
                            "error": str(create_error)
                        })
        
        return results
    
    async def search_customers(
        self,
        query: Optional[str] = None,
        is_company: Optional[bool] = None,
        country_code: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100
    ) -> List[ResPartner]:
        """Advanced customer search with multiple filters."""
        
        # Build query using Q objects for complex filtering
        filters = Q()
        
        # Customer rank filter (customers only)
        filters &= Q(customer_rank__gt=0)
        
        # Text search across multiple fields
        if query:
            text_filter = (
                Q(name__ilike=f"%{query}%") |
                Q(email__ilike=f"%{query}%") |
                Q(phone__ilike=f"%{query}%")
            )
            filters &= text_filter
        
        # Company/individual filter
        if is_company is not None:
            filters &= Q(is_company=is_company)
        
        # Country filter
        if country_code:
            country = await self.client.model(ResCountry).filter(
                code=country_code.upper()
            ).first()
            if country:
                filters &= Q(country_id=country.id)
        
        # Active filter
        if active_only:
            filters &= Q(active=True)
        
        # Execute search with caching
        customers = await (
            self.client.model(ResPartner)
            .filter(filters)
            .only("name", "email", "phone", "is_company", "country_id")
            .order_by("name")
            .limit(limit)
            .cache(ttl=300)  # Cache for 5 minutes
            .all()
        )
        
        return customers
    
    async def get_customer_with_contacts(self, customer_id: int) -> Dict[str, Any]:
        """Get customer with all related contacts and addresses."""
        
        # Get main customer
        customer = await self.client.model(ResPartner).filter(
            id=customer_id
        ).first()
        
        if not customer:
            raise ValidationError(f"Customer with ID {customer_id} not found")
        
        # Get related contacts (children)
        contacts = await self.client.model(ResPartner).filter(
            parent_id=customer_id,
            active=True
        ).only("name", "email", "phone", "function").all()
        
        # Get delivery addresses
        addresses = await self.client.model(ResPartner).filter(
            parent_id=customer_id,
            type__in=["delivery", "invoice"]
        ).only("name", "street", "city", "zip", "type").all()
        
        return {
            "customer": customer,
            "contacts": contacts,
            "addresses": addresses,
            "total_contacts": len(contacts),
            "total_addresses": len(addresses)
        }
    
    async def update_customer_batch(
        self, 
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update multiple customers efficiently."""
        
        results = {"successful": [], "failed": []}
        
        async with self.client.transaction() as tx:
            try:
                async with self.client.batch() as batch:
                    for update_data in updates:
                        customer_id = update_data.pop("id")
                        batch.update("res.partner", update_data, record_ids=[customer_id])
                
                batch_results = await batch.execute()
                results["successful"] = batch_results.get("updated", [])
                
            except Exception as e:
                # Rollback transaction and try individual updates
                await tx.rollback()
                
                for update_data in updates:
                    try:
                        customer_id = update_data.pop("id")
                        await self.client.model(ResPartner).update(
                            customer_id, update_data
                        )
                        results["successful"].append(customer_id)
                    except Exception as update_error:
                        results["failed"].append({
                            "id": customer_id,
                            "error": str(update_error)
                        })
        
        return results
    
    async def _log_customer_activity(
        self, 
        customer_id: int, 
        activity_type: str, 
        description: str
    ):
        """Log customer activity for audit trail."""
        # This would typically create a log entry
        # Implementation depends on your logging requirements
        pass

# Usage Example
async def main():
    """Demonstrate customer management system."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize customer manager
        customer_mgr = CustomerManager(client)
        
        # Create individual customer
        customer = await customer_mgr.create_customer(
            name="ACME Corporation",
            email="contact@acme.com",
            phone="+1-555-0123",
            is_company=True,
            country_code="US"
        )
        print(f"Created customer: {customer.name} (ID: {customer.id})")
        
        # Bulk import customers
        customer_data = [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1-555-0124",
                "is_company": False
            },
            {
                "name": "Jane Smith",
                "email": "jane@example.com",
                "is_company": False
            },
            {
                "name": "Tech Solutions Inc",
                "email": "info@techsolutions.com",
                "is_company": True
            }
        ]
        
        import_results = await customer_mgr.bulk_import_customers(customer_data)
        print(f"Import results: {len(import_results['successful'])} successful, "
              f"{len(import_results['failed'])} failed")
        
        # Search customers
        companies = await customer_mgr.search_customers(
            is_company=True,
            active_only=True,
            limit=10
        )
        print(f"Found {len(companies)} companies")
        
        # Get customer with contacts
        if companies:
            customer_details = await customer_mgr.get_customer_with_contacts(
                companies[0].id
            )
            print(f"Customer {customer_details['customer'].name} has "
                  f"{customer_details['total_contacts']} contacts")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Type Safety**
- Uses Pydantic models (`ResPartner`, `ResCountry`)
- Type hints throughout the implementation
- IDE autocompletion and validation

### 2. **Performance Optimization**
- Batch operations for bulk imports
- Query caching with TTL
- Efficient field selection with `only()`

### 3. **Transaction Safety**
- ACID transactions for data integrity
- Automatic rollback on errors
- Savepoint support for complex operations

### 4. **Advanced Querying**
- Q objects for complex filters
- Multiple field search
- Relationship filtering

### 5. **Error Handling**
- Comprehensive exception handling
- Graceful degradation (batch → individual)
- Detailed error reporting

### 6. **Real-World Patterns**
- Service layer architecture
- Validation and business logic
- Audit trail logging
- Duplicate detection

## Integration with Other Systems

This customer management system can be easily integrated with:

- **CRM Systems**: Sync customer data
- **E-commerce Platforms**: Customer import/export
- **Marketing Tools**: Customer segmentation
- **Analytics**: Customer behavior tracking

## Next Steps

- [Sales Dashboard](sales-dashboard.md) - Build analytics on customer data
- [Performance Metrics](performance-metrics.md) - Monitor system performance
- [Data Visualization](data-visualization.md) - Create customer insights
