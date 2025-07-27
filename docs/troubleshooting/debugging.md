# Debugging Guide

Comprehensive debugging guide for Zenoo RPC applications covering common issues, debugging techniques, logging configuration, and troubleshooting tools.

## Overview

Effective debugging in Zenoo RPC involves:

- **Logging Configuration**: Proper logging setup for visibility
- **Error Analysis**: Understanding error types and root causes
- **Network Debugging**: Troubleshooting connection and RPC issues
- **Performance Debugging**: Identifying bottlenecks and optimization opportunities
- **Development Tools**: Using debugging tools and techniques

## Logging Configuration

### Basic Logging Setup

```python
import logging
import sys
from zenoo_rpc import ZenooClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('zenoo_rpc.log')
    ]
)

# Enable specific loggers
logging.getLogger('zenoo_rpc').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.INFO)
logging.getLogger('asyncio').setLevel(logging.WARNING)

async def debug_example():
    """Example with debug logging."""
    async with ZenooClient("localhost", port=8069) as client:
        # Enable debug mode
        client.debug = True
        
        await client.login("demo", "admin", "admin")
        
        # This will log detailed request/response information
        partners = await client.model(ResPartner).filter(is_company=True).all()
```

### Advanced Logging Configuration

```python
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s - %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'zenoo_rpc_debug.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': 'zenoo_rpc_errors.log'
        }
    },
    'loggers': {
        'zenoo_rpc': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'zenoo_rpc.transport': {
            'level': 'DEBUG',
            'handlers': ['file'],
            'propagate': False
        },
        'zenoo_rpc.cache': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console']
    }
}

# Apply configuration
logging.config.dictConfig(LOGGING_CONFIG)
```

### Request/Response Logging

```python
class DebugTransport:
    """Transport wrapper with detailed logging."""
    
    def __init__(self, transport):
        self.transport = transport
        self.logger = logging.getLogger('zenoo_rpc.debug')
    
    async def json_rpc_call(self, service: str, method: str, params: dict):
        """Log detailed request/response information."""
        request_id = str(uuid.uuid4())[:8]
        
        self.logger.debug(f"[{request_id}] RPC Request:")
        self.logger.debug(f"  Service: {service}")
        self.logger.debug(f"  Method: {method}")
        self.logger.debug(f"  Params: {json.dumps(params, indent=2, default=str)}")
        
        start_time = time.time()
        
        try:
            response = await self.transport.json_rpc_call(service, method, params)
            
            duration = time.time() - start_time
            self.logger.debug(f"[{request_id}] RPC Response ({duration:.3f}s):")
            self.logger.debug(f"  Response: {json.dumps(response, indent=2, default=str)}")
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"[{request_id}] RPC Error ({duration:.3f}s): {e}")
            raise

# Usage
async def debug_with_detailed_logging():
    client = ZenooClient("localhost", port=8069)
    client.transport = DebugTransport(client.transport)
    
    async with client:
        await client.login("demo", "admin", "admin")
        partners = await client.search("res.partner", [])
```

## Common Issues & Solutions

### Connection Issues

#### Issue: Connection Refused

```python
# Error: ConnectionRefusedError: [Errno 61] Connection refused

# Debugging steps:
async def debug_connection():
    """Debug connection issues."""
    
    # 1. Check if Odoo server is running
    import socket
    
    def check_port(host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    
    if not check_port("localhost", 8069):
        print("❌ Odoo server is not running on localhost:8069")
        return
    
    print("✅ Odoo server is accessible")
    
    # 2. Test basic HTTP connectivity
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8069/web/database/selector")
            print(f"✅ HTTP connectivity OK (status: {response.status_code})")
    except Exception as e:
        print(f"❌ HTTP connectivity failed: {e}")
        return
    
    # 3. Test JSON-RPC endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8069/jsonrpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "service": "common",
                        "method": "version",
                        "args": []
                    },
                    "id": 1
                }
            )
            print(f"✅ JSON-RPC endpoint OK: {response.json()}")
    except Exception as e:
        print(f"❌ JSON-RPC endpoint failed: {e}")
```

#### Issue: SSL/TLS Errors

