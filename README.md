# dev-portfolio · 开发作品集（软件开发 / AI 智能体 / 算法）

[![CI](https://github.com/heee-a/dev-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/heee-a/dev-portfolio/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

按类别组织的开发能力作品集，39 个测试全部通过、全部离线可复现。

## 类别一览

### 🧱 [software/ 软件开发](software/)
**Task API** —— FastAPI 任务管理服务。分层架构、Pydantic 校验、SQLite 持久化、
分页搜索、Swagger 自动文档、6 项端到端测试。
→ [README](software/README.md)

### 🤖 [ai-agents/ 人工智能体](ai-agents/)
**ReAct 框架从零实现** —— 思考-行动-观察循环、装饰器工具注册（签名自动生成
JSON Schema）、AST 白名单安全计算器、只读 SQL 工具、滑动窗口记忆、
OpenAI 兼容模型接入（DeepSeek/Kimi/智谱通用）、FakeLLM 离线测试。
→ [README](ai-agents/README.md) · 离线演示 `python ai-agents/demo_offline.py`

### 🧮 [algorithms/ 算法](algorithms/)
**六大专题 25+ 经典算法** —— 排序/查找/DP/图/字符串/数据结构，
中文注释讲思路与复杂度、面试追问点标注、与标准实现对照的参数化测试、
实测性能基准（n=8000 时 O(n²) 比 O(n log n) 慢百倍）。
→ [README](algorithms/README.md) · 基准 `python algorithms/benchmark.py`

## 快速开始

```bash
pip install -e .
pytest -q                    # 39 个测试，全部离线

# 软件开发
python software/taskapi/run.py          # http://127.0.0.1:8000/docs

# AI 智能体（离线演示无需任何 Key）
python ai-agents/demo_offline.py
python ai-agents/cli.py                  # 接真实模型需配置 OPENAI_* 环境变量

# 算法
python algorithms/benchmark.py
```

## 目录结构

```
dev-portfolio/
├── software/taskapi/      # main.py 路由 / schemas.py 校验 / storage.py 存储
├── ai-agents/             # agent.py 循环 / tools.py 工具 / llm.py / memory.py
├── algorithms/            # sorting / searching / dynamic_programming / graph / strings / data_structures
└── tests/                 # 39 个测试（test_taskapi / test_agent / test_algorithms）
```

## 说明

- 全部代码为本人实现，算法部分不搬运题解，注释侧重思路与复杂度推导；
- 智能体的离线演示用 FakeLLM 脚本扮演模型（明确标注），接真实模型只需环境变量；
- License: [MIT](LICENSE)
