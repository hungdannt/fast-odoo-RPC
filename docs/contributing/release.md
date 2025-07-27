# Release Process

Comprehensive guide for managing Zenoo RPC releases, including versioning, changelog management, testing, and deployment procedures.

## Release Philosophy

Zenoo RPC follows semantic versioning and maintains high-quality releases:

- **Semantic Versioning**: MAJOR.MINOR.PATCH format
- **Quality Assurance**: Comprehensive testing before release
- **Documentation**: Complete changelog and migration guides
- **Backward Compatibility**: Careful handling of breaking changes
- **Community Communication**: Clear release announcements

## Versioning Strategy

### Semantic Versioning (SemVer)

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

Examples:
- 1.0.0        # Major release
- 1.1.0        # Minor release (new features)
- 1.1.1        # Patch release (bug fixes)
- 1.2.0-alpha.1  # Pre-release
- 1.2.0-beta.2   # Beta release
- 1.2.0-rc.1     # Release candidate
```

### Version Increment Rules

- **MAJOR**: Breaking changes, API incompatibilities
- **MINOR**: New features, backward-compatible changes
- **PATCH**: Bug fixes, security patches, documentation updates

### Pre-release Versions

- **Alpha**: Early development, unstable features
- **Beta**: Feature-complete, testing phase
- **RC (Release Candidate)**: Final testing before release

## Release Types

### Patch Release (1.0.x)

**When to use:**
- Bug fixes
- Security patches
- Documentation updates
- Performance improvements (non-breaking)

**Example changes:**
```python
# Bug fix: Handle connection timeout properly
async def connect(self, timeout: float = 30.0):
    try:
        await self._establish_connection(timeout)
    except asyncio.TimeoutError:
        raise NetworkError(f"Connection timeout after {timeout}s")
