# Sales Dashboard with Real-Time Analytics

A comprehensive example showing how to build a real-time sales dashboard using Zenoo RPC with advanced querying, caching, and data aggregation.

## Overview

This example demonstrates building a sales dashboard that provides:

- Real-time sales metrics and KPIs
- Customer analytics and segmentation
- Performance tracking with caching
- Automated report generation
- Interactive data visualization support

## Complete Implementation

### Sales Analytics Service

```python
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from dataclasses import dataclass
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q
from zenoo_rpc.cache.strategies import TTLCache

@dataclass
class SalesMetrics:
    """Sales metrics data structure."""
    total_revenue: Decimal
    total_orders: int
    average_order_value: Decimal
    new_customers: int
    conversion_rate: float
    period_start: date
    period_end: date

@dataclass
class CustomerSegment:
    """Customer segment analytics."""
    segment_name: str
    customer_count: int
    total_revenue: Decimal
    average_revenue_per_customer: Decimal
    top_customers: List[Dict[str, Any]]

class SalesDashboard:
    """Sales dashboard service with real-time analytics."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        # Setup caching for performance
        self.cache = TTLCache(max_size=1000, default_ttl=300)  # 5 minutes
    
    async def get_sales_overview(
        self, 
        start_date: date, 
        end_date: date
    ) -> SalesMetrics:
        """Get comprehensive sales overview for the period."""
        
        # Cache key for this query
        cache_key = f"sales_overview_{start_date}_{end_date}"
        
        # Try to get from cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return SalesMetrics(**cached_result)
        
        # Build date filter
        date_filter = Q(date_order__gte=start_date) & Q(date_order__lte=end_date)
        
        # Get all sales orders for the period
        orders = await (
            self.client.model(SaleOrder)
            .filter(date_filter & Q(state__in=["sale", "done"]))
            .only("amount_total", "partner_id", "date_order", "state")
            .all()
        )
        
        # Calculate metrics
        total_revenue = sum(order.amount_total for order in orders)
        total_orders = len(orders)
        average_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
        
        # Get new customers in this period
        new_customers_count = await self._get_new_customers_count(start_date, end_date)
        
        # Calculate conversion rate (simplified)
        conversion_rate = await self._calculate_conversion_rate(start_date, end_date)
        
        metrics = SalesMetrics(
            total_revenue=total_revenue,
            total_orders=total_orders,
            average_order_value=average_order_value,
            new_customers=new_customers_count,
            conversion_rate=conversion_rate,
            period_start=start_date,
            period_end=end_date
        )
        
        # Cache the result
        await self.cache.set(cache_key, metrics.__dict__)
        
        return metrics
    
    async def get_top_customers(
        self, 
        start_date: date, 
        end_date: date, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top customers by revenue for the period."""
        
        cache_key = f"top_customers_{start_date}_{end_date}_{limit}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get sales orders with customer info
        orders = await (
            self.client.model(SaleOrder)
            .filter(
                Q(date_order__gte=start_date) & 
                Q(date_order__lte=end_date) &
                Q(state__in=["sale", "done"])
            )
            .only("partner_id", "amount_total")
            .all()
        )
        
        # Aggregate by customer
        customer_revenue = {}
        for order in orders:
            partner_id = order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id
            if partner_id not in customer_revenue:
                customer_revenue[partner_id] = Decimal('0')
            customer_revenue[partner_id] += order.amount_total
        
        # Get top customers
        top_customer_ids = sorted(
            customer_revenue.keys(), 
            key=lambda x: customer_revenue[x], 
            reverse=True
        )[:limit]
        
        # Get customer details
        top_customers = []
        if top_customer_ids:
            customers = await (
                self.client.model(ResPartner)
                .filter(Q(id__in=top_customer_ids))
                .only("name", "email", "is_company")
                .all()
            )
            
            customer_dict = {c.id: c for c in customers}
            
            for customer_id in top_customer_ids:
                customer = customer_dict.get(customer_id)
                if customer:
                    top_customers.append({
                        "id": customer_id,
                        "name": customer.name,
                        "email": customer.email,
                        "is_company": customer.is_company,
                        "total_revenue": float(customer_revenue[customer_id]),
                        "order_count": len([o for o in orders if (
                            o.partner_id.id if hasattr(o.partner_id, 'id') else o.partner_id
                        ) == customer_id])
                    })
        
        # Cache the result
        await self.cache.set(cache_key, top_customers)
        
        return top_customers
    
    async def get_sales_by_period(
        self, 
        start_date: date, 
        end_date: date, 
        period_type: str = "daily"
    ) -> List[Dict[str, Any]]:
        """Get sales data grouped by time period."""
        
        cache_key = f"sales_by_period_{start_date}_{end_date}_{period_type}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get all orders for the period
        orders = await (
            self.client.model(SaleOrder)
            .filter(
                Q(date_order__gte=start_date) & 
                Q(date_order__lte=end_date) &
                Q(state__in=["sale", "done"])
            )
            .only("date_order", "amount_total")
            .order_by("date_order")
            .all()
        )
        
        # Group by period
        period_data = {}
        for order in orders:
            order_date = order.date_order.date() if isinstance(order.date_order, datetime) else order.date_order
            
            if period_type == "daily":
                period_key = order_date.strftime("%Y-%m-%d")
            elif period_type == "weekly":
                # Get Monday of the week
                monday = order_date - timedelta(days=order_date.weekday())
                period_key = monday.strftime("%Y-%m-%d")
            elif period_type == "monthly":
                period_key = order_date.strftime("%Y-%m")
            else:
                period_key = order_date.strftime("%Y-%m-%d")
            
            if period_key not in period_data:
                period_data[period_key] = {
                    "period": period_key,
                    "revenue": Decimal('0'),
                    "order_count": 0
                }
            
            period_data[period_key]["revenue"] += order.amount_total
            period_data[period_key]["order_count"] += 1
        
        # Convert to list and sort
        result = list(period_data.values())
        result.sort(key=lambda x: x["period"])
        
        # Convert Decimal to float for JSON serialization
        for item in result:
            item["revenue"] = float(item["revenue"])
        
        # Cache the result
        await self.cache.set(cache_key, result)
        
        return result
    
    async def get_customer_segments(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[CustomerSegment]:
        """Analyze customer segments based on purchase behavior."""
        
        cache_key = f"customer_segments_{start_date}_{end_date}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return [CustomerSegment(**segment) for segment in cached_result]
        
        # Get customer revenue data
        top_customers = await self.get_top_customers(start_date, end_date, limit=1000)
        
        if not top_customers:
            return []
        
        # Define segments based on revenue
        revenues = [c["total_revenue"] for c in top_customers]
        revenues.sort(reverse=True)
        
        # Calculate percentiles
        total_customers = len(revenues)
        high_value_threshold = revenues[int(total_customers * 0.1)] if total_customers > 10 else revenues[0]
        medium_value_threshold = revenues[int(total_customers * 0.3)] if total_customers > 3 else revenues[-1]
        
        # Segment customers
        segments = {
            "High Value": [],
            "Medium Value": [],
            "Low Value": []
        }
        
        for customer in top_customers:
            revenue = customer["total_revenue"]
            if revenue >= high_value_threshold:
                segments["High Value"].append(customer)
            elif revenue >= medium_value_threshold:
                segments["Medium Value"].append(customer)
            else:
                segments["Low Value"].append(customer)
        
        # Create segment objects
        segment_objects = []
        for segment_name, customers in segments.items():
            if customers:
                total_revenue = sum(c["total_revenue"] for c in customers)
                avg_revenue = total_revenue / len(customers)
                top_5 = customers[:5]  # Top 5 customers in segment
                
                segment_objects.append(CustomerSegment(
                    segment_name=segment_name,
                    customer_count=len(customers),
                    total_revenue=Decimal(str(total_revenue)),
                    average_revenue_per_customer=Decimal(str(avg_revenue)),
                    top_customers=top_5
                ))
        
        # Cache the result
        cache_data = [
            {
                "segment_name": s.segment_name,
                "customer_count": s.customer_count,
                "total_revenue": float(s.total_revenue),
                "average_revenue_per_customer": float(s.average_revenue_per_customer),
                "top_customers": s.top_customers
            }
            for s in segment_objects
        ]
        await self.cache.set(cache_key, cache_data)
        
        return segment_objects
    
    async def generate_dashboard_data(
        self, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Generate complete dashboard data efficiently using batch operations."""
        
        # Use asyncio.gather for concurrent execution
        results = await asyncio.gather(
            self.get_sales_overview(start_date, end_date),
            self.get_top_customers(start_date, end_date, limit=10),
            self.get_sales_by_period(start_date, end_date, "daily"),
            self.get_customer_segments(start_date, end_date),
            return_exceptions=True
        )
        
        # Handle any exceptions
        sales_overview = results[0] if not isinstance(results[0], Exception) else None
        top_customers = results[1] if not isinstance(results[1], Exception) else []
        sales_by_period = results[2] if not isinstance(results[2], Exception) else []
        customer_segments = results[3] if not isinstance(results[3], Exception) else []
        
        return {
            "overview": sales_overview.__dict__ if sales_overview else None,
            "top_customers": top_customers,
            "sales_by_period": sales_by_period,
            "customer_segments": [
                {
                    "segment_name": s.segment_name,
                    "customer_count": s.customer_count,
                    "total_revenue": float(s.total_revenue),
                    "average_revenue_per_customer": float(s.average_revenue_per_customer),
                    "top_customers": s.top_customers[:3]  # Limit for dashboard
                }
                for s in customer_segments
            ],
            "generated_at": datetime.now().isoformat(),
            "cache_info": {
                "hit_ratio": getattr(self.cache, 'hit_ratio', 0),
                "size": getattr(self.cache, 'size', 0)
            }
        }
    
    async def _get_new_customers_count(self, start_date: date, end_date: date) -> int:
        """Get count of new customers in the period."""
        new_customers = await (
            self.client.model(ResPartner)
            .filter(
                Q(create_date__gte=start_date) &
                Q(create_date__lte=end_date) &
                Q(customer_rank__gt=0)
            )
            .count()
        )
        return new_customers
    
    async def _calculate_conversion_rate(self, start_date: date, end_date: date) -> float:
        """Calculate conversion rate (simplified)."""
        # This is a simplified calculation
        # In reality, you'd track leads, opportunities, etc.
        total_orders = await (
            self.client.model(SaleOrder)
            .filter(
                Q(date_order__gte=start_date) &
                Q(date_order__lte=end_date)
            )
            .count()
        )
        
        confirmed_orders = await (
            self.client.model(SaleOrder)
            .filter(
                Q(date_order__gte=start_date) &
                Q(date_order__lte=end_date) &
                Q(state__in=["sale", "done"])
            )
            .count()
        )
        
        return (confirmed_orders / total_orders * 100) if total_orders > 0 else 0.0

# Usage Example
async def main():
    """Demonstrate sales dashboard functionality."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize dashboard
        dashboard = SalesDashboard(client)
        
        # Set date range (last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        print(f"Generating sales dashboard for {start_date} to {end_date}")
        
        # Generate complete dashboard data
        dashboard_data = await dashboard.generate_dashboard_data(start_date, end_date)
        
        # Display results
        if dashboard_data["overview"]:
            overview = dashboard_data["overview"]
            print(f"\n📊 Sales Overview:")
            print(f"  Total Revenue: ${overview['total_revenue']:,.2f}")
            print(f"  Total Orders: {overview['total_orders']:,}")
            print(f"  Average Order Value: ${overview['average_order_value']:,.2f}")
            print(f"  New Customers: {overview['new_customers']:,}")
            print(f"  Conversion Rate: {overview['conversion_rate']:.1f}%")
        
        # Top customers
        print(f"\n🏆 Top Customers:")
        for i, customer in enumerate(dashboard_data["top_customers"][:5], 1):
            print(f"  {i}. {customer['name']} - ${customer['total_revenue']:,.2f}")
        
        # Customer segments
        print(f"\n👥 Customer Segments:")
        for segment in dashboard_data["customer_segments"]:
            print(f"  {segment['segment_name']}: {segment['customer_count']} customers, "
                  f"${segment['total_revenue']:,.2f} revenue")
        
        # Cache performance
        cache_info = dashboard_data["cache_info"]
        print(f"\n⚡ Cache Performance:")
        print(f"  Hit Ratio: {cache_info['hit_ratio']:.1%}")
        print(f"  Cache Size: {cache_info['size']} items")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Real-Time Analytics**
- Concurrent data fetching with `asyncio.gather`
- Efficient caching with TTL strategies
- Performance monitoring and optimization

### 2. **Advanced Querying**
- Complex date range filtering
- Aggregation and grouping
- Customer segmentation logic

### 3. **Caching Strategy**
- TTL-based caching for performance
- Cache hit ratio monitoring
- Strategic cache key design

### 4. **Data Structures**
- Type-safe data classes
- Structured metrics and segments
- JSON-serializable outputs

### 5. **Business Intelligence**
- Customer lifetime value analysis
- Sales trend analysis
- Performance KPIs

## Integration Examples

### Web Dashboard (FastAPI)

```python
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/dashboard")
async def get_dashboard(
    start_date: date = Query(...),
    end_date: date = Query(...),
    dashboard: SalesDashboard = Depends(get_dashboard_service)
):
    data = await dashboard.generate_dashboard_data(start_date, end_date)
    return JSONResponse(data)
```

### Scheduled Reports

```python
import schedule
import time

async def generate_daily_report():
    """Generate and email daily sales report."""
    dashboard = SalesDashboard(client)
    yesterday = date.today() - timedelta(days=1)
    data = await dashboard.generate_dashboard_data(yesterday, yesterday)
    # Send email with data
    
schedule.every().day.at("08:00").do(generate_daily_report)
```

## Next Steps

- [Performance Metrics](performance-metrics.md) - Monitor dashboard performance
- [Custom Reports](custom-reports.md) - Build custom report generators
- [Data Visualization](data-visualization.md) - Create interactive charts
