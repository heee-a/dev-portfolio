"""ReAct 智能体测试（全部离线：LLM 用 FakeLLM 脚本扮演）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-agents"))

import sqlite3

import pytest

from agent import ReActAgent
from llm import FakeLLM, Message
from memory import ConversationMemory
from tools import make_default_registry


@pytest.fixture()
def registry(tmp_path):
    db = tmp_path / "demo.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE gdp_2023 (country TEXT, gdp_per_capita INT)")
        conn.executemany("INSERT INTO gdp_2023 VALUES (?, ?)",
                         [("Luxembourg", 129510), ("Burundi", 233)])
    return make_default_registry(db_path=db)


# ---------------- 工具层 ----------------
def test_calculator(registry):
    assert registry.execute("calculator", {"expression": "(1+2)*3.5"}) == "10.5"


def test_calculator_blocks_injection(registry):
    out = registry.execute("calculator", {"expression": "__import__('os').system('dir')"})
    assert out.startswith("工具执行出错")     # AST 白名单拦截，且不崩溃


def test_sql_query_readonly(registry):
    out = registry.execute("sql_query", {"sql": "SELECT * FROM gdp_2023 "
                                              "ORDER BY gdp_per_capita DESC"})
    assert "Luxembourg" in out
    out = registry.execute("sql_query", {"sql": "DELETE FROM gdp_2023"})
    assert "仅允许 SELECT" in out


def test_unknown_tool_lists_available(registry):
    out = registry.execute("nope", {})
    assert "不存在" in out and "calculator" in out


# ---------------- 智能体循环 ----------------
def test_react_agent_full_loop(registry):
    fake = FakeLLM(script=[
        "Thought: 先查库。\nAction: sql_query\n"
        'Action Input: {"sql": "SELECT * FROM gdp_2023 '
        'ORDER BY gdp_per_capita DESC"}',
        "Thought: 再算倍数。\nAction: calculator\n"
        'Action Input: {"expression": "129510 / 233"}',
        "Final Answer: 最高 Luxembourg，最低 Burundi，相差约 556 倍。",
    ])
    result = ReActAgent(fake, registry).run("最高最低差多少倍？")
    assert result.answer.startswith("最高 Luxembourg")
    assert len(result.steps) == 3
    assert "Luxembourg" in result.steps[0].observation
    trace = result.render_trace()
    assert "Action: sql_query" in trace and "Observation" in trace


def test_react_agent_recovers_from_malformed_output(registry):
    fake = FakeLLM(script=[
        "我觉得直接回答比较好。",                 # 不合协议
        "Observation 已收到。\nFinal Answer: 好的。",
    ])
    result = ReActAgent(fake, registry, max_steps=3).run("你好")
    assert result.answer == "好的。"
    assert result.steps[0].observation.startswith("输出不符合协议")


def test_react_agent_max_steps(registry):
    fake = FakeLLM(script=["Thought: 我一直想下去"] * 5)  # 永不合协议
    result = ReActAgent(fake, registry, max_steps=3).run("x")
    assert "最大步数" in result.answer


# ---------------- 记忆 ----------------
def test_memory_window():
    mem = ConversationMemory(max_turns=2)
    for i in range(6):
        mem.add(Message("user", f"q{i}"))
        mem.add(Message("assistant", f"a{i}"))
    view = mem.window("系统提示")
    assert view[0].role == "system" and view[0].content == "系统提示"
    assert len(view) == 5                            # system + 最近 2 轮(4 条)
    assert view[-1].content == "a5"
