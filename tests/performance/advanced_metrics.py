"""
Advanced Performance Metrics Collection and Analysis

This module provides comprehensive performance metrics collection with
statistical analysis, detailed reporting, and advanced visualization
capabilities for zenoo_rpc vs odoorpc benchmarking.
"""

import time
import psutil
import threading
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import csv
from datetime import datetime, timedelta
import asyncio
import gc
import tracemalloc
import sys
import os


@dataclass
class DetailedMetrics:
    """Comprehensive performance metrics with statistical analysis."""
    
    operation: str
    library: str
    test_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Response time metrics (milliseconds)
    response_times: List[float] = field(default_factory=list)
    
    # System resource metrics
    cpu_usage: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    memory_peak: float = 0.0
    memory_baseline: float = 0.0
    
    # Network metrics
    bytes_sent: List[int] = field(default_factory=list)
    bytes_received: List[int] = field(default_factory=list)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    timeouts: int = 0
    connection_errors: int = 0
    
    # Concurrency metrics
    concurrent_operations: int = 0
    queue_wait_times: List[float] = field(default_factory=list)
    
    # Success/failure counts
    success_count: int = 0
    total_operations: int = 0
    
    # Timing details
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration: float = 0.0
    
    # Advanced statistics
    _percentiles_cache: Optional[Dict[str, float]] = None
    _outliers_cache: Optional[List[float]] = None
    
    def add_response_time(self, response_time: float, success: bool = True):
        """Add response time measurement."""
        self.response_times.append(response_time)
        self.total_operations += 1
        if success:
            self.success_count += 1
    
    def add_system_metrics(self, cpu: float, memory: float):
        """Add system resource metrics."""
        self.cpu_usage.append(cpu)
        self.memory_usage.append(memory)
        if memory > self.memory_peak:
            self.memory_peak = memory
    
    def add_network_metrics(self, sent: int, received: int):
        """Add network metrics."""
        self.bytes_sent.append(sent)
        self.bytes_received.append(received)
    
    def add_error(self, error_type: str, message: str, traceback: str = ""):
        """Add error information."""
        self.errors.append({
            "type": error_type,
            "message": message,
            "traceback": traceback,
            "timestamp": datetime.now().isoformat()
        })
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.success_count / self.total_operations) * 100
    
    @property
    def error_rate(self) -> float:
        """Error rate as percentage."""
        return 100.0 - self.success_rate
    
    @property
    def avg_response_time(self) -> float:
        """Average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def median_response_time(self) -> float:
        """Median response time."""
        return statistics.median(self.response_times) if self.response_times else 0.0
    
    @property
    def std_deviation(self) -> float:
        """Standard deviation of response times."""
        return statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0.0
    
    @property
    def coefficient_of_variation(self) -> float:
        """Coefficient of variation (std_dev / mean)."""
        mean = self.avg_response_time
        return (self.std_deviation / mean) if mean > 0 else 0.0
    
    @property
    def percentiles(self) -> Dict[str, float]:
        """Calculate percentiles for response times."""
        if self._percentiles_cache is None and self.response_times:
            sorted_times = sorted(self.response_times)
            n = len(sorted_times)
            
            self._percentiles_cache = {
                "p50": np.percentile(sorted_times, 50),
                "p75": np.percentile(sorted_times, 75),
                "p90": np.percentile(sorted_times, 90),
                "p95": np.percentile(sorted_times, 95),
                "p99": np.percentile(sorted_times, 99),
                "p99.9": np.percentile(sorted_times, 99.9),
            }
        
        return self._percentiles_cache or {}
    
    @property
    def outliers(self) -> List[float]:
        """Identify outliers using IQR method."""
        if self._outliers_cache is None and len(self.response_times) > 4:
            q1 = np.percentile(self.response_times, 25)
            q3 = np.percentile(self.response_times, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            self._outliers_cache = [
                t for t in self.response_times 
                if t < lower_bound or t > upper_bound
            ]
        
        return self._outliers_cache or []
    
    @property
    def throughput(self) -> float:
        """Operations per second."""
        if self.total_duration > 0:
            return self.success_count / self.total_duration
        return 0.0
    
    @property
    def avg_cpu_usage(self) -> float:
        """Average CPU usage percentage."""
        return statistics.mean(self.cpu_usage) if self.cpu_usage else 0.0
    
    @property
    def avg_memory_usage(self) -> float:
        """Average memory usage in MB."""
        return statistics.mean(self.memory_usage) if self.memory_usage else 0.0
    
    @property
    def memory_growth(self) -> float:
        """Memory growth from baseline in MB."""
        return self.memory_peak - self.memory_baseline
    
    @property
    def total_bytes_transferred(self) -> int:
        """Total bytes sent and received."""
        return sum(self.bytes_sent) + sum(self.bytes_received)
    
    @property
    def avg_request_size(self) -> float:
        """Average request size in bytes."""
        return statistics.mean(self.bytes_sent) if self.bytes_sent else 0.0
    
    @property
    def avg_response_size(self) -> float:
        """Average response size in bytes."""
        return statistics.mean(self.bytes_received) if self.bytes_received else 0.0
    
    def get_latency_distribution(self, bins: int = 20) -> Dict[str, List]:
        """Get latency distribution for histogram."""
        if not self.response_times:
            return {"bins": [], "counts": []}
        
        hist, bin_edges = np.histogram(self.response_times, bins=bins)
        return {
            "bins": bin_edges.tolist(),
            "counts": hist.tolist(),
            "bin_centers": [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "operation": self.operation,
            "library": self.library,
            "test_id": self.test_id,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_operations": self.total_operations,
                "success_count": self.success_count,
                "success_rate": self.success_rate,
                "error_rate": self.error_rate,
                "total_duration": self.total_duration,
                "throughput": self.throughput
            },
            "response_times": {
                "avg": self.avg_response_time,
                "median": self.median_response_time,
                "std_dev": self.std_deviation,
                "coefficient_of_variation": self.coefficient_of_variation,
                "percentiles": self.percentiles,
                "outliers_count": len(self.outliers),
                "min": min(self.response_times) if self.response_times else 0,
                "max": max(self.response_times) if self.response_times else 0
            },
            "system_resources": {
                "avg_cpu_usage": self.avg_cpu_usage,
                "avg_memory_usage": self.avg_memory_usage,
                "memory_peak": self.memory_peak,
                "memory_growth": self.memory_growth
            },
            "network": {
                "total_bytes_transferred": self.total_bytes_transferred,
                "avg_request_size": self.avg_request_size,
                "avg_response_size": self.avg_response_size
            },
            "errors": {
                "total_errors": len(self.errors),
                "timeouts": self.timeouts,
                "connection_errors": self.connection_errors,
                "error_details": self.errors
            },
            "latency_distribution": self.get_latency_distribution()
        }


class SystemMonitor:
    """Real-time system resource monitoring."""
    
    def __init__(self, interval: float = 0.1):
        """Initialize system monitor.
        
        Args:
            interval: Monitoring interval in seconds
        """
        self.interval = interval
        self.monitoring = False
        self.metrics = defaultdict(list)
        self.process = psutil.Process()
        self._monitor_thread = None
        
        # Network baseline
        self.network_baseline = psutil.net_io_counters()
    
    def start_monitoring(self):
        """Start system monitoring in background thread."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.metrics.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, List[float]]:
        """Stop monitoring and return collected metrics."""
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        return dict(self.metrics)
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.metrics["cpu_usage"].append(cpu_percent)
                
                # Memory usage
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.metrics["memory_usage"].append(memory_mb)
                
                # System-wide metrics
                system_cpu = psutil.cpu_percent()
                system_memory = psutil.virtual_memory().percent
                self.metrics["system_cpu"].append(system_cpu)
                self.metrics["system_memory"].append(system_memory)
                
                # Network I/O
                net_io = psutil.net_io_counters()
                bytes_sent = net_io.bytes_sent - self.network_baseline.bytes_sent
                bytes_recv = net_io.bytes_recv - self.network_baseline.bytes_recv
                self.metrics["bytes_sent"].append(bytes_sent)
                self.metrics["bytes_received"].append(bytes_recv)
                
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                break
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current system metrics snapshot."""
        try:
            memory_info = self.process.memory_info()
            net_io = psutil.net_io_counters()
            
            return {
                "cpu_percent": self.process.cpu_percent(),
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_vms": memory_info.vms / 1024 / 1024,
                "system_cpu": psutil.cpu_percent(),
                "system_memory": psutil.virtual_memory().percent,
                "bytes_sent": net_io.bytes_sent - self.network_baseline.bytes_sent,
                "bytes_received": net_io.bytes_recv - self.network_baseline.bytes_recv
            }
        except Exception as e:
            print(f"Error getting current metrics: {e}")
            return {}


class MemoryProfiler:
    """Memory profiling with tracemalloc."""
    
    def __init__(self):
        """Initialize memory profiler."""
        self.snapshots = []
        self.baseline_snapshot = None
    
    def start_profiling(self):
        """Start memory profiling."""
        tracemalloc.start()
        self.baseline_snapshot = tracemalloc.take_snapshot()
    
    def take_snapshot(self, label: str = ""):
        """Take memory snapshot."""
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            self.snapshots.append({
                "label": label,
                "snapshot": snapshot,
                "timestamp": datetime.now()
            })
            return snapshot
        return None
    
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return analysis."""
        if not tracemalloc.is_tracing():
            return {}
        
        final_snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        
        if self.baseline_snapshot:
            top_stats = final_snapshot.compare_to(self.baseline_snapshot, 'lineno')
            
            return {
                "memory_growth": sum(stat.size_diff for stat in top_stats),
                "top_allocations": [
                    {
                        "filename": stat.traceback.format()[0] if stat.traceback else "unknown",
                        "size_diff": stat.size_diff,
                        "count_diff": stat.count_diff
                    }
                    for stat in top_stats[:10]
                ]
            }
        
        return {}


