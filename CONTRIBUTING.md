# Contributing to Zenoo-RPC

Thank you for your interest in contributing to Zenoo-RPC! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A virtual environment tool (venv, conda, etc.)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/zenoo-rpc.git
   cd zenoo-rpc
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e .[dev]
   ```

4. **Install pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

## 🧪 Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage
```bash
pytest --cov=src/zenoo-rpc --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_client.py -v
```

### Run tests for specific functionality
```bash
pytest -k "test_authentication" -v
```

## 🎯 Code Style and Quality

We use several tools to maintain code quality:

### Formatting
```bash
black src/ tests/ examples/
```

### Linting
```bash
ruff check src/ tests/ examples/
```

### Type Checking
```bash
mypy src/zenoo-rpc
```

### Run all quality checks
```bash
# Format code
black .

# Check linting
ruff check .

# Type checking
mypy src/zenoo-rpc

# Run tests
pytest
```

## 📝 Code Guidelines

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep line length to 88 characters (Black default)

### Async Code
- Use `async/await` syntax consistently
- Prefer `async with` for resource management
- Use `AsyncMock` for testing async functions

### Error Handling
- Create specific exception types for different error conditions
- Always provide meaningful error messages
- Include context information in exceptions when helpful

### Testing
- Write tests for all new functionality
- Aim for high test coverage (>90%)
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies

## 🏗️ Architecture Guidelines

### Project Structure
```
src/zenoo-rpc/
├── client.py              # Main client interface
├── transport/             # HTTP transport layer
├── models/                # Pydantic models (future)
├── query/                 # Query builder (future)
├── cache/                 # Caching layer (future)
├── exceptions/            # Exception hierarchy
├── transaction/           # Transaction management (future)
└── utils/                 # Utilities and helpers
```

### Design Principles
1. **Async-first**: All I/O operations should be async
2. **Type safety**: Use Pydantic and type hints extensively
3. **Developer experience**: API should be intuitive and well-documented
4. **Performance**: Minimize RPC calls, use caching where appropriate
5. **Error handling**: Provide structured, meaningful exceptions

## 🐛 Reporting Issues

### Bug Reports
When reporting bugs, please include:
- Python version
- Zenoo-RPC version
- Odoo server version (if applicable)
- Minimal code example that reproduces the issue
- Full error traceback
- Expected vs actual behavior

### Feature Requests
For feature requests, please:
- Describe the use case clearly
- Explain why the feature would be valuable
- Provide examples of how it would be used
- Consider backward compatibility

## 🔄 Pull Request Process

### Before Submitting
1. **Create an issue** first to discuss the change
2. **Fork the repository** and create a feature branch
3. **Write tests** for your changes
4. **Update documentation** if needed
5. **Run all quality checks** locally

### Pull Request Guidelines
1. **Clear title and description**
   - Use descriptive titles
   - Reference related issues
   - Explain what changes were made and why

2. **Small, focused changes**
   - Keep PRs focused on a single feature/fix
   - Break large changes into smaller PRs

3. **Tests and documentation**
   - Include tests for new functionality
   - Update docstrings and README if needed
   - Ensure all tests pass

4. **Code quality**
   - Follow the code style guidelines
   - Pass all linting and type checking
   - Maintain or improve test coverage

### Review Process
1. Automated checks must pass
2. At least one maintainer review required
3. Address review feedback promptly
4. Squash commits before merging (if requested)

## 🎯 Development Roadmap

### Phase 1: Core Foundation ✅
- [x] Async HTTP transport with httpx
- [x] Exception hierarchy and error handling
- [x] Session management and authentication
- [x] Basic RPC operations

### Phase 2: Pydantic Models and Query Builder (In Progress)
- [ ] Pydantic model system
- [ ] Fluent query builder
- [ ] Lazy loading for relationships
- [ ] Model registry and introspection

### Phase 3: Advanced Features (Planned)
- [ ] Transaction management
- [ ] Intelligent caching layer
- [ ] Batch operations
- [ ] Connection pooling and retry logic

### Phase 4: Documentation and Community (Planned)
- [ ] Comprehensive documentation
- [ ] Migration guide from odoorpc
- [ ] Performance benchmarks
- [ ] Community examples

## 💬 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check the docs for detailed information

## 📄 License

By contributing to Zenoo-RPC, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Zenoo-RPC! 🎉
