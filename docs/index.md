# Zenoo RPC

**A zen-like, modern async Python library for Odoo RPC with type safety and superior Developer Experience (DX)**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/zenoo-rpc.svg)](https://pypi.org/project/zenoo-rpc/)
[![Python versions](https://img.shields.io/pypi/pyversions/zenoo-rpc.svg)](https://pypi.org/project/zenoo-rpc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Why Zenoo RPC?

Zenoo RPC is a next-generation Python library designed to replace `odoorpc` with modern Python practices and superior performance. Built from the ground up with async/await, type safety, and developer experience in mind.

### ✨ Key Features

- **🔄 Async-First**: Built with `asyncio` and `httpx` for high-performance concurrent operations
- **🛡️ Type Safety**: Full Pydantic integration with IDE support and runtime validation
- **🎯 Fluent API**: Intuitive, chainable query builder that feels natural
- **⚡ Performance**: Intelligent caching, batch operations, and optimized RPC calls
- **🔧 Modern Python**: Leverages Python 3.8+ features with proper type hints
- **📦 Clean Architecture**: Well-structured, testable, and maintainable codebase
- **🔄 Transaction Support**: ACID-compliant transactions with rollback capabilities
- **🚀 Batch Operations**: Efficient bulk operations for high-performance scenarios
- **🔁 Retry Mechanisms**: Intelligent retry with exponential backoff and circuit breaker
- **💾 Intelligent Caching**: TTL/LRU caching with Redis support

### 🤔 Problems with odoorpc

- **Synchronous only**: No async support for modern Python applications
- **No type safety**: Raw dictionaries and lists without validation
- **Chatty API**: Multiple RPC calls for simple operations (search + browse)
- **Complex relationship handling**: Requires knowledge of Odoo's tuple commands
- **Poor error handling**: Generic exceptions without context
- **No caching**: Repeated calls for the same data
- **No transactions**: No rollback capabilities
- **No batch operations**: Inefficient for bulk operations

### 🎯 Zenoo RPC Solutions

```python
# odoorpc (old way)
Partner = odoo.env['res.partner']
partner_ids = Partner.search([('is_company', '=', True)], limit=10)
partners = Partner.browse(partner_ids)  # Second RPC call!

# Zenoo RPC (modern way)
partners = await client.model(ResPartner).filter(
    is_company=True
).limit(10).all()  # Single RPC call with type safety!
```

## 🚀 Quick Start

### Installation

```bash
pip install zenoo-rpc
```

For development with all optional dependencies:
```bash
pip install zenoo-rpc[dev,redis]
```

### Basic Usage

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def main():
    async with ZenooClient("https://your-odoo-server.com") as client:
        # Authenticate
        await client.login("your_database", "your_username", "your_password")

        # Type-safe queries with IDE support
        partners = await client.model(ResPartner).filter(
            is_company=True,
            name__ilike="company%"
        ).limit(10).all()
        
        # Access fields with full type safety
        for partner in partners:
            print(f"Company: {partner.name} - Email: {partner.email}")
        
        # Transaction management
        async with client.transaction() as tx:
            partner = await client.model(ResPartner).get(1)
            partner.name = "New Name"
            partner.email = "new@email.com"
            # Committed automatically on context exit

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 Documentation Sections

### 🏁 Getting Started
- [Installation Guide](getting-started/installation.md) - Complete installation instructions
- [Quick Start Tutorial](getting-started/quickstart.md) - Get up and running in 5 minutes
- [Migration from odoorpc](getting-started/migration.md) - Step-by-step migration guide

### 📖 User Guide
- [Client Usage](user-guide/client.md) - ZenooClient configuration and usage
- [Models & Type Safety](user-guide/models.md) - Pydantic models and validation
- [Query Builder](user-guide/queries.md) - Fluent queries and Q objects
- [Relationships](user-guide/relationships.md) - Lazy loading and relationships
- [Caching System](user-guide/caching.md) - Intelligent caching strategies
- [Transactions](user-guide/transactions.md) - ACID transactions and rollback
- [Batch Operations](user-guide/batch-operations.md) - Efficient bulk operations
- [Retry Mechanisms](user-guide/retry-mechanisms.md) - Resilient error handling
- [Error Handling](user-guide/error-handling.md) - Exception hierarchy and debugging

### 🎓 Tutorials
- [Basic CRUD Operations](tutorials/basic-crud.md) - Create, read, update, delete
- [Advanced Queries](tutorials/advanced-queries.md) - Complex filtering and joins
- [Performance Optimization](tutorials/performance-optimization.md) - Speed up your code
- [Testing Strategies](tutorials/testing.md) - Test your Odoo integrations
- [Production Deployment](tutorials/production-deployment.md) - Deploy with confidence

### 📋 Examples
- [Real-World Examples](examples/real-world/index.md) - Production-ready code samples
- [Common Patterns](examples/patterns/index.md) - Reusable patterns and recipes
- [Integration Examples](examples/integrations/index.md) - FastAPI, Django, Flask integrations

### 🔧 API Reference
- [Complete API Documentation](api-reference/index.md) - Auto-generated API reference

### 🏗️ Advanced Topics
- [Architecture Overview](advanced/architecture.md) - Internal design and patterns
- [Performance Considerations](advanced/performance.md) - Optimization techniques
- [Security Best Practices](advanced/security.md) - Secure your integrations
- [Extending Zenoo RPC](advanced/extending.md) - Custom models and transports

### 🔍 Troubleshooting
- [Common Issues](troubleshooting/common-issues.md) - Solutions to frequent problems
- [Debugging Guide](troubleshooting/debugging.md) - Debug your integrations
- [FAQ](troubleshooting/faq.md) - Frequently asked questions

### 🤝 Contributing
- [Development Setup](contributing/development.md) - Set up your dev environment
- [Testing Guidelines](contributing/testing.md) - Write and run tests
- [Documentation Guidelines](contributing/documentation.md) - Improve the docs

## 🏗️ Architecture

Zenoo RPC follows modern Python best practices with a clean, modular architecture:

```
src/zenoo_rpc/
├── client.py              # Main async client
├── transport/             # HTTP transport layer
├── models/                # Pydantic models
├── query/                 # Fluent query builder
├── cache/                 # Async caching layer
├── exceptions/            # Structured exception hierarchy
├── transaction/           # Transaction management
├── batch/                 # Batch operations
├── retry/                 # Retry mechanisms
└── utils/                 # Utilities and helpers
```

## 🧪 Development Status

Zenoo RPC is currently in **Alpha** stage. The core architecture is implemented and functional, but the API may change before the stable release.

### Roadmap

- [x] **Phase 1**: Core transport layer and async client
- [x] **Phase 2**: Pydantic models and query builder foundation
- [x] **Phase 3**: Advanced features (caching, transactions, batch ops)
- [ ] **Phase 4**: Documentation and community adoption
- [ ] **Phase 5**: Stable release and ecosystem growth

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](contributing/development.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/tuanle96/zenoo-rpc/blob/main/LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need to modernize the Odoo Python ecosystem
- Built on the shoulders of giants: `httpx`, `pydantic`, and `asyncio`
- Thanks to the OCA team for maintaining `odoorpc` and showing us what to improve

---

**Zenoo RPC**: Because your Odoo integrations deserve modern Python! 🐍✨
