"""树遍历求值器：环境链（作用域）、函数闭包、控制流、内置函数。"""

from __future__ import annotations

from dataclasses import dataclass

from parser import (Assign, Binary, Bool, Call, FnDecl, FnExpr, Ident, If,
                    Num, Program, Return, Str, Unary, While)


class MiniRuntimeError(Exception):
    pass


class ReturnSignal(Exception):
    """用异常实现 return——比在每个求值点检查返回标志干净得多。"""

    def __init__(self, value):
        self.value = value


@dataclass
class Function:
    """用户函数：参数 + 函数体 + 定义时的作用域（闭包捕获的就是它）。"""

    name: str
    params: list
    body: list
    env: "Environment"


class Environment:
    """链式作用域：变量查找沿 outer 逐层向上——闭包的实现基础。"""

    def __init__(self, outer: "Environment | None" = None):
        self.vars: dict = {}
        self.outer = outer

    def get(self, name: str):
        env = self
        while env:
            if name in env.vars:
                return env.vars[name]
            env = env.outer
        raise MiniRuntimeError(f"未定义的变量 {name!r}")

    def set(self, name: str, value) -> None:
        env = self
        while env:                                # 赋值更新最近的作用域
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.outer
        self.vars[name] = value                   # 未定义则在本层声明

    def define(self, name: str, value) -> None:
        self.vars[name] = value


class Interpreter:
    MAX_CALL_DEPTH = 200

    def __init__(self, print_fn=print):
        self.globals = Environment()
        self.print_fn = print_fn
        self._depth = 0
        for name, fn in {
            "print": lambda *a: self.print_fn(" ".join(_show(x) for x in a)),
            "len": len, "abs": abs, "min": min, "max": max,
            "str": _show, "int": lambda x: int(x), "float": float,
        }.items():
            self.globals.define(name, fn)

    # ---------- 入口 ----------
    def run(self, program: Program):
        result = None
        for stmt in program.statements:
            result = self.eval(stmt, self.globals)
        return result

    # ---------- 求值 ----------
    def eval(self, node, env: Environment):
        match node:
            case Num() | Str() | Bool():
                return node.value
            case Ident():
                return env.get(node.name)
            case Assign():
                value = self.eval(node.value, env)
                env.set(node.name, value)
                return value
            case Binary():
                return self._binary(node, env)
            case Unary():
                v = self.eval(node.operand, env)
                if node.op == "-":
                    return -_require_number(v)
                return not _truthy(v)
            case If():
                if _truthy(self.eval(node.cond, env)):
                    return self._exec_block(node.then, Environment(env))
                return self._exec_block(node.otherwise, Environment(env))
            case While():
                result = None
                while _truthy(self.eval(node.cond, env)):
                    result = self._exec_block(node.body, Environment(env))
                return result
            case FnDecl():
                env.define(node.name,
                           Function(node.name, node.params, node.body, env))
                return None
            case FnExpr():
                return Function("<匿名>", node.params, node.body, env)
            case Call():
                return self._call(node, env)
            case Return():
                raise ReturnSignal(self.eval(node.value, env))
            case Program():
                return self.run(node)
            case _:
                raise MiniRuntimeError(f"未知节点 {type(node).__name__}")

    def _exec_block(self, stmts: list, env: Environment):
        result = None
        for stmt in stmts:
            result = self.eval(stmt, env)
        return result

    def _call(self, node: Call, env: Environment):
        callee = env.get(node.callee)
        args = [self.eval(a, env) for a in node.args]
        if callable(callee):                      # 内置函数
            return callee(*args)
        if not isinstance(callee, Function):
            raise MiniRuntimeError(f"{node.callee!r} 不是函数")
        if len(args) != len(callee.params):
            raise MiniRuntimeError(
                f"{callee.name}() 需要 {len(callee.params)} 个参数，收到 {len(args)} 个")
        if self._depth >= self.MAX_CALL_DEPTH:
            raise MiniRuntimeError("调用栈过深（可能无限递归）")
        call_env = Environment(callee.env)        # 闭包：捕获定义时的作用域
        for p, a in zip(callee.params, args):
            call_env.define(p, a)
        self._depth += 1
        try:
            self._exec_block(callee.body, call_env)
            return None
        except ReturnSignal as sig:
            return sig.value
        finally:
            self._depth -= 1

    def _binary(self, node: Binary, env: Environment):
        op = node.op
        if op == "&&":
            left = self.eval(node.left, env)
            return self.eval(node.right, env) if _truthy(left) else False
        if op == "||":
            left = self.eval(node.left, env)
            return True if _truthy(left) else self.eval(node.right, env)
        left, right = self.eval(node.left, env), self.eval(node.right, env)
        match op:
            case "+":
                if isinstance(left, str) or isinstance(right, str):
                    return _show(left) + _show(right)   # 字符串拼接（自动转换）
                return _require_number(left) + _require_number(right)
            case "-":
                return _require_number(left) - _require_number(right)
            case "*":
                if isinstance(left, str):
                    return left * int(right)
                return _require_number(left) * _require_number(right)
            case "/":
                rn = _require_number(right)
                if rn == 0:
                    raise MiniRuntimeError("除以零")
                return _require_number(left) / rn
            case "%":
                return _require_number(left) % _require_number(right)
            case "==":
                return left == right
            case "!=":
                return left != right
            case "<":
                return _require_number(left) < _require_number(right)
            case ">":
                return _require_number(left) > _require_number(right)
            case "<=":
                return _require_number(left) <= _require_number(right)
            case ">=":
                return _require_number(left) >= _require_number(right)
        raise MiniRuntimeError(f"未知运算符 {op}")


def _truthy(v) -> bool:
    return v is not None and v is not False and v != 0 and v != ""


def _require_number(v) -> float | int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise MiniRuntimeError(f"需要数字，收到 {_show(v)}")
    return v


def _show(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def run_source(source: str, print_fn=print):
    """一站式入口：源码 -> 词法 -> 语法 -> 求值。"""
    from parser import parse

    program = parse(source)
    return Interpreter(print_fn=print_fn).run(program)
