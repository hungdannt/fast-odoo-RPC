# Testing Guide

Comprehensive testing guide for Zenoo RPC covering unit tests, integration tests, performance tests, and testing best practices.

## Testing Philosophy

Zenoo RPC follows a comprehensive testing strategy:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and real Odoo connectivity
- **Performance Tests**: Validate performance characteristics and benchmarks
- **End-to-End Tests**: Test complete workflows and user scenarios
- **Property-Based Tests**: Test with generated data to find edge cases

## Test Structure

### Test Organization

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_client.py       # Client tests
│   ├── test_models.py       # Model tests
│   ├── test_query.py        # Query builder tests
│   ├── test_cache.py        # Cache tests
│   ├── test_batch.py        # Batch operation tests
│   └── test_retry.py        # Retry mechanism tests
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_odoo_integration.py
│   ├── test_cache_backends.py
│   └── test_real_workflows.py
├── performance/             # Performance tests
│   ├── __init__.py
│   ├── test_benchmarks.py
│   └── test_memory_usage.py
├── fixtures/                # Test data and fixtures
│   ├── __init__.py
│   ├── sample_data.py
│   └── mock_responses.py
└── utils/                   # Test utilities
    ├── __init__.py
    ├── helpers.py
    └── assertions.py
```

### Test Configuration

```python
# tests/conftest.py
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator, Generator

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.transport.httpx_transport import AsyncTransport

# Pytest configuration
pytest_plugins = ["pytest_asyncio"]

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_transport() -> AsyncMock:
    """Create mock transport for testing."""
    transport = AsyncMock(spec=AsyncTransport)
    transport.json_rpc_call.return_value = {"result": "success"}
    return transport

@pytest.fixture
async def mock_client(mock_transport) -> AsyncGenerator[ZenooClient, None]:
    """Create mock client for testing."""
    client = ZenooClient("localhost", port=8069)
    client.transport = mock_transport
    client.uid = 1
    client.database = "test_db"
    client.password = "test_password"
    
    yield client
    
    await client.close()

@pytest.fixture
def sample_partner_data() -> dict:
    """Sample partner data for testing."""
    return {
        "id": 1,
        "name": "Test Company",
        "is_company": True,
        "email": "test@example.com",
        "phone": "+1-555-0100",
        "active": True
    }

# Integration test fixtures
@pytest.fixture(scope="session")
async def real_client() -> AsyncGenerator[ZenooClient, None]:
    """Create real client for integration tests."""
    if not os.getenv("ODOO_TEST_URL"):
        pytest.skip("No Odoo test server configured")
    
    client = ZenooClient(
        host=os.getenv("ODOO_TEST_URL", "localhost"),
        port=int(os.getenv("ODOO_TEST_PORT", "8069"))
    )
    
    try:
        await client.login(
            database=os.getenv("ODOO_TEST_DB", "demo"),
            username=os.getenv("ODOO_TEST_USER", "admin"),
            password=os.getenv("ODOO_TEST_PASSWORD", "admin")
        )
        yield client
    finally:
        await client.close()
```

## Unit Testing

### Client Testing

```python
# tests/unit/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import AuthenticationError, NetworkError

class TestZenooClient:
    """Test suite for ZenooClient."""
    
    async def test_login_success(self, mock_client, mock_transport):
        """Test successful login."""
        mock_transport.json_rpc_call.return_value = 1  # User ID
        
        await mock_client.login("demo", "admin", "admin")
        
        assert mock_client.uid == 1
        assert mock_client.database == "demo"
        mock_transport.json_rpc_call.assert_called_once_with(
            "common", "authenticate", ["demo", "admin", "admin", {}]
        )
    
    async def test_login_failure(self, mock_client, mock_transport):
        """Test login failure."""
        mock_transport.json_rpc_call.return_value = False
        
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await mock_client.login("demo", "admin", "wrong_password")
    
    @pytest.mark.parametrize("domain,expected_call", [
        ([], []),
        ([("name", "=", "Test")], [("name", "=", "Test")]),
        ([("id", "in", [1, 2, 3])], [("id", "in", [1, 2, 3])]),
    ])
    async def test_search_domains(self, mock_client, mock_transport, domain, expected_call):
        """Test search with different domains."""
        mock_transport.json_rpc_call.return_value = [1, 2, 3]
        
        result = await mock_client.search("res.partner", domain)
        
        assert result == [1, 2, 3]
        mock_transport.json_rpc_call.assert_called_with(
            "object", "execute_kw", [
                mock_client.database, mock_client.uid, mock_client.password,
                "res.partner", "search", [expected_call]
            ]
        )
    
    async def test_create_record(self, mock_client, mock_transport, sample_partner_data):
        """Test record creation."""
        mock_transport.json_rpc_call.return_value = 1  # Created ID
        
        result = await mock_client.create("res.partner", sample_partner_data)
        
        assert result == 1
        mock_transport.json_rpc_call.assert_called_with(
            "object", "execute_kw", [
                mock_client.database, mock_client.uid, mock_client.password,
                "res.partner", "create", [sample_partner_data]
            ]
        )
    
    async def test_network_error_handling(self, mock_client, mock_transport):
        """Test network error handling."""
        mock_transport.json_rpc_call.side_effect = NetworkError("Connection failed")
        
        with pytest.raises(NetworkError):
            await mock_client.search("res.partner", [])
