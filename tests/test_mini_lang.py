"""mini_lang 全链路测试：源码 -> 词法 -> 语法 -> 求值。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cs" / "mini_lang"))

import pytest

from interpreter import MiniRuntimeError, run_source
from lexer import MiniSyntaxError, tokenize


def run(src: str):
    out = []
    value = run_source(src, print_fn=out.append)
    return value, out


# ---------------- 词法 ----------------
def test_tokenize_positions():
    tok = tokenize('let x = 1;\nx = 2;')
    assert tok[0].kind == "let" and tok[0].line == 1
    second_let = [t for t in tok if t.kind == "NUM"]
    assert second_let[1].line == 2


def test_syntax_error_has_position():
    with pytest.raises(MiniSyntaxError, match="第 1 行"):
        run("let = 5;")


def test_unterminated_string():
    with pytest.raises(MiniSyntaxError, match="未闭合"):
        run('print("abc);')


# ---------------- 表达式 ----------------
def test_arithmetic_precedence():
    assert run("2 + 3 * 4;")[0] == 14
    assert run("(2 + 3) * 4;")[0] == 20
    assert run("10 % 3;")[0] == 1
    assert run("-5 + 2;")[0] == -3


def test_logic_short_circuit():
    # 右侧除零不能被执行——短路生效
    v, _ = run("false && 1 / 0 == 1;")
    assert v is False
    v, _ = run("true || 1 / 0 == 1;")
    assert v is True


def test_string_concat():
    v, _ = run('"年龄: " + 18;')
    assert v == "年龄: 18"


# ---------------- 变量与控制流 ----------------
def test_variables_and_if():
    v, out = run("""
let x = 7;
if x > 5 { print("大"); } else { print("小"); }
x = x * 2;
""")
    assert out == ["大"] and v == 14


def test_while_loop():
    v, _ = run("""
let s = 0;
let i = 1;
while i <= 100 { s = s + i; i = i + 1; }
s;
""")
    assert v == 5050


# ---------------- 函数 / 闭包 / 递归 ----------------
def test_function_and_recursion():
    v, out = run("""
fn fib(n) { if n < 2 { return n; } return fib(n - 1) + fib(n - 2); }
print(fib(10));
fib(10);
""")
    assert out == ["55"] and v == 55


def test_closure_counter():
    v, _ = run("""
fn make_counter() {
    let count = 0;
    return fn() { count = count + 1; return count; };
}
let a = make_counter();
let b = make_counter();      // 两个闭包各自独立
a(); a();
b();
a();
""")
    assert v == 3


def test_function_argument_count_error():
    with pytest.raises(MiniRuntimeError, match="需要 2 个参数"):
        run("fn add(a, b) { return a + b; } add(1);")


def test_infinite_recursion_guard():
    with pytest.raises(MiniRuntimeError, match="调用栈过深"):
        run("fn loop() { return loop(); } loop();")


# ---------------- 运行时错误 ----------------
def test_runtime_errors():
    with pytest.raises(MiniRuntimeError, match="未定义"):
        run("nope + 1;")
    with pytest.raises(MiniRuntimeError, match="除以零"):
        run("1 / 0;")
    with pytest.raises(MiniRuntimeError, match="需要数字"):
        run('"a" - 1;')


# ---------------- 示例文件回归 ----------------
def test_example_file_runs():
    src = (Path(__file__).resolve().parents[1] / "cs" / "mini_lang"
           / "examples" / "demo.mini").read_text(encoding="utf-8")
    value, out = run(src)
    assert out == ["fib(10) = 55", "计数器: 3", "1+2+...+100 = 5050"]
