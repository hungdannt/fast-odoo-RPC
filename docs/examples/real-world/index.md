# Real-World Examples

This section contains practical, production-ready examples that demonstrate how to use Zenoo RPC in real-world scenarios. Each example includes complete code, error handling, and best practices.

## Available Examples

### 🏢 Business Applications

- **[Customer Management System](customer-management.md)** - Complete CRM integration with Odoo
- **[E-commerce Integration](ecommerce-integration.md)** - Sync products and orders with online store
- **[Inventory Management](inventory-management.md)** - Real-time inventory tracking and updates
- **[Financial Reporting](financial-reporting.md)** - Generate financial reports and analytics

### 🔄 Data Integration

- **[ETL Pipeline](etl-pipeline.md)** - Extract, transform, and load data from external systems
- **[Data Synchronization](data-sync.md)** - Keep multiple systems in sync with Odoo
- **[Migration Scripts](migration-scripts.md)** - Migrate data from legacy systems
- **[Backup and Restore](backup-restore.md)** - Automated backup and restore procedures

### 🌐 Web Applications

- **[FastAPI Integration](fastapi-integration.md)** - Build REST APIs with FastAPI and Zenoo RPC
- **[Django Integration](django-integration.md)** - Integrate Odoo with Django applications
- **[Flask Integration](flask-integration.md)** - Create web services with Flask
- **[Webhook Handlers](webhook-handlers.md)** - Handle Odoo webhooks efficiently

### 📊 Analytics and Reporting

- **[Sales Dashboard](sales-dashboard.md)** - Real-time sales analytics dashboard
- **[Performance Metrics](performance-metrics.md)** - Track and analyze business KPIs
- **[Custom Reports](custom-reports.md)** - Generate custom business reports
- **[Data Visualization](data-visualization.md)** - Create charts and graphs from Odoo data

### 🔧 Automation and Workflows

- **[Automated Workflows](automated-workflows.md)** - Automate business processes
- **[Scheduled Tasks](scheduled-tasks.md)** - Background job processing
- **[Email Automation](email-automation.md)** - Automated email campaigns
- **[Document Processing](document-processing.md)** - Process and manage documents

## Quick Start Example

Here's a simple but complete example to get you started:

```python
import asyncio
import logging
from datetime import datetime, timedelta
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.exceptions import ZenooError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def daily_sales_report():
    """Generate a daily sales report"""
    
    try:
        async with ZenooClient("localhost", port=8069) as client:
            # Setup caching for better performance
            await client.cache_manager.setup_memory_cache(
                max_size=1000,
                default_ttl=300
            )
            
            # Authenticate
            await client.login("demo", "admin", "admin")
            logger.info("Connected to Odoo successfully")
            
            # Get today's date range
            today = datetime.now().date()
            start_date = datetime.combine(today, datetime.min.time())
            end_date = datetime.combine(today, datetime.max.time())
            
            # Fetch today's confirmed sales orders
            orders = await client.model(SaleOrder).filter(
                state="sale",
                date_order__gte=start_date,
                date_order__lte=end_date
            ).all()
            
            if not orders:
                logger.info("No sales orders found for today")
                return
            
            # Calculate totals
            total_amount = sum(order.amount_total for order in orders)
            total_orders = len(orders)
            
            # Get unique customers
            customer_ids = {order.partner_id.id for order in orders if order.partner_id}
            unique_customers = len(customer_ids)
            
            # Generate report
            print("\n" + "="*50)
            print(f"DAILY SALES REPORT - {today}")
            print("="*50)
            print(f"Total Orders: {total_orders}")
            print(f"Total Amount: ${total_amount:,.2f}")
            print(f"Unique Customers: {unique_customers}")
            print(f"Average Order Value: ${total_amount/total_orders:,.2f}")
            print("="*50)
            
            # Top 5 orders by amount
            top_orders = sorted(orders, key=lambda x: x.amount_total, reverse=True)[:5]
            print("\nTOP 5 ORDERS:")
            for i, order in enumerate(top_orders, 1):
                customer_name = "Unknown"
                if order.partner_id:
                    customer = await order.partner_id
                    customer_name = customer.name
                
                print(f"{i}. {order.name} - {customer_name} - ${order.amount_total:,.2f}")
            
            logger.info("Daily sales report generated successfully")
            
    except ZenooError as e:
        logger.error(f"Zenoo RPC error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(daily_sales_report())
```

## Example Categories

### 🎯 By Complexity Level

**Beginner Examples:**
- Basic CRUD operations
- Simple data queries
- Error handling patterns

**Intermediate Examples:**
- Batch operations
- Caching strategies
- Transaction management

**Advanced Examples:**
- Complex integrations
- Performance optimization
- Production deployments

### 🏭 By Industry

**Retail & E-commerce:**
- Product catalog management
- Order processing
- Inventory synchronization

**Manufacturing:**
- Production planning
- Quality control
- Supply chain management

**Services:**
- Project management
- Time tracking
- Resource allocation

**Healthcare:**
- Patient management
- Appointment scheduling
- Medical records

### 🔧 By Use Case

**Data Migration:**
- Legacy system migration
- Data cleaning and validation
- Bulk data operations

**Integration:**
- Third-party API integration
- Real-time synchronization
- Event-driven architecture

**Automation:**
- Workflow automation
- Scheduled tasks
- Business rule enforcement

**Reporting:**
- Custom reports
- Dashboard creation
- Analytics and insights

## Code Quality Standards

All examples in this section follow these standards:

### ✅ Best Practices

- **Async/await patterns** - Proper use of asyncio
- **Error handling** - Comprehensive exception handling
- **Type hints** - Full type annotations
- **Documentation** - Clear docstrings and comments
- **Logging** - Structured logging for debugging
- **Configuration** - Environment-based configuration
- **Testing** - Unit tests and integration tests

### 📋 Code Structure

```python
# Standard imports
import asyncio
import logging
from typing import List, Optional
from datetime import datetime

# Third-party imports
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.exceptions import ZenooError

# Configure logging
logger = logging.getLogger(__name__)

async def main_function():
    """Main function with proper error handling"""
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            # Your business logic here
            result = await business_logic(client)
            return result
            
    except ZenooError as e:
        logger.error(f"Zenoo RPC error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

async def business_logic(client: ZenooClient) -> List[ResPartner]:
    """Business logic with type hints and documentation"""
    # Implementation here
    pass

if __name__ == "__main__":
    asyncio.run(main_function())
```

## Getting Started

1. **Choose an example** that matches your use case
2. **Read the documentation** for context and requirements
3. **Copy the code** and adapt it to your needs
4. **Test thoroughly** in a development environment
5. **Deploy with confidence** using the provided guidelines

## Contributing Examples

We welcome contributions of real-world examples! Please see our [Contributing Guidelines](../../contributing/documentation.md) for details on:

- Code quality standards
- Documentation requirements
- Testing expectations
- Review process

## Support

If you need help with any of these examples:

1. Check the [Troubleshooting Guide](../../troubleshooting/debugging.md)
2. Review the [API Reference](../../api-reference/index.md)
3. Ask questions in [GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)
4. Report issues in [GitHub Issues](https://github.com/tuanle96/zenoo-rpc/issues)

---

**Ready to dive in?** Start with the [Customer Management System](customer-management.md) example for a comprehensive introduction to real-world Zenoo RPC usage.
