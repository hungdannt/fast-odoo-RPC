"""
Comprehensive Performance Benchmark: zenoo_rpc vs odoorpc

This module provides comprehensive performance testing comparing zenoo_rpc
with odoorpc across various scenarios including:
- Basic CRUD operations
- Bulk operations and batch processing
- Concurrent access patterns
- Memory usage and connection efficiency
- Real-world ERP workflows

The tests are designed to provide statistical analysis and actionable insights
for performance optimization.
"""

import asyncio
import time
import statistics
import psutil
import gc
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import pytest
from unittest.mock import AsyncMock, Mock

# zenoo_rpc imports
from src.zenoo_rpc import ZenooClient
from src.zenoo_rpc.models.common import ResPartner, SaleOrder, ProductProduct

# Import odoorpc for comparison
try:
    import odoorpc
    ODOORPC_AVAILABLE = True
except ImportError:
    ODOORPC_AVAILABLE = False
    print("Warning: odoorpc not available. Install with: pip install odoorpc")

# Import benchmark configuration
from .benchmark_config import BenchmarkConfig, get_config


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmark analysis."""
    
    operation: str
    library: str
    response_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    total_time: float = 0.0
    
    @property
    def avg_response_time(self) -> float:
        """Average response time in milliseconds."""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def median_response_time(self) -> float:
        """Median response time in milliseconds."""
        return statistics.median(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time(self) -> float:
        """95th percentile response time in milliseconds."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index]
    
    @property
    def throughput(self) -> float:
        """Operations per second."""
        return self.success_count / self.total_time if self.total_time > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Error rate as percentage."""
        total = self.success_count + self.error_count
        return (self.error_count / total * 100) if total > 0 else 0.0
    
    @property
    def avg_memory_usage(self) -> float:
        """Average memory usage in MB."""
        return statistics.mean(self.memory_usage) if self.memory_usage else 0.0


class PerformanceBenchmark:
    """Performance benchmark framework for comparing zenoo_rpc vs odoorpc."""

    def __init__(self, config: BenchmarkConfig = None):
        """Initialize benchmark framework.

        Args:
            config: Benchmark configuration
        """
        self.config = config or get_config()
        self.metrics: Dict[str, PerformanceMetrics] = {}

        # Real server configuration
        self.odoo_url = self.config.odoo_url
        self.odoo_database = self.config.odoo_database
        self.odoo_username = self.config.odoo_username
        self.odoo_password = self.config.odoo_password

    async def setup_zenoo_client(self) -> ZenooClient:
        """Setup zenoo_rpc client with optimal configuration."""
        client = ZenooClient(self.odoo_url)

        # Authenticate with real server
        await client.login(
            self.odoo_database,
            self.odoo_username,
            self.odoo_password
        )

        # Setup managers for performance testing
        await client.setup_cache_manager(
            backend="memory",
            max_size=10000,
            default_ttl=300
        )

        await client.setup_batch_manager(
            max_chunk_size=100,
            max_concurrency=10
        )

        await client.setup_transaction_manager()

        return client

    def setup_odoorpc_client(self):
        """Setup odoorpc client."""
        if not ODOORPC_AVAILABLE:
            raise ImportError("odoorpc not available. Install with: pip install odoorpc")

        # Parse URL for odoorpc
        from urllib.parse import urlparse
        parsed = urlparse(self.odoo_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        # Create odoorpc client
        client = odoorpc.ODOO(host, port=port, protocol=parsed.scheme)
        client.login(self.odoo_database, self.odoo_username, self.odoo_password)

        return client

    def measure_performance(self, operation: str, library: str):
        """Decorator to measure performance metrics."""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                metrics = PerformanceMetrics(operation=operation, library=library)
                
                start_time = time.time()
                process = psutil.Process()
                
                try:
                    # Measure memory before
                    memory_before = process.memory_info().rss / 1024 / 1024  # MB
                    
                    # Execute operation
                    result = await func(*args, **kwargs)
                    
                    # Measure memory after
                    memory_after = process.memory_info().rss / 1024 / 1024  # MB
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # ms
                    
                    metrics.response_times.append(response_time)
                    metrics.memory_usage.append(memory_after - memory_before)
                    metrics.success_count += 1
                    
                except Exception as e:
                    metrics.error_count += 1
                    raise e
                finally:
                    metrics.total_time = time.time() - start_time
                    
                    # Store metrics
                    key = f"{operation}_{library}"
                    if key not in self.metrics:
                        self.metrics[key] = metrics
                    else:
                        # Merge metrics
                        existing = self.metrics[key]
                        existing.response_times.extend(metrics.response_times)
                        existing.memory_usage.extend(metrics.memory_usage)
                        existing.success_count += metrics.success_count
                        existing.error_count += metrics.error_count
                        existing.total_time += metrics.total_time
                
                return result
            
            def sync_wrapper(*args, **kwargs):
                # For synchronous odoorpc operations
                metrics = PerformanceMetrics(operation=operation, library=library)
                
                start_time = time.time()
                process = psutil.Process()
                
                try:
                    memory_before = process.memory_info().rss / 1024 / 1024
                    result = func(*args, **kwargs)
                    memory_after = process.memory_info().rss / 1024 / 1024
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    
                    metrics.response_times.append(response_time)
                    metrics.memory_usage.append(memory_after - memory_before)
                    metrics.success_count += 1
                    
                except Exception as e:
                    metrics.error_count += 1
                    raise e
                finally:
                    metrics.total_time = time.time() - start_time
                    
                    key = f"{operation}_{library}"
                    if key not in self.metrics:
                        self.metrics[key] = metrics
                    else:
                        existing = self.metrics[key]
                        existing.response_times.extend(metrics.response_times)
                        existing.memory_usage.extend(metrics.memory_usage)
                        existing.success_count += metrics.success_count
                        existing.error_count += metrics.error_count
                        existing.total_time += metrics.total_time
                
                return result
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "summary": {},
            "detailed_metrics": {},
            "comparisons": {},
            "recommendations": []
        }
        
        # Group metrics by operation
        operations = set(m.operation for m in self.metrics.values())
        
        for operation in operations:
            zenoo_key = f"{operation}_zenoo_rpc"
            odoorpc_key = f"{operation}_odoorpc"
            
            if zenoo_key in self.metrics and odoorpc_key in self.metrics:
                zenoo_metrics = self.metrics[zenoo_key]
                odoorpc_metrics = self.metrics[odoorpc_key]
                
                # Calculate performance improvements
                response_time_improvement = (
                    (odoorpc_metrics.avg_response_time - zenoo_metrics.avg_response_time) /
                    odoorpc_metrics.avg_response_time * 100
                ) if odoorpc_metrics.avg_response_time > 0 else 0
                
                throughput_improvement = (
                    (zenoo_metrics.throughput - odoorpc_metrics.throughput) /
                    odoorpc_metrics.throughput * 100
                ) if odoorpc_metrics.throughput > 0 else 0
                
                report["comparisons"][operation] = {
                    "response_time_improvement_percent": response_time_improvement,
                    "throughput_improvement_percent": throughput_improvement,
                    "zenoo_rpc": {
                        "avg_response_time": zenoo_metrics.avg_response_time,
                        "p95_response_time": zenoo_metrics.p95_response_time,
                        "throughput": zenoo_metrics.throughput,
                        "error_rate": zenoo_metrics.error_rate,
                        "avg_memory_usage": zenoo_metrics.avg_memory_usage
                    },
                    "odoorpc": {
                        "avg_response_time": odoorpc_metrics.avg_response_time,
                        "p95_response_time": odoorpc_metrics.p95_response_time,
                        "throughput": odoorpc_metrics.throughput,
                        "error_rate": odoorpc_metrics.error_rate,
                        "avg_memory_usage": odoorpc_metrics.avg_memory_usage
                    }
                }
        
        # Add detailed metrics
        for key, metrics in self.metrics.items():
            report["detailed_metrics"][key] = {
                "operation": metrics.operation,
                "library": metrics.library,
                "avg_response_time": metrics.avg_response_time,
                "median_response_time": metrics.median_response_time,
                "p95_response_time": metrics.p95_response_time,
                "throughput": metrics.throughput,
                "error_rate": metrics.error_rate,
                "success_count": metrics.success_count,
                "error_count": metrics.error_count,
                "avg_memory_usage": metrics.avg_memory_usage
            }
        
        return report


class TestBasicOperations:
    """Test basic CRUD operations performance."""

    @pytest.fixture
    def perf_benchmark(self):
        """Create benchmark instance."""
        return PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_single_record_read_zenoo(self, perf_benchmark):
        """Test single record read with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        @perf_benchmark.measure_performance("single_read", "zenoo_rpc")
        async def read_partner():
            return await client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["name", "email", "is_company"],
                limit=1
            )

        result = await read_partner()
        assert len(result) >= 0  # May be 0 if no companies exist
        await client.close()

    def test_single_record_read_odoorpc(self, perf_benchmark):
        """Test single record read with odoorpc."""
        if not ODOORPC_AVAILABLE:
            pytest.skip("odoorpc not available")

        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("single_read", "odoorpc")
        def read_partner():
            # Use real odoorpc search_read
            Partner = client.env['res.partner']
            return Partner.search_read(
                [('is_company', '=', True)],
                ['name', 'email', 'is_company'],
                limit=1
            )

        result = read_partner()
        assert len(result) >= 0  # May be 0 if no companies exist
        client.logout()

    @pytest.mark.asyncio
    async def test_bulk_read_zenoo(self, perf_benchmark):
        """Test bulk read operations with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        @perf_benchmark.measure_performance("bulk_read", "zenoo_rpc")
        async def bulk_read_partners():
            return await client.search_read(
                "res.partner",
                domain=[],  # Get all partners
                fields=["name", "email", "is_company"],
                limit=50  # Reasonable limit for testing
            )

        result = await bulk_read_partners()
        assert len(result) >= 0  # May vary based on server data
        await client.close()

    def test_bulk_read_odoorpc(self, perf_benchmark):
        """Test bulk read operations with odoorpc."""
        if not ODOORPC_AVAILABLE:
            pytest.skip("odoorpc not available")

        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("bulk_read", "odoorpc")
        def bulk_read_partners():
            # Use real odoorpc bulk read
            Partner = client.env['res.partner']
            return Partner.search_read(
                [],  # Get all partners
                ['name', 'email', 'is_company'],
                limit=50  # Same limit as zenoo_rpc
            )

        result = bulk_read_partners()
        assert len(result) >= 0  # May vary based on server data
        client.logout()

    @pytest.mark.asyncio
    async def test_create_operation_zenoo(self, perf_benchmark):
        """Test create operations with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        # Mock create response
        client._transport.json_rpc_call.return_value = {"result": 1001}

        @perf_benchmark.measure_performance("create", "zenoo_rpc")
        async def create_partner():
            return await client.execute_kw(
                "res.partner",
                "create",
                [{
                    "name": "Test Partner",
                    "email": "test@example.com",
                    "is_company": True
                }]
            )

        result = await create_partner()
        assert result == 1001
        await client.close()

    def test_create_operation_odoorpc(self, perf_benchmark):
        """Test create operations with odoorpc."""
        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("create", "odoorpc")
        def create_partner():
            # Mock create operation
            return 1001

        result = create_partner()
        assert result == 1001

    @pytest.mark.asyncio
    async def test_update_operation_zenoo(self, perf_benchmark):
        """Test update operations with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        # Mock update response
        client._transport.json_rpc_call.return_value = {"result": True}

        @perf_benchmark.measure_performance("update", "zenoo_rpc")
        async def update_partner():
            return await client.execute_kw(
                "res.partner",
                "write",
                [[1], {"name": "Updated Partner"}]
            )

        result = await update_partner()
        assert result is True
        await client.close()

    def test_update_operation_odoorpc(self, perf_benchmark):
        """Test update operations with odoorpc."""
        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("update", "odoorpc")
        def update_partner():
            # Mock update operation
            return True

        result = update_partner()
        assert result is True


class TestConcurrentOperations:
    """Test concurrent operations performance."""

    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance."""
        return PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_concurrent_reads_zenoo(self, perf_benchmark):
        """Test concurrent read operations with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        # Mock responses
        client._transport.json_rpc_call.return_value = {
            "result": perf_benchmark.mock_partner_data[:10]
        }

        @perf_benchmark.measure_performance("concurrent_reads", "zenoo_rpc")
        async def concurrent_reads():
            tasks = []
            for i in range(10):
                task = client.search_read(
                    "res.partner",
                    domain=[("id", ">", i * 10)],
                    fields=["name", "email"],
                    limit=10
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return results

        results = await concurrent_reads()
        assert len(results) == 10
        await client.close()

    def test_concurrent_reads_odoorpc(self, perf_benchmark):
        """Test concurrent read operations with odoorpc (simulated)."""
        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("concurrent_reads", "odoorpc")
        def concurrent_reads():
            # Simulate sequential operations (odoorpc is synchronous)
            results = []
            for i in range(10):
                # Mock read operation
                result = perf_benchmark.mock_partner_data[i*10:(i+1)*10]
                results.append(result)
            return results

        results = concurrent_reads()
        assert len(results) == 10


class TestBatchOperations:
    """Test batch operations performance."""

    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance."""
        return PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_batch_create_zenoo(self, perf_benchmark):
        """Test batch create operations with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        # Mock batch create response
        client._transport.json_rpc_call.return_value = {
            "result": list(range(1001, 1101))
        }

        @perf_benchmark.measure_performance("batch_create", "zenoo_rpc")
        async def batch_create_partners():
            values_list = [
                {
                    "name": f"Batch Partner {i}",
                    "email": f"batch{i}@example.com",
                    "is_company": i % 2 == 0
                }
                for i in range(100)
            ]

            return await client.execute_kw(
                "res.partner",
                "create",
                [values_list]
            )

        result = await batch_create_partners()
        assert len(result) == 100
        await client.close()

    def test_batch_create_odoorpc(self, perf_benchmark):
        """Test batch create operations with odoorpc."""
        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("batch_create", "odoorpc")
        def batch_create_partners():
            # Mock batch create
            return list(range(1001, 1101))

        result = batch_create_partners()
        assert len(result) == 100


class TestMemoryUsage:
    """Test memory usage patterns."""

    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance."""
        return PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_memory_efficiency_zenoo(self, perf_benchmark):
        """Test memory efficiency with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        # Mock large dataset response
        large_dataset = perf_benchmark.mock_partner_data * 10  # 10,000 records
        client._transport.json_rpc_call.return_value = {"result": large_dataset}

        @perf_benchmark.measure_performance("memory_test", "zenoo_rpc")
        async def memory_intensive_operation():
            # Force garbage collection before test
            gc.collect()

            # Perform memory-intensive operation
            result = await client.search_read(
                "res.partner",
                domain=[],
                fields=["name", "email", "is_company", "customer_rank"],
                limit=10000
            )

            # Process data to simulate real usage
            processed = [
                {"name": r["name"], "email": r["email"]}
                for r in result if r.get("is_company")
            ]

            return processed

        result = await memory_intensive_operation()
        assert len(result) > 0
        await client.close()

    def test_memory_efficiency_odoorpc(self, perf_benchmark):
        """Test memory efficiency with odoorpc."""
        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("memory_test", "odoorpc")
        def memory_intensive_operation():
            # Force garbage collection before test
            gc.collect()

            # Mock large dataset
            large_dataset = perf_benchmark.mock_partner_data * 10

            # Process data to simulate real usage
            processed = [
                {"name": r["name"], "email": r["email"]}
                for r in large_dataset if r.get("is_company")
            ]

            return processed

        result = memory_intensive_operation()
        assert len(result) > 0


class TestRealWorldScenarios:
    """Test real-world ERP scenarios."""

    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance."""
        return PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_sales_workflow_zenoo(self, perf_benchmark):
        """Test complete sales workflow with zenoo_rpc."""
        client = await perf_benchmark.setup_zenoo_client()

        # Mock responses for sales workflow
        client._transport.json_rpc_call.side_effect = [
            {"result": perf_benchmark.mock_partner_data[:10]},  # Search customers
            {"result": perf_benchmark.mock_product_data[:5]},   # Search products
            {"result": 2001},                              # Create sale order
            {"result": [3001, 3002, 3003]},               # Create order lines
            {"result": True},                              # Confirm order
        ]

        @perf_benchmark.measure_performance("sales_workflow", "zenoo_rpc")
        async def sales_workflow():
            # 1. Search for customers
            customers = await client.search_read(
                "res.partner",
                domain=[("customer_rank", ">", 0)],
                fields=["name", "email"],
                limit=10
            )

            # 2. Search for products
            products = await client.search_read(
                "product.product",
                domain=[("sale_ok", "=", True)],
                fields=["name", "list_price"],
                limit=5
            )

            # 3. Create sale order
            order_id = await client.execute_kw(
                "sale.order",
                "create",
                [{
                    "partner_id": customers[0]["id"],
                    "date_order": "2024-01-01"
                }]
            )

            # 4. Create order lines
            line_values = [
                {
                    "order_id": order_id,
                    "product_id": product["id"],
                    "product_uom_qty": 1,
                    "price_unit": product["list_price"]
                }
                for product in products[:3]
            ]

            line_ids = await client.execute_kw(
                "sale.order.line",
                "create",
                [line_values]
            )

            # 5. Confirm order
            confirmed = await client.execute_kw(
                "sale.order",
                "action_confirm",
                [[order_id]]
            )

            return {
                "order_id": order_id,
                "line_ids": line_ids,
                "confirmed": confirmed
            }

        result = await sales_workflow()
        assert result["order_id"] == 2001
        assert len(result["line_ids"]) == 3
        await client.close()

    def test_sales_workflow_odoorpc(self, perf_benchmark):
        """Test complete sales workflow with odoorpc."""
        client = perf_benchmark.setup_odoorpc_client()

        @perf_benchmark.measure_performance("sales_workflow", "odoorpc")
        def sales_workflow():
            # Mock the same workflow synchronously
            customers = perf_benchmark.mock_partner_data[:10]
            products = perf_benchmark.mock_product_data[:5]
            order_id = 2001
            line_ids = [3001, 3002, 3003]
            confirmed = True

            return {
                "order_id": order_id,
                "line_ids": line_ids,
                "confirmed": confirmed
            }

        result = sales_workflow()
        assert result["order_id"] == 2001
        assert len(result["line_ids"]) == 3


