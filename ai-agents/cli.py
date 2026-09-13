"""交互式命令行智能体（需要真实 LLM 服务）。

配置环境变量后运行: python cli.py
    OPENAI_BASE_URL  如 https://api.deepseek.com/v1
    OPENAI_API_KEY   你的 Key
    OPENAI_MODEL     如 deepseek-chat
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import ReActAgent
from llm import Message, OpenAICompatLLM
from memory import ConversationMemory
from tools import make_default_registry

SYSTEM = """你是一个严谨的中文数据分析助手，可以读写当前目录下的示例数据库。
回答规则：
Thought: <思考>
Action: <工具名>
Action Input: <JSON 参数>
（Observation 由系统返回）
Final Answer: <最终中文回答>"""


def main() -> None:
    llm = OpenAICompatLLM()
    registry = make_default_registry(
        db_path=Path(__file__).parent / "data" / "demo_gdp.db")
    agent = ReActAgent(llm, registry)
    memory = ConversationMemory()
    last_trace = ""
    print("ReAct 智能体已启动（ctrl+c 退出，输入 trace 看上次推理轨迹）。"
          "试试：示例库里人均GDP最高和最低的国家相差多少倍？")
    while True:
        try:
            q = input("\n你> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q:
            continue
        if q == "trace":
            print(last_trace or "（还没有执行过任务）")
            continue
        memory.add(Message("user", q))
        result = agent.run(q)
        memory.add(Message("assistant", result.answer))
        last_trace = result.render_trace()
        print(f"\n助手> {result.answer}")
        print(f"（{len(result.steps)} 步，输入 trace 查看推理轨迹）")


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("请先配置 OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL 环境变量，"
              "或先运行 demo_offline.py 看离线演示。")
        sys.exit(1)
    main()
