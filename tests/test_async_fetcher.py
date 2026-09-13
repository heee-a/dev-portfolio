"""异步采集器测试：本地 TestServer，零外部依赖。"""

import sys
from pathlib import Path

import pytest
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software" / "async_fetcher"))

from async_fetcher import AsyncFetcher  # noqa: E402


@pytest.fixture()
async def server(tmp_path):
    async def ok_handler(request):
        return web.Response(text=f"page:{request.query.get('p', '0')}")

    def boom_handler(request):
        return web.Response(status=500, text="server error")

    app = web.Application()
    app.router.add_get("/ok", ok_handler)
    app.router.add_get("/boom", boom_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    yield f"http://127.0.0.1:{port}", tmp_path
    await runner.cleanup()


@pytest.mark.asyncio
async def test_fetch_writes_cache(server):
    base, tmp = server
    f = AsyncFetcher(cache_dir=tmp / "cache", concurrency=3, min_interval=0)
    async with __import__("aiohttp").ClientSession() as session:
        text = await f.get_text(session, f"{base}/ok?p=1")
    assert text == "page:1"
    assert len(list((tmp / "cache").glob("*.json"))) == 1


@pytest.mark.asyncio
async def test_fetch_500_raises_after_retries(server):
    base, tmp = server
    f = AsyncFetcher(cache_dir=tmp / "cache", concurrency=3, min_interval=0,
                     max_retries=1)
    async with __import__("aiohttp").ClientSession() as session:
        with pytest.raises(RuntimeError):
            await f.get_text(session, f"{base}/boom")
