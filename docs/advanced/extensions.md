# Extension Points

Comprehensive guide to extending Zenoo RPC with custom field types, model extensions, middleware, hooks, custom backends, and plugin architecture for building tailored solutions.

## Overview

Zenoo RPC provides multiple extension points for customization:

- **Custom Field Types**: Create specialized field types for domain-specific data
- **Model Extensions**: Extend existing models with additional functionality
- **Middleware System**: Add cross-cutting concerns and request processing
- **Hook System**: Inject custom logic at specific execution points
- **Custom Backends**: Implement custom cache, transport, or storage backends
- **Plugin Architecture**: Build reusable extensions and integrations

## Custom Field Types

### Creating Custom Fields

```python
from typing import Any, Optional, Type
from pydantic import Field, validator
from pydantic.fields import FieldInfo
from decimal import Decimal
import re

def EmailField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create an Email field with validation."""
    return Field(
        default=None,
        description=description,
        json_schema_extra={
            "odoo_type": "char",
            "odoo_size": 254,
            "format": "email",
            **kwargs
        }
    )

def PhoneField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Phone field with validation."""
    return Field(
        default=None,
        description=description,
        json_schema_extra={
            "odoo_type": "char",
            "odoo_size": 32,
            "format": "phone",
            **kwargs
        }
    )

def CurrencyField(
    precision: int = 2,
    currency_field: str = "currency_id",
    description: str = "",
    **kwargs: Any
) -> FieldInfo:
    """Create a Currency field with precision control."""
    return Field(
        default=Decimal("0.00"),
        description=description,
        json_schema_extra={
            "odoo_type": "monetary",
            "odoo_currency_field": currency_field,
            "precision": precision,
            **kwargs
        }
    )

def URLField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a URL field with validation."""
    return Field(
        default=None,
        description=description,
        json_schema_extra={
            "odoo_type": "char",
            "odoo_size": 1024,
            "format": "url",
            **kwargs
        }
    )

# Advanced custom field with validation
def VATField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a VAT number field with validation."""
    return Field(
        default=None,
        description=description,
        json_schema_extra={
            "odoo_type": "char",
            "odoo_size": 32,
            "format": "vat",
            **kwargs
        }
    )
```

### Field Validation Extensions

```python
from pydantic import BaseModel, validator
from typing import Optional

class ExtendedValidationMixin:
    """Mixin for extended field validation."""
    
    @validator("email", pre=True, always=True)
    def validate_email(cls, v):
        """Enhanced email validation."""
        if v is None or v == "":
            return None
        
        # Basic email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        
        # Check for common typos
        common_domains = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com"
        }
        domain = v.split("@")[1].lower()
        
        # Suggest corrections for common typos
        if domain.endswith(".co") and f"{domain}m" in common_domains:
            raise ValueError(f"Did you mean {domain}m?")
        
        return v.lower().strip()
    
    @validator("phone", pre=True, always=True)
    def validate_phone(cls, v):
        """Enhanced phone validation."""
        if v is None or v == "":
            return None
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Basic phone validation
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError("Phone number must be 7-15 digits")
        
        return cleaned
    
    @validator("vat", pre=True, always=True)
    def validate_vat(cls, v):
        """Enhanced VAT validation."""
        if v is None or v == "":
            return None
        
        # Remove spaces and convert to uppercase
        cleaned = re.sub(r'\s+', '', v.upper())
        
        # Basic VAT format validation (country-specific can be added)
        if not re.match(r'^[A-Z]{2}[A-Z0-9]+$', cleaned):
            raise ValueError("VAT must start with 2-letter country code")
        
        return cleaned

# Usage in models
class EnhancedPartner(OdooModel, ExtendedValidationMixin):
    """Partner model with enhanced validation."""
    
    _odoo_name: ClassVar[str] = "res.partner"
    
    name: str
    email: Optional[str] = EmailField(description="Email address")
    phone: Optional[str] = PhoneField(description="Phone number")
    website: Optional[str] = URLField(description="Website URL")
    vat: Optional[str] = VATField(description="VAT number")
```

## Model Extensions

### Extending Existing Models

