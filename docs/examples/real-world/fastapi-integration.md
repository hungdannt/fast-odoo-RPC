# FastAPI Integration Example

This example demonstrates how to build a modern REST API using FastAPI and Zenoo RPC to interact with Odoo. The API provides endpoints for managing customers, products, and orders with proper authentication, validation, and error handling.

## Overview

We'll create a FastAPI application that:

- Provides REST endpoints for Odoo data
- Uses dependency injection for Zenoo RPC client
- Implements proper authentication and authorization
- Includes request/response validation with Pydantic
- Handles errors gracefully
- Supports async operations for high performance

## Project Structure

```
fastapi_odoo_api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── dependencies.py      # Dependency injection
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   ├── customer.py
│   │   ├── product.py
│   │   └── order.py
│   ├── routers/             # API routers
│   │   ├── __init__.py
│   │   ├── customers.py
│   │   ├── products.py
│   │   └── orders.py
│   └── utils/               # Utilities
│       ├── __init__.py
│       └── auth.py
├── requirements.txt
└── README.md
```

## Installation and Setup

### Requirements

```txt
# requirements.txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
zenoo-rpc>=0.3.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
pydantic>=2.0.0
python-dotenv>=1.0.0
```

### Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Odoo Configuration
    odoo_host: str = "localhost"
    odoo_port: int = 8069
    odoo_protocol: str = "http"
    odoo_database: str = "demo"
    odoo_username: str = "admin"
    odoo_password: str = "admin"
    
    # API Configuration
    api_title: str = "Odoo FastAPI Integration"
    api_version: str = "1.0.0"
    api_description: str = "REST API for Odoo using Zenoo RPC"
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Performance
    cache_ttl: int = 300  # 5 minutes
    max_connections: int = 100
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Dependencies

```python
# app/dependencies.py
import asyncio
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError, AuthenticationError
from .config import settings
from .utils.auth import verify_token

security = HTTPBearer()

# Global client instance
_client_instance = None
_client_lock = asyncio.Lock()

async def get_zenoo_client() -> AsyncGenerator[ZenooClient, None]:
    """Dependency to get Zenoo RPC client instance"""
    global _client_instance
    
    async with _client_lock:
        if _client_instance is None:
            try:
                _client_instance = ZenooClient(
                    host=settings.odoo_host,
                    port=settings.odoo_port,
                    protocol=settings.odoo_protocol,
                    max_connections=settings.max_connections
                )
                
                # Setup caching
                await _client_instance.cache_manager.setup_memory_cache(
                    max_size=1000,
                    default_ttl=settings.cache_ttl
                )
                
                # Authenticate
                await _client_instance.login(
                    settings.odoo_database,
                    settings.odoo_username,
                    settings.odoo_password
                )
                
            except AuthenticationError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to authenticate with Odoo: {e}"
                )
            except ZenooError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to Odoo: {e}"
                )
    
    yield _client_instance

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated user"""
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### Pydantic Models

```python
# app/models/customer.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    is_company: bool = False
    street: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=50)
    zip: Optional[str] = Field(None, max_length=10)
    country_code: Optional[str] = Field(None, max_length=2)

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    is_company: Optional[bool] = None
    street: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=50)
    zip: Optional[str] = Field(None, max_length=10)
    country_code: Optional[str] = Field(None, max_length=2)
    active: Optional[bool] = None

class Customer(CustomerBase):
    id: int
    active: bool = True
    create_date: Optional[datetime] = None
    write_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CustomerList(BaseModel):
    customers: list[Customer]
    total: int
    page: int
    page_size: int
    total_pages: int
```

```python
# app/models/product.py
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    default_code: Optional[str] = Field(None, max_length=50)
    list_price: Decimal = Field(..., ge=0)
    standard_price: Decimal = Field(..., ge=0)
    type: str = Field("consu", regex="^(consu|service|product)$")
    categ_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    default_code: Optional[str] = Field(None, max_length=50)
    list_price: Optional[Decimal] = Field(None, ge=0)
    standard_price: Optional[Decimal] = Field(None, ge=0)
    type: Optional[str] = Field(None, regex="^(consu|service|product)$")
    categ_id: Optional[int] = None
    active: Optional[bool] = None

class Product(ProductBase):
    id: int
    active: bool = True
    qty_available: Optional[Decimal] = None
    
    class Config:
        from_attributes = True
```

### API Routers

```python
# app/routers/customers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, ResCountry
from zenoo_rpc.exceptions import ZenooError, ValidationError
from ..dependencies import get_zenoo_client, get_current_user
from ..models.customer import Customer, CustomerCreate, CustomerUpdate, CustomerList

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("/", response_model=CustomerList)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None, max_length=100),
    is_company: bool = Query(None),
    active: bool = Query(True),
    client: ZenooClient = Depends(get_zenoo_client),
    current_user: dict = Depends(get_current_user)
):
    """List customers with pagination and filtering"""
    try:
        # Build query
        query = client.model(ResPartner)
        
        # Apply filters
        if active is not None:
            query = query.filter(active=active)
        
        if is_company is not None:
            query = query.filter(is_company=is_company)
        
        if search:
            query = query.filter(name__ilike=f"%{search}%")
        
        # Get total count
        total = await query.count()
        
        # Get paginated results
        offset = (page - 1) * page_size
        partners = await query.order_by("name").limit(page_size).offset(offset).all()
        
        # Convert to response model
        customers = [
            Customer(
                id=partner.id,
                name=partner.name,
                email=partner.email,
                phone=partner.phone,
                is_company=partner.is_company,
                street=partner.street,
                city=partner.city,
                zip=partner.zip,
                active=partner.active,
                create_date=partner.create_date,
                write_date=partner.write_date
            )
            for partner in partners
        ]
        
        total_pages = (total + page_size - 1) // page_size
        
        return CustomerList(
            customers=customers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except ZenooError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Odoo service error: {e}"
        )

