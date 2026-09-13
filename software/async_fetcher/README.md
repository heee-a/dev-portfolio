# 异步采集器：asyncio + aiohttp，实测 3.6× 加速

同步采集基座（data-portfolio/datap）的异步对照实现，附带**同条件实测
性能对比**：toscrape 20 页、双方均礼貌限速、冷缓存——

```
同步 Fetcher:      30.22s
异步 AsyncFetcher:  8.35s
加速比: 3.6x
```

## 架构要点

- **asyncio.Semaphore(5)**：并发上限，礼貌采集的前提；
- **全局令牌间隔**：`asyncio.Lock` 保护的共享"上次请求时间"——所有协程
  共享一个节奏，而不是每协程各睡各的（常见的错误实现）；
- **429/5xx 退避**：尊重 Retry-After，指数退避重试；
- **磁盘缓存**：同 URL 只请求一次；
- **失败隔离**：`gather(return_exceptions=True)`，单个 URL 失败不影响整批。

## 为什么是 3.6× 而不是 20×

公平性设计：双方都施加了礼貌约束。同步版的耗时 = 请求数 × (延迟 + 间隔)；
异步版把网络等待重叠起来，但受并发上限与全局间隔约束。**在"礼貌"这个
约束下，3.6× 就是异步架构的真实收益**——对比实验控制了变量，而不是
把限速关掉制造夸张数字。

## 文件

| 文件 | 说明 |
|---|---|
| [async_fetcher.py](async_fetcher.py) | AsyncFetcher：信号量并发 + 令牌间隔 + 退避重试 + 缓存 |
| [bench.py](bench.py) | 同步 vs 异步同条件实测，结果写 bench_result.txt |
| [bench_result.txt](bench_result.txt) | 实测数据 |

## 复现

```bash
python bench.py    # 需要网络；约 40 秒（同步版占大头）
```
