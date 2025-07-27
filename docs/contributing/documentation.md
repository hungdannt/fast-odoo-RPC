# Documentation Guide

Comprehensive guide for contributing to Zenoo RPC documentation, including writing standards, structure, tools, and maintenance practices.

## Documentation Philosophy

Zenoo RPC documentation follows these principles:

- **User-Centric**: Written from the user's perspective with clear use cases
- **Comprehensive**: Covers all features with examples and best practices
- **Accurate**: Always up-to-date with the codebase
- **Accessible**: Clear language, good structure, and multiple formats
- **Practical**: Includes working examples and real-world scenarios

## Documentation Structure

### Current Structure

```
docs/
├── index.md                    # Main documentation homepage
├── getting-started/            # Getting started guides
│   ├── installation.md
│   ├── quickstart.md
│   └── migration.md
├── user-guide/                 # User guides and tutorials
│   ├── basic-usage.md
│   ├── advanced-features.md
│   ├── models-and-fields.md
│   ├── query-building.md
│   ├── caching.md
│   ├── batch-operations.md
│   ├── error-handling.md
│   ├── performance-tips.md
│   ├── configuration.md
│   └── best-practices.md
├── tutorials/                  # Step-by-step tutorials
│   ├── basic-crud.md
│   ├── advanced-queries.md
│   ├── batch-processing.md
│   ├── caching-strategies.md
│   └── integration-patterns.md
├── api-reference/              # Complete API documentation
│   ├── index.md
│   ├── client.md
│   ├── models/
│   ├── query/
│   ├── cache/
│   ├── batch/
│   ├── retry/
│   ├── transaction/
│   └── exceptions/
├── examples/                   # Practical examples
│   ├── index.md
│   ├── basic-examples.md
│   ├── advanced-examples.md
│   └── integration-examples.md
├── advanced/                   # Advanced topics
│   ├── architecture.md
│   ├── performance.md
│   ├── security.md
│   └── extensions.md
├── troubleshooting/            # Troubleshooting guides
│   ├── debugging.md
│   └── faq.md
└── contributing/               # Contribution guides
    ├── development.md
    ├── testing.md
    ├── documentation.md
    └── release.md
```

## Writing Standards

### Markdown Style Guide

#### Headers

```markdown
# Main Title (H1) - Only one per document

## Section Title (H2) - Main sections

### Subsection Title (H3) - Subsections

#### Detail Title (H4) - Detailed topics

##### Minor Title (H5) - Minor details (rarely used)
```

#### Code Examples

Always include working, tested code examples:

```markdown
# ✅ Good: Complete, working example
```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def example_function():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partners = await client.model(ResPartner).filter(
            is_company=True
        ).limit(10).all()
        
        for partner in partners:
            print(f"Company: {partner.name}")

# Run the example
import asyncio
asyncio.run(example_function())
```

# ❌ Avoid: Incomplete or non-working examples
```python
# This won't work without imports and setup
partners = client.search("res.partner", [])
```
```

#### Lists and Structure

```markdown
# Use numbered lists for sequential steps
1. First step with clear action
2. Second step with expected result
3. Third step with verification

# Use bullet points for non-sequential items
- Feature A: Description of feature
- Feature B: Description of feature
- Feature C: Description of feature

# Use nested lists for hierarchical information
- Main category
  - Subcategory 1
  - Subcategory 2
    - Detail A
    - Detail B
```

#### Links and References

```markdown
# Internal links (relative paths)
See [Installation Guide](../getting-started/installation.md) for setup instructions.

# API reference links
Check the [ZenooClient API](../api-reference/client.md) for complete method documentation.

# External links
Visit the [Odoo Documentation](https://www.odoo.com/documentation) for Odoo-specific information.

# Anchor links within document
Jump to [Advanced Configuration](#advanced-configuration) section.
```

### Content Guidelines

#### Writing Style

- **Clear and Concise**: Use simple, direct language
- **Active Voice**: "Create a client" instead of "A client should be created"
- **Present Tense**: "The client connects" instead of "The client will connect"
- **Consistent Terminology**: Use the same terms throughout documentation

