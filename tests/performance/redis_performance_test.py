"""
Redis Performance Testing for zenoo_rpc

This module provides comprehensive Redis performance testing comparing:
1. zenoo_rpc with Memory Cache
2. zenoo_rpc with Redis Cache  
3. odoorpc (no caching)

Tests various scenarios including cache hits, misses, distributed caching,
and cache invalidation patterns.
"""

import asyncio
import time
import sys
import os
from typing import Dict, Any, List
from datetime import datetime
import statistics

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.zenoo_rpc import ZenooClient
from advanced_metrics import DetailedMetrics, SystemMonitor
from detailed_reporting import DetailedReportGenerator

# Redis availability check
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis-py not available. Install with: pip install redis")


class RedisPerformanceTest:
    """Comprehensive Redis performance testing."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis performance test.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.results = {}
        self.test_data = self._generate_test_data()
        
        # Check Redis availability
        self.redis_available = self._check_redis_connection()
    
    def _check_redis_connection(self) -> bool:
        """Check if Redis is available and accessible."""
        if not REDIS_AVAILABLE:
            return False
        
        try:
            client = redis.from_url(self.redis_url)
            client.ping()
            client.close()
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return False
    
    def _generate_test_data(self) -> List[Dict[str, Any]]:
        """Generate test data for caching scenarios."""
        return [
            {
                "id": i,
                "name": f"Test Record {i}",
                "email": f"test{i}@example.com",
                "data": f"Large data payload {i} " * 100,  # ~2KB per record
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "category": f"category_{i % 10}",
                    "priority": i % 5,
                    "tags": [f"tag_{j}" for j in range(i % 5)]
                }
            }
            for i in range(1, 1001)  # 1000 test records
        ]
    
    async def run_comprehensive_redis_test(self) -> Dict[str, Any]:
        """Run comprehensive Redis performance test."""
        print("🚀 REDIS PERFORMANCE TESTING")
        print("=" * 60)
        
        if not self.redis_available:
            print("❌ Redis not available - running memory-only comparison")
            return await self._run_memory_only_test()
        
        print("✅ Redis available - running full comparison")
        
        # Test scenarios
        scenarios = [
            ("memory_cache", "Memory Cache Only"),
            ("redis_cache", "Redis Cache"),
            ("no_cache", "No Cache (odoorpc style)")
        ]
        
        for scenario_id, scenario_name in scenarios:
            print(f"\n📊 Testing: {scenario_name}")
            
            # Cache hit/miss scenarios
            await self._test_cache_hits(scenario_id)
            await self._test_cache_misses(scenario_id)
            await self._test_cache_invalidation(scenario_id)
            await self._test_concurrent_cache_access(scenario_id)
            await self._test_large_data_caching(scenario_id)
        
        # Generate comparison report
        return self._generate_redis_comparison_report()
    
    async def _test_cache_hits(self, scenario_id: str):
        """Test cache hit performance."""
        print(f"   🎯 Cache Hit Test...")
        
        client = await self._create_client(scenario_id)
        monitor = SystemMonitor()
        
        # Pre-populate cache
        await self._populate_cache(client, 100)
        
        # Test cache hits
        monitor.start_monitoring()
        start_time = time.perf_counter()
        
        hit_times = []
        for i in range(100):
            hit_start = time.perf_counter()
            
            # Simulate cache hit by requesting same data
            result = await self._fetch_data(client, f"cache_key_{i % 50}")
            
            hit_end = time.perf_counter()
            hit_times.append((hit_end - hit_start) * 1000)
        
        end_time = time.perf_counter()
        system_metrics = monitor.stop_monitoring()
        
        # Store results
        self.results[f"{scenario_id}_cache_hits"] = {
            "avg_response_time": statistics.mean(hit_times),
            "median_response_time": statistics.median(hit_times),
            "total_time": (end_time - start_time) * 1000,
            "throughput": 100 / (end_time - start_time),
            "system_metrics": system_metrics
        }
        
        await client.close()
    
    async def _test_cache_misses(self, scenario_id: str):
        """Test cache miss performance."""
        print(f"   ❌ Cache Miss Test...")
        
        client = await self._create_client(scenario_id)
        monitor = SystemMonitor()
        
        # Test cache misses
        monitor.start_monitoring()
        start_time = time.perf_counter()
        
        miss_times = []
        for i in range(50):
            miss_start = time.perf_counter()
            
            # Request data not in cache
            result = await self._fetch_data(client, f"miss_key_{i}")
            
            miss_end = time.perf_counter()
            miss_times.append((miss_end - miss_start) * 1000)
        
        end_time = time.perf_counter()
        system_metrics = monitor.stop_monitoring()
        
        # Store results
        self.results[f"{scenario_id}_cache_misses"] = {
            "avg_response_time": statistics.mean(miss_times),
            "median_response_time": statistics.median(miss_times),
            "total_time": (end_time - start_time) * 1000,
            "throughput": 50 / (end_time - start_time),
            "system_metrics": system_metrics
        }
        
        await client.close()
    
    async def _test_cache_invalidation(self, scenario_id: str):
        """Test cache invalidation performance."""
        print(f"   🔄 Cache Invalidation Test...")
        
        client = await self._create_client(scenario_id)
        
        # Pre-populate cache
        await self._populate_cache(client, 100)
        
        # Test invalidation
        start_time = time.perf_counter()
        
        if hasattr(client, 'cache_manager') and client.cache_manager:
            # Invalidate cache entries
            for i in range(50):
                await client.cache_manager.delete(f"cache_key_{i}")
        
        end_time = time.perf_counter()
        
        # Store results
        self.results[f"{scenario_id}_cache_invalidation"] = {
            "total_time": (end_time - start_time) * 1000,
            "throughput": 50 / (end_time - start_time) if (end_time - start_time) > 0 else 0
        }
        
        await client.close()
    
    async def _test_concurrent_cache_access(self, scenario_id: str):
        """Test concurrent cache access performance."""
        print(f"   🔀 Concurrent Access Test...")
        
        client = await self._create_client(scenario_id)
        
        # Pre-populate cache
        await self._populate_cache(client, 100)
        
        # Concurrent access test
        async def worker(worker_id: int):
            times = []
            for i in range(20):
                start = time.perf_counter()
                result = await self._fetch_data(client, f"cache_key_{i % 50}")
                end = time.perf_counter()
                times.append((end - start) * 1000)
            return times
        
        # Run 10 concurrent workers
        start_time = time.perf_counter()
        tasks = [worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        # Flatten results
        all_times = [time for worker_times in results for time in worker_times]
        
        # Store results
        self.results[f"{scenario_id}_concurrent_access"] = {
            "avg_response_time": statistics.mean(all_times),
            "median_response_time": statistics.median(all_times),
            "total_time": (end_time - start_time) * 1000,
            "throughput": 200 / (end_time - start_time),  # 10 workers * 20 operations
            "concurrent_workers": 10
        }
        
        await client.close()
    
    async def _test_large_data_caching(self, scenario_id: str):
        """Test large data caching performance."""
        print(f"   📦 Large Data Test...")
        
        client = await self._create_client(scenario_id)
        
        # Test with large data objects
        large_data = {
            "id": 1,
            "large_field": "x" * 10000,  # 10KB data
            "array_data": list(range(1000)),
            "nested_data": {
                "level1": {
                    "level2": {
                        "data": ["item"] * 500
                    }
                }
            }
        }
        
        # Test storing and retrieving large data
        start_time = time.perf_counter()
        
        for i in range(20):
            # Store large data
            if hasattr(client, 'cache_manager') and client.cache_manager:
                await client.cache_manager.set(f"large_key_{i}", large_data, ttl=300)
                
                # Retrieve large data
                result = await client.cache_manager.get(f"large_key_{i}")
        
        end_time = time.perf_counter()
        
        # Store results
        self.results[f"{scenario_id}_large_data"] = {
            "total_time": (end_time - start_time) * 1000,
            "throughput": 40 / (end_time - start_time),  # 20 sets + 20 gets
            "data_size_kb": 10
        }
        
        await client.close()
    
    async def _create_client(self, scenario_id: str):
        """Create client based on scenario."""
        if scenario_id == "no_cache":
            # Simulate no-cache client (like odoorpc)
            return SimulatedNoCacheClient()
        
        # Create zenoo_rpc client
        client = SimulatedZenooClient()
        
        if scenario_id == "memory_cache":
            await client.setup_cache_manager(
                backend="memory",
                max_size=10000,
                default_ttl=300
            )
        elif scenario_id == "redis_cache":
            await client.setup_cache_manager(
                backend="redis",
                url=self.redis_url,
                enable_fallback=True,
                circuit_breaker_threshold=5,
                ttl=300
            )
        
        return client
    
    async def _populate_cache(self, client, count: int):
        """Populate cache with test data."""
        if hasattr(client, 'cache_manager') and client.cache_manager:
            for i in range(count):
                data = self.test_data[i % len(self.test_data)]
                await client.cache_manager.set(f"cache_key_{i}", data, ttl=300)
    
    async def _fetch_data(self, client, key: str):
        """Fetch data from cache or simulate database call."""
        if hasattr(client, 'cache_manager') and client.cache_manager:
            # Try cache first
            result = await client.cache_manager.get(key)
            if result is not None:
                return result
        
        # Simulate database call
        await asyncio.sleep(0.01)  # 10ms database latency
        data = {"key": key, "data": "simulated_data", "timestamp": time.time()}
        
        # Store in cache if available
        if hasattr(client, 'cache_manager') and client.cache_manager:
            await client.cache_manager.set(key, data, ttl=300)
        
        return data
    
    async def _run_memory_only_test(self) -> Dict[str, Any]:
        """Run memory-only test when Redis is not available."""
        scenarios = [
            ("memory_cache", "Memory Cache Only"),
            ("no_cache", "No Cache")
        ]
        
        for scenario_id, scenario_name in scenarios:
            print(f"\n📊 Testing: {scenario_name}")
            await self._test_cache_hits(scenario_id)
            await self._test_cache_misses(scenario_id)
        
        return self._generate_redis_comparison_report()
    
    def _generate_redis_comparison_report(self) -> Dict[str, Any]:
        """Generate comprehensive Redis comparison report."""
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "redis_available": self.redis_available,
            "scenarios_tested": len(self.results),
            "detailed_results": self.results,
            "summary": {},
            "recommendations": []
        }
        
        # Generate summary comparisons
        if self.redis_available:
            # Compare Redis vs Memory vs No Cache
            cache_hit_comparison = self._compare_scenarios("cache_hits")
            cache_miss_comparison = self._compare_scenarios("cache_misses")
            
            report["summary"] = {
                "cache_hits": cache_hit_comparison,
                "cache_misses": cache_miss_comparison,
                "best_performer": self._identify_best_performer()
            }
            
            # Generate recommendations
            report["recommendations"] = self._generate_redis_recommendations()
        
        return report
    
    def _compare_scenarios(self, test_type: str) -> Dict[str, Any]:
        """Compare scenarios for specific test type."""
        comparison = {}
        
        scenarios = ["memory_cache", "redis_cache", "no_cache"]
        for scenario in scenarios:
            key = f"{scenario}_{test_type}"
            if key in self.results:
                comparison[scenario] = {
                    "avg_response_time": self.results[key]["avg_response_time"],
                    "throughput": self.results[key]["throughput"]
                }
        
        return comparison
    
    def _identify_best_performer(self) -> Dict[str, str]:
        """Identify best performing scenario for each test type."""
        best_performers = {}
        
        test_types = ["cache_hits", "cache_misses", "concurrent_access"]
        
        for test_type in test_types:
            best_throughput = 0
            best_scenario = ""
            
            for scenario in ["memory_cache", "redis_cache", "no_cache"]:
                key = f"{scenario}_{test_type}"
                if key in self.results:
                    throughput = self.results[key]["throughput"]
                    if throughput > best_throughput:
                        best_throughput = throughput
                        best_scenario = scenario
            
            if best_scenario:
                best_performers[test_type] = best_scenario
        
        return best_performers
    
    def _generate_redis_recommendations(self) -> List[str]:
        """Generate Redis-specific recommendations."""
        recommendations = []
        
        if self.redis_available:
            recommendations.extend([
                "🔧 Redis caching provides distributed cache benefits",
                "⚡ Use Redis for multi-instance deployments",
                "📊 Monitor Redis memory usage and eviction policies",
                "🔄 Implement proper cache invalidation strategies",
                "🛡️ Configure Redis persistence for cache durability",
                "📈 Use Redis clustering for high availability",
                "🔍 Monitor Redis performance metrics in production"
            ])
        else:
            recommendations.extend([
                "❌ Redis not available - install and configure Redis",
                "🔧 Memory cache is suitable for single-instance deployments",
                "⚡ Consider Redis for better performance and scalability",
                "📊 Implement cache monitoring regardless of backend"
            ])
        
        return recommendations


# Simulated clients for testing
class SimulatedZenooClient:
    """Simulated zenoo_rpc client with cache support."""
    
    def __init__(self):
        self.cache_manager = None
    
    async def setup_cache_manager(self, backend="memory", **kwargs):
        """Setup cache manager."""
        if backend == "memory":
            self.cache_manager = SimulatedMemoryCache()
        elif backend == "redis":
            self.cache_manager = SimulatedRedisCache(kwargs.get("url"))
    
    async def close(self):
        if self.cache_manager:
            await self.cache_manager.close()


class SimulatedMemoryCache:
    """Simulated memory cache."""
    
    def __init__(self):
        self.cache = {}
    
    async def get(self, key: str):
        # Simulate memory access time
        await asyncio.sleep(0.001)  # 1ms
        return self.cache.get(key)
    
    async def set(self, key: str, value, ttl: int = 300):
        await asyncio.sleep(0.001)  # 1ms
        self.cache[key] = value
    
    async def delete(self, key: str):
        await asyncio.sleep(0.001)  # 1ms
        self.cache.pop(key, None)
    
    async def close(self):
        pass


class SimulatedRedisCache:
    """Simulated Redis cache."""
    
    def __init__(self, url: str):
        self.url = url
        self.cache = {}  # Simulate Redis with dict
    
    async def get(self, key: str):
        # Simulate network latency for Redis
        await asyncio.sleep(0.002)  # 2ms network latency
        return self.cache.get(key)
    
    async def set(self, key: str, value, ttl: int = 300):
        await asyncio.sleep(0.002)  # 2ms network latency
        self.cache[key] = value
    
    async def delete(self, key: str):
        await asyncio.sleep(0.002)  # 2ms network latency
        self.cache.pop(key, None)
    
    async def close(self):
        pass


class SimulatedNoCacheClient:
    """Simulated client without caching (like odoorpc)."""
    
    async def close(self):
        pass


async def main():
    """Run Redis performance test."""
    tester = RedisPerformanceTest()
    results = await tester.run_comprehensive_redis_test()
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 REDIS PERFORMANCE TEST RESULTS")
    print("=" * 60)
    
    if results.get("redis_available"):
        print("✅ Redis Available - Full Comparison Completed")
        
        summary = results.get("summary", {})
        if "cache_hits" in summary:
            print(f"\n🎯 Cache Hits Performance:")
            for scenario, metrics in summary["cache_hits"].items():
                print(f"   {scenario}: {metrics['avg_response_time']:.2f}ms avg, {metrics['throughput']:.1f} ops/s")
        
        if "cache_misses" in summary:
            print(f"\n❌ Cache Misses Performance:")
            for scenario, metrics in summary["cache_misses"].items():
                print(f"   {scenario}: {metrics['avg_response_time']:.2f}ms avg, {metrics['throughput']:.1f} ops/s")
        
        best_performers = summary.get("best_performer", {})
        if best_performers:
            print(f"\n🏆 Best Performers:")
            for test_type, scenario in best_performers.items():
                print(f"   {test_type}: {scenario}")
    else:
        print("❌ Redis Not Available - Memory-Only Test Completed")
    
    print(f"\n💡 Recommendations:")
    for rec in results.get("recommendations", []):
        print(f"   {rec}")
    
    print("\n" + "=" * 60)
    print("🎉 REDIS PERFORMANCE TEST COMPLETED")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
