# Testing Strategies

This tutorial covers comprehensive testing strategies for applications using Zenoo RPC, including unit tests, integration tests, mocking, and test data management.

## Prerequisites

- Basic understanding of Python testing frameworks (pytest, unittest)
- Familiarity with async/await testing patterns
- Knowledge of Zenoo RPC client usage

## Testing Framework Setup

### Installing Test Dependencies

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-mock pytest-cov
pip install factory-boy faker  # For test data generation
pip install responses httpx-mock  # For HTTP mocking
```

### Basic Test Configuration

```python
# conftest.py
import pytest
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_client():
    """Create a mock Zenoo RPC client for testing."""
    client = ZenooClient("http://test.odoo.com")
    # Mock authentication
    client._session.uid = 1
    client._session.database = "test_db"
    client._session.password = "test_password"
    return client

@pytest.fixture
async def real_client():
    """Create a real client for integration tests."""
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("test_db", "admin", "admin")
        yield client

@pytest.fixture
def sample_partner_data():
    """Sample partner data for testing."""
    return {
        "name": "Test Company",
        "email": "test@company.com",
        "is_company": True,
        "phone": "+1-555-0123"
    }
```

## Unit Testing

### Testing Client Operations

```python
# test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import AuthenticationError, ValidationError

class TestZenooClient:
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with different parameters."""
        # Test with full URL
        client = ZenooClient("https://demo.odoo.com")
        assert client.host == "demo.odoo.com"
        assert client.port == 443
        assert client.protocol == "https"
        
        # Test with host and port
        client = ZenooClient("localhost", port=8069, protocol="http")
        assert client.host == "localhost"
        assert client.port == 8069
        assert client.protocol == "http"
    
    @pytest.mark.asyncio
    async def test_authentication_success(self, mock_client):
        """Test successful authentication."""
        with patch.object(mock_client._transport, 'json_rpc_call') as mock_call:
            mock_call.return_value = {"result": {"uid": 1, "session_id": "test_session"}}
            
            result = await mock_client.login("test_db", "admin", "admin")
            
            assert result is True
            assert mock_client.is_authenticated is True
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, mock_client):
        """Test authentication failure."""
        with patch.object(mock_client._transport, 'json_rpc_call') as mock_call:
            mock_call.return_value = {"result": False}
            
            with pytest.raises(AuthenticationError):
                await mock_client.login("test_db", "admin", "wrong_password")
    
    @pytest.mark.asyncio
    async def test_create_operation(self, mock_client, sample_partner_data):
        """Test record creation."""
        with patch.object(mock_client, 'execute_kw') as mock_execute:
            mock_execute.return_value = 123
            
            partner_id = await mock_client.create("res.partner", sample_partner_data)
            
            assert partner_id == 123
            mock_execute.assert_called_once_with(
                "res.partner", "create", [sample_partner_data], context=None
            )
    
    @pytest.mark.asyncio
    async def test_search_operation(self, mock_client):
        """Test search operation."""
        with patch.object(mock_client, 'execute_kw') as mock_execute:
            mock_execute.return_value = [1, 2, 3]
            
            result = await mock_client.search(
                "res.partner", 
                [("is_company", "=", True)], 
                limit=10
            )
            
            assert result == [1, 2, 3]
            mock_execute.assert_called_once()
```

### Testing Model Operations

```python
# test_models.py
import pytest
from unittest.mock import AsyncMock, patch
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.query.builder import QueryBuilder

class TestModelOperations:
    
    @pytest.mark.asyncio
    async def test_model_query_builder(self, mock_client):
        """Test model query builder creation."""
        builder = mock_client.model(ResPartner)
        
        assert isinstance(builder, QueryBuilder)
        assert builder.model_class == ResPartner
        assert builder.client == mock_client
    
    @pytest.mark.asyncio
    async def test_filter_query(self, mock_client):
        """Test query filtering."""
        with patch.object(mock_client, 'search_read') as mock_search_read:
            mock_search_read.return_value = [
                {"id": 1, "name": "Test Company", "is_company": True}
            ]
            
            partners = await mock_client.model(ResPartner).filter(
                is_company=True
            ).all()
            
            assert len(partners) == 1
            assert partners[0].name == "Test Company"
            mock_search_read.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_model_validation(self):
        """Test model validation."""
        # Valid data
        partner = ResPartner(
            id=1,
            name="Test Company",
            email="test@company.com",
            is_company=True
        )
        assert partner.name == "Test Company"
        assert partner.is_customer is False  # Default computed property
        
        # Invalid data should raise validation error
        with pytest.raises(ValidationError):
            ResPartner(
                id=1,
                name="",  # Empty name should fail validation
                email="invalid-email"  # Invalid email format
            )
```

### Testing Query Builder

```python
# test_query_builder.py
import pytest
from unittest.mock import AsyncMock, patch
from zenoo_rpc.models.common import ResPartner
from zenoo_rpc.query.filters import Q

class TestQueryBuilder:
    
    @pytest.mark.asyncio
    async def test_simple_filter(self, mock_client):
        """Test simple filtering."""
        builder = mock_client.model(ResPartner)
        queryset = builder.filter(is_company=True)
        
        # Check that domain is built correctly
        expected_domain = [("is_company", "=", True)]
        assert queryset._domain == expected_domain
    
    @pytest.mark.asyncio
    async def test_complex_filter_with_q_objects(self, mock_client):
        """Test complex filtering with Q objects."""
        builder = mock_client.model(ResPartner)
        queryset = builder.filter(
            Q(name__ilike="acme%") | Q(name__ilike="corp%")
        )
        
        # Verify Q object is processed correctly
        assert len(queryset._domain) > 0
    
    @pytest.mark.asyncio
    async def test_chaining_operations(self, mock_client):
        """Test method chaining."""
        builder = mock_client.model(ResPartner)
        queryset = builder.filter(
            is_company=True
        ).limit(10).offset(20).order_by("name")
        
        assert queryset._limit == 10
        assert queryset._offset == 20
        assert queryset._order == "name"
    
    @pytest.mark.asyncio
    async def test_field_selection(self, mock_client):
        """Test field selection."""
        builder = mock_client.model(ResPartner)
        queryset = builder.only("id", "name", "email")
        
        assert queryset._fields == ["id", "name", "email"]
```

## Integration Testing

### Database Integration Tests

```python
# test_integration.py
import pytest
from zenoo_rpc.models.common import ResPartner

class TestDatabaseIntegration:
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_crud_cycle(self, real_client):
        """Test complete CRUD cycle with real database."""
        # Create
        partner_data = {
            "name": "Integration Test Company",
            "email": "integration@test.com",
            "is_company": True
        }
        
        partner_id = await real_client.create("res.partner", partner_data)
        assert partner_id > 0
        
        # Read
        partner_records = await real_client.read(
            "res.partner", [partner_id], ["name", "email", "is_company"]
        )
        assert len(partner_records) == 1
        assert partner_records[0]["name"] == "Integration Test Company"
        
        # Update
        await real_client.write(
            "res.partner", [partner_id], {"email": "updated@test.com"}
        )
        
        updated_records = await real_client.read(
            "res.partner", [partner_id], ["email"]
        )
        assert updated_records[0]["email"] == "updated@test.com"
        
        # Delete
        success = await real_client.unlink("res.partner", [partner_id])
        assert success is True
        
        # Verify deletion
        deleted_records = await real_client.read(
            "res.partner", [partner_id], ["name"]
        )
        assert len(deleted_records) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_relationship_queries(self, real_client):
        """Test relationship queries with real data."""
        partners = await real_client.model(ResPartner).filter(
            is_company=True,
            country_id__isnull=False
        ).prefetch_related("country_id").limit(5).all()
        
        assert len(partners) > 0
        
        for partner in partners:
            country = await partner.country_id
            assert country is not None
            assert hasattr(country, 'name')
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_transaction_rollback(self, real_client):
        """Test transaction rollback functionality."""
        initial_count = await real_client.search_count("res.partner", [])
        
        try:
            async with real_client.transaction_manager.transaction():
                # Create a partner
                await real_client.create("res.partner", {
                    "name": "Transaction Test",
                    "email": "transaction@test.com"
                })
                
                # Force an error to trigger rollback
                raise Exception("Intentional error for testing")
                
        except Exception:
            pass  # Expected
        
        # Verify rollback - count should be unchanged
        final_count = await real_client.search_count("res.partner", [])
        assert final_count == initial_count
```

## Mocking and Test Doubles

### HTTP Response Mocking

```python
# test_mocking.py
import pytest
import httpx
from unittest.mock import patch
from zenoo_rpc import ZenooClient

class TestMocking:
    
    @pytest.mark.asyncio
    async def test_http_response_mocking(self):
        """Test HTTP response mocking."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "uid": 1,
                "session_id": "test_session"
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.status_code = 200
            
            client = ZenooClient("http://test.odoo.com")
            result = await client.login("test_db", "admin", "admin")
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_response_mocking(self):
        """Test error response mocking."""
        mock_error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {"name": "ValidationError"}
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_error_response
            mock_post.return_value.status_code = 200
            
            client = ZenooClient("http://test.odoo.com")
            
            with pytest.raises(ValidationError):
                await client.create("res.partner", {"invalid": "data"})
