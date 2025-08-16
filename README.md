# fast-odoo RPC

<div align="center">

**A next-generation, modern async Python library for Odoo RPC with type safety, AI integration, and MCP protocol support**


</div>

## 🚀 Why fast-odoo RPC?

fast-odoo RPC is a next-generation Python library designed to replace `odoorpc` with modern Python practices and superior performance. Built from the ground up with async/await, type safety, and developer experience in mind.


### ✨ Key Features

- **🔄 Async-First**: Built with `asyncio` and `httpx` for high-performance concurrent operations
- **🛡️ Type Safety**: Full Pydantic integration with IDE support and runtime validation
- **🎯 Fluent API**: Intuitive, chainable query builder that feels natural
- **🤖 AI-Powered**: Natural language queries, error diagnosis, and code generation
- **🔌 MCP Integration**: Full Model Context Protocol support for AI assistants (Claude Desktop, ChatGPT)
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

### 🎯 fast-odoo RPC Solutions

```python
# odoorpc (old way)
Partner = odoo.env['res.partner']
partner_ids = Partner.search([('is_company', '=', True)], limit=10)
partners = Partner.browse(partner_ids)  # Second RPC call!

# fast-odoo RPC (modern way)
async with fast-odooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")

    partners = await client.model(ResPartner).filter(
        is_company=True
    ).limit(10).all()  # Single RPC call with type safety!
```

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install fast-odoo-rpc
```

### With Optional Dependencies

```bash
# For Redis caching support
pip install fast-odoo-rpc[redis]

# For AI features (Gemini, OpenAI, Anthropic)
pip install fast-odoo-rpc[ai]

# For MCP integration (AI assistants)
pip install fast-odoo-rpc[mcp]

# For development
pip install fast-odoo-rpc[dev]

# All features
pip install fast-odoo-rpc[ai,mcp,redis,dev]
```

### HTTP/2 Support

fast-odoo RPC includes built-in HTTP/2 support for improved performance:
- **Automatic HTTP/2**: All connections use HTTP/2 when available
- **Multiplexing**: Multiple requests over a single connection
- **Header compression**: Reduced bandwidth usage
- **Server push**: Enhanced performance for compatible servers

No additional configuration required - HTTP/2 support is enabled by default.



## 🏗️ Architecture

fast-odoo RPC follows modern Python best practices with a clean, modular architecture:

```
src/fast-odoo_rpc/
├── client.py              # Main async client
├── transport/             # HTTP transport layer
├── models/                # Pydantic models
├── query/                 # Fluent query builder
├── cache/                 # Async caching layer
├── exceptions/            # Structured exception hierarchy
├── transaction/           # Transaction management
├── batch/                 # Batch operations
├── retry/                 # Retry mechanisms
├── ai/                    # AI-powered features
├── mcp_server/            # Model Context Protocol server
├── mcp_client/            # Model Context Protocol client
└── utils/                 # Utilities and helpers
```

## 🚀 Quick Start

```python
import asyncio
from fast-odoo_rpc import fast-odooClient
from fast-odoo_rpc.models.common import ResPartner

async def main():
    async with fast-odooClient("https://your-odoo-server.com") as client:
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

## 🔌 MCP Integration - AI Assistant Support

fast-odoo RPC provides full **Model Context Protocol (MCP)** support, enabling seamless integration with AI assistants like Claude Desktop, ChatGPT, and other MCP-compatible tools.

### 🤖 Use with Claude Desktop

Configure Claude Desktop to use fast-odoo RPC as an MCP server:

```json
// ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["-m", "fast-odoo_rpc.mcp_server.cli"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DATABASE": "demo",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "admin"
      }
    }
  }
}
```

Now Claude can directly interact with your Odoo data:

```
User: "Find all technology companies in Vietnam and analyze their sales"

Claude automatically:
1. Searches for companies with filters: is_company=True, country='Vietnam', name contains 'tech'
2. Retrieves their sales orders and analyzes performance
3. Provides insights and recommendations
```

### 🛠️ MCP Tools Available

- **search_records** - Advanced search with complex filters
- **get_record** - Retrieve specific records with relationships
- **create_record** - Create new records with validation
- **update_record** - Update existing records
- **delete_record** - Delete records safely
- **complex_search** - Advanced queries with Q objects
- **batch_operation** - High-performance bulk operations
- **analytics_query** - Data analysis and aggregation

