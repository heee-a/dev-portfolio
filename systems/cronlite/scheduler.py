"""调度引擎：按 cron 计划执行任务，线程安全，时间可注入（便于测试）。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from cron import CronSpec, parse_cron


def time_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)


@dataclass
class Job:
    name: str
    spec: CronSpec
    fn: Callable[[], None]
    next_run: datetime | None = None
    last_result: str = "未运行"
    runs: int = 0


class Scheduler:
    """调度器：register -> start() 后台线程按最早触发时间睡眠等待。

    时间与睡眠都可注入（clock/sleep 参数），单测不需要真实等待。
    """

    def __init__(self, clock: Callable[[], datetime] = datetime.now,
                 sleep: Callable[[float], None] = time_sleep,
                 poll_interval: float = 1.0):
        self.clock = clock
        self.sleep = sleep
        self.poll_interval = poll_interval
        self.jobs: dict[str, Job] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def register(self, name: str, cron_expr: str,
                 fn: Callable[[], None]) -> Job:
        job = Job(name, parse_cron(cron_expr), fn)
        job.next_run = job.spec.next_after(self.clock())
        self.jobs[name] = job
        return job

    def run_once(self, now: datetime | None = None) -> list[str]:
        """单步调度：执行所有到期任务并顺延计划（测试与手动触发入口）。"""
        now = now or self.clock()
        fired = []
        for job in self.jobs.values():
            if job.next_run is not None and now >= job.next_run:
                try:
                    job.fn()
                    job.last_result = "ok"
                except Exception as e:                # 任务失败不影响调度器
                    job.last_result = f"{type(e).__name__}: {e}"
                job.runs += 1
                fired.append(job.name)
                job.next_run = job.spec.next_after(max(job.next_run, now))
        return fired

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("调度器已在运行")

        def worker() -> None:
            while not self._stop.is_set():
                self.run_once()
                self._stop.wait(self.poll_interval)   # Event.wait = 可中断睡眠

        self._stop.clear()
        self._thread = threading.Thread(target=worker, daemon=True,
                                        name="cronlite-scheduler")
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