```python
from zenoo_rpc.models.common import ResPartner
from typing import List, Optional, Dict, Any

class ExtendedPartner(ResPartner):
    """Extended partner with additional functionality."""
    
    # Add computed properties
    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        if self.is_company:
            return self.name
        return f"{self.name} ({self.parent_id.name})" if self.parent_id else self.name
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [
            self.street,
            self.street2,
            f"{self.zip} {self.city}" if self.zip and self.city else self.city,
            self.state_id.name if self.state_id else None,
            self.country_id.name if self.country_id else None
        ]
        return ", ".join(filter(None, parts))
    
    # Add business logic methods
    async def get_orders(self, client: "ZenooClient", state: Optional[str] = None) -> List[Dict]:
        """Get all orders for this partner."""
        if not self.id:
            return []
        
        domain = [("partner_id", "=", self.id)]
        if state:
            domain.append(("state", "=", state))
        
        return await client.search_read("sale.order", domain)
    
    async def get_invoices(self, client: "ZenooClient", state: Optional[str] = None) -> List[Dict]:
        """Get all invoices for this partner."""
        if not self.id:
            return []
        
        domain = [("partner_id", "=", self.id)]
        if state:
            domain.append(("state", "=", state))
        
        return await client.search_read("account.move", domain)
    
    async def calculate_total_sales(self, client: "ZenooClient") -> Decimal:
        """Calculate total sales for this partner."""
        orders = await self.get_orders(client, state="sale")
        return sum(Decimal(str(order.get("amount_total", 0))) for order in orders)
    
    def to_vcard(self) -> str:
        """Export partner as vCard format."""
        vcard_lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{self.name}",
            f"ORG:{self.name}" if self.is_company else f"ORG:{self.parent_id.name if self.parent_id else ''}",
        ]
        
        if self.email:
            vcard_lines.append(f"EMAIL:{self.email}")
        
        if self.phone:
            vcard_lines.append(f"TEL:{self.phone}")
        
        if self.website:
            vcard_lines.append(f"URL:{self.website}")
        
        # Address
        if any([self.street, self.city, self.zip, self.country_id]):
            addr_parts = [
                self.street or "",
                self.city or "",
                self.state_id.name if self.state_id else "",
                self.zip or "",
                self.country_id.name if self.country_id else ""
            ]
            vcard_lines.append(f"ADR:;;{';'.join(addr_parts)}")
        
        vcard_lines.append("END:VCARD")
        return "\n".join(vcard_lines)

# Model factory for extensions
class ModelExtensionFactory:
    """Factory for creating extended models."""
    
    _extensions: Dict[str, Type[OdooModel]] = {}
    
    @classmethod
    def register_extension(cls, odoo_name: str, extended_class: Type[OdooModel]):
        """Register a model extension."""
        cls._extensions[odoo_name] = extended_class
    
    @classmethod
    def get_extended_model(cls, odoo_name: str) -> Optional[Type[OdooModel]]:
        """Get extended model class if available."""
        return cls._extensions.get(odoo_name)
    
    @classmethod
    def create_instance(cls, odoo_name: str, data: Dict[str, Any]) -> OdooModel:
        """Create instance using extended model if available."""
        extended_class = cls.get_extended_model(odoo_name)
        if extended_class:
            return extended_class(**data)
        
        # Fallback to base model
        base_class = get_model_class(odoo_name)
        return base_class(**data)

# Register extensions
ModelExtensionFactory.register_extension("res.partner", ExtendedPartner)
```

### Dynamic Model Generation