@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: int,
    client: ZenooClient = Depends(get_zenoo_client),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific customer by ID"""
    try:
        partner = await client.model(ResPartner).get(customer_id)
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        return Customer(
            id=partner.id,
            name=partner.name,
            email=partner.email,
            phone=partner.phone,
            is_company=partner.is_company,
            street=partner.street,
            city=partner.city,
            zip=partner.zip,
            active=partner.active,
            create_date=partner.create_date,
            write_date=partner.write_date
        )
        
    except ZenooError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Odoo service error: {e}"
        )

@router.post("/", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    client: ZenooClient = Depends(get_zenoo_client),
    current_user: dict = Depends(get_current_user)
):
    """Create a new customer"""
    try:
        # Prepare data for Odoo
        odoo_data = customer_data.dict(exclude_none=True)
        
        # Handle country code
        if customer_data.country_code:
            country = await client.model(ResCountry).filter(
                code=customer_data.country_code.upper()
            ).first()
            if country:
                odoo_data["country_id"] = country.id
            del odoo_data["country_code"]
        
        # Create partner in Odoo
        partner = await client.model(ResPartner).create(odoo_data)
        
        return Customer(
            id=partner.id,
            name=partner.name,
            email=partner.email,
            phone=partner.phone,
            is_company=partner.is_company,
            street=partner.street,
            city=partner.city,
            zip=partner.zip,
            active=partner.active,
            create_date=partner.create_date,
            write_date=partner.write_date
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e}"
        )
    except ZenooError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Odoo service error: {e}"
        )

@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    client: ZenooClient = Depends(get_zenoo_client),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing customer"""
    try:
        # Check if customer exists
        existing_partner = await client.model(ResPartner).get(customer_id)
        if not existing_partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Prepare update data
        update_data = customer_data.dict(exclude_none=True)
        
        # Handle country code
        if customer_data.country_code:
            country = await client.model(ResCountry).filter(
                code=customer_data.country_code.upper()
            ).first()
            if country:
                update_data["country_id"] = country.id
            del update_data["country_code"]
        
        # Update partner in Odoo
        partner = await client.model(ResPartner).update(customer_id, update_data)
        
        return Customer(
            id=partner.id,
            name=partner.name,
            email=partner.email,
            phone=partner.phone,
            is_company=partner.is_company,
            street=partner.street,
            city=partner.city,
            zip=partner.zip,
            active=partner.active,
            create_date=partner.create_date,
            write_date=partner.write_date
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e}"
        )
    except ZenooError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Odoo service error: {e}"
        )

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    client: ZenooClient = Depends(get_zenoo_client),
    current_user: dict = Depends(get_current_user)
):
    """Delete a customer (soft delete by setting active=False)"""
    try:
        # Check if customer exists
        existing_partner = await client.model(ResPartner).get(customer_id)
        if not existing_partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Soft delete by setting active=False
        await client.model(ResPartner).update(customer_id, {"active": False})
        
    except ZenooError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Odoo service error: {e}"
        )
```

### Main Application

```python
# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from .config import settings
from .routers import customers, products, orders
from .dependencies import _client_instance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting FastAPI application")
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    if _client_instance:
        await _client_instance.close()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customers.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Odoo FastAPI Integration",
        "version": settings.api_version,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "odoo-fastapi-api"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

## Running the Application

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ODOO_HOST=localhost
export ODOO_PORT=8069
export ODOO_DATABASE=demo
export ODOO_USERNAME=admin
export ODOO_PASSWORD=admin

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production with Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ODOO_HOST=odoo
      - ODOO_PORT=8069
      - ODOO_DATABASE=demo
      - ODOO_USERNAME=admin
      - ODOO_PASSWORD=admin
    depends_on:
      - odoo
  
  odoo:
    image: odoo:17
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
```

## API Usage Examples

### Create a Customer

```bash
curl -X POST "http://localhost:8000/api/v1/customers/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Acme Corporation",
    "email": "contact@acme.com",
    "phone": "+1-555-0123",
    "is_company": true,
    "street": "123 Business Ave",
    "city": "Business City",
    "zip": "12345",
    "country_code": "US"
  }'
```

### List Customers

```bash
curl "http://localhost:8000/api/v1/customers/?page=1&page_size=10&search=acme" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update a Customer

```bash
curl -X PUT "http://localhost:8000/api/v1/customers/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email": "newemail@acme.com",
    "phone": "+1-555-9999"
  }'
```

## Features

- ✅ **RESTful API** with proper HTTP methods and status codes
- ✅ **Async/await** for high performance
- ✅ **Pydantic validation** for request/response data
- ✅ **Dependency injection** for clean architecture
- ✅ **Error handling** with proper HTTP status codes
- ✅ **Authentication** with JWT tokens
- ✅ **Pagination** for large datasets
- ✅ **Filtering and search** capabilities
- ✅ **Caching** for improved performance
- ✅ **Docker support** for easy deployment
- ✅ **OpenAPI documentation** at `/docs`

## Next Steps

- Add more endpoints for products and orders
- Implement rate limiting
- Add comprehensive logging and monitoring
- Set up automated testing
- Configure production security settings

This example provides a solid foundation for building production-ready APIs that integrate with Odoo using Zenoo RPC and FastAPI.