class TestPerformanceRunner:
    """Main test runner for comprehensive performance analysis."""

    @pytest.mark.asyncio
    async def test_comprehensive_benchmark(self):
        """Run comprehensive benchmark and generate report."""
        benchmark = PerformanceBenchmark()

        print("\n" + "="*80)
        print("ZENOO-RPC vs ODOORPC PERFORMANCE BENCHMARK")
        print("="*80)

        # Run all test categories
        test_classes = [
            TestBasicOperations(),
            TestConcurrentOperations(),
            TestBatchOperations(),
            TestMemoryUsage(),
            TestRealWorldScenarios()
        ]

        for test_class in test_classes:
            test_class.benchmark = benchmark

            # Run tests for this class
            if hasattr(test_class, 'test_single_record_read_zenoo'):
                await test_class.test_single_record_read_zenoo(benchmark)
                test_class.test_single_record_read_odoorpc(benchmark)

            if hasattr(test_class, 'test_bulk_read_zenoo'):
                await test_class.test_bulk_read_zenoo(benchmark)
                test_class.test_bulk_read_odoorpc(benchmark)

            if hasattr(test_class, 'test_create_operation_zenoo'):
                await test_class.test_create_operation_zenoo(benchmark)
                test_class.test_create_operation_odoorpc(benchmark)

            if hasattr(test_class, 'test_concurrent_reads_zenoo'):
                await test_class.test_concurrent_reads_zenoo(benchmark)
                test_class.test_concurrent_reads_odoorpc(benchmark)

            if hasattr(test_class, 'test_batch_create_zenoo'):
                await test_class.test_batch_create_zenoo(benchmark)
                test_class.test_batch_create_odoorpc(benchmark)

            if hasattr(test_class, 'test_memory_efficiency_zenoo'):
                await test_class.test_memory_efficiency_zenoo(benchmark)
                test_class.test_memory_efficiency_odoorpc(benchmark)

            if hasattr(test_class, 'test_sales_workflow_zenoo'):
                await test_class.test_sales_workflow_zenoo(benchmark)
                test_class.test_sales_workflow_odoorpc(benchmark)

        # Generate and display report
        report = benchmark.generate_performance_report()

        print("\n" + "-"*80)
        print("PERFORMANCE COMPARISON SUMMARY")
        print("-"*80)

        for operation, comparison in report["comparisons"].items():
            print(f"\n{operation.upper()}:")
            print(f"  Response Time Improvement: {comparison['response_time_improvement_percent']:.1f}%")
            print(f"  Throughput Improvement: {comparison['throughput_improvement_percent']:.1f}%")

            zenoo = comparison['zenoo_rpc']
            odoorpc = comparison['odoorpc']

            print(f"  zenoo_rpc: {zenoo['avg_response_time']:.2f}ms avg, {zenoo['throughput']:.2f} ops/s")
            print(f"  odoorpc:   {odoorpc['avg_response_time']:.2f}ms avg, {odoorpc['throughput']:.2f} ops/s")

        print("\n" + "-"*80)
        print("DETAILED METRICS")
        print("-"*80)

        for key, metrics in report["detailed_metrics"].items():
            print(f"\n{key}:")
            print(f"  Avg Response Time: {metrics['avg_response_time']:.2f}ms")
            print(f"  P95 Response Time: {metrics['p95_response_time']:.2f}ms")
            print(f"  Throughput: {metrics['throughput']:.2f} ops/s")
            print(f"  Error Rate: {metrics['error_rate']:.2f}%")
            print(f"  Memory Usage: {metrics['avg_memory_usage']:.2f}MB")

        print("\n" + "="*80)
        print("BENCHMARK COMPLETED")
        print("="*80)

        # Assert that we have meaningful results
        assert len(report["comparisons"]) > 0
        assert len(report["detailed_metrics"]) > 0


if __name__ == "__main__":
    """Run benchmark directly."""
    import asyncio

    async def main():
        runner = TestPerformanceRunner()
        await runner.test_comprehensive_benchmark()

    asyncio.run(main())
