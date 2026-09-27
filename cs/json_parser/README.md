# JSON 解析器（从零实现）

手写 JSON 的完整实现：**词法分析 → 递归下降语法分析 → 序列化**，
与标准库 `json` 模块语义对齐（`loads/dumps/load/dump`）。

## 实现要点

| 模块 | 内容 | 难点 |
|---|---|---|
| 词法器 | 逐字符扫描；字符串支持全部 JSON 转义含 `\\uXXXX` 代理对（emoji 等 4 字节字符） | 转义扫描与位置同步 |
| 语法器 | 递归下降，每层显式校验分隔符与文档结尾 | 错误定位到行列号 |
| 数字 | 整数/小数/指数；拒绝前导零、空小数、空指数（严格 RFC 8259） | 分支多易漏 |
| 序列化 | 紧凑/缩进两种模式；`ensure_ascii` 含代理对拆分 | 浮点 `repr` 的往返一致性 |

## 用法

```python
from json_parser import loads, dumps, minify, JSONParseError

loads('{"a": [1, 2.5e3, "中文"]}')          # {'a': [1, 2500.0, '中文']}
dumps({"键": "值"}, indent=2)               # 缩进序列化
minify('{"a" : 1 }')                        # '{"a":1}'
loads('{"a": 1,}')                          # JSONParseError（第 1 行第 8 列）
```

## 测试

`tests/test_json_parser.py`：与标准库 `json` 的 roundtrip 对照、
非法输入全部报错且带行列号、代理对转义、深度嵌套、数字边界
（前导零/`1.`/`1e`/`-` 单独出现）等 20+ 断言。
