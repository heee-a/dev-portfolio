"""限流器测试：注入时钟精确推演，不依赖 sleep。pytest -q"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "systems"))

from ratelimit import (FixedWindowCounter, SlidingWindowLog,  # noqa: E402
                       TokenBucket)


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_token_bucket_allows_burst_then_refills():
    clock = FakeClock()
    bucket = TokenBucket(rate=2.0, capacity=3, now=clock)
    assert [bucket.acquire() for _ in range(3)] == [0.0, 0.0, 0.0]  # 突发 3 次
    assert bucket.acquire() == pytest.approx(0.5)                    # 第 4 次等 0.5s
    clock.advance(0.5)
    assert bucket.acquire() == 0.0                                   # 补回 1 个令牌


def test_token_bucket_capacity_caps_refill():
    clock = FakeClock()
    bucket = TokenBucket(rate=1.0, capacity=2, now=clock)
    bucket.acquire(); bucket.acquire()                               # 清空
    clock.advance(100)                                               # 长时间闲置
    assert bucket.acquire() == 0.0
    assert bucket.acquire() == 0.0                                   # 只回满到容量 2
    assert bucket.acquire() == pytest.approx(1.0)


def test_sliding_window_exact():
    clock = FakeClock()
    limiter = SlidingWindowLog(max_requests=3, window=10.0, now=clock)
    assert [limiter.acquire() for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.acquire() == pytest.approx(10.0)                  # 最早一条 10s 后过期
    clock.advance(10.0)
    assert limiter.acquire() == 0.0                                  # 窗口滑动，放行


def test_fixed_window_resets():
    clock = FakeClock()
    limiter = FixedWindowCounter(max_requests=2, window=60.0, now=clock)
    assert [limiter.acquire() for _ in range(2)] == [0.0, 0.0]
    assert limiter.acquire() == pytest.approx(60.0)
    clock.advance(60.0)
    assert limiter.acquire() == 0.0                                  # 新窗口清零


def test_rate_limiters_are_thread_safe():
    import threading

    clock = FakeClock()
    bucket = TokenBucket(rate=1000.0, capacity=500, now=clock)
    granted = []
    lock = threading.Lock()

    def worker():
        for _ in range(100):
            if bucket.acquire() == 0.0:
                with lock:
                    granted.append(1)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(granted) == 500                                       # 恰好放行容量数
