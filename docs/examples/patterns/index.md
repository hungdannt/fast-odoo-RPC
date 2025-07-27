# Design Patterns

This section demonstrates common design patterns and architectural approaches when building applications with Zenoo RPC. Each pattern includes implementation examples, use cases, and best practices.

## Overview

The design patterns covered include:

- **Repository Pattern**: Data access abstraction layer
- **Service Layer Pattern**: Business logic encapsulation
- **Factory Pattern**: Object creation and configuration
- **Observer Pattern**: Event-driven architecture
- **Command Pattern**: Operation encapsulation and queuing
- **Strategy Pattern**: Algorithm selection and configuration

## Repository Pattern

### Basic Repository Implementation

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import ValidationError, ZenooError

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for data access operations."""
    
    def __init__(self, client: ZenooClient, model_name: str):
        self.client = client
        self.model_name = model_name
    
    @abstractmethod
    async def get_by_id(self, record_id: int) -> Optional[T]:
        """Get a record by ID."""
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> int:
        """Create a new record."""
        pass
    
    @abstractmethod
    async def update(self, record_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing record."""
        pass
    
    @abstractmethod
    async def delete(self, record_id: int) -> bool:
        """Delete a record."""
        pass
    
    @abstractmethod
    async def find_all(self, filters: Dict[str, Any] = None, limit: int = None) -> List[T]:
        """Find records with optional filters."""
        pass

