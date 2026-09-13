"""离线演示：LLM 由脚本扮演，完整展示 ReAct 循环机制。

问题：示例数据库里 2023 年人均GDP 最高和最低的国家各是谁？
智能体应：1) 查库 2) 计算/排序 3) 给出 Final Answer。

运行: python demo_offline.py
（真实模型请用 cli.py，配好 OPENAI_* 环境变量）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3

from agent import ReActAgent
from llm import FakeLLM
from tools import make_default_registry

DATA = Path(__file__).parent / "data" / "demo_gdp.db"

# 用真实世界数据（2023 人均GDP，节选）构建演示库
ROWS = [("Luxembourg", 129510), ("Ireland", 103684), ("Switzerland", 99395),
        ("Norway", 87961), ("United States", 81695), ("China", 12951),
        ("Brazil", 10044), ("India", 2485), ("Ethiopia", 1022), ("Burundi", 233)]


def build_demo_db() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATA) as conn:
        conn.execute("DROP TABLE IF EXISTS gdp_2023")
        conn.execute("CREATE TABLE gdp_2023 (country TEXT, gdp_per_capita INT)")
        conn.executemany("INSERT INTO gdp_2023 VALUES (?, ?)", ROWS)
        conn.commit()


def main() -> None:
    build_demo_db()
    question = "示例数据库里 2023 年人均GDP 最高和最低的国家分别是谁？相差多少倍？"

    # FakeLLM 按脚本回放——模拟真实模型的三个步骤（查库 -> 计算 -> 总结）
    fake = FakeLLM(script=[
        "Thought: 我需要先查库拿到所有国家的人均GDP。\n"
        "Action: sql_query\n"
        'Action Input: {"sql": "SELECT * FROM gdp_2023 ORDER BY gdp_per_capita DESC"}',
        "Thought: 最高是 Luxembourg 129510，最低是 Burundi 233。我用计算器算倍数。\n"
        "Action: calculator\n"
        'Action Input: {"expression": "129510 / 233"}',
        "Thought: 数据齐了，可以给出最终答案。\n"
        "Final Answer: 2023 年人均GDP 最高的是 Luxembourg（129,510 美元），"
        "最低的是 Burundi（233 美元），相差约 556 倍。",
    ])
    registry = make_default_registry(db_path=DATA)
    agent = ReActAgent(fake, registry)

    result = agent.run(question)
    print("问题:", question)
    print("\n=== ReAct 轨迹 ===")
    print(result.render_trace())
    print("\n=== 最终回答 ===")
    print(result.answer)
    print(f"\n（本次演示中 LLM 由 FakeLLM 脚本扮演，用于展示循环机制；"
          f"接入真实模型请用 cli.py）")


if __name__ == "__main__":
    main()
