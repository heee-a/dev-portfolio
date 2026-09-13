"""词法分析器：源码字符流 -> Token 流。

支持：数字/字符串/标识符、关键字、运算符（含 == != <= >= && ||）、
行注释 #，并在 Token 上携带行号与列号——语法错误可以精确定位。
"""

from __future__ import annotations

from dataclasses import dataclass

KEYWORDS = {"let", "if", "else", "while", "fn", "true", "false", "return"}
SINGLE = {"+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH", "%": "PERCENT",
          "(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE",
          ",": "COMMA", ";": "SEMI", "<": "LT", ">": "GT", "=": "ASSIGN",
          "!": "BANG"}
COMPOUND = {"==": "EQ", "!=": "NEQ", "<=": "LE", ">=": "GE", "&&": "AND",
            "||": "OR"}


class MiniSyntaxError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"第 {line} 行第 {col} 列: {message}")
        self.line, self.col = line, col


@dataclass
class Token:
    kind: str          # NUM / STR / IDENT / 关键字 / 运算符名 / EOF
    value: object
    line: int
    col: int


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i, line, col = 0, 1, 1
    n = len(src)

    def error(msg: str) -> MiniSyntaxError:
        return MiniSyntaxError(msg, line, col)

    while i < n:
        ch = src[i]
        if ch == "\n":
            i, line, col = i + 1, line + 1, 1
            continue
        if ch in " \t\r":
            i, col = i + 1, col + 1
            continue
        if ch == "#" or src[i:i + 2] == "//":   # 行注释（# 与 // 皆可）
            while i < n and src[i] != "\n":
                i += 1
            continue

        start_line, start_col = line, col

        # 双字符运算符
        two = src[i:i + 2]
        if two in COMPOUND:
            tokens.append(Token(COMPOUND[two], two, start_line, start_col))
            i, col = i + 2, col + 2
            continue

        # 单字符
        if ch in SINGLE:
            tokens.append(Token(SINGLE[ch], ch, start_line, start_col))
            i, col = i + 1, col + 1
            continue

        # 数字
        if ch.isdigit():
            j = i
            while j < n and (src[j].isdigit() or (src[j] == "." and j + 1 < n
                                                  and src[j + 1].isdigit())):
                j += 1
            text = src[i:j]
            if text.count(".") > 1:
                raise error(f"非法数字 {text!r}")
            tokens.append(Token("NUM", float(text) if "." in text else int(text),
                                start_line, start_col))
            col += j - i
            i = j
            continue

        # 字符串
        if ch == '"':
            j = i + 1
            buf = []
            while j < n and src[j] != '"':
                if src[j] == "\n":
                    raise error("字符串未闭合（跨行）")
                if src[j] == "\\" and j + 1 < n and src[j + 1] in ('"', "\\n", "\\"):
                    esc = src[j + 1]
                    buf.append({'"': '"', "n": "\n", "\\": "\\"}[esc])
                    j += 2
                else:
                    buf.append(src[j])
                    j += 1
            if j >= n:
                raise error("字符串未闭合")
            tokens.append(Token("STR", "".join(buf), start_line, start_col))
            col += j + 1 - i
            i = j + 1
            continue

        # 标识符 / 关键字
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            tokens.append(Token(word if word in KEYWORDS else "IDENT", word,
                                start_line, start_col))
            col += j - i
            i = j
            continue

        raise error(f"无法识别的字符 {ch!r}")

    tokens.append(Token("EOF", None, line, col))
    return tokens