```python
# Error: SSL certificate verification failed

async def debug_ssl_issues():
    """Debug SSL/TLS issues."""
    
    # Option 1: Disable SSL verification (development only)
    client = ZenooClient(
        "https://demo.odoo.com",
        port=443,
        verify_ssl=False  # Only for development!
    )
    
    # Option 2: Custom SSL context
    import ssl
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    client = ZenooClient(
        "https://demo.odoo.com",
        port=443,
        ssl_context=ssl_context
    )
    
    # Option 3: Use custom CA bundle
    client = ZenooClient(
        "https://demo.odoo.com",
        port=443,
        ca_bundle_path="/path/to/ca-bundle.crt"
    )
```

### Authentication Issues

#### Issue: Invalid Credentials

```python
async def debug_authentication():
    """Debug authentication issues."""
    
    client = ZenooClient("localhost", port=8069)
    
    try:
        await client.login("demo", "admin", "wrong_password")
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        
        # Debug steps:
        
        # 1. Check database exists
        databases = await client.list_databases()
        print(f"Available databases: {databases}")
        
        if "demo" not in databases:
            print("❌ Database 'demo' does not exist")
            return
        
        # 2. Test with different credentials
        try:
            await client.login("demo", "admin", "admin")
            print("✅ Authentication successful with admin/admin")
        except AuthenticationError:
            print("❌ Default admin credentials don't work")
            
            # 3. Check if admin user exists
            # This requires a working login, so might need manual verification
            print("💡 Check Odoo logs for authentication errors")
            print("💡 Verify user exists in database")
            print("💡 Check if user is active")
```

### Query Issues

#### Issue: Invalid Domain Filters

```python
async def debug_domain_filters():
    """Debug domain filter issues."""
    
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    
    # Common domain errors and fixes:
    
    # ❌ Wrong: Using Python operators
    try:
        partners = await client.search("res.partner", [
            ("name", "==", "Test")  # Wrong operator
        ])
    except Exception as e:
        print(f"Domain error: {e}")
    
    # ✅ Correct: Using Odoo operators
    partners = await client.search("res.partner", [
        ("name", "=", "Test")  # Correct operator
    ])
    
    # ❌ Wrong: Invalid field name
    try:
        partners = await client.search("res.partner", [
            ("invalid_field", "=", "Test")
        ])
    except Exception as e:
        print(f"Field error: {e}")
        
        # Debug: Get available fields
        fields = await client.call(
            "object", "execute_kw",
            client.database, client.uid, client.password,
            "res.partner", "fields_get", []
        )
        print(f"Available fields: {list(fields.keys())}")
    
    # ❌ Wrong: Type mismatch
    try:
        partners = await client.search("res.partner", [
            ("id", "=", "not_a_number")  # Should be int
        ])
    except Exception as e:
        print(f"Type error: {e}")
```

### Performance Issues

#### Issue: Slow Queries

```python
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def timer(description: str):
    """Context manager for timing operations."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        print(f"{description}: {duration:.3f}s")

async def debug_performance():
    """Debug performance issues."""
    
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    
    # 1. Measure query performance
    async with timer("Basic search"):
        partners = await client.search("res.partner", [])
    
    async with timer("Search with limit"):
        partners = await client.search("res.partner", [], limit=10)
    
    # 2. Compare search vs search_read
    async with timer("Search + Read (N+1 problem)"):
        partner_ids = await client.search("res.partner", [], limit=10)
        partners = await client.read("res.partner", partner_ids)
    
    async with timer("Search_read (optimized)"):
        partners = await client.search_read("res.partner", [], limit=10)
    
    # 3. Field selection optimization
    async with timer("All fields"):
        partners = await client.search_read("res.partner", [], limit=10)
    
    async with timer("Selected fields only"):
        partners = await client.search_read(
            "res.partner", [], 
            fields=["name", "email"], 
            limit=10
        )
    
    # 4. Caching impact
    await client.setup_cache_manager(backend="memory")
    
    async with timer("First query (no cache)"):
        partners = await client.model(ResPartner).filter(is_company=True).cache(ttl=300).all()
    
    async with timer("Second query (cached)"):
        partners = await client.model(ResPartner).filter(is_company=True).cache(ttl=300).all()
```

## Debugging Tools

### Interactive Debugging

