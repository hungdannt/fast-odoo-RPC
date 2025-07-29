#!/usr/bin/env python3
"""
AI-Powered Supply Chain Optimization System

This example demonstrates a production-ready supply chain optimization using
Zenoo RPC's AI capabilities for:
- Demand forecasting and inventory optimization
- Supplier performance analysis and selection
- Logistics optimization and route planning
- Risk assessment and mitigation
- Real-time supply chain monitoring
- Automated procurement recommendations

Based on real-world Gemini API production patterns for supply chain management.
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
from enum import Enum
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError


# Configure logging for supply chain operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('supply_chain.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SupplierRating(Enum):
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass
class DemandForecast:
    """AI-generated demand forecast."""
    product_id: int
    product_name: str
    current_stock: Decimal
    forecasted_demand: List[Tuple[datetime, Decimal]]
    reorder_point: Decimal
    optimal_order_quantity: Decimal
    confidence_level: float
    seasonality_factors: Dict[str, float]
    risk_factors: List[str]


@dataclass
class SupplierAnalysis:
    """AI-powered supplier performance analysis."""
    supplier_id: int
    supplier_name: str
    overall_rating: SupplierRating
    performance_score: float
    delivery_reliability: float
    quality_score: float
    cost_competitiveness: float
    risk_assessment: RiskLevel
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


@dataclass
class LogisticsOptimization:
    """AI-optimized logistics plan."""
    route_id: str
    origin: str
    destinations: List[str]
    optimized_route: List[str]
    estimated_cost: Decimal
    estimated_time: int  # minutes
    fuel_efficiency: float
    carbon_footprint: Decimal
    risk_factors: List[str]
    alternative_routes: List[Dict]


@dataclass
class SupplyChainAlert:
    """Supply chain risk alert."""
    alert_id: str
    alert_type: str
    severity: RiskLevel
    affected_products: List[int]
    description: str
    impact_assessment: str
    recommended_actions: List[str]
    estimated_impact_cost: Decimal
    timeline: str
    created_at: datetime


class SupplyChainOptimization:
    """
    Production-ready supply chain optimization with AI capabilities.
    
    Features:
    - AI-powered demand forecasting and inventory optimization
    - Intelligent supplier analysis and selection
    - Logistics route optimization with cost analysis
    - Real-time risk monitoring and mitigation
    - Automated procurement recommendations
    - Performance analytics and reporting
    """
    
    def __init__(self, odoo_url: str, database: str, username: str, password: str):
        self.odoo_url = odoo_url
        self.database = database
        self.username = username
        self.password = password
        self.client: Optional[ZenooClient] = None
        self.forecasting_cache = {}
        self.supplier_cache = {}
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager for Odoo client with supply chain configuration."""
        client = ZenooClient(self.odoo_url)
        try:
            await client.login(self.database, self.username, self.password)
            
            # Setup AI for supply chain optimization
            await client.setup_ai(
                provider="gemini",
                model="gemini-2.5-pro",  # More capable for complex analysis
                api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.1,  # Deterministic for business decisions
                max_tokens=8192,  # Large context for complex data
                timeout=60.0,     # Longer timeout for complex calculations
                max_retries=5     # High reliability for critical operations
            )
            
            yield client
            
        except Exception as e:
            logger.error(f"Supply chain client setup failed: {e}")
            raise
        finally:
            await client.close()
    
    async def generate_demand_forecast(self, product_id: int, forecast_periods: int = 12) -> DemandForecast:
        """Generate AI-powered demand forecast for a product."""
        
        async with self.get_client() as client:
            logger.info(f"Generating demand forecast for product {product_id}")
            
            # Get historical sales data
            historical_data = await self._get_historical_sales_data(client, product_id, days=365)
            
            # Get current inventory levels
            current_stock = await self._get_current_stock(client, product_id)
            
            # Get external factors (seasonality, market trends, etc.)
            external_factors = await self._get_external_factors(client, product_id)
            
            # AI-powered demand forecasting
            forecast_analysis = await client.ai.chat(
                f"Generate a comprehensive demand forecast:\n"
                f"Product ID: {product_id}\n"
                f"Historical Sales Data (12 months): {json.dumps(historical_data, default=str)}\n"
                f"Current Stock: {current_stock}\n"
                f"External Factors: {json.dumps(external_factors, default=str)}\n"
                f"Forecast {forecast_periods} periods ahead (months).\n"
                f"Consider:\n"
                f"1. Seasonal patterns and trends\n"
                f"2. Market conditions and economic factors\n"
                f"3. Product lifecycle stage\n"
                f"4. Promotional activities and campaigns\n"
                f"5. Supply chain disruptions\n"
                f"Provide:\n"
                f"1. Monthly forecasted demand with dates\n"
                f"2. Reorder point calculation\n"
                f"3. Optimal order quantity (EOQ)\n"
                f"4. Confidence level and seasonality factors\n"
                f"5. Risk factors and mitigation strategies\n"
                f"Respond with detailed JSON forecast.",
                context="Supply chain demand forecasting"
            )
            
            try:
                forecast_data = json.loads(forecast_analysis)
                
                # Parse forecasted demand
                forecasted_demand = []
                for forecast_point in forecast_data.get('forecasted_demand', []):
                    date = datetime.fromisoformat(forecast_point['date'])
                    demand = Decimal(str(forecast_point['demand']))
                    forecasted_demand.append((date, demand))
                
                # Get product name
                product_info = await client.read('product.product', [product_id], ['name'])
                product_name = product_info[0]['name'] if product_info else f"Product {product_id}"
                
                forecast = DemandForecast(
                    product_id=product_id,
                    product_name=product_name,
                    current_stock=Decimal(str(current_stock)),
                    forecasted_demand=forecasted_demand,
                    reorder_point=Decimal(str(forecast_data.get('reorder_point', 0))),
                    optimal_order_quantity=Decimal(str(forecast_data.get('optimal_order_quantity', 0))),
                    confidence_level=float(forecast_data.get('confidence_level', 0.8)),
                    seasonality_factors=forecast_data.get('seasonality_factors', {}),
                    risk_factors=forecast_data.get('risk_factors', [])
                )
                
                # Cache forecast for performance
                self.forecasting_cache[product_id] = {
                    'forecast': forecast,
                    'timestamp': time.time()
                }
                
                return forecast
                
            except json.JSONDecodeError as e:
                logger.error(f"Demand forecast parsing failed: {e}")
                raise ValueError(f"Failed to generate forecast for product {product_id}")
    
    async def analyze_supplier_performance(self, supplier_id: int) -> SupplierAnalysis:
        """Analyze supplier performance using AI."""
        
        async with self.get_client() as client:
            logger.info(f"Analyzing supplier performance for supplier {supplier_id}")
            
            # Get supplier information
            supplier_info = await self._get_supplier_info(client, supplier_id)
            
            # Get purchase history and performance data
            performance_data = await self._get_supplier_performance_data(client, supplier_id)
            
            # AI supplier analysis
            supplier_analysis = await client.ai.chat(
                f"Analyze this supplier's performance comprehensively:\n"
                f"Supplier Info: {json.dumps(supplier_info, default=str)}\n"
                f"Performance Data: {json.dumps(performance_data, default=str)}\n"
                f"Evaluate:\n"
                f"1. Overall performance rating (poor/fair/good/excellent)\n"
                f"2. Performance score (0.0-1.0)\n"
                f"3. Delivery reliability percentage\n"
                f"4. Quality score based on returns/complaints\n"
                f"5. Cost competitiveness vs market\n"
                f"6. Risk assessment (low/medium/high/critical)\n"
                f"7. Key strengths and weaknesses\n"
                f"8. Specific recommendations for improvement\n"
                f"Consider: on-time delivery, quality issues, pricing, communication, financial stability.\n"
                f"Respond with detailed JSON analysis.",
                context="Supplier performance analysis"
            )
            
            try:
                analysis_data = json.loads(supplier_analysis)
                
                analysis = SupplierAnalysis(
                    supplier_id=supplier_id,
                    supplier_name=supplier_info.get('name', f'Supplier {supplier_id}'),
                    overall_rating=SupplierRating(analysis_data.get('overall_rating', 'fair')),
                    performance_score=float(analysis_data.get('performance_score', 0.5)),
                    delivery_reliability=float(analysis_data.get('delivery_reliability', 0.8)),
                    quality_score=float(analysis_data.get('quality_score', 0.8)),
                    cost_competitiveness=float(analysis_data.get('cost_competitiveness', 0.5)),
                    risk_assessment=RiskLevel(analysis_data.get('risk_assessment', 'medium')),
                    strengths=analysis_data.get('strengths', []),
                    weaknesses=analysis_data.get('weaknesses', []),
                    recommendations=analysis_data.get('recommendations', [])
                )
                
                # Cache analysis
                self.supplier_cache[supplier_id] = {
                    'analysis': analysis,
                    'timestamp': time.time()
                }
                
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Supplier analysis parsing failed: {e}")
                raise ValueError(f"Failed to analyze supplier {supplier_id}")
    
    async def optimize_logistics_route(self, origin: str, destinations: List[str], 
                                     constraints: Dict = None) -> LogisticsOptimization:
        """Optimize logistics route using AI."""
        
        async with self.get_client() as client:
            logger.info(f"Optimizing route from {origin} to {len(destinations)} destinations")
            
            # Get distance and cost data
            route_data = await self._get_route_data(client, origin, destinations)
            
            # Get traffic and weather conditions
            external_conditions = await self._get_external_conditions(origin, destinations)
            
            # AI route optimization
            route_optimization = await client.ai.chat(
                f"Optimize this logistics route:\n"
                f"Origin: {origin}\n"
                f"Destinations: {destinations}\n"
                f"Route Data: {json.dumps(route_data, default=str)}\n"
                f"External Conditions: {json.dumps(external_conditions, default=str)}\n"
                f"Constraints: {json.dumps(constraints or {}, default=str)}\n"
                f"Optimize for:\n"
                f"1. Minimum total cost\n"
                f"2. Shortest total time\n"
                f"3. Fuel efficiency\n"
                f"4. Risk minimization\n"
                f"5. Environmental impact\n"
                f"Provide:\n"
                f"1. Optimized route sequence\n"
                f"2. Estimated total cost and time\n"
                f"3. Fuel efficiency metrics\n"
                f"4. Carbon footprint calculation\n"
                f"5. Risk factors and mitigation\n"
                f"6. Alternative route options\n"
                f"Respond with detailed JSON optimization.",
                context="Logistics route optimization"
            )
            
            try:
                optimization_data = json.loads(route_optimization)
                
                optimization = LogisticsOptimization(
                    route_id=f"route_{int(time.time())}",
                    origin=origin,
                    destinations=destinations,
                    optimized_route=optimization_data.get('optimized_route', destinations),
                    estimated_cost=Decimal(str(optimization_data.get('estimated_cost', 0))),
                    estimated_time=int(optimization_data.get('estimated_time', 0)),
                    fuel_efficiency=float(optimization_data.get('fuel_efficiency', 0)),
                    carbon_footprint=Decimal(str(optimization_data.get('carbon_footprint', 0))),
                    risk_factors=optimization_data.get('risk_factors', []),
                    alternative_routes=optimization_data.get('alternative_routes', [])
                )
                
                return optimization
                
            except json.JSONDecodeError as e:
                logger.error(f"Route optimization parsing failed: {e}")
                raise ValueError("Failed to optimize logistics route")
    
    async def monitor_supply_chain_risks(self) -> List[SupplyChainAlert]:
        """Monitor and detect supply chain risks using AI."""
        
        async with self.get_client() as client:
            logger.info("Monitoring supply chain risks...")
            
            # Get current supply chain status
            supply_chain_status = await self._get_supply_chain_status(client)
            
            # Get external risk factors
            external_risks = await self._get_external_risk_factors()
            
            # AI risk analysis
            risk_analysis = await client.ai.chat(
                f"Analyze supply chain risks and generate alerts:\n"
                f"Supply Chain Status: {json.dumps(supply_chain_status, default=str)}\n"
                f"External Risk Factors: {json.dumps(external_risks, default=str)}\n"
                f"Identify risks in:\n"
                f"1. Inventory levels and stockouts\n"
                f"2. Supplier reliability and performance\n"
                f"3. Transportation and logistics\n"
                f"4. Market conditions and demand fluctuations\n"
                f"5. Geopolitical and economic factors\n"
                f"6. Natural disasters and force majeure\n"
                f"For each risk, provide:\n"
                f"1. Risk type and severity level\n"
                f"2. Affected products or suppliers\n"
                f"3. Impact assessment and cost estimation\n"
                f"4. Recommended mitigation actions\n"
                f"5. Timeline for action\n"
                f"Respond with JSON array of risk alerts.",
                context="Supply chain risk monitoring"
            )
            
            try:
                risks_data = json.loads(risk_analysis)
                alerts = []
                
                for risk_data in risks_data:
                    alert = SupplyChainAlert(
                        alert_id=f"alert_{int(time.time())}_{len(alerts)}",
                        alert_type=risk_data.get('alert_type', 'general'),
                        severity=RiskLevel(risk_data.get('severity', 'medium')),
                        affected_products=risk_data.get('affected_products', []),
                        description=risk_data.get('description', ''),
                        impact_assessment=risk_data.get('impact_assessment', ''),
                        recommended_actions=risk_data.get('recommended_actions', []),
                        estimated_impact_cost=Decimal(str(risk_data.get('estimated_impact_cost', 0))),
                        timeline=risk_data.get('timeline', 'immediate'),
                        created_at=datetime.now()
                    )
                    alerts.append(alert)
                
                # Log critical alerts
                for alert in alerts:
                    if alert.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                        logger.warning(f"Critical supply chain alert: {alert.description}")
                
                return alerts
                
            except json.JSONDecodeError as e:
                logger.error(f"Risk analysis parsing failed: {e}")
                return []
    
    async def generate_procurement_recommendations(self, product_ids: List[int]) -> List[Dict]:
        """Generate AI-powered procurement recommendations."""
        
        async with self.get_client() as client:
            logger.info(f"Generating procurement recommendations for {len(product_ids)} products")
            
            recommendations = []
            
            for product_id in product_ids:
                # Get product data
                product_data = await self._get_product_procurement_data(client, product_id)
                
                # Get supplier options
                supplier_options = await self._get_supplier_options(client, product_id)
                
                # AI procurement recommendation
                procurement_analysis = await client.ai.chat(
                    f"Generate procurement recommendation:\n"
                    f"Product Data: {json.dumps(product_data, default=str)}\n"
                    f"Supplier Options: {json.dumps(supplier_options, default=str)}\n"
                    f"Consider:\n"
                    f"1. Current stock levels and demand forecast\n"
                    f"2. Supplier performance and reliability\n"
                    f"3. Cost optimization and budget constraints\n"
                    f"4. Lead times and delivery schedules\n"
                    f"5. Quality requirements and specifications\n"
                    f"6. Risk factors and contingency planning\n"
                    f"Recommend:\n"
                    f"1. Optimal supplier selection\n"
                    f"2. Order quantity and timing\n"
                    f"3. Negotiation points and strategies\n"
                    f"4. Risk mitigation measures\n"
                    f"Respond with detailed JSON recommendation.",
                    context="Procurement optimization"
                )
                
                try:
                    recommendation_data = json.loads(procurement_analysis)
                    recommendation_data['product_id'] = product_id
                    recommendations.append(recommendation_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Procurement recommendation parsing failed for product {product_id}: {e}")
                    continue
            
            return recommendations
    
    async def _get_historical_sales_data(self, client: ZenooClient, product_id: int, days: int) -> List[Dict]:
        """Get historical sales data for demand forecasting."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        sales_data = await client.search_read(
            'sale.order.line',
            [
                ('product_id', '=', product_id),
                ('order_id.state', 'in', ['sale', 'done']),
                ('order_id.date_order', '>=', start_date.isoformat()),
                ('order_id.date_order', '<=', end_date.isoformat())
            ],
            ['product_uom_qty', 'order_id', 'price_unit']
        )
        
        return sales_data
    
    async def _get_current_stock(self, client: ZenooClient, product_id: int) -> float:
        """Get current stock level for a product."""
        
        stock_quants = await client.search_read(
            'stock.quant',
            [('product_id', '=', product_id)],
            ['quantity']
        )
        
        return sum(quant['quantity'] for quant in stock_quants)
    
    async def _get_external_factors(self, client: ZenooClient, product_id: int) -> Dict:
        """Get external factors affecting demand."""
        
        # In a real implementation, this would integrate with external APIs
        # for market data, economic indicators, weather, etc.
        return {
            'market_trends': 'stable',
            'economic_indicators': 'positive',
            'seasonal_factors': 'normal'
        }
    
    async def _get_supplier_info(self, client: ZenooClient, supplier_id: int) -> Dict:
        """Get supplier information."""
        
        supplier = await client.read(
            'res.partner',
            [supplier_id],
            ['name', 'email', 'phone', 'country_id', 'supplier_rank']
        )
        
        return supplier[0] if supplier else {}
    
    async def _get_supplier_performance_data(self, client: ZenooClient, supplier_id: int) -> Dict:
        """Get supplier performance data."""
        
        # Get purchase orders
        purchase_orders = await client.search_read(
            'purchase.order',
            [('partner_id', '=', supplier_id)],
            ['name', 'state', 'date_order', 'date_planned', 'amount_total']
        )
        
        # Get delivery performance
        pickings = await client.search_read(
            'stock.picking',
            [('partner_id', '=', supplier_id), ('picking_type_code', '=', 'incoming')],
            ['name', 'state', 'scheduled_date', 'date_done']
        )
        
        return {
            'purchase_orders': purchase_orders,
            'deliveries': pickings,
            'total_orders': len(purchase_orders),
            'on_time_deliveries': len([p for p in pickings if p['date_done'] and p['scheduled_date'] and p['date_done'] <= p['scheduled_date']])
        }
    
    async def _get_route_data(self, client: ZenooClient, origin: str, destinations: List[str]) -> Dict:
        """Get route data for optimization."""
        
        # In a real implementation, this would integrate with mapping APIs
        return {
            'distances': {dest: 100 + hash(dest) % 500 for dest in destinations},
            'costs': {dest: 50 + hash(dest) % 200 for dest in destinations}
        }
    
    async def _get_external_conditions(self, origin: str, destinations: List[str]) -> Dict:
        """Get external conditions affecting logistics."""
        
        # In a real implementation, this would integrate with weather and traffic APIs
        return {
            'weather': 'clear',
            'traffic': 'normal',
            'road_conditions': 'good'
        }
    
    async def _get_supply_chain_status(self, client: ZenooClient) -> Dict:
        """Get current supply chain status."""
        
        # Get inventory levels
        low_stock_products = await client.search_read(
            'stock.quant',
            [('quantity', '<', 10)],
            ['product_id', 'quantity']
        )
        
        # Get pending orders
        pending_orders = await client.search_read(
            'purchase.order',
            [('state', 'in', ['draft', 'sent', 'to approve'])],
            ['name', 'partner_id', 'amount_total']
        )
        
        return {
            'low_stock_products': low_stock_products,
            'pending_orders': pending_orders,
            'total_suppliers': len(set(order['partner_id'][0] for order in pending_orders if order['partner_id']))
        }
    
    async def _get_external_risk_factors(self) -> Dict:
        """Get external risk factors."""
        
        # In a real implementation, this would integrate with news APIs,
        # economic data sources, weather services, etc.
        return {
            'economic_indicators': 'stable',
            'geopolitical_risks': 'low',
            'natural_disasters': 'none',
            'market_volatility': 'normal'
        }
    
    async def _get_product_procurement_data(self, client: ZenooClient, product_id: int) -> Dict:
        """Get product data for procurement analysis."""
        
        product = await client.read('product.product', [product_id])
        
        # Get current stock
        current_stock = await self._get_current_stock(client, product_id)
        
        # Get recent consumption
        recent_moves = await client.search_read(
            'stock.move',
            [
                ('product_id', '=', product_id),
                ('state', '=', 'done'),
                ('date', '>=', (datetime.now() - timedelta(days=30)).isoformat())
            ],
            ['product_uom_qty', 'date']
        )
        
        return {
            'product_info': product[0] if product else {},
            'current_stock': current_stock,
            'recent_consumption': sum(move['product_uom_qty'] for move in recent_moves)
        }
    
    async def _get_supplier_options(self, client: ZenooClient, product_id: int) -> List[Dict]:
        """Get supplier options for a product."""
        
        # Get product suppliers
        supplier_infos = await client.search_read(
            'product.supplierinfo',
            [('product_id', '=', product_id)],
            ['name', 'price', 'min_qty', 'delay']
        )
        
        return supplier_infos


async def main():
    """Example usage of the Supply Chain Optimization system."""
    
    # Initialize optimization system
    sc_optimization = SupplyChainOptimization(
        odoo_url="http://localhost:8069",
        database="demo",
        username="admin",
        password="admin"
    )
    
    try:
        # Example: Generate demand forecast
        logger.info("Generating demand forecast...")
        
        forecast = await sc_optimization.generate_demand_forecast(product_id=1, forecast_periods=6)
        logger.info(f"Demand forecast for {forecast.product_name}:")
        logger.info(f"  Current stock: {forecast.current_stock}")
        logger.info(f"  Reorder point: {forecast.reorder_point}")
        logger.info(f"  Optimal order quantity: {forecast.optimal_order_quantity}")
        logger.info(f"  Confidence: {forecast.confidence_level}")
        
        # Example: Analyze supplier performance
        logger.info("Analyzing supplier performance...")
        
        supplier_analysis = await sc_optimization.analyze_supplier_performance(supplier_id=1)
        logger.info(f"Supplier analysis for {supplier_analysis.supplier_name}:")
        logger.info(f"  Overall rating: {supplier_analysis.overall_rating.value}")
        logger.info(f"  Performance score: {supplier_analysis.performance_score}")
        logger.info(f"  Delivery reliability: {supplier_analysis.delivery_reliability}")
        logger.info(f"  Risk level: {supplier_analysis.risk_assessment.value}")
        
        # Example: Optimize logistics route
        logger.info("Optimizing logistics route...")
        
        route_optimization = await sc_optimization.optimize_logistics_route(
            origin="Warehouse A",
            destinations=["Customer 1", "Customer 2", "Customer 3"]
        )
        
        logger.info(f"Route optimization:")
        logger.info(f"  Optimized route: {' -> '.join(route_optimization.optimized_route)}")
        logger.info(f"  Estimated cost: ${route_optimization.estimated_cost}")
        logger.info(f"  Estimated time: {route_optimization.estimated_time} minutes")
        
        # Example: Monitor supply chain risks
        logger.info("Monitoring supply chain risks...")
        
        risk_alerts = await sc_optimization.monitor_supply_chain_risks()
        
        for alert in risk_alerts:
            logger.warning(f"Risk Alert: {alert.alert_type} - {alert.severity.value}")
            logger.warning(f"  Description: {alert.description}")
            logger.warning(f"  Impact: ${alert.estimated_impact_cost}")
        
        # Example: Generate procurement recommendations
        logger.info("Generating procurement recommendations...")
        
        recommendations = await sc_optimization.generate_procurement_recommendations([1, 2])
        
        for rec in recommendations:
            logger.info(f"Procurement recommendation for product {rec['product_id']}:")
            logger.info(f"  Recommended supplier: {rec.get('recommended_supplier', 'N/A')}")
            logger.info(f"  Order quantity: {rec.get('order_quantity', 'N/A')}")
            logger.info(f"  Timing: {rec.get('timing', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Supply chain optimization failed: {e}")
        raise


if __name__ == "__main__":
    import os
    
    # Ensure API key is set
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        exit(1)
    
    asyncio.run(main())
