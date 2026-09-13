# AI 智能体：从零实现 ReAct 框架

不调 LangChain，从零写一个 **ReAct（Reasoning + Acting）智能体**的完整实现：
工具注册表、思考-行动-观察循环、对话记忆、任意 OpenAI 兼容模型接入、
以及不依赖任何 API Key 的离线测试与演示。

## ReAct 循环原理

```
用户问题
   │
   ▼
┌─────────────────────────────┐
│ Thought:  我需要先查数据      │ ◄── LLM 推理
│ Action:   sql_query          │ ◄── 选择工具
│ Action Input: {"sql": "..."} │
│ Observation: ...             │ ◄── 框架执行工具并回填
│ Thought:  再算倍数 …         │
│ Action:   calculator …       │
│ Final Answer: …              │ ──► 循环终止
└─────────────────────────────┘
```

## 文件结构

| 文件 | 职责 |
|---|---|
| [react_agent/llm.py](react_agent/llm.py) | LLM 抽象：OpenAI 兼容端点（DeepSeek/Kimi/智谱通用）+ FakeLLM 脚本回放 |
| [react_agent/tools.py](react_agent/tools.py) | 工具注册表：装饰器注册、签名自动生成 JSON Schema、AST 白名单安全计算器、只读 SQL 工具 |
| [react_agent/agent.py](react_agent/agent.py) | ReAct 循环：协议解析、Observation 回填、格式纠错、最大步数保护、完整轨迹 |
| [react_agent/memory.py](react_agent/memory.py) | 滑动窗口对话记忆 |
| [demo_offline.py](demo_offline.py) | 离线演示：FakeLLM 脚本扮演模型，完整跑通三步循环 |
| [cli.py](cli.py) | 交互式命令行（配好环境变量后接真实模型） |

## 运行

```bash
# 离线演示（不需要任何 API Key）
python demo_offline.py

# 接真实模型（DeepSeek / Kimi / 智谱 等 OpenAI 兼容服务均可）
export OPENAI_BASE_URL=https://api.deepseek.com/v1
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=deepseek-chat
python cli.py
```

## 设计决策（面试可展开）

1. **纯文本协议而非 function calling**：Thought/Action/Action Input 的文本协议
   不依赖模型的结构化输出能力，任何对话模型都能接——这在国产模型生态里很实用；
2. **工具层沙箱**：计算器用 AST 白名单求值（`__import__` 注入直接被拦截）、
   SQL 工具只放行 SELECT；工具异常不终止循环，而是作为 Observation 喂回模型
   自我纠正（演示里真实发生过：缺 tabulate 时模型收到报错后换路径完成）；
3. **可测试性**：LLM 是注入的抽象（FakeLLM 脚本回放），8 个测试全部离线；
4. **已知边界**：文本协议对模型输出格式有依赖（有格式纠错兜底）；无流式输出；
   记忆是滑动窗口而非向量检索（RAG 是下一步扩展）。

## 测试

```bash
pytest tests/test_agent.py -q    # 8 项：工具安全 / 完整循环 / 格式纠错 / 最大步数 / 记忆窗口
```
