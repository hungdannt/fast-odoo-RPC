---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: 'bug'
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Code Example**
If applicable, add a minimal code example to help explain your problem:

```python
from zenoo_rpc import ZenooClient

async def reproduce_bug():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        # Your code that reproduces the bug
        result = await client.search("res.partner", [])
```

**Error Message**
If applicable, add the full error message and traceback:

```
Traceback (most recent call last):
  File "example.py", line 10, in <module>
    result = await client.search("res.partner", [])
  ...
Error: Description of the error
```

**Environment (please complete the following information):**
 - OS: [e.g. Ubuntu 22.04, macOS 13.0, Windows 11]
 - Python version: [e.g. 3.11.0]
 - Zenoo RPC version: [e.g. 1.0.0]
 - Odoo version: [e.g. 18.0] (currently only 18.0 is tested)
 - Other relevant packages: [e.g. httpx 0.24.1, pydantic 2.0.0]

**Additional context**
Add any other context about the problem here.

**Checklist**
- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have provided a minimal code example that reproduces the issue
- [ ] I have included the full error message and traceback
- [ ] I have specified my environment details
- [ ] I have checked the documentation and FAQ