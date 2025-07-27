# Custom Report Generation System

A comprehensive example showing how to build a flexible custom report generation system using Zenoo RPC with advanced querying, data aggregation, and export capabilities.

## Overview

This example demonstrates:

- Dynamic report builder with flexible filters
- Multiple output formats (JSON, CSV, Excel, PDF)
- Scheduled report generation
- Template-based reporting
- Performance optimization for large datasets
- Email delivery integration

## Complete Implementation

### Report Generation Service

```python
import asyncio
import csv
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from io import StringIO, BytesIO
from pathlib import Path
import tempfile

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q
from zenoo_rpc.batch.manager import BatchManager

@dataclass
class ReportFilter:
    """Report filter configuration."""
    field_name: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, like, ilike
    value: Any
    logical_operator: str = "AND"  # AND, OR

@dataclass
class ReportColumn:
    """Report column configuration."""
    field_name: str
    display_name: str
    data_type: str = "string"  # string, number, date, boolean
    format_string: Optional[str] = None
    aggregation: Optional[str] = None  # sum, avg, count, min, max

@dataclass
class ReportTemplate:
    """Report template configuration."""
    name: str
    description: str
    model_name: str
    columns: List[ReportColumn]
    filters: List[ReportFilter] = field(default_factory=list)
    order_by: Optional[str] = None
    limit: Optional[int] = None
    group_by: Optional[List[str]] = None

class CustomReportGenerator:
    """Custom report generation service with flexible configuration."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.templates: Dict[str, ReportTemplate] = {}
        self._register_default_templates()
    
    def register_template(self, template: ReportTemplate):
        """Register a new report template."""
        self.templates[template.name] = template
    
    async def generate_report(
        self,
        template_name: str,
        additional_filters: Optional[List[ReportFilter]] = None,
        output_format: str = "json",
        date_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Generate a report using a registered template."""
        
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        # Build query
        query_builder = self.client.model(self._get_model_class(template.model_name))
        
        # Apply template filters
        filters = self._build_filters(template.filters + (additional_filters or []))
        if filters:
            query_builder = query_builder.filter(filters)
        
        # Apply date range if provided
        if date_range:
            start_date, end_date = date_range
            date_filter = Q(create_date__gte=start_date) & Q(create_date__lte=end_date)
            query_builder = query_builder.filter(date_filter)
        
        # Apply field selection
        field_names = [col.field_name for col in template.columns]
        query_builder = query_builder.only(*field_names)
        
        # Apply ordering
        if template.order_by:
            query_builder = query_builder.order_by(template.order_by)
        
        # Apply limit
        if template.limit:
            query_builder = query_builder.limit(template.limit)
        
        # Execute query
        start_time = datetime.now()
        records = await query_builder.all()
        query_duration = (datetime.now() - start_time).total_seconds()
        
        # Process data
        processed_data = self._process_report_data(records, template)
        
        # Generate output
        report_data = {
            "template_name": template_name,
            "generated_at": datetime.now().isoformat(),
            "query_duration": query_duration,
            "record_count": len(records),
            "columns": [
                {
                    "field_name": col.field_name,
                    "display_name": col.display_name,
                    "data_type": col.data_type
                }
                for col in template.columns
            ],
            "data": processed_data,
            "summary": self._generate_summary(processed_data, template)
        }
        
        # Format output
        if output_format == "json":
            return report_data
        elif output_format == "csv":
            return self._export_to_csv(report_data)
        elif output_format == "excel":
            return await self._export_to_excel(report_data)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    async def generate_sales_report(
        self,
        start_date: date,
        end_date: date,
        group_by: str = "month",
        include_details: bool = False
    ) -> Dict[str, Any]:
        """Generate comprehensive sales report."""
        
        # Build date filter
        date_filter = Q(date_order__gte=start_date) & Q(date_order__lte=end_date)
        
        # Get sales orders
        orders = await (
            self.client.model(SaleOrder)
            .filter(date_filter & Q(state__in=["sale", "done"]))
            .only("date_order", "amount_total", "partner_id", "state")
            .order_by("date_order")
            .all()
        )
        
        # Group data by period
        grouped_data = self._group_sales_by_period(orders, group_by)
        
        # Calculate summary statistics
        total_revenue = sum(order.amount_total for order in orders)
        total_orders = len(orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Get customer data if details requested
        customer_details = {}
        if include_details and orders:
            partner_ids = list(set(
                order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id
                for order in orders
            ))
            
            customers = await (
                self.client.model(ResPartner)
                .filter(Q(id__in=partner_ids))
                .only("name", "email", "is_company")
                .all()
            )
            
            customer_details = {c.id: c for c in customers}
        
        return {
            "report_type": "sales_summary",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "group_by": group_by
            },
            "summary": {
                "total_revenue": float(total_revenue),
                "total_orders": total_orders,
                "average_order_value": float(avg_order_value)
            },
            "grouped_data": grouped_data,
            "customer_details": customer_details if include_details else None,
            "generated_at": datetime.now().isoformat()
        }
    
    async def generate_customer_analysis_report(self) -> Dict[str, Any]:
        """Generate customer analysis report with segmentation."""
        
        # Get all customers with order data
        customers = await (
            self.client.model(ResPartner)
            .filter(Q(customer_rank__gt=0))
            .only("name", "email", "is_company", "create_date", "country_id")
            .all()
        )
        
        # Get sales data for customers
        customer_sales = {}
        if customers:
            customer_ids = [c.id for c in customers]
            
            # Use batch operations for efficiency
            async with self.client.batch() as batch:
                for customer_id in customer_ids:
                    batch.search("sale.order", [
                        ("partner_id", "=", customer_id),
                        ("state", "in", ["sale", "done"])
                    ])
            
            batch_results = await batch.execute()
            
            # Process sales data
            for i, customer_id in enumerate(customer_ids):
                orders = batch_results.get("search_results", [])[i] if i < len(batch_results.get("search_results", [])) else []
                customer_sales[customer_id] = {
                    "order_count": len(orders),
                    "total_revenue": sum(order.get("amount_total", 0) for order in orders)
                }
        
        # Segment customers
        segments = self._segment_customers(customers, customer_sales)
        
        # Generate geographic analysis
        geographic_analysis = self._analyze_customer_geography(customers)
        
        return {
            "report_type": "customer_analysis",
            "total_customers": len(customers),
            "segments": segments,
            "geographic_analysis": geographic_analysis,
            "generated_at": datetime.now().isoformat()
        }
    
    async def schedule_report(
        self,
        template_name: str,
        schedule_config: Dict[str, Any],
        delivery_config: Dict[str, Any]
    ) -> str:
        """Schedule a report for automatic generation."""
        
        # This would typically integrate with a task scheduler like Celery
        # For this example, we'll simulate the scheduling
        
        schedule_id = f"schedule_{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Store schedule configuration (in real implementation, this would go to a database)
        schedule_data = {
            "schedule_id": schedule_id,
            "template_name": template_name,
            "schedule_config": schedule_config,  # cron expression, frequency, etc.
            "delivery_config": delivery_config,  # email, file path, etc.
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        print(f"Report scheduled with ID: {schedule_id}")
        print(f"Template: {template_name}")
        print(f"Schedule: {schedule_config}")
        print(f"Delivery: {delivery_config}")
        
        return schedule_id
    
    def _register_default_templates(self):
        """Register default report templates."""
        
        # Customer list template
        customer_template = ReportTemplate(
            name="customer_list",
            description="Basic customer listing with contact information",
            model_name="res.partner",
            columns=[
                ReportColumn("name", "Customer Name", "string"),
                ReportColumn("email", "Email", "string"),
                ReportColumn("phone", "Phone", "string"),
                ReportColumn("is_company", "Is Company", "boolean"),
                ReportColumn("create_date", "Created Date", "date", "%Y-%m-%d")
            ],
            filters=[
                ReportFilter("customer_rank", "gt", 0)
            ],
            order_by="name"
        )
        
        # Sales summary template
        sales_template = ReportTemplate(
            name="sales_summary",
            description="Sales orders summary with revenue data",
            model_name="sale.order",
            columns=[
                ReportColumn("name", "Order Reference", "string"),
                ReportColumn("partner_id", "Customer", "string"),
                ReportColumn("date_order", "Order Date", "date", "%Y-%m-%d"),
                ReportColumn("amount_total", "Total Amount", "number", "%.2f"),
                ReportColumn("state", "Status", "string")
            ],
            filters=[
                ReportFilter("state", "in", ["sale", "done"])
            ],
            order_by="date_order desc"
        )
        
        self.register_template(customer_template)
        self.register_template(sales_template)
    
    def _get_model_class(self, model_name: str):
        """Get model class from model name."""
        model_mapping = {
            "res.partner": ResPartner,
            "sale.order": SaleOrder
        }
        return model_mapping.get(model_name, ResPartner)
    
    def _build_filters(self, filters: List[ReportFilter]) -> Optional[Q]:
        """Build Q object from report filters."""
        if not filters:
            return None
        
        q_objects = []
        for filter_obj in filters:
            field_lookup = f"{filter_obj.field_name}__{filter_obj.operator}"
            if filter_obj.operator in ["eq", "="]:
                field_lookup = filter_obj.field_name
            
            q_obj = Q(**{field_lookup: filter_obj.value})
            q_objects.append(q_obj)
        
        # Combine with logical operators (simplified - assumes all AND)
        result = q_objects[0]
        for q_obj in q_objects[1:]:
            result &= q_obj
        
        return result
    
    def _process_report_data(self, records: List[Any], template: ReportTemplate) -> List[Dict[str, Any]]:
        """Process raw records into report data."""
        processed_data = []
        
        for record in records:
            row = {}
            for column in template.columns:
                value = getattr(record, column.field_name, None)
                
                # Format value based on data type
                if column.data_type == "date" and value:
                    if isinstance(value, datetime):
                        value = value.strftime(column.format_string or "%Y-%m-%d %H:%M:%S")
                    elif isinstance(value, date):
                        value = value.strftime(column.format_string or "%Y-%m-%d")
                elif column.data_type == "number" and value is not None:
                    if column.format_string:
                        value = column.format_string % float(value)
                    else:
                        value = float(value)
                
                row[column.field_name] = value
            
            processed_data.append(row)
        
        return processed_data
    
    def _generate_summary(self, data: List[Dict[str, Any]], template: ReportTemplate) -> Dict[str, Any]:
        """Generate summary statistics for the report."""
        if not data:
            return {}
        
        summary = {"record_count": len(data)}
        
        # Calculate aggregations for numeric columns
        for column in template.columns:
            if column.data_type == "number" and column.aggregation:
                values = [row.get(column.field_name, 0) for row in data if row.get(column.field_name) is not None]
                
                if values:
                    if column.aggregation == "sum":
                        summary[f"{column.field_name}_sum"] = sum(values)
                    elif column.aggregation == "avg":
                        summary[f"{column.field_name}_avg"] = sum(values) / len(values)
                    elif column.aggregation == "min":
                        summary[f"{column.field_name}_min"] = min(values)
                    elif column.aggregation == "max":
                        summary[f"{column.field_name}_max"] = max(values)
        
        return summary
    
    def _export_to_csv(self, report_data: Dict[str, Any]) -> str:
        """Export report data to CSV format."""
        output = StringIO()
        
        if not report_data["data"]:
            return ""
        
        # Write header
        fieldnames = [col["field_name"] for col in report_data["columns"]]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write data
        for row in report_data["data"]:
            writer.writerow(row)
        
        return output.getvalue()
    
    async def _export_to_excel(self, report_data: Dict[str, Any]) -> bytes:
        """Export report data to Excel format."""
        # This would require openpyxl or xlsxwriter
        # For this example, we'll return a placeholder
        return b"Excel export would be implemented here"
    
    def _group_sales_by_period(self, orders: List[Any], group_by: str) -> List[Dict[str, Any]]:
        """Group sales data by time period."""
        grouped = {}
        
        for order in orders:
            order_date = order.date_order.date() if isinstance(order.date_order, datetime) else order.date_order
            
            if group_by == "day":
                key = order_date.strftime("%Y-%m-%d")
            elif group_by == "week":
                # Get Monday of the week
                monday = order_date - timedelta(days=order_date.weekday())
                key = monday.strftime("%Y-%m-%d")
            elif group_by == "month":
                key = order_date.strftime("%Y-%m")
            elif group_by == "year":
                key = order_date.strftime("%Y")
            else:
                key = order_date.strftime("%Y-%m-%d")
            
            if key not in grouped:
                grouped[key] = {
                    "period": key,
                    "revenue": 0,
                    "order_count": 0
                }
            
            grouped[key]["revenue"] += float(order.amount_total)
            grouped[key]["order_count"] += 1
        
        return sorted(grouped.values(), key=lambda x: x["period"])
    
    def _segment_customers(self, customers: List[Any], sales_data: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """Segment customers based on purchase behavior."""
        segments = {
            "high_value": [],
            "medium_value": [],
            "low_value": [],
            "new_customers": []
        }
        
        # Simple segmentation logic
        for customer in customers:
            customer_sales = sales_data.get(customer.id, {"order_count": 0, "total_revenue": 0})
            
            if customer_sales["total_revenue"] > 10000:
                segments["high_value"].append(customer.name)
            elif customer_sales["total_revenue"] > 1000:
                segments["medium_value"].append(customer.name)
            elif customer_sales["order_count"] > 0:
                segments["low_value"].append(customer.name)
            else:
                segments["new_customers"].append(customer.name)
        
        return {
            segment: {"count": len(customers), "customers": customers[:5]}  # Limit to 5 for display
            for segment, customers in segments.items()
        }
    
    def _analyze_customer_geography(self, customers: List[Any]) -> Dict[str, Any]:
        """Analyze customer distribution by geography."""
        # Simplified geographic analysis
        country_distribution = {}
        company_vs_individual = {"companies": 0, "individuals": 0}
        
        for customer in customers:
            # Count by company type
            if customer.is_company:
                company_vs_individual["companies"] += 1
            else:
                company_vs_individual["individuals"] += 1
            
            # Count by country (simplified)
            country = getattr(customer, 'country_id', 'Unknown')
            if country not in country_distribution:
                country_distribution[country] = 0
            country_distribution[country] += 1
        
        return {
            "country_distribution": country_distribution,
            "company_vs_individual": company_vs_individual
        }

# Usage Example
async def main():
    """Demonstrate custom report generation."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize report generator
        report_gen = CustomReportGenerator(client)
        
        print("📊 Generating custom reports...")
        
        # Generate customer list report
        customer_report = await report_gen.generate_report(
            "customer_list",
            output_format="json"
        )
        print(f"Customer Report: {customer_report['record_count']} customers found")
        
        # Generate sales report with date range
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        sales_report = await report_gen.generate_sales_report(
            start_date=start_date,
            end_date=end_date,
            group_by="week",
            include_details=True
        )
        print(f"Sales Report: ${sales_report['summary']['total_revenue']:,.2f} revenue")
        
        # Generate customer analysis
        analysis_report = await report_gen.generate_customer_analysis_report()
        print(f"Customer Analysis: {analysis_report['total_customers']} total customers")
        
        # Schedule a report
        schedule_id = await report_gen.schedule_report(
            "sales_summary",
            {"frequency": "weekly", "day": "monday", "time": "09:00"},
            {"email": "manager@company.com", "format": "excel"}
        )
        print(f"Scheduled report: {schedule_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Flexible Report Templates**
- Dynamic column configuration
- Customizable filters and sorting
- Multiple data types and formatting

### 2. **Multiple Output Formats**
- JSON for API integration
- CSV for spreadsheet import
- Excel for business users

### 3. **Advanced Analytics**
- Customer segmentation
- Geographic analysis
- Time-based grouping

### 4. **Performance Optimization**
- Batch operations for large datasets
- Efficient field selection
- Query optimization

### 5. **Automation Features**
- Scheduled report generation
- Email delivery integration
- Template management

## Integration Examples

### Web API Integration

```python
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/api/reports/{template_name}")
async def generate_report_api(
    template_name: str,
    format: str = Query("json", enum=["json", "csv", "excel"]),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    report_data = await report_gen.generate_report(
        template_name, 
        output_format=format,
        date_range=(start_date, end_date) if start_date and end_date else None
    )
    
    if format == "csv":
        return StreamingResponse(
            io.StringIO(report_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={template_name}.csv"}
        )
    
    return report_data
```

### Scheduled Reports with Celery

```python
from celery import Celery

app = Celery('reports')

@app.task
async def generate_scheduled_report(template_name: str, config: dict):
    """Generate and deliver scheduled report."""
    report_data = await report_gen.generate_report(template_name)
    
    # Send email with report
    await send_email_with_attachment(
        to=config["email"],
        subject=f"Scheduled Report: {template_name}",
        attachment_data=report_data
    )
```

## Next Steps

- [Data Visualization](data-visualization.md) - Create interactive charts from report data
- [Automated Workflows](automated-workflows.md) - Automate report delivery workflows
- [Document Processing](document-processing.md) - Generate PDF reports with charts