```

### Minor Release (1.x.0)

**When to use:**
- New features
- New API methods
- Backward-compatible enhancements
- Deprecation warnings

**Example changes:**
```python
# New feature: Batch operations
class ZenooClient:
    async def batch_create(self, model: str, records: List[Dict]) -> List[int]:
        """Create multiple records in a single batch operation."""
        # Implementation
        pass
    
    # Deprecated method with warning
    async def bulk_create(self, model: str, records: List[Dict]) -> List[int]:
        """Deprecated: Use batch_create instead."""
        warnings.warn(
            "bulk_create is deprecated, use batch_create instead",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.batch_create(model, records)
```

### Major Release (x.0.0)

**When to use:**
- Breaking API changes
- Architectural changes
- Removal of deprecated features
- Major dependency updates

**Example changes:**
```python
# Breaking change: Async-only API
# Before (v0.x): Sync and async support
class ZenooClient:
    def search(self, model: str, domain: list) -> list:
        # Sync method
        pass
    
    async def search_async(self, model: str, domain: list) -> list:
        # Async method
        pass

# After (v1.0): Async-only
class ZenooClient:
    async def search(self, model: str, domain: list) -> list:
        # Only async method
        pass
```

## Release Workflow

### 1. Pre-Release Planning

```bash
# Create release branch
git checkout -b release/1.2.0
git push origin release/1.2.0

# Update version number
# Edit pyproject.toml, __init__.py, etc.
```

### 2. Version Management

```python
# src/zenoo_rpc/__init__.py
__version__ = "1.2.0"

# Update in pyproject.toml
[project]
version = "1.2.0"

# Update in documentation
# docs/conf.py or mkdocs.yml
version = "1.2.0"
```

### 3. Changelog Generation

```markdown
# CHANGELOG.md

## [1.2.0] - 2024-01-15

### Added
- Batch operations support for improved performance
- Redis cache backend with connection pooling
- Retry mechanisms with exponential backoff
- Transaction management with savepoints

### Changed
- Improved error handling with custom exception hierarchy
- Enhanced query builder with type safety
- Updated dependencies to latest versions

### Deprecated
- `bulk_create()` method (use `batch_create()` instead)
- `simple_cache` configuration (use `cache_manager` instead)

### Removed
- Support for Python 3.7 (EOL)
- Legacy sync API methods

### Fixed
- Connection timeout handling in transport layer
- Memory leak in connection pooling
- Race condition in cache invalidation

### Security
- Updated httpx to fix CVE-2023-XXXX
- Improved input validation for SQL injection prevention

## [1.1.2] - 2024-01-01

### Fixed
- Fixed authentication error handling
- Resolved cache key collision issue

## [1.1.1] - 2023-12-15

### Fixed
- Fixed connection pool cleanup on client close
- Resolved type hints for Python 3.8 compatibility
```

### 4. Testing Checklist

```bash
# Run comprehensive test suite
pytest tests/ -v --cov=zenoo_rpc

# Run integration tests
pytest tests/integration/ -v

# Run performance tests
pytest tests/performance/ -v

# Test with different Python versions
tox

# Test installation from source
pip install -e .
python -c "import zenoo_rpc; print(zenoo_rpc.__version__)"

# Test documentation build
mkdocs build
mkdocs serve

# Test package build
python -m build
twine check dist/*
```

### 5. Documentation Updates

```bash
# Update API documentation
python scripts/generate_api_docs.py

# Update migration guide
# docs/getting-started/migration.md

# Update examples
# docs/examples/

# Build and test documentation
mkdocs build
mkdocs serve
```

### 6. Release Creation

```bash
# Tag the release
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0

# Create GitHub release
gh release create v1.2.0 \
  --title "Zenoo RPC v1.2.0" \
  --notes-file RELEASE_NOTES.md \
  --draft

# Build and upload to PyPI
python -m build
twine upload dist/*
```

## Automated Release Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev,redis]"
    
    - name: Run tests
      run: |
        pytest --cov=zenoo_rpc --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Check package
      run: twine check dist/*
    
    - name: Upload to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
    
    - name: Create GitHub Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        body_path: RELEASE_NOTES.md
        draft: false
        prerelease: false

  docs:
    needs: build
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
        pip install mkdocs mkdocs-material
    
    - name: Build documentation
      run: mkdocs build
    
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./site
```

### Release Scripts

```bash
# scripts/release.sh
#!/bin/bash
set -e

# Get version from command line
VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.2.0"
    exit 1
fi

echo "Preparing release $VERSION..."

# Update version in files
sed -i "s/__version__ = .*/__version__ = \"$VERSION\"/" src/zenoo_rpc/__init__.py
sed -i "s/version = .*/version = \"$VERSION\"/" pyproject.toml

# Update changelog
python scripts/update_changelog.py $VERSION

# Run tests
echo "Running tests..."
pytest tests/ -v

# Build documentation
echo "Building documentation..."
mkdocs build

# Build package
echo "Building package..."
python -m build

# Check package
echo "Checking package..."
twine check dist/*

echo "Release $VERSION prepared successfully!"
echo "Next steps:"
echo "1. Review changes: git diff"
echo "2. Commit changes: git commit -am 'Prepare release $VERSION'"
echo "3. Create tag: git tag -a v$VERSION -m 'Release version $VERSION'"
echo "4. Push: git push origin main --tags"
```

```python
# scripts/update_changelog.py
#!/usr/bin/env python3
"""Update changelog for new release."""

import sys
import re
from datetime import datetime
from pathlib import Path

def update_changelog(version: str):
    """Update CHANGELOG.md with new version."""
    changelog_path = Path("CHANGELOG.md")
    
    if not changelog_path.exists():
        print("CHANGELOG.md not found")
        return
    
    content = changelog_path.read_text()
    
    # Find unreleased section
    unreleased_pattern = r"## \[Unreleased\](.*?)(?=## \[|\Z)"
    match = re.search(unreleased_pattern, content, re.DOTALL)
    
    if not match:
        print("No [Unreleased] section found")
        return
    
    unreleased_content = match.group(1).strip()
    
    if not unreleased_content:
        print("No changes in [Unreleased] section")
        return
    
    # Create new release section
    today = datetime.now().strftime("%Y-%m-%d")
    new_section = f"## [{version}] - {today}\n\n{unreleased_content}\n\n"
    
    # Replace unreleased section
    new_content = content.replace(
        match.group(0),
        f"## [Unreleased]\n\n{new_section}"
    )
    
    # Write updated changelog
    changelog_path.write_text(new_content)
    print(f"Updated CHANGELOG.md for version {version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_changelog.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    update_changelog(version)
```

## Release Communication

### Release Notes Template

```markdown
# Zenoo RPC v1.2.0 Release Notes

We're excited to announce the release of Zenoo RPC v1.2.0! This release brings significant performance improvements, new features, and enhanced developer experience.

## 🚀 What's New

### Batch Operations
Efficiently process large datasets with new batch operation support:

```python
async with client.batch_context() as batch:
    batch.create("res.partner", partner_data)
    batch.update("res.partner", update_data)
    results = await batch.execute()
```

### Redis Cache Backend
Enterprise-grade caching with Redis support:

```python
await client.setup_cache_manager(
    backend="redis",
    url="redis://localhost:6379/0"
)
```

### Enhanced Error Handling
Improved error messages and custom exception hierarchy for better debugging.

## 📈 Performance Improvements

- 5x faster batch operations
- 3x improved query performance with caching
- Reduced memory usage by 40%

## 🔧 Breaking Changes

- Removed support for Python 3.7
- `bulk_create()` method deprecated (use `batch_create()`)
- Async-only API (removed sync methods)

## 📚 Migration Guide

See our [Migration Guide](https://zenoo-rpc.readthedocs.io/en/latest/getting-started/migration/) for detailed upgrade instructions.

## 🙏 Contributors

Thanks to all contributors who made this release possible:
- @contributor1
- @contributor2
- @contributor3

## 📦 Installation

```bash
pip install --upgrade zenoo-rpc
```

For the full changelog, see [CHANGELOG.md](CHANGELOG.md).
```

### Community Announcements

```markdown
# Social Media Announcement

🎉 Zenoo RPC v1.2.0 is here! 

✨ New batch operations for 5x performance
🚀 Redis caching support
🔧 Enhanced error handling
📚 Comprehensive documentation

Upgrade today: pip install --upgrade zenoo-rpc

#Python #Odoo #AsyncProgramming #OpenSource
```

## Post-Release Tasks

### 1. Verify Release

```bash
# Test PyPI installation
pip install zenoo-rpc==$VERSION
python -c "import zenoo_rpc; print(zenoo_rpc.__version__)"

# Test documentation deployment
curl -I https://zenoo-rpc.readthedocs.io/

# Check GitHub release
gh release view v$VERSION
```

### 2. Update Development

```bash
# Merge release branch
git checkout main
git merge release/$VERSION
git branch -d release/$VERSION

# Start next development cycle
git checkout -b develop
# Update version to next dev version
# e.g., 1.2.1-dev or 1.3.0-dev
```

### 3. Monitor Release

- Monitor PyPI download statistics
- Watch for bug reports and issues
- Track community feedback
- Update documentation based on feedback

## Hotfix Process

For critical bugs requiring immediate fixes:

```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/1.2.1

# Make minimal fix
# Update version to 1.2.1
# Update changelog

# Test thoroughly
pytest tests/

# Release hotfix
git tag v1.2.1
git push origin v1.2.1

# Merge back to main and develop
git checkout main
git merge hotfix/1.2.1
git checkout develop
git merge hotfix/1.2.1
```

## Best Practices

### 1. Release Planning
- Plan releases in advance
- Communicate breaking changes early
- Maintain backward compatibility when possible
- Follow semantic versioning strictly

### 2. Quality Assurance
- Comprehensive testing before release
- Documentation review and updates
- Performance regression testing
- Security vulnerability scanning

### 3. Communication
- Clear release notes
- Migration guides for breaking changes
- Community announcements
- Responsive support for issues

### 4. Automation
- Automated testing pipelines
- Automated documentation deployment
- Automated package publishing
- Automated changelog generation

## Next Steps

- Review [Development Guide](development.md) for contribution workflow
- Check [Testing Guide](testing.md) for release testing procedures
- Explore [Documentation Guide](documentation.md) for documentation updates
- Learn about project governance and maintenance procedures
