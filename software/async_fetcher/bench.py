"""同步 vs 异步采集的实测性能对比（目标：books.toscrape.com，礼貌限速）。

公平性设计（面试可讲）：
- 相同的 20 个目录页、相同的礼貌约束：同步 0.25s 全局间隔；
  异步 5 并发 + 0.05s 全局间隔（异步的总请求速率上限略高，但同属礼貌范围）；
- 两者都冷缓存启动、只统计网络耗时；
- 结论以实测为准写入 README——不是"异步一定快"的口号。

运行: python bench.py
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from async_fetcher import AsyncFetcher
from datap.fetching import Fetcher

PAGES = 20
URLS = [f"https://books.toscrape.com/catalogue/page-{p}.html"
        for p in range(1, PAGES + 1)]


def bench_sync() -> float:
    f = Fetcher(cache_dir=Path(".cache_sync"), min_interval=0.25, max_retries=3)
    t0 = time.perf_counter()
    for url in URLS:
        f.get_text(url)
    return time.perf_counter() - t0


async def bench_async() -> float:
    f = AsyncFetcher(cache_dir=Path(".cache_async"), concurrency=5,
                     min_interval=0.05)
    t0 = time.perf_counter()
    await f.fetch_many(URLS)
    return time.perf_counter() - t0


def main() -> None:
    print(f"目标: toscrape {PAGES} 个目录页（礼貌限速，冷缓存）")
    t_sync = bench_sync()
    print(f"同步 Fetcher:      {t_sync:.2f}s")
    t_async = asyncio.run(bench_async())
    print(f"异步 AsyncFetcher: {t_async:.2f}s")
    speedup = t_sync / t_async
    print(f"加速比: {speedup:.1f}x")
    (Path(__file__).parent / "bench_result.txt").write_text(
        "\n".join([f"sync={t_sync:.2f}s", f"async={t_async:.2f}s",
                   f"speedup={speedup:.1f}x"]), encoding="utf-8")
    print("结果已写入 bench_result.txt")


if __name__ == "__main__":
    main()
