# Development Guide

Comprehensive guide for contributing to Zenoo RPC development, including setup, coding standards, testing, and contribution workflow.

## Development Setup

### Prerequisites

- **Python 3.8+** (3.11+ recommended)
- **Git** for version control
- **Docker** (optional, for testing with Odoo)
- **Redis** (optional, for cache testing)

### Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/tuanle96/zenoo-rpc.git
cd zenoo-rpc

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -e ".[dev,redis]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify installation
python -m pytest tests/ -v
```

### Development Dependencies

```toml
# pyproject.toml - Development dependencies
[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    
    # Code quality
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
    
    # Documentation
    "mkdocs>=1.4.0",
    "mkdocs-material>=9.0.0",
    "mkdocstrings[python]>=0.20.0",
    
    # Development tools
    "ipython>=8.0.0",
    "jupyter>=1.0.0",
    "httpx[cli]>=0.24.0"
]

redis = [
    "redis>=4.5.0",
    "hiredis>=2.2.0"
]
```

## Project Structure

```
zenoo-rpc/
├── src/zenoo_rpc/           # Main package
│   ├── __init__.py
│   ├── client.py            # Main client
│   ├── models/              # Model definitions
│   │   ├── __init__.py
│   │   ├── base.py          # Base model classes
│   │   ├── fields.py        # Field types
│   │   ├── common.py        # Common Odoo models
│   │   └── registry.py      # Model registry
│   ├── query/               # Query building
│   │   ├── __init__.py
│   │   ├── builder.py       # Query builder
│   │   ├── filters.py       # Filter expressions
│   │   └── expressions.py   # Field expressions
│   ├── cache/               # Caching system
│   │   ├── __init__.py
│   │   ├── manager.py       # Cache manager
│   │   ├── backends.py      # Cache backends
│   │   └── strategies.py    # Cache strategies
│   ├── transport/           # Transport layer
│   │   ├── __init__.py
│   │   ├── httpx_transport.py
│   │   ├── session.py       # Session management
│   │   └── pool.py          # Connection pooling
│   ├── batch/               # Batch operations
│   │   ├── __init__.py
│   │   ├── manager.py       # Batch manager
│   │   ├── operations.py    # Batch operations
│   │   └── executor.py      # Batch executor
│   ├── retry/               # Retry mechanisms
│   │   ├── __init__.py
│   │   ├── decorators.py    # Retry decorators
│   │   ├── strategies.py    # Retry strategies
│   │   └── policies.py      # Retry policies
│   ├── transaction/         # Transaction management
│   │   ├── __init__.py
│   │   ├── manager.py       # Transaction manager
│   │   └── context.py       # Transaction context
│   └── exceptions.py        # Custom exceptions
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── fixtures/            # Test fixtures
├── docs/                    # Documentation
├── examples/                # Example scripts
├── scripts/                 # Development scripts
├── pyproject.toml           # Project configuration
├── README.md
└── CHANGELOG.md
```

## Coding Standards

### Code Style

We use **Black** for code formatting and **isort** for import sorting:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check formatting
black --check src/ tests/
isort --check-only src/ tests/
```

### Type Hints

All code must include comprehensive type hints:

```python
from typing import List, Optional, Dict, Any, Union, TypeVar, Generic
from typing_extensions import Protocol

# ✅ Good: Complete type hints
async def search_records(
    client: ZenooClient,
    model: str,
    domain: List[Union[str, tuple]],
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Search records with proper type hints."""
    return await client.search_read(model, domain, limit=limit)

# ✅ Good: Generic types
T = TypeVar('T', bound=OdooModel)

class QueryBuilder(Generic[T]):
    def __init__(self, model_class: Type[T], client: ZenooClient):
        self.model_class = model_class
        self.client = client
    
    async def all(self) -> List[T]:
        """Return all matching records."""
        # Implementation
        pass

# ✅ Good: Protocol for interfaces
class CacheBackend(Protocol):
    async def get(self, key: str) -> Optional[Any]: ...
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool: ...
```

### Documentation Standards

All public APIs must have comprehensive docstrings:

```python
async def create_partner(
    client: ZenooClient,
    partner_data: Dict[str, Any],
    validate: bool = True
) -> Dict[str, Any]:
    """Create a new partner record.
    
    Args:
        client: Authenticated Zenoo RPC client
        partner_data: Partner data dictionary with required fields
        validate: Whether to validate data before creation
    
    Returns:
        Created partner record with ID and other fields
    
    Raises:
        ValidationError: If partner data is invalid
        AuthenticationError: If client is not authenticated
        NetworkError: If network communication fails
    
    Example:
        >>> async with ZenooClient("localhost") as client:
        ...     await client.login("demo", "admin", "admin")
        ...     partner = await create_partner(client, {
        ...         "name": "Test Company",
        ...         "is_company": True,
        ...         "email": "info@test.com"
        ...     })
        ...     print(f"Created partner ID: {partner['id']}")
    """
    if validate:
        _validate_partner_data(partner_data)
    
    return await client.create("res.partner", partner_data)
```

