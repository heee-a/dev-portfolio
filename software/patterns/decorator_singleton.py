"""装饰器模式 + 单例模式：横切关注点与配置中心。

装饰器：Python 的 @decorator 就是装饰器模式的一等公民形态——
这里实现「重试 + 计时」两个可组合的横切能力。
单例：配置中心。用模块级实例 + __new__ 双保险，并说明测试时如何隔离。
"""

from __future__ import annotations

import functools
import threading
import time


# ---------- 装饰器 ----------
def retry(times: int = 3, delay: float = 0.1, exceptions=(Exception,)):
    """失败重试：指数退避。真实项目中最常用的横切能力之一。"""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < times - 1:
                        time.sleep(delay * (2 ** attempt))
            raise last_exc
        return wrapper
    return decorator


def timed(fn):
    """计时：把耗时写到函数属性而非打印——不污染调用方输出。"""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            wrapper.last_elapsed = time.perf_counter() - start
    wrapper.last_elapsed = 0.0
    return wrapper


@timed
@retry(times=3, delay=0.01)
def flaky_task(fail_times: int = 0) -> str:
    """模拟不稳定任务：前 fail_times 次抛错。通过闭包计数（演示用）。"""
    flaky_task.calls = getattr(flaky_task, "calls", 0) + 1
    if flaky_task.calls <= fail_times:
        raise ConnectionError("网络抖动")
    return "ok"


# ---------- 单例 ----------
class ConfigCenter:
    """线程安全的单例配置中心。

    实现选择：__new__ + 双检锁。测试隔离：提供 _reset()；
    生产中更推荐的其实是「模块级单例」（config = load_config()），
    这里演示的是教科书式写法，两种都要能说清。
    """

    _instance: "ConfigCenter | None" = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._data = {}
                    inst._loaded = False
                    cls._instance = inst
        return cls._instance

    def load(self, data: dict) -> None:
        self._data.update(data)
        self._loaded = True

    def get(self, key: str, default=None):
        if not self._loaded:
            raise RuntimeError("配置尚未加载")
        return self._data.get(key, default)

    @classmethod
    def _reset(cls):
        """仅供测试：销毁单例。"""
        with cls._lock:
            cls._instance = None