```python
from typing import Dict, Any, Type
from pydantic import create_model

class DynamicModelBuilder:
    """Build models dynamically based on Odoo field definitions."""
    
    def __init__(self, client: "ZenooClient"):
        self.client = client
        self._field_type_mapping = {
            "char": str,
            "text": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "date": date,
            "datetime": datetime,
            "many2one": int,
            "one2many": List[int],
            "many2many": List[int],
        }
    
    async def build_model_from_odoo(self, model_name: str) -> Type[OdooModel]:
        """Build a model class from Odoo field definitions."""
        
        # Get field definitions from Odoo
        fields_info = await self.client.call(
            "object", "execute_kw",
            self.client.database, self.client.uid, self.client.password,
            model_name, "fields_get", []
        )
        
        # Build field definitions
        field_definitions = {}
        annotations = {}
        
        for field_name, field_info in fields_info.items():
            field_type = field_info.get("type", "char")
            python_type = self._field_type_mapping.get(field_type, str)
            
            # Handle optional fields
            if not field_info.get("required", False):
                python_type = Optional[python_type]
            
            annotations[field_name] = python_type
            
            # Create field with metadata
            field_definitions[field_name] = Field(
                default=None if not field_info.get("required") else ...,
                description=field_info.get("string", ""),
                json_schema_extra={
                    "odoo_type": field_type,
                    "odoo_required": field_info.get("required", False),
                    "odoo_readonly": field_info.get("readonly", False),
                }
            )
        
        # Add class variables
        field_definitions["_odoo_name"] = model_name
        field_definitions["__annotations__"] = annotations
        
        # Create dynamic model class
        model_class = create_model(
            f"Dynamic{model_name.replace('.', '').title()}",
            __base__=OdooModel,
            **field_definitions
        )
        
        return model_class
```

## Middleware System

### Request/Response Middleware

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
import time
import logging

class Middleware(ABC):
    """Base middleware class."""
    
    @abstractmethod
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request before sending to Odoo."""
        pass
    
    @abstractmethod
    async def process_response(self, response_data: Any, request_data: Dict[str, Any]) -> Any:
        """Process response after receiving from Odoo."""
        pass

class LoggingMiddleware(Middleware):
    """Middleware for request/response logging."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log request details."""
        self.logger.info(f"RPC Request: {request_data.get('method')} - {request_data.get('model')}")
        self.logger.debug(f"Request data: {request_data}")
        
        # Add timestamp
        request_data["_middleware_start_time"] = time.time()
        return request_data
    
    async def process_response(self, response_data: Any, request_data: Dict[str, Any]) -> Any:
        """Log response details."""
        start_time = request_data.get("_middleware_start_time", time.time())
        duration = time.time() - start_time
        
        self.logger.info(f"RPC Response: {request_data.get('method')} completed in {duration:.3f}s")
        
        if isinstance(response_data, dict) and "error" in response_data:
            self.logger.error(f"RPC Error: {response_data['error']}")
        
        return response_data

class CachingMiddleware(Middleware):
    """Middleware for automatic caching."""
    
    def __init__(self, cache_manager: "CacheManager"):
        self.cache_manager = cache_manager
        self.cacheable_methods = {"search", "search_read", "read", "search_count"}
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check cache before request."""
        method = request_data.get("method")
        
        if method in self.cacheable_methods:
            cache_key = self._generate_cache_key(request_data)
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result is not None:
                request_data["_cached_result"] = cached_result
                request_data["_cache_hit"] = True
        
        return request_data
    
    async def process_response(self, response_data: Any, request_data: Dict[str, Any]) -> Any:
        """Cache response if applicable."""
        if request_data.get("_cache_hit"):
            return request_data["_cached_result"]
        
        method = request_data.get("method")
        
        if method in self.cacheable_methods and not isinstance(response_data, dict) or "error" not in response_data:
            cache_key = self._generate_cache_key(request_data)
            await self.cache_manager.set(cache_key, response_data, ttl=300)
        
        return response_data
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key from request data."""
        key_parts = [
            request_data.get("model", ""),
            request_data.get("method", ""),
            str(hash(str(request_data.get("args", []))))
        ]
        return ":".join(key_parts)