#### Code Documentation

```python
# ✅ Good: Comprehensive docstring
async def create_partner(
    client: ZenooClient,
    partner_data: Dict[str, Any],
    validate: bool = True
) -> Dict[str, Any]:
    """Create a new partner record in Odoo.
    
    This function creates a partner record with validation and error handling.
    It supports both company and individual partner creation.
    
    Args:
        client: Authenticated ZenooClient instance
        partner_data: Dictionary containing partner information
            Required fields: name
            Optional fields: email, phone, is_company, etc.
        validate: Whether to validate data before creation (default: True)
    
    Returns:
        Dictionary containing the created partner data with ID
    
    Raises:
        ValidationError: If partner_data is invalid
        AuthenticationError: If client is not authenticated
        NetworkError: If connection to Odoo fails
    
    Example:
        >>> async with ZenooClient("localhost") as client:
        ...     await client.login("demo", "admin", "admin")
        ...     partner = await create_partner(client, {
        ...         "name": "ACME Corp",
        ...         "is_company": True,
        ...         "email": "info@acme.com"
        ...     })
        ...     print(f"Created partner ID: {partner['id']}")
        Created partner ID: 123
    
    Note:
        This function requires an authenticated client. Make sure to call
        client.login() before using this function.
    
    See Also:
        - update_partner(): Update existing partner
        - delete_partner(): Delete partner
        - ZenooClient.create(): Low-level create method
    """
    if validate:
        _validate_partner_data(partner_data)
    
    return await client.create("res.partner", partner_data)
```

#### Examples and Tutorials

Every feature should include:

1. **Basic Example**: Simple, minimal working code
2. **Advanced Example**: Real-world usage with error handling
3. **Complete Tutorial**: Step-by-step guide with explanation

```markdown
## Basic Usage

Simple partner creation:

```python
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    
    partner = await client.create("res.partner", {
        "name": "Test Company",
        "is_company": True
    })
    
    print(f"Created partner ID: {partner}")
```

## Advanced Usage

Production-ready partner creation with error handling:

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ValidationError, AuthenticationError

async def create_partner_safely(partner_data):
    """Create partner with comprehensive error handling."""
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            # Validate required fields
            if not partner_data.get("name"):
                raise ValueError("Partner name is required")
            
            # Create partner
            partner = await client.create("res.partner", partner_data)
            
            # Log success
            print(f"Successfully created partner: {partner}")
            return partner
            
    except AuthenticationError:
        print("Failed to authenticate with Odoo")
        raise
    except ValidationError as e:
        print(f"Partner data validation failed: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

# Usage
partner_data = {
    "name": "ACME Corporation",
    "is_company": True,
    "email": "info@acme.com",
    "phone": "+1-555-0100"
}

partner = await create_partner_safely(partner_data)
```

## Complete Tutorial

For a complete step-by-step tutorial, see [Partner Management Tutorial](../tutorials/partner-management.md).
```

## Documentation Tools

### MkDocs Configuration

```yaml
# mkdocs.yml
site_name: Zenoo RPC Documentation
site_description: Modern async Python library for Odoo RPC
site_url: https://zenoo-rpc.readthedocs.io/

repo_name: tuanle96/zenoo-rpc
repo_url: https://github.com/tuanle96/zenoo-rpc

