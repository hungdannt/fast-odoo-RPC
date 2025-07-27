# Performance Metrics and Monitoring

A comprehensive example demonstrating how to implement performance monitoring, metrics collection, and optimization strategies using Zenoo RPC's built-in monitoring capabilities.

## Overview

This example shows how to:

- Monitor Zenoo RPC performance metrics
- Implement custom performance tracking
- Optimize query performance with caching
- Track batch operation efficiency
- Monitor connection pool health
- Generate performance reports

## Complete Implementation

### Performance Monitor Service

```python
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.cache.strategies import TTLCache
from zenoo_rpc.retry.strategies import ExponentialBackoffStrategy

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    cache_hit: bool = False
    retry_count: int = 0
    record_count: int = 0

@dataclass
class SystemMetrics:
    """System-wide performance metrics."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_response_time: float = 0.0
    cache_hit_ratio: float = 0.0
    total_cache_hits: int = 0
    total_cache_misses: int = 0
    connection_pool_active: int = 0
    connection_pool_idle: int = 0
    retry_operations: int = 0
    batch_operations: int = 0

class PerformanceMonitor:
    """Performance monitoring and metrics collection service."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.metrics: List[PerformanceMetrics] = []
        self.system_metrics = SystemMetrics()
        self._start_time = time.time()
    
    @asynccontextmanager
    async def track_operation(
        self, 
        operation_name: str, 
        expected_records: int = 0
    ):
        """Context manager to track operation performance."""
        start_time = time.time()
        success = True
        error_message = None
        cache_hit = False
        retry_count = 0
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            self.system_metrics.failed_operations += 1
            raise
        else:
            self.system_metrics.successful_operations += 1
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # Create performance metric
            metric = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=success,
                error_message=error_message,
                cache_hit=cache_hit,
                retry_count=retry_count,
                record_count=expected_records
            )
            
            self.metrics.append(metric)
            self.system_metrics.total_operations += 1
            
            # Update average response time
            total_duration = sum(m.duration for m in self.metrics)
            self.system_metrics.average_response_time = total_duration / len(self.metrics)
    
    async def benchmark_query_performance(self) -> Dict[str, Any]:
        """Benchmark different query patterns and optimizations."""
        
        results = {
            "basic_queries": {},
            "optimized_queries": {},
            "cached_queries": {},
            "batch_operations": {}
        }
        
        # Test basic queries
        print("🔍 Testing basic query performance...")
        
        # Basic query without optimization
        async with self.track_operation("basic_search_all_fields"):
            partners = await self.client.model(ResPartner).filter(
                customer_rank__gt=0
            ).limit(100).all()
            
        results["basic_queries"]["all_fields"] = {
            "duration": self.metrics[-1].duration,
            "record_count": len(partners)
        }
        
        # Optimized query with field selection
        async with self.track_operation("optimized_search_selected_fields"):
            partners_opt = await (
                self.client.model(ResPartner)
                .filter(customer_rank__gt=0)
                .only("name", "email", "phone")
                .limit(100)
                .all()
            )
            
        results["optimized_queries"]["selected_fields"] = {
            "duration": self.metrics[-1].duration,
            "record_count": len(partners_opt),
            "improvement": (
                results["basic_queries"]["all_fields"]["duration"] - 
                self.metrics[-1].duration
            ) / results["basic_queries"]["all_fields"]["duration"] * 100
        }
        
        # Test caching performance
        print("⚡ Testing cache performance...")
        
        # First call (cache miss)
        async with self.track_operation("cached_query_miss"):
            cached_partners = await (
                self.client.model(ResPartner)
                .filter(customer_rank__gt=0)
                .only("name", "email")
                .limit(50)
                .cache(ttl=300)
                .all()
            )
            
        results["cached_queries"]["cache_miss"] = {
            "duration": self.metrics[-1].duration,
            "record_count": len(cached_partners)
        }
        
        # Second call (cache hit)
        async with self.track_operation("cached_query_hit"):
            cached_partners_hit = await (
                self.client.model(ResPartner)
                .filter(customer_rank__gt=0)
                .only("name", "email")
                .limit(50)
                .cache(ttl=300)
                .all()
            )
            
        results["cached_queries"]["cache_hit"] = {
            "duration": self.metrics[-1].duration,
            "record_count": len(cached_partners_hit),
            "speedup": (
                results["cached_queries"]["cache_miss"]["duration"] / 
                self.metrics[-1].duration
            )
        }
        
        # Test batch operations
        print("📦 Testing batch operation performance...")
        
        # Individual creates
        start_time = time.time()
        individual_ids = []
        for i in range(10):
            async with self.track_operation(f"individual_create_{i}"):
                partner = await self.client.model(ResPartner).create({
                    "name": f"Test Partner Individual {i}",
                    "email": f"individual{i}@test.com"
                })
                individual_ids.append(partner.id)
        
        individual_duration = time.time() - start_time
        
        # Batch creates
        async with self.track_operation("batch_create_10_records"):
            async with self.client.batch() as batch:
                for i in range(10):
                    batch.create("res.partner", {
                        "name": f"Test Partner Batch {i}",
                        "email": f"batch{i}@test.com"
                    })
            
            batch_results = await batch.execute()
        
        results["batch_operations"] = {
            "individual_creates": {
                "duration": individual_duration,
                "records": 10
            },
            "batch_creates": {
                "duration": self.metrics[-1].duration,
                "records": len(batch_results.get("created", [])),
                "speedup": individual_duration / self.metrics[-1].duration
            }
        }
        
        # Cleanup test records
        await self._cleanup_test_records(individual_ids)
        
        return results
    
    async def monitor_connection_pool(self) -> Dict[str, Any]:
        """Monitor connection pool health and performance."""
        
        pool_stats = {}
        
        # Get transport pool statistics if available
        if hasattr(self.client, 'transport') and hasattr(self.client.transport, 'pool'):
            pool = self.client.transport.pool
            
            pool_stats = {
                "active_connections": getattr(pool, 'active_connections', 0),
                "idle_connections": getattr(pool, 'idle_connections', 0),
                "max_connections": getattr(pool, 'max_connections', 0),
                "total_requests": getattr(pool, 'total_requests', 0),
                "failed_requests": getattr(pool, 'failed_requests', 0),
                "average_response_time": getattr(pool, 'average_response_time', 0.0)
            }
            
            # Update system metrics
            self.system_metrics.connection_pool_active = pool_stats["active_connections"]
            self.system_metrics.connection_pool_idle = pool_stats["idle_connections"]
        
        return pool_stats
    
    async def test_retry_mechanisms(self) -> Dict[str, Any]:
        """Test and monitor retry mechanism performance."""
        
        retry_results = {}
        
        # Test with exponential backoff strategy
        retry_strategy = ExponentialBackoffStrategy(
            max_attempts=3,
            base_delay=0.1,
            max_delay=2.0
        )
        
        # Simulate operations that might need retries
        async with self.track_operation("retry_test_search"):
            try:
                # This should succeed normally
                partners = await (
                    self.client.model(ResPartner)
                    .filter(customer_rank__gt=0)
                    .limit(5)
                    .all()
                )
                
                retry_results["normal_operation"] = {
                    "success": True,
                    "duration": self.metrics[-1].duration,
                    "retry_count": 0
                }
                
            except Exception as e:
                retry_results["normal_operation"] = {
                    "success": False,
                    "error": str(e),
                    "retry_count": getattr(e, 'retry_count', 0)
                }
        
        return retry_results
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        # Calculate metrics
        total_operations = len(self.metrics)
        successful_ops = len([m for m in self.metrics if m.success])
        failed_ops = total_operations - successful_ops
        
        if total_operations > 0:
            avg_duration = sum(m.duration for m in self.metrics) / total_operations
            success_rate = successful_ops / total_operations * 100
        else:
            avg_duration = 0.0
            success_rate = 0.0
        
        # Group by operation type
        operation_stats = {}
        for metric in self.metrics:
            op_name = metric.operation_name
            if op_name not in operation_stats:
                operation_stats[op_name] = {
                    "count": 0,
                    "total_duration": 0.0,
                    "min_duration": float('inf'),
                    "max_duration": 0.0,
                    "success_count": 0,
                    "error_count": 0
                }
            
            stats = operation_stats[op_name]
            stats["count"] += 1
            stats["total_duration"] += metric.duration
            stats["min_duration"] = min(stats["min_duration"], metric.duration)
            stats["max_duration"] = max(stats["max_duration"], metric.duration)
            
            if metric.success:
                stats["success_count"] += 1
            else:
                stats["error_count"] += 1
        
        # Calculate averages
        for op_name, stats in operation_stats.items():
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            stats["success_rate"] = stats["success_count"] / stats["count"] * 100
        
        # Get connection pool stats
        pool_stats = await self.monitor_connection_pool()
        
        # Generate report
        report = {
            "summary": {
                "total_operations": total_operations,
                "successful_operations": successful_ops,
                "failed_operations": failed_ops,
                "success_rate": success_rate,
                "average_duration": avg_duration,
                "monitoring_duration": time.time() - self._start_time
            },
            "operation_breakdown": operation_stats,
            "connection_pool": pool_stats,
            "system_metrics": {
                "cache_hit_ratio": self.system_metrics.cache_hit_ratio,
                "retry_operations": self.system_metrics.retry_operations,
                "batch_operations": self.system_metrics.batch_operations
            },
            "recommendations": self._generate_recommendations(operation_stats)
        }
        
        return report
    
    def _generate_recommendations(self, operation_stats: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        # Check for slow operations
        slow_operations = [
            op for op, stats in operation_stats.items()
            if stats["avg_duration"] > 1.0  # Operations taking more than 1 second
        ]
        
        if slow_operations:
            recommendations.append(
                f"Consider optimizing slow operations: {', '.join(slow_operations)}"
            )
            recommendations.append(
                "Use field selection with .only() to reduce data transfer"
            )
            recommendations.append(
                "Implement caching for frequently accessed data"
            )
        
        # Check for high failure rates
        failing_operations = [
            op for op, stats in operation_stats.items()
            if stats["success_rate"] < 95.0
        ]
        
        if failing_operations:
            recommendations.append(
                f"Investigate failing operations: {', '.join(failing_operations)}"
            )
            recommendations.append(
                "Implement retry mechanisms for transient failures"
            )
        
        # Check for operations that could benefit from batching
        frequent_creates = [
            op for op, stats in operation_stats.items()
            if "create" in op.lower() and stats["count"] > 5
        ]
        
        if frequent_creates:
            recommendations.append(
                "Consider using batch operations for multiple creates/updates"
            )
        
        return recommendations
    
    async def _cleanup_test_records(self, record_ids: List[int]):
        """Clean up test records created during benchmarking."""
        if record_ids:
            try:
                async with self.client.batch() as batch:
                    batch.delete("res.partner", record_ids)
                await batch.execute()
            except Exception as e:
                print(f"Warning: Could not clean up test records: {e}")

# Usage Example
async def main():
    """Demonstrate performance monitoring."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize performance monitor
        monitor = PerformanceMonitor(client)
        
        print("🚀 Starting performance benchmarks...")
        
        # Run comprehensive benchmarks
        benchmark_results = await monitor.benchmark_query_performance()
        
        # Test retry mechanisms
        retry_results = await monitor.test_retry_mechanisms()
        
        # Generate performance report
        report = await monitor.generate_performance_report()
        
        # Display results
        print("\n📊 Performance Benchmark Results:")
        print(f"  Query Optimization Improvement: {benchmark_results['optimized_queries']['selected_fields']['improvement']:.1f}%")
        print(f"  Cache Speedup: {benchmark_results['cached_queries']['cache_hit']['speedup']:.1f}x")
        print(f"  Batch Operation Speedup: {benchmark_results['batch_operations']['batch_creates']['speedup']:.1f}x")
        
        print(f"\n📈 Overall Performance:")
        print(f"  Total Operations: {report['summary']['total_operations']}")
        print(f"  Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"  Average Duration: {report['summary']['average_duration']:.3f}s")
        
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Performance Tracking**
- Context manager for operation timing
- Comprehensive metrics collection
- Success/failure rate monitoring

### 2. **Query Optimization**
- Field selection optimization
- Caching performance comparison
- Query pattern analysis

### 3. **Batch Operation Analysis**
- Individual vs batch performance
- Throughput measurements
- Efficiency calculations

### 4. **System Monitoring**
- Connection pool health
- Cache hit ratios
- Retry mechanism effectiveness

### 5. **Automated Recommendations**
- Performance bottleneck identification
- Optimization suggestions
- Best practice recommendations

## Integration with Monitoring Systems

### Prometheus Metrics Export

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
operation_counter = Counter('zenoo_operations_total', 'Total operations', ['operation', 'status'])
operation_duration = Histogram('zenoo_operation_duration_seconds', 'Operation duration')
cache_hit_ratio = Gauge('zenoo_cache_hit_ratio', 'Cache hit ratio')

# Export metrics in track_operation
operation_counter.labels(operation=operation_name, status='success' if success else 'error').inc()
operation_duration.observe(duration)
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Zenoo RPC Performance",
    "panels": [
      {
        "title": "Operation Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(zenoo_operations_total[5m])",
            "legendFormat": "{{operation}} - {{status}}"
          }
        ]
      }
    ]
  }
}
```

## Next Steps

- [Custom Reports](custom-reports.md) - Build performance reports
- [Data Visualization](data-visualization.md) - Create performance dashboards
- [Automated Workflows](automated-workflows.md) - Automate performance monitoring
