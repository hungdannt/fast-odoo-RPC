# Integration Examples

This section provides comprehensive examples of integrating Zenoo RPC with popular frameworks, databases, and external services. Each integration includes complete setup, configuration, and best practices.

## Overview

Integration examples cover:

- **FastAPI Integration**: REST API development with Zenoo RPC backend
- **Django Integration**: Using Zenoo RPC within Django applications
- **Celery Integration**: Asynchronous task processing with Odoo data
- **Database Integration**: PostgreSQL, Redis, and other database connections
- **Message Queue Integration**: RabbitMQ, Apache Kafka integration patterns
- **Monitoring Integration**: Prometheus, Grafana, and logging systems

## FastAPI Integration

### Complete REST API with Zenoo RPC Backend

```python
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
import uvicorn

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import ValidationError, ZenooError
from zenoo_rpc.batch.manager import BatchManager
from zenoo_rpc.transaction.manager import TransactionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = None
    is_company: bool = True
    country_code: Optional[str] = Field(None, max_length=2)
    categories: Optional[List[str]] = None

class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    website: Optional[str]
    is_company: bool
    customer_rank: int
    country: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = None
    categories: Optional[List[str]] = None

class BulkCreateRequest(BaseModel):
    customers: List[CustomerCreate]

class BulkCreateResponse(BaseModel):
    successful: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    total: int
    success_count: int
    failure_count: int

# Global client instance
zenoo_client: Optional[ZenooClient] = None
batch_manager: Optional[BatchManager] = None
transaction_manager: Optional[TransactionManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global zenoo_client, batch_manager, transaction_manager
    
    try:
        # Startup
        logger.info("Starting FastAPI application with Zenoo RPC")
        
        # Initialize Zenoo RPC client
        zenoo_client = ZenooClient("localhost", port=8069, protocol="http")
        await zenoo_client.__aenter__()
        
        # Authenticate
        await zenoo_client.login("demo", "admin", "admin")
        
        # Setup cache
        await zenoo_client.cache_manager.setup_memory_cache(
            name="api_cache",
            max_size=1000,
            strategy="ttl"
        )
        
        # Setup managers
        batch_manager = BatchManager(client=zenoo_client, max_chunk_size=100)
        transaction_manager = TransactionManager(zenoo_client)
        
        logger.info("Zenoo RPC client initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize Zenoo RPC: {e}")
        raise
    finally:
        # Shutdown
        if zenoo_client:
            await zenoo_client.__aexit__(None, None, None)
        logger.info("FastAPI application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Customer Management API",
    description="REST API for customer management using Zenoo RPC",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get Zenoo client
async def get_zenoo_client() -> ZenooClient:
    """Dependency to get the Zenoo RPC client."""
    if not zenoo_client:
        raise HTTPException(status_code=503, detail="Zenoo RPC client not available")
    return zenoo_client

# Exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Validation Error", "detail": str(exc)}
    )

@app.exception_handler(ZenooError)
async def zenoo_exception_handler(request, exc: ZenooError):
    return JSONResponse(
        status_code=500,
        content={"error": "Zenoo RPC Error", "detail": str(exc)}
    )

# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if zenoo_client and zenoo_client.is_authenticated:
            # Test connection with a simple query
            count = await zenoo_client.search_count("res.users", [])
            return {
                "status": "healthy",
                "zenoo_connected": True,
                "user_count": count,
                "timestamp": datetime.utcnow()
            }
        else:
            return {
                "status": "unhealthy",
                "zenoo_connected": False,
                "timestamp": datetime.utcnow()
            }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post("/customers", response_model=CustomerResponse)
async def create_customer(
    customer: CustomerCreate,
    client: ZenooClient = Depends(get_zenoo_client)
):
    """Create a new customer."""
    try:
        async with transaction_manager.transaction() as tx:
            # Check for duplicates
            existing = await client.model(ResPartner).filter(
                email=customer.email
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Customer with email {customer.email} already exists"
                )
            
            # Prepare customer data
            customer_data = {
                "name": customer.name,
                "email": customer.email,
                "is_company": customer.is_company,
                "customer_rank": 1,
                "supplier_rank": 0
            }
            
            # Add optional fields
            if customer.phone:
                customer_data["phone"] = customer.phone
            if customer.website:
                customer_data["website"] = customer.website
            
            # Handle country
            if customer.country_code:
                from zenoo_rpc.models.common import ResCountry
                country = await client.model(ResCountry).filter(
                    code=customer.country_code.upper()
                ).first()
                if country:
                    customer_data["country_id"] = country.id
            
            # Create customer
            customer_id = await client.create("res.partner", customer_data)
            
            # Handle categories
            if customer.categories:
                await _assign_categories(client, customer_id, customer.categories)
            
            # Fetch created customer for response
            created_customer = await client.model(ResPartner).filter(
                id=customer_id
            ).first()
            
            return await _format_customer_response(created_customer)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    is_company: Optional[bool] = None,
    country_code: Optional[str] = None,
    client: ZenooClient = Depends(get_zenoo_client)
):
    """List customers with filtering and pagination."""
    try:
        query = client.model(ResPartner)
        
        # Build filters
        filters = {}
        
        if search:
            from zenoo_rpc.query.filters import Q
            search_filter = Q(name__ilike=f"%{search}%") | Q(email__ilike=f"%{search}%")
            query = query.filter(search_filter)
        
        if is_company is not None:
            filters["is_company"] = is_company
        
        if country_code:
            filters["country_id.code"] = country_code.upper()
        
        # Apply filters
        if filters:
            query = query.filter(**filters)
        
        # Apply pagination
        partners = await query.offset(offset).limit(limit).all()
        
        # Format response
        customers = []
        for partner in partners:
            customer = await _format_customer_response(partner)
            customers.append(customer)
        
        return customers
        
    except Exception as e:
        logger.error(f"Failed to list customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    client: ZenooClient = Depends(get_zenoo_client)
):
    """Get a specific customer by ID."""
    try:
        partner = await client.model(ResPartner).filter(id=customer_id).first()
        
        if not partner:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        return await _format_customer_response(partner)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    client: ZenooClient = Depends(get_zenoo_client)
):
    """Update a customer."""
    try:
        async with transaction_manager.transaction() as tx:
            # Check if customer exists
            existing = await client.model(ResPartner).filter(id=customer_id).first()
            if not existing:
                raise HTTPException(status_code=404, detail="Customer not found")
            
            # Prepare update data
            update_data = {}
            
            if customer_update.name is not None:
                update_data["name"] = customer_update.name
            if customer_update.email is not None:
                # Check for email conflicts
                email_conflict = await client.model(ResPartner).filter(
                    email=customer_update.email,
                    id__ne=customer_id
                ).first()
                if email_conflict:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Email {customer_update.email} is already in use"
                    )
                update_data["email"] = customer_update.email
            
            if customer_update.phone is not None:
                update_data["phone"] = customer_update.phone
            if customer_update.website is not None:
                update_data["website"] = customer_update.website
            
            # Update customer
            if update_data:
                await client.write("res.partner", [customer_id], update_data)
            
            # Handle categories
            if customer_update.categories is not None:
                await _assign_categories(client, customer_id, customer_update.categories)
            
            # Fetch updated customer
            updated_customer = await client.model(ResPartner).filter(
                id=customer_id
            ).first()
            
            return await _format_customer_response(updated_customer)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: int,
    client: ZenooClient = Depends(get_zenoo_client)
):
    """Delete a customer."""
    try:
        # Check if customer exists
        existing = await client.model(ResPartner).filter(id=customer_id).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Delete customer
        success = await client.unlink("res.partner", [customer_id])
        
        if success:
            return {"message": f"Customer {customer_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete customer")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/customers/bulk", response_model=BulkCreateResponse)
async def bulk_create_customers(
    request: BulkCreateRequest,
    background_tasks: BackgroundTasks,
    client: ZenooClient = Depends(get_zenoo_client)
):
    """Bulk create customers."""
    try:
        results = {
            "successful": [],
            "failed": [],
            "total": len(request.customers)
        }
        
        async with batch_manager.batch() as batch_context:
            # Validate and prepare data
            valid_customers = []
            
            for i, customer in enumerate(request.customers):
                try:
                    # Check for duplicates
                    existing = await client.model(ResPartner).filter(
                        email=customer.email
                    ).first()
                    
                    if existing:
                        results["failed"].append({
                            "index": i,
                            "customer": customer.dict(),
                            "error": f"Customer with email {customer.email} already exists"
                        })
                        continue
                    
                    # Prepare customer data
                    customer_data = {
                        "name": customer.name,
                        "email": customer.email,
                        "is_company": customer.is_company,
                        "customer_rank": 1,
                        "supplier_rank": 0
                    }
                    
                    if customer.phone:
                        customer_data["phone"] = customer.phone
                    if customer.website:
                        customer_data["website"] = customer.website
                    
                    valid_customers.append({
                        "index": i,
                        "original": customer,
                        "data": customer_data
                    })
                    
                except Exception as e:
                    results["failed"].append({
                        "index": i,
                        "customer": customer.dict(),
                        "error": str(e)
                    })
            
            # Bulk create
            if valid_customers:
                customer_data_list = [item["data"] for item in valid_customers]
                
                created_ids = await batch_manager.bulk_create(
                    model="res.partner",
                    records=customer_data_list,
                    chunk_size=50
                )
                
                # Map results
                for i, item in enumerate(valid_customers):
                    if i < len(created_ids):
                        results["successful"].append({
                            "index": item["index"],
                            "customer": item["original"].dict(),
                            "customer_id": created_ids[i]
                        })
                    else:
                        results["failed"].append({
                            "index": item["index"],
                            "customer": item["original"].dict(),
                            "error": "Bulk creation failed"
                        })
        
        # Add background task for category assignment
        if results["successful"]:
            background_tasks.add_task(
                _assign_bulk_categories,
                client,
                results["successful"],
                request.customers
            )
        
        return BulkCreateResponse(
            successful=results["successful"],
            failed=results["failed"],
            total=results["total"],
            success_count=len(results["successful"]),
            failure_count=len(results["failed"])
        )
        
    except Exception as e:
        logger.error(f"Bulk create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _format_customer_response(partner: ResPartner) -> CustomerResponse:
    """Format partner object as CustomerResponse."""
    response_data = {
        "id": partner.id,
        "name": partner.name,
        "email": partner.email,
        "phone": partner.phone,
        "website": partner.website,
        "is_company": partner.is_company,
        "customer_rank": partner.customer_rank,
        "created_at": partner.create_date
    }
    
    # Add country info if available
    if partner.country_id:
        country = await partner.country_id
        if country:
            response_data["country"] = {
                "id": country.id,
                "name": country.name,
                "code": country.code
            }
    
    return CustomerResponse(**response_data)

async def _assign_categories(client: ZenooClient, partner_id: int, category_names: List[str]):
    """Assign categories to a partner."""
    try:
        from zenoo_rpc.models.common import ResPartnerCategory
        
        category_ids = []
        for name in category_names:
            category = await client.model(ResPartnerCategory).filter(name=name).first()
            
            if not category:
                category_id = await client.create(
                    "res.partner.category",
                    {"name": name}
                )
                category_ids.append(category_id)
            else:
                category_ids.append(category.id)
        
        if category_ids:
            await client.write(
                "res.partner",
                [partner_id],
                {"category_id": [(6, 0, category_ids)]}
            )
            
    except Exception as e:
        logger.error(f"Failed to assign categories: {e}")

async def _assign_bulk_categories(
    client: ZenooClient,
    successful_customers: List[Dict[str, Any]],
    original_customers: List[CustomerCreate]
):
    """Background task to assign categories for bulk created customers."""
    try:
        for success_item in successful_customers:
            index = success_item["index"]
            customer_id = success_item["customer_id"]
            original_customer = original_customers[index]
            
            if original_customer.categories:
                await _assign_categories(client, customer_id, original_customer.categories)
                
    except Exception as e:
        logger.error(f"Background category assignment failed: {e}")

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

## Key Integration Features

### 1. **Lifecycle Management**
- Proper startup/shutdown with lifespan events
- Resource cleanup and connection management
- Health check endpoints

### 2. **Error Handling**
- Custom exception handlers for Zenoo RPC errors
- Proper HTTP status codes
- Detailed error responses

### 3. **Performance Optimization**
- Connection pooling and caching
- Background tasks for non-critical operations
- Batch processing for bulk operations

### 4. **Production Features**
- CORS middleware
- Request validation with Pydantic
- Comprehensive logging
- Transaction management

## Next Steps

- Explore [Django Integration](django-integration.md) for Django applications
- Check [Celery Integration](celery-integration.md) for async task processing
- Learn [Database Integration](database-integration.md) for multi-database setups
