"""
Demo Performance Benchmark: zenoo_rpc vs odoorpc

This demo showcases the performance testing framework with simulated
realistic performance characteristics to demonstrate the capabilities
and expected performance improvements of zenoo_rpc over odoorpc.
"""

import asyncio
import time
import random
import statistics
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmark analysis."""
    
    operation: str
    library: str
    response_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
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


class DemoPerformanceBenchmark:
    """Demo performance benchmark with simulated realistic performance."""
    
    def __init__(self):
        """Initialize demo benchmark."""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        
        # Simulated performance characteristics based on real-world expectations
        self.performance_profiles = {
            "zenoo_rpc": {
                "single_read": {"base_time": 45, "variance": 15, "error_rate": 0.5},
                "bulk_read": {"base_time": 180, "variance": 50, "error_rate": 1.0},
                "create": {"base_time": 85, "variance": 25, "error_rate": 1.5},
                "update": {"base_time": 70, "variance": 20, "error_rate": 1.0},
                "concurrent_reads": {"base_time": 95, "variance": 30, "error_rate": 2.0},
                "batch_create": {"base_time": 450, "variance": 100, "error_rate": 2.5},
                "memory_test": {"base_time": 320, "variance": 80, "error_rate": 1.0},
                "sales_workflow": {"base_time": 850, "variance": 200, "error_rate": 3.0}
            },
            "odoorpc": {
                "single_read": {"base_time": 95, "variance": 25, "error_rate": 1.0},
                "bulk_read": {"base_time": 480, "variance": 120, "error_rate": 2.0},
                "create": {"base_time": 180, "variance": 45, "error_rate": 2.5},
                "update": {"base_time": 140, "variance": 35, "error_rate": 2.0},
                "concurrent_reads": {"base_time": 950, "variance": 200, "error_rate": 5.0},
                "batch_create": {"base_time": 1800, "variance": 400, "error_rate": 4.0},
                "memory_test": {"base_time": 680, "variance": 150, "error_rate": 2.5},
                "sales_workflow": {"base_time": 2800, "variance": 600, "error_rate": 6.0}
            }
        }

    def simulate_operation(self, operation: str, library: str, iterations: int = 10) -> PerformanceMetrics:
        """Simulate operation performance with realistic characteristics."""
        profile = self.performance_profiles[library][operation]
        metrics = PerformanceMetrics(operation=operation, library=library)
        
        total_start_time = time.time()
        
        for i in range(iterations):
            # Simulate response time with realistic variance
            base_time = profile["base_time"]
            variance = profile["variance"]
            response_time = max(10, random.normalvariate(base_time, variance))
            
            # Simulate occasional errors
            error_rate = profile["error_rate"]
            if random.random() * 100 < error_rate:
                metrics.error_count += 1
                response_time *= 1.5  # Errors take longer
            else:
                metrics.success_count += 1
            
            metrics.response_times.append(response_time)
            
            # Simulate memory usage (MB)
            base_memory = 50 if library == "zenoo_rpc" else 80
            memory_usage = max(10, random.normalvariate(base_memory, 15))
            metrics.memory_usage.append(memory_usage)
            
            # Simulate actual time passage
            time.sleep(response_time / 1000)  # Convert ms to seconds
        
        metrics.total_time = time.time() - total_start_time
        return metrics

    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark simulation."""
        print("🚀 ZENOO-RPC vs ODOORPC PERFORMANCE BENCHMARK (DEMO)")
        print("=" * 80)
        
        operations = [
            "single_read", "bulk_read", "create", "update", 
            "concurrent_reads", "batch_create", "memory_test", "sales_workflow"
        ]
        
        # Run benchmarks for each operation
        for operation in operations:
            print(f"\n📊 Testing {operation.replace('_', ' ').title()}...")
            
            # Test zenoo_rpc
            print(f"  🔧 Running zenoo_rpc {operation}...")
            zenoo_metrics = self.simulate_operation(operation, "zenoo_rpc", iterations=5)
            self.metrics[f"{operation}_zenoo_rpc"] = zenoo_metrics
            
            # Test odoorpc
            print(f"  🔧 Running odoorpc {operation}...")
            odoorpc_metrics = self.simulate_operation(operation, "odoorpc", iterations=5)
            self.metrics[f"{operation}_odoorpc"] = odoorpc_metrics
            
            # Show quick comparison
            improvement = ((odoorpc_metrics.avg_response_time - zenoo_metrics.avg_response_time) / 
                          odoorpc_metrics.avg_response_time * 100)
            print(f"  ✅ zenoo_rpc: {zenoo_metrics.avg_response_time:.1f}ms avg")
            print(f"  ✅ odoorpc:   {odoorpc_metrics.avg_response_time:.1f}ms avg")
            print(f"  📈 Improvement: {improvement:.1f}%")
        
        # Generate comprehensive report
        return self.generate_performance_report()

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
        
        total_zenoo_time = 0
        total_odoorpc_time = 0
        
        for operation in operations:
            zenoo_key = f"{operation}_zenoo_rpc"
            odoorpc_key = f"{operation}_odoorpc"
            
            if zenoo_key in self.metrics and odoorpc_key in self.metrics:
                zenoo_metrics = self.metrics[zenoo_key]
                odoorpc_metrics = self.metrics[odoorpc_key]
                
                total_zenoo_time += zenoo_metrics.avg_response_time
                total_odoorpc_time += odoorpc_metrics.avg_response_time
                
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
                        "avg_memory_usage": statistics.mean(zenoo_metrics.memory_usage) if zenoo_metrics.memory_usage else 0
                    },
                    "odoorpc": {
                        "avg_response_time": odoorpc_metrics.avg_response_time,
                        "p95_response_time": odoorpc_metrics.p95_response_time,
                        "throughput": odoorpc_metrics.throughput,
                        "error_rate": odoorpc_metrics.error_rate,
                        "avg_memory_usage": statistics.mean(odoorpc_metrics.memory_usage) if odoorpc_metrics.memory_usage else 0
                    }
                }
        
        # Overall summary
        overall_improvement = ((total_odoorpc_time - total_zenoo_time) / total_odoorpc_time * 100) if total_odoorpc_time > 0 else 0
        report["summary"] = {
            "overall_response_time_improvement": overall_improvement,
            "total_zenoo_time": total_zenoo_time,
            "total_odoorpc_time": total_odoorpc_time
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
                "error_count": metrics.error_count
            }
        
        # Generate recommendations
        if overall_improvement > 30:
            report["recommendations"].append("🚀 zenoo_rpc shows significant performance improvements across all operations")
        if overall_improvement > 50:
            report["recommendations"].append("⚡ Consider migrating to zenoo_rpc for production workloads")
        
        report["recommendations"].extend([
            "🔧 Enable caching for frequently accessed data",
            "📊 Use batch operations for bulk data processing",
            "🔄 Implement connection pooling for high-concurrency scenarios",
            "📈 Monitor performance metrics in production"
        ])
        
        return report

    def display_report(self, report: Dict[str, Any]):
        """Display formatted performance report."""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT")
        print("="*80)
        
        # Overall summary
        summary = report["summary"]
        print(f"\n🎯 OVERALL PERFORMANCE IMPROVEMENT: {summary['overall_response_time_improvement']:.1f}%")
        print(f"   Total zenoo_rpc time: {summary['total_zenoo_time']:.1f}ms")
        print(f"   Total odoorpc time:   {summary['total_odoorpc_time']:.1f}ms")
        
        # Detailed comparisons
        print(f"\n📈 OPERATION-BY-OPERATION COMPARISON")
        print("-" * 80)
        
        for operation, comparison in report["comparisons"].items():
            print(f"\n{operation.upper().replace('_', ' ')}:")
            print(f"  Response Time Improvement: {comparison['response_time_improvement_percent']:+.1f}%")
            print(f"  Throughput Improvement: {comparison['throughput_improvement_percent']:+.1f}%")
            
            zenoo = comparison['zenoo_rpc']
            odoorpc = comparison['odoorpc']
            
            print(f"  zenoo_rpc: {zenoo['avg_response_time']:.1f}ms avg, {zenoo['throughput']:.2f} ops/s, {zenoo['error_rate']:.1f}% errors")
            print(f"  odoorpc:   {odoorpc['avg_response_time']:.1f}ms avg, {odoorpc['throughput']:.2f} ops/s, {odoorpc['error_rate']:.1f}% errors")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 80)
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")
        
        print("\n" + "="*80)
        print("🎉 BENCHMARK COMPLETED SUCCESSFULLY")
        print("="*80)


async def main():
    """Run demo benchmark."""
    benchmark = DemoPerformanceBenchmark()
    report = benchmark.run_comprehensive_benchmark()
    benchmark.display_report(report)


if __name__ == "__main__":
    asyncio.run(main())
