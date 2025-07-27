"""
Performance Benchmark Configuration

This module provides configuration settings for performance benchmarks
between zenoo_rpc and odoorpc, including test scenarios, data generation,
and reporting options.
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class BenchmarkConfig:
    """Configuration for performance benchmarks."""
    
    # Server configuration - Use environment variables for real testing
    odoo_url: str = "https://demo.odoo.com"
    odoo_database: str = "demo_database"
    odoo_username: str = "demo_user"
    odoo_password: str = "demo_password"
    
    # Test configuration
    iterations_per_test: int = 10
    warmup_iterations: int = 3
    concurrent_users: int = 10
    batch_sizes: List[int] = None
    
    # Data configuration
    test_records_count: int = 1000
    bulk_operation_size: int = 100
    large_dataset_size: int = 10000
    
    # Performance thresholds
    max_response_time_ms: float = 5000.0
    min_throughput_ops_per_sec: float = 10.0
    max_memory_usage_mb: float = 500.0
    max_error_rate_percent: float = 1.0
    
    # Reporting configuration
    generate_charts: bool = True
    save_raw_data: bool = True
    output_directory: str = "benchmark_results"
    
    def __post_init__(self):
        """Initialize default values."""
        if self.batch_sizes is None:
            self.batch_sizes = [10, 50, 100, 500, 1000]
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_directory, exist_ok=True)


# Test scenarios configuration
BENCHMARK_SCENARIOS = {
    "basic_crud": {
        "description": "Basic CRUD operations performance",
        "tests": [
            "single_read",
            "bulk_read", 
            "create",
            "update",
            "delete"
        ],
        "record_counts": [1, 10, 100, 1000],
        "iterations": 20
    },
    
    "concurrent_access": {
        "description": "Concurrent access patterns",
        "tests": [
            "concurrent_reads",
            "concurrent_writes",
            "mixed_operations"
        ],
        "concurrent_users": [1, 5, 10, 20, 50],
        "iterations": 10
    },
    
    "batch_operations": {
        "description": "Batch processing performance",
        "tests": [
            "batch_create",
            "batch_update",
            "batch_delete"
        ],
        "batch_sizes": [10, 50, 100, 500, 1000],
        "iterations": 15
    },
    
    "memory_efficiency": {
        "description": "Memory usage and efficiency",
        "tests": [
            "large_dataset_processing",
            "memory_leak_detection",
            "garbage_collection_impact"
        ],
        "dataset_sizes": [1000, 5000, 10000, 50000],
        "iterations": 5
    },
    
    "real_world_workflows": {
        "description": "Real-world ERP workflows",
        "tests": [
            "sales_order_workflow",
            "purchase_order_workflow",
            "inventory_management",
            "accounting_entries",
            "reporting_queries"
        ],
        "complexity_levels": ["simple", "medium", "complex"],
        "iterations": 10
    },
    
    "caching_performance": {
        "description": "Caching system performance (zenoo_rpc only)",
        "tests": [
            "cache_hit_performance",
            "cache_miss_performance",
            "cache_invalidation",
            "cache_stampede_prevention"
        ],
        "cache_sizes": [100, 500, 1000, 5000],
        "iterations": 25
    },
    
    "connection_management": {
        "description": "Connection pooling and management",
        "tests": [
            "connection_establishment",
            "connection_reuse",
            "connection_pooling",
            "connection_timeout_handling"
        ],
        "pool_sizes": [1, 5, 10, 20],
        "iterations": 15
    }
}

# Mock data generators
MOCK_DATA_GENERATORS = {
    "res.partner": {
        "fields": ["name", "email", "phone", "is_company", "customer_rank", "supplier_rank"],
        "generator": lambda i: {
            "id": i,
            "name": f"Partner {i}",
            "email": f"partner{i}@test.com",
            "phone": f"+1-555-{i:04d}",
            "is_company": i % 3 == 0,
            "customer_rank": 1 if i % 2 == 0 else 0,
            "supplier_rank": 1 if i % 4 == 0 else 0
        }
    },
    
    "product.product": {
        "fields": ["name", "list_price", "standard_price", "type", "sale_ok", "purchase_ok"],
        "generator": lambda i: {
            "id": i,
            "name": f"Product {i}",
            "list_price": 100.0 + (i * 0.5),
            "standard_price": 80.0 + (i * 0.4),
            "type": "product" if i % 2 == 0 else "service",
            "sale_ok": True,
            "purchase_ok": i % 3 == 0
        }
    },
    
    "sale.order": {
        "fields": ["name", "partner_id", "date_order", "amount_total", "state"],
        "generator": lambda i: {
            "id": i,
            "name": f"SO{i:05d}",
            "partner_id": (i % 100) + 1,
            "date_order": "2024-01-01",
            "amount_total": 1000.0 + (i * 10),
            "state": "draft" if i % 3 == 0 else "sale"
        }
    },
    
    "sale.order.line": {
        "fields": ["order_id", "product_id", "product_uom_qty", "price_unit"],
        "generator": lambda i: {
            "id": i,
            "order_id": (i // 3) + 1,
            "product_id": (i % 50) + 1,
            "product_uom_qty": (i % 10) + 1,
            "price_unit": 50.0 + (i * 0.25)
        }
    }
}

# Performance expectations
PERFORMANCE_EXPECTATIONS = {
    "zenoo_rpc": {
        "single_read": {"max_response_time": 50, "min_throughput": 100},
        "bulk_read": {"max_response_time": 200, "min_throughput": 50},
        "create": {"max_response_time": 100, "min_throughput": 80},
        "update": {"max_response_time": 80, "min_throughput": 90},
        "concurrent_reads": {"max_response_time": 100, "min_throughput": 200},
        "batch_create": {"max_response_time": 500, "min_throughput": 20},
        "memory_test": {"max_memory_usage": 200},
        "sales_workflow": {"max_response_time": 1000, "min_throughput": 10}
    },
    
    "odoorpc": {
        "single_read": {"max_response_time": 100, "min_throughput": 50},
        "bulk_read": {"max_response_time": 500, "min_throughput": 20},
        "create": {"max_response_time": 200, "min_throughput": 40},
        "update": {"max_response_time": 150, "min_throughput": 50},
        "concurrent_reads": {"max_response_time": 1000, "min_throughput": 10},
        "batch_create": {"max_response_time": 2000, "min_throughput": 5},
        "memory_test": {"max_memory_usage": 300},
        "sales_workflow": {"max_response_time": 3000, "min_throughput": 3}
    }
}

# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    "development": {
        "iterations_per_test": 5,
        "test_records_count": 100,
        "concurrent_users": 5,
        "timeout": 30
    },
    
    "testing": {
        "iterations_per_test": 10,
        "test_records_count": 1000,
        "concurrent_users": 10,
        "timeout": 60
    },
    
    "production": {
        "iterations_per_test": 50,
        "test_records_count": 10000,
        "concurrent_users": 50,
        "timeout": 300
    }
}

def get_config(environment: str = "testing") -> BenchmarkConfig:
    """Get benchmark configuration for specified environment.
    
    Args:
        environment: Environment name (development, testing, production)
        
    Returns:
        BenchmarkConfig instance
    """
    base_config = BenchmarkConfig()
    
    if environment in ENVIRONMENT_CONFIGS:
        env_config = ENVIRONMENT_CONFIGS[environment]
        for key, value in env_config.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)
    
    return base_config


def generate_mock_data(model: str, count: int) -> List[Dict[str, Any]]:
    """Generate mock data for testing.
    
    Args:
        model: Model name (e.g., 'res.partner')
        count: Number of records to generate
        
    Returns:
        List of mock records
    """
    if model not in MOCK_DATA_GENERATORS:
        raise ValueError(f"No mock data generator for model: {model}")
    
    generator = MOCK_DATA_GENERATORS[model]["generator"]
    return [generator(i + 1) for i in range(count)]


def get_performance_expectations(library: str, operation: str) -> Dict[str, float]:
    """Get performance expectations for library and operation.
    
    Args:
        library: Library name (zenoo_rpc or odoorpc)
        operation: Operation name
        
    Returns:
        Dictionary with performance expectations
    """
    if library not in PERFORMANCE_EXPECTATIONS:
        return {}
    
    return PERFORMANCE_EXPECTATIONS[library].get(operation, {})
