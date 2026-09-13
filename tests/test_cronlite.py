"""cronlite 测试：解析正确性、边界语义、调度逻辑（时间注入，无需真实等待）。"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "systems" / "cronlite"))

import pytest

from cron import CronError, is_valid, parse_cron
from scheduler import Scheduler


# ---------------- 解析 ----------------
def test_parse_basic_sets():
    spec = parse_cron("30 2 * * *")               # 每天 02:30
    assert spec.minutes == {30} and spec.hours == {2}
    assert spec.dom_star and spec.dow_star


def test_parse_ranges_lists_steps():
    spec = parse_cron("*/15 9-17 1,15 3-6/2 mon-fri")
    assert spec.minutes == {0, 15, 30, 45}
    assert spec.hours == set(range(9, 18))
    assert spec.days_of_month == {1, 15}
    assert spec.months == {3, 5}
    assert spec.days_of_week == {1, 2, 3, 4, 5}


def test_parse_errors():
    assert not is_valid("61 * * * *")             # 分钟超范围
    assert not is_valid("* 25 * * *")             # 小时超范围
    assert not is_valid("* * * *")                # 字段数不足
    assert not is_valid("a * * * *")
    assert not is_valid("*/0 * * * *")            # 步进必须为正


def test_weekday_alias():
    spec = parse_cron("0 0 * * mon")
    assert spec.days_of_week == {1}


# ---------------- next_after ----------------
def test_next_after_same_day():
    spec = parse_cron("30 10 * * *")
    base = datetime(2026, 9, 13, 8, 0)
    assert spec.next_after(base) == datetime(2026, 9, 13, 10, 30)


def test_next_after_rolls_to_tomorrow():
    spec = parse_cron("0 0 * * *")                # 每天 00:00
    base = datetime(2026, 9, 13, 0, 0, 30)        # 刚过触发点
    assert spec.next_after(base) == datetime(2026, 9, 14, 0, 0)


def test_next_after_month_skip():
    spec = parse_cron("0 0 1 3 *")                # 每年 3 月 1 日
    base = datetime(2026, 4, 1, 12, 0)
    assert spec.next_after(base) == datetime(2027, 3, 1, 0, 0)


def test_dom_dow_or_semantics():
    # 13 日 + 周五 双受限：命中任一即触发（POSIX 语义）
    spec = parse_cron("0 0 13 * fri")
    friday_13 = datetime(2026, 11, 13, 0, 0)      # 2026-11-13 是周五
    assert spec.matches(friday_13)
    # 从 9-1 起：9-4 是周五（OR 语义先命中），随后 9-11 也是周五，
    # 9-13 是 13 日（周日）——三者都该触发
    assert spec.next_after(datetime(2026, 9, 1, 0, 0)) == datetime(2026, 9, 4, 0, 0)
    assert spec.next_after(datetime(2026, 9, 5, 0, 0)) == datetime(2026, 9, 11, 0, 0)
    assert spec.next_after(datetime(2026, 9, 12, 0, 0)) == datetime(2026, 9, 13, 0, 0)


def test_dom_star_meaning():
    spec = parse_cron("0 12 * * mon")             # 仅周限 -> 每周一 12 点
    monday = datetime(2026, 9, 14, 12, 0)         # 周一
    assert spec.matches(monday)
    assert not spec.matches(datetime(2026, 9, 15, 12, 0))


def test_next_after_leap():
    spec = parse_cron("0 0 29 2 *")               # 2 月 29 日
    base = datetime(2027, 1, 1, 0, 0)
    assert spec.next_after(base) == datetime(2028, 2, 29, 0, 0)  # 2028 闰年


# ---------------- 调度器 ----------------
class FakeClock:
    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw):
        self.now += __import__("datetime").timedelta(**kw)


def test_scheduler_fires_due_jobs():
    clock = FakeClock(datetime(2026, 9, 13, 9, 59, 30))
    sched = Scheduler(clock=clock, sleep=lambda s: None)
    ran = []
    sched.register("every_min", "* * * * *", lambda: ran.append("tick"))
    # 09:59:30 -> 下次触发 10:00
    fired = sched.run_once(clock.now)             # 未到期
    assert fired == [] and ran == []
    clock.advance(minutes=1)                      # 10:00:30 到期
    fired = sched.run_once(clock.now)
    assert fired == ["every_min"] and len(ran) == 1
    # 同一时刻再 run_once 不重复触发（已顺延到 10:01）
    assert sched.run_once(clock.now) == []
    clock.advance(minutes=1)
    assert sched.run_once(clock.now) == ["every_min"]


def test_scheduler_counts_and_failure_isolation():
    clock = FakeClock(datetime(2026, 9, 13, 0, 0, 5))
    sched = Scheduler(clock=clock, sleep=lambda s: None)

    def bad():
        raise ValueError("任务炸了")

    sched.register("bad", "* * * * *", bad)
    sched.register("good", "* * * * *", lambda: None)
    clock.advance(minutes=1)
    fired = sched.run_once(clock.now)
    assert set(fired) == {"bad", "good"}          # 一个任务失败不影响另一个
    assert "ValueError" in sched.jobs["bad"].last_result
    assert sched.jobs["bad"].runs == 1 and sched.jobs["good"].runs == 1


def test_scheduler_next_run_chains_correctly():
    clock = FakeClock(datetime(2026, 9, 13, 23, 59, 0))
    sched = Scheduler(clock=clock, sleep=lambda s: None)
    sched.register("daily", "0 8 * * *", lambda: None)
    assert sched.jobs["daily"].next_run == datetime(2026, 9, 14, 8, 0)
    clock.advance(days=1)                          # -> 9-14 23:59
    sched.run_once(clock.now)                      # 触发 8 点的那次
    assert sched.jobs["daily"].next_run == datetime(2026, 9, 15, 8, 0)
