"""限流器集合：令牌桶 / 滑动窗口日志 / 固定窗口计数，时钟可注入。

设计要点（面试可讲）：
- 三个实现共用 `now` 可调用注入时间——测试可以精确推演，不 sleep；
- 全部线程安全（锁保护状态），供采集器多线程复用；
- 语义差异与适用场景见 README 对比表。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


class RateLimiter:
    def acquire(self) -> float:
        """请求一个许可；返回需要等待的秒数（0 = 立即放行）。"""
        raise NotImplementedError


@dataclass
class TokenBucket(RateLimiter):
    """令牌桶：允许突发 burst 次请求，长期速率 = rate/秒。

    适用：平滑限速但容忍短时突发（对应 API 采集器的常见需求）。
    """

    rate: float                    # 每秒生成令牌数
    capacity: float                # 桶容量（最大突发）
    now: Callable[[], float] = field(default_factory=time.monotonic)
    _tokens: float = field(init=False)
    _updated: float = field(init=False, default_factory=lambda: 0.0)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        self._tokens = self.capacity
        self._updated = self.now()

    def acquire(self) -> float:
        with self._lock:
            now = self.now()
            self._tokens = min(self.capacity,
                               self._tokens + (now - self._updated) * self.rate)
            self._updated = now
            if self._tokens >= 1:
                self._tokens -= 1
                return 0.0
            wait = (1 - self._tokens) / self.rate
            self._tokens = 0
            return wait


@dataclass
class SlidingWindowLog(RateLimiter):
    """滑动窗口日志：精确限制窗口内请求数，无边界突刺。

    适用：严格的"每 N 秒最多 M 次"；内存 O(窗口内请求数)。
    """

    max_requests: int              # 窗口内最大请求数
    window: float                  # 窗口长度（秒）
    now: Callable[[], float] = field(default_factory=time.monotonic)
    _log: deque = field(default_factory=deque, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def acquire(self) -> float:
        with self._lock:
            now = self.now()
            while self._log and now - self._log[0] >= self.window:
                self._log.popleft()
            if len(self._log) < self.max_requests:
                self._log.append(now)
                return 0.0
            wait = self.window - (now - self._log[0])
            return max(0.0, wait)


@dataclass
class FixedWindowCounter(RateLimiter):
    """固定窗口计数：按整窗清零。实现最省内存，但窗口边界允许 2x 突刺。

    适用：统计口径的粗粒度限速（如"每分钟第 N 次"）。
    """

    max_requests: int
    window: float = 60.0
    now: Callable[[], float] = field(default_factory=time.monotonic)
    _count: int = field(default=0, init=False)
    _window_start: float = field(init=False, default_factory=lambda: 0.0)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def acquire(self) -> float:
        with self._lock:
            now = self.now()
            if now - self._window_start >= self.window:
                self._window_start = now
                self._count = 0
            if self._count < self.max_requests:
                self._count += 1
                return 0.0
            wait = self.window - (now - self._window_start)
            return max(0.0, wait)
