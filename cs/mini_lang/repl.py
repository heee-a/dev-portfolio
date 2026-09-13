"""交互式 REPL：python repl.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from interpreter import Interpreter, MiniRuntimeError
from lexer import MiniSyntaxError
from parser import parse

BANNER = """
mini-lang REPL（ctrl+c 退出）
语法示例: let x = 3;  if x > 2 { print("大"); }  fn add(a, b) { return a + b; }
"""
PROMPT = "mini> "


def main() -> None:
    print(BANNER)
    interp = Interpreter()
    buffer = ""
    while True:
        try:
            line = input(PROMPT if not buffer else "... ")
        except (KeyboardInterrupt, EOFError):
            print("\n再见")
            break
        if line.strip() in ("exit", "quit"):
            break
        buffer += line + "\n"
        if buffer.count("{") > buffer.count("}"):
            continue                       # 多行块未闭合，继续读
        try:
            result = interp.run(parse(buffer))
            if result is not None:
                from interpreter import _show
                print(_show(result))
        except (MiniSyntaxError, MiniRuntimeError) as e:
            print(f"错误: {e}")
        buffer = ""


if __name__ == "__main__":
    main()
