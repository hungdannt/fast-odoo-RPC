# Advanced Patterns

Advanced design patterns and best practices for Zenoo RPC applications.

## Overview

This document covers:
- Repository pattern implementation
- Factory pattern for model creation
- Observer pattern for event handling
- Strategy pattern for business logic
- Decorator pattern for cross-cutting concerns

## Repository Pattern

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

class PartnerRepository(ABC):
    """Abstract repository for partner operations."""
    
    @abstractmethod
    async def find_by_id(self, partner_id: int) -> Optional[ResPartner]:
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[ResPartner]:
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> ResPartner:
        pass
    
    @abstractmethod
    async def update(self, partner_id: int, data: Dict[str, Any]) -> ResPartner:
        pass

class OdooPartnerRepository(PartnerRepository):
    """Odoo implementation of partner repository."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def find_by_id(self, partner_id: int) -> Optional[ResPartner]:
        return await self.client.model(ResPartner).filter(id=partner_id).first()
    
    async def find_by_email(self, email: str) -> Optional[ResPartner]:
        return await self.client.model(ResPartner).filter(email=email).first()
    
    async def create(self, data: Dict[str, Any]) -> ResPartner:
        return await self.client.model(ResPartner).create(data)
    
    async def update(self, partner_id: int, data: Dict[str, Any]) -> ResPartner:
        partner = await self.find_by_id(partner_id)
        if partner:
            await partner.update(data)
            return partner
        raise ValueError(f"Partner {partner_id} not found")
```

## Factory Pattern

```python
from typing import Type, Dict, Any
from zenoo_rpc.models.base import OdooModel

class ModelFactory:
    """Factory for creating model instances."""
    
    _models: Dict[str, Type[OdooModel]] = {}
    
    @classmethod
    def register_model(cls, model_name: str, model_class: Type[OdooModel]):
        """Register a model class."""
        cls._models[model_name] = model_class
    
    @classmethod
    def create_model(cls, model_name: str, client: ZenooClient) -> OdooModel:
        """Create model instance."""
        if model_name not in cls._models:
            raise ValueError(f"Model {model_name} not registered")
        
        return cls._models[model_name](client)

# Usage
ModelFactory.register_model("res.partner", ResPartner)
partner_model = ModelFactory.create_model("res.partner", client)
```

## Observer Pattern

```python
from typing import List, Callable, Any
from abc import ABC, abstractmethod

class Observer(ABC):
    """Abstract observer interface."""
    
    @abstractmethod
    async def update(self, event: str, data: Any):
        pass

class Subject:
    """Subject that notifies observers."""
    
    def __init__(self):
        self._observers: List[Observer] = []
    
    def attach(self, observer: Observer):
        """Attach an observer."""
        self._observers.append(observer)
    
    def detach(self, observer: Observer):
        """Detach an observer."""
        self._observers.remove(observer)
    
    async def notify(self, event: str, data: Any):
        """Notify all observers."""
        for observer in self._observers:
            await observer.update(event, data)

class PartnerService(Subject):
    """Partner service with event notifications."""
    
    def __init__(self, repository: PartnerRepository):
        super().__init__()
        self.repository = repository
    
    async def create_partner(self, data: Dict[str, Any]) -> ResPartner:
        """Create partner and notify observers."""
        partner = await self.repository.create(data)
        await self.notify("partner_created", partner)
        return partner

class EmailNotificationObserver(Observer):
    """Observer for email notifications."""
    
    async def update(self, event: str, data: Any):
        if event == "partner_created":
            print(f"Sending welcome email to {data.email}")
```

## Strategy Pattern

```python
from abc import ABC, abstractmethod

class PricingStrategy(ABC):
    """Abstract pricing strategy."""
    
    @abstractmethod
    def calculate_price(self, base_price: float, quantity: int) -> float:
        pass

class StandardPricing(PricingStrategy):
    """Standard pricing strategy."""
    
    def calculate_price(self, base_price: float, quantity: int) -> float:
        return base_price * quantity

class BulkDiscountPricing(PricingStrategy):
    """Bulk discount pricing strategy."""
    
    def __init__(self, discount_threshold: int = 10, discount_rate: float = 0.1):
        self.discount_threshold = discount_threshold
        self.discount_rate = discount_rate
    
    def calculate_price(self, base_price: float, quantity: int) -> float:
        total = base_price * quantity
        if quantity >= self.discount_threshold:
            total *= (1 - self.discount_rate)
        return total

class PricingContext:
    """Context for pricing strategies."""
    
    def __init__(self, strategy: PricingStrategy):
        self.strategy = strategy
    
    def set_strategy(self, strategy: PricingStrategy):
        self.strategy = strategy
    
    def calculate_price(self, base_price: float, quantity: int) -> float:
        return self.strategy.calculate_price(base_price, quantity)
```

## Decorator Pattern

```python
from functools import wraps
import time
import logging

def log_execution_time(func):
    """Decorator to log execution time."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        logging.info(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
        return result
    
    return wrapper