```python
import pdb
import asyncio

async def debug_with_pdb():
    """Use pdb for interactive debugging."""
    
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    
    # Set breakpoint
    pdb.set_trace()
    
    # Now you can inspect variables interactively:
    # (Pdb) client.uid
    # (Pdb) await client.search("res.partner", [])
    # (Pdb) continue
    
    partners = await client.search("res.partner", [])
    return partners

# For async debugging, use:
# python -m pdb your_script.py
```

### Memory Debugging

```python
import tracemalloc
import gc

async def debug_memory_usage():
    """Debug memory usage and leaks."""
    
    # Start tracing
    tracemalloc.start()
    
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    
    # Take snapshot before operations
    snapshot1 = tracemalloc.take_snapshot()
    
    # Perform operations
    for i in range(100):
        partners = await client.search("res.partner", [], limit=10)
    
    # Take snapshot after operations
    snapshot2 = tracemalloc.take_snapshot()
    
    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("Top 10 memory allocations:")
    for stat in top_stats[:10]:
        print(stat)
    
    # Force garbage collection
    gc.collect()
    
    # Check for unclosed resources
    import asyncio
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    if tasks:
        print(f"Warning: {len(tasks)} unclosed tasks")
        for task in tasks:
            print(f"  {task}")
```

### Network Debugging

```python
import httpx

class DebugHTTPTransport(httpx.AsyncClient):
    """HTTP client with detailed network debugging."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('zenoo_rpc.network')
    
    async def request(self, method, url, **kwargs):
        """Log detailed network information."""
        
        # Log request
        self.logger.debug(f"→ {method} {url}")
        if 'json' in kwargs:
            self.logger.debug(f"  Request body: {json.dumps(kwargs['json'], indent=2)}")
        if 'headers' in kwargs:
            self.logger.debug(f"  Headers: {kwargs['headers']}")
        
        start_time = time.time()
        
        try:
            response = await super().request(method, url, **kwargs)
            
            duration = time.time() - start_time
            self.logger.debug(f"← {response.status_code} ({duration:.3f}s)")
            self.logger.debug(f"  Response headers: {dict(response.headers)}")
            
            # Log response body for JSON-RPC
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    response_json = response.json()
                    self.logger.debug(f"  Response body: {json.dumps(response_json, indent=2)}")
                except:
                    self.logger.debug(f"  Response body: {response.text}")
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"✗ Network error ({duration:.3f}s): {e}")
            raise

# Usage
async def debug_network():
    """Debug network issues."""
    
    # Replace default HTTP client
    debug_client = DebugHTTPTransport()
    
    # Manual JSON-RPC call with debugging
    response = await debug_client.post(
        "http://localhost:8069/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "version",
                "args": []
            },
            "id": 1
        }
    )
    
    await debug_client.aclose()
```

### Error Analysis Tools

```python
class ErrorAnalyzer:
    """Analyze and categorize errors."""
    
    def __init__(self):
        self.error_patterns = {
            'connection': [
                'Connection refused',
                'Connection timeout',
                'Name or service not known'
            ],
            'authentication': [
                'Access Denied',
                'Invalid login',
                'Authentication failed'
            ],
            'permission': [
                'Access rights',
                'Permission denied',
                'You do not have the rights'
            ],
            'validation': [
                'ValidationError',
                'Invalid value',
                'Required field'
            ],
            'database': [
                'database does not exist',
                'relation does not exist',
                'column does not exist'
            ]
        }
    
    def analyze_error(self, error: Exception) -> dict:
        """Analyze error and provide suggestions."""
        error_str = str(error).lower()
        
        analysis = {
            'error_type': 'unknown',
            'category': 'unknown',
            'suggestions': []
        }
        
        # Categorize error
        for category, patterns in self.error_patterns.items():
            if any(pattern.lower() in error_str for pattern in patterns):
                analysis['category'] = category
                break
        
        # Provide suggestions based on category
        if analysis['category'] == 'connection':
            analysis['suggestions'] = [
                'Check if Odoo server is running',
                'Verify host and port configuration',
                'Check network connectivity',
                'Verify firewall settings'
            ]
        elif analysis['category'] == 'authentication':
            analysis['suggestions'] = [
                'Verify username and password',
                'Check if database exists',
                'Verify user is active',
                'Check user permissions'
            ]
        elif analysis['category'] == 'permission':
            analysis['suggestions'] = [
                'Check user access rights',
                'Verify record rules',
                'Check field-level permissions',
                'Review security groups'
            ]
        elif analysis['category'] == 'validation':
            analysis['suggestions'] = [
                'Check required fields',
                'Verify field formats',
                'Review field constraints',
                'Check data types'
            ]
        elif analysis['category'] == 'database':
            analysis['suggestions'] = [
                'Check database name',
                'Verify model exists',
                'Check field names',
                'Review database schema'
            ]
        
        return analysis

# Usage
async def analyze_errors():
    """Example error analysis."""
    
    analyzer = ErrorAnalyzer()
    
    try:
        client = ZenooClient("localhost", port=8069)
        await client.login("demo", "admin", "wrong_password")
    except Exception as e:
        analysis = analyzer.analyze_error(e)
        
        print(f"Error: {e}")
        print(f"Category: {analysis['category']}")
        print("Suggestions:")
        for suggestion in analysis['suggestions']:
            print(f"  • {suggestion}")
```

