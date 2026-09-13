"""字符串算法：KMP、回文、无重复字符最长子串。"""

from __future__ import annotations


def kmp_search(text: str, pattern: str) -> int:
    """KMP：O(n+m)，先构造前缀函数（失配表）避免主串指针回退。

    面试点：next 数组含义 = pattern[:i] 的最长相等前后缀长度。
    """
    if not pattern:
        return 0
    nxt = [0] * len(pattern)
    k = 0
    for i in range(1, len(pattern)):
        while k and pattern[i] != pattern[k]:
            k = nxt[k - 1]
        if pattern[i] == pattern[k]:
            k += 1
        nxt[i] = k
    k = 0
    for i, ch in enumerate(text):
        while k and ch != pattern[k]:
            k = nxt[k - 1]
        if ch == pattern[k]:
            k += 1
            if k == len(pattern):
                return i - k + 1
    return -1


def longest_palindrome(s: str) -> str:
    """最长回文子串：中心扩展 O(n²)/O(1)。Manacher O(n) 可作面试加分口述。"""
    if not s:
        return ""
    best = (0, 1)  # (start, length)

    def expand(lo: int, hi: int) -> tuple[int, int]:
        while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
            lo -= 1
            hi += 1
        return lo + 1, hi - lo - 1

    for i in range(len(s)):
        for st, ln in (expand(i, i), expand(i, i + 1)):   # 奇/偶中心
            if ln > best[1]:
                best = (st, ln)
    return s[best[0]:best[0] + best[1]]


def length_of_longest_substring(s: str) -> int:
    """无重复字符的最长子串（LeetCode 3）：滑动窗口 + 最近位置表，O(n)。"""
    last: dict[str, int] = {}
    best = left = 0
    for right, ch in enumerate(s):
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best


def group_anagrams(words: list[str]) -> list[list[str]]:
    """字母异位词分组：排序结果作哈希键。O(n·k log k)。"""
    groups: dict[str, list[str]] = {}
    for w in words:
        key = "".join(sorted(w))
        groups.setdefault(key, []).append(w)
    return list(groups.values())