```

### Model Testing

```python
# tests/unit/test_models.py
import pytest
from pydantic import ValidationError
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.models.fields import CharField, EmailField

class TestOdooModels:
    """Test suite for Odoo models."""
    
    def test_model_creation(self, sample_partner_data):
        """Test model instance creation."""
        partner = ResPartner(**sample_partner_data)
        
        assert partner.id == 1
        assert partner.name == "Test Company"
        assert partner.is_company is True
        assert partner.email == "test@example.com"
    
    def test_model_validation(self):
        """Test model field validation."""
        # Valid data
        partner = ResPartner(name="Valid Company", is_company=True)
        assert partner.name == "Valid Company"
        
        # Invalid data - missing required field
        with pytest.raises(ValidationError):
            ResPartner(is_company=True)  # Missing name
    
    def test_model_serialization(self, sample_partner_data):
        """Test model serialization."""
        partner = ResPartner(**sample_partner_data)
        
        # Test dict conversion
        partner_dict = partner.dict()
        assert partner_dict["name"] == "Test Company"
        assert partner_dict["is_company"] is True
        
        # Test JSON serialization
        partner_json = partner.json()
        assert "Test Company" in partner_json
        assert "true" in partner_json.lower()
    
    def test_custom_field_types(self):
        """Test custom field type validation."""
        # Test email field
        with pytest.raises(ValidationError):
            ResPartner(name="Test", email="invalid-email")
        
        # Valid email
        partner = ResPartner(name="Test", email="valid@example.com")
        assert partner.email == "valid@example.com"
    
    @pytest.mark.parametrize("field_name,valid_value,invalid_value", [
        ("name", "Valid Name", ""),
        ("email", "test@example.com", "invalid-email"),
        ("phone", "+1-555-0100", None),  # Phone can be None
    ])
    def test_field_validation_parametrized(self, field_name, valid_value, invalid_value):
        """Test field validation with parameters."""
        # Test valid value
        data = {"name": "Test Company"}
        if valid_value is not None:
            data[field_name] = valid_value
        
        partner = ResPartner(**data)
        if valid_value is not None:
            assert getattr(partner, field_name) == valid_value
        
        # Test invalid value (if applicable)
        if invalid_value is not None and field_name == "name":
            with pytest.raises(ValidationError):
                ResPartner(**{field_name: invalid_value})
```

### Query Builder Testing

```python
# tests/unit/test_query.py
import pytest
from unittest.mock import AsyncMock
from zenoo_rpc.query.builder import QueryBuilder
from zenoo_rpc.models.common import ResPartner

class TestQueryBuilder:
    """Test suite for QueryBuilder."""
    
    @pytest.fixture
    def query_builder(self, mock_client):
        """Create query builder for testing."""
        return QueryBuilder(ResPartner, mock_client)
    
    def test_filter_building(self, query_builder):
        """Test filter building."""
        # Simple filter
        query_builder.filter(name="Test")
        assert ("name", "=", "Test") in query_builder._domain
        
        # Multiple filters
        query_builder.filter(is_company=True, active=True)
        assert ("is_company", "=", True) in query_builder._domain
        assert ("active", "=", True) in query_builder._domain
    
    def test_complex_filters(self, query_builder):
        """Test complex filter expressions."""
        # ilike filter
        query_builder.filter(name__ilike="Test%")
        assert ("name", "ilike", "Test%") in query_builder._domain
        
        # in filter
        query_builder.filter(id__in=[1, 2, 3])
        assert ("id", "in", [1, 2, 3]) in query_builder._domain
        
        # gt filter
        query_builder.filter(id__gt=10)
        assert ("id", ">", 10) in query_builder._domain
    
    def test_limit_and_offset(self, query_builder):
        """Test limit and offset."""
        query_builder.limit(10).offset(20)
        
        assert query_builder._limit == 10
        assert query_builder._offset == 20
    
    def test_field_selection(self, query_builder):
        """Test field selection."""
        query_builder.only("name", "email")
        
        assert query_builder._fields == ["name", "email"]
    
    async def test_query_execution(self, query_builder, mock_client):
        """Test query execution."""
        mock_client.search_read.return_value = [
            {"id": 1, "name": "Test", "is_company": True}
        ]
        
        results = await query_builder.filter(is_company=True).all()
        
        assert len(results) == 1
        assert isinstance(results[0], ResPartner)
        assert results[0].name == "Test"
        
        mock_client.search_read.assert_called_once()
