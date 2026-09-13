"""异步采集器：asyncio + aiohttp + 信号量并发限速 + 磁盘缓存 + 重试。

与同步版 Fetcher（data-portfolio/datap）的架构对比见 bench.py 的实测数据。

要点：
- asyncio.Semaphore 控制并发上限（礼貌采集的前提）；
- 每请求最小间隔由"令牌节流"实现：进入信号量前先排队；
- 429/5xx 指数退避重试；磁盘缓存与同步版同构（同 URL 只请求一次）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

import aiohttp


class AsyncFetcher:
    def __init__(self, cache_dir: str | Path = ".cache",
                 concurrency: int = 5, min_interval: float = 0.1,
                 max_retries: int = 3, timeout: float = 30.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(concurrency)
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._last = 0.0
        self._interval_lock = asyncio.Lock()

    def _cache_path(self, url: str) -> Path:
        h = hashlib.sha1(url.encode()).hexdigest()[:20]
        return self.cache_dir / f"{h}.json"

    async def _throttle(self) -> None:
        async with self._interval_lock:               # 全局间隔，而非每协程独立
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()

    async def get_text(self, session: aiohttp.ClientSession, url: str,
                       refresh: bool = False) -> str:
        cache = self._cache_path(url)
        if cache.exists() and not refresh:
            return cache.read_text(encoding="utf-8")

        err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            async with self.semaphore:
                await self._throttle()
                try:
                    async with session.get(url, timeout=self.timeout) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            cache.write_text(text, encoding="utf-8")
                            return text
                        if resp.status == 429:
                            retry_after = float(resp.headers.get("Retry-After") or 61)
                            await asyncio.sleep(retry_after)
                            err = RuntimeError("429")
                            continue
                        if resp.status >= 500:
                            await asyncio.sleep(2 ** attempt)
                            err = RuntimeError(f"{resp.status}: {url}")
                            continue
                        resp.raise_for_status()
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    err = e
                    await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"重试 {self.max_retries} 次后仍失败: {url}") from err

    async def fetch_many(self, urls: list[str]) -> dict[str, str]:
        """并发抓取一组 URL；单个失败不影响其他（结果中该 URL 缺失）。"""
        async with aiohttp.ClientSession(
                headers={"User-Agent": "data-portfolio-async/0.1"}) as session:
            results = await asyncio.gather(
                *(self.get_text(session, u) for u in urls),
                return_exceptions=True)
        out = {}
        for url, res in zip(urls, results):
            if isinstance(res, Exception):
                print(f"  [失败] {url}: {res}")
            else:
                out[url] = res
        return out
