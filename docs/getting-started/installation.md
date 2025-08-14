# Installation Guide

This guide will help you install Zenoo RPC and its dependencies for different use cases.

## Requirements

- **Python 3.8+** (Python 3.11+ recommended for best performance)
- **Odoo 18.0** (currently tested version)
- **Other Odoo versions** (12.0-17.0) - compatibility not yet verified

## Basic Installation

### Install from PyPI

```bash
pip install zenoo-rpc
```

This installs the core dependencies:
- `httpx>=0.25.0` - Modern async HTTP client
- `h2>=4.0.0` - HTTP/2 support for better performance
- `pydantic>=2.0.0` - Data validation and type safety
- `typing-extensions>=4.0.0` - Enhanced type hints

### Verify Installation

```python
import zenoo_rpc
print(zenoo_rpc.__version__)
```

## Optional Dependencies

### Redis Support

For production caching with Redis:

```bash
pip install zenoo-rpc[redis]
```

This adds:
- `redis[hiredis]>=5.0.0` - Redis client with high-performance parser

### Development Dependencies

For development and testing:

```bash
pip install zenoo-rpc[dev]
```

This includes:
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `pytest-cov>=4.0.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `ruff>=0.1.0` - Fast linting
- `mypy>=1.0.0` - Static type checking
- `pre-commit>=3.0.0` - Git hooks

### Documentation Dependencies

For building documentation:

```bash
pip install zenoo-rpc[docs]
```

This includes:
- `mkdocs>=1.5.0` - Documentation generator
- `mkdocs-material>=9.0.0` - Material theme
- `mkdocstrings[python]>=0.23.0` - API documentation

### All Dependencies

Install everything:

```bash
pip install zenoo-rpc[dev,redis,docs]
```

## Installation Methods

### Using pip

Standard installation:
```bash
pip install zenoo-rpc
```

Upgrade to latest version:
```bash
pip install --upgrade zenoo-rpc
```

Install specific version:
```bash
pip install zenoo-rpc==0.1.7
```

### Using Poetry

Add to your `pyproject.toml`:
```toml
[tool.poetry.dependencies]
zenoo-rpc = "^0.1.7"

# Optional dependencies
redis = {extras = ["hiredis"], version = "^5.0.0", optional = true}
```

Then install:
```bash
poetry install
```

### Using pipenv

```bash
pipenv install zenoo-rpc
```

With optional dependencies:
```bash
pipenv install zenoo-rpc[redis]
```

### From Source

For the latest development version:

```bash
git clone https://github.com/tuanle96/zenoo-rpc.git
cd zenoo-rpc
pip install -e .
```

With development dependencies:
```bash
pip install -e .[dev,redis]
```

## Docker Installation

### Using Official Python Image

```dockerfile
FROM python:3.11-slim

# Install Zenoo RPC
RUN pip install zenoo-rpc[redis]

# Copy your application
COPY . /app
WORKDIR /app

CMD ["python", "main.py"]
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  app:
    build: .
    environment:
      - ODOO_HOST=odoo
      - ODOO_PORT=8069
      - REDIS_URL=redis://redis:6379
    depends_on:
      - odoo
      - redis
  
  odoo:
    image: odoo:17
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Virtual Environment Setup

### Using venv

```bash
# Create virtual environment
python -m venv zenoo-env

# Activate (Linux/Mac)
source zenoo-env/bin/activate

# Activate (Windows)
zenoo-env\Scripts\activate

# Install Zenoo RPC
pip install zenoo-rpc[redis]
```

### Using conda

```bash
# Create environment
conda create -n zenoo python=3.11

# Activate environment
conda activate zenoo

# Install Zenoo RPC
pip install zenoo-rpc[redis]
```

## Troubleshooting

### Common Issues

**ImportError: No module named 'zenoo_rpc'**
- Ensure you're in the correct virtual environment
- Verify installation: `pip list | grep zenoo-rpc`

**SSL Certificate Issues**
```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org zenoo-rpc
```

**Permission Denied (Linux/Mac)**
```bash
pip install --user zenoo-rpc
```

**Outdated pip**
```bash
pip install --upgrade pip
pip install zenoo-rpc
```

### Version Conflicts

Check for conflicts:
```bash
pip check
```

Resolve conflicts:
```bash
pip install --upgrade zenoo-rpc httpx pydantic
```

### Performance Issues

For better performance, install with optimized dependencies:
```bash
pip install zenoo-rpc[redis]
pip install uvloop  # Linux/Mac only
```

## Next Steps

After installation, continue with:

1. [Quick Start Tutorial](quickstart.md) - Get up and running in 5 minutes
2. [Migration Guide](migration.md) - Migrate from odoorpc
3. [Basic CRUD Tutorial](../tutorials/basic-crud.md) - Learn the fundamentals

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](../troubleshooting/common-issues.md)
2. Search [GitHub Issues](https://github.com/tuanle96/zenoo-rpc/issues)
3. Ask questions in [GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)
4. Read the [FAQ](../troubleshooting/faq.md)
