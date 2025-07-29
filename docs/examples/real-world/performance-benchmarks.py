#!/usr/bin/env python3
"""
Performance Benchmarks for Zenoo RPC AI Features

This script provides comprehensive performance benchmarking for Zenoo RPC's AI
capabilities in production environments, based on real-world Gemini API usage patterns.

Benchmarks include:
- AI response time analysis
- Throughput testing under load
- Memory usage profiling
- Error rate analysis
- Cost optimization metrics
- Scalability testing
"""

import asyncio
import logging
import time
import statistics
import json
import psutil
import tracemalloc
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError


# Configure logging for benchmarking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('benchmark_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark test result."""
    test_name: str
    operation: str
    provider: str
    model: str
    success_count: int
    error_count: int
    total_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput_rps: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    total_tokens_used: int
    cost_estimate_usd: float
    timestamp: datetime


@dataclass
class LoadTestResult:
    """Load test result with detailed metrics."""
    concurrent_users: int
    test_duration_seconds: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    throughput_rps: float
    error_rate: float
    resource_usage: Dict[str, float]
    bottlenecks: List[str]
    recommendations: List[str]


class PerformanceBenchmark:
    """
    Comprehensive performance benchmarking suite for Zenoo RPC AI features.
    
    Features:
    - Response time analysis across different operations
    - Load testing with concurrent users
    - Memory and CPU profiling
    - Error rate analysis under stress
    - Cost optimization benchmarks
    - Scalability testing
    """
    
    def __init__(self, odoo_url: str, database: str, username: str, password: str):
        self.odoo_url = odoo_url
        self.database = database
        self.username = username
        self.password = password
        self.benchmark_results: List[BenchmarkResult] = []
        self.load_test_results: List[LoadTestResult] = []
    
    @asynccontextmanager
    async def get_client(self):
        """Get configured client for benchmarking."""
        client = ZenooClient(self.odoo_url)
        try:
            await client.login(self.database, self.username, self.password)
            
            # Setup AI for benchmarking
            await client.setup_ai(
                provider="gemini",
                model="gemini-2.5-flash-lite",
                api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.1,
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
    
    async def benchmark_ai_operations(self) -> List[BenchmarkResult]:
        """Benchmark different AI operations."""
        
        logger.info("Starting AI operations benchmark...")
        
        operations = [
            {
                'name': 'simple_chat',
                'operation': lambda client: client.ai.chat("What is Odoo?", max_tokens=100),
                'description': 'Simple AI chat query'
            },
            {
                'name': 'query_explanation',
                'operation': lambda client: client.ai.explain_query("Find all customers"),
                'description': 'Natural language query explanation'
            },
            {
                'name': 'error_diagnosis',
                'operation': lambda client: client.ai.diagnose(
                    ValueError("Test error"), {"model": "res.partner"}
                ),
                'description': 'AI error diagnosis'
            },
            {
                'name': 'model_generation',
                'operation': lambda client: client.ai.generate_model("res.partner"),
                'description': 'AI model code generation'
            }
        ]
        
        results = []
        
        for op in operations:
            logger.info(f"Benchmarking {op['name']}...")
            result = await self._benchmark_single_operation(
                op['name'], op['operation'], iterations=50
            )
            results.append(result)
            self.benchmark_results.append(result)
        
        return results
    
    async def _benchmark_single_operation(self, test_name: str, operation_func, 
                                        iterations: int = 50) -> BenchmarkResult:
        """Benchmark a single operation."""
        
        response_times = []
        success_count = 0
        error_count = 0
        total_tokens = 0
        
        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        
        async with self.get_client() as client:
            for i in range(iterations):
                operation_start = time.time()
                
                try:
                    result = await operation_func(client)
                    operation_time = time.time() - operation_start
                    response_times.append(operation_time)
                    success_count += 1
                    
                    # Estimate tokens (simplified)
                    if hasattr(result, '__len__'):
                        total_tokens += len(str(result)) // 4
                    
                except Exception as e:
                    error_count += 1
                    logger.warning(f"Operation {i+1} failed: {e}")
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory
        
        # Stop memory tracking
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        throughput_rps = success_count / total_time if total_time > 0 else 0
        error_rate = error_count / iterations if iterations > 0 else 0
        
        # Estimate cost (simplified - actual costs vary by provider)
        cost_estimate = (total_tokens / 1000) * 0.002  # Rough estimate for Gemini
        
        return BenchmarkResult(
            test_name=test_name,
            operation=test_name,
            provider="gemini",
            model="gemini-2.5-flash-lite",
            success_count=success_count,
            error_count=error_count,
            total_requests=iterations,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput_rps=throughput_rps,
            error_rate=error_rate,
            memory_usage_mb=memory_used,
            cpu_usage_percent=process.cpu_percent(),
            total_tokens_used=total_tokens,
            cost_estimate_usd=cost_estimate,
            timestamp=datetime.now()
        )
    
    async def load_test(self, concurrent_users: List[int], 
                       test_duration: int = 60) -> List[LoadTestResult]:
        """Perform load testing with different concurrency levels."""
        
        logger.info("Starting load testing...")
        
        results = []
        
        for users in concurrent_users:
            logger.info(f"Load testing with {users} concurrent users...")
            result = await self._run_load_test(users, test_duration)
            results.append(result)
            self.load_test_results.append(result)
            
            # Cool down between tests
            await asyncio.sleep(10)
        
        return results
    
    async def _run_load_test(self, concurrent_users: int, 
                           duration_seconds: int) -> LoadTestResult:
        """Run load test with specified parameters."""
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        # Metrics tracking
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        # Resource monitoring
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        cpu_samples = []
        
        async def worker():
            """Worker function for load testing."""
            nonlocal total_requests, successful_requests, failed_requests, response_times
            
            async with self.get_client() as client:
                while time.time() < end_time:
                    request_start = time.time()
                    total_requests += 1
                    
                    try:
                        # Simple AI operation for load testing
                        await client.ai.chat("Load test query", max_tokens=50)
                        successful_requests += 1
                        
                        response_time = time.time() - request_start
                        response_times.append(response_time)
                        
                    except Exception as e:
                        failed_requests += 1
                        logger.debug(f"Load test request failed: {e}")
                    
                    # Small delay to simulate realistic usage
                    await asyncio.sleep(0.1)
        
        # Start workers
        tasks = [asyncio.create_task(worker()) for _ in range(concurrent_users)]
        
        # Monitor resources during test
        monitor_task = asyncio.create_task(self._monitor_resources(cpu_samples, end_time))
        
        # Wait for test completion
        await asyncio.gather(*tasks, monitor_task, return_exceptions=True)
        
        # Calculate final metrics
        actual_duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - initial_memory
        
        avg_response_time = statistics.mean(response_times) if response_times else 0
        throughput_rps = successful_requests / actual_duration if actual_duration > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
        
        # Analyze bottlenecks
        bottlenecks = self._analyze_bottlenecks(
            error_rate, avg_response_time, avg_cpu, memory_used
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            concurrent_users, error_rate, avg_response_time, throughput_rps
        )
        
        return LoadTestResult(
            concurrent_users=concurrent_users,
            test_duration_seconds=int(actual_duration),
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            throughput_rps=throughput_rps,
            error_rate=error_rate,
            resource_usage={
                'memory_mb': memory_used,
                'cpu_percent': avg_cpu,
                'peak_memory_mb': final_memory
            },
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )
    
    async def _monitor_resources(self, cpu_samples: List[float], end_time: float):
        """Monitor system resources during load test."""
        
        process = psutil.Process()
        
        while time.time() < end_time:
            cpu_samples.append(process.cpu_percent())
            await asyncio.sleep(1)
    
    def _analyze_bottlenecks(self, error_rate: float, avg_response_time: float,
                           avg_cpu: float, memory_used: float) -> List[str]:
        """Analyze performance bottlenecks."""
        
        bottlenecks = []
        
        if error_rate > 0.05:  # 5% error rate threshold
            bottlenecks.append("High error rate - API rate limiting or network issues")
        
        if avg_response_time > 5.0:  # 5 second threshold
            bottlenecks.append("High response times - API latency or processing delays")
        
        if avg_cpu > 80:  # 80% CPU threshold
            bottlenecks.append("High CPU usage - processing bottleneck")
        
        if memory_used > 1000:  # 1GB memory threshold
            bottlenecks.append("High memory usage - potential memory leak")
        
        return bottlenecks
    
    def _generate_recommendations(self, concurrent_users: int, error_rate: float,
                                avg_response_time: float, throughput_rps: float) -> List[str]:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        if error_rate > 0.02:
            recommendations.append("Implement exponential backoff and retry logic")
            recommendations.append("Consider rate limiting client requests")
        
        if avg_response_time > 3.0:
            recommendations.append("Implement response caching for repeated queries")
            recommendations.append("Consider using faster AI models for simple operations")
        
        if throughput_rps < concurrent_users * 0.5:
            recommendations.append("Optimize connection pooling and reuse")
            recommendations.append("Consider horizontal scaling with load balancing")
        
        if concurrent_users > 10 and throughput_rps < 5:
            recommendations.append("Implement request queuing and batching")
            recommendations.append("Consider using multiple API keys for higher limits")
        
        return recommendations
    
    async def benchmark_model_comparison(self) -> Dict[str, BenchmarkResult]:
        """Compare performance across different AI models."""
        
        logger.info("Benchmarking model comparison...")
        
        models = [
            ("gemini-2.5-flash-lite", "Fast model for quick responses"),
            ("gemini-2.5-pro", "Advanced model for complex tasks")
        ]
        
        results = {}
        
        for model, description in models:
            logger.info(f"Testing {model}...")
            
            # Temporarily switch model
            async with self.get_client() as client:
                await client.setup_ai(
                    provider="gemini",
                    model=model,
                    api_key=os.getenv("GEMINI_API_KEY"),
                    temperature=0.1,
                    max_tokens=1000,
                    timeout=30.0,
                    max_retries=3
                )
                
                # Test with standard query
                result = await self._benchmark_single_operation(
                    f"model_comparison_{model}",
                    lambda c: c.ai.chat("Explain the benefits of ERP systems", max_tokens=500),
                    iterations=20
                )
                
                results[model] = result
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_summary(),
            'benchmark_results': [asdict(result) for result in self.benchmark_results],
            'load_test_results': [asdict(result) for result in self.load_test_results],
            'recommendations': self._generate_overall_recommendations()
        }
        
        return report
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        
        if not self.benchmark_results:
            return {}
        
        avg_response_times = [r.avg_response_time for r in self.benchmark_results]
        throughputs = [r.throughput_rps for r in self.benchmark_results]
        error_rates = [r.error_rate for r in self.benchmark_results]
        
        return {
            'total_tests': len(self.benchmark_results),
            'avg_response_time': statistics.mean(avg_response_times),
            'avg_throughput_rps': statistics.mean(throughputs),
            'avg_error_rate': statistics.mean(error_rates),
            'total_requests': sum(r.total_requests for r in self.benchmark_results),
            'total_cost_estimate': sum(r.cost_estimate_usd for r in self.benchmark_results)
        }
    
    def _generate_overall_recommendations(self) -> List[str]:
        """Generate overall optimization recommendations."""
        
        recommendations = [
            "Monitor AI API usage and costs regularly",
            "Implement caching for frequently requested operations",
            "Use appropriate AI models based on complexity requirements",
            "Set up proper error handling and retry mechanisms",
            "Consider implementing request queuing for high-load scenarios"
        ]
        
        # Add specific recommendations based on results
        if self.benchmark_results:
            avg_error_rate = statistics.mean([r.error_rate for r in self.benchmark_results])
            if avg_error_rate > 0.05:
                recommendations.append("High error rate detected - review API limits and network stability")
        
        return recommendations
    
    def save_report(self, filename: str = None):
        """Save benchmark report to file."""
        
        if filename is None:
            filename = f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Benchmark report saved to {filename}")


