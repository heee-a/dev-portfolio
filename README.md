# dev-portfolio · 开发作品集（软件开发 / AI 智能体 / 算法 / 系统编程 / 编程语言）

[![CI](https://github.com/heee-a/dev-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/heee-a/dev-portfolio/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-80%20passed-brightgreen)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

按类别组织的开发能力作品集：**5 个类别、9 个子项目、80 个测试**，全部离线可复现。

## 类别一览

### 🧱 [software/ 软件开发](software/)
- **[Task API](software/README.md)** —— FastAPI 任务管理服务：三层架构、Pydantic 校验、
  分页搜索、Swagger 文档、端到端测试
- **[设计模式库](software/patterns/)** —— 10 个模式全部场景化落地：
  策略(促销定价)、观察者(库存预警)、责任链(风控审批链，轨迹累积)、状态机(订单)、
  工厂+开放注册(导出器)、建造者(查询构造器)、装饰器(重试/计时)、单例(配置中心)、
  适配器(双支付渠道)、模板方法(ETL)。每个模式附「何时不用」。

### 🤖 [ai-agents/ 人工智能体](ai-agents/)
**ReAct 框架从零实现** —— 思考-行动-观察循环、装饰器工具注册（签名自动生成
JSON Schema）、AST 白名单安全计算器、只读 SQL 工具、滑动窗口记忆、
任意 OpenAI 兼容模型接入（DeepSeek/Kimi/智谱）、FakeLLM 离线测试与演示。
→ [README](ai-agents/README.md) · `python ai-agents/demo_offline.py`

### 🧮 [algorithms/ 算法](algorithms/)
**六大专题 25+ 经典算法** —— 中文思路注释、面试追问点、参数化测试、实测性能
基准（n=8000 时 O(n²) 比 O(n log n) 慢百倍）。
→ [README](algorithms/README.md) · `python algorithms/benchmark.py`

### 💻 [cs/ 编程语言原理](cs/mini_lang/)
**mini-lang 解释器** —— 词法分析（行列定位报错）→ Pratt 解析（优先级即语法）→
树遍历求值（链式作用域/闭包/递归/控制流/内建函数）→ REPL。
14 个测试覆盖闭包计数器、无限递归护栏、短路求值等。
→ [README](cs/mini_lang/README.md) · `python cs/mini_lang/repl.py`

### ⏰ [systems/ 系统编程](systems/cronlite/)
**cronlite 调度器** —— 手写 cron 表达式解析（POSIX 双受限 OR 语义、闰年）、
按月/日/时逐级快进的 `next_after`、时间可注入的调度引擎、任务失败隔离。
→ [README](systems/cronlite/README.md)

## 快速开始

```bash
pip install -e .
pytest -q                            # 80 个测试，全部离线

python software/taskapi/run.py       # Web 服务 + Swagger 文档
python ai-agents/demo_offline.py     # 智能体离线演示（无需 API Key）
python ai-agents/cli.py              # 接真实模型
python algorithms/benchmark.py       # 排序性能基准
python cs/mini_lang/repl.py          # mini-lang 交互式解释器
```

## 说明

- 全部代码为本人实现；算法与解释器不搬运现成实现，注释侧重思路推导；
- 每个子项目有独立 README：设计决策、面试追问点、已知边界；
- License: [MIT](LICENSE)