class SecurityMiddleware(Middleware):
    """Middleware for security checks."""
    
    def __init__(self):
        self.blocked_methods = {"unlink"}  # Dangerous methods
        self.rate_limiter = {}
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security checks."""
        method = request_data.get("method")
        model = request_data.get("model")
        
        # Check for blocked methods
        if method in self.blocked_methods:
            raise SecurityError(f"Method {method} is blocked by security policy")
        
        # Rate limiting (simplified)
        client_id = request_data.get("client_id", "unknown")
        current_time = time.time()
        
        if client_id not in self.rate_limiter:
            self.rate_limiter[client_id] = []
        
        # Clean old requests (last minute)
        self.rate_limiter[client_id] = [
            req_time for req_time in self.rate_limiter[client_id]
            if current_time - req_time < 60
        ]
        
        # Check rate limit (100 requests per minute)
        if len(self.rate_limiter[client_id]) >= 100:
            raise SecurityError("Rate limit exceeded")
        
        self.rate_limiter[client_id].append(current_time)
        
        return request_data
    
    async def process_response(self, response_data: Any, request_data: Dict[str, Any]) -> Any:
        """Process response for security."""
        # Could add response filtering here
        return response_data

# Middleware manager
class MiddlewareManager:
    """Manage middleware stack."""
    
    def __init__(self):
        self.middlewares: List[Middleware] = []
    
    def add_middleware(self, middleware: Middleware):
        """Add middleware to the stack."""
        self.middlewares.append(middleware)
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through middleware stack."""
        for middleware in self.middlewares:
            request_data = await middleware.process_request(request_data)
        return request_data
    
    async def process_response(self, response_data: Any, request_data: Dict[str, Any]) -> Any:
        """Process response through middleware stack (reverse order)."""
        for middleware in reversed(self.middlewares):
            response_data = await middleware.process_response(response_data, request_data)
        return response_data
```

## Hook System

### Event Hooks

```python
from typing import Callable, List, Dict, Any
from enum import Enum

class HookEvent(Enum):
    """Available hook events."""
    BEFORE_REQUEST = "before_request"
    AFTER_REQUEST = "after_request"
    BEFORE_CREATE = "before_create"
    AFTER_CREATE = "after_create"
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE = "after_update"
    BEFORE_DELETE = "before_delete"
    AFTER_DELETE = "after_delete"
    ON_ERROR = "on_error"
    ON_CACHE_HIT = "on_cache_hit"
    ON_CACHE_MISS = "on_cache_miss"

class HookManager:
    """Manage event hooks."""
    
    def __init__(self):
        self.hooks: Dict[HookEvent, List[Callable]] = {event: [] for event in HookEvent}
    
    def register_hook(self, event: HookEvent, callback: Callable):
        """Register a hook callback."""
        self.hooks[event].append(callback)
    
    def unregister_hook(self, event: HookEvent, callback: Callable):
        """Unregister a hook callback."""
        if callback in self.hooks[event]:
            self.hooks[event].remove(callback)
    
    async def trigger_hook(self, event: HookEvent, *args, **kwargs):
        """Trigger all callbacks for an event."""
        results = []
        for callback in self.hooks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(*args, **kwargs)
                else:
                    result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logging.error(f"Hook callback error for {event}: {e}")
        return results

# Hook decorators
def hook(event: HookEvent):
    """Decorator to register a function as a hook."""
    def decorator(func: Callable):
        # Register with global hook manager
        hook_manager.register_hook(event, func)
        return func
    return decorator

# Global hook manager instance
hook_manager = HookManager()

# Example hooks
@hook(HookEvent.BEFORE_CREATE)
async def validate_partner_data(model: str, data: Dict[str, Any]):
    """Validate partner data before creation."""
    if model == "res.partner":
        if not data.get("name"):
            raise ValueError("Partner name is required")
        
        # Additional validation logic
        if data.get("email") and "@" not in data["email"]:
            raise ValueError("Invalid email format")

@hook(HookEvent.AFTER_CREATE)
async def log_partner_creation(model: str, record_id: int, data: Dict[str, Any]):
    """Log partner creation."""
    if model == "res.partner":
        logging.info(f"Created partner {record_id}: {data.get('name')}")

@hook(HookEvent.ON_ERROR)
async def handle_rpc_error(error: Exception, request_data: Dict[str, Any]):
    """Handle RPC errors."""
    logging.error(f"RPC Error: {error} for request: {request_data}")
    
    # Could send to monitoring system
    # await send_to_monitoring(error, request_data)
```

## Custom Backends

### Custom Cache Backend

```python
from zenoo_rpc.cache.backends import CacheBackend
import aiofiles
import json
import os
from pathlib import Path

