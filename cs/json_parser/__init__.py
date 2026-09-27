"""json_parser: 从零实现的 JSON 解析器（词法 + 递归下降 + 序列化）。"""

from .parser import JSONParseError, dumps, load, loads, minify, dumps as dump  # noqa

__all__ = ["JSONParseError", "loads", "dumps", "load", "dump", "minify"]
