"""ReAct 智能体：Thought -> Action -> Observation 循环。

协议（纯文本，不依赖模型的结构化输出能力，因此可接任意对话模型）：

    Thought: 我需要先查数据        （模型的推理）
    Action: sql_query              （选择工具）
    Action Input: {"sql": "..."}   （JSON 参数）
    Observation: ...               （工具结果，由框架注入）
    ... 循环 ...
    Final Answer: ...              （最终回答，循环终止）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from llm import BaseLLM, Message
from tools import ToolRegistry

SYSTEM_TEMPLATE = """你是一个严谨的中文数据分析助手。你可以使用以下工具：

{tools}

回答规则（严格遵守）：
1. 每次只输出一个步骤，格式为：
Thought: <你的思考>
Action: <工具名>
Action Input: <JSON 格式的参数，如 {{"sql": "SELECT ..."}}>
2. 工具结果会以 Observation 的形式返回给你，然后你再继续思考。
3. 已经得到足够信息时，输出：
Final Answer: <最终中文回答，给出结论与依据>
4. 不要编造 Observation；Action Input 必须是合法 JSON。"""

_ACTION_RE = re.compile(r"Action\s*:\s*(\S+)")
_INPUT_RE = re.compile(r"Action Input\s*:\s*(\{.*\})", re.S)
_FINAL_RE = re.compile(r"Final Answer\s*:\s*(.+)", re.S)


@dataclass
class TraceStep:
    step: int
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""


@dataclass
class AgentResult:
    answer: str
    steps: list[TraceStep] = field(default_factory=list)

    def render_trace(self) -> str:
        out = []
        for s in self.steps:
            out.append(f"[step {s.step}] Thought: {s.thought}")
            if s.action:
                out.append(f"  Action: {s.action} {s.action_input}")
                obs = s.observation if len(s.observation) <= 300 else s.observation[:300] + "..."
                out.append(f"  Observation: {obs}")
        return "\n".join(out)


class ReActAgent:
    def __init__(self, llm: BaseLLM, registry: ToolRegistry, max_steps: int = 8):
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps

    def run(self, question: str) -> AgentResult:
        messages = [Message("system", SYSTEM_TEMPLATE.format(
            tools=self.registry.prompt_lines())),
            Message("user", question)]
        steps: list[TraceStep] = []

        for step in range(1, self.max_steps + 1):
            reply = self.llm.chat(messages)
            final = _FINAL_RE.search(reply)
            if final:
                steps.append(TraceStep(step=step, thought=reply))
                return AgentResult(answer=final.group(1).strip(), steps=steps)

            action_m = _ACTION_RE.search(reply)
            input_m = _INPUT_RE.search(reply)
            if not action_m:  # 模型输出不合协议：注入纠错提示继续
                obs = ("输出不符合协议。请严格输出 'Thought: / Action: / "
                       "Action Input:' 或 'Final Answer: '。")
                steps.append(TraceStep(step=step, thought=reply, observation=obs))
                messages.append(Message("assistant", reply))
                messages.append(Message("user", f"Observation: {obs}"))
                continue

            action = action_m.group(1)
            try:
                arguments = json.loads(input_m.group(1)) if input_m else {}
            except json.JSONDecodeError:
                arguments = {}
            observation = self.registry.execute(action, arguments)

            steps.append(TraceStep(step=step, thought=reply, action=action,
                                   action_input=input_m.group(1) if input_m else "{}",
                                   observation=observation))
            messages.append(Message("assistant", reply))
            messages.append(Message("user", f"Observation: {observation}"))

        return AgentResult(answer=f"达到最大步数（{self.max_steps}）仍未得出最终答案。",
                           steps=steps)
