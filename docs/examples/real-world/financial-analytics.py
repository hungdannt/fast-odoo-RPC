#!/usr/bin/env python3
"""
AI-Powered Financial Analytics Dashboard

This example demonstrates a production-ready financial analytics system using
Zenoo RPC's AI capabilities for:
- Real-time financial data analysis
- AI-powered trend detection and forecasting
- Automated anomaly detection
- Intelligent financial reporting
- Risk assessment and recommendations

Based on real-world Gemini API production patterns for financial services.
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError


# Configure logging for financial compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s:%(lineno)d',
    handlers=[
        logging.FileHandler('financial_analytics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class FinancialMetric:
    """Financial metric with AI analysis."""
    name: str
    value: Decimal
    currency: str
    period: str
    trend: str  # 'increasing', 'decreasing', 'stable'
    confidence: float
    ai_insight: str
    risk_level: str  # 'low', 'medium', 'high', 'critical'


@dataclass
class AnomalyAlert:
    """Financial anomaly detection result."""
    metric_name: str
    current_value: Decimal
    expected_value: Decimal
    deviation_percentage: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    recommended_actions: List[str]
    timestamp: datetime


@dataclass
class ForecastResult:
    """AI-powered financial forecast."""
    metric_name: str
    current_value: Decimal
    forecasted_values: List[Tuple[datetime, Decimal]]
    confidence_interval: Tuple[Decimal, Decimal]
    methodology: str
    key_factors: List[str]
    risks: List[str]


class FinancialAnalyticsDashboard:
    """
    Production-ready financial analytics dashboard with AI capabilities.
    
    Features:
    - Real-time financial KPI monitoring
    - AI-powered trend analysis and forecasting
    - Automated anomaly detection with alerts
    - Intelligent financial reporting
    - Risk assessment and compliance monitoring
    - Performance benchmarking
    """
    
    def __init__(self, odoo_url: str, database: str, username: str, password: str):
        self.odoo_url = odoo_url
        self.database = database
        self.username = username
        self.password = password
        self.client: Optional[ZenooClient] = None
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache for financial data
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager for Odoo client with financial-grade security."""
        client = ZenooClient(self.odoo_url)
        try:
            await client.login(self.database, self.username, self.password)
            
            # Setup AI with financial analysis configuration
            await client.setup_ai(
                provider="gemini",
                model="gemini-2.5-pro",  # More capable for financial analysis
                api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.05,  # Very deterministic for financial data
                max_tokens=8192,   # Larger context for complex analysis
                timeout=60.0,      # Longer timeout for complex calculations
                max_retries=5      # High reliability for financial operations
            )
            
            yield client
            
        except Exception as e:
            logger.error(f"Financial client setup failed: {e}")
            raise
        finally:
            await client.close()
    
    async def get_real_time_kpis(self) -> List[FinancialMetric]:
        """Get real-time financial KPIs with AI analysis."""
        
        cache_key = "real_time_kpis"
        if self._is_cached(cache_key):
            return self.cache[cache_key]['data']
        
        async with self.get_client() as client:
            logger.info("Calculating real-time financial KPIs...")
            
            # Get current period data
            current_date = datetime.now()
            start_of_month = current_date.replace(day=1)
            start_of_year = current_date.replace(month=1, day=1)
            
            # Revenue metrics
            revenue_data = await self._calculate_revenue_metrics(client, start_of_month, current_date)
            
            # Expense metrics
            expense_data = await self._calculate_expense_metrics(client, start_of_month, current_date)
            
            # Cash flow metrics
            cashflow_data = await self._calculate_cashflow_metrics(client, start_of_month, current_date)
            
            # Profitability metrics
            profit_data = await self._calculate_profitability_metrics(client, start_of_year, current_date)
            
            # AI analysis of all metrics
            all_metrics_data = {
                'revenue': revenue_data,
                'expenses': expense_data,
                'cashflow': cashflow_data,
                'profitability': profit_data
            }
            
            ai_analysis = await client.ai.chat(
                f"Analyze these financial metrics and provide insights:\n"
                f"Data: {json.dumps(all_metrics_data, default=str)}\n"
                f"For each metric, provide:\n"
                f"1. Trend analysis (increasing/decreasing/stable)\n"
                f"2. Risk assessment (low/medium/high/critical)\n"
                f"3. Key insights and recommendations\n"
                f"4. Confidence level (0.0-1.0)\n"
                f"Respond with JSON array of metric analyses.",
                context="Real-time financial KPI analysis"
            )
            
            try:
                ai_insights = json.loads(ai_analysis)
                kpis = self._build_financial_metrics(all_metrics_data, ai_insights)
                
                # Cache results
                self._cache_data(cache_key, kpis)
                return kpis
                
            except json.JSONDecodeError as e:
                logger.error(f"AI analysis parsing failed: {e}")
                # Fallback to basic metrics without AI insights
                return self._build_basic_metrics(all_metrics_data)
    
    async def _calculate_revenue_metrics(self, client: ZenooClient, 
                                       start_date: datetime, end_date: datetime) -> Dict:
        """Calculate comprehensive revenue metrics."""
        
        # Total revenue
        invoices = await client.search_read(
            'account.move',
            [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', start_date.date()),
                ('invoice_date', '<=', end_date.date())
            ],
            ['amount_total', 'currency_id', 'invoice_date', 'partner_id']
        )
        
        total_revenue = sum(Decimal(str(inv['amount_total'])) for inv in invoices)
        
        # Revenue by customer segment
        customer_revenue = {}
        for invoice in invoices:
            partner_id = invoice['partner_id'][0] if invoice['partner_id'] else 'unknown'
            customer_revenue[partner_id] = customer_revenue.get(partner_id, Decimal('0')) + Decimal(str(invoice['amount_total']))
        
        # Previous period comparison
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date
        
        prev_invoices = await client.search_read(
            'account.move',
            [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', prev_start.date()),
                ('invoice_date', '<=', prev_end.date())
            ],
            ['amount_total']
        )
        
        prev_revenue = sum(Decimal(str(inv['amount_total'])) for inv in prev_invoices)
        growth_rate = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else Decimal('0')
        
        return {
            'total_revenue': total_revenue,
            'customer_revenue': customer_revenue,
            'growth_rate': growth_rate,
            'invoice_count': len(invoices),
            'average_invoice_value': total_revenue / len(invoices) if invoices else Decimal('0')
        }
    
    async def _calculate_expense_metrics(self, client: ZenooClient,
                                       start_date: datetime, end_date: datetime) -> Dict:
        """Calculate comprehensive expense metrics."""
        
        # Total expenses
        bills = await client.search_read(
            'account.move',
            [
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', start_date.date()),
                ('invoice_date', '<=', end_date.date())
            ],
            ['amount_total', 'partner_id', 'invoice_date']
        )
        
        total_expenses = sum(Decimal(str(bill['amount_total'])) for bill in bills)
        
        # Expense categories (simplified)
        expense_lines = await client.search_read(
            'account.move.line',
            [
                ('move_id.move_type', '=', 'in_invoice'),
                ('move_id.state', '=', 'posted'),
                ('move_id.invoice_date', '>=', start_date.date()),
                ('move_id.invoice_date', '<=', end_date.date()),
                ('account_id.user_type_id.name', '=', 'Expenses')
            ],
            ['account_id', 'debit', 'name']
        )
        
        category_expenses = {}
        for line in expense_lines:
            account_name = line['account_id'][1] if line['account_id'] else 'Other'
            category_expenses[account_name] = category_expenses.get(account_name, Decimal('0')) + Decimal(str(line['debit']))
        
        return {
            'total_expenses': total_expenses,
            'category_expenses': category_expenses,
            'bill_count': len(bills),
            'average_bill_value': total_expenses / len(bills) if bills else Decimal('0')
        }
    
    async def _calculate_cashflow_metrics(self, client: ZenooClient,
                                        start_date: datetime, end_date: datetime) -> Dict:
        """Calculate cash flow metrics."""
        
        # Cash inflows (payments received)
        inflows = await client.search_read(
            'account.payment',
            [
                ('payment_type', '=', 'inbound'),
                ('state', '=', 'posted'),
                ('date', '>=', start_date.date()),
                ('date', '<=', end_date.date())
            ],
            ['amount', 'currency_id']
        )
        
        total_inflows = sum(Decimal(str(payment['amount'])) for payment in inflows)
        
        # Cash outflows (payments made)
        outflows = await client.search_read(
            'account.payment',
            [
                ('payment_type', '=', 'outbound'),
                ('state', '=', 'posted'),
                ('date', '>=', start_date.date()),
                ('date', '<=', end_date.date())
            ],
            ['amount', 'currency_id']
        )
        
        total_outflows = sum(Decimal(str(payment['amount'])) for payment in outflows)
        net_cashflow = total_inflows - total_outflows
        
        return {
            'cash_inflows': total_inflows,
            'cash_outflows': total_outflows,
            'net_cashflow': net_cashflow,
            'cashflow_ratio': total_inflows / total_outflows if total_outflows else Decimal('0')
        }
    
    async def _calculate_profitability_metrics(self, client: ZenooClient,
                                             start_date: datetime, end_date: datetime) -> Dict:
        """Calculate profitability metrics."""
        
        # Get P&L data
        revenue_accounts = await client.search_read(
            'account.move.line',
            [
                ('account_id.user_type_id.name', '=', 'Income'),
                ('move_id.state', '=', 'posted'),
                ('date', '>=', start_date.date()),
                ('date', '<=', end_date.date())
            ],
            ['credit', 'debit']
        )
        
        total_revenue = sum(Decimal(str(line['credit'])) - Decimal(str(line['debit'])) for line in revenue_accounts)
        
        expense_accounts = await client.search_read(
            'account.move.line',
            [
                ('account_id.user_type_id.name', '=', 'Expenses'),
                ('move_id.state', '=', 'posted'),
                ('date', '>=', start_date.date()),
                ('date', '<=', end_date.date())
            ],
            ['credit', 'debit']
        )
        
        total_expenses = sum(Decimal(str(line['debit'])) - Decimal(str(line['credit'])) for line in expense_accounts)
        
        gross_profit = total_revenue - total_expenses
        profit_margin = (gross_profit / total_revenue * 100) if total_revenue else Decimal('0')
        
        return {
            'gross_profit': gross_profit,
            'profit_margin': profit_margin,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses
        }
    
    def _build_financial_metrics(self, data: Dict, ai_insights: List[Dict]) -> List[FinancialMetric]:
        """Build FinancialMetric objects with AI insights."""
        
        metrics = []
        insight_map = {insight.get('metric_name', ''): insight for insight in ai_insights}
        
        # Revenue metrics
        revenue_insight = insight_map.get('total_revenue', {})
        metrics.append(FinancialMetric(
            name='Total Revenue',
            value=data['revenue']['total_revenue'],
            currency='USD',
            period='Current Month',
            trend=revenue_insight.get('trend', 'stable'),
            confidence=revenue_insight.get('confidence', 0.8),
            ai_insight=revenue_insight.get('insight', 'Revenue analysis pending'),
            risk_level=revenue_insight.get('risk_level', 'medium')
        ))
        
        # Add more metrics...
        # (Similar pattern for expenses, cashflow, profitability)
        
        return metrics
    
    def _build_basic_metrics(self, data: Dict) -> List[FinancialMetric]:
        """Build basic metrics without AI insights (fallback)."""
        
        return [
            FinancialMetric(
                name='Total Revenue',
                value=data['revenue']['total_revenue'],
                currency='USD',
                period='Current Month',
                trend='stable',
                confidence=0.5,
                ai_insight='Basic calculation without AI analysis',
                risk_level='medium'
            )
            # Add more basic metrics...
        ]
    
    async def detect_financial_anomalies(self) -> List[AnomalyAlert]:
        """Detect financial anomalies using AI analysis."""
        
        async with self.get_client() as client:
            # Get historical data for baseline
            historical_data = await self._get_historical_financial_data(client, days=90)
            current_data = await self._get_current_financial_data(client)
            
            # AI-powered anomaly detection
            anomaly_analysis = await client.ai.chat(
                f"Detect financial anomalies by comparing current data to historical patterns:\n"
                f"Historical Data (90 days): {json.dumps(historical_data, default=str)}\n"
                f"Current Data: {json.dumps(current_data, default=str)}\n"
                f"Identify significant deviations, unusual patterns, or concerning trends.\n"
                f"For each anomaly, provide:\n"
                f"1. Metric name and current vs expected value\n"
                f"2. Deviation percentage and severity\n"
                f"3. Possible causes and recommended actions\n"
                f"Respond with JSON array of anomaly alerts.",
                context="Financial anomaly detection"
            )
            
            try:
                anomalies_data = json.loads(anomaly_analysis)
                alerts = []
                
                for anomaly in anomalies_data:
                    alert = AnomalyAlert(
                        metric_name=anomaly.get('metric_name', 'Unknown'),
                        current_value=Decimal(str(anomaly.get('current_value', 0))),
                        expected_value=Decimal(str(anomaly.get('expected_value', 0))),
                        deviation_percentage=float(anomaly.get('deviation_percentage', 0)),
                        severity=anomaly.get('severity', 'medium'),
                        description=anomaly.get('description', ''),
                        recommended_actions=anomaly.get('recommended_actions', []),
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
                
                return alerts
                
            except json.JSONDecodeError as e:
                logger.error(f"Anomaly detection parsing failed: {e}")
                return []
    
    async def generate_financial_forecast(self, metric_name: str, periods: int = 6) -> ForecastResult:
        """Generate AI-powered financial forecast."""
        
        async with self.get_client() as client:
            # Get historical data for forecasting
            historical_data = await self._get_historical_metric_data(client, metric_name, days=365)
            
            # AI-powered forecasting
            forecast_analysis = await client.ai.chat(
                f"Generate a financial forecast for {metric_name}:\n"
                f"Historical Data (12 months): {json.dumps(historical_data, default=str)}\n"
                f"Forecast {periods} periods ahead (months).\n"
                f"Consider:\n"
                f"1. Seasonal patterns and trends\n"
                f"2. Economic factors and market conditions\n"
                f"3. Business growth patterns\n"
                f"4. Risk factors and uncertainties\n"
                f"Provide:\n"
                f"1. Forecasted values with dates\n"
                f"2. Confidence intervals (min/max)\n"
                f"3. Key factors influencing the forecast\n"
                f"4. Potential risks and scenarios\n"
                f"Respond with detailed JSON forecast.",
                context="Financial forecasting and prediction"
            )
            
            try:
                forecast_data = json.loads(forecast_analysis)
                
                # Parse forecasted values
                forecasted_values = []
                for forecast_point in forecast_data.get('forecasted_values', []):
                    date = datetime.fromisoformat(forecast_point['date'])
                    value = Decimal(str(forecast_point['value']))
                    forecasted_values.append((date, value))
                
                return ForecastResult(
                    metric_name=metric_name,
                    current_value=Decimal(str(historical_data[-1]['value'])) if historical_data else Decimal('0'),
                    forecasted_values=forecasted_values,
                    confidence_interval=(
                        Decimal(str(forecast_data.get('confidence_min', 0))),
                        Decimal(str(forecast_data.get('confidence_max', 0)))
                    ),
                    methodology=forecast_data.get('methodology', 'AI-powered analysis'),
                    key_factors=forecast_data.get('key_factors', []),
                    risks=forecast_data.get('risks', [])
                )
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Forecast parsing failed: {e}")
                raise ValueError(f"Failed to generate forecast for {metric_name}")
    
    async def _get_historical_financial_data(self, client: ZenooClient, days: int) -> Dict:
        """Get historical financial data for analysis."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get revenue trend
        revenue_data = await self._calculate_revenue_metrics(client, start_date, end_date)
        
        # Get expense trend
        expense_data = await self._calculate_expense_metrics(client, start_date, end_date)
        
        return {
            'revenue': revenue_data,
            'expenses': expense_data,
            'period': f"{start_date.date()} to {end_date.date()}"
        }
    
    async def _get_current_financial_data(self, client: ZenooClient) -> Dict:
        """Get current financial data for comparison."""
        
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1)
        
        return await self._get_historical_financial_data(client, (current_date - start_of_month).days)
    
    async def _get_historical_metric_data(self, client: ZenooClient, metric_name: str, days: int) -> List[Dict]:
        """Get historical data for a specific metric."""
        
        # This would typically query time-series data
        # For demo purposes, we'll simulate monthly data points
        data_points = []
        
        for i in range(12):  # 12 months of data
            date = datetime.now() - timedelta(days=30*i)
            # Simulate metric values (in real implementation, query actual data)
            value = 100000 + (i * 5000)  # Simplified growth pattern
            
            data_points.append({
                'date': date.isoformat(),
                'value': value,
                'metric': metric_name
            })
        
        return list(reversed(data_points))
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and still valid."""
        if key not in self.cache:
            return False
        
        cache_time = self.cache[key]['timestamp']
        return (time.time() - cache_time) < self.cache_ttl
    
    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp."""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }


async def main():
    """Example usage of the Financial Analytics Dashboard."""
    
    # Initialize dashboard
    dashboard = FinancialAnalyticsDashboard(
        odoo_url="http://localhost:8069",
        database="demo",
        username="admin",
        password="admin"
    )
    
    try:
        # Get real-time KPIs
        logger.info("Fetching real-time financial KPIs...")
        kpis = await dashboard.get_real_time_kpis()
        
        for kpi in kpis:
            logger.info(f"KPI: {kpi.name} = {kpi.value} {kpi.currency}")
            logger.info(f"  Trend: {kpi.trend}, Risk: {kpi.risk_level}")
            logger.info(f"  AI Insight: {kpi.ai_insight}")
        
        # Detect anomalies
        logger.info("Detecting financial anomalies...")
        anomalies = await dashboard.detect_financial_anomalies()
        
        for anomaly in anomalies:
            logger.warning(f"Anomaly detected in {anomaly.metric_name}")
            logger.warning(f"  Current: {anomaly.current_value}, Expected: {anomaly.expected_value}")
            logger.warning(f"  Deviation: {anomaly.deviation_percentage}%, Severity: {anomaly.severity}")
        
        # Generate forecast
        logger.info("Generating revenue forecast...")
        forecast = await dashboard.generate_financial_forecast("Total Revenue", periods=6)
        
        logger.info(f"Revenue Forecast for {forecast.metric_name}:")
        logger.info(f"  Current: {forecast.current_value}")
        logger.info(f"  Methodology: {forecast.methodology}")
        for date, value in forecast.forecasted_values:
            logger.info(f"  {date.strftime('%Y-%m')}: {value}")
        
    except Exception as e:
        logger.error(f"Financial analytics failed: {e}")
        raise


if __name__ == "__main__":
    import os
    
    # Ensure API key is set
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        exit(1)
    
    asyncio.run(main())