def cache_result(ttl: int = 300):
    """Decorator to cache function results."""
    
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Simple cache key generation
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            if cache_key in cache:
                cached_result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return cached_result
            
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result
        
        return wrapper
    return decorator

class EnhancedPartnerService:
    """Partner service with decorators."""
    
    def __init__(self, repository: PartnerRepository):
        self.repository = repository
    
    @log_execution_time
    @cache_result(ttl=600)
    async def get_partner_by_email(self, email: str) -> Optional[ResPartner]:
        """Get partner by email with logging and caching."""
        return await self.repository.find_by_email(email)
```

## Unit of Work Pattern

```python
from typing import List, Dict, Any
from contextlib import asynccontextmanager

class UnitOfWork:
    """Unit of Work pattern implementation."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.new_objects: List[Dict[str, Any]] = []
        self.dirty_objects: List[Dict[str, Any]] = []
        self.removed_objects: List[int] = []
    
    def register_new(self, model_name: str, data: Dict[str, Any]):
        """Register new object for creation."""
        self.new_objects.append({"model": model_name, "data": data})
    
    def register_dirty(self, model_name: str, object_id: int, data: Dict[str, Any]):
        """Register dirty object for update."""
        self.dirty_objects.append({
            "model": model_name,
            "id": object_id,
            "data": data
        })
    
    def register_removed(self, model_name: str, object_id: int):
        """Register object for removal."""
        self.removed_objects.append({"model": model_name, "id": object_id})
    
    async def commit(self):
        """Commit all changes."""
        async with self.client.batch() as batch:
            # Create new objects
            for obj in self.new_objects:
                batch.create(obj["model"], obj["data"])
            
            # Update dirty objects
            for obj in self.dirty_objects:
                batch.update(obj["model"], obj["data"], [obj["id"]])
            
            # Remove objects
            for obj in self.removed_objects:
                batch.delete(obj["model"], [obj["id"]])
            
            results = await batch.execute()
            
            # Clear collections
            self.new_objects.clear()
            self.dirty_objects.clear()
            self.removed_objects.clear()
            
            return results

@asynccontextmanager
async def unit_of_work(client: ZenooClient):
    """Context manager for unit of work."""
    uow = UnitOfWork(client)
    try:
        yield uow
        await uow.commit()
    except Exception:
        # Rollback logic here if needed
        raise
```

## Usage Examples

```python
async def main():
    """Demonstrate advanced patterns."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Repository pattern
        repo = OdooPartnerRepository(client)
        partner = await repo.find_by_email("test@example.com")
        
        # Observer pattern
        service = PartnerService(repo)
        email_observer = EmailNotificationObserver()
        service.attach(email_observer)
        
        new_partner = await service.create_partner({
            "name": "John Doe",
            "email": "john@example.com"
        })
        
        # Strategy pattern
        pricing = PricingContext(BulkDiscountPricing())
        price = pricing.calculate_price(10.0, 15)  # With bulk discount
        
        # Unit of Work pattern
        async with unit_of_work(client) as uow:
            uow.register_new("res.partner", {"name": "Jane Doe"})
            uow.register_dirty("res.partner", 1, {"phone": "+1234567890"})
            # Changes committed automatically

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

1. **Separation of Concerns**: Keep business logic separate from data access
2. **Dependency Injection**: Use dependency injection for better testability
3. **Interface Segregation**: Create focused interfaces
4. **Single Responsibility**: Each class should have one reason to change
5. **Open/Closed Principle**: Open for extension, closed for modification

## Next Steps

- [Integration Examples](../integrations/index.md) - Framework integrations
- [Real-World Examples](../real-world/index.md) - Production examples
- [API Reference](../../api-reference/index.md) - Complete API documentation
