"""
Comprehensive Performance Test Scenarios

This module provides detailed test scenarios for comprehensive performance
analysis including stress testing, load patterns, edge cases, and
real-world workflow simulations.
"""

import asyncio
import time
import random
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import concurrent.futures
import threading
from contextlib import asynccontextmanager
import numpy as np

from advanced_metrics import DetailedMetrics, measure_performance, SystemMonitor


@dataclass
class TestScenario:
    """Test scenario configuration."""
    
    name: str
    description: str
    iterations: int
    concurrent_users: int
    data_size: str  # "small", "medium", "large", "xlarge"
    complexity: str  # "simple", "medium", "complex"
    duration_seconds: Optional[int] = None
    ramp_up_seconds: int = 0
    think_time_ms: int = 0
    error_threshold: float = 5.0  # Max acceptable error rate %
    
    def get_data_size_multiplier(self) -> int:
        """Get data size multiplier based on size category."""
        multipliers = {
            "small": 1,
            "medium": 10,
            "large": 100,
            "xlarge": 1000
        }
        return multipliers.get(self.data_size, 1)
    
    def get_complexity_factor(self) -> float:
        """Get complexity factor for operations."""
        factors = {
            "simple": 1.0,
            "medium": 2.5,
            "complex": 5.0
        }
        return factors.get(self.complexity, 1.0)


