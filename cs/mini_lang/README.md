# mini-lang：从零实现的表达式语言

不使用任何解析库，手写一门小语言的三层完整实现：

```
源码文本
  │  lexer.py     词法分析：字符流 -> Token 流（行/列定位，支持 # 与 // 注释）
  ▼
Token 流
  │  parser.py    Pratt 解析：Token -> AST（运算符优先级 = 绑定力表）
  ▼
AST
  │  interpreter.py  树遍历求值：链式作用域 / 闭包 / 递归 / 控制流
  ▼
结果
```

## 语言特性

- 数字（整/浮点）、字符串（含转义）、布尔、`nil`
- 算术（`+ - * / %`）、比较、逻辑（`&&`/`||` **短路求值**）
- `let` 赋值、`if/else`、`while`、`fn`（命名声明 + **匿名闭包**）、`return`（异常实现）
- 作用域：链式环境，闭包捕获定义时的环境（互相独立的计数器验证）
- 内建：`print / len / abs / min / max / str / int / float`
- 工程化：行列级语法错误定位、200 层调用栈护栏（无限递归友好报错）、REPL

## 示例

```js
// examples/demo.mini —— 闭包捕获外层作用域
fn make_counter() {
    let count = 0;
    return fn() {          // 匿名函数：Pratt 解析器在表达式位置遇到 fn
        count = count + 1;
        return count;
    };
}
let next = make_counter();
next(); next();
print("计数器:", next());  // 3
```

运行 `python repl.py` 交互体验，或 `python -c "from interpreter import run_source; ..."`。

## 测试（14 项）

`pytest tests/test_mini_lang.py -q`，覆盖：
- 词法：行列定位、未闭合字符串
- 优先级：`2+3*4`、括号、一元负号、短路求值（右侧除零不执行）
- 闭包：两个计数器互不干扰（作用域独立性的关键断言）
- 递归：fib(10)、200 层栈护栏
- 错误：未定义变量、除零、类型错误、参数个数

## 面试可展开的点

1. **为什么用 Pratt 而不是递归下降手写优先级**：每个中缀运算符只标一个绑定力数字，
   新增运算符 = 表中加一行，不用改解析结构；
2. **闭包 = 函数值 + 定义时环境**：`Environment` 链是唯一的数据结构支撑，
   赋值沿链查找最近作用域（与 Python 的 LEGB 一致）；
3. **return 用异常实现**：控制流穿越任意深度块，比在每层求值点传递标志干净；
4. **已知边界**：无数组/哈希类型、无 for-in、解释执行性能天然受限
   （字节码编译 + 栈机是下一步，见《Crafting Interpreters》）。