## Development Debugging

### Debug Mode Configuration

```python
class DebugConfig:
    """Debug configuration for development."""
    
    def __init__(self):
        self.debug_mode = os.getenv("ZENOO_DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("ZENOO_LOG_LEVEL", "INFO").upper()
        self.log_requests = os.getenv("ZENOO_LOG_REQUESTS", "false").lower() == "true"
        self.log_responses = os.getenv("ZENOO_LOG_RESPONSES", "false").lower() == "true"
        self.profile_performance = os.getenv("ZENOO_PROFILE", "false").lower() == "true"
    
    def setup_logging(self):
        """Setup logging based on debug configuration."""
        if self.debug_mode:
            logging.getLogger('zenoo_rpc').setLevel(logging.DEBUG)
        else:
            logging.getLogger('zenoo_rpc').setLevel(getattr(logging, self.log_level))

# Environment variables for debugging:
# export ZENOO_DEBUG=true
# export ZENOO_LOG_LEVEL=DEBUG
# export ZENOO_LOG_REQUESTS=true
# export ZENOO_LOG_RESPONSES=true
# export ZENOO_PROFILE=true
```

### Testing Helpers

```python
import pytest
from unittest.mock import AsyncMock, patch

class DebugTestHelpers:
    """Helpers for debugging tests."""
    
    @staticmethod
    def mock_client():
        """Create a mock client for testing."""
        client = AsyncMock()
        client.uid = 1
        client.database = "test_db"
        client.password = "test_password"
        return client
    
    @staticmethod
    async def assert_rpc_call(mock_transport, service, method, *args):
        """Assert that a specific RPC call was made."""
        mock_transport.json_rpc_call.assert_called_with(service, method, list(args))
    
    @staticmethod
    def capture_logs(logger_name='zenoo_rpc'):
        """Capture logs for testing."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        return log_capture, handler

# Example test with debugging
@pytest.mark.asyncio
async def test_with_debugging():
    """Test with debugging helpers."""
    
    # Capture logs
    log_capture, handler = DebugTestHelpers.capture_logs()
    
    # Mock client
    client = DebugTestHelpers.mock_client()
    
    try:
        # Your test code here
        await client.search("res.partner", [])
        
        # Check logs
        log_output = log_capture.getvalue()
        assert "search" in log_output
        
    finally:
        # Cleanup
        logging.getLogger('zenoo_rpc').removeHandler(handler)
```

## Best Practices

### 1. Logging Strategy
- Use appropriate log levels (DEBUG for development, INFO for production)
- Include context information (request IDs, user IDs, etc.)
- Avoid logging sensitive information (passwords, tokens)
- Use structured logging for better analysis

### 2. Error Handling
- Catch specific exceptions rather than generic Exception
- Provide meaningful error messages
- Include debugging information in error context
- Log errors with full stack traces

### 3. Performance Monitoring
- Monitor response times and identify slow operations
- Track memory usage and detect leaks
- Profile critical code paths
- Use caching strategically

### 4. Development Workflow
- Use debug mode during development
- Set up proper IDE debugging configuration
- Write comprehensive tests with debugging helpers
- Use version control for debugging configurations

## Next Steps

- Review [FAQ](faq.md) for common questions and solutions
- Explore [Performance Optimization](../advanced/performance.md) for performance debugging
- Check [Security Considerations](../advanced/security.md) for security debugging
- Learn about [Monitoring Setup](monitoring.md) for production debugging
