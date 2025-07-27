"""
Comprehensive Performance Test Runner

This module orchestrates comprehensive performance testing with detailed
analysis, advanced scenarios, and comprehensive reporting for zenoo_rpc
vs odoorpc comparison.
"""

import asyncio
import time
import sys
import os
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import traceback

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from comprehensive_scenarios import ComprehensiveTestSuite, TestScenario
from detailed_reporting import DetailedReportGenerator, PerformanceAnalyzer
from advanced_metrics import DetailedMetrics, SystemMonitor

# Import zenoo_rpc
from src.zenoo_rpc import ZenooClient

# Import odoorpc if available
try:
    import odoorpc
    ODOORPC_AVAILABLE = True
except ImportError:
    ODOORPC_AVAILABLE = False
    print("Warning: odoorpc not available. Install with: pip install odoorpc")


class ComprehensiveTestRunner:
    """Comprehensive test runner with advanced analysis and reporting."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize comprehensive test runner.
        
        Args:
            config: Test configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.test_suite = ComprehensiveTestSuite()
        self.report_generator = DetailedReportGenerator(
            output_dir=self.config.get("output_dir", "benchmark_results")
        )
        self.analyzer = PerformanceAnalyzer()
        
        # Test results storage
        self.results = {}
        self.global_metrics = {}
        self.test_start_time = None
        self.test_end_time = None
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default test configuration."""
        return {
            # Server configuration (using simulated data for demo)
            "use_real_server": False,
            "odoo_url": "https://demo.odoo.com",
            "odoo_database": "demo_database",
            "odoo_username": "demo_user",
            "odoo_password": "demo_password",
            
            # Test configuration
            "scenarios_to_run": "all",  # or list of scenario names
            "iterations_multiplier": 1.0,  # Scale iterations up/down
            "concurrent_users_multiplier": 1.0,  # Scale concurrency up/down
            "include_stress_tests": True,
            "include_endurance_tests": False,  # Long-running tests
            
            # Reporting configuration
            "generate_html_report": True,
            "generate_charts": True,
            "generate_executive_summary": True,
            "output_dir": "benchmark_results",
            
            # Performance thresholds
            "min_improvement_threshold": 10.0,  # Minimum % improvement expected
            "max_error_rate": 5.0,  # Maximum acceptable error rate
            "max_response_time": 5000.0,  # Maximum acceptable response time (ms)
        }
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark with all scenarios."""
        print("🚀 STARTING COMPREHENSIVE PERFORMANCE BENCHMARK")
        print("=" * 80)
        
        self.test_start_time = datetime.now()
        
        try:
            # Initialize clients
            print("🔧 Initializing test clients...")
            zenoo_client_factory = self._create_zenoo_client_factory()
            odoorpc_client_factory = self._create_odoorpc_client_factory()
            
            # Get scenarios to run
            scenarios_to_run = self._get_scenarios_to_run()
            print(f"📋 Running {len(scenarios_to_run)} test scenarios...")
            
            # Run each scenario
            for i, scenario_name in enumerate(scenarios_to_run, 1):
                print(f"\n[{i}/{len(scenarios_to_run)}] Running scenario: {scenario_name}")
                
                try:
                    scenario_results = await self.test_suite.run_scenario(
                        scenario_name,
                        zenoo_client_factory,
                        odoorpc_client_factory
                    )
                    
                    self.results[scenario_name] = scenario_results
                    
                    # Show quick results
                    comparison = scenario_results.get("comparison", {})
                    improvement = comparison.get("response_time_improvement_percent", 0)
                    grade = comparison.get("performance_grade", "C")
                    
                    print(f"   ✅ Completed - Improvement: {improvement:+.1f}%, Grade: {grade}")
                    
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
                    self.results[scenario_name] = {
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
            
            self.test_end_time = datetime.now()
            
            # Generate comprehensive analysis
            print(f"\n📊 Generating comprehensive analysis...")
            analysis_results = await self._generate_comprehensive_analysis()
            
            # Generate reports
            print(f"📄 Generating detailed reports...")
            report_paths = self._generate_reports()
            
            # Display summary
            self._display_test_summary()
            
            return {
                "results": self.results,
                "analysis": analysis_results,
                "reports": report_paths,
                "test_duration": (self.test_end_time - self.test_start_time).total_seconds(),
                "scenarios_completed": len([r for r in self.results.values() if "error" not in r]),
                "scenarios_failed": len([r for r in self.results.values() if "error" in r])
            }
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            traceback.print_exc()
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def _create_zenoo_client_factory(self) -> Callable:
        """Create zenoo_rpc client factory."""
        async def factory():
            if self.config.get("use_real_server", False):
                # Real server connection
                client = ZenooClient(self.config["odoo_url"])
                await client.login(
                    self.config["odoo_database"],
                    self.config["odoo_username"],
                    self.config["odoo_password"]
                )
                
                # Setup performance optimizations
                await client.setup_cache_manager(
                    backend="memory",
                    max_size=10000,
                    default_ttl=300
                )
                
                await client.setup_batch_manager(
                    max_chunk_size=100,
                    max_concurrency=10
                )
                
                return client
            else:
                # Simulated client for demo
                return SimulatedZenooClient()
        
        return factory
    
    def _create_odoorpc_client_factory(self) -> Callable:
        """Create odoorpc client factory."""
        async def factory():
            if self.config.get("use_real_server", False) and ODOORPC_AVAILABLE:
                # Real server connection
                from urllib.parse import urlparse
                parsed = urlparse(self.config["odoo_url"])
                host = parsed.hostname
                port = parsed.port or (443 if parsed.scheme == 'https' else 80)

                client = odoorpc.ODOO(host, port=port, protocol=parsed.scheme)
                client.login(
                    self.config["odoo_database"],
                    self.config["odoo_username"],
                    self.config["odoo_password"]
                )
                return client
            else:
                # Simulated client for demo
                return SimulatedOdooRPCClient()

        return factory
    
    def _get_scenarios_to_run(self) -> List[str]:
        """Get list of scenarios to run based on configuration."""
        all_scenarios = list(self.test_suite.scenarios.keys())
        
        scenarios_config = self.config.get("scenarios_to_run", "all")
        
        if scenarios_config == "all":
            scenarios = all_scenarios
        elif isinstance(scenarios_config, list):
            scenarios = [s for s in scenarios_config if s in all_scenarios]
        else:
            scenarios = all_scenarios
        
        # Filter based on test type preferences
        if not self.config.get("include_stress_tests", True):
            scenarios = [s for s in scenarios if "stress" not in s.lower()]
        
        if not self.config.get("include_endurance_tests", False):
            scenarios = [s for s in scenarios if "endurance" not in s.lower()]
        
        return scenarios
    
    async def _generate_comprehensive_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive performance analysis."""
        analysis = {
            "performance_trends": self.analyzer.analyze_performance_trends(self.results),
            "bottlenecks": self.analyzer.identify_performance_bottlenecks(self.results),
            "statistical_summary": self._generate_statistical_summary(),
            "performance_grades": self._calculate_performance_grades(),
            "recommendations": self._generate_detailed_recommendations()
        }
        
        return analysis
    
    def _generate_reports(self) -> Dict[str, str]:
        """Generate comprehensive reports."""
        test_config = {
            "config": self.config,
            "test_duration": (self.test_end_time - self.test_start_time).total_seconds(),
            "scenarios_run": len(self.results),
            "timestamp": self.test_start_time.isoformat()
        }
        
        return self.report_generator.generate_comprehensive_report(
            self.results,
            test_config
        )
    
    def _generate_statistical_summary(self) -> Dict[str, Any]:
        """Generate statistical summary of all results."""
        all_improvements = []
        all_throughput_improvements = []
        all_grades = []
        
        for scenario_results in self.results.values():
            if "error" not in scenario_results:
                comparison = scenario_results.get("comparison", {})
                
                response_improvement = comparison.get("response_time_improvement_percent", 0)
                throughput_improvement = comparison.get("throughput_improvement_percent", 0)
                grade = comparison.get("performance_grade", "C")
                
                all_improvements.append(response_improvement)
                all_throughput_improvements.append(throughput_improvement)
                all_grades.append(grade)
        
        import statistics
        
        return {
            "response_time_improvements": {
                "mean": statistics.mean(all_improvements) if all_improvements else 0,
                "median": statistics.median(all_improvements) if all_improvements else 0,
                "min": min(all_improvements) if all_improvements else 0,
                "max": max(all_improvements) if all_improvements else 0,
                "std_dev": statistics.stdev(all_improvements) if len(all_improvements) > 1 else 0
            },
            "throughput_improvements": {
                "mean": statistics.mean(all_throughput_improvements) if all_throughput_improvements else 0,
                "median": statistics.median(all_throughput_improvements) if all_throughput_improvements else 0,
                "min": min(all_throughput_improvements) if all_throughput_improvements else 0,
                "max": max(all_throughput_improvements) if all_throughput_improvements else 0,
                "std_dev": statistics.stdev(all_throughput_improvements) if len(all_throughput_improvements) > 1 else 0
            },
            "grade_distribution": {grade: all_grades.count(grade) for grade in set(all_grades)}
        }
    
    def _calculate_performance_grades(self) -> Dict[str, str]:
        """Calculate performance grades for each scenario."""
        grades = {}
        
        for scenario_name, scenario_results in self.results.items():
            if "error" not in scenario_results:
                comparison = scenario_results.get("comparison", {})
                grades[scenario_name] = comparison.get("performance_grade", "C")
        
        return grades
    
    def _generate_detailed_recommendations(self) -> List[Dict[str, Any]]:
        """Generate detailed recommendations based on analysis."""
        recommendations = []
        
        # Analyze overall performance
        stats = self._generate_statistical_summary()
        avg_improvement = stats["response_time_improvements"]["mean"]
        
        if avg_improvement > 50:
            recommendations.append({
                "priority": "high",
                "category": "migration",
                "title": "Immediate Migration Recommended",
                "description": f"With {avg_improvement:.1f}% average improvement, immediate migration to zenoo_rpc is strongly recommended",
                "impact": "high",
                "effort": "medium"
            })
        
        # Analyze bottlenecks
        bottlenecks = self.analyzer.identify_performance_bottlenecks(self.results)
        if bottlenecks:
            recommendations.append({
                "priority": "medium",
                "category": "optimization",
                "title": "Address Performance Bottlenecks",
                "description": f"Found {len(bottlenecks)} potential bottlenecks that should be addressed",
                "impact": "medium",
                "effort": "low"
            })
        
        # Add standard recommendations
        recommendations.extend([
            {
                "priority": "high",
                "category": "caching",
                "title": "Enable Intelligent Caching",
                "description": "Implement caching for frequently accessed data to maximize performance gains",
                "impact": "high",
                "effort": "low"
            },
            {
                "priority": "medium",
                "category": "monitoring",
                "title": "Implement Performance Monitoring",
                "description": "Set up comprehensive monitoring to track performance in production",
                "impact": "medium",
                "effort": "medium"
            }
        ])
        
        return recommendations
    
    def _display_test_summary(self):
        """Display comprehensive test summary."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE BENCHMARK SUMMARY")
        print("=" * 80)
        
        # Test execution summary
        duration = (self.test_end_time - self.test_start_time).total_seconds()
        completed = len([r for r in self.results.values() if "error" not in r])
        failed = len([r for r in self.results.values() if "error" in r])
        
        print(f"⏱️  Test Duration: {duration:.1f} seconds")
        print(f"✅ Scenarios Completed: {completed}")
        print(f"❌ Scenarios Failed: {failed}")
        print(f"📈 Success Rate: {(completed / len(self.results) * 100):.1f}%")
        
        # Performance summary
        stats = self._generate_statistical_summary()
        avg_improvement = stats["response_time_improvements"]["mean"]
        max_improvement = stats["response_time_improvements"]["max"]
        
        print(f"\n🎯 PERFORMANCE RESULTS:")
        print(f"   Average Improvement: {avg_improvement:.1f}%")
        print(f"   Best Improvement: {max_improvement:.1f}%")
        print(f"   Throughput Gain: {stats['throughput_improvements']['mean']:.1f}%")
        
        # Grade distribution
        grade_dist = stats["grade_distribution"]
        print(f"\n🏆 GRADE DISTRIBUTION:")
        for grade, count in sorted(grade_dist.items()):
            print(f"   Grade {grade}: {count} scenarios")
        
        print("\n" + "=" * 80)
        print("🎉 COMPREHENSIVE BENCHMARK COMPLETED")
        print("=" * 80)


# Simulated clients for demo purposes
class SimulatedZenooClient:
    """Simulated zenoo_rpc client for demo."""
    
    async def search_read(self, model, domain=None, fields=None, limit=None):
        # Simulate faster response
        await asyncio.sleep(0.02 + (limit or 10) * 0.001)
        return [{"id": i, "name": f"Record {i}"} for i in range(min(limit or 10, 100))]
    
    async def execute_kw(self, model, method, args):
        await asyncio.sleep(0.05)
        return 12345
    
    async def close(self):
        pass


class SimulatedOdooRPCClient:
    """Simulated odoorpc client for demo."""
    
    def __init__(self):
        self.env = SimulatedEnv()
    
    def logout(self):
        pass


class SimulatedEnv:
    """Simulated odoorpc environment."""
    
    def __getitem__(self, model_name):
        return SimulatedModel()


class SimulatedModel:
    """Simulated odoorpc model."""
    
    def search_read(self, domain=None, fields=None, limit=None):
        # Simulate slower response
        time.sleep(0.08 + (limit or 10) * 0.002)
        return [{"id": i, "name": f"Record {i}"} for i in range(min(limit or 10, 100))]
    
    def create(self, values):
        time.sleep(0.12)
        return 12345
    
    def browse(self, ids):
        return SimulatedRecord()
    
    def search(self, domain=None, limit=None):
        time.sleep(0.06)
        return list(range(min(limit or 10, 100)))


class SimulatedRecord:
    """Simulated odoorpc record."""
    
    def write(self, values):
        time.sleep(0.09)
        return True


async def main():
    """Main function to run comprehensive benchmark."""
    # Configuration for demo
    config = {
        "use_real_server": False,  # Use simulated clients for demo
        "scenarios_to_run": [
            "crud_light_load",
            "crud_medium_load", 
            "crud_heavy_load",
            "stress_concurrent_reads",
            "memory_large_datasets",
            "workflow_sales_process"
        ],
        "include_stress_tests": True,
        "include_endurance_tests": False,
        "generate_html_report": True,
        "generate_charts": False,  # Disable charts for demo
        "output_dir": "comprehensive_benchmark_results"
    }
    
    # Run comprehensive benchmark
    runner = ComprehensiveTestRunner(config)
    results = await runner.run_comprehensive_benchmark()
    
    if "error" not in results:
        print(f"\n📄 Reports generated in: {config['output_dir']}")
        print("   - detailed.json: Complete raw data")
        print("   - summary.csv: Data for analysis")
        print("   - report.html: Comprehensive visual report")
        print("   - executive_summary.txt: Executive summary")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
