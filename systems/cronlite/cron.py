"""cron 表达式解析：标准 5 字段（分 时 日 月 周）。

支持语法：`*`、`*/步进`、`a-b` 范围、`a,b,c` 列表、`a-b/n` 组合。

易错细节（面试可讲）：「日」与「周」同时受限时的 OR 语义——
这是 POSIX cron 的规定：两个字段都不是 * 时，日期命中任意一个即可触发。
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta

FIELD_RANGES = [(0, 59, "分钟"), (0, 23, "小时"), (1, 31, "日"),
                (1, 12, "月"), (0, 6, "周几")]
WEEKDAY_ALIASES = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4,
                   "fri": 5, "sat": 6}


class CronError(ValueError):
    pass


@dataclass(frozen=True)
class CronSpec:
    expression: str
    minutes: frozenset
    hours: frozenset
    days_of_month: frozenset
    months: frozenset
    days_of_week: frozenset      # 0=周日
    dom_star: bool
    dow_star: bool

    def matches(self, dt: datetime) -> bool:
        if dt.minute not in self.minutes or dt.hour not in self.hours:
            return False
        if dt.month not in self.months:
            return False
        dom_ok = dt.day in self.days_of_month
        dow_ok = ((dt.weekday() + 1) % 7) in self.days_of_week  # 周一=0 -> 周日=0
        if self.dom_star and self.dow_star:
            return True
        if self.dom_star:
            return dow_ok
        if self.dow_star:
            return dom_ok
        return dom_ok or dow_ok                  # 双受限：POSIX 的 OR 语义

    def next_after(self, dt: datetime) -> datetime:
        """严格晚于 dt 的下一次触发时间（秒被截断）。最多向前查 4 年。"""
        candidate = (dt + timedelta(minutes=1)).replace(second=0, microsecond=0)
        limit = dt + timedelta(days=366 * 4)
        while candidate < limit:
            if candidate.month not in self.months:
                y, m = candidate.year, candidate.month    # 整月不匹配：快进
                m += 1
                if m > 12:
                    m, y = 1, y + 1
                candidate = candidate.replace(year=y, month=m, day=1,
                                              hour=0, minute=0)
                continue
            if not self._day_matches(candidate):
                candidate = (candidate + timedelta(days=1)).replace(
                    hour=0, minute=0)
                continue
            if candidate.hour not in self.hours:
                later = sorted(h for h in self.hours if h > candidate.hour)
                if later:
                    candidate = candidate.replace(hour=later[0], minute=0)
                else:
                    candidate = (candidate + timedelta(days=1)).replace(
                        hour=0, minute=0)
                continue
            if candidate.minute in self.minutes:          # 落在匹配分钟上
                return candidate
            later = sorted(m for m in self.minutes if m > candidate.minute)
            if later:
                return candidate.replace(minute=later[0])
            candidate = (candidate + timedelta(hours=1)).replace(minute=0)
        raise CronError(f"{self.expression}: 4 年内没有匹配的触发时间")

    def _day_matches(self, dt: datetime) -> bool:
        dom_ok = dt.day in self.days_of_month
        dow_ok = ((dt.weekday() + 1) % 7) in self.days_of_week
        if self.dom_star and self.dow_star:
            return True
        if self.dom_star:
            return dow_ok
        if self.dow_star:
            return dom_ok
        return dom_ok or dow_ok


def _parse_field(token: str, lo: int, hi: int, field_name: str) -> set[int]:
    values: set[int] = set()
    for part in token.split(","):
        part = part.strip().lower()
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = int(step_s)
            if step <= 0:
                raise CronError(f"{field_name} 步进必须为正: /{step_s}")
        if part == "*":
            start, end = lo, hi
        elif "-" in part and not part.lstrip("-").isdigit():
            range_part = part
            if field_name == "周几":
                range_part = part
            a_s, b_s = part.split("-", 1)
            start, end = _atom(a_s, field_name), _atom(b_s, field_name)
        else:
            start = end = _atom(part, field_name)
        if start < lo or end > hi or start > end:
            raise CronError(f"{field_name} 字段 {token!r} 超出范围 [{lo}, {hi}]")
        values.update(range(start, end + 1, step))
    if not values:
        raise CronError(f"{field_name} 字段为空")
    return values


def _atom(token: str, field_name: str) -> int:
    if field_name == "周几" and token in WEEKDAY_ALIASES:
        return WEEKDAY_ALIASES[token]
    if not token.lstrip("-").isdigit():
        raise CronError(f"{field_name} 字段含非法值 {token!r}")
    return int(token)


def parse_cron(expression: str) -> CronSpec:
    fields = expression.split()
    if len(fields) != 5:
        raise CronError(f"cron 表达式需要 5 个字段，收到 {len(fields)} 个: {expression!r}")
    specs = [_parse_field(tok, lo, hi, name)
             for tok, (lo, hi, name) in zip(fields, FIELD_RANGES)]
    return CronSpec(
        expression=expression,
        minutes=frozenset(specs[0]), hours=frozenset(specs[1]),
        days_of_month=frozenset(specs[2]), months=frozenset(specs[3]),
        days_of_week=frozenset(specs[4]),
        dom_star=fields[2] in ("*",), dow_star=fields[4] in ("*",),
    )


def is_valid(expression: str) -> bool:
    try:
        parse_cron(expression)
        return True
    except CronError:
        return False
