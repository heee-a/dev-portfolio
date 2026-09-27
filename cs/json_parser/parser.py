"""从零实现的 JSON 解析器：词法分析 + 递归下降 + 序列化。

功能：loads / load / dumps / dump（与标准库 json 语义对齐的子集），
错误统一抛 JSONParseError 并带行列号定位。

实现要点：
- 词法器逐字符扫描，字符串支持全部 JSON 转义（含 \\uXXXX 代理对）；
- 语法分析递归下降，每层显式检查分隔符与结尾，杜绝静默截断；
- 序列化器支持 indent 美化 / ensure_ascii / 紧凑模式。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class JSONParseError(ValueError):
    """JSON 解析错误，带行列号定位。"""

    def __init__(self, message: str, pos: int, source: str):
        line = source.count("\n", 0, pos) + 1
        col = pos - (source.rfind("\n", 0, pos) + 1) + 1
        super().__init__(f"{message}（第 {line} 行第 {col} 列）")
        self.pos = pos


# ---------------- 词法 ----------------
_PUNCT = {"{": "LBRACE", "}": "RBRACE", "[": "LBRACKET", "]": "RBRACKET",
          ":": "COLON", ",": "COMMA"}
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
            "n": "\n", "r": "\r", "t": "\t"}


@dataclass
class Token:
    kind: str            # LBRACE/RBRACE/LBRACKET/RBRACKET/COLON/COMMA/
                         # STRING/NUMBER/TRUE/FALSE/NULL/EOF
    value: object
    pos: int


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i, n = 0, len(source)
    while i < n:
        ch = source[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch in _PUNCT:
            tokens.append(Token(_PUNCT[ch], ch, i))
            i += 1
            continue
        if ch == '"':
            tokens.append(Token("STRING", _scan_string(source, i), i))
            i = _scan_string_end(source, i)
            continue
        if ch in "-0123456789":
            value, end = _scan_number(source, i)
            tokens.append(Token("NUMBER", value, i))
            i = end
            continue
        for literal, kind in (("true", "TRUE"), ("false", "FALSE"), ("null", "NULL")):
            if source.startswith(literal, i):
                tokens.append(Token(kind, {"true": True, "false": False,
                                           "null": None}[literal], i))
                i += len(literal)
                break
        else:
            raise JSONParseError(f"非法字符 {ch!r}", i, source)
    tokens.append(Token("EOF", None, n))
    return tokens


def _scan_string(source: str, start: int) -> str:
    """从起始引号扫描字符串字面量，返回解码后的值。"""
    out = []
    i = start + 1
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == '"':
            return "".join(out)
        if ch == "\\":
            if i + 1 >= n:
                raise JSONParseError("转义符后缺少字符", i, source)
            esc = source[i + 1]
            if esc in _ESCAPES:
                out.append(_ESCAPES[esc])
                i += 2
            elif esc == "u":
                hex4 = source[i + 2:i + 6]
                if len(hex4) != 4:
                    raise JSONParseError("\\u 转义需要 4 位十六进制", i, source)
                try:
                    code = int(hex4, 16)
                except ValueError:
                    raise JSONParseError(f"非法十六进制 {hex4!r}", i + 2, source)
                i += 6
                # 代理对：高代理后必须跟 \uDC00-\uDFFF
                if 0xD800 <= code <= 0xDBFF and source[i:i + 2] == "\\u":
                    low = int(source[i + 2:i + 6], 16)
                    if 0xDC00 <= low <= 0xDFFF:
                        code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                        i += 6
                out.append(chr(code))
            else:
                raise JSONParseError(f"非法转义 \\{esc}", i, source)
            continue
        if ord(ch) < 0x20:
            raise JSONParseError("字符串内含未转义控制字符", i, source)
        out.append(ch)
        i += 1
    raise JSONParseError("字符串缺少结束引号", start, source)


def _scan_string_end(source: str, start: int) -> int:
    """返回字符串结束引号之后的位置（与 _scan_string 同步扫描）。"""
    i = start + 1
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == '"':
            return i + 1
        if ch == "\\":
            if source[i + 1:i + 2] == "u":
                i += 6
                # 代理对再跳 6
                code = int(source[i - 4:i], 16)
                if 0xD800 <= code <= 0xDBFF and source[i:i + 2] == "\\u":
                    i += 6
            else:
                i += 2
            continue
        i += 1
    raise JSONParseError("字符串缺少结束引号", start, source)


def _scan_number(source: str, start: int) -> tuple[float | int, int]:
    i = start
    n = len(source)
    if source[i] == "-":
        i += 1
    int_part = ""
    while i < n and source[i].isdigit():
        int_part += source[i]
        i += 1
    if not int_part:
        raise JSONParseError("数字缺少整数部分", start, source)
    if int_part.startswith("0") and len(int_part) > 1:
        raise JSONParseError("前导零不合法", start, source)
    frac, exp = "", ""
    if i < n and source[i] == ".":
        i += 1
        while i < n and source[i].isdigit():
            frac += source[i]
            i += 1
        if not frac:
            raise JSONParseError("小数点后缺少数字", start, source)
    if i < n and source[i] in "eE":
        i += 1
        if i < n and source[i] in "+-":
            exp += source[i]
            i += 1
        digits = ""
        while i < n and source[i].isdigit():
            digits += source[i]
            i += 1
        if not digits:
            raise JSONParseError("指数缺少数字", start, source)
        exp += digits
    text = ("-" if source[start] == "-" else "") + int_part + \
           (f".{frac}" if frac else "") + (f"e{exp}" if exp else "")
    value = float(text) if (frac or exp) else int(text)
    return value, i


# ---------------- 语法分析 ----------------
class _Parser:
    def __init__(self, source: str):
        self.source = source
        self.tokens = tokenize(source)
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.kind != "EOF":
            self.pos += 1
        return tok

    def expect(self, kind: str) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            raise JSONParseError(f"期望 {kind}，实际 {tok.kind}", tok.pos, self.source)
        return self.advance()

    def parse(self) -> object:
        value = self.parse_value()
        tok = self.peek()
        if tok.kind != "EOF":
            raise JSONParseError("JSON 文档结束后仍有内容", tok.pos, self.source)
        return value

    def parse_value(self) -> object:
        kind = self.peek().kind
        if kind == "LBRACE":
            return self.parse_object()
        if kind == "LBRACKET":
            return self.parse_array()
        if kind == "STRING":
            return self.advance().value
        if kind == "NUMBER":
            return self.advance().value
        if kind in ("TRUE", "FALSE", "NULL"):
            return self.advance().value
        raise JSONParseError(f"意外的 {kind}", self.peek().pos, self.source)

    def parse_object(self) -> dict:
        self.expect("LBRACE")
        obj: dict = {}
        if self.peek().kind == "RBRACE":
            self.advance()
            return obj
        while True:
            key_tok = self.expect("STRING")
            self.expect("COLON")
            obj[key_tok.value] = self.parse_value()
            tok = self.advance()
            if tok.kind == "RBRACE":
                return obj
            if tok.kind != "COMMA":
                raise JSONParseError("对象中期望 ',' 或 '}'", tok.pos, self.source)

    def parse_array(self) -> list:
        self.expect("LBRACKET")
        arr: list = []
        if self.peek().kind == "RBRACKET":
            self.advance()
            return arr
        while True:
            arr.append(self.parse_value())
            tok = self.advance()
            if tok.kind == "RBRACKET":
                return arr
            if tok.kind != "COMMA":
                raise JSONParseError("数组中期望 ',' 或 ']'", tok.pos, self.source)


# ---------------- 序列化 ----------------
def _encode(value, indent: int | None, level: int, ensure_ascii: bool,
            compact: bool = False) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("JSON 不支持 NaN/Infinity")
        return repr(value) if isinstance(value, float) else str(value)
    if isinstance(value, str):
        return _encode_string(value, ensure_ascii)
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        items = [_encode(v, indent, level + 1, ensure_ascii, compact)
                 for v in value]
        if compact:
            return "[" + ",".join(items) + "]"
        if indent is None:
            return "[" + ", ".join(items) + "]"
        pad, inner = " " * (indent * (level + 1)), " " * (indent * level)
        return "[\n" + ",\n".join(pad + it for it in items) + "\n" + inner + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        kv_sep = ":" if compact else ": "
        items = [_encode_string(str(k), ensure_ascii) + kv_sep +
                 _encode(v, indent, level + 1, ensure_ascii, compact)
                 for k, v in value.items()]
        if compact:
            return "{" + ",".join(items) + "}"
        if indent is None:
            return "{" + ", ".join(items) + "}"
        pad, inner = " " * (indent * (level + 1)), " " * (indent * level)
        return "{\n" + ",\n".join(pad + it for it in items) + "\n" + inner + "}"
    raise TypeError(f"类型 {type(value).__name__} 不可序列化为 JSON")


_ESCAPE_MAP = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t",
               "\b": "\\b", "\f": "\\f"}


def _encode_string(s: str, ensure_ascii: bool) -> str:
    out = ['"']
    for ch in s:
        if ch in _ESCAPE_MAP:
            out.append(_ESCAPE_MAP[ch])
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        elif ensure_ascii and ord(ch) > 0x7E:
            code = ord(ch)
            if code > 0xFFFF:
                code -= 0x10000
                out.append(f"\\u{0xD800 + (code >> 10):04x}"
                           f"\\u{0xDC00 + (code & 0x3FF):04x}")
            else:
                out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


# ---------------- 公共 API ----------------
def loads(source: str) -> object:
    return _Parser(source).parse()


def dumps(value, indent: int | None = None, ensure_ascii: bool = False) -> str:
    return _encode(value, indent, 0, ensure_ascii)


def load(path: str | Path) -> object:
    return loads(Path(path).read_text(encoding="utf-8"))


def dump(value, path: str | Path, indent: int | None = None) -> None:
    Path(path).write_text(dumps(value, indent), encoding="utf-8")


def minify(source: str, ensure_ascii: bool = False) -> str:
    """去掉 JSON 文本中的无意义空白（重新解析后以紧凑分隔符输出）。"""
    return _encode(loads(source), None, 0, ensure_ascii, compact=True)
    """去掉 JSON 文本中的无意义空白（基于重新解析）。"""
    return dumps(loads(source))