def measure_performance(operation: str, library: str, test_id: str = None):
    """Decorator for comprehensive performance measurement."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Initialize metrics
            metrics = DetailedMetrics(
                operation=operation,
                library=library,
                test_id=test_id or f"{operation}_{library}_{int(time.time())}"
            )
            
            # Start monitoring
            monitor = SystemMonitor()
            profiler = MemoryProfiler()
            
            metrics.start_time = datetime.now()
            metrics.memory_baseline = psutil.Process().memory_info().rss / 1024 / 1024
            
            monitor.start_monitoring()
            profiler.start_profiling()
            
            try:
                # Execute operation
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                metrics.add_response_time(response_time, success=True)
                
            except Exception as e:
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                
                metrics.add_response_time(response_time, success=False)
                metrics.add_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback=traceback.format_exc()
                )
                raise e
            
            finally:
                metrics.end_time = datetime.now()
                metrics.total_duration = (metrics.end_time - metrics.start_time).total_seconds()
                
                # Stop monitoring and collect metrics
                system_metrics = monitor.stop_monitoring()
                memory_analysis = profiler.stop_profiling()
                
                # Add system metrics to our metrics object
                if "cpu_usage" in system_metrics:
                    metrics.cpu_usage = system_metrics["cpu_usage"]
                if "memory_usage" in system_metrics:
                    metrics.memory_usage = system_metrics["memory_usage"]
                if "bytes_sent" in system_metrics:
                    metrics.bytes_sent = system_metrics["bytes_sent"]
                if "bytes_received" in system_metrics:
                    metrics.bytes_received = system_metrics["bytes_received"]
            
            return result, metrics
        
        def sync_wrapper(*args, **kwargs):
            # Similar implementation for sync functions
            metrics = DetailedMetrics(
                operation=operation,
                library=library,
                test_id=test_id or f"{operation}_{library}_{int(time.time())}"
            )
            
            monitor = SystemMonitor()
            metrics.start_time = datetime.now()
            metrics.memory_baseline = psutil.Process().memory_info().rss / 1024 / 1024
            
            monitor.start_monitoring()
            
            try:
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                
                response_time = (end_time - start_time) * 1000
                metrics.add_response_time(response_time, success=True)
                
            except Exception as e:
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                
                metrics.add_response_time(response_time, success=False)
                metrics.add_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback=traceback.format_exc()
                )
                raise e
            
            finally:
                metrics.end_time = datetime.now()
                metrics.total_duration = (metrics.end_time - metrics.start_time).total_seconds()
                
                system_metrics = monitor.stop_monitoring()
                if "cpu_usage" in system_metrics:
                    metrics.cpu_usage = system_metrics["cpu_usage"]
                if "memory_usage" in system_metrics:
                    metrics.memory_usage = system_metrics["memory_usage"]
            
            return result, metrics
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
