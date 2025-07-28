# Zenoo RPC

<div align="center">

**A zen-like, modern async Python library for Odoo RPC with type safety and superior Developer Experience (DX)**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/zenoo-rpc.svg)](https://pypi.org/project/zenoo-rpc/)
[![Python versions](https://img.shields.io/pypi/pyversions/zenoo-rpc.svg)](https://pypi.org/project/zenoo-rpc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/tuanle96/zenoo-rpc/workflows/CI/badge.svg)](https://github.com/tuanle96/zenoo-rpc/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/tuanle96/zenoo-rpc/branch/main/graph/badge.svg)](https://codecov.io/gh/tuanle96/zenoo-rpc)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue.svg)](https://zenoo-rpc.readthedocs.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Downloads](https://img.shields.io/pypi/dm/zenoo-rpc.svg)](https://pypi.org/project/zenoo-rpc/)
[![GitHub stars](https://img.shields.io/github/stars/tuanle96/zenoo-rpc.svg)](https://github.com/tuanle96/zenoo-rpc/stargazers)

[📚 Documentation](https://zenoo-rpc.readthedocs.io) • [🚀 Quick Start](https://zenoo-rpc.readthedocs.io/getting-started/quickstart/) • [📦 PyPI](https://pypi.org/project/zenoo-rpc/) • [🐛 Issues](https://github.com/tuanle96/zenoo-rpc/issues) • [💬 Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)

</div>

## 🚀 Why Zenoo RPC?

Zenoo RPC is a next-generation Python library designed to replace `odoorpc` with modern Python practices and superior performance. Built from the ground up with async/await, type safety, and developer experience in mind.

> **"Zen"** - Simple, elegant, and intuitive API design  
> **"oo"** - Object-oriented with Odoo integration  
> **"RPC"** - Remote Procedure Call excellence

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

### 🎯 Zenoo RPC Solutions

```python
# odoorpc (old way)
Partner = odoo.env['res.partner']
partner_ids = Partner.search([('is_company', '=', True)], limit=10)
partners = Partner.browse(partner_ids)  # Second RPC call!

# Zenoo RPC (modern way)
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")

    partners = await client.model(ResPartner).filter(
        is_company=True
    ).limit(10).all()  # Single RPC call with type safety!
```

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install zenoo-rpc
```

### With Optional Dependencies

```bash
# For Redis caching support
pip install zenoo-rpc[redis]

# For development
pip install zenoo-rpc[dev]

# All optional dependencies
pip install zenoo-rpc[dev,redis]
```

### From Source

```bash
git clone https://github.com/tuanle96/zenoo-rpc.git
cd zenoo-rpc
pip install -e .
```

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

## 🚀 Quick Start

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

        # Transaction management (optional)
        await client.setup_transaction_manager()
        async with client.transaction():
            partner = await client.model(ResPartner).filter(
                is_company=True
            ).first()
            if partner:
                print(f"Processing: {partner.name}")
                # Modifications are committed automatically on context exit

if __name__ == "__main__":
    asyncio.run(main())
```

## 🎯 Advanced Features

### Lazy Loading with Type Safety

```python
# Relationship fields are lazy-loaded automatically
partner = await client.model(ResPartner).get(1)
company = await partner.company_id  # Loaded on demand
children = await partner.child_ids.all()  # Lazy collection
```

### Intelligent Caching

```python
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")

    # Setup cache manager
    await client.setup_cache_manager(backend="redis", url="redis://localhost:6379/0")

    # Cached queries
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).cache(ttl=300).all()  # Cached for 5 minutes
```

### Batch Operations

```python
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")

    # Setup batch manager
    await client.setup_batch_manager(max_chunk_size=100)

    # Efficient bulk operations
    async with client.batch() as batch:
        partners_data = [
            {"name": "Company 1", "email": "c1@example.com"},
            {"name": "Company 2", "email": "c2@example.com"},
        ]
        partners = await batch.create_many(ResPartner, partners_data)
```

### Transaction Management

```python
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")

    # Setup transaction manager
    await client.setup_transaction_manager()

    # ACID transactions with rollback
    async with client.transaction() as tx:
        partner = await client.model(ResPartner).create({
            "name": "Test Company",
            "email": "test@example.com"
        })

        # If any error occurs, transaction is automatically rolled back
        await partner.update({"phone": "+1234567890"})
        # Committed automatically on successful exit
```

## 🧪 Development Status

Zenoo RPC is currently in **Alpha** stage with active development. The core architecture is stable and functional, but we're continuously improving based on community feedback.

### Current Status

- ✅ **Core Features**: Fully implemented and tested
- ✅ **Type Safety**: Complete Pydantic integration
- ✅ **Async Operations**: Full async/await support
- ✅ **Advanced Features**: Caching, transactions, batch operations
- ✅ **Documentation**: Comprehensive guides and examples
- 🔄 **Community**: Growing user base and contributors
- 🔄 **Performance**: Ongoing optimization efforts

### Roadmap

- [x] **Phase 1**: Core transport layer and async client
- [x] **Phase 2**: Pydantic models and query builder foundation  
- [x] **Phase 3**: Advanced features (caching, transactions, batch ops)
- [x] **Phase 4**: Documentation and community adoption
- [ ] **Phase 5**: Performance optimization and production hardening
- [ ] **Phase 6**: Plugin system and extensibility
- [ ] **Phase 7**: GraphQL support and modern APIs

### Production Readiness

Zenoo RPC is being used in production environments, but we recommend:

- **Testing**: Thoroughly test in your specific environment
- **Monitoring**: Implement proper logging and monitoring
- **Gradual Migration**: Migrate from odoorpc incrementally
- **Community Support**: Join our discussions for help and feedback

### Compatibility

- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Odoo**: 18.0 (tested) - other versions compatibility not yet verified
- **Operating Systems**: Linux, macOS, Windows

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or sharing feedback, your contributions help make Zenoo RPC better for everyone.

### Ways to Contribute

- 🐛 **Report Bugs**: Use our [issue templates](https://github.com/tuanle96/zenoo-rpc/issues/new/choose)
- ✨ **Request Features**: Share your ideas in [GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)
- 📝 **Improve Documentation**: Help us make the docs clearer and more comprehensive
- 🧪 **Write Tests**: Increase test coverage and add edge cases
- 🔧 **Fix Issues**: Pick up issues labeled `good first issue` or `help wanted`
- 💡 **Share Examples**: Contribute real-world usage examples

### Quick Development Setup

```bash
# Clone the repository
git clone https://github.com/tuanle96/zenoo-rpc.git
cd zenoo-rpc

# Install development dependencies
pip install -e ".[dev,redis]"

# Install pre-commit hooks (recommended)
pre-commit install

# Run tests
pytest

# Run quality checks
ruff check .
black .
mypy src/zenoo_rpc

# Build documentation locally
mkdocs serve
```

### Contribution Guidelines

Please read our [Contributing Guide](CONTRIBUTING.md) for detailed information about:

- Code style and conventions
- Testing requirements
- Pull request process
- Issue reporting guidelines
- Community standards

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with tests
4. **Run** quality checks (`pre-commit run --all-files`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to your branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### Getting Help

- 💬 **[GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)**: Ask questions and get help
- 📚 **[Documentation](https://zenoo-rpc.readthedocs.io)**: Comprehensive guides and examples
- 🐛 **[Issues](https://github.com/tuanle96/zenoo-rpc/issues)**: Report bugs or request features

## 🛠️ Development

Want to contribute? Here's how to set up your development environment:

```bash
# Clone the repository
git clone https://github.com/tuanle96/zenoo-rpc.git
cd zenoo-rpc

# Install development dependencies
pip install -e ".[dev,redis]"

# Install pre-commit hooks (recommended)
pre-commit install

# Run tests
pytest

# Run quality checks
ruff check .
black .
mypy src/zenoo_rpc
```

## 📚 Documentation

- **[Getting Started](https://zenoo-rpc.readthedocs.io/getting-started/)**: Installation and basic usage
- **[User Guide](https://zenoo-rpc.readthedocs.io/user-guide/)**: Comprehensive feature documentation
- **[API Reference](https://zenoo-rpc.readthedocs.io/api/)**: Complete API documentation
- **[Migration Guide](https://zenoo-rpc.readthedocs.io/migration/)**: Migrating from odoorpc
- **[Examples](https://zenoo-rpc.readthedocs.io/examples/)**: Real-world usage examples

## 🐛 Support

- **[GitHub Issues](https://github.com/tuanle96/zenoo-rpc/issues)**: Bug reports and feature requests
- **[GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)**: Questions and community discussion
- **[Documentation](https://zenoo-rpc.readthedocs.io)**: Comprehensive guides and API reference

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need to modernize the Odoo Python ecosystem
- Built on the shoulders of giants: `httpx`, `pydantic`, and `asyncio`
- Thanks to the OCA team for maintaining `odoorpc` and showing us what to improve
- Special thanks to all contributors and early adopters

---

**Zenoo RPC**: Because your Odoo integrations deserve modern Python! 🐍✨

<div align="center">

**[⭐ Star us on GitHub](https://github.com/tuanle96/zenoo-rpc) • [📦 Try it on PyPI](https://pypi.org/project/zenoo-rpc/) • [📚 Read the Docs](https://zenoo-rpc.readthedocs.io)**

</div>