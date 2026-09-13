"""排序算法性能基准：同一随机数组上计时对比，输出表格。

运行: python benchmark.py
（教学用 timeit 对比；注意 Python 解释器常数与 O(n log n) 的理论优势不矛盾——
  n 到万级时差距才明显）
"""

import random
import time

from sorting import ALGORITHMS


def bench(n: int, repeats: int = 3) -> dict[str, float]:
    data = [random.randint(0, 10**6) for _ in range(n)]
    out = {}
    for name, fn in ALGORITHMS.items():
        times = []
        for _ in range(repeats):
            arr = list(data)
            t0 = time.perf_counter()
            fn(arr)
            times.append(time.perf_counter() - t0)
        out[name] = min(times)  # 取最小值以减少系统噪声
    return out


def main() -> None:
    random.seed(42)
    print(f"{'算法':<10}{'n=200 (s)':>12}{'n=2000 (s)':>12}{'n=8000 (s)':>12}")
    small = bench(200)
    mid = bench(2000)
    big = bench(8000)
    for name in ALGORITHMS:
        print(f"{name:<10}{small[name]:>12.4f}{mid[name]:>12.4f}{big[name]:>12.4f}")
    print("\n预期：O(n²) 三兄弟在 n=8000 时明显掉队；快排/归并/堆排保持平缓增长。")


if __name__ == "__main__":
    main()