class ComprehensiveTestSuite:
    """Comprehensive test suite with advanced scenarios."""
    
    def __init__(self):
        """Initialize test suite."""
        self.scenarios = self._define_test_scenarios()
        self.results = {}
        self.global_metrics = {}
    
    def _define_test_scenarios(self) -> Dict[str, TestScenario]:
        """Define comprehensive test scenarios."""
        return {
            # Basic CRUD scenarios with varying loads
            "crud_light_load": TestScenario(
                name="CRUD Light Load",
                description="Basic CRUD operations with minimal load",
                iterations=50,
                concurrent_users=1,
                data_size="small",
                complexity="simple",
                think_time_ms=100
            ),
            
            "crud_medium_load": TestScenario(
                name="CRUD Medium Load",
                description="CRUD operations with moderate concurrent load",
                iterations=100,
                concurrent_users=5,
                data_size="medium",
                complexity="medium",
                think_time_ms=50
            ),
            
            "crud_heavy_load": TestScenario(
                name="CRUD Heavy Load",
                description="CRUD operations under heavy concurrent load",
                iterations=200,
                concurrent_users=20,
                data_size="large",
                complexity="complex",
                think_time_ms=10
            ),
            
            # Stress testing scenarios
            "stress_concurrent_reads": TestScenario(
                name="Stress Concurrent Reads",
                description="Maximum concurrent read operations",
                iterations=500,
                concurrent_users=50,
                data_size="medium",
                complexity="simple",
                duration_seconds=60,
                ramp_up_seconds=10
            ),
            
            "stress_mixed_operations": TestScenario(
                name="Stress Mixed Operations",
                description="Mixed CRUD operations under stress",
                iterations=300,
                concurrent_users=30,
                data_size="large",
                complexity="complex",
                duration_seconds=120,
                ramp_up_seconds=15
            ),
            
            # Endurance testing
            "endurance_long_running": TestScenario(
                name="Endurance Long Running",
                description="Long-running operations for stability testing",
                iterations=1000,
                concurrent_users=10,
                data_size="medium",
                complexity="medium",
                duration_seconds=300,  # 5 minutes
                think_time_ms=200
            ),
            
            # Memory stress scenarios
            "memory_large_datasets": TestScenario(
                name="Memory Large Datasets",
                description="Processing large datasets to test memory efficiency",
                iterations=50,
                concurrent_users=5,
                data_size="xlarge",
                complexity="complex",
                think_time_ms=500
            ),
            
            # Network intensive scenarios
            "network_bulk_transfer": TestScenario(
                name="Network Bulk Transfer",
                description="Large data transfers to test network efficiency",
                iterations=100,
                concurrent_users=10,
                data_size="large",
                complexity="medium",
                think_time_ms=100
            ),
            
            # Real-world workflow scenarios
            "workflow_sales_process": TestScenario(
                name="Sales Process Workflow",
                description="Complete sales order workflow simulation",
                iterations=100,
                concurrent_users=8,
                data_size="medium",
                complexity="complex",
                think_time_ms=300
            ),
            
            "workflow_inventory_management": TestScenario(
                name="Inventory Management Workflow",
                description="Inventory operations and stock movements",
                iterations=150,
                concurrent_users=12,
                data_size="large",
                complexity="complex",
                think_time_ms=200
            ),
            
            # Edge case scenarios
            "edge_case_timeouts": TestScenario(
                name="Edge Case Timeouts",
                description="Testing timeout handling and recovery",
                iterations=50,
                concurrent_users=5,
                data_size="small",
                complexity="simple",
                error_threshold=20.0  # Higher threshold for timeout testing
            ),
            
            "edge_case_large_payloads": TestScenario(
                name="Edge Case Large Payloads",
                description="Testing with extremely large request/response payloads",
                iterations=20,
                concurrent_users=2,
                data_size="xlarge",
                complexity="complex",
                think_time_ms=1000
            )
        }
    
    async def run_scenario(
        self, 
        scenario_name: str, 
        zenoo_client_factory: Callable,
        odoorpc_client_factory: Callable
    ) -> Dict[str, Any]:
        """Run a specific test scenario."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        scenario = self.scenarios[scenario_name]
        print(f"\n🧪 Running Scenario: {scenario.name}")
        print(f"   Description: {scenario.description}")
        print(f"   Config: {scenario.iterations} iterations, {scenario.concurrent_users} users")
        
        results = {
            "scenario": scenario,
            "zenoo_rpc": None,
            "odoorpc": None,
            "comparison": None
        }
        
        # Test zenoo_rpc
        print(f"   🔧 Testing zenoo_rpc...")
        zenoo_metrics = await self._run_library_test(
            scenario, "zenoo_rpc", zenoo_client_factory
        )
        results["zenoo_rpc"] = zenoo_metrics
        
        # Test odoorpc
        print(f"   🔧 Testing odoorpc...")
        odoorpc_metrics = await self._run_library_test(
            scenario, "odoorpc", odoorpc_client_factory
        )
        results["odoorpc"] = odoorpc_metrics
        
        # Generate comparison
        results["comparison"] = self._compare_results(zenoo_metrics, odoorpc_metrics)
        
        # Store results
        self.results[scenario_name] = results
        
        print(f"   ✅ Scenario completed")
        return results
    
    async def _run_library_test(
        self, 
        scenario: TestScenario, 
        library: str,
        client_factory: Callable
    ) -> DetailedMetrics:
        """Run test for specific library."""
        metrics = DetailedMetrics(
            operation=scenario.name,
            library=library,
            test_id=f"{scenario.name}_{library}_{int(time.time())}"
        )
        
        # Create client
        client = await client_factory()
        
        try:
            if scenario.concurrent_users == 1:
                # Sequential execution
                await self._run_sequential_test(scenario, client, metrics)
            else:
                # Concurrent execution
                await self._run_concurrent_test(scenario, client, metrics)
        
        finally:
            # Cleanup client
            if hasattr(client, 'close'):
                await client.close()
            elif hasattr(client, 'logout'):
                client.logout()
        
        return metrics
    
    async def _run_sequential_test(
        self, 
        scenario: TestScenario, 
        client: Any, 
        metrics: DetailedMetrics
    ):
        """Run sequential test operations."""
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = datetime.now()
        
        for i in range(scenario.iterations):
            try:
                # Simulate think time
                if scenario.think_time_ms > 0:
                    await asyncio.sleep(scenario.think_time_ms / 1000)
                
                # Execute operation based on scenario
                operation_start = time.perf_counter()
                await self._execute_scenario_operation(scenario, client, i)
                operation_end = time.perf_counter()
                
                response_time = (operation_end - operation_start) * 1000
                metrics.add_response_time(response_time, success=True)
                
                # Add system metrics
                current_metrics = monitor.get_current_metrics()
                if current_metrics:
                    metrics.add_system_metrics(
                        current_metrics.get("cpu_percent", 0),
                        current_metrics.get("memory_mb", 0)
                    )
                    metrics.add_network_metrics(
                        current_metrics.get("bytes_sent", 0),
                        current_metrics.get("bytes_received", 0)
                    )
                
            except Exception as e:
                operation_end = time.perf_counter()
                response_time = (operation_end - operation_start) * 1000
                metrics.add_response_time(response_time, success=False)
                metrics.add_error(
                    error_type=type(e).__name__,
                    message=str(e)
                )
        
        end_time = datetime.now()
        metrics.start_time = start_time
        metrics.end_time = end_time
        metrics.total_duration = (end_time - start_time).total_seconds()
        
        # Stop monitoring
        system_metrics = monitor.stop_monitoring()
        if "cpu_usage" in system_metrics:
            metrics.cpu_usage.extend(system_metrics["cpu_usage"])
        if "memory_usage" in system_metrics:
            metrics.memory_usage.extend(system_metrics["memory_usage"])
    
    async def _run_concurrent_test(
        self, 
        scenario: TestScenario, 
        client: Any, 
        metrics: DetailedMetrics
    ):
        """Run concurrent test operations."""
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = datetime.now()
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(scenario.concurrent_users)
        
        async def worker(worker_id: int):
            """Worker function for concurrent execution."""
            async with semaphore:
                iterations_per_worker = scenario.iterations // scenario.concurrent_users
                
                for i in range(iterations_per_worker):
                    try:
                        # Simulate think time
                        if scenario.think_time_ms > 0:
                            await asyncio.sleep(scenario.think_time_ms / 1000)
                        
                        # Execute operation
                        operation_start = time.perf_counter()
                        await self._execute_scenario_operation(scenario, client, i)
                        operation_end = time.perf_counter()
                        
                        response_time = (operation_end - operation_start) * 1000
                        metrics.add_response_time(response_time, success=True)
                        
                    except Exception as e:
                        operation_end = time.perf_counter()
                        response_time = (operation_end - operation_start) * 1000
                        metrics.add_response_time(response_time, success=False)
                        metrics.add_error(
                            error_type=type(e).__name__,
                            message=str(e)
                        )
        
        # Create and run workers
        tasks = [worker(i) for i in range(scenario.concurrent_users)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        metrics.start_time = start_time
        metrics.end_time = end_time
        metrics.total_duration = (end_time - start_time).total_seconds()
        metrics.concurrent_operations = scenario.concurrent_users
        
        # Stop monitoring
        system_metrics = monitor.stop_monitoring()
        if "cpu_usage" in system_metrics:
            metrics.cpu_usage.extend(system_metrics["cpu_usage"])
        if "memory_usage" in system_metrics:
            metrics.memory_usage.extend(system_metrics["memory_usage"])
    
    async def _execute_scenario_operation(
        self, 
        scenario: TestScenario, 
        client: Any, 
        iteration: int
    ):
        """Execute specific operation based on scenario type."""
        data_multiplier = scenario.get_data_size_multiplier()
        complexity_factor = scenario.get_complexity_factor()
        
        # Determine operation type based on scenario name and iteration
        operation_type = self._get_operation_type(scenario.name, iteration)
        
        if operation_type == "read":
            await self._execute_read_operation(client, data_multiplier, complexity_factor)
        elif operation_type == "create":
            await self._execute_create_operation(client, data_multiplier, complexity_factor)
        elif operation_type == "update":
            await self._execute_update_operation(client, data_multiplier, complexity_factor)
        elif operation_type == "delete":
            await self._execute_delete_operation(client, data_multiplier, complexity_factor)
        elif operation_type == "workflow":
            await self._execute_workflow_operation(client, scenario.name, complexity_factor)
        else:
            # Default to read operation
            await self._execute_read_operation(client, data_multiplier, complexity_factor)
    
    def _get_operation_type(self, scenario_name: str, iteration: int) -> str:
        """Determine operation type based on scenario and iteration."""
        if "read" in scenario_name.lower():
            return "read"
        elif "workflow" in scenario_name.lower():
            return "workflow"
        elif "memory" in scenario_name.lower() or "bulk" in scenario_name.lower():
            return "read"  # Large data reads for memory/network testing
        else:
            # Mixed operations - cycle through CRUD
            operations = ["read", "create", "update", "delete"]
            return operations[iteration % len(operations)]
    
    async def _execute_read_operation(self, client: Any, data_multiplier: int, complexity_factor: float):
        """Execute read operation with specified complexity."""
        limit = min(int(10 * data_multiplier), 1000)  # Cap at 1000 records
        
        if hasattr(client, 'search_read'):
            # zenoo_rpc client
            return await client.search_read(
                "res.partner",
                domain=[],
                fields=["name", "email", "is_company", "customer_rank"],
                limit=limit
            )
        else:
            # odoorpc client
            Partner = client.env['res.partner']
            return Partner.search_read(
                [],
                ['name', 'email', 'is_company', 'customer_rank'],
                limit=limit
            )
    
    async def _execute_create_operation(self, client: Any, data_multiplier: int, complexity_factor: float):
        """Execute create operation with specified complexity."""
        # Create test data
        partner_data = {
            "name": f"Test Partner {int(time.time() * 1000)}",
            "email": f"test{int(time.time() * 1000)}@benchmark.com",
            "is_company": random.choice([True, False]),
            "customer_rank": 1
        }
        
        # Add complexity with additional fields
        if complexity_factor > 2.0:
            partner_data.update({
                "phone": f"+1-555-{random.randint(1000, 9999)}",
                "website": f"https://test{int(time.time())}.com",
                "comment": f"Benchmark test partner created at {datetime.now()}"
            })
        
        if hasattr(client, 'execute_kw'):
            # zenoo_rpc client
            return await client.execute_kw(
                "res.partner",
                "create",
                [partner_data]
            )
        else:
            # odoorpc client
            Partner = client.env['res.partner']
            return Partner.create(partner_data)
    
    async def _execute_update_operation(self, client: Any, data_multiplier: int, complexity_factor: float):
        """Execute update operation with specified complexity."""
        # First find a record to update
        if hasattr(client, 'search'):
            # zenoo_rpc client
            partner_ids = await client.search("res.partner", domain=[], limit=1)
            if partner_ids:
                return await client.execute_kw(
                    "res.partner",
                    "write",
                    [partner_ids, {"name": f"Updated Partner {int(time.time())}"}]
                )
        else:
            # odoorpc client
            Partner = client.env['res.partner']
            partner_ids = Partner.search([], limit=1)
            if partner_ids:
                partner = Partner.browse(partner_ids[0])
                return partner.write({"name": f"Updated Partner {int(time.time())}"})
        
        return None
    
    async def _execute_delete_operation(self, client: Any, data_multiplier: int, complexity_factor: float):
        """Execute delete operation (simulated - we don't actually delete)."""
        # For safety, we'll just simulate delete by doing a read operation
        # In real scenarios, you might create temporary records to delete
        return await self._execute_read_operation(client, 1, 1.0)
    
    async def _execute_workflow_operation(self, client: Any, scenario_name: str, complexity_factor: float):
        """Execute complex workflow operations."""
        if "sales" in scenario_name.lower():
            return await self._execute_sales_workflow(client, complexity_factor)
        elif "inventory" in scenario_name.lower():
            return await self._execute_inventory_workflow(client, complexity_factor)
        else:
            return await self._execute_read_operation(client, 1, complexity_factor)
    
    async def _execute_sales_workflow(self, client: Any, complexity_factor: float):
        """Execute sales workflow simulation."""
        # Simplified sales workflow: search customers, products, create order
        try:
            if hasattr(client, 'search_read'):
                # zenoo_rpc client
                customers = await client.search_read(
                    "res.partner",
                    domain=[("customer_rank", ">", 0)],
                    fields=["name", "email"],
                    limit=5
                )
                
                products = await client.search_read(
                    "product.product",
                    domain=[("sale_ok", "=", True)],
                    fields=["name", "list_price"],
                    limit=3
                )
                
                return {"customers": len(customers), "products": len(products)}
            else:
                # odoorpc client
                Partner = client.env['res.partner']
                Product = client.env['product.product']
                
                customers = Partner.search_read(
                    [('customer_rank', '>', 0)],
                    ['name', 'email'],
                    limit=5
                )
                
                products = Product.search_read(
                    [('sale_ok', '=', True)],
                    ['name', 'list_price'],
                    limit=3
                )
                
                return {"customers": len(customers), "products": len(products)}
        
        except Exception as e:
            # Fallback to simple read if models don't exist
            return await self._execute_read_operation(client, 1, complexity_factor)
    
    async def _execute_inventory_workflow(self, client: Any, complexity_factor: float):
        """Execute inventory workflow simulation."""
        # Simplified inventory workflow: search products and stock
        try:
            if hasattr(client, 'search_read'):
                # zenoo_rpc client
                products = await client.search_read(
                    "product.product",
                    domain=[("type", "=", "product")],
                    fields=["name", "qty_available"],
                    limit=10
                )
                return {"products": len(products)}
            else:
                # odoorpc client
                Product = client.env['product.product']
                products = Product.search_read(
                    [('type', '=', 'product')],
                    ['name', 'qty_available'],
                    limit=10
                )
                return {"products": len(products)}
        
        except Exception as e:
            # Fallback to simple read if models don't exist
            return await self._execute_read_operation(client, 1, complexity_factor)
    
    def _compare_results(self, zenoo_metrics: DetailedMetrics, odoorpc_metrics: DetailedMetrics) -> Dict[str, Any]:
        """Compare results between zenoo_rpc and odoorpc."""
        if not zenoo_metrics.response_times or not odoorpc_metrics.response_times:
            return {"error": "Insufficient data for comparison"}
        
        # Response time comparison
        response_time_improvement = (
            (odoorpc_metrics.avg_response_time - zenoo_metrics.avg_response_time) /
            odoorpc_metrics.avg_response_time * 100
        ) if odoorpc_metrics.avg_response_time > 0 else 0
        
        # Throughput comparison
        throughput_improvement = (
            (zenoo_metrics.throughput - odoorpc_metrics.throughput) /
            odoorpc_metrics.throughput * 100
        ) if odoorpc_metrics.throughput > 0 else 0
        
        # Error rate comparison
        error_rate_improvement = odoorpc_metrics.error_rate - zenoo_metrics.error_rate
        
        # Memory usage comparison
        memory_improvement = (
            (odoorpc_metrics.avg_memory_usage - zenoo_metrics.avg_memory_usage) /
            odoorpc_metrics.avg_memory_usage * 100
        ) if odoorpc_metrics.avg_memory_usage > 0 else 0
        
        return {
            "response_time_improvement_percent": response_time_improvement,
            "throughput_improvement_percent": throughput_improvement,
            "error_rate_improvement_percent": error_rate_improvement,
            "memory_improvement_percent": memory_improvement,
            "statistical_significance": self._calculate_statistical_significance(
                zenoo_metrics.response_times,
                odoorpc_metrics.response_times
            ),
            "performance_grade": self._calculate_performance_grade(
                response_time_improvement,
                throughput_improvement,
                error_rate_improvement
            )
        }
    
    def _calculate_statistical_significance(self, zenoo_times: List[float], odoorpc_times: List[float]) -> Dict[str, Any]:
        """Calculate statistical significance of performance difference."""
        try:
            from scipy import stats
            
            # Perform t-test
            t_stat, p_value = stats.ttest_ind(zenoo_times, odoorpc_times)
            
            # Calculate effect size (Cohen's d)
            pooled_std = ((len(zenoo_times) - 1) * np.std(zenoo_times, ddof=1)**2 + 
                         (len(odoorpc_times) - 1) * np.std(odoorpc_times, ddof=1)**2) / \
                        (len(zenoo_times) + len(odoorpc_times) - 2)
            pooled_std = np.sqrt(pooled_std)
            
            cohens_d = (np.mean(zenoo_times) - np.mean(odoorpc_times)) / pooled_std
            
            return {
                "t_statistic": t_stat,
                "p_value": p_value,
                "significant": p_value < 0.05,
                "cohens_d": cohens_d,
                "effect_size": "large" if abs(cohens_d) > 0.8 else "medium" if abs(cohens_d) > 0.5 else "small"
            }
        
        except ImportError:
            # Fallback without scipy
            return {
                "error": "scipy not available for statistical analysis",
                "significant": abs(np.mean(zenoo_times) - np.mean(odoorpc_times)) > 10  # Simple threshold
            }
    
    def _calculate_performance_grade(self, response_improvement: float, throughput_improvement: float, error_improvement: float) -> str:
        """Calculate overall performance grade."""
        score = 0
        
        # Response time score (0-40 points)
        if response_improvement > 50:
            score += 40
        elif response_improvement > 30:
            score += 30
        elif response_improvement > 10:
            score += 20
        elif response_improvement > 0:
            score += 10
        
        # Throughput score (0-40 points)
        if throughput_improvement > 100:
            score += 40
        elif throughput_improvement > 50:
            score += 30
        elif throughput_improvement > 20:
            score += 20
        elif throughput_improvement > 0:
            score += 10
        
        # Error rate score (0-20 points)
        if error_improvement > 5:
            score += 20
        elif error_improvement > 2:
            score += 15
        elif error_improvement > 0:
            score += 10
        elif error_improvement >= -1:
            score += 5
        
        # Convert to grade
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        elif score >= 40:
            return "C"
        else:
            return "D"