async def main():
    """Run comprehensive performance benchmarks."""
    
    # Initialize benchmark suite
    benchmark = PerformanceBenchmark(
        odoo_url="http://localhost:8069",
        database="demo",
        username="admin",
        password="admin"
    )
    
    try:
        logger.info("Starting comprehensive performance benchmarks...")
        
        # 1. Benchmark AI operations
        logger.info("=== AI Operations Benchmark ===")
        ai_results = await benchmark.benchmark_ai_operations()
        
        for result in ai_results:
            logger.info(f"{result.test_name}: {result.avg_response_time:.2f}s avg, "
                       f"{result.throughput_rps:.2f} RPS, {result.error_rate:.1%} errors")
        
        # 2. Load testing
        logger.info("=== Load Testing ===")
        load_results = await benchmark.load_test([1, 5, 10, 20], test_duration=30)
        
        for result in load_results:
            logger.info(f"{result.concurrent_users} users: {result.throughput_rps:.2f} RPS, "
                       f"{result.error_rate:.1%} errors, {result.avg_response_time:.2f}s avg")
        
        # 3. Model comparison
        logger.info("=== Model Comparison ===")
        model_results = await benchmark.benchmark_model_comparison()
        
        for model, result in model_results.items():
            logger.info(f"{model}: {result.avg_response_time:.2f}s avg, "
                       f"${result.cost_estimate_usd:.4f} estimated cost")
        
        # 4. Generate and save report
        logger.info("=== Generating Report ===")
        benchmark.save_report()
        
        # Print summary
        summary = benchmark._generate_summary()
        logger.info("=== Benchmark Summary ===")
        logger.info(f"Total tests: {summary['total_tests']}")
        logger.info(f"Average response time: {summary['avg_response_time']:.2f}s")
        logger.info(f"Average throughput: {summary['avg_throughput_rps']:.2f} RPS")
        logger.info(f"Average error rate: {summary['avg_error_rate']:.1%}")
        logger.info(f"Total cost estimate: ${summary['total_cost_estimate']:.4f}")
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    import os
    
    # Ensure API key is set
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        exit(1)
    
    asyncio.run(main())