theme:
  name: material
  palette:
    - scheme: default
      primary: blue
      accent: blue
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: blue
      accent: blue
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - search.share
    - content.code.copy

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            show_source: true
            show_root_heading: true
            show_root_toc_entry: false

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.tabbed:
      alternate_style: true
  - attr_list
  - md_in_html

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/quickstart.md
    - Migration: getting-started/migration.md
  - User Guide:
    - Basic Usage: user-guide/basic-usage.md
    - Advanced Features: user-guide/advanced-features.md
    - Models & Fields: user-guide/models-and-fields.md
    - Query Building: user-guide/query-building.md
    - Caching: user-guide/caching.md
    - Batch Operations: user-guide/batch-operations.md
    - Error Handling: user-guide/error-handling.md
    - Performance Tips: user-guide/performance-tips.md
    - Configuration: user-guide/configuration.md
    - Best Practices: user-guide/best-practices.md
  - Tutorials:
    - Basic CRUD: tutorials/basic-crud.md
    - Advanced Queries: tutorials/advanced-queries.md
    - Batch Processing: tutorials/batch-processing.md
    - Caching Strategies: tutorials/caching-strategies.md
    - Integration Patterns: tutorials/integration-patterns.md
  - API Reference:
    - Overview: api-reference/index.md
    - Client: api-reference/client.md
    - Models: api-reference/models/index.md
    - Query: api-reference/query/index.md
    - Cache: api-reference/cache/index.md
    - Batch: api-reference/batch/index.md
    - Retry: api-reference/retry/index.md
    - Transaction: api-reference/transaction/index.md
    - Exceptions: api-reference/exceptions/index.md
  - Examples:
    - Overview: examples/index.md
    - Basic Examples: examples/basic-examples.md
    - Advanced Examples: examples/advanced-examples.md
    - Integration Examples: examples/integration-examples.md
  - Advanced:
    - Architecture: advanced/architecture.md
    - Performance: advanced/performance.md
    - Security: advanced/security.md
    - Extensions: advanced/extensions.md
  - Troubleshooting:
    - Debugging: troubleshooting/debugging.md
    - FAQ: troubleshooting/faq.md
  - Contributing:
    - Development: contributing/development.md
    - Testing: contributing/testing.md
    - Documentation: contributing/documentation.md
    - Release: contributing/release.md
```

### Auto-Generated API Documentation

```python
# scripts/generate_api_docs.py
"""Generate API documentation from docstrings."""

import inspect
import os
from pathlib import Path
from typing import Any, Dict, List

def generate_module_docs(module_name: str, output_path: str):
    """Generate documentation for a module."""
    
    # Import module
    module = __import__(module_name, fromlist=[''])
    
    # Get all public classes and functions
    members = inspect.getmembers(module, 
        lambda x: inspect.isclass(x) or inspect.isfunction(x))
    
    # Filter public members
    public_members = [(name, obj) for name, obj in members 
                     if not name.startswith('_')]
    
    # Generate markdown
    markdown_content = f"# {module_name} API Reference\n\n"
    
    for name, obj in public_members:
        markdown_content += f"## {name}\n\n"
        
        # Get docstring
        docstring = inspect.getdoc(obj)
        if docstring:
            markdown_content += f"{docstring}\n\n"
        
        # Get signature for functions
        if inspect.isfunction(obj):
            signature = inspect.signature(obj)
            markdown_content += f"```python\n{name}{signature}\n```\n\n"
        
        # Get methods for classes
        elif inspect.isclass(obj):
            methods = inspect.getmembers(obj, inspect.ismethod)
            public_methods = [(n, m) for n, m in methods 
                            if not n.startswith('_')]
            
            for method_name, method in public_methods:
                markdown_content += f"### {method_name}\n\n"
                method_doc = inspect.getdoc(method)
                if method_doc:
                    markdown_content += f"{method_doc}\n\n"
    
    # Write to file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(markdown_content)

# Generate docs for all modules
modules = [
    ("zenoo_rpc.client", "docs/api-reference/client.md"),
    ("zenoo_rpc.models.base", "docs/api-reference/models/base.md"),
    ("zenoo_rpc.query.builder", "docs/api-reference/query/builder.md"),
    ("zenoo_rpc.cache.manager", "docs/api-reference/cache/manager.md"),
]

for module_name, output_path in modules:
    generate_module_docs(module_name, output_path)
    print(f"Generated documentation for {module_name}")
```

### Documentation Testing

```python
# tests/test_documentation.py
"""Test documentation for accuracy and completeness."""

import pytest
import re
import ast
from pathlib import Path

