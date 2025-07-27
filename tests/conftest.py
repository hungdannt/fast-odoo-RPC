import pytest
import asyncio
from typing import Dict, Any
import aiohttp
from aiohttp import web


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmpdir_factory(tmp_path_factory):
    """Provide tmpdir factory for tests."""
    return tmp_path_factory


@pytest.fixture
def monkeypatch(monkeypatch):
    """Provide monkeypatch fixture."""
    return monkeypatch


@pytest.fixture
async def dummy_httpx_server():
    """Create a dummy HTTP server for testing."""
    app = web.Application()

    async def handle_request(request):
        return web.json_response({"status": "ok", "method": request.method})

    app.router.add_route("*", "/{path:.*}", handle_request)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://localhost:{port}"

    yield base_url

    await runner.cleanup()