```

### Service Layer Mocking

```python
# test_service_mocking.py
import pytest
from unittest.mock import AsyncMock, patch

class PartnerService:
    """Example service layer for testing."""
    
    def __init__(self, client):
        self.client = client
    
    async def create_company(self, name, email):
        """Create a new company."""
        return await self.client.create("res.partner", {
            "name": name,
            "email": email,
            "is_company": True
        })
    
    async def get_companies_by_country(self, country_name):
        """Get companies by country name."""
        return await self.client.model(ResPartner).filter(
            is_company=True,
            country_id__name=country_name
        ).all()

class TestPartnerService:
    
    @pytest.mark.asyncio
    async def test_create_company(self, mock_client):
        """Test company creation through service layer."""
        service = PartnerService(mock_client)
        
        with patch.object(mock_client, 'create') as mock_create:
            mock_create.return_value = 123
            
            result = await service.create_company("Test Corp", "test@corp.com")
            
            assert result == 123
            mock_create.assert_called_once_with("res.partner", {
                "name": "Test Corp",
                "email": "test@corp.com",
                "is_company": True
            })
    
    @pytest.mark.asyncio
    async def test_get_companies_by_country(self, mock_client):
        """Test getting companies by country."""
        service = PartnerService(mock_client)
        
        # Mock the model query chain
        mock_builder = AsyncMock()
        mock_queryset = AsyncMock()
        mock_queryset.all.return_value = [
            ResPartner(id=1, name="US Company", is_company=True)
        ]
        mock_builder.filter.return_value = mock_queryset
        
        with patch.object(mock_client, 'model', return_value=mock_builder):
            companies = await service.get_companies_by_country("United States")
            
            assert len(companies) == 1
            assert companies[0].name == "US Company"