```

### Cache Testing

```python
# tests/unit/test_cache.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from zenoo_rpc.cache.backends import MemoryCache, RedisCache
from zenoo_rpc.cache.manager import CacheManager

class TestMemoryCache:
    """Test suite for MemoryCache."""
    
    @pytest.fixture
    def memory_cache(self):
        """Create memory cache for testing."""
        return MemoryCache(max_size=100, default_ttl=60)
    
    async def test_set_and_get(self, memory_cache):
        """Test basic set and get operations."""
        await memory_cache.set("key1", "value1")
        
        result = await memory_cache.get("key1")
        assert result == "value1"
    
    async def test_ttl_expiration(self, memory_cache):
        """Test TTL expiration."""
        await memory_cache.set("key1", "value1", ttl=1)
        
        # Should exist immediately
        result = await memory_cache.get("key1")
        assert result == "value1"
        
        # Should expire after TTL
        await asyncio.sleep(1.1)
        result = await memory_cache.get("key1")
        assert result is None
    
    async def test_lru_eviction(self, memory_cache):
        """Test LRU eviction."""
        # Fill cache to capacity
        for i in range(100):
            await memory_cache.set(f"key{i}", f"value{i}")
        
        # Add one more item (should evict oldest)
        await memory_cache.set("key100", "value100")
        
        # First item should be evicted
        result = await memory_cache.get("key0")
        assert result is None
        
        # Last item should exist
        result = await memory_cache.get("key100")
        assert result == "value100"

class TestCacheManager:
    """Test suite for CacheManager."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager for testing."""
        return CacheManager()
    
    async def test_backend_registration(self, cache_manager):
        """Test cache backend registration."""
        memory_cache = MemoryCache()
        await cache_manager.register_backend("memory", memory_cache)
        
        assert "memory" in cache_manager.backends
        assert cache_manager.backends["memory"] == memory_cache
    
    async def test_cache_operations(self, cache_manager):
        """Test cache operations through manager."""
        memory_cache = MemoryCache()
        await cache_manager.register_backend("memory", memory_cache)
        await cache_manager.set_default_backend("memory")
        
        # Test set and get
        await cache_manager.set("test_key", "test_value")
        result = await cache_manager.get("test_key")
        
        assert result == "test_value"
    
    async def test_cache_stats(self, cache_manager):
        """Test cache statistics."""
        memory_cache = MemoryCache()
        await cache_manager.register_backend("memory", memory_cache)
        await cache_manager.set_default_backend("memory")
        
        # Perform operations
        await cache_manager.set("key1", "value1")
        await cache_manager.get("key1")  # Hit
        await cache_manager.get("key2")  # Miss
        
        stats = await cache_manager.get_stats()
        
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
```

## Integration Testing

### Real Odoo Integration

```python
# tests/integration/test_odoo_integration.py
import pytest
import os
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

# Skip if no test server
pytestmark = pytest.mark.skipif(
    not os.getenv("ODOO_TEST_URL"),
    reason="No Odoo test server configured"
)

