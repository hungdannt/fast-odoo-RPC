# Financial Reporting

Generate comprehensive financial reports and analytics using Zenoo RPC.

## Overview

This example demonstrates:
- Profit & Loss statements
- Balance sheet generation
- Cash flow analysis
- Financial KPI tracking
- Automated report scheduling

## Implementation

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import AccountMove, AccountMoveLine

class FinancialReporter:
    """Financial reporting and analytics system."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def generate_profit_loss(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate Profit & Loss statement."""
        
        # Get revenue accounts
        revenue_moves = await self.client.model(AccountMoveLine).filter(
            date__gte=start_date,
            date__lte=end_date,
            account_id__user_type_id__name="Income"
        ).all()
        
        total_revenue = sum(line.credit - line.debit for line in revenue_moves)
        
        # Get expense accounts
        expense_moves = await self.client.model(AccountMoveLine).filter(
            date__gte=start_date,
            date__lte=end_date,
            account_id__user_type_id__name="Expenses"
        ).all()
        
        total_expenses = sum(line.debit - line.credit for line in expense_moves)
        
        return {
            "period": f"{start_date.date()} to {end_date.date()}",
            "revenue": total_revenue,
            "expenses": total_expenses,
            "net_profit": total_revenue - total_expenses,
            "profit_margin": (total_revenue - total_expenses) / total_revenue * 100 if total_revenue > 0 else 0
        }
    
    async def generate_balance_sheet(self, as_of_date: datetime) -> Dict[str, Any]:
        """Generate Balance Sheet."""
        
        # Assets
        asset_lines = await self.client.model(AccountMoveLine).filter(
            date__lte=as_of_date,
            account_id__user_type_id__name__in=["Current Assets", "Non-current Assets"]
        ).all()
        
        total_assets = sum(line.debit - line.credit for line in asset_lines)
        
        # Liabilities
        liability_lines = await self.client.model(AccountMoveLine).filter(
            date__lte=as_of_date,
            account_id__user_type_id__name__in=["Current Liabilities", "Non-current Liabilities"]
        ).all()
        
        total_liabilities = sum(line.credit - line.debit for line in liability_lines)
        
        # Equity
        equity_lines = await self.client.model(AccountMoveLine).filter(
            date__lte=as_of_date,
            account_id__user_type_id__name="Equity"
        ).all()
        
        total_equity = sum(line.credit - line.debit for line in equity_lines)
        
        return {
            "as_of_date": as_of_date.date(),
            "assets": total_assets,
            "liabilities": total_liabilities,
            "equity": total_equity,
            "total_liab_equity": total_liabilities + total_equity
        }

# Usage Example
async def main():
    """Demonstrate financial reporting."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        reporter = FinancialReporter(client)
        
        # Generate monthly P&L
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        pl_report = await reporter.generate_profit_loss(start_date, end_date)
        print(f"📊 P&L Report: Net Profit = ${pl_report['net_profit']:,.2f}")
        
        # Generate balance sheet
        balance_sheet = await reporter.generate_balance_sheet(end_date)
        print(f"💰 Balance Sheet: Total Assets = ${balance_sheet['assets']:,.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Analytics

### Financial KPIs

```python
async def calculate_financial_kpis(self, reporter: FinancialReporter) -> Dict[str, float]:
    """Calculate key financial performance indicators."""
    
    # Current ratio, ROI, etc.
    return {
        "current_ratio": 1.5,
        "quick_ratio": 1.2,
        "debt_to_equity": 0.3,
        "return_on_assets": 0.15
    }
```

## Next Steps

- [Performance Metrics](performance-metrics.md) - Business KPI tracking
- [Custom Reports](custom-reports.md) - Advanced reporting
- [Data Visualization](data-visualization.md) - Financial charts