### 🚀 Installation with MCP

```bash
# Install with MCP support
pip install fast-odoo-rpc[mcp]

# Start MCP server
python -m fast-odoo_rpc.mcp_server.cli --transport stdio
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
async with fast-odooClient("localhost", port=8069) as client:
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
async with fast-odooClient("localhost", port=8069) as client:
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
async with fast-odooClient("localhost", port=8069) as client:
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

### 🤖 AI-Powered Features

fast-odoo RPC includes cutting-edge AI capabilities powered by LiteLLM and Google Gemini:

```python
async with fast-odooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")

    # Setup AI capabilities
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-gemini-api-key"
    )

    # Natural language queries
    partners = await client.ai.query("Find all companies in Vietnam with revenue > 1M USD")

    # Intelligent error diagnosis
    try:
        result = await client.search("invalid.model", [])
    except Exception as error:
        diagnosis = await client.ai.diagnose(error)
        print(f"Problem: {diagnosis['problem']}")
        print(f"Solution: {diagnosis['solution']}")

    # Smart code generation
    model_code = await client.ai.generate_model("res.partner")

    # Performance optimization suggestions
    suggestions = await client.ai.suggest_optimization(query_stats)

    # Interactive AI chat
    response = await client.ai.chat("How do I create a Many2one field in Odoo?")
```

**AI Features:**
- 🗣️ **Natural Language Queries**: Convert plain English to optimized Odoo queries
- 🔍 **Error Diagnosis**: AI-powered error analysis with actionable solutions
- 🏗️ **Code Generation**: Generate typed Python models from Odoo schemas
- ⚡ **Performance Optimization**: AI suggestions for query and cache optimization
- 💬 **Interactive Chat**: Get expert advice on Odoo development

**Installation with AI:**
```bash
pip install fast-odoo-rpc[ai]
```

## 🧪 Development Status

fast-odoo RPC is currently in **Alpha** stage with active development. The core architecture is stable and functional, but we're continuously improving based on community feedback.

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
- [x] **Phase 4**: AI-powered features (natural language queries, error diagnosis, code generation)
- [x] **Phase 5**: Documentation and community adoption
- [ ] **Phase 6**: Performance optimization and production hardening
- [ ] **Phase 7**: Advanced AI features (predictive analytics, auto-optimization)
- [ ] **Phase 8**: Plugin system and extensibility
- [ ] **Phase 9**: GraphQL support and modern APIs

### Production Readiness

fast-odoo RPC is being used in production environments, but we recommend:

- **Testing**: Thoroughly test in your specific environment
- **Monitoring**: Implement proper logging and monitoring
- **Gradual Migration**: Migrate from odoorpc incrementally
- **Community Support**: Join our discussions for help and feedback

### Compatibility

- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Odoo**: 18.0 (tested) - other versions compatibility not yet verified
- **Operating Systems**: Linux, macOS, Windows

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or sharing feedback, your contributions help make fast-odoo RPC better for everyone.



### Quick Development Setup

```bash
# Clone the repository
git clone https://github.com/hungdannt/fast-odoo-rpc.git
cd fast-odoo-rpc

# Install development dependencies
pip install -e ".[dev,redis]"

# Install pre-commit hooks (recommended)
pre-commit install

# Run tests
pytest

# Run quality checks
ruff check .
black .
mypy src/fast-odoo_rpc

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



## 📚 Documentation

- **[Getting Started](https://fast-odoo-rpc.readthedocs.io/getting-started/)**: Installation and basic usage
- **[User Guide](https://fast-odoo-rpc.readthedocs.io/user-guide/)**: Comprehensive feature documentation
- **[API Reference](https://fast-odoo-rpc.readthedocs.io/api/)**: Complete API documentation
- **[Migration Guide](https://fast-odoo-rpc.readthedocs.io/migration/)**: Migrating from odoorpc
- **[Examples](https://fast-odoo-rpc.readthedocs.io/examples/)**: Real-world usage examples



## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need to modernize the Odoo Python ecosystem
- Built on the shoulders of giants: `httpx`, `pydantic`, and `asyncio`
- Thanks to the OCA team for maintaining `odoorpc` and showing us what to improve
- Special thanks to all contributors and early adopters

---

**fast-odoo RPC**: Because your Odoo integrations deserve modern Python! 🐍✨