class PartnerRepository(BaseRepository[ResPartner]):
    """Repository for partner/customer operations."""
    
    def __init__(self, client: ZenooClient):
        super().__init__(client, "res.partner")
    
    async def get_by_id(self, record_id: int) -> Optional[ResPartner]:
        """Get a partner by ID."""
        try:
            partner = await self.client.model(ResPartner).filter(id=record_id).first()
            return partner
        except Exception as e:
            raise ZenooError(f"Failed to get partner {record_id}: {e}")
    
    async def create(self, data: Dict[str, Any]) -> int:
        """Create a new partner."""
        try:
            # Validate required fields
            if not data.get("name"):
                raise ValidationError("Partner name is required")
            
            # Set default values
            partner_data = {
                "customer_rank": 1,
                "supplier_rank": 0,
                **data
            }
            
            partner_id = await self.client.create(self.model_name, partner_data)
            return partner_id
            
        except Exception as e:
            raise ZenooError(f"Failed to create partner: {e}")
    
    async def update(self, record_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing partner."""
        try:
            # Verify partner exists
            existing = await self.get_by_id(record_id)
            if not existing:
                raise ValidationError(f"Partner {record_id} not found")
            
            success = await self.client.write(self.model_name, [record_id], data)
            return success
            
        except Exception as e:
            raise ZenooError(f"Failed to update partner {record_id}: {e}")
    
    async def delete(self, record_id: int) -> bool:
        """Delete a partner."""
        try:
            success = await self.client.unlink(self.model_name, [record_id])
            return success
            
        except Exception as e:
            raise ZenooError(f"Failed to delete partner {record_id}: {e}")
    
    async def find_all(self, filters: Dict[str, Any] = None, limit: int = None) -> List[ResPartner]:
        """Find partners with optional filters."""
        try:
            query = self.client.model(ResPartner)
            
            if filters:
                query = query.filter(**filters)
            
            if limit:
                query = query.limit(limit)
            
            partners = await query.all()
            return partners
            
        except Exception as e:
            raise ZenooError(f"Failed to find partners: {e}")
    
    async def find_by_email(self, email: str) -> Optional[ResPartner]:
        """Find a partner by email address."""
        partners = await self.find_all({"email": email}, limit=1)
        return partners[0] if partners else None
    
    async def find_companies(self, limit: int = None) -> List[ResPartner]:
        """Find all company partners."""
        return await self.find_all({"is_company": True}, limit=limit)
    
    async def find_by_country(self, country_code: str, limit: int = None) -> List[ResPartner]:
        """Find partners by country code."""
        return await self.find_all({"country_id.code": country_code}, limit=limit)
```

## Service Layer Pattern

### Business Logic Service

```python
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from zenoo_rpc.transaction.manager import TransactionManager
from zenoo_rpc.batch.manager import BatchManager
from zenoo_rpc.exceptions import ValidationError, ZenooError

logger = logging.getLogger(__name__)

@dataclass
class CustomerCreationRequest:
    """Data transfer object for customer creation."""
    name: str
    email: str
    phone: Optional[str] = None
    is_company: bool = True
    website: Optional[str] = None
    country_code: Optional[str] = None
    categories: Optional[List[str]] = None

@dataclass
class CustomerCreationResult:
    """Result of customer creation operation."""
    customer_id: int
    success: bool
    message: str
    warnings: List[str] = None

class CustomerService:
    """Service layer for customer business logic."""
    
    def __init__(
        self, 
        partner_repository: PartnerRepository,
        transaction_manager: TransactionManager,
        batch_manager: BatchManager
    ):
        self.partner_repo = partner_repository
        self.transaction_manager = transaction_manager
        self.batch_manager = batch_manager
    
    async def create_customer(self, request: CustomerCreationRequest) -> CustomerCreationResult:
        """Create a new customer with business logic validation."""
        warnings = []
        
        try:
            async with self.transaction_manager.transaction() as tx:
                # Business validation
                await self._validate_customer_request(request, warnings)
                
                # Check for duplicates
                existing = await self.partner_repo.find_by_email(request.email)
                if existing:
                    raise ValidationError(f"Customer with email {request.email} already exists")
                
                # Prepare customer data
                customer_data = {
                    "name": request.name,
                    "email": request.email,
                    "is_company": request.is_company,
                    "customer_rank": 1
                }
                
                # Add optional fields
                if request.phone:
                    customer_data["phone"] = request.phone
                if request.website:
                    customer_data["website"] = request.website
                
                # Handle country
                if request.country_code:
                    country_id = await self._resolve_country(request.country_code)
                    if country_id:
                        customer_data["country_id"] = country_id
                    else:
                        warnings.append(f"Country code {request.country_code} not found")
                
                # Create customer
                customer_id = await self.partner_repo.create(customer_data)
                
                # Handle categories
                if request.categories:
                    await self._assign_categories(customer_id, request.categories)
                
                # Log business event
                logger.info(f"Customer created: {request.name} (ID: {customer_id})")
                
                return CustomerCreationResult(
                    customer_id=customer_id,
                    success=True,
                    message=f"Customer {request.name} created successfully",
                    warnings=warnings
                )
                
        except ValidationError as e:
            logger.warning(f"Customer creation validation failed: {e}")
            return CustomerCreationResult(
                customer_id=0,
                success=False,
                message=str(e),
                warnings=warnings
            )
        except Exception as e:
            logger.error(f"Customer creation failed: {e}")
            raise ZenooError(f"Failed to create customer: {e}")
    
    async def bulk_create_customers(
        self, 
        requests: List[CustomerCreationRequest]
    ) -> Dict[str, Any]:
        """Bulk create customers with batch processing."""
        results = {
            "successful": [],
            "failed": [],
            "total": len(requests),
            "warnings": []
        }
        
        try:
            async with self.batch_manager.batch() as batch_context:
                # Validate all requests first
                valid_requests = []
                
                for i, request in enumerate(requests):
                    try:
                        warnings = []
                        await self._validate_customer_request(request, warnings)
                        
                        # Check for duplicates within the batch
                        duplicate_in_batch = any(
                            r.email == request.email 
                            for r in valid_requests
                        )
                        
                        if duplicate_in_batch:
                            results["failed"].append({
                                "index": i,
                                "request": request,
                                "error": f"Duplicate email in batch: {request.email}"
                            })
                            continue
                        
                        # Check for existing customers
                        existing = await self.partner_repo.find_by_email(request.email)
                        if existing:
                            results["failed"].append({
                                "index": i,
                                "request": request,
                                "error": f"Customer already exists: {request.email}"
                            })
                            continue
                        
                        valid_requests.append({
                            "index": i,
                            "request": request,
                            "warnings": warnings
                        })
                        
                    except Exception as e:
                        results["failed"].append({
                            "index": i,
                            "request": request,
                            "error": str(e)
                        })
                
                # Bulk create valid customers
                if valid_requests:
                    customer_data_list = []
                    
                    for item in valid_requests:
                        request = item["request"]
                        customer_data = {
                            "name": request.name,
                            "email": request.email,
                            "is_company": request.is_company,
                            "customer_rank": 1
                        }
                        
                        if request.phone:
                            customer_data["phone"] = request.phone
                        if request.website:
                            customer_data["website"] = request.website
                        
                        customer_data_list.append(customer_data)
                    
                    # Execute bulk creation
                    created_ids = await self.batch_manager.bulk_create(
                        model="res.partner",
                        records=customer_data_list,
                        chunk_size=50
                    )
                    
                    # Map results
                    for i, item in enumerate(valid_requests):
                        if i < len(created_ids):
                            results["successful"].append({
                                "index": item["index"],
                                "request": item["request"],
                                "customer_id": created_ids[i],
                                "warnings": item["warnings"]
                            })
                        else:
                            results["failed"].append({
                                "index": item["index"],
                                "request": item["request"],
                                "error": "Bulk creation failed"
                            })
            
            logger.info(f"Bulk customer creation: {len(results['successful'])}/{results['total']} successful")
            return results
            
        except Exception as e:
            logger.error(f"Bulk customer creation failed: {e}")
            raise
    
    async def _validate_customer_request(
        self, 
        request: CustomerCreationRequest, 
        warnings: List[str]
    ):
        """Validate customer creation request."""
        # Required field validation
        if not request.name or len(request.name.strip()) < 2:
            raise ValidationError("Customer name must be at least 2 characters")
        
        if not request.email or "@" not in request.email:
            raise ValidationError("Valid email address is required")
        
        # Business rule validation
        if request.website and not request.website.startswith(("http://", "https://")):
            warnings.append("Website URL should include protocol (http:// or https://)")
        
        if request.phone and len(request.phone) < 10:
            warnings.append("Phone number seems too short")
    
    async def _resolve_country(self, country_code: str) -> Optional[int]:
        """Resolve country code to country ID."""
        try:
            from zenoo_rpc.models.common import ResCountry
            country = await self.partner_repo.client.model(ResCountry).filter(
                code=country_code.upper()
            ).first()
            return country.id if country else None
        except Exception:
            return None
    
    async def _assign_categories(self, customer_id: int, category_names: List[str]):
        """Assign categories to customer."""
        try:
            from zenoo_rpc.models.common import ResPartnerCategory
            
            category_ids = []
            for name in category_names:
                category = await self.partner_repo.client.model(ResPartnerCategory).filter(
                    name=name
                ).first()
                
                if not category:
                    # Create category if it doesn't exist
                    category_id = await self.partner_repo.client.create(
                        "res.partner.category",
                        {"name": name}
                    )
                    category_ids.append(category_id)
                else:
                    category_ids.append(category.id)
            
            # Assign categories
            if category_ids:
                await self.partner_repo.client.write(
                    "res.partner",
                    [customer_id],
                    {"category_id": [(6, 0, category_ids)]}
                )
                
        except Exception as e:
            logger.error(f"Failed to assign categories: {e}")
            # Don't fail the entire operation for category assignment
```

## Factory Pattern

### Client Factory

```python
import os
from typing import Optional, Dict, Any
from zenoo_rpc import ZenooClient
from zenoo_rpc.batch.manager import BatchManager
from zenoo_rpc.transaction.manager import TransactionManager
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy
from zenoo_rpc.retry.policies import DefaultRetryPolicy

class ZenooClientFactory:
    """Factory for creating configured Zenoo RPC clients."""
    
    @staticmethod
    async def create_production_client(
        host: str,
        database: str,
        username: str,
        password: str,
        port: int = 443,
        protocol: str = "https"
    ) -> ZenooClient:
        """Create a production-ready client with all features enabled."""
        
        client = ZenooClient(
            host_or_url=host,
            port=port,
            protocol=protocol,
            timeout=30.0,
            verify_ssl=True
        )
        
        # Setup cache
        await client.cache_manager.setup_redis_cache(
            name="production_cache",
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            namespace="zenoo_rpc",
            strategy="ttl",
            enable_fallback=True
        )
        
        # Authenticate
        await client.login(database, username, password)
        
        return client
    
    @staticmethod
    async def create_development_client(
        host: str = "localhost",
        database: str = "demo",
        username: str = "admin",
        password: str = "admin",
        port: int = 8069
    ) -> ZenooClient:
        """Create a development client with memory cache."""
        
        client = ZenooClient(
            host_or_url=host,
            port=port,
            protocol="http",
            timeout=60.0,
            verify_ssl=False
        )
        
        # Setup memory cache for development
        await client.cache_manager.setup_memory_cache(
            name="dev_cache",
            max_size=500,
            strategy="ttl"
        )
        
        # Authenticate
        await client.login(database, username, password)
        
        return client
    
    @staticmethod
    async def create_testing_client() -> ZenooClient:
        """Create a client for testing with mocked transport."""
        from tests.helpers.memory_transport import MemoryTransport
        
        client = ZenooClient("http://test.odoo.com")
        client._transport = MemoryTransport()
        
        # Mock authentication
        client._session.uid = 1
        client._session.database = "test_db"
        client._session.password = "test_password"
        
        return client

class ServiceFactory:
    """Factory for creating service layer objects."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.batch_manager = BatchManager(client=client)
        self.transaction_manager = TransactionManager(client)
    
    def create_customer_service(self) -> CustomerService:
        """Create a customer service instance."""
        partner_repo = PartnerRepository(self.client)
        return CustomerService(
            partner_repository=partner_repo,
            transaction_manager=self.transaction_manager,
            batch_manager=self.batch_manager
        )
    
    def create_partner_repository(self) -> PartnerRepository:
        """Create a partner repository instance."""
        return PartnerRepository(self.client)
```

## Usage Example

### Complete Application Structure

```python
import asyncio
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerManagementApp:
    """Complete customer management application using design patterns."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[ZenooClient] = None
        self.service_factory: Optional[ServiceFactory] = None
        self.customer_service: Optional[CustomerService] = None
    
    async def startup(self):
        """Initialize the application."""
        try:
            # Create client using factory
            if self.config.get("environment") == "production":
                self.client = await ZenooClientFactory.create_production_client(
                    host=self.config["host"],
                    database=self.config["database"],
                    username=self.config["username"],
                    password=self.config["password"]
                )
            else:
                self.client = await ZenooClientFactory.create_development_client(
                    host=self.config.get("host", "localhost"),
                    database=self.config.get("database", "demo"),
                    username=self.config.get("username", "admin"),
                    password=self.config.get("password", "admin")
                )
            
            # Create services using factory
            self.service_factory = ServiceFactory(self.client)
            self.customer_service = self.service_factory.create_customer_service()
            
            logger.info("Application started successfully")
            
        except Exception as e:
            logger.error(f"Application startup failed: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup application resources."""
        if self.client:
            await self.client.close()
        logger.info("Application shutdown complete")
    
    async def create_sample_customers(self):
        """Create sample customers using the service layer."""
        customers = [
            CustomerCreationRequest(
                name="ACME Corporation",
                email="contact@acme.com",
                phone="+1-555-0123",
                website="https://acme.com",
                country_code="US",
                categories=["Technology", "Enterprise"]
            ),
            CustomerCreationRequest(
                name="Global Solutions Ltd",
                email="info@globalsolutions.com",
                website="https://globalsolutions.com",
                country_code="GB",
                categories=["Consulting"]
            )
        ]
        
        # Bulk create customers
        results = await self.customer_service.bulk_create_customers(customers)
        
        logger.info(f"Created {len(results['successful'])} customers")
        for success in results["successful"]:
            logger.info(f"- {success['request'].name} (ID: {success['customer_id']})")
        
        if results["failed"]:
            logger.warning(f"Failed to create {len(results['failed'])} customers")
            for failure in results["failed"]:
                logger.warning(f"- {failure['request'].name}: {failure['error']}")

async def main():
    """Main application entry point."""
    config = {
        "environment": "development",
        "host": "localhost",
        "database": "demo",
        "username": "admin",
        "password": "admin"
    }
    
    app = CustomerManagementApp(config)
    
    try:
        await app.startup()
        await app.create_sample_customers()
    finally:
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Benefits

### 1. **Separation of Concerns**
- Repository handles data access
- Service layer contains business logic
- Factory manages object creation

### 2. **Testability**
- Easy to mock repositories and services
- Clear interfaces for testing
- Dependency injection support

### 3. **Maintainability**
- Clear code organization
- Reusable components
- Easy to extend and modify

### 4. **Scalability**
- Modular architecture
- Easy to add new features
- Performance optimization points

## Next Steps

- Explore [Integration Patterns](../integrations/index.md) for external system integration
- Check [Real-World Examples](../real-world/index.md) for complete applications
- Learn [Advanced Patterns](advanced-patterns.md) for complex scenarios
