"""
Hybrid Cache Strategy for zenoo_rpc

This module demonstrates an intelligent hybrid caching approach that combines
the speed of memory cache with the scalability of Redis cache for optimal
performance across different deployment scenarios.
"""

import asyncio
import time
import sys
import os
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import statistics

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class HybridCacheStrategy:
    """Intelligent hybrid caching strategy combining memory and Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize hybrid cache strategy.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.results = {}
        
        # Strategy configurations
        self.strategies = {
            "memory_only": {
                "name": "Memory Only",
                "description": "Pure memory cache for maximum speed",
                "use_case": "Single server, maximum performance"
            },
            "redis_only": {
                "name": "Redis Only", 
                "description": "Pure Redis cache for scalability",
                "use_case": "Multi-server, shared cache state"
            },
            "l1_l2_cache": {
                "name": "L1/L2 Cache",
                "description": "Memory (L1) + Redis (L2) hybrid",
                "use_case": "Best of both worlds"
            },
            "smart_routing": {
                "name": "Smart Routing",
                "description": "Intelligent cache selection based on data",
                "use_case": "Optimized for different data types"
            },
            "write_through": {
                "name": "Write-Through",
                "description": "Write to both memory and Redis",
                "use_case": "High consistency requirements"
            }
        }
    
    async def run_hybrid_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive hybrid cache benchmark."""
        print("🚀 HYBRID CACHE STRATEGY BENCHMARK")
        print("=" * 60)
        
        # Test each strategy
        for strategy_id, strategy_info in self.strategies.items():
            print(f"\n📊 Testing: {strategy_info['name']}")
            print(f"   Use Case: {strategy_info['use_case']}")
            
            await self._test_strategy(strategy_id)
        
        # Generate analysis
        analysis = self._analyze_strategies()
        
        # Display results
        self._display_strategy_comparison(analysis)
        
        return {
            "results": self.results,
            "analysis": analysis,
            "recommendations": self._generate_strategy_recommendations(analysis)
        }
    
    async def _test_strategy(self, strategy_id: str):
        """Test specific caching strategy."""
        
        # Create cache client for strategy
        cache_client = await self._create_strategy_client(strategy_id)
        
        # Test scenarios
        scenarios = [
            ("read_heavy", self._test_read_heavy_workload),
            ("write_heavy", self._test_write_heavy_workload),
            ("mixed_workload", self._test_mixed_workload),
            ("large_objects", self._test_large_objects),
            ("concurrent_access", self._test_concurrent_access)
        ]
        
        strategy_results = {}
        
        for scenario_name, test_func in scenarios:
            print(f"   🔧 {scenario_name.replace('_', ' ').title()}...")
            
            result = await test_func(cache_client)
            strategy_results[scenario_name] = result
        
        self.results[strategy_id] = strategy_results
        
        # Cleanup
        await cache_client.close()
    
    async def _test_read_heavy_workload(self, cache_client) -> Dict[str, Any]:
        """Test read-heavy workload (90% reads, 10% writes)."""
        
        # Pre-populate cache
        await self._populate_cache(cache_client, 100)
        
        read_times = []
        write_times = []
        
        # 90% reads, 10% writes
        for i in range(100):
            if i % 10 == 0:  # 10% writes
                start_time = time.perf_counter()
                await cache_client.set(f"write_key_{i}", f"data_{i}", ttl=300)
                end_time = time.perf_counter()
                write_times.append((end_time - start_time) * 1000)
            else:  # 90% reads
                start_time = time.perf_counter()
                result = await cache_client.get(f"key_{i % 50}")
                end_time = time.perf_counter()
                read_times.append((end_time - start_time) * 1000)
        
        return {
            "avg_read_time": statistics.mean(read_times) if read_times else 0,
            "avg_write_time": statistics.mean(write_times) if write_times else 0,
            "read_count": len(read_times),
            "write_count": len(write_times),
            "workload_type": "read_heavy"
        }
    
    async def _test_write_heavy_workload(self, cache_client) -> Dict[str, Any]:
        """Test write-heavy workload (30% reads, 70% writes)."""
        
        read_times = []
        write_times = []
        
        # 30% reads, 70% writes
        for i in range(100):
            if i % 10 < 3:  # 30% reads
                start_time = time.perf_counter()
                result = await cache_client.get(f"key_{i % 20}")
                end_time = time.perf_counter()
                read_times.append((end_time - start_time) * 1000)
            else:  # 70% writes
                start_time = time.perf_counter()
                await cache_client.set(f"write_key_{i}", f"data_{i}", ttl=300)
                end_time = time.perf_counter()
                write_times.append((end_time - start_time) * 1000)
        
        return {
            "avg_read_time": statistics.mean(read_times) if read_times else 0,
            "avg_write_time": statistics.mean(write_times) if write_times else 0,
            "read_count": len(read_times),
            "write_count": len(write_times),
            "workload_type": "write_heavy"
        }
    
    async def _test_mixed_workload(self, cache_client) -> Dict[str, Any]:
        """Test mixed workload (50% reads, 50% writes)."""
        
        read_times = []
        write_times = []
        
        # 50% reads, 50% writes
        for i in range(100):
            if i % 2 == 0:  # 50% reads
                start_time = time.perf_counter()
                result = await cache_client.get(f"key_{i % 30}")
                end_time = time.perf_counter()
                read_times.append((end_time - start_time) * 1000)
            else:  # 50% writes
                start_time = time.perf_counter()
                await cache_client.set(f"write_key_{i}", f"data_{i}", ttl=300)
                end_time = time.perf_counter()
                write_times.append((end_time - start_time) * 1000)
        
        return {
            "avg_read_time": statistics.mean(read_times) if read_times else 0,
            "avg_write_time": statistics.mean(write_times) if write_times else 0,
            "read_count": len(read_times),
            "write_count": len(write_times),
            "workload_type": "mixed"
        }
    
    async def _test_large_objects(self, cache_client) -> Dict[str, Any]:
        """Test large object caching performance."""
        
        # Create large objects (10KB each)
        large_object = {
            "id": 1,
            "data": "x" * 10000,
            "metadata": {"size": "10KB", "type": "large_test"}
        }
        
        store_times = []
        retrieve_times = []
        
        for i in range(20):
            # Store large object
            start_time = time.perf_counter()
            await cache_client.set(f"large_key_{i}", large_object, ttl=300)
            end_time = time.perf_counter()
            store_times.append((end_time - start_time) * 1000)
            
            # Retrieve large object
            start_time = time.perf_counter()
            result = await cache_client.get(f"large_key_{i}")
            end_time = time.perf_counter()
            retrieve_times.append((end_time - start_time) * 1000)
        
        return {
            "avg_store_time": statistics.mean(store_times),
            "avg_retrieve_time": statistics.mean(retrieve_times),
            "object_size_kb": 10,
            "operations": 40
        }
    
    async def _test_concurrent_access(self, cache_client) -> Dict[str, Any]:
        """Test concurrent access performance."""
        
        # Pre-populate cache
        await self._populate_cache(cache_client, 50)
        
        async def worker(worker_id: int):
            """Worker function for concurrent testing."""
            times = []
            for i in range(20):
                start_time = time.perf_counter()
                
                if i % 3 == 0:
                    # Write operation
                    await cache_client.set(f"concurrent_key_{worker_id}_{i}", f"data_{i}", ttl=300)
                else:
                    # Read operation
                    result = await cache_client.get(f"key_{i % 25}")
                
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            
            return times
        
        # Run 5 concurrent workers
        start_time = time.perf_counter()
        tasks = [worker(i) for i in range(5)]
        worker_results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        # Aggregate results
        all_times = [time for worker_times in worker_results for time in worker_times]
        
        return {
            "avg_response_time": statistics.mean(all_times),
            "total_operations": len(all_times),
            "total_time": (end_time - start_time) * 1000,
            "throughput": len(all_times) / (end_time - start_time),
            "concurrent_workers": 5
        }
    
    async def _create_strategy_client(self, strategy_id: str):
        """Create cache client based on strategy."""
        
        if strategy_id == "memory_only":
            return MemoryOnlyCache()
        
        elif strategy_id == "redis_only":
            return RedisOnlyCache(self.redis_url)
        
        elif strategy_id == "l1_l2_cache":
            return L1L2HybridCache(self.redis_url)
        
        elif strategy_id == "smart_routing":
            return SmartRoutingCache(self.redis_url)
        
        elif strategy_id == "write_through":
            return WriteThroughCache(self.redis_url)
        
        else:
            return MemoryOnlyCache()  # Default fallback
    
    async def _populate_cache(self, cache_client, count: int):
        """Populate cache with test data."""
        for i in range(count):
            await cache_client.set(f"key_{i}", f"data_{i}", ttl=300)
    
    def _analyze_strategies(self) -> Dict[str, Any]:
        """Analyze strategy performance."""
        analysis = {
            "best_performers": {},
            "workload_analysis": {},
            "strategy_scores": {}
        }
        
        # Analyze each workload type
        workload_types = ["read_heavy", "write_heavy", "mixed_workload", "large_objects", "concurrent_access"]
        
        for workload in workload_types:
            best_strategy = None
            best_performance = float('inf')
            
            workload_results = {}
            
            for strategy_id, strategy_results in self.results.items():
                if workload in strategy_results:
                    result = strategy_results[workload]
                    
                    # Calculate performance score based on workload type
                    if workload in ["read_heavy", "write_heavy", "mixed_workload"]:
                        # Use average read time as primary metric
                        performance_score = result.get("avg_read_time", float('inf'))
                    elif workload == "large_objects":
                        # Use average retrieve time for large objects
                        performance_score = result.get("avg_retrieve_time", float('inf'))
                    elif workload == "concurrent_access":
                        # Use average response time for concurrent access
                        performance_score = result.get("avg_response_time", float('inf'))
                    else:
                        performance_score = float('inf')
                    
                    workload_results[strategy_id] = {
                        "performance_score": performance_score,
                        "details": result
                    }
                    
                    if performance_score < best_performance:
                        best_performance = performance_score
                        best_strategy = strategy_id
            
            analysis["best_performers"][workload] = best_strategy
            analysis["workload_analysis"][workload] = workload_results
        
        # Calculate overall strategy scores
        for strategy_id in self.results.keys():
            wins = sum(1 for best in analysis["best_performers"].values() if best == strategy_id)
            analysis["strategy_scores"][strategy_id] = wins
        
        return analysis
    
    def _display_strategy_comparison(self, analysis: Dict[str, Any]):
        """Display strategy comparison results."""
        print("\n" + "=" * 60)
        print("📊 HYBRID CACHE STRATEGY ANALYSIS")
        print("=" * 60)
        
        # Best performers by workload
        print(f"\n🏆 Best Performers by Workload:")
        for workload, best_strategy in analysis["best_performers"].items():
            strategy_name = self.strategies[best_strategy]["name"]
            print(f"   {workload.replace('_', ' ').title():20}: {strategy_name}")
        
        # Overall strategy scores
        print(f"\n📈 Overall Strategy Scores:")
        sorted_strategies = sorted(analysis["strategy_scores"].items(), 
                                 key=lambda x: x[1], reverse=True)
        
        for strategy_id, score in sorted_strategies:
            strategy_name = self.strategies[strategy_id]["name"]
            print(f"   {strategy_name:20}: {score}/5 wins")
        
        # Performance details for read-heavy workload
        if "read_heavy" in analysis["workload_analysis"]:
            print(f"\n⚡ Read-Heavy Workload Performance:")
            workload_data = analysis["workload_analysis"]["read_heavy"]
            
            for strategy_id, data in workload_data.items():
                strategy_name = self.strategies[strategy_id]["name"]
                read_time = data["details"].get("avg_read_time", 0)
                print(f"   {strategy_name:20}: {read_time:6.2f}ms avg read")
    
    def _generate_strategy_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate strategy recommendations."""
        recommendations = []
        
        # Find overall best strategy
        best_strategy_id = max(analysis["strategy_scores"].items(), key=lambda x: x[1])[0]
        best_strategy_name = self.strategies[best_strategy_id]["name"]
        
        recommendations.extend([
            f"🏆 Overall best strategy: {best_strategy_name}",
            "⚡ Memory-only cache for single-server deployments",
            "🔄 L1/L2 hybrid for balanced performance and scalability",
            "🎯 Smart routing for mixed workload optimization",
            "📊 Monitor cache hit ratios to optimize strategy selection",
            "🔧 Consider workload patterns when choosing strategy"
        ])
        
        return recommendations


# Cache implementation classes
class MemoryOnlyCache:
    """Pure memory cache implementation."""
    
    def __init__(self):
        self.cache = {}
    
    async def get(self, key: str):
        await asyncio.sleep(0.0005)  # 0.5ms memory access
        return self.cache.get(key)
    
    async def set(self, key: str, value, ttl: int = 300):
        await asyncio.sleep(0.0005)  # 0.5ms memory write
        self.cache[key] = value
    
    async def close(self):
        pass


class RedisOnlyCache:
    """Pure Redis cache implementation."""
    
    def __init__(self, url: str):
        self.url = url
        self.cache = {}  # Simulated Redis
    
    async def get(self, key: str):
        await asyncio.sleep(0.002)  # 2ms network + Redis
        return self.cache.get(key)
    
    async def set(self, key: str, value, ttl: int = 300):
        await asyncio.sleep(0.002)  # 2ms network + Redis
        self.cache[key] = value
    
    async def close(self):
        pass


class L1L2HybridCache:
    """L1 (Memory) + L2 (Redis) hybrid cache."""
    
    def __init__(self, redis_url: str):
        self.l1_cache = {}  # Memory cache (L1)
        self.l2_cache = {}  # Redis cache (L2)
        self.redis_url = redis_url
    
    async def get(self, key: str):
        # Try L1 first (memory)
        await asyncio.sleep(0.0005)  # L1 access time
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # Try L2 (Redis)
        await asyncio.sleep(0.002)  # L2 access time
        if key in self.l2_cache:
            value = self.l2_cache[key]
            # Promote to L1
            self.l1_cache[key] = value
            return value
        
        return None
    
    async def set(self, key: str, value, ttl: int = 300):
        # Write to both L1 and L2
        await asyncio.sleep(0.0005)  # L1 write
        self.l1_cache[key] = value
        
        await asyncio.sleep(0.002)  # L2 write
        self.l2_cache[key] = value
    
    async def close(self):
        pass


class SmartRoutingCache:
    """Smart routing cache based on data characteristics."""
    
    def __init__(self, redis_url: str):
        self.memory_cache = {}
        self.redis_cache = {}
        self.redis_url = redis_url
    
    def _should_use_memory(self, key: str, value=None) -> bool:
        """Decide whether to use memory or Redis based on data."""
        # Small, frequently accessed data goes to memory
        if "frequent" in key or "small" in key:
            return True
        
        # Large or infrequent data goes to Redis
        if "large" in key or "infrequent" in key:
            return False
        
        # Default to memory for better performance
        return True
    
    async def get(self, key: str):
        if self._should_use_memory(key):
            await asyncio.sleep(0.0005)  # Memory access
            return self.memory_cache.get(key)
        else:
            await asyncio.sleep(0.002)  # Redis access
            return self.redis_cache.get(key)
    
    async def set(self, key: str, value, ttl: int = 300):
        if self._should_use_memory(key, value):
            await asyncio.sleep(0.0005)  # Memory write
            self.memory_cache[key] = value
        else:
            await asyncio.sleep(0.002)  # Redis write
            self.redis_cache[key] = value
    
    async def close(self):
        pass


class WriteThroughCache:
    """Write-through cache (writes to both memory and Redis)."""
    
    def __init__(self, redis_url: str):
        self.memory_cache = {}
        self.redis_cache = {}
        self.redis_url = redis_url
    
    async def get(self, key: str):
        # Always read from memory first (fastest)
        await asyncio.sleep(0.0005)  # Memory access
        return self.memory_cache.get(key)
    
    async def set(self, key: str, value, ttl: int = 300):
        # Write to both memory and Redis
        await asyncio.sleep(0.0005)  # Memory write
        self.memory_cache[key] = value
        
        await asyncio.sleep(0.002)  # Redis write
        self.redis_cache[key] = value
    
    async def close(self):
        pass


async def main():
    """Run hybrid cache strategy benchmark."""
    benchmark = HybridCacheStrategy()
    results = await benchmark.run_hybrid_benchmark()
    
    print(f"\n💡 Recommendations:")
    for rec in results["recommendations"]:
        print(f"   {rec}")
    
    print("\n" + "=" * 60)
    print("🎉 HYBRID CACHE STRATEGY BENCHMARK COMPLETED")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
