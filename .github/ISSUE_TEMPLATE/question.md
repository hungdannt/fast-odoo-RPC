---
name: Question
about: Ask a question about usage or get help
title: '[QUESTION] '
labels: 'question'
assignees: ''

---

**What would you like to know?**
A clear and concise description of your question.

**Context**
Provide context about what you're trying to achieve:

**Code Example (if applicable)**
If your question is about code, please provide a minimal example:

```python
from zenoo_rpc import ZenooClient

async def my_code():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # What I'm trying to do
        result = await client.search("res.partner", [])
        
        # What I want to achieve
        # ...
```

**What have you tried?**
Describe what you've already attempted:

**Environment (if relevant):**
 - OS: [e.g. Ubuntu 22.04]
 - Python version: [e.g. 3.11.0]
 - Zenoo RPC version: [e.g. 1.0.0]
 - Odoo version: [e.g. 18.0] (currently only 18.0 is tested)

**Documentation Checked**
Which documentation have you already consulted?
- [ ] [Getting Started Guide](https://zenoo-rpc.readthedocs.io/en/latest/getting-started/)
- [ ] [User Guide](https://zenoo-rpc.readthedocs.io/en/latest/user-guide/)
- [ ] [API Reference](https://zenoo-rpc.readthedocs.io/en/latest/api-reference/)
- [ ] [Examples](https://zenoo-rpc.readthedocs.io/en/latest/examples/)
- [ ] [FAQ](https://zenoo-rpc.readthedocs.io/en/latest/troubleshooting/faq/)
- [ ] [Troubleshooting Guide](https://zenoo-rpc.readthedocs.io/en/latest/troubleshooting/debugging/)

**Additional context**
Add any other context about your question here.

**Checklist**
- [ ] I have searched existing issues and discussions
- [ ] I have checked the relevant documentation
- [ ] I have provided sufficient context for my question
- [ ] I have included code examples where applicable