"""工厂模式 + 建造者模式：报表导出与查询构造。

工厂：根据 format 参数创建对应导出器，调用方不感知具体类——
新增 PDF 导出只加一个类 + 一行注册。
建造者：分步构造复杂对象（SQL 查询），避免多参数构造函数的「 Telescope 反模式」。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


# ---------- 工厂 ----------
class Exporter:
    format_name = ""

    def export(self, rows: list[dict]) -> str:
        raise NotImplementedError


class CsvExporter(Exporter):
    format_name = "csv"

    def export(self, rows: list[dict]) -> str:
        if not rows:
            return ""
        head = ",".join(rows[0])
        lines = [",".join(str(r[k]) for k in rows[0]) for r in rows]
        return "\n".join([head] + lines)


class JsonExporter(Exporter):
    format_name = "json"

    def export(self, rows: list[dict]) -> str:
        return json.dumps(rows, ensure_ascii=False, indent=2)


_REGISTRY: dict[str, type[Exporter]] = {"csv": CsvExporter, "json": JsonExporter}


def register_format(name: str):
    """开放注册点：新格式在模块加载时自注册，工厂函数无需修改（OCP 开闭原则）。"""
    def decorator(cls: type[Exporter]):
        _REGISTRY[name] = cls
        cls.format_name = name
        return cls
    return decorator


def make_exporter(fmt: str) -> Exporter:
    cls = _REGISTRY.get(fmt)
    if cls is None:
        raise ValueError(f"未知格式 {fmt!r}，可用: {sorted(_REGISTRY)}")
    return cls()


# ---------- 建造者 ----------
@dataclass
class Query:
    table: str
    columns: list[str] = field(default_factory=list)
    wheres: list[tuple[str, str, object]] = field(default_factory=list)
    order_by: str = ""
    limit: int | None = None

    def to_sql(self) -> str:
        cols = ", ".join(self.columns) or "*"
        sql = f"SELECT {cols} FROM {self.table}"
        if self.wheres:
            sql += " WHERE " + " AND ".join(
                f"{c} {op} {self._lit(v)}" for c, op, v in self.wheres)
        if self.order_by:
            sql += f" ORDER BY {self.order_by}"
        if self.limit is not None:
            sql += f" LIMIT {self.limit}"
        return sql

    @staticmethod
    def _lit(v) -> str:
        if isinstance(v, str):
            return f"'{v}'"          # 教学实现：生产请用参数绑定防注入
        return str(v)


class QueryBuilder:
    """流式接口：每次方法返回自身，最后 build() 产出不可变 Query。"""

    def __init__(self, table: str):
        self._table = table
        self._columns: list[str] = []
        self._wheres: list[tuple[str, str, object]] = []
        self._order_by = ""
        self._limit: int | None = None

    def select(self, *columns: str) -> "QueryBuilder":
        self._columns = list(columns)
        return self

    def where(self, column: str, op: str, value) -> "QueryBuilder":
        self._wheres.append((column, op, value))
        return self

    def order_desc(self, column: str) -> "QueryBuilder":
        self._order_by = f"{column} DESC"
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit = n
        return self

    def build(self) -> Query:
        return Query(self._table, list(self._columns), list(self._wheres),
                     self._order_by, self._limit)
