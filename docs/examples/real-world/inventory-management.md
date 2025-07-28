# Inventory Management

Real-time inventory tracking and management system using Zenoo RPC.

## Overview

This example demonstrates:
- Real-time inventory tracking
- Stock level monitoring
- Automated reordering
- Multi-location inventory management
- Stock movement reporting

## Implementation

```python
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ProductProduct, StockQuant, StockMove

class InventoryManager:
    """Advanced inventory management system."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.low_stock_threshold = 10
        self.reorder_quantity = 50
    
    async def get_current_stock_levels(self, location_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get current stock levels for all products."""
        
        query = self.client.model(StockQuant).filter(
            quantity__gt=0
        ).only("product_id", "location_id", "quantity", "reserved_quantity")
        
        if location_id:
            query = query.filter(location_id=location_id)
        
        stock_quants = await query.all()
        
        # Group by product
        stock_levels = {}
        for quant in stock_quants:
            product_id = quant.product_id.id if hasattr(quant.product_id, 'id') else quant.product_id
            
            if product_id not in stock_levels:
                stock_levels[product_id] = {
                    "product_id": product_id,
                    "total_quantity": 0,
                    "available_quantity": 0,
                    "reserved_quantity": 0,
                    "locations": []
                }
            
            available = quant.quantity - quant.reserved_quantity
            stock_levels[product_id]["total_quantity"] += quant.quantity
            stock_levels[product_id]["available_quantity"] += available
            stock_levels[product_id]["reserved_quantity"] += quant.reserved_quantity
            
            stock_levels[product_id]["locations"].append({
                "location_id": quant.location_id.id if hasattr(quant.location_id, 'id') else quant.location_id,
                "quantity": quant.quantity,
                "available": available
            })
        
        return list(stock_levels.values())
    
    async def check_low_stock_products(self) -> List[Dict[str, Any]]:
        """Identify products with low stock levels."""
        
        stock_levels = await self.get_current_stock_levels()
        low_stock_products = []
        
        for stock in stock_levels:
            if stock["available_quantity"] <= self.low_stock_threshold:
                # Get product details
                product = await self.client.model(ProductProduct).filter(
                    id=stock["product_id"]
                ).only("name", "default_code", "categ_id").first()
                
                if product:
                    low_stock_products.append({
                        "product_id": stock["product_id"],
                        "product_name": product.name,
                        "product_code": product.default_code,
                        "category": product.categ_id.name if hasattr(product.categ_id, 'name') else None,
                        "current_stock": stock["available_quantity"],
                        "threshold": self.low_stock_threshold,
                        "suggested_reorder": self.reorder_quantity
                    })
        
        return low_stock_products
    
    async def create_stock_adjustment(self, adjustments: List[Dict[str, Any]]) -> int:
        """Create stock adjustment for inventory corrections."""
        
        # Create inventory adjustment
        inventory_vals = {
            "name": f"Stock Adjustment {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "date": datetime.now(),
            "state": "draft"
        }
        
        inventory = await self.client.model("stock.inventory").create(inventory_vals)
        
        # Create adjustment lines
        for adjustment in adjustments:
            line_vals = {
                "inventory_id": inventory.id,
                "product_id": adjustment["product_id"],
                "location_id": adjustment["location_id"],
                "product_qty": adjustment["new_quantity"],
                "theoretical_qty": adjustment["current_quantity"]
            }
            
            await self.client.model("stock.inventory.line").create(line_vals)
        
        # Validate inventory
        await inventory.action_validate()
        
        return inventory.id
    
    async def track_stock_movements(self, days: int = 7) -> List[Dict[str, Any]]:
        """Track stock movements over specified period."""
        
        start_date = datetime.now() - timedelta(days=days)
        
        movements = await self.client.model(StockMove).filter(
            date__gte=start_date,
            state="done"
        ).only(
            "product_id", "location_id", "location_dest_id",
            "product_uom_qty", "date", "origin", "reference"
        ).all()
        
        movement_summary = []
        
        for move in movements:
            movement_summary.append({
                "product_id": move.product_id.id if hasattr(move.product_id, 'id') else move.product_id,
                "from_location": move.location_id.id if hasattr(move.location_id, 'id') else move.location_id,
                "to_location": move.location_dest_id.id if hasattr(move.location_dest_id, 'id') else move.location_dest_id,
                "quantity": move.product_uom_qty,
                "date": move.date,
                "origin": move.origin,
                "reference": move.reference
            })
        
        return movement_summary
    
    async def generate_reorder_suggestions(self) -> List[Dict[str, Any]]:
        """Generate automatic reorder suggestions."""
        
        low_stock = await self.check_low_stock_products()
        movements = await self.track_stock_movements(days=30)
        
        suggestions = []
        
        for product in low_stock:
            # Calculate average consumption
            product_movements = [
                m for m in movements 
                if m["product_id"] == product["product_id"]
            ]
            
            if product_movements:
                total_consumed = sum(m["quantity"] for m in product_movements)
                avg_daily_consumption = total_consumed / 30
                
                # Calculate suggested order quantity
                lead_time_days = 7  # Assume 7 days lead time
                safety_stock = avg_daily_consumption * 3  # 3 days safety stock
                suggested_qty = (avg_daily_consumption * lead_time_days) + safety_stock
                
                suggestions.append({
                    **product,
                    "avg_daily_consumption": avg_daily_consumption,
                    "suggested_order_qty": max(suggested_qty, self.reorder_quantity),
                    "lead_time_days": lead_time_days,
                    "safety_stock": safety_stock
                })
            else:
                suggestions.append({
                    **product,
                    "suggested_order_qty": self.reorder_quantity,
                    "note": "No movement history available"
                })
        
        return suggestions
    
    async def create_purchase_order_from_suggestions(self, suggestions: List[Dict[str, Any]], vendor_id: int) -> int:
        """Create purchase order from reorder suggestions."""
        
        # Create purchase order
        po_vals = {
            "partner_id": vendor_id,
            "date_order": datetime.now(),
            "origin": "Automatic Reorder System"
        }
        
        purchase_order = await self.client.model("purchase.order").create(po_vals)
        
        # Create order lines
        for suggestion in suggestions:
            line_vals = {
                "order_id": purchase_order.id,
                "product_id": suggestion["product_id"],
                "product_qty": suggestion["suggested_order_qty"],
                "date_planned": datetime.now() + timedelta(days=7)
            }
            
            await self.client.model("purchase.order.line").create(line_vals)
        
        return purchase_order.id
    
    async def get_inventory_valuation(self) -> Dict[str, Any]:
        """Calculate total inventory valuation."""
        
        stock_levels = await self.get_current_stock_levels()
        total_value = 0
        product_values = []
        
        for stock in stock_levels:
            # Get product cost
            product = await self.client.model(ProductProduct).filter(
                id=stock["product_id"]
            ).only("name", "standard_price").first()
            
            if product:
                value = stock["total_quantity"] * product.standard_price
                total_value += value
                
                product_values.append({
                    "product_id": stock["product_id"],
                    "product_name": product.name,
                    "quantity": stock["total_quantity"],
                    "unit_cost": product.standard_price,
                    "total_value": value
                })
        
        return {
            "total_inventory_value": total_value,
            "product_count": len(product_values),
            "products": product_values,
            "valuation_date": datetime.now()
        }

# Usage Example
async def main():
    """Demonstrate inventory management capabilities."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        inventory_manager = InventoryManager(client)
        
        print("🏭 Inventory Management System")
        print("=" * 50)
        
        # Check current stock levels
        stock_levels = await inventory_manager.get_current_stock_levels()
        print(f"📦 Total products in stock: {len(stock_levels)}")
        
        # Check low stock products
        low_stock = await inventory_manager.check_low_stock_products()
        if low_stock:
            print(f"⚠️  Low stock products: {len(low_stock)}")
            for product in low_stock[:5]:  # Show first 5
                print(f"  - {product['product_name']}: {product['current_stock']} units")
        
        # Generate reorder suggestions
        suggestions = await inventory_manager.generate_reorder_suggestions()
        if suggestions:
            print(f"🔄 Reorder suggestions: {len(suggestions)}")
            for suggestion in suggestions[:3]:  # Show first 3
                print(f"  - {suggestion['product_name']}: Order {suggestion['suggested_order_qty']} units")
        
        # Get inventory valuation
        valuation = await inventory_manager.get_inventory_valuation()
        print(f"💰 Total inventory value: ${valuation['total_inventory_value']:,.2f}")
        
        # Track recent movements
        movements = await inventory_manager.track_stock_movements(days=7)
        print(f"📊 Stock movements (last 7 days): {len(movements)}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Features

### ABC Analysis

```python
async def perform_abc_analysis(self, inventory_manager: InventoryManager) -> Dict[str, List[Dict[str, Any]]]:
    """Perform ABC analysis on inventory."""
    
    valuation = await inventory_manager.get_inventory_valuation()
    products = valuation["products"]
    
    # Sort by value
    products.sort(key=lambda x: x["total_value"], reverse=True)
    
    total_value = sum(p["total_value"] for p in products)
    cumulative_value = 0
    
    a_products, b_products, c_products = [], [], []
    
    for product in products:
        cumulative_value += product["total_value"]
        percentage = (cumulative_value / total_value) * 100
        
        if percentage <= 80:
            a_products.append(product)
        elif percentage <= 95:
            b_products.append(product)
        else:
            c_products.append(product)
    
    return {
        "A_products": a_products,  # High value - 80% of total value
        "B_products": b_products,  # Medium value - 15% of total value
        "C_products": c_products   # Low value - 5% of total value
    }