class TestOdooIntegration:
    """Integration tests with real Odoo server."""
    
    async def test_authentication(self, real_client):
        """Test authentication with real server."""
        assert real_client.uid is not None
        assert real_client.database is not None
        
        # Test version call
        version = await real_client.version()
        assert "server_version" in version
    
    async def test_basic_crud_operations(self, real_client):
        """Test basic CRUD operations."""
        # Create
        partner_data = {
            "name": f"Test Partner {asyncio.get_event_loop().time()}",
            "is_company": True,
            "email": "test@example.com"
        }
        
        partner_id = await real_client.create("res.partner", partner_data)
        assert isinstance(partner_id, int)
        
        # Read
        partner = await real_client.read("res.partner", [partner_id])
        assert len(partner) == 1
        assert partner[0]["name"] == partner_data["name"]
        
        # Update
        await real_client.write("res.partner", [partner_id], {"phone": "+1-555-0100"})
        
        updated_partner = await real_client.read("res.partner", [partner_id])
        assert updated_partner[0]["phone"] == "+1-555-0100"
        
        # Delete
        await real_client.unlink("res.partner", [partner_id])
        
        # Verify deletion
        deleted_partner = await real_client.read("res.partner", [partner_id])
        assert len(deleted_partner) == 0
    
    async def test_model_query_builder(self, real_client):
        """Test model query builder with real data."""
        partners = await (
            real_client.model(ResPartner)
            .filter(is_company=True)
            .limit(5)
            .only("id", "name", "email")
            .all()
        )
        
        assert isinstance(partners, list)
        assert len(partners) <= 5
        assert all(isinstance(p, ResPartner) for p in partners)
        assert all(hasattr(p, "name") for p in partners)
    
    async def test_batch_operations(self, real_client):
        """Test batch operations with real server."""
        # Prepare test data
        partner_data = [
            {"name": f"Batch Partner {i}", "is_company": True}
            for i in range(10)
        ]
        
        # Batch create
        async with real_client.batch_context() as batch:
            batch.create("res.partner", partner_data)
            results = await batch.execute()
        
        created_ids = results[0].result
        assert len(created_ids) == 10
        assert all(isinstance(id_, int) for id_ in created_ids)
        
        # Cleanup
        await real_client.unlink("res.partner", created_ids)
