---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: 'enhancement'
assignees: ''

---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Use Case**
Describe the specific use case for this feature:

```python
# Example of how you would like to use this feature
from zenoo_rpc import ZenooClient

async def example_usage():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Your proposed API usage
        result = await client.new_feature_method()
```

**API Design (if applicable)**
If you have ideas about the API design, please share them:

```python
class ZenooClient:
    async def proposed_method(
        self,
        param1: str,
        param2: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Proposed method description."""
        pass
```

**Impact**
Describe the impact this feature would have:
- [ ] Performance improvement
- [ ] Developer experience enhancement
- [ ] New functionality
- [ ] Better error handling
- [ ] Improved compatibility
- [ ] Other: ___________

**Priority**
How important is this feature to you?
- [ ] Critical - blocking my work
- [ ] High - would significantly improve my workflow
- [ ] Medium - nice to have
- [ ] Low - minor improvement

**Additional context**
Add any other context, screenshots, or examples about the feature request here.

**Related Issues**
Link any related issues or discussions:
- Related to #
- Depends on #
- Blocks #

**Checklist**
- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have provided a clear use case for this feature
- [ ] I have considered alternative solutions
- [ ] I have described the expected API (if applicable)
- [ ] I have indicated the priority and impact