class FileCacheBackend(CacheBackend):
    """File-based cache backend."""
    
    def __init__(self, cache_dir: str = "/tmp/zenoo_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    async def get(self, key: str) -> Any:
        """Get value from file cache."""
        file_path = self.cache_dir / f"{key}.json"
        
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
            
            # Check TTL
            if data.get("expires_at") and time.time() > data["expires_at"]:
                await self.delete(key)
                return None
            
            return data["value"]
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in file cache."""
        file_path = self.cache_dir / f"{key}.json"
        
        data = {
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + ttl if ttl else None
        }
        
        try:
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(data, default=str))
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from file cache."""
        file_path = self.cache_dir / f"{key}.json"
        
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception:
            return False
    
    async def clear(self) -> bool:
        """Clear all cached values."""
        try:
            for file_path in self.cache_dir.glob("*.json"):
                file_path.unlink()
            return True
        except Exception:
            return False

# Custom transport backend
class CustomTransport:
    """Custom transport with additional features."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_pool = {}
    
    async def json_rpc_call(self, service: str, method: str, params: Dict[str, Any]) -> Any:
        """Custom RPC call with additional features."""
        
        # Add custom headers
        headers = {
            "X-Custom-Client": "ZenooRPC",
            "X-Request-ID": str(uuid.uuid4())
        }
        
        # Custom request processing
        request_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": params
            },
            "id": 1
        }
        
        # Add custom logic here
        # - Request signing
        # - Compression
        # - Custom authentication
        
        # Make actual request (simplified)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/jsonrpc",
                json=request_data,
                headers=headers
            )
            
            return response.json()
```

## Plugin Architecture

### Plugin System

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import importlib
import pkgutil

class Plugin(ABC):
    """Base plugin class."""
    
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    
    @abstractmethod
    async def initialize(self, client: "ZenooClient") -> None:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get plugin information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description
        }

class PluginManager:
    """Manage plugins."""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_paths: List[str] = []
    
    def add_plugin_path(self, path: str):
        """Add a path to search for plugins."""
        self.plugin_paths.append(path)
    
    def register_plugin(self, plugin: Plugin):
        """Register a plugin instance."""
        self.plugins[plugin.name] = plugin
    
    def discover_plugins(self):
        """Discover plugins in plugin paths."""
        for path in self.plugin_paths:
            for finder, name, ispkg in pkgutil.iter_modules([path]):
                try:
                    module = importlib.import_module(name)
                    
                    # Look for Plugin classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, Plugin) and 
                            attr != Plugin):
                            plugin_instance = attr()
                            self.register_plugin(plugin_instance)
                            
                except Exception as e:
                    logging.error(f"Failed to load plugin {name}: {e}")
    
    async def initialize_all(self, client: "ZenooClient"):
        """Initialize all registered plugins."""
        for plugin in self.plugins.values():
            try:
                await plugin.initialize(client)
                logging.info(f"Initialized plugin: {plugin.name}")
            except Exception as e:
                logging.error(f"Failed to initialize plugin {plugin.name}: {e}")
    
    async def cleanup_all(self):
        """Cleanup all plugins."""
        for plugin in self.plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                logging.error(f"Failed to cleanup plugin {plugin.name}: {e}")
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[Dict[str, str]]:
        """List all registered plugins."""
        return [plugin.get_info() for plugin in self.plugins.values()]

# Example plugins
class AuditLogPlugin(Plugin):
    """Plugin for audit logging."""
    
    name = "audit_log"
    version = "1.0.0"
    description = "Audit logging for all RPC operations"
    
    def __init__(self):
        self.log_file = None
    
    async def initialize(self, client: "ZenooClient") -> None:
        """Initialize audit logging."""
        self.log_file = open("audit.log", "a")
        
        # Register hooks
        hook_manager.register_hook(HookEvent.AFTER_CREATE, self.log_create)
        hook_manager.register_hook(HookEvent.AFTER_UPDATE, self.log_update)
        hook_manager.register_hook(HookEvent.AFTER_DELETE, self.log_delete)
    
    async def cleanup(self) -> None:
        """Cleanup audit logging."""
        if self.log_file:
            self.log_file.close()
    
    async def log_create(self, model: str, record_id: int, data: Dict[str, Any]):
        """Log create operations."""
        log_entry = f"{time.time()}: CREATE {model} {record_id} {data}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()
    
    async def log_update(self, model: str, record_id: int, data: Dict[str, Any]):
        """Log update operations."""
        log_entry = f"{time.time()}: UPDATE {model} {record_id} {data}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()
    
    async def log_delete(self, model: str, record_id: int):
        """Log delete operations."""
        log_entry = f"{time.time()}: DELETE {model} {record_id}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()

class MetricsPlugin(Plugin):
    """Plugin for metrics collection."""
    
    name = "metrics"
    version = "1.0.0"
    description = "Collect performance and usage metrics"
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_by_model": {},
            "response_times": [],
            "errors_total": 0
        }
    
    async def initialize(self, client: "ZenooClient") -> None:
        """Initialize metrics collection."""
        hook_manager.register_hook(HookEvent.BEFORE_REQUEST, self.start_timer)
        hook_manager.register_hook(HookEvent.AFTER_REQUEST, self.record_metrics)
        hook_manager.register_hook(HookEvent.ON_ERROR, self.record_error)
    
    async def cleanup(self) -> None:
        """Cleanup metrics collection."""
        # Could export metrics to file or monitoring system
        pass
    
    async def start_timer(self, request_data: Dict[str, Any]):
        """Start timing request."""
        request_data["_metrics_start_time"] = time.time()
    
    async def record_metrics(self, response_data: Any, request_data: Dict[str, Any]):
        """Record request metrics."""
        self.metrics["requests_total"] += 1
        
        model = request_data.get("model", "unknown")
        self.metrics["requests_by_model"][model] = (
            self.metrics["requests_by_model"].get(model, 0) + 1
        )
        
        start_time = request_data.get("_metrics_start_time")
        if start_time:
            response_time = time.time() - start_time
            self.metrics["response_times"].append(response_time)
    
    async def record_error(self, error: Exception, request_data: Dict[str, Any]):
        """Record error metrics."""
        self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_response_time = (
            sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            if self.metrics["response_times"] else 0
        )
        
        return {
            **self.metrics,
            "avg_response_time": avg_response_time
        }
```

## Integration Examples

### Complete Extension Setup

```python
async def setup_extended_client():
    """Setup client with all extensions."""
    
    # Create client
    client = ZenooClient("localhost", port=8069)
    
    # Setup middleware
    middleware_manager = MiddlewareManager()
    middleware_manager.add_middleware(LoggingMiddleware())
    middleware_manager.add_middleware(SecurityMiddleware())
    middleware_manager.add_middleware(CachingMiddleware(client.cache_manager))
    
    # Setup plugins
    plugin_manager = PluginManager()
    plugin_manager.register_plugin(AuditLogPlugin())
    plugin_manager.register_plugin(MetricsPlugin())
    
    await plugin_manager.initialize_all(client)
    
    # Register custom backends
    await client.cache_manager.register_backend("file", FileCacheBackend())
    
    # Setup hooks
    @hook(HookEvent.BEFORE_CREATE)
    async def custom_validation(model: str, data: Dict[str, Any]):
        """Custom validation logic."""
        # Your validation logic here
        pass
    
    return client, middleware_manager, plugin_manager

# Usage
client, middleware, plugins = await setup_extended_client()

# Use extended models
partner = ExtendedPartner(name="Test Company", is_company=True)
vcard = partner.to_vcard()

# Get metrics
metrics_plugin = plugins.get_plugin("metrics")
current_metrics = metrics_plugin.get_metrics()
```

## Best Practices

### 1. Extension Design
- Keep extensions focused and single-purpose
- Use dependency injection for better testability
- Implement proper error handling and logging
- Follow the plugin interface contracts

### 2. Performance Considerations
- Minimize overhead in middleware and hooks
- Use async patterns consistently
- Cache expensive operations
- Profile extension performance impact

### 3. Security
- Validate all extension inputs
- Use secure defaults
- Implement proper access controls
- Audit extension behavior

### 4. Maintainability
- Document extension APIs clearly
- Use type hints throughout
- Write comprehensive tests
- Version extensions properly

## Next Steps

- Review [Architecture Overview](architecture.md) for integration patterns
- Explore [Performance Optimization](performance.md) for extension performance
- Check [Security Considerations](security.md) for secure extensions
- Learn about [Monitoring Setup](../troubleshooting/monitoring.md) for extension monitoring