### Error Handling

Implement comprehensive error handling with custom exceptions:

```python
from zenoo_rpc.exceptions import (
    ZenooRPCError,
    AuthenticationError,
    ValidationError,
    NetworkError
)

async def robust_operation(client: ZenooClient) -> Any:
    """Example of proper error handling."""
    try:
        result = await client.search("res.partner", [])
        return result
    
    except AuthenticationError:
        # Re-raise authentication errors
        raise
    
    except NetworkError as e:
        # Log network errors and provide context
        logger.error(f"Network error in robust_operation: {e}")
        raise NetworkError(f"Failed to connect to Odoo server: {e}") from e
    
    except ValidationError as e:
        # Handle validation errors gracefully
        logger.warning(f"Validation error: {e}")
        return []  # Return empty result or default
    
    except Exception as e:
        # Wrap unexpected errors
        logger.error(f"Unexpected error in robust_operation: {e}")
        raise ZenooRPCError(f"Operation failed: {e}") from e
```

## Testing Guidelines

### Test Structure

```python
# tests/unit/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import AuthenticationError

class TestZenooClient:
    """Test suite for ZenooClient."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        client = ZenooClient("localhost", port=8069)
        yield client
        await client.close()
    
    @pytest.fixture
    def mock_transport(self):
        """Mock transport for testing."""
        transport = AsyncMock()
        transport.json_rpc_call.return_value = {"result": "success"}
        return transport
    
    async def test_login_success(self, client, mock_transport):
        """Test successful login."""
        client.transport = mock_transport
        mock_transport.json_rpc_call.return_value = 1  # User ID
        
        await client.login("demo", "admin", "admin")
        
        assert client.uid == 1
        assert client.database == "demo"
        mock_transport.json_rpc_call.assert_called_once()
    
    async def test_login_failure(self, client, mock_transport):
        """Test login failure."""
        client.transport = mock_transport
        mock_transport.json_rpc_call.return_value = False
        
        with pytest.raises(AuthenticationError):
            await client.login("demo", "admin", "wrong_password")
    
    @pytest.mark.parametrize("domain,expected", [
        ([], []),
        ([("name", "=", "Test")], [("name", "=", "Test")]),
        ([("id", "in", [1, 2, 3])], [("id", "in", [1, 2, 3])]),
    ])
    async def test_search_domains(self, client, mock_transport, domain, expected):
        """Test search with different domains."""
        client.transport = mock_transport
        client.uid = 1
        client.database = "demo"
        client.password = "admin"
        
        mock_transport.json_rpc_call.return_value = [1, 2, 3]
        
        result = await client.search("res.partner", domain)
        
        assert result == [1, 2, 3]
        # Verify the call was made with correct parameters
        call_args = mock_transport.json_rpc_call.call_args
        assert call_args[0][0] == "object"  # service
        assert call_args[0][1] == "execute_kw"  # method
```

### Integration Tests

```python
# tests/integration/test_real_odoo.py
import pytest
import os
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

# Skip integration tests if no Odoo server available
pytestmark = pytest.mark.skipif(
    not os.getenv("ODOO_TEST_URL"),
    reason="No Odoo test server configured"
)

class TestRealOdoo:
    """Integration tests with real Odoo server."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated client for testing."""
        url = os.getenv("ODOO_TEST_URL", "http://localhost:8069")
        database = os.getenv("ODOO_TEST_DB", "demo")
        username = os.getenv("ODOO_TEST_USER", "admin")
        password = os.getenv("ODOO_TEST_PASSWORD", "admin")
        
        client = ZenooClient(url)
        await client.login(database, username, password)
        
        yield client
        
        await client.close()
    
    async def test_search_partners(self, authenticated_client):
        """Test searching for partners."""
        partners = await authenticated_client.search("res.partner", [], limit=5)
        
        assert isinstance(partners, list)
        assert len(partners) <= 5
        assert all(isinstance(p, int) for p in partners)
    
    async def test_model_query_builder(self, authenticated_client):
        """Test model query builder."""
        partners = await (
            authenticated_client.model(ResPartner)
            .filter(is_company=True)
            .limit(3)
            .all()
        )
        
        assert isinstance(partners, list)
        assert len(partners) <= 3
        assert all(isinstance(p, ResPartner) for p in partners)
        assert all(p.is_company for p in partners)
```