```

## Performance Testing

### Benchmark Tests

```python
# tests/performance/test_benchmarks.py
import pytest
import time
import asyncio
from zenoo_rpc import ZenooClient

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.mark.performance
    async def test_search_performance(self, real_client):
        """Benchmark search operations."""
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            await real_client.search("res.partner", [], limit=10)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        print(f"Search performance: {avg_time:.3f}s per operation")
        assert avg_time < 0.1  # Should be under 100ms per search
    
    @pytest.mark.performance
    async def test_concurrent_operations(self, real_client):
        """Test concurrent operation performance."""
        async def search_operation():
            return await real_client.search("res.partner", [], limit=5)
        
        # Run 10 concurrent searches
        start_time = time.time()
        tasks = [search_operation() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        print(f"Concurrent operations: {total_time:.3f}s for 10 operations")
        
        assert len(results) == 10
        assert total_time < 2.0  # Should complete within 2 seconds
    
    @pytest.mark.performance
    async def test_cache_performance(self, real_client):
        """Test cache performance impact."""
        # Setup cache
        await real_client.setup_cache_manager(backend="memory")
        
        # First query (no cache)
        start_time = time.time()
        result1 = await (
            real_client.model(ResPartner)
            .filter(is_company=True)
            .limit(10)
            .cache(ttl=300)
            .all()
        )
        first_query_time = time.time() - start_time
        
        # Second query (cached)
        start_time = time.time()
        result2 = await (
            real_client.model(ResPartner)
            .filter(is_company=True)
            .limit(10)
            .cache(ttl=300)
            .all()
        )
        cached_query_time = time.time() - start_time
        
        print(f"First query: {first_query_time:.3f}s")
        print(f"Cached query: {cached_query_time:.3f}s")
        print(f"Cache speedup: {first_query_time / cached_query_time:.1f}x")
        
        assert len(result1) == len(result2)
        assert cached_query_time < first_query_time  # Cache should be faster
```

### Memory Usage Tests

```python
# tests/performance/test_memory_usage.py
import pytest
import tracemalloc
import gc
from zenoo_rpc import ZenooClient

class TestMemoryUsage:
    """Memory usage tests."""
    
    @pytest.mark.performance
    async def test_memory_leak_detection(self, real_client):
        """Test for memory leaks in repeated operations."""
        tracemalloc.start()
        
        # Take initial snapshot
        snapshot1 = tracemalloc.take_snapshot()
        
        # Perform many operations
        for _ in range(100):
            await real_client.search("res.partner", [], limit=1)
        
        # Force garbage collection
        gc.collect()
        
        # Take final snapshot
        snapshot2 = tracemalloc.take_snapshot()
        
        # Compare snapshots
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        # Check for significant memory growth
        total_growth = sum(stat.size_diff for stat in top_stats)
        print(f"Total memory growth: {total_growth / 1024 / 1024:.2f} MB")
        
        # Should not grow more than 10MB for 100 operations
        assert total_growth < 10 * 1024 * 1024
    
    @pytest.mark.performance
    async def test_connection_pool_memory(self):
        """Test connection pool memory usage."""
        tracemalloc.start()
        
        # Create multiple clients
        clients = []
        for _ in range(10):
            client = ZenooClient("localhost", port=8069)
            clients.append(client)
        
        snapshot1 = tracemalloc.take_snapshot()
        
        # Close all clients
        for client in clients:
            await client.close()
        
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()
        
        # Memory should be released
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_change = sum(stat.size_diff for stat in top_stats)
        
        print(f"Memory change after cleanup: {total_change / 1024:.2f} KB")
        
        # Should release most memory
        assert abs(total_change) < 1024 * 1024  # Less than 1MB difference
```

## Test Utilities

### Custom Assertions

```python
# tests/utils/assertions.py
import pytest
from typing import Any, List, Dict

def assert_valid_partner(partner_data: Dict[str, Any]):
    """Assert that partner data is valid."""
    assert "id" in partner_data
    assert "name" in partner_data
    assert isinstance(partner_data["id"], int)
    assert isinstance(partner_data["name"], str)
    assert len(partner_data["name"]) > 0

def assert_rpc_call_made(mock_transport, service: str, method: str, *args):
    """Assert that specific RPC call was made."""
    mock_transport.json_rpc_call.assert_called_with(service, method, list(args))

def assert_performance_threshold(duration: float, threshold: float, operation: str):
    """Assert that operation completed within performance threshold."""
    assert duration < threshold, f"{operation} took {duration:.3f}s, expected < {threshold}s"

class AsyncContextManager:
    """Helper for testing async context managers."""
    
    def __init__(self, async_cm):
        self.async_cm = async_cm
        self.result = None
    
    async def __aenter__(self):
        self.result = await self.async_cm.__aenter__()
        return self.result
    
    async def __aexit__(self, *args):
        return await self.async_cm.__aexit__(*args)
```

### Test Data Generators

```python
# tests/fixtures/sample_data.py
import random
import string
from typing import Dict, List, Any

def generate_partner_data(count: int = 1) -> List[Dict[str, Any]]:
    """Generate sample partner data for testing."""
    partners = []
    
    for i in range(count):
        partner = {
            "name": f"Test Company {i}",
            "is_company": random.choice([True, False]),
            "email": f"test{i}@example.com",
            "phone": f"+1-555-{random.randint(1000, 9999)}",
            "active": True
        }
        
        if partner["is_company"]:
            partner["website"] = f"https://company{i}.example.com"
        
        partners.append(partner)
    
    return partners

def generate_random_string(length: int = 10) -> str:
    """Generate random string for testing."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_large_dataset(size: int = 1000) -> List[Dict[str, Any]]:
    """Generate large dataset for performance testing."""
    return [
        {
            "name": f"Partner {i}",
            "ref": generate_random_string(8),
            "is_company": i % 3 == 0,
            "active": True
        }
        for i in range(size)
    ]
```

## Running Tests

### Test Commands

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only
pytest tests/performance/             # Performance tests only

# Run with coverage
pytest --cov=zenoo_rpc --cov-report=html --cov-report=term-missing

# Run with performance markers
pytest -m performance

# Run tests in parallel
pytest -n auto

# Run with verbose output
pytest -v -s

# Run specific test file
pytest tests/unit/test_client.py

# Run specific test method
pytest tests/unit/test_client.py::TestZenooClient::test_login_success
```

### Environment Variables for Testing

```bash
# Integration test configuration
export ODOO_TEST_URL="http://localhost:8069"
export ODOO_TEST_DB="demo"
export ODOO_TEST_USER="admin"
export ODOO_TEST_PASSWORD="admin"

# Performance test configuration
export PERFORMANCE_TESTS=true
export BENCHMARK_ITERATIONS=100

# Cache test configuration
export REDIS_TEST_URL="redis://localhost:6379/1"
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev,redis]"
    
    - name: Run tests
      run: |
        pytest --cov=zenoo_rpc --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Best Practices

### 1. Test Organization
- Keep tests focused and independent
- Use descriptive test names
- Group related tests in classes
- Use fixtures for common setup

### 2. Mocking Strategy
- Mock external dependencies (HTTP calls, databases)
- Use real objects for unit tests when possible
- Mock at the right level (transport, not client methods)

### 3. Performance Testing
- Set realistic performance thresholds
- Test with representative data sizes
- Monitor memory usage and leaks
- Use profiling for optimization

### 4. Integration Testing
- Test with real Odoo instances when possible
- Use test databases for integration tests
- Clean up test data after tests
- Test error conditions and edge cases

## Next Steps

- Review [Documentation Guide](documentation.md) for documentation testing
- Check [Development Guide](development.md) for development setup
- Explore [Release Process](release.md) for release testing
- Learn about CI/CD pipeline configuration
