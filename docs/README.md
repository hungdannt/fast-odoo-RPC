# Zenoo RPC Documentation

Welcome to the comprehensive documentation for Zenoo RPC - a zen-like, modern async Python library for Odoo RPC with type safety and superior Developer Experience (DX).

## 📚 Documentation Structure

This documentation is organized into several sections to help you get the most out of Zenoo RPC:

### 🏁 Getting Started
Perfect for newcomers to Zenoo RPC:
- **[Installation](getting-started/installation.md)** - Complete installation guide with all options
- **[Quick Start](getting-started/quickstart.md)** - Get up and running in 5 minutes
- **[Migration from odoorpc](getting-started/migration.md)** - Step-by-step migration guide

### 📖 User Guide
Comprehensive guides for all features:
- **[Client Usage](user-guide/client.md)** - ZenooClient configuration and usage
- **[Models & Type Safety](user-guide/models.md)** - Pydantic models and validation
- **[Query Builder](user-guide/queries.md)** - Fluent queries and Q objects
- **[Relationships](user-guide/relationships.md)** - Lazy loading and relationships
- **[Caching System](user-guide/caching.md)** - Intelligent caching strategies
- **[Transactions](user-guide/transactions.md)** - ACID transactions and rollback
- **[Batch Operations](user-guide/batch-operations.md)** - Efficient bulk operations
- **[Retry Mechanisms](user-guide/retry-mechanisms.md)** - Resilient error handling
- **[Error Handling](user-guide/error-handling.md)** - Exception hierarchy and debugging
- **[Configuration](user-guide/configuration.md)** - Advanced configuration options

### 🎓 Tutorials
Step-by-step tutorials for common tasks:
- **[Basic CRUD Operations](tutorials/basic-crud.md)** - Create, read, update, delete
- **[Advanced Queries](tutorials/advanced-queries.md)** - Complex filtering and joins
- **[Performance Optimization](tutorials/performance-optimization.md)** - Speed up your code
- **[Testing Strategies](tutorials/testing.md)** - Test your Odoo integrations
- **[Production Deployment](tutorials/production-deployment.md)** - Deploy with confidence

### 📋 Examples
Real-world examples and patterns:
- **[Real-World Examples](examples/real-world/)** - Production-ready code samples
- **[Common Patterns](examples/patterns/)** - Reusable patterns and recipes
- **[Integration Examples](examples/integrations/)** - FastAPI, Django, Flask integrations

### 🔧 API Reference
Complete API documentation:
- **[Client API](api-reference/client.md)** - ZenooClient methods and properties
- **[Models API](api-reference/models/)** - Model classes and fields
- **[Query API](api-reference/query/)** - Query builder and expressions
- **[Cache API](api-reference/cache/)** - Caching system
- **[Transaction API](api-reference/transaction/)** - Transaction management
- **[Batch API](api-reference/batch/)** - Batch operations
- **[Retry API](api-reference/retry/)** - Retry mechanisms
- **[Exceptions API](api-reference/exceptions/)** - Exception hierarchy

### 🏗️ Advanced Topics
Deep dives into advanced concepts:
- **[Architecture Overview](advanced/architecture.md)** - Internal design and patterns
- **[Performance Considerations](advanced/performance.md)** - Optimization techniques
- **[Security Best Practices](advanced/security.md)** - Secure your integrations
- **[Extending Zenoo RPC](advanced/extending.md)** - Custom models and transports
- **[Internal Implementation](advanced/internals.md)** - How it works under the hood

### 🔍 Troubleshooting
Solutions to common problems:
- **[Common Issues](troubleshooting/common-issues.md)** - Solutions to frequent problems
- **[Debugging Guide](troubleshooting/debugging.md)** - Debug your integrations
- **[FAQ](troubleshooting/faq.md)** - Frequently asked questions

### 🤝 Contributing
Help improve Zenoo RPC:
- **[Development Setup](contributing/development.md)** - Set up your dev environment
- **[Testing Guidelines](contributing/testing.md)** - Write and run tests
- **[Documentation Guidelines](contributing/documentation.md)** - Improve the docs
- **[Release Process](contributing/release.md)** - How releases are made

## 🚀 Quick Navigation

### New to Zenoo RPC?
1. Start with [Installation](getting-started/installation.md)
2. Follow the [Quick Start](getting-started/quickstart.md) tutorial
3. Try the [Basic CRUD](tutorials/basic-crud.md) tutorial
4. Explore [Real-World Examples](examples/real-world/)

### Migrating from odoorpc?
1. Read the [Migration Guide](getting-started/migration.md)
2. Check the [API Reference](api-reference/) for equivalent methods
3. Review [Performance Optimization](tutorials/performance-optimization.md)

### Looking for specific features?
- **Type Safety**: [Models & Type Safety](user-guide/models.md)
- **Performance**: [Caching](user-guide/caching.md) and [Batch Operations](user-guide/batch-operations.md)
- **Reliability**: [Transactions](user-guide/transactions.md) and [Retry Mechanisms](user-guide/retry-mechanisms.md)
- **Integration**: [FastAPI Example](examples/real-world/fastapi-integration.md)

### Having issues?
1. Check [Common Issues](troubleshooting/common-issues.md)
2. Use the [Debugging Guide](troubleshooting/debugging.md)
3. Search the [FAQ](troubleshooting/faq.md)
4. Ask in [GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)

## 📖 Reading the Documentation

### Online Documentation
The latest documentation is available at: [https://zenoo-rpc.readthedocs.io](https://zenoo-rpc.readthedocs.io)

### Local Documentation
To build and serve the documentation locally:

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocstrings[python]

# Serve documentation locally
mkdocs serve

# Build static documentation
mkdocs build
```

The documentation will be available at `http://localhost:8000`

## 🎯 Documentation Features

### Interactive Examples
All code examples are tested and can be run directly. Look for the copy button (📋) to copy code snippets.

### Search Functionality
Use the search box (Ctrl/Cmd + K) to quickly find information across all documentation.

### Mobile Friendly
The documentation is fully responsive and works great on mobile devices.

### Dark Mode
Toggle between light and dark themes using the theme switcher.

### Version Support
Documentation is available for all major versions of Zenoo RPC.

## 🔄 Documentation Updates

The documentation is continuously updated with:
- New features and improvements
- Additional examples and tutorials
- Community contributions
- Bug fixes and clarifications

## 🤝 Contributing to Documentation

We welcome contributions to improve the documentation! See our [Documentation Guidelines](contributing/documentation.md) for:
- Writing style guide
- Documentation structure
- How to add examples
- Review process

## 📞 Getting Help

If you can't find what you're looking for in the documentation:

1. **Search**: Use the search functionality (Ctrl/Cmd + K)
2. **GitHub Discussions**: Ask questions in [GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)
3. **GitHub Issues**: Report documentation bugs in [GitHub Issues](https://github.com/tuanle96/zenoo-rpc/issues)
4. **Community**: Join our community discussions

## 📄 License

This documentation is licensed under the same MIT License as Zenoo RPC. See the [LICENSE](https://github.com/tuanle96/zenoo-rpc/blob/main/LICENSE) file for details.

---

**Happy coding with Zenoo RPC!** 🐍✨

*Last updated: December 2024*