```

## Test Data Management

### Factory Pattern for Test Data

```python
# test_factories.py
import factory
from faker import Faker
from zenoo_rpc.models.common import ResPartner

fake = Faker()

class PartnerFactory(factory.Factory):
    """Factory for creating test partner data."""
    
    class Meta:
        model = dict
    
    name = factory.LazyFunction(fake.company)
    email = factory.LazyFunction(fake.email)
    phone = factory.LazyFunction(fake.phone_number)
    is_company = True
    street = factory.LazyFunction(fake.street_address)
    city = factory.LazyFunction(fake.city)
    zip = factory.LazyFunction(fake.zipcode)
    website = factory.LazyFunction(fake.url)

class ContactFactory(PartnerFactory):
    """Factory for creating test contact data."""
    
    name = factory.LazyFunction(fake.name)
    is_company = False
    function = factory.LazyFunction(fake.job)

# Usage in tests
class TestWithFactories:
    
    @pytest.mark.asyncio
    async def test_with_factory_data(self, mock_client):
        """Test using factory-generated data."""
        # Generate test data
        company_data = PartnerFactory()
        contact_data = ContactFactory()
        
        with patch.object(mock_client, 'create') as mock_create:
            mock_create.side_effect = [1, 2]  # Return different IDs
            
            company_id = await mock_client.create("res.partner", company_data)
            contact_id = await mock_client.create("res.partner", contact_data)
            
            assert company_id == 1
            assert contact_id == 2
            assert mock_create.call_count == 2
```

### Database Fixtures and Cleanup

```python
# test_fixtures.py
import pytest

@pytest.fixture
async def test_partner(real_client):
    """Create a test partner and clean up after test."""
    partner_data = {
        "name": "Test Partner for Cleanup",
        "email": "cleanup@test.com",
        "is_company": True
    }
    
    partner_id = await real_client.create("res.partner", partner_data)
    
    yield partner_id
    
    # Cleanup
    try:
        await real_client.unlink("res.partner", [partner_id])
    except Exception:
        pass  # Partner might already be deleted

