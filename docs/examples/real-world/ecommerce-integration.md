# E-commerce Integration

Complete guide for integrating Odoo with e-commerce platforms using Zenoo RPC.

## Overview

This example demonstrates how to:
- Sync products between Odoo and e-commerce platforms
- Process orders from online stores
- Manage inventory across multiple channels
- Handle customer data synchronization

## Implementation

```python
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ProductProduct, SaleOrder, ResPartner

class EcommerceIntegration:
    """E-commerce platform integration with Odoo."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def sync_products_to_ecommerce(self) -> List[Dict[str, Any]]:
        """Sync Odoo products to e-commerce platform."""
        
        # Get published products from Odoo
        products = await self.client.model(ProductProduct).filter(
            sale_ok=True,
            active=True,
            website_published=True
        ).only(
            "name", "default_code", "list_price", 
            "description_sale", "qty_available"
        ).all()
        
        synced_products = []
        
        for product in products:
            ecommerce_product = {
                "sku": product.default_code or f"PROD_{product.id}",
                "name": product.name,
                "price": float(product.list_price),
                "description": product.description_sale or "",
                "stock_quantity": int(product.qty_available),
                "status": "active" if product.qty_available > 0 else "out_of_stock"
            }
            
            # Sync to e-commerce platform (implementation depends on platform)
            await self._sync_to_platform(ecommerce_product)
            synced_products.append(ecommerce_product)
        
        return synced_products
    
    async def process_ecommerce_order(self, order_data: Dict[str, Any]) -> int:
        """Process an order from e-commerce platform."""
        
        # Find or create customer
        customer = await self._find_or_create_customer(order_data["customer"])
        
        # Create sale order
        order_vals = {
            "partner_id": customer.id,
            "date_order": datetime.now(),
            "origin": f"Ecommerce Order #{order_data['order_number']}",
            "note": order_data.get("notes", "")
        }
        
        order = await self.client.model(SaleOrder).create(order_vals)
        
        # Add order lines
        for item in order_data["items"]:
            await self._create_order_line(order.id, item)
        
        # Confirm order if payment is completed
        if order_data.get("payment_status") == "paid":
            await order.action_confirm()
        
        return order.id
    
    async def _find_or_create_customer(self, customer_data: Dict[str, Any]) -> ResPartner:
        """Find existing customer or create new one."""
        
        # Try to find by email
        existing = await self.client.model(ResPartner).filter(
            email=customer_data["email"]
        ).first()
        
        if existing:
            return existing
        
        # Create new customer
        customer_vals = {
            "name": customer_data["name"],
            "email": customer_data["email"],
            "phone": customer_data.get("phone"),
            "street": customer_data.get("address", {}).get("street"),
            "city": customer_data.get("address", {}).get("city"),
            "zip": customer_data.get("address", {}).get("zip"),
            "customer_rank": 1,
            "is_company": False
        }
        
        return await self.client.model(ResPartner).create(customer_vals)
    
    async def _create_order_line(self, order_id: int, item_data: Dict[str, Any]):
        """Create order line for product."""
        
        # Find product by SKU
        product = await self.client.model(ProductProduct).filter(
            default_code=item_data["sku"]
        ).first()
        
        if not product:
            raise ValueError(f"Product not found: {item_data['sku']}")
        
        line_vals = {
            "order_id": order_id,
            "product_id": product.id,
            "product_uom_qty": item_data["quantity"],
            "price_unit": item_data["price"]
        }
        
        await self.client.model("sale.order.line").create(line_vals)
    
    async def _sync_to_platform(self, product_data: Dict[str, Any]):
        """Sync product to e-commerce platform."""
        # Implementation depends on specific platform API
        # This is a placeholder for the actual sync logic
        print(f"Syncing product: {product_data['name']}")

# Usage Example
async def main():
    """Demonstrate e-commerce integration."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        integration = EcommerceIntegration(client)
        
        # Sync products to e-commerce
        products = await integration.sync_products_to_ecommerce()
        print(f"Synced {len(products)} products")
        
        # Process incoming order
        sample_order = {
            "order_number": "EC001",
            "customer": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "zip": "10001"
                }
            },
            "items": [
                {
                    "sku": "PROD_1",
                    "quantity": 2,
                    "price": 29.99
                }
            ],
            "payment_status": "paid",
            "notes": "Express delivery requested"
        }
        
        order_id = await integration.process_ecommerce_order(sample_order)
        print(f"Created order: {order_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Platform-Specific Integrations

### Shopify Integration

```python
import shopify

class ShopifyIntegration(EcommerceIntegration):
    """Shopify-specific integration."""
    
    def __init__(self, client: ZenooClient, shop_url: str, access_token: str):
        super().__init__(client)
        shopify.ShopifyResource.set_site(shop_url)
        shopify.ShopifyResource.set_headers({"X-Shopify-Access-Token": access_token})
    
    async def _sync_to_platform(self, product_data: Dict[str, Any]):
        """Sync product to Shopify."""
        
        shopify_product = shopify.Product()
        shopify_product.title = product_data["name"]
        shopify_product.body_html = product_data["description"]
        
        variant = shopify.Variant()
        variant.price = product_data["price"]
        variant.sku = product_data["sku"]
        variant.inventory_quantity = product_data["stock_quantity"]
        
        shopify_product.variants = [variant]
        shopify_product.save()
```

### WooCommerce Integration

```python
from woocommerce import API

class WooCommerceIntegration(EcommerceIntegration):
    """WooCommerce-specific integration."""
    
    def __init__(self, client: ZenooClient, wc_api: API):
        super().__init__(client)
        self.wc_api = wc_api
    
    async def _sync_to_platform(self, product_data: Dict[str, Any]):
        """Sync product to WooCommerce."""
        
        wc_product = {
            "name": product_data["name"],
            "type": "simple",
            "regular_price": str(product_data["price"]),
            "description": product_data["description"],
            "sku": product_data["sku"],
            "manage_stock": True,
            "stock_quantity": product_data["stock_quantity"],
            "in_stock": product_data["status"] == "active"
        }
        
        self.wc_api.post("products", wc_product)
```

## Webhook Handling

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/order")
async def handle_order_webhook(request: Request):
    """Handle incoming order webhook."""
    
    order_data = await request.json()
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        integration = EcommerceIntegration(client)
        order_id = await integration.process_ecommerce_order(order_data)
        
        return {"status": "success", "order_id": order_id}
```

## Best Practices

1. **Error Handling**: Always handle API failures gracefully
2. **Rate Limiting**: Respect platform API rate limits
3. **Data Validation**: Validate all incoming data
4. **Logging**: Log all sync operations for debugging
5. **Testing**: Test with sandbox environments first

## Next Steps

- [Inventory Management](inventory-management.md) - Advanced inventory sync
- [Customer Management](customer-management.md) - Customer data handling
- [Webhook Handlers](webhook-handlers.md) - Advanced webhook processing
