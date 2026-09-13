"""动态规划经典题：从入门到面试高频。"""

from __future__ import annotations

from functools import lru_cache


def fib(n: int) -> int:
    """斐波那契（滚动变量 O(1) 空间）。面试点：朴素递归 O(2^n) -> 记忆化 -> 滚动变量的三级优化。"""
    if n < 2:
        return n
    prev, cur = 0, 1
    for _ in range(2, n + 1):
        prev, cur = cur, prev + cur
    return cur


def climb_stairs(n: int) -> int:
    """爬楼梯：每次 1 或 2 阶的方案数（就是斐波那契的业务化包装）。"""
    return fib(n + 1)


def lis(nums: list[int]) -> int:
    """最长递增子序列长度。

    O(n²) DP：dp[i] = 以 i 结尾的 LIS 长度；
    O(n log n) 贪心+二分：维护 tails 数组，tails[k] = 长度 k+1 的 LIS 的最小结尾。
    面试点：tails 数组不是 LIS 本身，只是长度等价。
    """
    tails: list[int] = []
    for x in nums:
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if tails[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        if lo == len(tails):
            tails.append(x)
        else:
            tails[lo] = x
    return len(tails)


def lcs(text1: str, text2: str) -> int:
    """最长公共子序列长度（LeetCode 1143）。二维 DP 的模板题。"""
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def edit_distance(word1: str, word2: str) -> int:
    """编辑距离（LeetCode 72）：插入/删除/替换的最少操作数。

    状态转移与 LCS 同构，diff 工具（git diff）的底层原理。
    """
    m, n = len(word1), len(word2)
    dp = list(range(n + 1))                       # 滚动数组优化到 O(n) 空间
    for i in range(1, m + 1):
        prev_diag, dp[0] = dp[0], i
        for j in range(1, n + 1):
            prev_diag, dp[j] = dp[j], (
                prev_diag if word1[i - 1] == word2[j - 1]
                else min(dp[j], dp[j - 1], prev_diag) + 1)
    return dp[n]


def knapsack_01(weights: list[int], values: list[int], capacity: int) -> int:
    """0-1 背包最大价值。滚动数组必须倒序遍历容量——正序会变成完全背包（可重复选）。"""
    dp = [0] * (capacity + 1)
    for w, v in zip(weights, values):
        for c in range(capacity, w - 1, -1):      # 倒序！
            dp[c] = max(dp[c], dp[c - w] + v)
    return dp[capacity]


def coin_change(coins: list[int], amount: int) -> int:
    """零钱兑换：凑出 amount 的最少硬币数（完全背包）。无法凑出返回 -1。

    面试点：与 0-1 背包唯一的遍历顺序差别（正序=可重复使用）。
    """
    dp = [0] + [float("inf")] * amount
    for c in coins:
        for x in range(c, amount + 1):
            dp[x] = min(dp[x], dp[x - c] + 1)
    return dp[amount] if dp[amount] != float("inf") else -1


def longest_palindrome_subseq(s: str) -> int:
    """最长回文子序列：区间 DP，等价于 LCS(s, reversed(s))。"""
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        dp[i][i] = 1
        for j in range(i + 1, n):
            dp[i][j] = (dp[i + 1][j - 1] + 2 if s[i] == s[j]
                        else max(dp[i + 1][j], dp[i][j - 1]))
    return dp[0][n - 1]
