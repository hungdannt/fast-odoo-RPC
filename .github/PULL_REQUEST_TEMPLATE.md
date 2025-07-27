## Description

Brief description of the changes in this PR.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Test improvements
- [ ] CI/CD improvements

## Related Issues

- Fixes #(issue number)
- Related to #(issue number)
- Part of #(issue number)

## Changes Made

Detailed description of the changes:

### Added
- New feature X
- New method Y
- New documentation Z

### Changed
- Modified behavior of X
- Updated Y to improve Z
- Refactored A for better B

### Removed
- Deprecated method X
- Unused code Y
- Outdated documentation Z

### Fixed
- Bug in X that caused Y
- Memory leak in Z
- Race condition in A

## Code Examples

If applicable, provide examples of the new functionality:

```python
# Before (if applicable)
old_result = await client.old_method()

# After
new_result = await client.new_method()
```

## Testing

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Performance tests added/updated
- [ ] Documentation tests added/updated

### Test Results
```bash
# Paste test results here
pytest tests/ -v
# ========================= test session starts =========================
# collected X items
# tests/test_example.py::test_new_feature PASSED
# ========================= X passed in Y.YYs =========================
```

### Manual Testing
Describe any manual testing performed:

1. Tested with Odoo 18.0 (currently supported version)
2. Verified performance improvements
3. Checked backward compatibility

## Documentation

- [ ] Code is self-documenting with clear variable names and comments
- [ ] Docstrings added/updated for new/modified functions
- [ ] Type hints added/updated
- [ ] Documentation updated (if applicable)
- [ ] Examples updated (if applicable)
- [ ] Changelog updated

## Performance Impact

- [ ] No performance impact
- [ ] Performance improvement (describe below)
- [ ] Potential performance regression (describe below and justify)

**Performance Details:**
<!-- Describe performance impact, include benchmarks if applicable -->

## Breaking Changes

- [ ] No breaking changes
- [ ] Breaking changes (describe below)

**Breaking Change Details:**
<!-- Describe breaking changes and migration path -->

## Backward Compatibility

- [ ] Fully backward compatible
- [ ] Backward compatible with deprecation warnings
- [ ] Not backward compatible (breaking change)

## Security Considerations

- [ ] No security implications
- [ ] Security improvement
- [ ] Potential security impact (describe below)

**Security Details:**
<!-- Describe security implications -->

## Checklist

### Code Quality
- [ ] Code follows the project's coding standards
- [ ] Code is properly formatted (black, isort)
- [ ] Code passes linting (flake8, mypy)
- [ ] No unnecessary debug prints or comments
- [ ] Error handling is appropriate

### Testing
- [ ] All tests pass locally
- [ ] New tests cover the changes
- [ ] Test coverage is maintained or improved
- [ ] Integration tests pass (if applicable)

### Documentation
- [ ] Code is well-documented
- [ ] Public APIs have docstrings
- [ ] Type hints are complete
- [ ] Documentation builds without errors

### Review
- [ ] Self-review completed
- [ ] Ready for review
- [ ] Addressed all review comments (if re-submitting)

## Additional Notes

Any additional information that reviewers should know:

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## Deployment Notes

<!-- Any special deployment considerations -->

---

**For Reviewers:**

### Review Checklist
- [ ] Code quality and style
- [ ] Test coverage and quality
- [ ] Documentation completeness
- [ ] Performance impact
- [ ] Security implications
- [ ] Backward compatibility
- [ ] API design (if applicable)

### Review Comments
<!-- Reviewers: Add your comments here -->