```

### Automated Alerts

```python
import smtplib
from email.mime.text import MimeText

async def send_low_stock_alerts(self, inventory_manager: InventoryManager):
    """Send automated low stock alerts."""
    
    low_stock = await inventory_manager.check_low_stock_products()
    
    if low_stock:
        message = "Low Stock Alert:\n\n"
        for product in low_stock:
            message += f"- {product['product_name']}: {product['current_stock']} units remaining\n"
        
        # Send email alert
        msg = MimeText(message)
        msg['Subject'] = f"Low Stock Alert - {len(low_stock)} products"
        msg['From'] = "inventory@company.com"
        msg['To'] = "manager@company.com"
        
        # Send email (configure SMTP settings)
        # smtp_server.send_message(msg)
```

## Best Practices

1. **Regular Monitoring**: Check stock levels daily
2. **Accurate Forecasting**: Use historical data for predictions
3. **Safety Stock**: Maintain buffer stock for critical items
4. **Supplier Management**: Maintain good supplier relationships
5. **Cycle Counting**: Regular physical inventory checks

## Next Steps

- [E-commerce Integration](ecommerce-integration.md) - Sync with online stores
- [Financial Reporting](financial-reporting.md) - Inventory valuation reports
- [Automated Workflows](automated-workflows.md) - Automate reordering
