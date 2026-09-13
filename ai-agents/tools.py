"""工具系统：装饰器注册 + 签名自动生成 JSON Schema + 安全执行。"""

from __future__ import annotations

import ast
import datetime
import inspect
import json
import operator
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}


@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    parameters: dict          # JSON Schema

    def run(self, **kwargs) -> str:
        return str(self.func(**kwargs))


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, description: str, name: str | None = None) -> Callable:
        """装饰器：从函数签名自动生成 JSON Schema。

        @registry.register("查询世界发展指标 SQLite 库", name="sql_query")
        def sql_query(sql: str) -> str: ...
        """
        def decorator(func: Callable) -> Callable:
            props, required = {}, []
            for pname, param in inspect.signature(func).parameters.items():
                ann = param.annotation if param.annotation != inspect.Parameter.empty else str
                props[pname] = {"type": _PY_TO_JSON.get(ann, "string"),
                                "description": pname}
                if param.default is inspect.Parameter.empty:
                    required.append(pname)
            tool = Tool(
                name=name or func.__name__, description=description, func=func,
                parameters={"type": "object", "properties": props,
                            "required": required})
            self._tools[tool.name] = tool
            return func
        return decorator

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def prompt_lines(self) -> str:
        """渲染进系统提示词的工具清单。"""
        return "\n".join(
            f"- {t.name}: {t.description} 参数: {json.dumps(t.parameters, ensure_ascii=False)}"
            for t in self._tools.values())

    def execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"错误: 工具 {name!r} 不存在。可用工具: {', '.join(self._tools)}"
        try:
            return tool.run(**arguments)
        except Exception as e:  # 工具报错作为 Observation 返回给模型自我纠正
            return f"工具执行出错: {type(e).__name__}: {e}"


# ---------- 内置工具实现 ----------

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
        ast.Mod: operator.mod}


def _safe_eval(node: ast.AST) -> float:
    """AST 白名单求值：只允许四则运算，杜绝 eval 注入。"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("只支持算术运算")


def make_default_registry(db_path: str | Path | None = None) -> ToolRegistry:
    reg = ToolRegistry()

    @reg.register("数学计算器，输入合法的算术表达式，如 (1+2)*3.5", name="calculator")
    def calculator(expression: str) -> str:
        return str(_safe_eval(ast.parse(expression, mode="eval")))

    @reg.register("查询当前 UTC 时间", name="current_time")
    def current_time() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds")

    @reg.register("对一个 SQLite 数据库执行只读 SELECT 查询，返回 Markdown 表格",
                  name="sql_query")
    def sql_query(sql: str, db: str = str(db_path or ":memory:")) -> str:
        import pandas as pd

        if not sql.lstrip().upper().startswith("SELECT"):
            return "仅允许 SELECT 查询"
        with sqlite3.connect(db) as conn:
            df = pd.read_sql_query(sql, conn)
        if df.empty:
            return "(空结果)"
        return df.to_markdown(index=False)

    return reg
