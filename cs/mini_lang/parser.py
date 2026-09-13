"""语法分析：Token 流 -> AST（Pratt 解析法处理表达式优先级）。

Pratt 的核心：每个中缀运算符有绑定力（binding power），
右侧操作数按「更高绑定力」递归解析，优先级表即语言语法本身。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexer import MiniSyntaxError, Token, tokenize

# 优先级（越大绑定越紧）
LOWEST, OR, AND, EQUALS, COMPARE, SUM, PRODUCT, CALL = 1, 2, 3, 4, 5, 6, 7, 8
INFIX_BP = {"OR": OR, "AND": AND, "EQ": EQUALS, "NEQ": EQUALS,
            "LT": COMPARE, "GT": COMPARE, "LE": COMPARE, "GE": COMPARE,
            "PLUS": SUM, "MINUS": SUM, "STAR": PRODUCT, "SLASH": PRODUCT,
            "PERCENT": PRODUCT}
INFIX_OP = {"PLUS": "+", "MINUS": "-", "STAR": "*", "SLASH": "/",
            "PERCENT": "%", "EQ": "==", "NEQ": "!=", "LT": "<", "GT": ">",
            "LE": "<=", "GE": ">=", "AND": "&&", "OR": "||"}


# ---------- AST 节点 ----------
@dataclass
class Num:
    value: float | int


@dataclass
class Str:
    value: str


@dataclass
class Bool:
    value: bool


@dataclass
class Ident:
    name: str


@dataclass
class Assign:
    name: str
    value: object


@dataclass
class Binary:
    op: str
    left: object
    right: object


@dataclass
class Unary:
    op: str
    operand: object


@dataclass
class If:
    cond: object
    then: list
    otherwise: list


@dataclass
class While:
    cond: object
    body: list


@dataclass
class FnDecl:
    name: str
    params: list
    body: list


@dataclass
class FnExpr:
    """匿名函数表达式（闭包本体）：`return fn() { ... };` 或 `let f = fn(a){...};`"""

    params: list
    body: list


@dataclass
class Call:
    callee: str
    args: list


@dataclass
class Return:
    value: object


@dataclass
class Program:
    statements: list = field(default_factory=list)


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # —— 基础游标 ——
    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: str) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            raise MiniSyntaxError(f"期望 {kind}，实际是 {tok.kind} {tok.value!r}",
                                  tok.line, tok.col)
        return self.advance()

    # ---------- 语句 ----------
    def parse_program(self) -> Program:
        prog = Program()
        while self.peek().kind != "EOF":
            prog.statements.append(self.parse_statement())
        return prog

    def parse_block(self) -> list:
        self.expect("LBRACE")
        stmts = []
        while self.peek().kind not in ("RBRACE", "EOF"):
            stmts.append(self.parse_statement())
        self.expect("RBRACE")
        return stmts

    def parse_statement(self):
        tok = self.peek()
        if tok.kind == "let":
            stmt = self.parse_let()
        elif tok.kind == "if":
            stmt = self.parse_if()
        elif tok.kind == "while":
            stmt = self.parse_while()
        elif tok.kind == "fn":
            stmt = self.parse_fn()
        elif tok.kind == "return":
            self.advance()
            stmt = Return(self.parse_expression())
        else:
            stmt = self.parse_expression_statement()
        if self.peek().kind == "SEMI":            # 语句后的分号统一消费
            self.advance()
        return stmt

    def parse_let(self) -> Assign:
        self.expect("let")
        name = self.expect("IDENT").value
        self.expect("ASSIGN")
        return Assign(name, self.parse_expression())

    def parse_if(self) -> If:
        self.expect("if")
        cond = self.parse_expression()
        then = self.parse_block()
        otherwise = []
        if self.peek().kind == "else":
            self.advance()
            otherwise = self.parse_block()
        return If(cond, then, otherwise)

    def parse_while(self) -> While:
        self.expect("while")
        cond = self.parse_expression()
        return While(cond, self.parse_block())

    def parse_fn(self) -> FnDecl | FnExpr:
        self.advance()                            # fn
        name = None
        if self.peek().kind == "IDENT":           # 名称可选：语句位置为声明，表达式位置为闭包
            name = self.advance().value
        self.expect("LPAREN")
        params = []
        if self.peek().kind != "RPAREN":
            params.append(self.expect("IDENT").value)
            while self.peek().kind == "COMMA":
                self.advance()
                params.append(self.expect("IDENT").value)
        self.expect("RPAREN")
        body = self.parse_block()
        if name is None:
            return FnExpr(params, body)
        return FnDecl(name, params, body)

    def parse_expression_statement(self):
        expr = self.parse_expression()
        if self.peek().kind == "SEMI":
            self.advance()
        return expr

    # ---------- 表达式（Pratt） ----------
    def parse_expression(self, bp: int = LOWEST):
        left = self.parse_prefix()
        while (infix := self.peek().kind) in INFIX_BP and INFIX_BP[infix] > bp:
            self.advance()
            left = Binary(INFIX_OP[infix], left,
                          self.parse_expression(INFIX_BP[infix]))
        if self.peek().kind == "ASSIGN":           # 赋值右结合
            self.advance()
            return Assign(left.name if hasattr(left, "name") else left,
                          self.parse_expression(LOWEST - 1))
        return left

    def parse_prefix(self):
        if self.peek().kind == "fn":              # 匿名/命名函数表达式
            return self.parse_fn()
        tok = self.advance()
        if tok.kind == "NUM":
            return Num(tok.value)
        if tok.kind == "STR":
            return Str(tok.value)
        if tok.kind in ("true", "false"):
            return Bool(tok.kind == "true")
        if tok.kind == "IDENT":
            return self.finish_call(Ident(tok.value))
        if tok.kind == "MINUS":
            return Unary("-", self.parse_expression(PRODUCT))
        if tok.kind == "BANG":
            return Unary("!", self.parse_expression(PRODUCT))
        if tok.kind == "LPAREN":
            expr = self.parse_expression()
            self.expect("RPAREN")
            return expr
        raise MiniSyntaxError(f"意外的标记 {tok.kind} {tok.value!r}",
                              tok.line, tok.col)

    def finish_call(self, callee: Ident):
        if self.peek().kind != "LPAREN":
            return callee
        self.advance()
        args = []
        if self.peek().kind != "RPAREN":
            args.append(self.parse_expression())
            while self.peek().kind == "COMMA":
                self.advance()
                args.append(self.parse_expression())
        self.expect("RPAREN")
        return Call(callee.name, args)


def parse(source: str) -> Program:
    return Parser(tokenize(source)).parse_program()