class TestDocumentation:
    """Test documentation quality and accuracy."""
    
    def test_code_examples_syntax(self):
        """Test that all code examples have valid Python syntax."""
        docs_dir = Path("docs")
        
        for md_file in docs_dir.rglob("*.md"):
            content = md_file.read_text()
            
            # Extract Python code blocks
            python_blocks = re.findall(
                r'```python\n(.*?)\n```', 
                content, 
                re.DOTALL
            )
            
            for i, code_block in enumerate(python_blocks):
                try:
                    # Parse the code to check syntax
                    ast.parse(code_block)
                except SyntaxError as e:
                    pytest.fail(
                        f"Syntax error in {md_file}:{i+1}: {e}\n"
                        f"Code block:\n{code_block}"
                    )
    
    def test_internal_links(self):
        """Test that internal links are valid."""
        docs_dir = Path("docs")
        
        for md_file in docs_dir.rglob("*.md"):
            content = md_file.read_text()
            
            # Extract internal links
            internal_links = re.findall(
                r'\[.*?\]\(([^http][^)]+)\)', 
                content
            )
            
            for link in internal_links:
                # Resolve relative path
                if link.startswith('../'):
                    target_path = (md_file.parent / link).resolve()
                else:
                    target_path = (md_file.parent / link).resolve()
                
                # Check if target exists
                if not target_path.exists():
                    pytest.fail(
                        f"Broken internal link in {md_file}: {link}\n"
                        f"Target does not exist: {target_path}"
                    )
    
    def test_api_reference_completeness(self):
        """Test that API reference covers all public APIs."""
        from zenoo_rpc import ZenooClient
        
        # Get all public methods
        public_methods = [
            name for name in dir(ZenooClient) 
            if not name.startswith('_')
        ]
        
        # Read API reference
        api_ref_path = Path("docs/api-reference/client.md")
        if api_ref_path.exists():
            content = api_ref_path.read_text()
            
            # Check that each public method is documented
            for method in public_methods:
                if method not in content:
                    pytest.fail(
                        f"Method {method} not documented in API reference"
                    )
```

## Documentation Maintenance

### Automated Updates

```bash
# scripts/update_docs.sh
#!/bin/bash
set -e

echo "Updating documentation..."

# Generate API documentation from code
python scripts/generate_api_docs.py

# Update version numbers
VERSION=$(python -c "import zenoo_rpc; print(zenoo_rpc.__version__)")
sed -i "s/version: .*/version: $VERSION/" mkdocs.yml

# Build documentation
mkdocs build

# Test documentation
pytest tests/test_documentation.py

echo "Documentation updated successfully!"
```

### Review Checklist

Before submitting documentation changes:

- [ ] All code examples are tested and working
- [ ] Internal links are valid
- [ ] External links are accessible
- [ ] Spelling and grammar are correct
- [ ] Content follows style guide
- [ ] API changes are reflected in documentation
- [ ] Examples include error handling
- [ ] Screenshots are up-to-date (if applicable)

### Documentation Workflow

1. **Plan**: Outline the documentation structure
2. **Write**: Create content following style guide
3. **Review**: Self-review for clarity and accuracy
4. **Test**: Run documentation tests
5. **Build**: Generate documentation site
6. **Preview**: Review generated documentation
7. **Submit**: Create pull request with changes

## Best Practices

### 1. Keep Documentation Current
- Update docs with every API change
- Review and update examples regularly
- Remove outdated information promptly

### 2. Write for Your Audience
- Beginners: Step-by-step instructions with explanations
- Advanced users: Concise reference with examples
- Contributors: Detailed technical information

### 3. Use Consistent Structure
- Follow established patterns
- Use standard section headings
- Maintain consistent code style

### 4. Include Working Examples
- Test all code examples
- Show complete, runnable code
- Include error handling in advanced examples

### 5. Cross-Reference Related Content
- Link to related documentation
- Reference API documentation
- Connect tutorials to user guides

## Next Steps

- Review [Development Guide](development.md) for code documentation standards
- Check [Testing Guide](testing.md) for documentation testing
- Explore [Release Process](release.md) for documentation release workflow
- Learn about MkDocs and Material theme for advanced customization
