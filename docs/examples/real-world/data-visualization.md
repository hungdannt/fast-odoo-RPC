# Data Visualization and Interactive Dashboards

A comprehensive example showing how to create interactive data visualizations and dashboards using Zenoo RPC data with popular visualization libraries like Plotly, Matplotlib, and Chart.js.

## Overview

This example demonstrates:

- Real-time data visualization with Plotly
- Interactive dashboards with Dash
- Chart generation for web applications
- Performance monitoring visualizations
- Export capabilities for presentations
- Integration with business intelligence tools

## Complete Implementation

### Data Visualization Service

```python
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import base64
from io import BytesIO

# Visualization libraries
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q

@dataclass
class ChartConfig:
    """Chart configuration settings."""
    chart_type: str  # line, bar, pie, scatter, heatmap
    title: str
    x_axis_label: str = ""
    y_axis_label: str = ""
    color_scheme: str = "viridis"
    width: int = 800
    height: int = 600
    interactive: bool = True

class DataVisualizationService:
    """Service for creating data visualizations from Zenoo RPC data."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.color_schemes = {
            "business": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            "modern": ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"],
            "pastel": ["#a8e6cf", "#dcedc1", "#ffd3a5", "#ffa8a8", "#c7ceea"]
        }
    
    async def create_sales_dashboard(
        self, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Create comprehensive sales dashboard with multiple visualizations."""
        
        # Get sales data
        sales_data = await self._get_sales_data(start_date, end_date)
        customer_data = await self._get_customer_data()
        
        # Create multiple charts
        charts = {}
        
        # 1. Sales trend over time
        charts["sales_trend"] = await self._create_sales_trend_chart(sales_data)
        
        # 2. Top customers bar chart
        charts["top_customers"] = await self._create_top_customers_chart(sales_data)
        
        # 3. Sales by customer type pie chart
        charts["customer_type_pie"] = await self._create_customer_type_pie(customer_data)
        
        # 4. Monthly revenue heatmap
        charts["revenue_heatmap"] = await self._create_revenue_heatmap(sales_data)
        
        # 5. Performance metrics gauge
        charts["performance_gauge"] = await self._create_performance_gauge(sales_data)
        
        return {
            "dashboard_title": f"Sales Dashboard ({start_date} to {end_date})",
            "generated_at": datetime.now().isoformat(),
            "charts": charts,
            "summary_stats": self._calculate_summary_stats(sales_data)
        }
    
    async def create_customer_analytics_charts(self) -> Dict[str, Any]:
        """Create customer analytics visualizations."""
        
        # Get customer data with sales information
        customers = await (
            self.client.model(ResPartner)
            .filter(Q(customer_rank__gt=0))
            .only("name", "email", "is_company", "create_date", "country_id")
            .all()
        )
        
        # Get sales data for customers
        customer_sales = await self._get_customer_sales_data([c.id for c in customers])
        
        charts = {}
        
        # 1. Customer acquisition over time
        charts["acquisition_trend"] = self._create_customer_acquisition_chart(customers)
        
        # 2. Customer value distribution
        charts["value_distribution"] = self._create_customer_value_distribution(customer_sales)
        
        # 3. Geographic distribution
        charts["geographic_map"] = self._create_geographic_distribution(customers)
        
        # 4. Customer segmentation scatter plot
        charts["segmentation_scatter"] = self._create_customer_segmentation_scatter(
            customers, customer_sales
        )
        
        return {
            "dashboard_title": "Customer Analytics",
            "generated_at": datetime.now().isoformat(),
            "charts": charts,
            "total_customers": len(customers)
        }
    
    async def create_performance_monitoring_dashboard(self) -> Dict[str, Any]:
        """Create performance monitoring visualizations."""
        
        # Simulate performance metrics (in real implementation, get from monitoring system)
        performance_data = await self._get_performance_metrics()
        
        charts = {}
        
        # 1. Response time trend
        charts["response_time"] = self._create_response_time_chart(performance_data)
        
        # 2. Error rate monitoring
        charts["error_rate"] = self._create_error_rate_chart(performance_data)
        
        # 3. Cache hit ratio gauge
        charts["cache_performance"] = self._create_cache_performance_gauge(performance_data)
        
        # 4. Database query performance
        charts["query_performance"] = self._create_query_performance_chart(performance_data)
        
        return {
            "dashboard_title": "Performance Monitoring",
            "generated_at": datetime.now().isoformat(),
            "charts": charts,
            "system_health": self._assess_system_health(performance_data)
        }
    
    def create_interactive_web_dashboard(self, dashboard_data: Dict[str, Any]) -> str:
        """Create interactive web dashboard using Dash."""
        
        # This would create a Dash application
        # For this example, we'll return HTML with embedded Plotly charts
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .chart-container {{ margin: 20px 0; }}
                .summary-stats {{ 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div class="summary-stats">
                <h3>Summary Statistics</h3>
                {summary_html}
            </div>
            {charts_html}
        </body>
        </html>
        """
        
        # Generate summary HTML
        summary_html = ""
        if "summary_stats" in dashboard_data:
            stats = dashboard_data["summary_stats"]
            summary_html = "<ul>"
            for key, value in stats.items():
                summary_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
            summary_html += "</ul>"
        
        # Generate charts HTML
        charts_html = ""
        for chart_name, chart_data in dashboard_data.get("charts", {}).items():
            charts_html += f"""
            <div class="chart-container">
                <div id="{chart_name}"></div>
                <script>
                    Plotly.newPlot('{chart_name}', {json.dumps(chart_data['data'])}, 
                                   {json.dumps(chart_data['layout'])});
                </script>
            </div>
            """
        
        return html_template.format(
            title=dashboard_data.get("dashboard_title", "Dashboard"),
            summary_html=summary_html,
            charts_html=charts_html
        )
    
    async def export_charts_to_images(
        self, 
        charts: Dict[str, Any], 
        output_dir: str = "/tmp"
    ) -> Dict[str, str]:
        """Export charts as image files for presentations."""
        
        exported_files = {}
        
        for chart_name, chart_data in charts.items():
            try:
                # Create Plotly figure
                fig = go.Figure(data=chart_data["data"], layout=chart_data["layout"])
                
                # Export as PNG
                img_bytes = fig.to_image(format="png", width=800, height=600)
                
                # Save to file
                filename = f"{output_dir}/{chart_name}.png"
                with open(filename, "wb") as f:
                    f.write(img_bytes)
                
                exported_files[chart_name] = filename
                
            except Exception as e:
                print(f"Error exporting chart {chart_name}: {e}")
        
        return exported_files
    
    async def _get_sales_data(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get sales data for the specified period."""
        
        orders = await (
            self.client.model(SaleOrder)
            .filter(
                Q(date_order__gte=start_date) & 
                Q(date_order__lte=end_date) &
                Q(state__in=["sale", "done"])
            )
            .only("date_order", "amount_total", "partner_id", "state")
            .order_by("date_order")
            .all()
        )
        
        # Convert to list of dictionaries for easier processing
        sales_data = []
        for order in orders:
            sales_data.append({
                "date": order.date_order.date() if isinstance(order.date_order, datetime) else order.date_order,
                "amount": float(order.amount_total),
                "partner_id": order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id,
                "state": order.state
            })
        
        return sales_data
    
    async def _get_customer_data(self) -> List[Dict[str, Any]]:
        """Get customer data for analysis."""
        
        customers = await (
            self.client.model(ResPartner)
            .filter(Q(customer_rank__gt=0))
            .only("name", "is_company", "create_date", "country_id")
            .all()
        )
        
        customer_data = []
        for customer in customers:
            customer_data.append({
                "id": customer.id,
                "name": customer.name,
                "is_company": customer.is_company,
                "create_date": customer.create_date.date() if isinstance(customer.create_date, datetime) else customer.create_date,
                "country_id": getattr(customer, 'country_id', None)
            })
        
        return customer_data
    
    async def _create_sales_trend_chart(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create sales trend line chart."""
        
        # Group by date
        daily_sales = {}
        for sale in sales_data:
            date_str = sale["date"].strftime("%Y-%m-%d")
            if date_str not in daily_sales:
                daily_sales[date_str] = 0
            daily_sales[date_str] += sale["amount"]
        
        # Sort by date
        sorted_dates = sorted(daily_sales.keys())
        amounts = [daily_sales[date] for date in sorted_dates]
        
        # Create Plotly chart
        trace = go.Scatter(
            x=sorted_dates,
            y=amounts,
            mode='lines+markers',
            name='Daily Sales',
            line=dict(color='#3498db', width=3),
            marker=dict(size=6)
        )
        
        layout = go.Layout(
            title="Sales Trend Over Time",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Sales Amount ($)"),
            hovermode='x unified'
        )
        
        return {
            "data": [trace],
            "layout": layout
        }
    
    async def _create_top_customers_chart(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create top customers bar chart."""
        
        # Group by customer
        customer_sales = {}
        for sale in sales_data:
            partner_id = sale["partner_id"]
            if partner_id not in customer_sales:
                customer_sales[partner_id] = 0
            customer_sales[partner_id] += sale["amount"]
        
        # Get top 10 customers
        top_customers = sorted(customer_sales.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Get customer names (simplified - in real implementation, fetch from database)
        customer_names = [f"Customer {cid}" for cid, _ in top_customers]
        amounts = [amount for _, amount in top_customers]
        
        trace = go.Bar(
            x=customer_names,
            y=amounts,
            marker=dict(color='#e74c3c'),
            name='Revenue'
        )
        
        layout = go.Layout(
            title="Top 10 Customers by Revenue",
            xaxis=dict(title="Customer"),
            yaxis=dict(title="Revenue ($)"),
            xaxis_tickangle=-45
        )
        
        return {
            "data": [trace],
            "layout": layout
        }
    
    def _create_customer_type_pie(self, customer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create customer type pie chart."""
        
        companies = sum(1 for c in customer_data if c["is_company"])
        individuals = len(customer_data) - companies
        
        trace = go.Pie(
            labels=["Companies", "Individuals"],
            values=[companies, individuals],
            marker=dict(colors=["#2ecc71", "#f39c12"])
        )
        
        layout = go.Layout(
            title="Customer Distribution by Type"
        )
        
        return {
            "data": [trace],
            "layout": layout
        }
    
    async def _create_revenue_heatmap(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create monthly revenue heatmap."""
        
        # Group by month and year
        monthly_data = {}
        for sale in sales_data:
            year = sale["date"].year
            month = sale["date"].month
            
            if year not in monthly_data:
                monthly_data[year] = {}
            if month not in monthly_data[year]:
                monthly_data[year][month] = 0
            
            monthly_data[year][month] += sale["amount"]
        
        # Prepare data for heatmap
        years = sorted(monthly_data.keys())
        months = list(range(1, 13))
        
        z_data = []
        for year in years:
            row = []
            for month in months:
                amount = monthly_data.get(year, {}).get(month, 0)
                row.append(amount)
            z_data.append(row)
        
        trace = go.Heatmap(
            z=z_data,
            x=[f"Month {m}" for m in months],
            y=[str(y) for y in years],
            colorscale="Viridis"
        )
        
        layout = go.Layout(
            title="Revenue Heatmap by Month and Year",
            xaxis=dict(title="Month"),
            yaxis=dict(title="Year")
        )
        
        return {
            "data": [trace],
            "layout": layout
        }
    
    async def _create_performance_gauge(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create performance gauge chart."""
        
        total_revenue = sum(sale["amount"] for sale in sales_data)
        target_revenue = 100000  # Example target
        
        performance_percentage = min((total_revenue / target_revenue) * 100, 100)
        
        trace = go.Indicator(
            mode="gauge+number+delta",
            value=performance_percentage,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Revenue Target Achievement (%)"},
            delta={'reference': 100},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        )
        
        layout = go.Layout(
            title="Performance Gauge"
        )
        
        return {
            "data": [trace],
            "layout": layout
        }
    
    def _calculate_summary_stats(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for the dashboard."""
        
        if not sales_data:
            return {}
        
        total_revenue = sum(sale["amount"] for sale in sales_data)
        total_orders = len(sales_data)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        return {
            "total_revenue": f"${total_revenue:,.2f}",
            "total_orders": f"{total_orders:,}",
            "average_order_value": f"${avg_order_value:,.2f}",
            "period_days": len(set(sale["date"] for sale in sales_data))
        }
    
    # Additional helper methods would be implemented here...
    async def _get_customer_sales_data(self, customer_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get sales data for specific customers."""
        # Implementation would fetch sales data for each customer
        return {}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring dashboard."""
        # Implementation would fetch real performance data
        return {
            "response_times": [0.1, 0.2, 0.15, 0.3, 0.25],
            "error_rates": [0.01, 0.02, 0.01, 0.03, 0.02],
            "cache_hit_ratio": 0.85
        }

# Usage Example
async def main():
    """Demonstrate data visualization capabilities."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize visualization service
        viz_service = DataVisualizationService(client)
        
        print("📊 Creating data visualizations...")
        
        # Create sales dashboard
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        sales_dashboard = await viz_service.create_sales_dashboard(start_date, end_date)
        print(f"Sales Dashboard: {len(sales_dashboard['charts'])} charts created")
        
        # Create customer analytics
        customer_analytics = await viz_service.create_customer_analytics_charts()
        print(f"Customer Analytics: {len(customer_analytics['charts'])} charts created")
        
        # Create interactive web dashboard
        web_dashboard = viz_service.create_interactive_web_dashboard(sales_dashboard)
        
        # Save dashboard to file
        with open("/tmp/sales_dashboard.html", "w") as f:
            f.write(web_dashboard)
        print("Interactive dashboard saved to /tmp/sales_dashboard.html")
        
        # Export charts as images
        exported_files = await viz_service.export_charts_to_images(
            sales_dashboard["charts"]
        )
        print(f"Exported {len(exported_files)} chart images")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Multiple Chart Types**
- Line charts for trends
- Bar charts for comparisons
- Pie charts for distributions
- Heatmaps for patterns
- Gauge charts for KPIs

### 2. **Interactive Dashboards**
- Real-time data updates
- Hover interactions
- Zoom and pan capabilities
- Responsive design

### 3. **Export Capabilities**
- PNG/JPEG image export
- HTML dashboard generation
- PDF report integration
- Presentation-ready formats

### 4. **Performance Optimization**
- Efficient data aggregation
- Cached visualization data
- Optimized chart rendering

### 5. **Business Intelligence**
- Customer segmentation visuals
- Sales trend analysis
- Performance monitoring
- Geographic distribution

## Integration Examples

### FastAPI Web Dashboard

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    viz_service = DataVisualizationService(client)
    dashboard_data = await viz_service.create_sales_dashboard(
        start_date=date.today() - timedelta(days=30),
        end_date=date.today()
    )
    
    html_content = viz_service.create_interactive_web_dashboard(dashboard_data)
    return HTMLResponse(content=html_content)
```

### Real-time Dashboard with WebSockets

```python
import websockets
import json

async def dashboard_websocket(websocket, path):
    """WebSocket endpoint for real-time dashboard updates."""
    while True:
        # Get latest data
        dashboard_data = await viz_service.create_sales_dashboard(
            start_date=date.today(),
            end_date=date.today()
        )
        
        # Send to client
        await websocket.send(json.dumps(dashboard_data))
        await asyncio.sleep(60)  # Update every minute
```

## Next Steps

- [Automated Workflows](automated-workflows.md) - Automate dashboard generation
- [Scheduled Tasks](scheduled-tasks.md) - Schedule dashboard updates
- [Email Automation](email-automation.md) - Email dashboard reports