@pytest.fixture
async def test_partners_batch(real_client):
    """Create multiple test partners."""
    partner_ids = []
    
    for i in range(3):
        partner_data = {
            "name": f"Batch Test Partner {i}",
            "email": f"batch{i}@test.com",
            "is_company": True
        }
        partner_id = await real_client.create("res.partner", partner_data)
        partner_ids.append(partner_id)
    
    yield partner_ids
    
    # Cleanup
    try:
        await real_client.unlink("res.partner", partner_ids)
    except Exception:
        pass

class TestWithFixtures:
    
    @pytest.mark.asyncio
    async def test_with_single_partner(self, real_client, test_partner):
        """Test with a single test partner."""
        partner_records = await real_client.read(
            "res.partner", [test_partner], ["name"]
        )
        assert len(partner_records) == 1
        assert "Test Partner for Cleanup" in partner_records[0]["name"]
    
    @pytest.mark.asyncio
    async def test_with_multiple_partners(self, real_client, test_partners_batch):
        """Test with multiple test partners."""
        partner_records = await real_client.read(
            "res.partner", test_partners_batch, ["name"]
        )
        assert len(partner_records) == 3
```

## Performance Testing

### Load Testing

```python
# test_performance.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_requests(self, real_client):
        """Test concurrent request performance."""
        async def search_partners():
            return await real_client.search(
                "res.partner", [("is_company", "=", True)], limit=10
            )
        
        start_time = time.time()
        
        # Run 10 concurrent searches
        tasks = [search_partners() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 10
        assert duration < 5.0  # Should complete within 5 seconds
        print(f"10 concurrent searches completed in {duration:.2f} seconds")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_bulk_operations_performance(self, real_client):
        """Test bulk operations performance."""
        # Create test data
        partners_data = [
            {
                "name": f"Bulk Test Partner {i}",
                "email": f"bulk{i}@test.com",
                "is_company": True
            }
            for i in range(100)
        ]
        
        start_time = time.time()
        
        # Use batch manager for bulk creation
        created_ids = await real_client.batch_manager.bulk_create(
            "res.partner", partners_data
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(created_ids) == 100
        assert duration < 10.0  # Should complete within 10 seconds
        
        # Cleanup
        await real_client.unlink("res.partner", created_ids)
        
        print(f"Bulk creation of 100 records completed in {duration:.2f} seconds")
```

## Running Tests

### Pytest Configuration

```ini
# pytest.ini
[tool:pytest]
asyncio_mode = auto
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
    performance: marks tests as performance tests (deselect with '-m "not performance"')
    slow: marks tests as slow running tests
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html
```

### Running Different Test Suites

```bash
# Run all tests
pytest

# Run only unit tests (exclude integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run with coverage
pytest --cov=src --cov-report=html

# Run performance tests
pytest -m performance

# Run specific test file
pytest tests/test_client.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto  # Requires pytest-xdist
```

## Best Practices

### 1. Test Organization

```python
# ✅ Good: Organize tests by functionality
tests/
├── unit/
│   ├── test_client.py
│   ├── test_models.py
│   └── test_query_builder.py
├── integration/
│   ├── test_database.py
│   └── test_transactions.py
├── performance/
│   └── test_load.py
└── conftest.py
```

### 2. Use Appropriate Test Types

```python
# ✅ Good: Unit test for business logic
async def test_partner_validation():
    with pytest.raises(ValidationError):
        ResPartner(name="", email="invalid")

# ✅ Good: Integration test for database operations
@pytest.mark.integration
async def test_database_crud(real_client):
    partner_id = await real_client.create("res.partner", data)
    # ... test with real database
```

### 3. Mock External Dependencies

```python
# ✅ Good: Mock HTTP calls
with patch('httpx.AsyncClient.post') as mock_post:
    mock_post.return_value.json.return_value = mock_response
    result = await client.login("db", "user", "pass")

# ❌ Avoid: Testing against production systems
async def test_production_data():
    client = ZenooClient("https://production.odoo.com")  # Don't do this
```

### 4. Clean Up Test Data

```python
# ✅ Good: Use fixtures for cleanup
@pytest.fixture
async def test_partner(real_client):
    partner_id = await real_client.create("res.partner", data)
    yield partner_id
    await real_client.unlink("res.partner", [partner_id])  # Cleanup
```

## Next Steps

- Learn about [Production Deployment](production-deployment.md) for testing in production environments
- Explore [Performance Optimization](performance-optimization.md) for performance testing strategies
- Check [Error Handling](../user-guide/error-handling.md) for testing error scenarios
