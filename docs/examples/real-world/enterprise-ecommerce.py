#!/usr/bin/env python3
"""
Enterprise E-commerce Integration with AI-Powered Features

This example demonstrates a production-ready e-commerce integration using
Zenoo RPC's AI capabilities for:
- Intelligent product synchronization
- AI-powered inventory management
- Smart order processing
- Automated customer insights
- Performance optimization

Based on real-world Gemini API production patterns and best practices.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError


# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecommerce_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProductSyncResult:
    """Result of product synchronization operation."""
    success_count: int
    error_count: int
    skipped_count: int
    processing_time: float
    errors: List[str]


@dataclass
class AIInsight:
    """AI-generated business insight."""
    category: str
    insight: str
    confidence: float
    recommended_actions: List[str]
    data_source: str


class EnterpriseEcommerceIntegration:
    """
    Production-ready e-commerce integration with AI capabilities.
    
    Features:
    - Intelligent product synchronization with conflict resolution
    - AI-powered inventory optimization
    - Smart order processing and routing
    - Automated customer behavior analysis
    - Performance monitoring and optimization
    """
    
    def __init__(self, odoo_url: str, database: str, username: str, password: str):
        self.odoo_url = odoo_url
        self.database = database
        self.username = username
        self.password = password
        self.client: Optional[ZenooClient] = None
        self.performance_metrics = {
            'sync_times': [],
            'ai_response_times': [],
            'error_rates': [],
            'throughput': []
        }
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager for Odoo client with proper cleanup."""
        client = ZenooClient(self.odoo_url)
        try:
            await client.login(self.database, self.username, self.password)
            
            # Setup AI with production configuration
            await client.setup_ai(
                provider="gemini",
                model="gemini-2.5-flash-lite",  # Fast for production
                api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.1,  # Deterministic for business logic
                max_tokens=4096,
                timeout=30.0,
                max_retries=3
            )
            
            yield client
            
        except Exception as e:
            logger.error(f"Client setup failed: {e}")
            raise
        finally:
            await client.close()
    
    async def intelligent_product_sync(self, external_products: List[Dict]) -> ProductSyncResult:
        """
        Intelligent product synchronization with AI-powered conflict resolution.
        
        Features:
        - Duplicate detection and merging
        - Price optimization suggestions
        - Category mapping with AI
        - Inventory level optimization
        """
        start_time = time.time()
        success_count = 0
        error_count = 0
        skipped_count = 0
        errors = []
        
        async with self.get_client() as client:
            logger.info(f"Starting sync of {len(external_products)} products")
            
            for product_data in external_products:
                try:
                    # AI-powered duplicate detection
                    duplicate_check = await self._check_product_duplicates(
                        client, product_data
                    )
                    
                    if duplicate_check['is_duplicate']:
                        # AI-guided merge strategy
                        merge_result = await self._merge_product_intelligently(
                            client, product_data, duplicate_check['existing_product']
                        )
                        
                        if merge_result['action'] == 'skip':
                            skipped_count += 1
                            continue
                        elif merge_result['action'] == 'update':
                            await self._update_product_with_ai_insights(
                                client, duplicate_check['existing_product']['id'], 
                                merge_result['merged_data']
                            )
                    else:
                        # Create new product with AI enhancements
                        enhanced_product = await self._enhance_product_with_ai(
                            client, product_data
                        )
                        
                        await client.create('product.product', enhanced_product)
                    
                    success_count += 1
                    
                    # Rate limiting to avoid API overload
                    if success_count % 50 == 0:
                        await asyncio.sleep(1)
                        logger.info(f"Processed {success_count} products...")
                
                except Exception as e:
                    error_count += 1
                    error_msg = f"Product sync failed for {product_data.get('name', 'unknown')}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
                    # Circuit breaker pattern
                    if error_count > len(external_products) * 0.1:  # 10% error threshold
                        logger.error("Error rate too high, stopping sync")
                        break
        
        processing_time = time.time() - start_time
        self.performance_metrics['sync_times'].append(processing_time)
        
        result = ProductSyncResult(
            success_count=success_count,
            error_count=error_count,
            skipped_count=skipped_count,
            processing_time=processing_time,
            errors=errors
        )
        
        logger.info(f"Sync completed: {success_count} success, {error_count} errors, {processing_time:.2f}s")
        return result
    
    async def _check_product_duplicates(self, client: ZenooClient, product_data: Dict) -> Dict:
        """Use AI to detect potential product duplicates."""
        
        # Search for similar products
        similar_products = await client.search_read(
            'product.product',
            [('name', 'ilike', product_data['name'][:20])],
            ['name', 'default_code', 'barcode', 'list_price']
        )
        
        if not similar_products:
            return {'is_duplicate': False}
        
        # AI analysis for duplicate detection
        duplicate_analysis = await client.ai.chat(
            f"Analyze if this product is a duplicate:\n"
            f"New Product: {product_data}\n"
            f"Existing Products: {similar_products}\n"
            f"Consider name similarity, SKU, barcode, and price.\n"
            f"Respond with JSON: {{'is_duplicate': bool, 'confidence': float, 'best_match_id': int or null}}",
            context="Product duplicate detection"
        )
        
        try:
            import json
            analysis = json.loads(duplicate_analysis)
            
            if analysis['is_duplicate'] and analysis['confidence'] > 0.8:
                best_match = next(
                    (p for p in similar_products if p['id'] == analysis['best_match_id']), 
                    None
                )
                return {
                    'is_duplicate': True,
                    'confidence': analysis['confidence'],
                    'existing_product': best_match
                }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"AI duplicate analysis parsing failed: {e}")
        
        return {'is_duplicate': False}
    
    async def _merge_product_intelligently(self, client: ZenooClient, 
                                         new_product: Dict, existing_product: Dict) -> Dict:
        """AI-guided product merging strategy."""
        
        merge_strategy = await client.ai.chat(
            f"Determine the best merge strategy for these products:\n"
            f"New: {new_product}\n"
            f"Existing: {existing_product}\n"
            f"Consider: price differences, stock levels, descriptions, specifications.\n"
            f"Respond with JSON: {{'action': 'skip|update|create_variant', 'merged_data': dict, 'reasoning': str}}",
            context="Product merge strategy"
        )
        
        try:
            import json
            return json.loads(merge_strategy)
        except json.JSONDecodeError:
            # Fallback to conservative approach
            return {
                'action': 'skip',
                'merged_data': {},
                'reasoning': 'AI analysis failed, skipping to avoid conflicts'
            }
    
    async def _enhance_product_with_ai(self, client: ZenooClient, product_data: Dict) -> Dict:
        """Enhance product data with AI-generated insights."""
        
        # AI-powered category suggestion
        category_suggestion = await client.ai.chat(
            f"Suggest the best Odoo product category for: {product_data}\n"
            f"Consider product name, description, and type.\n"
            f"Respond with category name only.",
            context="Product category classification"
        )
        
        # AI-powered SEO optimization
        seo_optimization = await client.ai.chat(
            f"Optimize this product for SEO:\n"
            f"Product: {product_data}\n"
            f"Generate: improved name, meta description, keywords.\n"
            f"Respond with JSON: {{'optimized_name': str, 'meta_description': str, 'keywords': list}}",
            context="Product SEO optimization"
        )
        
        enhanced_product = product_data.copy()
        
        try:
            import json
            seo_data = json.loads(seo_optimization)
            
            enhanced_product.update({
                'name': seo_data.get('optimized_name', product_data['name']),
                'website_meta_description': seo_data.get('meta_description', ''),
                'website_meta_keywords': ', '.join(seo_data.get('keywords', []))
            })
        except json.JSONDecodeError:
            logger.warning("SEO optimization parsing failed, using original data")
        
        return enhanced_product
    
    async def _update_product_with_ai_insights(self, client: ZenooClient, 
                                             product_id: int, merged_data: Dict):
        """Update product with AI-enhanced data."""
        
        # Get current product data
        current_product = await client.read('product.product', [product_id])
        
        if not current_product:
            raise ValueError(f"Product {product_id} not found")
        
        # AI-powered update strategy
        update_strategy = await client.ai.chat(
            f"Determine safe updates for this product:\n"
            f"Current: {current_product[0]}\n"
            f"Proposed: {merged_data}\n"
            f"Avoid breaking changes. Focus on: price, description, stock.\n"
            f"Respond with JSON of safe updates only.",
            context="Product update strategy"
        )
        
        try:
            import json
            safe_updates = json.loads(update_strategy)
            
            if safe_updates:
                await client.write('product.product', [product_id], safe_updates)
                logger.info(f"Updated product {product_id} with AI insights")
        except json.JSONDecodeError:
            logger.warning(f"Update strategy parsing failed for product {product_id}")
    
    async def generate_inventory_insights(self) -> List[AIInsight]:
        """Generate AI-powered inventory management insights."""
        
        async with self.get_client() as client:
            # Get inventory data
            inventory_data = await client.search_read(
                'stock.quant',
                [('quantity', '>', 0)],
                ['product_id', 'quantity', 'location_id']
            )
            
            # Get sales data for trend analysis
            recent_sales = await client.search_read(
                'sale.order.line',
                [('create_date', '>=', (datetime.now() - timedelta(days=30)).isoformat())],
                ['product_id', 'product_uom_qty', 'price_unit']
            )
            
            # AI analysis for inventory optimization
            insights_analysis = await client.ai.chat(
                f"Analyze inventory data and provide actionable insights:\n"
                f"Current Inventory: {inventory_data[:50]}...\n"  # Limit for token efficiency
                f"Recent Sales: {recent_sales[:50]}...\n"
                f"Identify: overstocked items, understocked items, fast movers, slow movers.\n"
                f"Provide specific recommendations with confidence levels.\n"
                f"Respond with JSON array of insights.",
                context="Inventory optimization analysis"
            )
            
            try:
                import json
                insights_data = json.loads(insights_analysis)
                
                insights = []
                for insight_data in insights_data:
                    insight = AIInsight(
                        category=insight_data.get('category', 'inventory'),
                        insight=insight_data.get('insight', ''),
                        confidence=insight_data.get('confidence', 0.5),
                        recommended_actions=insight_data.get('recommended_actions', []),
                        data_source='inventory_analysis'
                    )
                    insights.append(insight)
                
                return insights
                
            except json.JSONDecodeError:
                logger.error("Failed to parse inventory insights")
                return []
    
    async def optimize_order_processing(self, order_data: Dict) -> Dict:
        """AI-powered order processing optimization."""
        
        async with self.get_client() as client:
            # AI analysis for order routing and prioritization
            order_optimization = await client.ai.chat(
                f"Optimize this order processing:\n"
                f"Order: {order_data}\n"
                f"Consider: customer priority, product availability, shipping costs, delivery time.\n"
                f"Suggest: warehouse selection, shipping method, processing priority.\n"
                f"Respond with JSON: {{'warehouse_id': int, 'shipping_method': str, 'priority': str, 'estimated_delivery': str}}",
                context="Order processing optimization"
            )
            
            try:
                import json
                optimization = json.loads(order_optimization)
                
                # Apply optimizations to order
                optimized_order = order_data.copy()
                optimized_order.update({
                    'warehouse_id': optimization.get('warehouse_id'),
                    'carrier_id': await self._get_carrier_id(client, optimization.get('shipping_method')),
                    'priority': optimization.get('priority', 'normal'),
                    'commitment_date': optimization.get('estimated_delivery')
                })
                
                return optimized_order
                
            except json.JSONDecodeError:
                logger.warning("Order optimization parsing failed")
                return order_data
    
    async def _get_carrier_id(self, client: ZenooClient, shipping_method: str) -> Optional[int]:
        """Get carrier ID based on shipping method name."""
        if not shipping_method:
            return None
        
        carriers = await client.search_read(
            'delivery.carrier',
            [('name', 'ilike', shipping_method)],
            ['id', 'name']
        )
        
        return carriers[0]['id'] if carriers else None
    
    async def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report with AI insights."""
        
        metrics = self.performance_metrics
        
        async with self.get_client() as client:
            # AI analysis of performance metrics
            performance_analysis = await client.ai.chat(
                f"Analyze these performance metrics and provide optimization recommendations:\n"
                f"Sync Times: {metrics['sync_times'][-10:] if metrics['sync_times'] else []}\n"
                f"AI Response Times: {metrics['ai_response_times'][-10:] if metrics['ai_response_times'] else []}\n"
                f"Error Rates: {metrics['error_rates'][-10:] if metrics['error_rates'] else []}\n"
                f"Provide specific recommendations for improvement.\n"
                f"Respond with JSON: {{'overall_health': str, 'bottlenecks': list, 'recommendations': list}}",
                context="Performance analysis and optimization"
            )
            
            try:
                import json
                analysis = json.loads(performance_analysis)
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'metrics': metrics,
                    'ai_analysis': analysis,
                    'summary': {
                        'avg_sync_time': sum(metrics['sync_times']) / len(metrics['sync_times']) if metrics['sync_times'] else 0,
                        'total_operations': len(metrics['sync_times']),
                        'error_rate': sum(metrics['error_rates']) / len(metrics['error_rates']) if metrics['error_rates'] else 0
                    }
                }
                
            except json.JSONDecodeError:
                logger.error("Performance analysis parsing failed")
                return {'error': 'Analysis failed', 'metrics': metrics}


async def main():
    """Example usage of the Enterprise E-commerce Integration."""
    
    # Initialize integration
    integration = EnterpriseEcommerceIntegration(
        odoo_url="http://localhost:8069",
        database="demo",
        username="admin",
        password="admin"
    )
    
    # Example external product data
    external_products = [
        {
            'name': 'Premium Wireless Headphones',
            'default_code': 'PWH001',
            'list_price': 299.99,
            'description': 'High-quality wireless headphones with noise cancellation',
            'barcode': '1234567890123'
        },
        {
            'name': 'Smart Fitness Tracker',
            'default_code': 'SFT002',
            'list_price': 199.99,
            'description': 'Advanced fitness tracker with heart rate monitoring',
            'barcode': '1234567890124'
        }
    ]
    
    try:
        # Intelligent product synchronization
        logger.info("Starting intelligent product sync...")
        sync_result = await integration.intelligent_product_sync(external_products)
        logger.info(f"Sync completed: {sync_result}")
        
        # Generate inventory insights
        logger.info("Generating inventory insights...")
        insights = await integration.generate_inventory_insights()
        for insight in insights:
            logger.info(f"Insight: {insight.insight} (Confidence: {insight.confidence})")
        
        # Generate performance report
        logger.info("Generating performance report...")
        report = await integration.generate_performance_report()
        logger.info(f"Performance report: {report}")
        
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        raise


if __name__ == "__main__":
    import os
    
    # Ensure API key is set
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        exit(1)
    
    asyncio.run(main())