### Test Configuration

```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock
from zenoo_rpc import ZenooClient

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_client():
    """Create mock client for testing."""
    client = AsyncMock(spec=ZenooClient)
    client.uid = 1
    client.database = "test_db"
    client.password = "test_password"
    
    # Mock common methods
    client.search.return_value = [1, 2, 3]
    client.read.return_value = [{"id": 1, "name": "Test"}]
    client.create.return_value = {"id": 1, "name": "Test"}
    
    return client

@pytest.fixture
def sample_partner_data():
    """Sample partner data for testing."""
    return {
        "name": "Test Company",
        "is_company": True,
        "email": "test@example.com",
        "phone": "+1-555-0100"
    }
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=zenoo_rpc --cov-report=html

# Run specific test file
pytest tests/unit/test_client.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/ -m integration

# Run tests in parallel
pytest -n auto
```

## Development Workflow

### Branch Strategy

```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Make changes and commit
git add .
git commit -m "feat: add new feature"

# 3. Push branch
git push origin feature/new-feature

# 4. Create pull request
# Use GitHub web interface or CLI
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```bash
git commit -m "feat(cache): add Redis backend support"
git commit -m "fix(client): handle connection timeout properly"
git commit -m "docs(api): update query builder documentation"
git commit -m "test(batch): add integration tests for batch operations"
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Development Scripts

```bash
# scripts/dev-setup.sh
#!/bin/bash
set -e

echo "Setting up development environment..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev,redis]"

# Install pre-commit hooks
pre-commit install

# Run initial tests
pytest tests/unit/ -v

echo "Development environment ready!"
```

```bash
# scripts/test.sh
#!/bin/bash
set -e

echo "Running test suite..."

# Code formatting
black --check src/ tests/
isort --check-only src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/

# Tests with coverage
pytest --cov=zenoo_rpc --cov-report=term-missing --cov-report=html

echo "All tests passed!"
```

## Performance Considerations

### Profiling

```python
# scripts/profile.py
import asyncio
import cProfile
import pstats
from zenoo_rpc import ZenooClient

async def profile_operations():
    """Profile common operations."""
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Profile search operations
        for _ in range(100):
            await client.search("res.partner", [], limit=10)

def run_profiling():
    """Run profiling with cProfile."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    asyncio.run(profile_operations())
    
    profiler.disable()
    
    # Save and display results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

if __name__ == "__main__":
    run_profiling()
```

### Memory Testing

```python
# scripts/memory_test.py
import asyncio
import tracemalloc
from zenoo_rpc import ZenooClient

async def memory_test():
    """Test memory usage patterns."""
    tracemalloc.start()
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Take initial snapshot
        snapshot1 = tracemalloc.take_snapshot()
        
        # Perform operations
        for i in range(1000):
            await client.search("res.partner", [], limit=1)
        
        # Take final snapshot
        snapshot2 = tracemalloc.take_snapshot()
        
        # Compare snapshots
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        print("Top 10 memory allocations:")
        for stat in top_stats[:10]:
            print(stat)

if __name__ == "__main__":
    asyncio.run(memory_test())
```

## Debugging Development Issues

### Common Development Issues

```python
# Debug import issues
import sys
print("Python path:", sys.path)
print("Installed packages:", [p for p in sys.modules.keys() if 'zenoo' in p])

# Debug async issues
import asyncio
import logging

# Enable asyncio debug mode
asyncio.get_event_loop().set_debug(True)
logging.getLogger('asyncio').setLevel(logging.DEBUG)

# Debug type checking issues
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type checking
    from some_module import SomeClass
```

### Development Tools

```python
# Development utilities
class DevUtils:
    @staticmethod
    def print_model_fields(model_class):
        """Print all fields of a model class."""
        for name, field in model_class.__fields__.items():
            print(f"{name}: {field.type_} = {field.default}")
    
    @staticmethod
    async def inspect_rpc_call(client, service, method, *args):
        """Inspect RPC call details."""
        print(f"RPC Call: {service}.{method}")
        print(f"Args: {args}")
        
        result = await client.call(service, method, *args)
        print(f"Result: {result}")
        return result
    
    @staticmethod
    def mock_odoo_response(data):
        """Create mock Odoo response."""
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": data
        }
```

## Next Steps

- Review [Testing Guide](testing.md) for comprehensive testing strategies
- Check [Documentation Guide](documentation.md) for documentation standards
- Explore [Release Process](release.md) for release management
- Read project files for community guidelines
